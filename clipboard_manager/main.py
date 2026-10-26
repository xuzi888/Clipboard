import sys
import os
import json
import time
import keyboard
import hashlib
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel, QSystemTrayIcon, QMenu,
                             QStyle, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QPushButton, QDialog, QFormLayout, QSpinBox, QLineEdit, QCheckBox, QFrame, QStyleFactory, QStyledItemDelegate, QProxyStyle, QAbstractScrollArea, QScrollArea, QComboBox, QTextEdit, QStackedWidget, QToolButton, QMessageBox, QSizePolicy)
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QIcon, QClipboard, QAction, QColor, QFont, QFontMetrics, QKeyEvent, QPainterPath, QImage
from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal, QObject, QByteArray, QSize, QEvent, QPropertyAnimation, QEasingCurve, QBuffer, QIODevice, QSharedMemory, pyqtProperty, QUrl, QTimer, QRect
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

APP_VERSION = "1.1.1" # 全局统一版本号
APP_NAME = "剪贴板管理器"
APP_ID = "KjjClipboardManager"

class NoFocusStyle(QProxyStyle):
    def __init__(self, base_style=None):
        if base_style:
            super().__init__(base_style)
        else:
            super().__init__()

    def drawPrimitive(self, element, option, painter, widget=None):
        # 全局拦截并丢弃所有绘制“焦点虚线框”的请求
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)

class Toast(QWidget):
    def __init__(self, text, parent=None, theme="light", is_error=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        prefix = "❌ " if is_error else "✓ "
        self.label = QLabel(prefix + text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        
        if theme == "dark":
            color = "#f38ba8" if is_error else "#a6e3a1"
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(49, 50, 68, 0.95);
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 12px;
                    padding: 12px 24px;
                }}
            """)
        else:
            color = "#d20f39" if is_error else "#40a02b"
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(255, 255, 255, 0.95);
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 12px;
                    padding: 12px 24px;
                }}
            """)
            
        layout.addWidget(self.label)
        
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(2000)  # 稍微延长提示停留时间
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(self.close)

    def show_toast(self, pos=None):
        self.adjustSize()
        if pos:
            # 居中显示在指定的坐标上
            self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        else:
            # 如果没有指定坐标，默认居中显示在主屏幕上
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.center() - self.rect().center())
        self.show()
        self.animation.start()

class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 移除 option 中的焦点状态标志，避免系统绘制虚线框
        option.state &= ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)

class ClipboardListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        # 彻底移除自带的边框和框架绘制
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("QListWidget { border: none; outline: none; background: transparent; } QListWidget::item { border: none; outline: none; } QListWidget::item:focus { border: none; outline: none; }")
        
        # 开启完全视口重绘，禁止 Qt 默认的 bitblt (像素拷贝) 滚动，这能彻底解决滑动时出现水平残影横线的问题
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        viewport_width = self.viewport().width() - 12
        if viewport_width > 0:
            for i in range(self.count()):
                item = self.item(i)
                widget = self.itemWidget(item)
                if widget:
                    widget.setFixedWidth(viewport_width)
                    item.setSizeHint(widget.sizeHint())

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        # 强制在每次滑动后完全重绘视口，彻底解决透明背景下的残影问题
        self.viewport().update()
        
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        
        data = item.data(Qt.ItemDataRole.UserRole)
        drag = QDrag(self)
        mime_data = QMimeData()
        
        if isinstance(data, dict):
            item_type = data.get("type")
            if item_type == "image":
                path = data.get("path")
                if path and os.path.exists(path):
                    # 为了兼容大多数应用（包括拼多多、微信等 Electron 应用和 Office）
                    # 最好的方式是提供文件路径 (Urls) 和 标准图片数据 (ImageData)。
                    # 避免使用 HTML Base64，因为它会导致部分聊天软件解析混乱，无法提取出图片。
                    image = QImage(path)
                    mime_data.setImageData(image)
                    mime_data.setUrls([QUrl.fromLocalFile(path)])
            elif item_type in ["file", "document", "video", "audio", "folder"]:
                paths = data.get("urls", [])
                urls = [QUrl.fromLocalFile(p) for p in paths]
                mime_data.setUrls(urls)
                # 移除这里的 setText，因为如果同时提供文本和文件，Word等软件会优先粘贴纯文本（文件路径）而不是插入文件
            else:
                # 纯文本处理 (当 data 是 dict 且 type 为 text 或其他时)
                text = data.get("text", "")
                mime_data.setText(text)
        else:
            # 纯文本处理
            text = str(data)
            
            # 仅提供最纯净的文本拖拽，剥离任何富文本(HTML)和路径解析
            # 防止第三方软件过度解析（例如把正常的路径字符串当成文件拖入，或出现格式错误）
            mime_data.setText(text)
            
        drag.setMimeData(mime_data)
        
        widget = self.itemWidget(item)
        if widget:
            pixmap = widget.grab()
            transparent_pixmap = QPixmap(pixmap.size())
            transparent_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(transparent_pixmap)
            painter.setOpacity(0.9)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            drag.setPixmap(transparent_pixmap)
            drag.setHotSpot(QPoint(transparent_pixmap.width() // 2, transparent_pixmap.height() // 2))
            
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

from PyQt6.QtSvg import QSvgRenderer
from snippets_ui import SnippetsUI

SVG_IMAGE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>'
SVG_SNIPPETS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'
SVG_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
SVG_PAUSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>'

_svg_cache = {}

def create_svg_icon(svg_str, size=24, color=None, checked_color=None):
    def make_pixmap(c):
        # 构造缓存键
        cache_key = (svg_str, size, c)
        if cache_key in _svg_cache:
            return _svg_cache[cache_key]
            
        s = svg_str
        if c and 'currentColor' in s:
            s = s.replace('currentColor', c)
        elif 'currentColor' in s:
            s = s.replace('currentColor', '#a6adc8')
        renderer = QSvgRenderer(QByteArray(s.encode('utf-8')))
        
        # 增加渲染倍数以解决高分屏模糊和残影问题
        scale_factor = 2
        render_size = size * scale_factor
        
        pixmap = QPixmap(render_size, render_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()
        
        # 设置 devicePixelRatio 让 Qt 知道这是一个高分屏图标
        pixmap.setDevicePixelRatio(scale_factor)
        
        _svg_cache[cache_key] = pixmap
        return pixmap

    icon = QIcon()
    icon.addPixmap(make_pixmap(color), QIcon.Mode.Normal, QIcon.State.Off)
    if checked_color:
        icon.addPixmap(make_pixmap(checked_color), QIcon.Mode.Normal, QIcon.State.On)
    return icon

SVG_SETTINGS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>'
SVG_SETTINGS_BTN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>'
SVG_CLOSE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
SVG_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
SVG_DATABASE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>'
SVG_TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="#f38ba8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>'
SVG_CANCEL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
SVG_SAVE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
SVG_SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
SVG_MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
SVG_POWER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>'

SVG_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
SVG_ZOOM = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>'
SVG_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
SVG_KEYBOARD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" ry="2"/><line x1="6" y1="8" x2="6" y2="8"/><line x1="10" y1="8" x2="10" y2="8"/><line x1="14" y1="8" x2="14" y2="8"/><line x1="18" y1="8" x2="18" y2="8"/><line x1="6" y1="12" x2="6" y2="12"/><line x1="10" y1="12" x2="10" y2="12"/><line x1="14" y1="12" x2="14" y2="12"/><line x1="18" y1="12" x2="18" y2="12"/><line x1="7" y1="16" x2="17" y2="16"/></svg>'

SVG_BOOK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>'
SVG_IDEA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>'
SVG_LINK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'
SVG_SHIELD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>'
SVG_CLIPBOARD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>'

SVG_FILE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>'
SVG_IMPORT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
SVG_EXPORT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>'
SVG_FOLDER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>'
SVG_ROCKET = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="M12 15l-3-3a22 22 0 0 1 3.86-2.64c1-.62 2.21-1.32 3.14-1.36h.04c.94 0 1.95 1.05 1.95 2.04v.04c-.04.93-.74 2.14-1.36 3.14A22 22 0 0 1 12 15z"></path><path d="M16 6l2-2a2.08 2.08 0 0 1 2.83 0 2.08 2.08 0 0 1 0 2.83l-2 2"></path></svg>'
SVG_HELP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
SVG_PIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.68V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3v4.68a2 2 0 0 1-1.11 1.87l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg>'
SVG_PIN_FILLED = '<svg viewBox="0 0 24 24" fill="#df8e1d" stroke="#df8e1d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.68V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3v4.68a2 2 0 0 1-1.11 1.87l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg>'
SVG_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'

SVG_EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
SVG_MORE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>'
SVG_PALETTE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>'

def get_system_theme():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value == 1 else "dark"
    except Exception:
        return "light"

def check_autostart():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_ID)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def set_autostart(enable):
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            elif sys.argv[0].endswith('.py'):
                python_exe = sys.executable
                if python_exe.endswith('python.exe'):
                    python_exe = python_exe.replace('python.exe', 'pythonw.exe')
                script_path = os.path.abspath(sys.argv[0])
                cmd = f'"{python_exe}" "{script_path}"'
            else:
                cmd = f'"{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_ID)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Auto start error: {e}")


class HotkeySignal(QObject):
    activated = pyqtSignal()

class HotkeyInput(QLineEdit):
    def __init__(self, parent=None, default_hotkey="alt+v"):
        super().__init__(parent)
        self.setText(default_hotkey)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("点击录制快捷键")
        self.setReadOnly(True)

    def focusInEvent(self, event):
        # 仅在获取焦点时选中所有文本，方便用户知道接下来按键会覆盖它
        # 而不是直接清空，这样用户还能看到之前的快捷键是什么
        self.selectAll()
        self.setPlaceholderText("请直接按键盘...")
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setPlaceholderText("点击录制快捷键")
        # 失去焦点时取消选中文本
        self.deselect()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        # 忽略单纯的修饰键按下
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        modifiers = event.modifiers()
        parts = []
        
        # 按照常用习惯的顺序排列修饰键
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("win")

        # 映射一些特殊按键名称以匹配 keyboard 库的要求
        key_name = ""
        if key == Qt.Key.Key_Space:
            key_name = "space"
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            key_name = "enter"
        elif key == Qt.Key.Key_Escape:
            key_name = "esc"
        elif key == Qt.Key.Key_Tab:
            key_name = "tab"
        else:
            # 获取按键名称（兼容组合键的情况，过滤掉修饰键文本）
            from PyQt6.QtGui import QKeySequence
            raw_text = QKeySequence(key).toString().lower()
            # 剥离可能附带的 "ctrl+", "shift+" 等修饰键文本，只取最后的主按键
            key_name = raw_text.split('+')[-1].strip()

        if key_name:
            parts.append(key_name)
            
        hotkey_str = "+".join(parts)
        if hotkey_str:
            self.setText(hotkey_str)
            # 完成一次有效输入后自动取消焦点
            self.clearFocus()

class ConfirmDialog(QDialog):
    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)
        self.setMinimumSize(360, 260)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.result_btn = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        
        # shadow = QGraphicsDropShadowEffect()
        # shadow.setBlurRadius(20)
        # shadow.setOffset(0, 4)
        # if theme == "dark":
        #     shadow.setColor(QColor(0, 0, 0, 150))
        #     bg = "#1e1e2e"
        #     text = "#cdd6f4"
        #     border = "#313244"
        #     btn_bg = "#313244"
        #     btn_hover = "#45475a"
        #     danger_bg = "#f38ba8"
        #     danger_text = "#11111b"
        # else:
        #     shadow.setColor(QColor(0, 0, 0, 40))
        #     bg = "#ffffff"
        #     text = "#4c4f69"
        #     border = "#e6e9ef"
        #     btn_bg = "#e6e9ef"
        #     btn_hover = "#bcc0cc"
        #     danger_bg = "#d20f39"
        #     danger_text = "#eff1f5"
            
        # self.container.setGraphicsEffect(shadow)
        
        if theme == "dark":
            bg = "#1e1e2e"
            text = "#cdd6f4"
            border = "#313244"
            btn_bg = "#313244"
            btn_hover = "#45475a"
            danger_bg = "#f38ba8"
            danger_text = "#11111b"
        else:
            bg = "#ffffff"
            text = "#4c4f69"
            border = "#e6e9ef"
            btn_bg = "#e6e9ef"
            btn_hover = "#bcc0cc"
            danger_bg = "#d20f39"
            danger_text = "#eff1f5"
            
        self.container.setStyleSheet(f"""
            QWidget#Container {{
                background-color: {bg};
                border-radius: 12px;
                border: 1px solid {border};
            }}
            QLabel {{
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 24px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: none;
            }}
            QPushButton#CancelBtn {{
                background-color: {btn_bg};
                color: {text};
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#ConfirmBtn {{
                background-color: {danger_bg};
                color: {danger_text};
            }}
            QPushButton#ConfirmBtn:hover {{
                background-color: {danger_text};
                color: {danger_bg};
            }}
        """)
        
        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(20, 24, 20, 20)
        c_layout.setSpacing(16)
        
        title_lbl = QLabel("确认彻底清除？")
        title_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        msg_lbl = QLabel("确定要永久清空所有剪贴板历史记录和本地图片吗？\n\n注意：此操作仅清理剪贴板历史。快捷短语请右键删除。\n此操作不可恢复！")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        confirm_btn = QPushButton("确定清除")
        confirm_btn.setObjectName("ConfirmBtn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addStretch()
        
        c_layout.addWidget(title_lbl)
        c_layout.addWidget(msg_lbl)
        c_layout.addStretch()
        c_layout.addLayout(btn_layout)
        
        layout.addWidget(self.container)

    def accept(self):
        self.result_btn = True
        super().accept()

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme = theme
        self.anim = QPropertyAnimation(self, b"position")
        self.anim.setDuration(200)
        self.stateChanged.connect(self.start_animation)

    def showEvent(self, event):
        self._position = 21 if self.isChecked() else 3
        super().showEvent(event)

    @pyqtProperty(float)
    def position(self):
        return getattr(self, '_position', 3)

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def start_animation(self, state):
        self.anim.stop()
        self.anim.setStartValue(self.position)
        self.anim.setEndValue(21 if self.isChecked() else 3)
        self.anim.start()
        
    def update_theme(self, theme):
        self.theme = theme
        self.update()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.theme == "dark":
            bg_off = QColor("#45475a")
            bg_on = QColor("#cba6f7")
            thumb = QColor("#cdd6f4")
        else:
            bg_off = QColor("#ccd0da")
            bg_on = QColor("#1e66f5")
            thumb = QColor("#ffffff")
            
        p.setBrush(bg_on if self.isChecked() else bg_off)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 11, 11)
        
        p.setBrush(thumb)
        pos = getattr(self, '_position', 21 if self.isChecked() else 3)
        # 将绘制的圆微调使其垂直居中
        p.drawEllipse(int(pos), 3, 16, 16)
        p.end()

class CustomSaveConfirmDialog(QDialog):
    def __init__(self, title, text, theme="light", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.theme = theme
        self.result_action = "cancel" # save, discard, cancel
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # 标题
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        container_layout.addWidget(title_lbl)
        
        # 提示内容
        desc_lbl = QLabel(text)
        desc_lbl.setFont(QFont("Microsoft YaHei", 10))
        desc_lbl.setWordWrap(True)
        container_layout.addWidget(desc_lbl)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.on_cancel)
        
        self.btn_discard = QPushButton("不保存")
        self.btn_discard.setObjectName("DiscardBtn")
        self.btn_discard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discard.clicked.connect(self.on_discard)
        
        self.btn_save = QPushButton("保存")
        self.btn_save.setObjectName("SaveBtn")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.on_save)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_discard)
        btn_layout.addWidget(self.btn_save)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # 阴影
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(0, 0, 0, 80 if theme == "light" else 150))
        # shadow.setOffset(0, 4)
        # self.container.setGraphicsEffect(shadow)
        
        self.update_theme(theme)
        
    def on_save(self):
        self.result_action = "save"
        self.accept()
        
    def on_discard(self):
        self.result_action = "discard"
        self.accept()
        
    def on_cancel(self):
        self.result_action = "cancel"
        self.reject()

    def update_theme(self, theme=None):
        if theme:
            self.theme = theme
            
        if self.theme == "dark":
            bg = "#1e1e2e"
            text = "#cdd6f4"
            border = "#313244"
            btn_bg = "#313244"
            btn_hover = "#45475a"
            primary = "#89b4fa"
            primary_hover = "#b4befe"
            danger = "#f38ba8"
            danger_hover = "#f5c2e7"
        else:
            bg = "#ffffff"
            text = "#1f2937"
            border = "#e5e7eb"
            btn_bg = "#f3f4f6"
            btn_hover = "#e5e7eb"
            primary = "#2563eb"
            primary_hover = "#1d4ed8"
            danger = "#ef4444"
            danger_hover = "#dc2626"
            
        self.setStyleSheet(f"""
            #Container {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel {{
                color: {text};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 16px;
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                font-weight: bold;
            }}
            #CancelBtn {{
                background-color: transparent;
                color: {text};
                border: 1px solid {border};
            }}
            #CancelBtn:hover {{
                background-color: {btn_hover};
            }}
            #DiscardBtn {{
                background-color: {danger};
                color: #ffffff;
                border: none;
            }}
            #DiscardBtn:hover {{
                background-color: {danger_hover};
            }}
            #SaveBtn {{
                background-color: {primary};
                color: #ffffff;
                border: none;
            }}
            #SaveBtn:hover {{
                background-color: {primary_hover};
            }}
        """)

class SettingsWidget(QWidget):
    def __init__(self, main_app=None):
        super().__init__(None)
        self.main_app = main_app
        self.has_unsaved_changes = False
        self._last_theme = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 15, 5, 0)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)
        
        self.icon_labels = []
        
        # 头部
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 10, 15)
        
        header_layout.addSpacing(28) # Balance the close button on the right
        header_title = QLabel(f"偏好设置 (v{APP_VERSION})")
        header_title.setObjectName("HeaderTitle")
        header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        header_title.setMinimumHeight(30)
        header_layout.addWidget(header_title, 1)
        
        self.close_btn = QPushButton("")
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(self.request_close)
        header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; } QWidget#ScrollWidget { background-color: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setObjectName("ScrollWidget")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 14, 0) # Account for scrollbar width (14px)
        scroll_layout.setSpacing(16)
        
        # 设置组1：通用
        group1 = QWidget()
        group1.setObjectName("SettingGroup")
        g1_layout = QVBoxLayout(group1)
        g1_layout.setContentsMargins(20, 16, 20, 16)
        g1_layout.setSpacing(16)
        
        # Row 1: Days
        row1 = QVBoxLayout()
        row1.setSpacing(4)
        
        row1_top = QHBoxLayout()
        icon1 = QLabel(); self.icon_labels.append((icon1, SVG_CLOCK)); icon1.setPixmap(create_svg_icon(SVG_CLOCK, 18).pixmap(18, 18))
        lbl1 = QLabel("历史保留天数")
        lbl1.setProperty("class", "SettingLabel")
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 3650)
        self.days_spin.setValue(self.main_app.config.get("retain_days", 7) if self.main_app else 7)
        self.days_spin.valueChanged.connect(self.mark_unsaved)
        self.days_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.days_spin.setFixedWidth(80)
        self.days_spin.setFixedHeight(30)
        
        row1_top.addWidget(icon1)
        row1_top.addSpacing(5)
        row1_top.addWidget(lbl1)
        row1_top.addStretch()
        row1_top.addWidget(self.days_spin)
        row1_top.addWidget(QLabel("天"))
        
        row1_bottom = QHBoxLayout()
        days_tip_lbl = QLabel("超过天数的记录将自动清理")
        days_tip_lbl.setProperty("class", "TipLabel")
        days_tip_lbl.setWordWrap(True)
        row1_bottom.addSpacing(23)
        row1_bottom.addWidget(days_tip_lbl)
        
        row1.addLayout(row1_top)
        row1.addLayout(row1_bottom)
        g1_layout.addLayout(row1)
        
        # Divider
        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        g1_layout.addWidget(div)
        
        # Row 2: Hotkey
        row2 = QVBoxLayout()
        row2.setSpacing(4)
        
        row2_top = QHBoxLayout()
        icon2 = QLabel(); self.icon_labels.append((icon2, SVG_KEYBOARD)); icon2.setPixmap(create_svg_icon(SVG_KEYBOARD, 18).pixmap(18, 18))
        lbl2 = QLabel("唤出快捷键")
        lbl2.setProperty("class", "SettingLabel")
        self.hotkey_input = HotkeyInput(self, self.main_app.config.get("hotkey", "alt+v") if self.main_app else "alt+v")
        self.hotkey_input.textChanged.connect(self.mark_unsaved)
        self.hotkey_input.setFixedWidth(130)
        self.hotkey_input.setFixedHeight(30)
        
        row2_top.addWidget(icon2)
        row2_top.addSpacing(5)
        row2_top.addWidget(lbl2)
        row2_top.addStretch()
        row2_top.addWidget(self.hotkey_input)
        
        row2_bottom = QHBoxLayout()
        tip_lbl = QLabel("点击上方输入框，直接按键盘录制，例如 Ctrl+C")
        tip_lbl.setProperty("class", "TipLabel")
        tip_lbl.setWordWrap(True)
        row2_bottom.addSpacing(23)
        row2_bottom.addWidget(tip_lbl)
        
        row2.addLayout(row2_top)
        row2.addLayout(row2_bottom)
        g1_layout.addLayout(row2)
        
        # Row 3: Enable Image
        div2 = QFrame()
        div2.setObjectName("Divider")
        div2.setFixedHeight(1)
        g1_layout.addWidget(div2)
        
        row3 = QVBoxLayout()
        row3.setSpacing(4)
        
        row3_top = QHBoxLayout()
        icon_img = QLabel(); self.icon_labels.append((icon_img, SVG_IMAGE)); icon_img.setPixmap(create_svg_icon(SVG_IMAGE, 18, '#a6adc8').pixmap(18, 18))
        theme = self.main_app.get_current_effective_theme() if self.main_app else "light"
        lbl_img = QLabel("记录剪贴板图片")
        lbl_img.setProperty("class", "SettingLabel")
        self.img_checkbox = ToggleSwitch(theme=theme)
        self.img_checkbox.setChecked(self.main_app.config.get("enable_image", True) if self.main_app else True)
        self.img_checkbox.stateChanged.connect(self.mark_unsaved)
        
        row3_top.addWidget(icon_img)
        row3_top.addSpacing(5)
        row3_top.addWidget(lbl_img)
        row3_top.addStretch()
        row3_top.addWidget(self.img_checkbox)
        
        row3_bottom = QHBoxLayout()
        tip_lbl_img = QLabel("开启后可保存截图和图片文件")
        tip_lbl_img.setProperty("class", "TipLabel")
        tip_lbl_img.setWordWrap(True)
        row3_bottom.addSpacing(23)
        row3_bottom.addWidget(tip_lbl_img)
        
        row3.addLayout(row3_top)
        row3.addLayout(row3_bottom)
        g1_layout.addLayout(row3)
        
        # Row 5: Hide After Copy
        div4 = QFrame()
        div4.setObjectName("Divider")
        div4.setFixedHeight(1)
        g1_layout.addWidget(div4)
        
        row5 = QVBoxLayout()
        row5.setSpacing(4)
        
        row5_top = QHBoxLayout()
        icon_hide = QLabel(); self.icon_labels.append((icon_hide, SVG_EYE_OFF)); icon_hide.setPixmap(create_svg_icon(SVG_EYE_OFF, 18).pixmap(18, 18))
        lbl_hide = QLabel("复制后隐藏窗口")
        lbl_hide.setProperty("class", "SettingLabel")
        self.hide_checkbox = ToggleSwitch(theme=theme)
        self.hide_checkbox.setChecked(main_app.config.get("hide_after_copy", True) if main_app else True)
        self.hide_checkbox.stateChanged.connect(self.mark_unsaved)
        
        row5_top.addWidget(icon_hide)
        row5_top.addSpacing(5)
        row5_top.addWidget(lbl_hide)
        row5_top.addStretch()
        row5_top.addWidget(self.hide_checkbox)
        
        row5_bottom = QHBoxLayout()
        tip_lbl_hide = QLabel("开启后，点击列表项复制后将自动隐藏窗口")
        tip_lbl_hide.setProperty("class", "TipLabel")
        tip_lbl_hide.setWordWrap(True)
        row5_bottom.addSpacing(23)
        row5_bottom.addWidget(tip_lbl_hide)
        
        row5.addLayout(row5_top)
        row5.addLayout(row5_bottom)
        g1_layout.addLayout(row5)
        
        # Row 6: Auto Start
        div5 = QFrame()
        div5.setObjectName("Divider")
        div5.setFixedHeight(1)
        g1_layout.addWidget(div5)
        
        row6 = QVBoxLayout()
        row6.setSpacing(4)
        
        row6_top = QHBoxLayout()
        icon_power = QLabel(); self.icon_labels.append((icon_power, SVG_POWER)); icon_power.setPixmap(create_svg_icon(SVG_POWER, 18).pixmap(18, 18))
        lbl_power = QLabel("开机自动启动")
        lbl_power.setProperty("class", "SettingLabel")
        self.autostart_checkbox = ToggleSwitch(theme=theme)
        self.autostart_checkbox.setChecked(check_autostart())
        self.autostart_checkbox.stateChanged.connect(self.mark_unsaved)
        
        row6_top.addWidget(icon_power)
        row6_top.addSpacing(5)
        row6_top.addWidget(lbl_power)
        row6_top.addStretch()
        row6_top.addWidget(self.autostart_checkbox)
        
        row6_bottom = QHBoxLayout()
        tip_lbl_power = QLabel("跟随电脑系统自动运行，随时记录剪贴板")
        tip_lbl_power.setProperty("class", "TipLabel")
        tip_lbl_power.setWordWrap(True)
        row6_bottom.addSpacing(23)
        row6_bottom.addWidget(tip_lbl_power)
        
        row6.addLayout(row6_top)
        row6.addLayout(row6_bottom)
        g1_layout.addLayout(row6)
        
        scroll_layout.addWidget(group1)
        
        # 设置组2：数据清理
        group2 = QWidget()
        group2.setObjectName("SettingGroup")
        g2_layout = QVBoxLayout(group2)
        g2_layout.setContentsMargins(20, 16, 20, 16)
        g2_layout.setSpacing(10)
        
        g2_top = QHBoxLayout()
        icon3 = QLabel(); self.icon_labels.append((icon3, SVG_DATABASE)); icon3.setPixmap(create_svg_icon(SVG_DATABASE, 18).pixmap(18, 18))
        lbl3 = QLabel("清理历史数据")
        lbl3.setProperty("class", "SettingLabel")
        
        self.clear_btn = QPushButton("立即清除")
        self.clear_btn.setObjectName("ClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clear_btn.setFixedHeight(30)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        
        g2_top.addWidget(icon3)
        g2_top.addSpacing(5)
        g2_top.addWidget(lbl3)
        g2_top.addStretch()
        g2_top.addWidget(self.clear_btn)
        
        g2_bottom = QHBoxLayout()
        clear_tip_lbl = QLabel("永久清空本地所有剪贴板记录（快捷短语请右键删除）")
        clear_tip_lbl.setProperty("class", "TipLabel")
        clear_tip_lbl.setWordWrap(True)
        g2_bottom.addSpacing(23)
        g2_bottom.addWidget(clear_tip_lbl)
        
        g2_layout.addLayout(g2_top)
        g2_layout.addLayout(g2_bottom)
        
        scroll_layout.addWidget(group2)
        
        # 设置组3：快捷短语
        group3 = QWidget()
        group3.setObjectName("SettingGroup")
        g3_layout = QVBoxLayout(group3)
        g3_layout.setContentsMargins(20, 16, 20, 16)
        g3_layout.setSpacing(10)
        
        g3_top = QHBoxLayout()
        icon4 = QLabel(); icon4.setPixmap(create_svg_icon(SVG_FILE, 18).pixmap(18, 18))
        lbl4 = QLabel("快捷短语数据")
        lbl4.setProperty("class", "SettingLabel")
        
        self.import_btn = QPushButton("导入数据")
        self.import_btn.setObjectName("ImportBtn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.import_btn.setFixedHeight(30)
        self.import_btn.clicked.connect(self.on_import_clicked)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setObjectName("ExportBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.export_btn.setFixedHeight(30)
        self.export_btn.clicked.connect(self.on_export_clicked)
        
        g3_top.addWidget(icon4)
        g3_top.addSpacing(5)
        g3_top.addWidget(lbl4)
        g3_top.addStretch()
        g3_top.addWidget(self.import_btn)
        g3_top.addWidget(self.export_btn)
        
        g3_bottom = QHBoxLayout()
        snippet_tip_lbl = QLabel("备份或恢复你的快捷短语分类和数据")
        snippet_tip_lbl.setProperty("class", "TipLabel")
        snippet_tip_lbl.setWordWrap(True)
        g3_bottom.addSpacing(23)
        g3_bottom.addWidget(snippet_tip_lbl)
        
        g3_layout.addLayout(g3_top)
        g3_layout.addLayout(g3_bottom)
        
        scroll_layout.addWidget(group3)
        scroll_layout.addStretch()
        
        self.scroll_area.setWidget(scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_btn.setFixedHeight(34)
        self.save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        self.update_theme(theme)

    def update_theme(self, theme):
        self.img_checkbox.update_theme(theme)
        self.hide_checkbox.update_theme(theme)
        self.autostart_checkbox.update_theme(theme)
        if hasattr(self, 'close_btn'):
            self.close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff" if theme == "dark" else "#1e1e2e"))
            
        self.apply_style(theme)

    def save_settings(self):
        if not self.main_app:
            return
        
        self.main_app.config["retain_days"] = self.days_spin.value()
        self.main_app.config["enable_image"] = self.img_checkbox.isChecked()
        self.main_app.config["hide_after_copy"] = self.hide_checkbox.isChecked()
        set_autostart(self.autostart_checkbox.isChecked())
        
        new_hotkey = self.hotkey_input.text()
        if new_hotkey != self.main_app.config.get("hotkey"):
            self.main_app.register_hotkey(new_hotkey)
            
        self.main_app.save_config()
        self.main_app.apply_theme()
        self.main_app.clean_expired_history()
        self.main_app.update_list()
        self.main_app.save_history()

        self.has_unsaved_changes = False

        # 显示保存成功的提示 (可以加个动画或临时改文字)
        if hasattr(self, 'save_btn'):
            self.save_btn.setText("✔ 保存成功")
            QTimer.singleShot(1500, lambda: self.save_btn.setText("保存设置"))

    def mark_unsaved(self, *args):
        self.has_unsaved_changes = True

    def request_close(self):
        if not self.main_app:
            return
        if self.has_unsaved_changes:
            dialog = CustomSaveConfirmDialog(
                "保存提示", "您有未保存的设置，是否要保存并关闭？", 
                theme=self.main_app.get_current_effective_theme(), 
                parent=self
            )
            dialog.exec()
            if dialog.result_action == "save":
                self.save_settings()
                self.main_app.hide()
            elif dialog.result_action == "discard":
                self.has_unsaved_changes = False
                self.main_app.hide()
        else:
            self.main_app.hide()

    def apply_style(self, theme):
        if theme == self._last_theme:
            return
        self._last_theme = theme
        
        if theme == "dark":
            bg = "#1e1e2e"
            card = "#242634"
            text = "#cdd6f4"
            border = "#313244"
            input_bg = "#181825"
            primary = "#89b4fa"
            primary_hover = "#b4befe"
            tip_color = "#6c7086"
            red_bg = "rgba(243, 139, 168, 0.15)"
            red_text = "#f38ba8"
            icon_color = "#cdd6f4"
            text_muted = "#a6adc8"
        else:
            bg = "#f2f4f8"
            card = "#ffffff"
            text = "#4c4f69"
            border = "#dce0e8"
            input_bg = "#e6e9ef"
            primary = "#1e66f5"
            primary_hover = "#7287fd"
            tip_color = "#9ca0b0"
            red_bg = "rgba(210, 15, 57, 0.1)"
            red_text = "#d20f39"
            icon_color = "#1f2937"
            text_muted = "#7c7f93"
            
        # 更新图标颜色
        if hasattr(self, 'icon_labels'):
            for lbl, svg in self.icon_labels:
                lbl.setPixmap(create_svg_icon(svg, 18, icon_color).pixmap(18, 18))
            
        self.setStyleSheet(f'''
            #Container {{
                background-color: transparent;
                border: none;
            }}
            #HeaderTitle {{
                font-size: 18px;
                font-weight: bold;
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            #SettingGroup {{
                background-color: {card};
                border: none;
                border-radius: 12px;
            }}
            .SettingLabel {{
                font-size: 14px;
                color: {text};
                font-weight: 500;
                font-family: 'Microsoft YaHei';
            }}
            .TipLabel {{
                font-size: 12px;
                color: {tip_color};
                font-family: 'Microsoft YaHei';
                margin-top: 2px;
            }}
            QLabel {{
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            #Divider {{
                background-color: {border};
                border: none;
            }}
            QSpinBox, QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                color: {text};
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                font-weight: bold;
            }}
            QSpinBox:focus, QLineEdit:focus {{
                border: 1px solid {primary};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 0px; 
            }}
            QComboBox {{
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                color: {text};
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                font-weight: bold;
            }}
            QComboBox:focus {{
                border: 1px solid {primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card};
                border: 1px solid {border};
                border-radius: 6px;
                color: {text};
                selection-background-color: rgba(137, 180, 250, 0.15);
                outline: none;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 4px 16px;
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                font-weight: bold;
            }}
            #SaveBtn {{
                background-color: {primary};
                color: #ffffff;
                border: none;
                padding: 6px 16px;
            }}
            #SaveBtn:hover {{
                background-color: {primary_hover};
            }}
            #CloseButton {{
                background-color: transparent;
                border: none;
                padding: 0px;
                border-radius: 4px;
            }}
            #CloseButton:hover {{
                background-color: rgba(137, 180, 250, 0.2);
            }}
            #CancelBtn, #ImportBtn, #ExportBtn {{
                background-color: {card};
                color: {text};
                border: 1px solid {border};
            }}
            #CancelBtn:hover, #ImportBtn:hover, #ExportBtn:hover {{
                background-color: {input_bg};
            }}
            #ClearBtn {{
                background-color: {red_bg};
                color: {red_text};
                border: none;
                padding: 4px 16px;
            }}
            #ClearBtn:hover {{
                background-color: {red_text};
                color: #ffffff;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {primary if theme == "dark" else border};
                min-height: 30px;
                border-radius: 4px;
                margin: 4px 4px 4px 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {primary_hover if theme == "dark" else primary};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {text_muted};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: transparent;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        ''')

    def get_days(self):
        return self.days_spin.value()

    def get_hotkey(self):
        return self.hotkey_input.text().strip().lower()

    def get_enable_img(self):
        return self.img_checkbox.isChecked()

    def get_hide_after_copy(self):
        return self.hide_checkbox.isChecked()

    def get_autostart(self):
        return self.autostart_checkbox.isChecked()

    def on_clear_clicked(self):
        theme = "light"
        if self.main_app:
            theme = self.main_app.get_current_effective_theme()
            
        dialog = ConfirmDialog(self, theme)
        # 将弹窗居中显示在屏幕中央（而不是相对于父窗口，防止在某些多层嵌套下无法点击）
        screen = QApplication.primaryScreen().geometry()
        dialog.move(screen.center() - dialog.rect().center())
        dialog.exec()
        
        if dialog.result_btn:
            if self.main_app:
                self.main_app.clear_history()
            self.clear_btn.setText("✔ 已彻底清除")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.clear_btn.setText("立即清除"))

    def on_import_clicked(self):
        from PyQt6.QtWidgets import QFileDialog
        if not self.main_app or not hasattr(self.main_app, 'snippets_ui'):
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入快捷短语数据", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            manager = self.main_app.snippets_ui.manager
            if manager.import_data(file_path):
                self.main_app.snippets_ui.load_tree()
                self.toast = Toast("快捷短语导入成功！", parent=self, theme=self.main_app.get_current_effective_theme())
                self.toast.show_toast()
            else:
                self.toast = Toast("导入失败，文件格式可能不正确", parent=self, theme=self.main_app.get_current_effective_theme(), is_error=True)
                self.toast.show_toast()

    def on_export_clicked(self):
        from PyQt6.QtWidgets import QFileDialog
        if not self.main_app or not hasattr(self.main_app, 'snippets_ui'):
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出快捷短语数据", "snippets_backup.json", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            manager = self.main_app.snippets_ui.manager
            if manager.export_data(file_path):
                self.toast = Toast("快捷短语导出成功！", parent=self, theme=self.main_app.get_current_effective_theme())
                self.toast.show_toast()
            else:
                self.toast = Toast("导出数据失败，请检查写入权限", parent=self, theme=self.main_app.get_current_effective_theme(), is_error=True)
                self.toast.show_toast()

class FooterHintWidget(QWidget):
    def __init__(self, theme="light", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.end_state = False  # 是否已显示全部记录（滚动到底/内容不足一屏）
        self.setFixedHeight(20)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.icon_label = QLabel()
        self.icon_label.setPixmap(create_svg_icon(SVG_INFO, 13).pixmap(13, 13))
        
        self.text_label = QLabel()
        self.text_label.setFont(QFont("Microsoft YaHei", 8))
        
        layout.addStretch()
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        self.update_theme(theme)
        
    def set_end_state(self, active):
        """切换"已显示全部记录"状态，改变底部提示文字"""
        if active != self.end_state:
            self.end_state = active
            self.update_theme(self.theme)
        
    def _refresh_text(self):
        if self.end_state:
            self.text_label.setText('已显示全部记录 | 作者: xuzi | <a href="https://github.com/xuzi888/Clipboard" style="color: inherit; text-decoration: none;">GitHub</a>')
        else:
            self.text_label.setText('单击条目可粘贴 | 支持拖拽 | 作者: xuzi | <a href="https://github.com/xuzi888/Clipboard" style="color: inherit; text-decoration: none;">GitHub</a>')
        
        self.text_label.setOpenExternalLinks(True)
        
    def update_theme(self, theme):
        self.theme = theme
        self._refresh_text()
        if theme == "dark":
            self.text_label.setStyleSheet("color: #6c7086;")
        else:
            self.text_label.setStyleSheet("color: #8c8fa1;")
        self.update()
        
    def paintEvent(self, event):
        from PyQt6.QtGui import QLinearGradient, QPen, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制高级渐变分割线（两端透明，中间实色），这是最现代的高级 UI 做法
        gradient = QLinearGradient(0, 0, self.width(), 0)
        if self.theme == "dark":
            color = QColor(255, 255, 255, 30)
        else:
            color = QColor(0, 0, 0, 20)
            
        transparent = QColor(color.red(), color.green(), color.blue(), 0)
        
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.2, color)
        gradient.setColorAt(0.8, color)
        gradient.setColorAt(1.0, transparent)
        
        pen = QPen(QBrush(gradient), 1)
        painter.setPen(pen)
        painter.drawLine(0, 0, self.width(), 0)
        painter.end()


class TutorialDialog(QDialog):
    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)
        self.theme = theme
        self._last_theme = None
        self._page_icons = {} # 使用字典存储，key为索引
        self._loaded_pages = set() # 记录已加载的页面索引
        self.setWindowTitle("使用教程")
        self.setFixedSize(720, 520)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 35, 35, 35)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 头部 Header
        header_widget = QWidget()
        header_widget.setObjectName("HeaderWidget")
        header_widget.setFixedHeight(50)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_title = QLabel("使用教程")
        header_title.setObjectName("HeaderTitle")
        
        close_btn = QPushButton("")
        close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff" if self.theme == "dark" else "#1e1e2e"))
        close_btn.setObjectName("HeaderCloseBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        
        header_layout.addSpacing(30)
        header_layout.addStretch()
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        # 主体区域 (左侧导航 + 右侧内容)
        body_widget = QWidget()
        body_widget.setObjectName("BodyWidget")
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        
        # 左侧导航列表
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        self.nav_list.setFixedWidth(180)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setProperty("class", "NavList")
        
        # 右侧内容堆叠视图
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("ContentStack")
        
        body_layout.addWidget(self.nav_list)
        
        # 分割线 (左右)
        v_line = QFrame()
        v_line.setFixedWidth(1)
        v_line.setObjectName("VLine")
        body_layout.addWidget(v_line)
        
        body_layout.addWidget(self.stacked_widget)
        
        container_layout.addWidget(header_widget)
        
        # 分割线 (上下)
        h_line = QFrame()
        h_line.setFixedHeight(1)
        h_line.setObjectName("HLine")
        container_layout.addWidget(h_line)
        
        container_layout.addWidget(body_widget)
        
        # 定义教程章节
        self.sections = [
            ("基础唤出与粘贴", SVG_KEYBOARD, "基础使用与粘贴",
             "<b>唤出面板：</b>按下 <code>ALT+V</code>（可在设置中修改）即可瞬间呼出历史面板，随时随地触手可及。<br><br>"
             "<b>快速粘贴：</b>呼出面板后，鼠标左键单击任意历史条目，程序会自动将其粘贴到您当前的光标位置（如编辑器、聊天框内）。<br><br>"
             "<b>复制后隐藏：</b>在设置中开启“复制后隐藏窗口”后，单击粘贴条目即可自动收起面板，让操作行云流水。"),
            ("高级悬浮操作", SVG_MORE, "高级悬浮操作",
             "将鼠标悬浮在历史记录上，可看到多种快捷操作按钮：<br><br>"
             "&nbsp;&nbsp;📌 <b>置顶(Pin)：</b>将重要数据置顶，防止在自动清理时被删除。<br><br>"
             "&nbsp;&nbsp;✏️ <b>内联编辑：</b>直接在面板中修改文本剪贴板的内容，支持保存和取消。<br><br>"
             "&nbsp;&nbsp;🔍 <b>查看大图：</b>双击图片条目或点击放大镜图标，即可全屏预览高清大图，并支持鼠标滚轮缩放。<br><br>"
             "&nbsp;&nbsp;▶️ <b>播放视频：</b>点击播放按钮，直接调用内置播放器预览视频文件。<br><br>"
             "&nbsp;&nbsp;📁 <b>打开位置：</b>复制了文件或文件夹后，点击文件夹图标可直达文件所在的本地目录。<br><br>"
             "&nbsp;&nbsp;🗑️ <b>单条删除：</b>点击右侧出现的垃圾桶图标即可删除不需要的数据。"),
            ("超级拖拽", SVG_IMPORT, "超级拖拽",
             "<b>无缝交互：</b>按住任意文本或图片条目向外拖拽，可直接将内容拖入各类编辑器、IDE或输入框中。<br><br>"
             "<b>快捷保存：</b>图片和文件不仅可以拖入聊天框发送，还可以直接拖拽至桌面或任意文件夹，快速保存为本地文件！<br><br>"
             "<b>⚠️ 第三方软件拖拽限制说明：</b><br>"
             "&nbsp;&nbsp;1. <b>部分聊天软件工作台：</b>已完美兼容图片、文件、纯文本和视频的直接拖拽发送。若发现纯文本、图片、视频或文件无法拖拽，是因为部分软件自身禁用了该类型内容的拖拽输入以防排版错乱，请改用点击复制后 <code>Ctrl+V</code> 粘贴。<br>"
             "&nbsp;&nbsp;2. <b>权限拦截：</b>如果拖拽时鼠标变成“禁止符号 🚫”，通常是因为目标软件（如某些游戏、以管理员身份运行的软件）权限比本程序高。请尝试右键以“管理员身份运行”本程序。"),
            ("快捷短语管理", SVG_FOLDER, "快捷短语管理",
             "<b>短语分组：</b>点击左侧导航栏的“快捷短语”进入管理页面，您可以创建不同的分组（如：问候语、代码片段、邮箱地址等）。<br><br>"
             "<b>一键发送：</b>在短语列表中单击即可快速粘贴常用短语，极大提升客服或日常回复的效率。<br><br>"
             "<b>自由编辑：</b>支持对短语进行添加、修改、删除和拖拽排序，打造您的专属素材库。"),
            ("搜索与数据维护", SVG_SEARCH, "搜索与数据维护",
             "<b>智能搜索：</b>面板顶部提供搜索框，输入关键词即可实时过滤出您需要的历史记录或短语。<br><br>"
             "<b>数据存储：</b>所有的历史剪贴板数据和设置均保存在本地，保护您的隐私安全。"),
            ("偏好与高级设置", SVG_SETTINGS, "偏好与高级设置",
             "<b>呼出快捷键：</b>可自定义唤出历史面板的快捷键组合，默认为 <code>ALT+V</code>。<br><br>"
             "<b>保留天数：</b>配置历史数据的自动保留天数（默认7天），到期数据会自动清理。<br><br>"
             "<b>记录图片数据：</b>如果不需要记录图片剪贴板，可以关闭此项以节省本地存储空间。<br><br>"
             "<b>开机自动启动：</b>建议开启此项，确保每次开机都能无缝使用。<br><br>"
             "<b>外观主题：</b>支持“跟随系统”、“亮色模式”与“暗色模式”，也可通过左侧边栏图标一键切换。<br><br>"
             "<b>复制后隐藏窗口：</b>开启后，当您单击粘贴某条记录时，程序面板会自动收起。<br><br>"
             "<b>立即清除：</b>一键彻底清空所有的历史记录数据（置顶条目也会被清除）。<br><br>"
             "<b>数据导入与导出：</b>支持将当前配置与所有数据导出为ZIP包，或从已有ZIP包中恢复，轻松完成数据迁移。"),
            ("常见问题 (FAQ)", SVG_HELP, "常见问题 (FAQ)",
             "<b>Q: 程序的数据和图片缓存存储在哪里？如何备份或迁移？</b><br>"
             "A: 本程序采用纯本地存储设计，绝不上传隐私数据，所有文件均保存在程序运行目录下：<br>"
             "&nbsp;&nbsp;• <b>数据与设置：</b>分别保存在 <code>data.json</code> 和 <code>config.json</code> 文件中。<br>"
             "&nbsp;&nbsp;• <b>图片缓存：</b>只有复制的“纯图片”会缓存至 <code>images/</code> 文件夹。<br>"
             "&nbsp;&nbsp;⚠️ <b>注意：</b>如果您复制的是本地已存在的文件，或在短语中添加了本地文件，程序仅记录它们的“文件路径”，绝不会重复拷贝占用硬盘空间。<br>"
             "&nbsp;&nbsp;💡 <b>备份与迁移：</b>只需将上述两个 JSON 文件和 <code>images/</code> 文件夹整体拷贝到新电脑的程序目录下即可恢复。<i>(注：仅记录路径的本地文件需保证原文件依然存在)</i><br><br>"
             "<b>Q: 为什么按下全局快捷键 <code>Alt+V</code> 无法唤出界面？</b><br>"
             "A: 请检查是否有其他软件（如 QQ、微信或输入法）占用了此快捷键。您可以右键托盘图标进入“偏好设置”，修改为您习惯的其他组合键（如 <code>Ctrl+Shift+C</code>）。<br><br>"
             "<b>Q: 杀毒软件或 Windows Defender 提示风险或报毒？</b><br>"
             "A: 这是因为程序使用了 <code>keyboard</code> 模块进行全局快捷键监听，且由 PyInstaller 打包，部分杀毒软件可能会产生误报。本项目完全开源，您可以自行检查源码，或将程序添加至白名单中放心使用。<br><br>"
             "<b>Q: 如何彻底退出程序？</b><br>"
             "A: 为保证剪贴板监听不中断，点击主界面右上角的关闭按钮默认会隐藏到系统托盘。如需彻底退出，请在右下角系统托盘找到本程序的图标，右键选择“退出”。<br><br>"
             "<b>Q: 复制的图片为什么有时候无法显示？</b><br>"
             "A: 本程序支持绝大多数标准系统剪贴板图片格式。但部分第三方软件（如某些截图工具或游戏内截图）可能使用了私有格式写入剪贴板，导致无法读取。")
        ]
        
        nav_icon_color = "#4c4f69" if theme == "light" else "#a6adc8"
        
        for i, (nav_title, icon_svg, page_title, desc) in enumerate(self.sections):
            # 左侧导航项
            item = QListWidgetItem(f"  {nav_title}")
            item.setIcon(QIcon(create_svg_icon(icon_svg, 16, nav_icon_color).pixmap(16, 16)))
            self.nav_list.addItem(item)
            
            # 添加占位符页面，实际内容在点击时加载
            placeholder = QWidget()
            self.stacked_widget.addWidget(placeholder)
            
        self.nav_list.currentRowChanged.connect(self.load_page)
        
        main_layout.addWidget(self.container)
        
        # 阴影
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(25)
        # shadow.setColor(QColor(0, 0, 0, 150 if theme == "light" else 200))
        # shadow.setOffset(0, 6)
        # self.container.setGraphicsEffect(shadow)
        
        self.apply_style(theme)
        
        # 默认选中第一页
        self.nav_list.setCurrentRow(0)

    def load_page(self, index):
        """延迟加载页面内容"""
        if index in self._loaded_pages:
            self.stacked_widget.setCurrentIndex(index)
            return
            
        nav_title, icon_svg, page_title, desc = self.sections[index]
        
        # 创建真实页面
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 30, 40, 30)
        page_layout.setSpacing(20)
        
        icon_color = "#1e66f5" if self.theme == "light" else "#89b4fa"
        
        # 页面标题
        title_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(create_svg_icon(icon_svg, 28, icon_color).pixmap(28, 28))
        
        p_title = QLabel(page_title)
        p_title.setProperty("class", "PageTitle")
        
        title_layout.addStretch()
        title_layout.addWidget(icon_lbl)
        self._page_icons[index] = (icon_lbl, icon_svg) # 记录引用
        title_layout.addSpacing(10)
        title_layout.addWidget(p_title)
        title_layout.addStretch()
        
        page_layout.addLayout(title_layout)
        
        # 滚动区域描述
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("class", "ContentScroll")
        
        desc_container = QWidget()
        desc_container.setObjectName("DescContainer")
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 10, 10, 10)
        
        p_desc = QLabel(desc)
        p_desc.setProperty("class", "PageDesc")
        p_desc.setWordWrap(True)
        p_desc.setTextFormat(Qt.TextFormat.RichText)
        p_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        desc_layout.addWidget(p_desc)
        
        scroll.setWidget(desc_container)
        page_layout.addWidget(scroll)
        
        # 替换占位符
        old_placeholder = self.stacked_widget.widget(index)
        self.stacked_widget.removeWidget(old_placeholder)
        self.stacked_widget.insertWidget(index, page)
        old_placeholder.deleteLater()
        
        self._loaded_pages.add(index)
        self.stacked_widget.setCurrentIndex(index)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging', False) and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def apply_style(self, theme):
        if theme == self._last_theme:
            return
        self._last_theme = theme
        self.theme = theme
        
        if theme == "dark":
            bg = "#1e1e2e"
            nav_bg = "#181825"
            text = "#cdd6f4"
            text_muted = "#a6adc8"
            border = "#313244"
            accent = "#89b4fa"
            accent_bg = "#313244"
            hover_bg = "#313244"
            icon_color = "#cdd6f4"
            nav_icon_color = "#cdd6f4"
        else:
            bg = "#ffffff"
            nav_bg = "#f8f9fa"
            text = "#1f2937"
            text_muted = "#4b5563"
            border = "#e5e7eb"
            accent = "#2563eb"
            accent_bg = "#eff6ff"
            hover_bg = "#e5e7eb"
            icon_color = "#1f2937"
            nav_icon_color = "#1f2937"
            
        # 更新图标颜色
        if hasattr(self, 'sections'):
            for i in range(len(self.sections)):
                nav_title, icon_svg, page_title, desc = self.sections[i]
                item = self.nav_list.item(i)
                if item:
                    item.setIcon(QIcon(create_svg_icon(icon_svg, 16, nav_icon_color).pixmap(16, 16)))
            
            # 使用预存的引用列表快速更新已加载页面的图标
            for index, (icon_lbl, icon_svg) in self._page_icons.items():
                icon_lbl.setPixmap(create_svg_icon(icon_svg, 28, accent).pixmap(28, 28))

        # 找到关闭按钮并更新图标颜色
        close_btn = self.findChild(QPushButton, "HeaderCloseBtn")
        if close_btn:
            close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, text_muted if theme == "dark" else nav_icon_color))
            close_btn.setStyleSheet(f"""
                #HeaderCloseBtn {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                }}
                #HeaderCloseBtn:hover {{
                    background-color: {border};
                }}
            """)
            
        self.setStyleSheet(f'''
            #Container {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            #HeaderWidget {{
                background-color: {nav_bg};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            #HeaderTitle {{
                font-size: 15px;
                font-weight: bold;
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            #HLine, #VLine {{
                background-color: {border};
            }}
            #BodyWidget {{
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            #NavList {{
                background-color: {nav_bg};
                border: none;
                border-bottom-left-radius: 12px;
                outline: none;
                padding: 15px 10px;
            }}
            #NavList::item {{
                height: 42px;
                border-radius: 8px;
                color: {text_muted};
                font-family: 'Microsoft YaHei';
                font-size: 14px;
                margin-bottom: 4px;
            }}
            #NavList::item:hover {{
                background-color: {hover_bg};
                color: {text};
            }}
            #NavList::item:selected {{
                background-color: {accent_bg};
                color: {accent};
                font-weight: bold;
            }}
            .PageTitle {{
                font-size: 22px;
                font-weight: bold;
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            .PageDesc {{
                font-size: 14px;
                color: {text_muted};
                line-height: 2.0;
                font-family: 'Microsoft YaHei';
            }}
            .PageDesc b {{
                color: {text};
                font-weight: 600;
            }}
            .PageDesc code {{
                background-color: {hover_bg};
                color: {accent};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: Consolas, monospace;
            }}
            .ContentScroll {{
                background-color: transparent;
            }}
            #DescContainer {{
                background-color: transparent;
            }}
            #ContentStack {{
                background-color: {bg};
                border-bottom-right-radius: 12px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {accent if theme == "dark" else border};
                min-height: 30px;
                border-radius: 4px;
                margin: 4px 4px 4px 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {text_muted if theme == "dark" else accent};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {text_muted};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        ''')


class AboutDialog(QDialog):
    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)
        self.theme = theme
        self._last_theme = None
        self.icon_labels = [] # 存储图标引用
        self.setWindowTitle("关于与使用说明")
        self.setFixedSize(420, 640)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. 顶部 Header (包含 Logo 和标题)
        header_widget = QWidget()
        header_widget.setObjectName("HeaderWidget")
        header_widget.setFixedHeight(160) # 稍微增加高度
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 10, 0, 10)
        header_layout.setSpacing(8)

        # 头部右上角关闭按钮
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 10, 0)
        top_bar.addStretch()
        self.close_btn_top = QPushButton("")
        self.close_btn_top.setObjectName("HeaderCloseBtn")
        self.close_btn_top.setFixedSize(30, 30)
        self.close_btn_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn_top.clicked.connect(self.accept)
        top_bar.addWidget(self.close_btn_top)
        header_layout.addLayout(top_bar)
        
        # App Logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if getattr(sys, 'frozen', False):
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
            if not os.path.exists(app_logo_path):
                app_logo_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), '_internal', 'assets', 'app_logo.png')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
            
        if os.path.exists(app_logo_path):
            pix = QPixmap(app_logo_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        header_layout.addWidget(logo_lbl)
        
        app_name = QLabel(APP_NAME)
        app_name.setObjectName("AppName")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(app_name)
        
        version_lbl = QLabel(f"Version {APP_VERSION}")
        version_lbl.setObjectName("VersionLabel")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version_lbl)
        
        layout.addWidget(header_widget)
        
        # 2. 内容滚动区
        scroll_area = QScrollArea()
        scroll_area.setObjectName("ScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(15)
        
        def create_section(title, icon_svg, content_text, is_rich=False):
            card = QFrame()
            card.setObjectName("SectionCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 12, 15, 12)
            card_layout.setSpacing(8)
            
            title_layout = QHBoxLayout()
            icon_lbl = QLabel()
            icon_lbl.setPixmap(create_svg_icon(icon_svg, 16).pixmap(16, 16))
            self.icon_labels.append((icon_lbl, icon_svg))
            
            title_lbl = QLabel(title)
            title_lbl.setProperty("class", "SectionTitle")
            title_layout.addWidget(icon_lbl)
            title_layout.addSpacing(6)
            title_layout.addWidget(title_lbl)
            title_layout.addStretch()
            
            desc_lbl = QLabel(content_text)
            desc_lbl.setProperty("class", "SectionDesc")
            desc_lbl.setWordWrap(True)
            if is_rich:
                desc_lbl.setTextFormat(Qt.TextFormat.RichText)
            
            card_layout.addLayout(title_layout)
            card_layout.addWidget(desc_lbl)
            return card

        # 简介
        content_layout.addWidget(create_section("软件简介", SVG_BOOK, 
            f"极简、高效的全局剪贴板管理器。自动记录图文数据，快捷键一键唤出，释放你的工作效率。"))
            
        # 初衷
        content_layout.addWidget(create_section("开发初衷", SVG_IDEA, 
            "为了打造一款更符合使用习惯、兼具现代化颜值与高效管理（特别是“场景-分组-短语”三级管理）的纯本地剪贴板工具。希望它能帮助大家减少机械的重复劳动。"))
            
        # 声明
        content_layout.addWidget(create_section("使用声明与免责", SVG_SHIELD, 
            "1. <b>合法使用</b>：本软件为免费开源工具，仅供个人学习及办公辅助使用。<br>"
            "2. <b>隐私安全</b>：软件承诺纯本地运行，无任何后台数据上传行为。<br>"
            "3. <b>免责声明</b>：作者不对因使用本软件造成的任何数据丢失或损失承担责任。", True))
            
        # 相关信息卡片
        info_card = QFrame()
        info_card.setObjectName("SectionCard")
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(15, 12, 15, 12)
        
        info_title_layout = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(create_svg_icon(SVG_LINK, 16).pixmap(16, 16))
        self.icon_labels.append((info_icon, SVG_LINK))
        info_title_lbl = QLabel("相关信息")
        info_title_lbl.setProperty("class", "SectionTitle")
        info_title_layout.addWidget(info_icon)
        info_title_layout.addSpacing(6)
        info_title_layout.addWidget(info_title_lbl)
        info_title_layout.addStretch()
        info_card_layout.addLayout(info_title_layout)
        
        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 5, 0, 0)
        info_grid.setSpacing(10)
        
        def add_grid_row(row, key, val, is_link=False):
            k_lbl = QLabel(key)
            k_lbl.setProperty("class", "InfoKey")
            if is_link:
                v_lbl = QLabel(f'<a href="{val}" style="text-decoration:none;">点击访问</a>')
                v_lbl.setOpenExternalLinks(True)
                v_lbl.setProperty("class", "InfoLink")
            else:
                v_lbl = QLabel(val)
                v_lbl.setProperty("class", "InfoVal")
            info_grid.addWidget(k_lbl, row, 0)
            info_grid.addWidget(v_lbl, row, 1)

        add_grid_row(0, "作者", "xuzi")
        add_grid_row(1, "开源地址", "https://github.com/xuzi888/Clipboard", True)
        add_grid_row(2, "程序下载", "https://github.com/xuzi888/Clipboard/releases/tag/%E5%89%AA%E8%B4%B4%E6%9D%BF%E7%AE%A1%E7%90%86%E5%99%A8%E5%AE%89%E8%A3%85%E5%8C%85", True)
        add_grid_row(3, "QQ交流群", "550133641")
        
        info_card_layout.addLayout(info_grid)
        content_layout.addWidget(info_card)
        
        scroll_area.setWidget(content_area)
        layout.addWidget(scroll_area)
        
        # 3. 底部操作区
        footer_widget = QWidget()
        footer_widget.setObjectName("FooterWidget")
        footer_widget.setFixedHeight(60)
        footer_layout = QHBoxLayout(footer_widget)
        
        close_btn = QPushButton("我知道了")
        close_btn.setObjectName("PrimaryBtn")
        close_btn.setFixedSize(120, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        
        footer_layout.addStretch()
        footer_layout.addWidget(close_btn)
        footer_layout.addStretch()
        layout.addWidget(footer_widget)
        
        main_layout.addWidget(self.container)
        
        # 阴影
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(25)
        # shadow.setColor(QColor(0, 0, 0, 150 if theme == "light" else 200))
        # shadow.setOffset(0, 5)
        # self.container.setGraphicsEffect(shadow)
        
        self.apply_style(theme)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging', False) and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def apply_style(self, theme):
        if theme == self._last_theme:
            return
        self._last_theme = theme
        
        if theme == "dark":
            bg = "#1e1e2e"
            header_bg = "#181825"
            card_bg = "#242634"
            text_main = "#cdd6f4"
            text_sub = "#a6adc8"
            accent = "#89b4fa"
            border = "#313244"
            btn_bg = "#313244"
            btn_hover = "#45475a"
        else:
            bg = "#ffffff"
            header_bg = "#f8f9fa"
            card_bg = "#f2f4f8"
            text_main = "#1f2937"
            text_sub = "#6b7280"
            accent = "#2563eb"
            border = "#e5e7eb"
            btn_bg = "#2563eb"
            btn_hover = "#1d4ed8"
            
        # 更新图标颜色
        icon_color = text_main
        if hasattr(self, 'icon_labels'):
            for lbl, svg in self.icon_labels:
                lbl.setPixmap(create_svg_icon(svg, 16, icon_color).pixmap(16, 16))
        
        if hasattr(self, 'close_btn_top'):
            self.close_btn_top.setIcon(create_svg_icon(SVG_CLOSE, 16, text_sub))
            self.close_btn_top.setStyleSheet(f"""
                #HeaderCloseBtn {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                }}
                #HeaderCloseBtn:hover {{
                    background-color: {border};
                }}
            """)
                    
        self.setStyleSheet(f'''
            #Container {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            #HeaderWidget {{
                background-color: {header_bg};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid {border};
            }}
            #AppName {{
                font-size: 18px;
                font-weight: bold;
                color: {text_main};
                font-family: 'Microsoft YaHei';
            }}
            #VersionLabel {{
                font-size: 12px;
                color: {text_sub};
            }}
            #ScrollArea {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {accent if theme == "dark" else border};
                min-height: 30px;
                border-radius: 4px;
                margin: 4px 4px 4px 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {text_main if theme == "dark" else accent};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {text_sub};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            #ContentArea {{
                background: transparent;
            }}
            #SectionCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            .SectionTitle {{
                font-size: 14px;
                font-weight: bold;
                color: {text_main};
            }}
            .SectionDesc {{
                font-size: 13px;
                line-height: 1.5;
                color: {text_sub};
            }}
            .InfoKey {{
                color: {text_sub};
                font-size: 13px;
            }}
            .InfoVal {{
                color: {text_main};
                font-weight: bold;
                font-size: 13px;
            }}
            .InfoLink {{
                color: {accent};
                font-size: 13px;
                font-weight: bold;
            }}
            #FooterWidget {{
                background-color: {header_bg};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top: 1px solid {border};
            }}
            #PrimaryBtn {{
                background-color: {btn_bg};
                color: {"#ffffff" if theme == "light" else text_main};
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }}
            #PrimaryBtn:hover {{
                background-color: {btn_hover};
            }}
        ''')


class EditTextDialog(QDialog):
    def __init__(self, parent=None, text="", theme="light"):
        super().__init__(parent)
        self.setWindowTitle("编辑文本")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_title = QLabel("编辑文本")
        header_title.setObjectName("HeaderTitle")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Text Edit
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setObjectName("TextEdit")
        layout.addWidget(self.text_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setObjectName("SaveBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # Shadow
        # 阴影会导致无边框半透明窗口闪烁或报错，暂时移除
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(0, 0, 0, 150 if theme == "light" else 200))
        # shadow.setOffset(0, 4)
        # self.container.setGraphicsEffect(shadow)
        
        self.apply_style(theme)

    def get_text(self):
        return self.text_edit.toPlainText()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging', False) and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def apply_style(self, theme):
        if theme == "dark":
            bg = "#1e1e2e"
            input_bg = "#313244"
            text = "#cdd6f4"
            border = "#45475a"
            btn_bg = "#313244"
            btn_hover = "#45475a"
            save_bg = "#89b4fa"
            save_text = "#11111b"
            save_hover = "#b4befe"
        else:
            bg = "#f2f4f8"
            input_bg = "#ffffff"
            text = "#4c4f69"
            border = "#dce0e8"
            btn_bg = "#e6e9ef"
            btn_hover = "#ccd0da"
            save_bg = "#1e66f5"
            save_text = "#ffffff"
            save_hover = "#7287fd"
            
        self.setStyleSheet(f'''
            #Container {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            #HeaderTitle {{
                font-size: 16px;
                font-weight: bold;
                color: {text};
                font-family: 'Microsoft YaHei';
            }}
            #TextEdit {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
                font-family: 'Microsoft YaHei';
                font-size: 14px;
            }}
            #CancelBtn {{
                background-color: {btn_bg};
                color: {text};
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-family: 'Microsoft YaHei';
            }}
            #CancelBtn:hover {{ background-color: {btn_hover}; }}
            #SaveBtn {{
                background-color: {save_bg};
                color: {save_text};
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }}
            #SaveBtn:hover {{ background-color: {save_hover}; }}
        ''')


class ImageLabel(QLabel):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pixmap = pixmap
        self.zoom_factor = 1.0
        self.setPixmap(self._pixmap)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._is_panning = False
        self._pan_start = None
        
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle > 0:
            self.zoom_factor *= 1.1
        else:
            self.zoom_factor *= 0.9
        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))
        self._update_pixmap()
        
    def _update_pixmap(self):
        new_w = int(self._pixmap.width() * self.zoom_factor)
        new_h = int(self._pixmap.height() * self.zoom_factor)
        scaled = self._pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._pan_start = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_panning', False) and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._pan_start
            scroll_area = self.parent().parent()
            if hasattr(scroll_area, 'horizontalScrollBar'):
                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
            self._pan_start = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

class ImageViewerDialog(QDialog):
    def __init__(self, image_path=None, pixmap=None, parent=None, theme="light"):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        if pixmap:
            self.original_pixmap = pixmap
        else:
            self.original_pixmap = QPixmap(image_path)
        
        screen = QApplication.primaryScreen().geometry()
        max_w = int(screen.width() * 0.8)
        max_h = int(screen.height() * 0.8)
        
        pm_w, pm_h = self.original_pixmap.width(), self.original_pixmap.height()
        if pm_w > max_w or pm_h > max_h:
            self.initial_pixmap = self.original_pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            self.initial_pixmap = self.original_pixmap
            
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        hint_text = "提示: 滚轮缩放 | 滑动拖拽"
        if image_path:
            file_name = os.path.basename(image_path)
            hint_text += f" | {file_name}"
        hint = QLabel(hint_text)
        hint.setStyleSheet("color: #8c8fa1; font-size: 12px;")
        header_layout.addWidget(hint)
        header_layout.addStretch()
        
        close_btn = QPushButton()
        close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        
        if theme == "dark":
            close_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); border-radius: 14px; }")
        else:
            close_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(0, 0, 0, 0.1); border-radius: 14px; }")
            
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        from PyQt6.QtWidgets import QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.img_label = ImageLabel(self.original_pixmap)
        self.img_label.setPixmap(self.initial_pixmap)
        
        # Calculate initial zoom factor based on the scaling we just did
        if pm_w > max_w or pm_h > max_h:
            self.img_label.zoom_factor = self.initial_pixmap.width() / pm_w
        
        self.scroll_area.setWidget(self.img_label)
        container_layout.addWidget(self.scroll_area)
        
        layout.addWidget(self.container)
        
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(0, 0, 0, 150 if theme == "light" else 200))
        # shadow.setOffset(0, 4)
        # self.container.setGraphicsEffect(shadow)
        
        bg_color = "#1e1e2e" if theme == "dark" else "#f2f4f8"
        border_color = "#45475a" if theme == "dark" else "#dce0e8"
        self.setStyleSheet(f"#Container {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 14px; }}")

        # Set dialog size to fit initial pixmap plus padding
        self.resize(self.initial_pixmap.width() + 60, self.initial_pixmap.height() + 100)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging', False) and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

class ClipboardApp(QMainWindow):
    image_saved_signal = pyqtSignal()

    @pyqtProperty(int)
    def _win_width(self):
        return self.width()

    @_win_width.setter
    def _win_width(self, w):
        self.setFixedWidth(w)

    def __init__(self):
        super().__init__()
        # 启动时先禁用更新，防止布局过程中的闪烁
        self.setUpdatesEnabled(False)
        
        self.image_saved_signal.connect(self.update_list)
        self.clipboard = QApplication.clipboard()
        self.history = []
        self.ignore_change = False
        
        self.init_data_paths()
        
        self.config = {"retain_days": 7, "hotkey": "alt+v", "theme": "light", "enable_image": True} # 默认配置
        self.load_config()
        
        self._is_dragging = False
        self._drag_start_position = None
        self.last_text = ""
        self.last_image_hash = ""
        
        self.init_ui()
        self.init_tray()
        
        self.load_history()
        
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        
        self.hotkey_signal = HotkeySignal()
        self.hotkey_signal.activated.connect(self.toggle_window)
        self.register_hotkey(self.config.get("hotkey", "alt+v"))

        self.on_clipboard_change()
        
        # 初始化完成，恢复更新
        self.setUpdatesEnabled(True)

    def init_data_paths(self):
        import shutil
        if getattr(sys, 'frozen', False):
            # 打包后，数据文件放在 exe 所在目录
            base_path = os.path.dirname(os.path.abspath(sys.executable))
            self.user_data_dir = base_path
            
            self.data_file = os.path.join(self.user_data_dir, "data.json")
            self.config_file = os.path.join(self.user_data_dir, "config.json")
            self.images_dir = os.path.join(self.user_data_dir, "images")
            
            # 为了兼容更新和全新安装，从打包的 _internal 里释放初始模板（如果有）
            internal_dir = getattr(sys, '_MEIPASS', os.path.join(base_path, '_internal'))
            default_data = os.path.join(internal_dir, "data.json")
            default_config = os.path.join(internal_dir, "config.json")
            default_images = os.path.join(internal_dir, "images")
            
            if not os.path.exists(self.data_file) and os.path.exists(default_data):
                try: shutil.copy2(default_data, self.data_file)
                except Exception as e: print(f"释放默认数据文件失败: {e}")
                
            if not os.path.exists(self.config_file) and os.path.exists(default_config):
                try: 
                    shutil.copy2(default_config, self.config_file)
                    # 第一次运行，默认开启开机自启
                    set_autostart(True)
                except Exception as e: print(f"释放默认配置文件失败: {e}")
                
            if not os.path.exists(self.images_dir) and os.path.exists(default_images):
                try: shutil.copytree(default_images, self.images_dir, dirs_exist_ok=True)
                except Exception as e: pass
        else:
            # 开发环境下，放在 main.py 所在目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            self.user_data_dir = base_path
            self.data_file = os.path.join(self.user_data_dir, "data.json")
            self.config_file = os.path.join(self.user_data_dir, "config.json")
            self.images_dir = os.path.join(self.user_data_dir, "images")
            
            if not os.path.exists(self.config_file):
                set_autostart(True)
            
        os.makedirs(self.images_dir, exist_ok=True)

    def register_hotkey(self, hotkey_str):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            if not hotkey_str:
                hotkey_str = "alt+v"
            # suppress=True 阻止按键事件传递给其他程序（如菜单栏焦点）
            keyboard.add_hotkey(hotkey_str, self.hotkey_signal.activated.emit, suppress=True)
            self.config["hotkey"] = hotkey_str
            
            # 更新UI上的文字提示
            if hasattr(self, 'title_label'):
                self.title_label.setText(f"剪贴板历史 ({hotkey_str.upper()})")
            if hasattr(self, 'show_action'):
                self.show_action.setText(f"显示主界面 ({hotkey_str.upper()})")
            if hasattr(self, 'tray_icon'):
                self.tray_icon.setToolTip(f"{APP_NAME} ({hotkey_str.upper()})")
        except Exception as e:
            print(f"快捷键注册失败: {e}")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def switch_tab(self, index, animate=True):
        # 性能优化点 1: 立即切换 UI 状态，给予瞬间反馈
        if self.stacked_widget.currentIndex() == index:
            return
            
        # 如果当前在设置页面，且有未保存更改，则提示保存
        if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
            if getattr(self.settings_widget, 'has_unsaved_changes', False):
                dialog = CustomSaveConfirmDialog(
                    "保存提示", "您有未保存的设置，是否要保存？", 
                    theme=self.get_current_effective_theme(), 
                    parent=self
                )
                dialog.exec()
                
                if dialog.result_action == "save":
                    self.settings_widget.save_settings()
                elif dialog.result_action == "cancel":
                    self._update_nav_btns(self.stacked_widget.currentIndex())
                    return
                else:
                    self.settings_widget.has_unsaved_changes = False

        # 性能优化点 2: 优先切换堆叠窗口，实现“点击即见”
        self.stacked_widget.setCurrentIndex(index)
        self._update_nav_btns(index)
                    
        # 确定目标宽度
        target_width = 470
        if index == 1: target_width = 770
        elif index == 2: target_width = 510
            
        # 性能优化点 3: 极速缩放动画 (120ms)，使用 OutQuint 实现更灵敏的启动感
        if animate and self.width() != target_width:
            if hasattr(self, 'win_anim') and self.win_anim.state() == QPropertyAnimation.State.Running:
                self.win_anim.stop()
            
            self.win_anim = QPropertyAnimation(self, b"_win_width")
            self.win_anim.setDuration(120)
            self.win_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
            self.win_anim.setStartValue(self.width())
            self.win_anim.setEndValue(target_width)
            self.win_anim.start()
        elif not animate:
            self.setFixedWidth(target_width)

    def _update_nav_btns(self, index):
        if index == 0 and hasattr(self, 'btn_nav_clipboard'):
            self.btn_nav_clipboard.setChecked(True)
        elif index == 1 and hasattr(self, 'btn_nav_snippets'):
            self.btn_nav_snippets.setChecked(True)
        elif index == 2 and hasattr(self, 'settings_btn'):
            self.settings_btn.setChecked(True)

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        if getattr(sys, 'frozen', False):
            # PyInstaller 6.x 在 -D 模式下资源可能在 _internal 目录下
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
            if not os.path.exists(app_logo_path):
                # 兼容不同版本的 PyInstaller 目录结构
                app_logo_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), '_internal', 'assets', 'app_logo.png')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
        self.setWindowIcon(QIcon(app_logo_path))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 默认初始为剪贴板历史窗口尺寸
        self.resize(470, 600)
        
        self.central_widget = QWidget()
        self.central_widget.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        self.setCentralWidget(self.central_widget)
        
        # 外层布局，产生留白以显示阴影
        outer_layout = QVBoxLayout(self.central_widget)
        outer_layout.setContentsMargins(25, 25, 25, 25) # 进一步减小阴影留白，让界面物理感更紧凑
        
        # 实际的内容容器
        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        self.container.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        outer_layout.addWidget(self.container)
        
        # 容器内使用水平布局，左侧导航栏，右侧堆叠区域
        main_hbox = QHBoxLayout(self.container)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)
        
        # --- 左侧导航栏 ---
        self.nav_bar = QWidget()
        self.nav_bar.setObjectName("NavBar")
        self.nav_bar.setFixedWidth(75) # 恢复到 75，避免“快捷短语”被遮挡
        nav_layout = QVBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(2, 20, 2, 20)
        nav_layout.setSpacing(10)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        def create_nav_btn(text, obj_name, callback, checkable=False):
            btn = QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setFixedSize(72, 56) # 宽度增加到 72
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setObjectName(obj_name)
            if checkable:
                btn.setCheckable(True)
            
            # 直接连接回调，不再使用 QTimer 延迟，提升响应速度体验
            btn.clicked.connect(callback)
            return btn
            
        self.btn_nav_clipboard = create_nav_btn("剪贴板", "NavBtnClipboard", lambda: self.switch_tab(0), True)
        self.btn_nav_snippets = create_nav_btn("快捷短语", "NavBtnSnippets", lambda: self.switch_tab(1), True)
        
        # 按钮互斥，表示侧边栏的激活状态
        from PyQt6.QtWidgets import QButtonGroup
        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.addButton(self.btn_nav_clipboard, 0)
        self.nav_btn_group.addButton(self.btn_nav_snippets, 1)
        self.btn_nav_clipboard.setChecked(True)
        
        nav_layout.addWidget(self.btn_nav_clipboard)
        nav_layout.addWidget(self.btn_nav_snippets)
        
        nav_layout.addStretch()
        
        self.settings_btn = create_nav_btn("设置", "SettingsButton", lambda: self.switch_tab(2), True)
        self.nav_btn_group.addButton(self.settings_btn, 2)
        
        self.tutorial_btn = create_nav_btn("教程", "TutorialButton", self.open_tutorial)
        self.about_btn = create_nav_btn("关于", "AboutButton", self.open_about)
        self.theme_btn = create_nav_btn("主题", "ThemeButton", self.toggle_theme)
        
        nav_layout.addWidget(self.settings_btn)
        nav_layout.addWidget(self.tutorial_btn)
        nav_layout.addWidget(self.about_btn)
        nav_layout.addWidget(self.theme_btn)
        
        main_hbox.addWidget(self.nav_bar)
        
        # --- 右侧堆叠区域 ---
        self.stacked_widget = QStackedWidget()
        main_hbox.addWidget(self.stacked_widget)
        
        # 1. 剪贴板历史界面
        self.clipboard_widget = QWidget()
        # 不再使用固定宽度，而是通过调整 QStackedWidget 尺寸策略来实现自适应
        # self.clipboard_widget.setFixedWidth(366)
        layout = QVBoxLayout(self.clipboard_widget)
        # 整体减少左右空白，使其更紧凑
        layout.setContentsMargins(5, 15, 0, 0)
        layout.setSpacing(6)
        
        self.stacked_widget.addWidget(self.clipboard_widget)
        
        # 2. 快捷短语界面
        self.snippets_ui = SnippetsUI(self.get_current_effective_theme(), self)
        self.snippets_ui.phrase_clicked.connect(self.on_snippet_phrase_clicked)
        self.stacked_widget.addWidget(self.snippets_ui)
        
        # 3. 设置界面
        self.settings_widget = SettingsWidget(self)
        self.stacked_widget.addWidget(self.settings_widget)
        
        # 以下原剪贴板的控件全部放入 clipboard_widget 的 layout 中
        title_layout = QHBoxLayout()
        # 调整右侧预留空间以适应向内偏移的滚动条
        title_layout.setContentsMargins(0, 0, 8, 0)
        
        self.title_label = QLabel("剪贴板历史 (ALT+V)")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.title_label.setMinimumHeight(30)
        title_layout.addWidget(self.title_label, 1)
        
        close_btn = QPushButton("")
        close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff" if self.get_current_effective_theme() == "dark" else "#1e1e2e"))
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(16, 8, 8, 8)
        search_layout.setSpacing(8)
        
        # 添加搜索图标
        self.search_icon_label = QLabel()
        self.search_icon_label.setPixmap(create_svg_icon(SVG_SEARCH, 16, "#ffffff" if self.get_current_effective_theme() == "dark" else "#1e1e2e").pixmap(16, 16))
        search_layout.addWidget(self.search_icon_label)
        
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("搜索历史记录...")
        self.search_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search_input.textChanged.connect(self.update_list)
        
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("FilterCombo")
        self.filter_combo.addItems(["全部", "文本", "图片", "文件", "文档", "视频", "音频", "文件夹"])
        self.filter_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.filter_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filter_combo.currentIndexChanged.connect(self.update_list)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.filter_combo)
        
        # 将图标和输入框包装在一起
        self.search_container = QWidget()
        self.search_container.setObjectName("SearchContainer")
        self.search_container.setLayout(search_layout)
        
        # 调整右侧预留空间以适应向内偏移的滚动条
        search_wrapper = QHBoxLayout()
        search_wrapper.setContentsMargins(0, 0, 8, 0)
        search_wrapper.addWidget(self.search_container)
        
        layout.addLayout(search_wrapper)
        
        self.list_widget = ClipboardListWidget()
        self.list_widget.setObjectName("ListWidget")
        # 移除列表控件自身的边距和内边距，减少左侧空白
        self.list_widget.setContentsMargins(0, 0, 0, 0)
        self.list_widget.setWordWrap(True)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust) # 恢复自动排版以适应高度变化
        self.list_widget.setFont(QFont("Microsoft YaHei", 10))
        # 为了防止按钮点击时穿透，我们不再使用自带的 itemClicked 信号，而是交给 HistoryItemWidget 处理
        # self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        # 禁用右键菜单
        # self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # self.list_widget.customContextMenuRequested.connect(self.show_item_context_menu)
        
        # 恢复 ScrollPerPixel，因为 ScrollPerItem 会导致底部有巨大的空白缝隙（因为无法切分半个Item）
        # 透明背景下的残影问题已经在上方的 scrollContentsBy 中通过 viewport().update() 彻底解决了
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus) # 彻底禁用焦点，防止出现虚线框
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection) # 彻底禁用选中状态
        
        # 将整个列表和视口的背景强制置为透明，并且禁用任何系统自带的边框
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setFrameShadow(QFrame.Shadow.Plain)
        self.list_widget.setLineWidth(0)
        self.list_widget.viewport().setAutoFillBackground(False)
        self.list_widget.viewport().setStyleSheet("background-color: transparent;")
        
        # 给列表组件整体加一点右边距，留一点呼吸空间给悬浮滚动条
        self.list_widget.setStyleSheet("QListWidget { padding-right: 6px; }")
        
        # 隐藏掉因为禁用焦点或选中导致的系统虚线框绘制
        self.list_widget.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.list_widget.setSpacing(6)
        
        layout.addWidget(self.list_widget)
        
        self.footer_hint = FooterHintWidget(self.get_current_effective_theme(), self)
        
        footer_wrapper = QHBoxLayout()
        footer_wrapper.setContentsMargins(0, 0, 8, 0)
        footer_wrapper.addWidget(self.footer_hint)
        
        layout.addLayout(footer_wrapper)
        
        # 滚动到底/离开底部时切换底部提示文字
        self.list_widget.verticalScrollBar().valueChanged.connect(self._update_footer_end_state)
        
        # 设置整个窗体的焦点策略，防止点击空白处产生焦点边框
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.apply_theme()
        
        # shadow = QGraphicsDropShadowEffect(self.container)
        # shadow.setBlurRadius(15)
        # shadow.setColor(QColor(0, 0, 0, 120))
        # shadow.setOffset(0, 4)
        # self.container.setGraphicsEffect(shadow)
        
        # 初始化正确的 QSizePolicy 状态，启动时不使用动画防止抖动
        self.switch_tab(0, animate=False)
        
        # 居中显示必须在所有布局和尺寸确定后进行
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        # 对于无边框窗口，使用 rect() 获取的尺寸更可靠
        w = self.width()
        h = self.height()
        self.move((screen.width() - w) // 2, (screen.height() - h) // 2)

        # 启动焦点追踪定时器
        self.focus_tracker_timer = QTimer(self)
        self.focus_tracker_timer.timeout.connect(self._track_foreground_window)
        self.focus_tracker_timer.start(200)
        self.previous_hwnd = None

    def _track_foreground_window(self):
        try:
            import win32gui
            current_hwnd = win32gui.GetForegroundWindow()
            if current_hwnd and current_hwnd != int(self.winId()):
                self.previous_hwnd = current_hwnd
        except Exception:
            pass

    def get_current_effective_theme(self):
        if self.config.get("sync_system_theme", False):
            return get_system_theme()
        return self.config.get("theme", "light")

    def toggle_theme(self):
        # 切换主题时，如果设置界面有未保存内容，也提示
        if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
            if getattr(self.settings_widget, 'has_unsaved_changes', False):
                dialog = CustomSaveConfirmDialog(
                    "保存提示", "您有未保存的设置，是否要保存后再切换主题？", 
                    theme=self.get_current_effective_theme(), 
                    parent=self
                )
                dialog.exec()
                
                if dialog.result_action == "save":
                    self.settings_widget.save_settings()
                elif dialog.result_action == "cancel":
                    return
                else:
                    self.settings_widget.has_unsaved_changes = False

        pixmap = self.grab()
        self.overlay = QLabel(self)
        self.overlay.setPixmap(pixmap)
        self.overlay.resize(self.size())
        self.overlay.show()
        
        self.opacity_effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.opacity_effect)
        
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self.overlay.deleteLater)
        
        current = self.get_current_effective_theme()
        new_theme = "light" if current == "dark" else "dark"
        self.config["sync_system_theme"] = False
        self.config["theme"] = new_theme
        self.save_config()
        self.apply_theme()
        self.update_list()
        
        # 更新设置页面的下拉框
        if hasattr(self, 'settings_widget') and hasattr(self.settings_widget, 'theme_combo'):
            self.settings_widget.theme_combo.setCurrentIndex(2 if new_theme == "dark" else 1)
        
        self.animation.start()

    def apply_theme(self, force=False):
        theme = self.get_current_effective_theme()
        if not force and getattr(self, '_last_applied_theme', None) == theme:
            return
        self._last_applied_theme = theme
        
        self.update_tray_menu_style()
        
        if hasattr(self, 'footer_hint'):
            self.footer_hint.update_theme(theme)
            
        if hasattr(self, 'snippets_ui'):
            self.snippets_ui.update_theme(theme)
            
        if hasattr(self, 'settings_widget'):
            self.settings_widget.update_theme(theme)
                
        if theme == "dark":
            self.tutorial_btn.setIcon(create_svg_icon(SVG_BOOK, 24, "#ffffff"))
            self.about_btn.setIcon(create_svg_icon(SVG_INFO, 24, "#ffffff"))
            self.settings_btn.setIcon(create_svg_icon(SVG_SETTINGS_BTN, 24, "#ffffff"))
            self.search_icon_label.setPixmap(create_svg_icon(SVG_SEARCH, 16, "#ffffff").pixmap(16, 16))
            
            if hasattr(self, 'btn_nav_clipboard'):
                self.btn_nav_clipboard.setIcon(create_svg_icon(SVG_CLIPBOARD, 24, "#ffffff", "#89b4fa"))
                self.btn_nav_snippets.setIcon(create_svg_icon(SVG_SNIPPETS, 24, "#ffffff", "#89b4fa"))
                self.settings_btn.setIcon(create_svg_icon(SVG_SETTINGS_BTN, 24, "#ffffff"))
                self.tutorial_btn.setIcon(create_svg_icon(SVG_BOOK, 24, "#ffffff"))
                self.about_btn.setIcon(create_svg_icon(SVG_INFO, 24, "#ffffff"))
                if hasattr(self, 'theme_btn'): self.theme_btn.setIcon(create_svg_icon(SVG_SUN, 24, "#ffffff"))
            
            # 找到关闭按钮并更新图标颜色（如果可以的话）
            close_btn = self.findChild(QPushButton, "CloseButton")
            if close_btn:
                close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff"))
                
            self.setStyleSheet("""
                * {
                    outline: 0px;
                }
                #MainContainer {
                    background-color: #1e1e2e;
                    border-radius: 12px;
                    border: 1px solid #313244;
                }
                #TitleLabel {
                    color: #cdd6f4;
                    padding: 5px;
                }
                #FooterLabel {
                    color: #6c7086;
                    padding-top: 5px;
                }
                #NavBar {
                    background-color: #181825;
                    border-top-left-radius: 12px;
                    border-bottom-left-radius: 12px;
                    border-right: 1px solid #11111b;
                }
                #NavBtnClipboard, #NavBtnSnippets, #ThemeButton, #TutorialButton, #AboutButton, #SettingsButton {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 4px;
                    margin: 0px;
                    font-size: 11px;
                }
                #CloseButton {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    border-radius: 6px;
                    margin: 0px;
                }
                #NavBtnClipboard:hover, #NavBtnSnippets:hover, #ThemeButton:hover, #TutorialButton:hover, #AboutButton:hover, #SettingsButton:hover {
                    background-color: #45475a;
                    border: 1px solid transparent;
                    padding: 4px;
                    margin: 0px;
                }
                #NavBtnClipboard:checked, #NavBtnSnippets:checked, #SettingsButton:checked {
                    background-color: #313244;
                    color: #89b4fa;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 4px;
                    margin: 0px;
                }
                #NavBtnClipboard:pressed, #NavBtnSnippets:pressed, #ThemeButton:pressed, #TutorialButton:pressed, #AboutButton:pressed, #SettingsButton:pressed {
                    background-color: #313244;
                    border: 1px solid transparent;
                    padding: 4px;
                }
                #CloseButton:hover {
                    background-color: #f38ba8;
                }
                #SearchContainer {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 8px;
                }
                #SearchContainer:focus-within {
                    border: 1px solid #89b4fa;
                    background-color: #313244;
                }
                #SearchInput {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    padding: 0px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei';
                }
                #FilterCombo {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    border-left: 1px solid #45475a;
                    padding: 4px 8px;
                    padding-right: 20px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei';
                    border-radius: 0px;
                }
                #FilterCombo:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                #FilterCombo::drop-down {
                    border: none;
                    width: 0px;
                }
                #FilterCombo::down-arrow {
                    image: none;
                }
                #FilterCombo QAbstractItemView {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    color: #cdd6f4;
                    selection-background-color: rgba(137, 180, 250, 0.15);
                    outline: none;
                }
                #ListWidget {
                    border: none;
                    background-color: transparent;
                    outline: none;
                    padding: 0px;
                    padding-right: 10px;
                    margin: 0px;
                }
                QListWidget {
                    border: 0px;
                    outline: 0px;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 14px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(255, 255, 255, 0.2);
                    min-height: 40px;
                    border-radius: 3px;
                    margin: 4px 4px 4px 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(255, 255, 255, 0.4);
                }
                QScrollBar::handle:vertical:pressed {
                    background: rgba(255, 255, 255, 0.6);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: transparent;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                #ListWidget::item {
                    border: 0px;
                    outline: 0px;
                    border-bottom: none;
                }
                #ListWidget::item:focus {
                    border: 0px;
                    outline: 0px;
                    border-bottom: none;
                }
                QListWidget::item {
                    background-color: transparent;
                    color: transparent;
                    border-radius: 8px;
                    margin: 0px;
                    border: none;
                    outline: none;
                }
                QListWidget::item:focus {
                    border: none;
                    outline: none;
                    background-color: transparent;
                }
                QListWidget::item:hover {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item:selected {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
            """)
        else:
            self.tutorial_btn.setIcon(create_svg_icon(SVG_BOOK, 24, "#1e1e2e"))
            self.about_btn.setIcon(create_svg_icon(SVG_INFO, 24, "#1e1e2e"))
            self.settings_btn.setIcon(create_svg_icon(SVG_SETTINGS_BTN, 24, "#1e1e2e"))
            self.search_icon_label.setPixmap(create_svg_icon(SVG_SEARCH, 16, "#1e1e2e").pixmap(16, 16))
            
            if hasattr(self, 'btn_nav_clipboard'):
                self.btn_nav_clipboard.setIcon(create_svg_icon(SVG_CLIPBOARD, 24, "#1e1e2e", "#1e66f5"))
                self.btn_nav_snippets.setIcon(create_svg_icon(SVG_SNIPPETS, 24, "#1e1e2e", "#1e66f5"))
                self.settings_btn.setIcon(create_svg_icon(SVG_SETTINGS_BTN, 24, "#1e1e2e"))
                self.tutorial_btn.setIcon(create_svg_icon(SVG_BOOK, 24, "#1e1e2e"))
                self.about_btn.setIcon(create_svg_icon(SVG_INFO, 24, "#1e1e2e"))
                if hasattr(self, 'theme_btn'): self.theme_btn.setIcon(create_svg_icon(SVG_MOON, 24, "#1e1e2e"))
            
            # 找到关闭按钮并更新图标颜色
            close_btn = self.findChild(QPushButton, "CloseButton")
            if close_btn:
                close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#1e1e2e"))
                
            self.setStyleSheet("""
                * {
                    outline: 0px;
                }
                #MainContainer {
                    background-color: #eff1f5;
                    border-radius: 12px;
                    border: 1px solid #ccd0da;
                }
                #TitleLabel {
                    color: #4c4f69;
                    padding: 5px;
                }
                #FooterLabel {
                    color: #8c8fa1;
                    padding-top: 5px;
                }
                #NavBar {
                    background-color: #dce0e8;
                    border-top-left-radius: 12px;
                    border-bottom-left-radius: 12px;
                    border-right: 1px solid #bcc0cc;
                }
                #NavBtnClipboard, #NavBtnSnippets, #ThemeButton, #TutorialButton, #AboutButton, #SettingsButton {
                    background-color: transparent;
                    color: #4c4f69;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 4px;
                    margin: 0px;
                    font-size: 11px;
                }
                #CloseButton {
                    background-color: transparent;
                    color: #4c4f69;
                    border: none;
                    border-radius: 6px;
                    margin: 0px;
                }
                #NavBtnClipboard:hover, #NavBtnSnippets:hover, #ThemeButton:hover, #TutorialButton:hover, #AboutButton:hover, #SettingsButton:hover {
                    background-color: #ccd0da;
                    border: 1px solid transparent;
                    padding: 4px;
                    margin: 0px;
                }
                #NavBtnClipboard:checked, #NavBtnSnippets:checked, #SettingsButton:checked {
                    background-color: #ccd0da;
                    color: #4c4f69;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 4px;
                    margin: 0px;
                }
                #NavBtnClipboard:pressed, #NavBtnSnippets:pressed, #ThemeButton:pressed, #TutorialButton:pressed, #AboutButton:pressed, #SettingsButton:pressed {
                    background-color: #ccd0da;
                    border: 1px solid transparent;
                    padding: 4px;
                }
                #CloseButton:hover {
                    background-color: #f38ba8;
                }
                #SearchContainer {
                    background-color: #eff1f5;
                    border: 1px solid #ccd0da;
                    border-radius: 8px;
                }
                #SearchContainer:focus-within {
                    border: 1px solid #1e66f5;
                    background-color: #ffffff;
                }
                #SearchInput {
                    background-color: transparent;
                    color: #4c4f69;
                    border: none;
                    padding: 0px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei';
                }
                #FilterCombo {
                    background-color: transparent;
                    color: #4c4f69;
                    border: none;
                    border-left: 1px solid #ccd0da;
                    padding: 4px 8px;
                    padding-right: 20px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei';
                    border-radius: 0px;
                }
                #FilterCombo:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                }
                #FilterCombo::drop-down {
                    border: none;
                    width: 0px;
                }
                #FilterCombo::down-arrow {
                    image: none;
                }
                #FilterCombo QAbstractItemView {
                    background-color: #eff1f5;
                    border: 1px solid #ccd0da;
                    border-radius: 4px;
                    color: #4c4f69;
                    selection-background-color: rgba(30, 102, 245, 0.15);
                    outline: none;
                }
                #ListWidget {
                    border: none;
                    background-color: transparent;
                    outline: none;
                    padding: 0px;
                    padding-right: 10px;
                    margin: 0px;
                }
                QListWidget {
                    border: 0px;
                    outline: 0px;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 14px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(0, 0, 0, 0.2);
                    min-height: 40px;
                    border-radius: 3px;
                    margin: 4px 4px 4px 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(0, 0, 0, 0.35);
                }
                QScrollBar::handle:vertical:pressed {
                    background: rgba(0, 0, 0, 0.5);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: transparent;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                #ListWidget::item {
                    border: 0px;
                    outline: 0px;
                    border-bottom: none;
                }
                #ListWidget::item:focus {
                    border: 0px;
                    outline: 0px;
                    border-bottom: none;
                }
                QListWidget::item {
                    background-color: transparent;
                    color: transparent;
                    border-radius: 8px;
                    margin: 0px;
                    border: none;
                    outline: none;
                }
                QListWidget::item:focus {
                    border: none;
                    outline: none;
                    background-color: transparent;
                }
                QListWidget::item:hover {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item:selected {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
            """)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # 尝试根据主题生成合适的托盘图标颜色
        # 大部分Windows任务栏是深色，所以默认用浅色图标
        icon_color = "#ffffff" if self.get_current_effective_theme() == "dark" else "#1e1e2e"
        
        # 兼容 PyInstaller 打包后的路径
        if getattr(sys, 'frozen', False):
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
            if not os.path.exists(app_logo_path):
                app_logo_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), '_internal', 'assets', 'app_logo.png')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            app_logo_path = os.path.join(base_path, 'assets', 'app_logo.png')
            
        icon = QIcon(app_logo_path)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(f"{APP_NAME} (ALT+V)")
        
        tray_menu = QMenu()
        self.show_action = QAction("显示主界面 (ALT+V)", self)
        self.show_action.setIcon(icon)
        self.show_action.triggered.connect(self.show_window)
        
        clipboard_action = QAction("剪贴板", self)
        clipboard_action.setIcon(create_svg_icon(SVG_CLIPBOARD, 16, icon_color))
        clipboard_action.triggered.connect(lambda: [self.switch_tab(0), self.show_window()])
        
        snippets_action = QAction("快捷短语", self)
        snippets_action.setIcon(create_svg_icon(SVG_SNIPPETS, 16, icon_color))
        snippets_action.triggered.connect(lambda: [self.switch_tab(1), self.show_window()])
        
        settings_action = QAction("设置", self)
        settings_action.setIcon(create_svg_icon(SVG_SETTINGS_BTN, 16, icon_color))
        settings_action.triggered.connect(self.open_settings)
        
        clear_action = QAction("清空历史", self)
        clear_action.setIcon(create_svg_icon(SVG_TRASH, 16, "#f38ba8" if self.get_current_effective_theme() == "dark" else "#d20f39"))
        clear_action.triggered.connect(self.confirm_and_clear_history)
        
        quit_action = QAction("退出", self)
        quit_action.setIcon(create_svg_icon(SVG_POWER, 16, icon_color))
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(self.show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(clipboard_action)
        tray_menu.addAction(snippets_action)
        tray_menu.addSeparator()
        tray_menu.addAction(settings_action)
        tray_menu.addAction(clear_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
        self.update_tray_menu_style()

    def update_tray_menu_style(self):
        if not hasattr(self, 'tray_icon'): return
        menu = self.tray_icon.contextMenu()
        if not menu: return
        
        theme = self.get_current_effective_theme()
        is_dark = theme == "dark"
        
        # Update icons
        icon_color = "#ffffff" if is_dark else "#1e1e2e"
        actions = menu.actions()
        if len(actions) >= 9:
            # show_action keeps app_logo
            actions[2].setIcon(create_svg_icon(SVG_CLIPBOARD, 16, icon_color)) # clipboard
            actions[3].setIcon(create_svg_icon(SVG_SNIPPETS, 16, icon_color)) # snippets
            actions[5].setIcon(create_svg_icon(SVG_SETTINGS_BTN, 16, icon_color)) # settings
            actions[6].setIcon(create_svg_icon(SVG_TRASH, 16, "#f38ba8" if is_dark else "#d20f39")) # clear
            actions[8].setIcon(create_svg_icon(SVG_POWER, 16, icon_color)) # quit
            
        # Update style
        if is_dark:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    border: 1px solid #313244;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 32px 8px 12px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #313244;
                    color: #89b4fa;
                }
                QMenu::separator {
                    height: 1px;
                    background: #313244;
                    margin: 6px 12px;
                }
                QMenu::icon {
                    padding-left: 10px;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 32px 8px 12px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #eff1f5;
                    color: #1e66f5;
                }
                QMenu::separator {
                    height: 1px;
                    background: #dce0e8;
                    margin: 6px 12px;
                }
                QMenu::icon {
                    padding-left: 10px;
                }
            """)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()

    def open_settings(self):
        self.show_window()
        self.settings_btn.setChecked(True)
        self.switch_tab(2)

    def open_tutorial(self):
        # 提示未保存的设置
        if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
            if getattr(self.settings_widget, 'has_unsaved_changes', False):
                dialog = CustomSaveConfirmDialog(
                    "保存提示", "您有未保存的设置，是否要保存？", 
                    theme=self.get_current_effective_theme(), 
                    parent=self
                )
                dialog.exec()
                
                if dialog.result_action == "save":
                    self.settings_widget.save_settings()
                elif dialog.result_action == "cancel":
                    return
                else:
                    self.settings_widget.has_unsaved_changes = False

        self._settings_open = True
        
        # 延迟初始化，如果存在则瞬间显示
        if not hasattr(self, '_tutorial_dialog'):
            self._tutorial_dialog = TutorialDialog(None, self.get_current_effective_theme())
        else:
            # apply_style 内部已做防抖，这里直接调用即可，只有主题变化时才会真正执行重绘
            self._tutorial_dialog.apply_style(self.get_current_effective_theme())
            
        self._tutorial_dialog.move(self.geometry().center() - self._tutorial_dialog.rect().center())
        self._tutorial_dialog.exec()
        self._settings_open = False

    def open_about(self):
        # 提示未保存的设置
        if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
            if getattr(self.settings_widget, 'has_unsaved_changes', False):
                dialog = CustomSaveConfirmDialog(
                    "保存提示", "您有未保存的设置，是否要保存？", 
                    theme=self.get_current_effective_theme(), 
                    parent=self
                )
                dialog.exec()
                
                if dialog.result_action == "save":
                    self.settings_widget.save_settings()
                elif dialog.result_action == "cancel":
                    return
                else:
                    self.settings_widget.has_unsaved_changes = False
                    
        self._settings_open = True
        
        # 延迟初始化，如果存在则瞬间显示
        if not hasattr(self, '_about_dialog'):
            self._about_dialog = AboutDialog(None, self.get_current_effective_theme())
        else:
            # apply_style 内部已做防抖，这里直接调用即可，只有主题变化时才会真正执行重绘
            self._about_dialog.apply_style(self.get_current_effective_theme())
            
        self._about_dialog.move(self.geometry().center() - self._about_dialog.rect().center())
        self._about_dialog.exec()
        self._settings_open = False

    def focusOutEvent(self, event):
        # 如果设置对话框在打开状态，不要因为失去焦点隐藏主窗口
        if getattr(self, '_settings_open', False):
            return
            
        if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
            if getattr(self.settings_widget, 'has_unsaved_changes', False):
                # 如果有未保存设置，不自动隐藏
                return
                
        self.hide()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()

    def clean_expired_history(self):
        current_time = time.time()
        retain_seconds = self.config.get("retain_days", 7) * 86400
        valid_history = []
        for item in self.history:
            if isinstance(item, dict):
                # 如果是置顶项，或者在保留天数之内，则保留
                if item.get("pinned", False) or (current_time - item.get("timestamp", 0) <= retain_seconds):
                    valid_history.append(item)
                else:
                    if item.get("type") == "image":
                        try:
                            if not item.get("is_external"):
                                os.remove(item.get("path"))
                        except:
                            pass
            else:
                valid_history.append({"text": item, "timestamp": current_time})
        self.history = valid_history

    def get_image_hash(self, image):
        try:
            # 统一转换为 Format_RGB32 保证哈希值在不同环境和重启后一致
            if image.format() != QImage.Format.Format_RGB32:
                image = image.convertToFormat(QImage.Format.Format_RGB32)
            
            # 极速 Hash 算法：直接读取图片的原始内存数据进行哈希，速度是保存 PNG 再哈希的 10 倍以上
            ptr = image.constBits()
            ptr.setsize(image.sizeInBytes())
            return hashlib.md5(ptr.asstring()).hexdigest()
        except Exception:
            # 兜底算法
            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            return hashlib.md5(ba.data()).hexdigest()

    def on_clipboard_change(self):
        if self.ignore_change:
            self.ignore_change = False
            return
            
        mime_data = self.clipboard.mimeData()
        enable_image = self.config.get("enable_image", True)
        
        # 优先判断是否包含文件URL（比如在文件管理器或者微信中复制了图片文件）
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                # 检查是否全部是图片文件
                all_images = True
                first_url = urls[0].toLocalFile()
                
                for url in urls:
                    local_file = url.toLocalFile()
                    if not local_file or not local_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                        all_images = False
                        break
                        
                # 如果复制的是单张图片，走图片逻辑
                if all_images and len(urls) == 1 and first_url:
                    if not enable_image:
                        return # 关闭图片时，直接拦截图片URL的复制
                    image = QImage(first_url)
                    if not image.isNull():
                        img_hash = self.get_image_hash(image)
                        if img_hash == self.last_image_hash:
                            return
                        self.last_image_hash = img_hash
                        self.last_text = ""
                        
                        self._handle_image_copy(image, img_hash, local_file_path=first_url)
                        return
                    else:
                        # 尝试读取文件内容来构造图片，防止因为特殊字符导致读取失败
                        with open(first_url, "rb") as f:
                            image.loadFromData(f.read())
                        if not image.isNull():
                            img_hash = self.get_image_hash(image)
                            if img_hash == self.last_image_hash:
                                return
                            self.last_image_hash = img_hash
                            self.last_text = ""
                            self._handle_image_copy(image, img_hash, local_file_path=first_url)
                            return
                            
                # 否则，智能分类【文件/文件夹/文档/视频/音频】来记录
                file_paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
                if file_paths:
                    file_hash = hashlib.md5("".join(file_paths).encode()).hexdigest()
                    if file_hash == self.last_image_hash: # 复用last_image_hash字段来去重
                        return
                    self.last_image_hash = file_hash
                    self.last_text = ""
                    
                    # 智能识别文件类型
                    file_type = "file"
                    if len(file_paths) == 1:
                        path = file_paths[0]
                        if os.path.isdir(path):
                            file_type = "folder"
                        else:
                            ext = path.lower().split('.')[-1] if '.' in path else ""
                            if ext in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'txt', 'md', 'csv']:
                                file_type = "document"
                            elif ext in ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm']:
                                file_type = "video"
                            elif ext in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']:
                                file_type = "audio"
                    else:
                        # 如果是多个文件混合，统一称为 file
                        file_type = "file"
                    
                    existing_item = None
                    for h in self.history:
                        if isinstance(h, dict) and h.get("type") in ["file", "document", "video", "audio", "folder"] and h.get("hash") == file_hash:
                            existing_item = h
                            break
                            
                    if existing_item:
                        self.history.remove(existing_item)
                        existing_item["timestamp"] = time.time()
                        existing_item["type"] = file_type
                        existing_item["urls"] = file_paths
                        self.history.insert(0, existing_item)
                    else:
                        self.history.insert(0, {
                            "type": file_type,
                            "urls": file_paths,
                            "hash": file_hash,
                            "timestamp": time.time()
                        })
                    
                    if len(self.history) > 50:
                        removed = self.history.pop()
                        if isinstance(removed, dict) and removed.get("type") == "image":
                            try:
                                if not removed.get("is_external"):
                                    os.remove(removed.get("path"))
                            except:
                                pass
                                
                    self.clean_expired_history()
                    self.update_list()
                    self.save_history()
                    return

        # 如果没有URL，再判断是否是纯图片数据（比如截图）
        if enable_image and mime_data.hasImage():
            image = self.clipboard.image()
            if not image.isNull():
                img_hash = self.get_image_hash(image)
                if img_hash == self.last_image_hash:
                    return
                self.last_image_hash = img_hash
                self.last_text = ""
                
                self._handle_image_copy(image, img_hash)
                return
        elif enable_image:
            # 某些情况下（比如从浏览器或者某些特殊软件复制），图片数据存在但 hasImage() 返回 False
            formats = mime_data.formats()
            if "image/png" in formats or "image/jpeg" in formats or "image/bmp" in formats:
                image = self.clipboard.image()
                if not image.isNull():
                    img_hash = self.get_image_hash(image)
                    if img_hash == self.last_image_hash:
                        return
                    self.last_image_hash = img_hash
                    self.last_text = ""
                    self._handle_image_copy(image, img_hash)
                    return

        # 如果没有URL，也没有直接Image，但在某些特殊情况下（例如微信某些版本），
        # 复制图片可能只有特定的MIME格式，我们可以尝试从其他格式里强行提取
        if enable_image and mime_data.hasFormat("application/x-qt-image"):
            image = self.clipboard.image()
            if not image.isNull():
                img_hash = self.get_image_hash(image)
                if img_hash == self.last_image_hash:
                    return
                self.last_image_hash = img_hash
                self.last_text = ""
                self._handle_image_copy(image, img_hash)
                return

        if mime_data.hasText():
            text = mime_data.text().strip()
            # 如果是自己的提示文本，直接丢弃，防止被记录到剪贴板历史
            if text == "单击条目可粘贴 | 支持拖拽文本与图片" or text == "点击条目即可自动粘贴并置于顶部":
                return
                
            # 如果文字就是个本地图片路径（比如某些软件里复制会以file:///协议传递文本）
            is_image_url = text.startswith("file:///") and text.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))
            
            if is_image_url:
                if enable_image:
                    from urllib.parse import unquote
                    # 去除file:///前缀并处理URL编码
                    local_path = unquote(text[8:])
                    # 处理Windows路径（将前置的/C:/...转换为C:/...）
                    if local_path.startswith('/') and ':' in local_path:
                        local_path = local_path[1:]
                        
                    if os.path.exists(local_path):
                        image = QImage(local_path)
                        if not image.isNull():
                            img_hash = self.get_image_hash(image)
                            if img_hash == self.last_image_hash:
                                return
                            self.last_image_hash = img_hash
                            self.last_text = ""
                            self._handle_image_copy(image, img_hash, local_file_path=local_path)
                            return
                else:
                    # 如果关闭了图片保存，直接丢弃这个 file:/// 图片路径，不保存为文本
                    return

            if text and text != self.last_text:
                self.last_text = text
                self.last_image_hash = ""
                
                existing_item = None
                for h in self.history:
                    if (h.get("text") if isinstance(h, dict) else h) == text:
                        existing_item = h
                        break
                
                if existing_item:
                    self.history.remove(existing_item)
                    if isinstance(existing_item, dict):
                        existing_item["timestamp"] = time.time()
                        if "type" not in existing_item:
                            existing_item["type"] = "text"
                        self.history.insert(0, existing_item)
                    else:
                        self.history.insert(0, {"type": "text", "text": text, "timestamp": time.time()})
                else:
                    self.history.insert(0, {"type": "text", "text": text, "timestamp": time.time()})
                
                if len(self.history) > 50:
                    removed = self.history.pop()
                    if isinstance(removed, dict) and removed.get("type") == "image":
                        try:
                            if not removed.get("is_external"):
                                os.remove(removed.get("path"))
                        except:
                            pass
                    
                self.clean_expired_history()
                self.update_list()
                self.save_history()

    def _handle_image_copy(self, image, img_hash, local_file_path=None):
        existing_item = None
        for h in self.history:
            if isinstance(h, dict) and h.get("type") == "image" and h.get("hash") == img_hash:
                existing_item = h
                break
                
        if existing_item:
            self.history.remove(existing_item)
            existing_item["timestamp"] = time.time()
            self.history.insert(0, existing_item)
        else:
            img_dir = self.images_dir
            
            if local_file_path and os.path.exists(local_file_path):
                self.history.insert(0, {
                    "type": "image",
                    "path": local_file_path,
                    "hash": img_hash,
                    "timestamp": time.time(),
                    "is_external": True
                })
                # 由于不需要保存，直接刷新
                self.image_saved_signal.emit()
            else:
                img_name = f"img_{img_hash}.png"
                img_path = os.path.join(img_dir, img_name)
                
                # 使用多线程异步保存图片，彻底消除复制大图片时的 UI 卡顿延迟
                import threading
                img_copy = image.copy()
                def save_and_update(p, img, app_instance):
                    img.save(p, "PNG")
                    # 保存完成后，通过信号安全地通知主线程刷新UI，确保图片显示出来
                    app_instance.image_saved_signal.emit()
                    
                threading.Thread(target=save_and_update, args=(img_path, img_copy, self), daemon=True).start()
                
                self.history.insert(0, {
                    "type": "image",
                    "path": img_path,
                    "hash": img_hash,
                    "timestamp": time.time()
                })
                
            if len(self.history) > 50:
                removed = self.history.pop()
                if isinstance(removed, dict) and removed.get("type") == "image":
                    try:
                        if not removed.get("is_external"):
                            os.remove(removed.get("path"))
                    except:
                        pass
        
        self.clean_expired_history()
        self.update_list()
        self.save_history()

    def load_history(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    
                    if isinstance(file_data, list):
                        self.history = file_data
                    elif isinstance(file_data, dict):
                        self.history = file_data.get("history", [])
                        
                    self.clean_expired_history()
                    self.update_list()
                    if self.history:
                        first_item = self.history[0]
                        if isinstance(first_item, dict) and first_item.get("type") in ["image", "file", "document", "video", "audio", "folder"]:
                            self.last_image_hash = first_item.get("hash", "")
                        else:
                            self.last_text = first_item.get("text", "") if isinstance(first_item, dict) else first_item
        except Exception as e:
            print(f"读取历史失败: {e}")

    def save_history(self):
        try:
            data = {"history": self.history}
            
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        if isinstance(file_data, dict) and "snippets" in file_data:
                            data["snippets"] = file_data["snippets"]
                except Exception:
                    pass
                    
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")

    def sync_item_data_to_history(self, updated_data):
        # 查找并在内存历史记录中同步更新（用于编辑文本和置顶状态保存）
        for item in self.history:
            if item.get("timestamp") == updated_data.get("timestamp") and item.get("type") == updated_data.get("type"):
                if "text" in updated_data:
                    item["text"] = updated_data["text"]
                if "pinned" in updated_data:
                    item["pinned"] = updated_data["pinned"]
                break
        self.save_history()

    def update_list(self):
        # 记录当前滚动条位置
        scroll_val = self.list_widget.verticalScrollBar().value()
        
        self.list_widget.clear()
        # 清除任何可能存在的虚线边框或选择残影
        self.list_widget.clearSelection()
        self.list_widget.clearFocus()
        
        search_query = self.search_input.text().strip().lower()
        filter_type = self.filter_combo.currentText()
        
        # 定义一个内部组件用于显示复杂的列表项
        class HistoryItemWidget(QWidget):
            def __init__(self, app_instance, list_item, text=None, image_path=None, pixmap=None, video_path=None, timestamp=0, is_pinned=False, theme="light"):
                super().__init__()
                self.app_instance = app_instance
                self.list_item = list_item
                self.video_path = video_path
                self.is_pinned = is_pinned
                self.theme = theme
                self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                
                self.setObjectName("HistoryCard")
                self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                self.setProperty("hover", False)
                self.setProperty("pinned", is_pinned)
                
                card_bg = "#313244" if theme == "dark" else "#ffffff"
                card_hover = "#45475a" if theme == "dark" else "#f2f4f8"
                border_color = "#313244" if theme == "dark" else "#e6e9ef"
                hover_border = "#89b4fa" if theme == "dark" else "#b4befe"
                
                self.setStyleSheet(f"""
                    #HistoryCard {{ background-color: {card_bg}; border-radius: 10px; border: 1px solid {border_color}; }}
                    #HistoryCard[hover="true"] {{ background-color: {card_hover}; border: 1px solid {hover_border}; }}
                    #HistoryCard[pinned="true"] {{ border: 1px solid {'#fab387' if theme == 'dark' else '#df8e1d'}; }}
                    #HistoryCard[hover="true"][pinned="true"] {{ border: 1px solid {'#fab387' if theme == 'dark' else '#df8e1d'}; background-color: {card_hover}; }}
                """)
                
                layout = QVBoxLayout(self)
                layout.setContentsMargins(16, 12, 12, 12)
                layout.setSpacing(8)
                
                header_layout = QHBoxLayout()
                header_layout.setSpacing(8)
                
                type_icon = QLabel()
                type_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                if video_path:
                    icon_color = "#f9e2af" if theme == "dark" else "#df8e1d"
                    type_icon.setPixmap(create_svg_icon(SVG_PLAY, 14, icon_color).pixmap(14, 14))
                    type_text = "视频"
                elif image_path or (pixmap and not text):
                    icon_color = "#a6e3a1" if theme == "dark" else "#40a02b"
                    type_icon.setPixmap(create_svg_icon(SVG_IMAGE, 14, icon_color).pixmap(14, 14))
                    type_text = "图片"
                elif text and ("[文件]" in text or "[文档]" in text or "[音频]" in text):
                    icon_color = "#cba6f7" if theme == "dark" else "#8839ef"
                    type_icon.setPixmap(create_svg_icon(SVG_FILE, 14, icon_color).pixmap(14, 14))
                    if "[文件]" in text: type_text = "文件"
                    elif "[文档]" in text: type_text = "文档"
                    elif "[音频]" in text: type_text = "音频"
                    else: type_text = "文件"
                elif text and "[文件夹]" in text:
                    icon_color = "#f38ba8" if theme == "dark" else "#d20f39"
                    type_icon.setPixmap(create_svg_icon(SVG_FOLDER, 14, icon_color).pixmap(14, 14))
                    type_text = "文件夹"
                elif text and "[视频]" in text:
                    icon_color = "#f9e2af" if theme == "dark" else "#df8e1d"
                    type_icon.setPixmap(create_svg_icon(SVG_PLAY, 14, icon_color).pixmap(14, 14))
                    type_text = "视频"
                elif text and "[图片]" in text:
                    icon_color = "#a6e3a1" if theme == "dark" else "#40a02b"
                    type_icon.setPixmap(create_svg_icon(SVG_IMAGE, 14, icon_color).pixmap(14, 14))
                    type_text = "图片"
                else:
                    icon_color = "#89b4fa" if theme == "dark" else "#1e66f5"
                    type_icon.setPixmap(create_svg_icon(SVG_BOOK, 14, icon_color).pixmap(14, 14))
                    type_text = "文本"
                
                type_label = QLabel(type_text)
                type_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                type_label.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                if theme == "dark":
                    type_label.setStyleSheet("color: #cdd6f4;")
                else:
                    type_label.setStyleSheet("color: #4c4f69;")
                
                time_lbl = QLabel(time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp)))
                time_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                time_lbl.setFont(QFont("Microsoft YaHei", 9))
                if theme == "dark":
                    time_lbl.setStyleSheet("color: #a6adc8;")
                else:
                    time_lbl.setStyleSheet("color: #9ca0b0;")
                    
                type_layout = QHBoxLayout()
                type_layout.setSpacing(2)
                type_layout.setContentsMargins(0, 0, 0, 0)
                type_icon.setFixedSize(14, 14)
                type_layout.addWidget(type_icon)
                type_layout.addWidget(type_label)
                
                header_layout.addLayout(type_layout)
                header_layout.addWidget(time_lbl)
                header_layout.addStretch()
                header_layout.setContentsMargins(0, 0, 4, 0)
                
                # 隐藏/显示的按钮组
                self.btn_container = QWidget()
                self.btn_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                btn_layout = QHBoxLayout(self.btn_container)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                btn_layout.setSpacing(4)
                
                item_data = list_item.data(Qt.ItemDataRole.UserRole)
                file_path_to_open = None
                if isinstance(item_data, dict):
                    i_type = item_data.get("type", "text")
                    if i_type == "image" and item_data.get("path"):
                        file_path_to_open = item_data.get("path")
                    elif i_type in ["file", "document", "video", "audio", "folder"] and item_data.get("urls"):
                        file_path_to_open = item_data.get("urls")[0]
                        if file_path_to_open.startswith("file:///"):
                            from PyQt6.QtCore import QUrl
                            file_path_to_open = QUrl(file_path_to_open).toLocalFile()
                
                # 置顶按钮
                self.pin_btn = QPushButton()
                pin_icon = SVG_PIN_FILLED if is_pinned else SVG_PIN
                # 如果是实心图钉，给它加上高亮颜色
                pin_color = "#df8e1d" if is_pinned else ("#a6adc8" if theme == "dark" else "#8c8fa1")
                self.pin_btn.setIcon(create_svg_icon(pin_icon, 14, pin_color))
                self.pin_btn.setFixedSize(24, 24)
                self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.pin_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                self.pin_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(250, 179, 135, 0.2)' if theme == 'dark' else 'rgba(223, 142, 29, 0.1)'}; }}")
                self.pin_btn.clicked.connect(self.on_pin_clicked)
                btn_layout.addWidget(self.pin_btn)
                
                # 编辑按钮 (仅对文本可用)
                is_text_item = False
                if isinstance(item_data, dict):
                    i_type = item_data.get("type")
                    if i_type == "text" or (not i_type and "text" in item_data):
                        is_text_item = True
                elif isinstance(item_data, str):
                    is_text_item = True
                    
                if is_text_item:
                    self.edit_btn = QPushButton()
                    btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    self.edit_btn.setIcon(create_svg_icon(SVG_EDIT, 14, btn_color))
                    self.edit_btn.setFixedSize(24, 24)
                    self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    self.edit_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(137, 180, 250, 0.2)' if theme == 'dark' else 'rgba(30, 102, 245, 0.1)'}; }}")
                    self.edit_btn.clicked.connect(self.on_edit_clicked)
                    btn_layout.addWidget(self.edit_btn)

                if video_path and os.path.exists(video_path):
                    play_btn = QPushButton()
                    btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    play_btn.setIcon(create_svg_icon(SVG_PLAY, 14, btn_color))
                    play_btn.setFixedSize(24, 24)
                    play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    play_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    play_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(166, 227, 161, 0.2)' if theme == 'dark' else 'rgba(64, 160, 43, 0.1)'}; }}")
                    play_btn.clicked.connect(self.on_play_clicked)
                    btn_layout.addWidget(play_btn)

                if (image_path and os.path.exists(image_path)) or pixmap:
                    self.image_path_to_view = image_path
                    self.pixmap_to_view = pixmap
                    view_btn = QPushButton()
                    btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    view_btn.setIcon(create_svg_icon(SVG_ZOOM, 14, btn_color))
                    view_btn.setFixedSize(24, 24)
                    view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    view_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    
                    hover_color = 'rgba(137, 180, 250, 0.2)' if theme == 'dark' else 'rgba(30, 102, 245, 0.1)'
                    view_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {hover_color}; }}")
                    
                    self.image_path_to_view = image_path
                    view_btn.clicked.connect(self.on_view_image_clicked)
                    btn_layout.addWidget(view_btn)

                if file_path_to_open and os.path.exists(file_path_to_open):
                    open_btn = QPushButton()
                    btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    open_btn.setIcon(create_svg_icon(SVG_FOLDER, 14, btn_color))
                    open_btn.setFixedSize(24, 24)
                    open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    open_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    open_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(137, 180, 250, 0.2)' if theme == 'dark' else 'rgba(30, 102, 245, 0.1)'}; }}")
                    self.file_path_to_open = file_path_to_open
                    open_btn.clicked.connect(self.on_open_location_clicked)
                    btn_layout.addWidget(open_btn)
                
                del_btn = QPushButton()
                del_btn.setIcon(create_svg_icon(SVG_TRASH, 14, "#f38ba8" if theme == "dark" else "#d20f39"))
                del_btn.setFixedSize(24, 24)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                del_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(243, 139, 168, 0.2)' if theme == 'dark' else 'rgba(210, 15, 57, 0.1)'}; }}")
                del_btn.clicked.connect(self.on_delete_clicked)
                btn_layout.addWidget(del_btn)
                
                self.btn_container.hide() # 默认隐藏，悬浮显示
                sp = self.btn_container.sizePolicy()
                sp.setRetainSizeWhenHidden(True)
                self.btn_container.setSizePolicy(sp)
                header_layout.addWidget(self.btn_container)
                layout.addLayout(header_layout)
                    
                if image_path or pixmap:
                    class ClickableLabel(QLabel):
                        singleClicked = pyqtSignal()
                        doubleClicked = pyqtSignal()
                        def mouseReleaseEvent(self, event):
                            if event.button() == Qt.MouseButton.LeftButton:
                                self.singleClicked.emit()
                                event.accept()
                            else:
                                super().mouseReleaseEvent(event)
                        def mouseDoubleClickEvent(self, event):
                            if event.button() == Qt.MouseButton.LeftButton:
                                self.doubleClicked.emit()
                                event.accept()
                            else:
                                super().mouseDoubleClickEvent(event)

                    img_lbl = ClickableLabel()
                    img_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                    
                    pm = pixmap if pixmap else QPixmap(image_path) if os.path.exists(image_path) else None
                    if pm:
                        scaled = pm.scaled(304, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        target = QPixmap(scaled.size())
                        target.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(target)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        path = QPainterPath()
                        path.addRoundedRect(0, 0, scaled.width(), scaled.height(), 6, 6)
                        painter.setClipPath(path)
                        painter.drawPixmap(0, 0, scaled)
                        painter.end()
                        img_lbl.setPixmap(target)
                        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        # 单击图片：复制并粘贴（与普通条目行为一致）
                        img_lbl.singleClicked.connect(lambda: self.app_instance.on_item_clicked(self.list_item))
                        # 双击图片：看大图
                        if hasattr(self, 'on_view_image_clicked'):
                            img_lbl.doubleClicked.connect(self.on_view_image_clicked)
                            
                        layout.addWidget(img_lbl)
                    else:
                        img_lbl.setText("[图片正在保存中...]")
                        img_lbl.setStyleSheet("color: #a6adc8; font-style: italic;")
                        layout.addWidget(img_lbl)
                
                if text is not None:
                    display_text = text
                    
                    # 使用 QFontMetrics 动态计算并在必要时添加省略号
                    font = QFont("Microsoft YaHei", 10)
                    fm = QFontMetrics(font)
                    
                    # 设定最大允许宽度和高度（给一些安全边距）
                    # 假设卡片宽度约 260px，最大高度约 150px
                    # 但为了保险，我们使用字符级别的绝对限制来确保截断可见
                    max_chars = 150
                    lines = display_text.split('\n')
                    if len(lines) > 4:
                        display_text = '\n'.join(lines[:4]) + "\n..."
                    elif len(display_text) > max_chars:
                        display_text = display_text[:max_chars] + "..."
                    
                    # 容器用于包含 label 和 editor
                    self.text_container = QWidget()
                    self.text_container.setObjectName("TextContainer")
                    tc_layout = QVBoxLayout(self.text_container)
                    tc_layout.setContentsMargins(0, 0, 0, 0)
                    tc_layout.setSpacing(8)

                    self.text_lbl = QLabel(display_text)
                    self.text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    self.text_lbl.setFont(QFont("Microsoft YaHei", 10))
                    self.text_lbl.setWordWrap(True)
                    self.text_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                    self.text_lbl.setMaximumHeight(160) # 限制最大高度，超长文本在底部自然裁剪，不遮挡顶部
                    # 移除硬编码宽度，使用布局自动适应
                    self.text_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    if theme == "dark":
                        self.text_lbl.setStyleSheet("color: #cdd6f4; line-height: 1.4;")
                    else:
                        self.text_lbl.setStyleSheet("color: #4c4f69; line-height: 1.4;")
                    tc_layout.addWidget(self.text_lbl)

                    # 编辑器组件
                    self.text_edit = QTextEdit()
                    self.text_edit.setPlainText(text) # 使用完整文本进行编辑
                    self.text_edit.setFont(QFont("Microsoft YaHei", 10))
                    self.text_edit.setFixedHeight(120) # 默认高度
                    self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    if theme == "dark":
                        self.text_edit.setStyleSheet("QTextEdit { color: #cdd6f4; background-color: #181825; border: 1px solid #45475a; border-radius: 6px; padding: 8px; }")
                    else:
                        self.text_edit.setStyleSheet("QTextEdit { color: #4c4f69; background-color: #e6e9ef; border: 1px solid #dce0e8; border-radius: 6px; padding: 8px; }")
                    self.text_edit.hide()
                    tc_layout.addWidget(self.text_edit)

                    # 按钮行
                    self.edit_actions = QWidget()
                    ea_layout = QHBoxLayout(self.edit_actions)
                    ea_layout.setContentsMargins(0, 0, 0, 0)
                    ea_layout.setSpacing(8)
                    ea_layout.addStretch()

                    save_btn = QPushButton("保存")
                    save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    if theme == "dark":
                        save_btn.setStyleSheet("QPushButton { background-color: #89b4fa; color: #11111b; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background-color: #b4befe; }")
                    else:
                        save_btn.setStyleSheet("QPushButton { background-color: #1e66f5; color: #ffffff; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background-color: #7287fd; }")
                    
                    cancel_btn = QPushButton("取消")
                    cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    if theme == "dark":
                        cancel_btn.setStyleSheet("QPushButton { background-color: #45475a; color: #cdd6f4; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background-color: #585b70; }")
                    else:
                        cancel_btn.setStyleSheet("QPushButton { background-color: #dce0e8; color: #4c4f69; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background-color: #bcc0cc; }")

                    ea_layout.addWidget(cancel_btn)
                    ea_layout.addWidget(save_btn)
                    
                    self.edit_actions.hide()
                    tc_layout.addWidget(self.edit_actions)

                    layout.addWidget(self.text_container)

                    # 绑定内联编辑事件
                    def on_save():
                        new_text = self.text_edit.toPlainText()
                        
                        # 获取原始完整数据
                        data = self.list_item.data(Qt.ItemDataRole.UserRole)
                        old_text = ""
                        if isinstance(data, str):
                            old_text = data
                        elif isinstance(data, dict):
                            old_text = data.get("text", "")
                            
                        if new_text != old_text:
                            if isinstance(data, str):
                                data = {"type": "text", "text": new_text, "timestamp": time.time(), "pinned": False}
                            elif isinstance(data, dict):
                                data["text"] = new_text
                            self.list_item.setData(Qt.ItemDataRole.UserRole, data)
                            
                            new_display_text = new_text
                            max_chars = 200
                            lines = new_display_text.split('\n')
                            if len(lines) > 5:
                                new_display_text = '\n'.join(lines[:5]) + "\n..."
                            elif len(new_display_text) > max_chars:
                                new_display_text = new_display_text[:max_chars] + "..."
                            self.text_lbl.setText(new_display_text)
                            
                            self.app_instance.sync_item_data_to_history(data)
                            
                        self.text_edit.hide()
                        self.edit_actions.hide()
                        self.text_lbl.show()
                        self.app_instance._settings_open = False
                        
                        # 强制刷新列表项大小
                        self.adjustSize()
                        self.list_item.setSizeHint(self.sizeHint())
                        self.app_instance.update_list()
                        
                    def on_cancel():
                        # 获取原始完整数据以重置编辑器
                        data = self.list_item.data(Qt.ItemDataRole.UserRole)
                        old_text = ""
                        if isinstance(data, str):
                            old_text = data
                        elif isinstance(data, dict):
                            old_text = data.get("text", "")
                        self.text_edit.setPlainText(old_text)
                        self.text_edit.hide()
                        self.edit_actions.hide()
                        self.text_lbl.show()
                        self.app_instance._settings_open = False
                        
                        # 恢复原始大小
                        self.adjustSize()
                        self.list_item.setSizeHint(self.sizeHint())

                    save_btn.clicked.connect(on_save)
                    cancel_btn.clicked.connect(on_cancel)

            def on_view_image_clicked(self):
                image_path = getattr(self, 'image_path_to_view', None)
                pixmap = getattr(self, 'pixmap_to_view', None)
                if (image_path and os.path.exists(image_path)) or pixmap:
                    theme = self.app_instance.get_current_effective_theme()
                    self.app_instance._settings_open = True
                    dialog = ImageViewerDialog(image_path=image_path, pixmap=pixmap, parent=self.app_instance, theme=theme)
                    dialog.exec()
                    self.app_instance._settings_open = False

            def on_play_clicked(self):
                if self.video_path and os.path.exists(self.video_path):
                    import subprocess
                    # 使用系统默认播放器打开视频文件
                    os.startfile(self.video_path)

            def on_open_location_clicked(self):
                import os
                if hasattr(self, 'file_path_to_open') and self.file_path_to_open and os.path.exists(self.file_path_to_open):
                    import subprocess
                    if os.name == 'nt':
                        # Windows 下打开文件所在目录并选中该文件
                        subprocess.Popen(f'explorer /select,"{os.path.normpath(self.file_path_to_open)}"')
                    else:
                        # Mac/Linux 下简单打开所在目录
                        subprocess.call(('open', os.path.dirname(self.file_path_to_open)))

            def on_delete_clicked(self):
                QTimer.singleShot(0, lambda: self.app_instance.delete_single_item(self.list_item))

            def on_pin_clicked(self):
                # Toggle pinned state
                self.is_pinned = not self.is_pinned
                item_data = self.list_item.data(Qt.ItemDataRole.UserRole)
                if isinstance(item_data, dict):
                    item_data["pinned"] = self.is_pinned
                    self.list_item.setData(Qt.ItemDataRole.UserRole, item_data)
                
                # Update icon
                self.pin_btn.setIcon(create_svg_icon(SVG_PIN_FILLED if self.is_pinned else SVG_PIN, 14))
                
                # 实时更新卡片的边框高亮样式
                self.setProperty("pinned", self.is_pinned)
                self.style().unpolish(self)
                self.style().polish(self)
                
                # Sync to main history array and save
                self.app_instance.sync_item_data_to_history(item_data)
                # Re-sort list visually
                self.app_instance.update_list()

            def on_edit_clicked(self):
                # 展开内联编辑
                if hasattr(self, 'text_lbl') and hasattr(self, 'text_edit'):
                    self.app_instance._settings_open = True
                    self.text_lbl.hide()
                    self.text_edit.show()
                    self.edit_actions.show()
                    self.text_edit.setFocus()
                    # 重新计算卡片高度
                    self.adjustSize()
                    self.list_item.setSizeHint(self.sizeHint())

            def enterEvent(self, event):
                self.setProperty("hover", True)
                self.style().unpolish(self)
                self.style().polish(self)
                if hasattr(self, 'btn_container'):
                    self.btn_container.show()
                super().enterEvent(event)

            def leaveEvent(self, event):
                self.setProperty("hover", False)
                self.style().unpolish(self)
                self.style().polish(self)
                if hasattr(self, 'btn_container'):
                    self.btn_container.hide()
                super().leaveEvent(event)

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_start_pos = event.pos()
                super().mousePressEvent(event)
                
            def mouseMoveEvent(self, event):
                if not (event.buttons() & Qt.MouseButton.LeftButton):
                    return
                if hasattr(self, '_drag_start_pos'):
                    if (event.pos() - self._drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                        del self._drag_start_pos
                        self.app_instance.list_widget.setCurrentItem(self.list_item)
                        
                        # 手动触发列表的拖拽
                        self.app_instance.list_widget.startDrag(Qt.DropAction.CopyAction)

            def mouseReleaseEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    # 检查鼠标是否在按钮区域内，如果在按钮上释放，则不触发卡片的点击（粘贴）事件
                    # 必须将事件坐标映射到全局再判断，或者分别映射到各个按钮
                    if hasattr(self, 'btn_container') and self.btn_container.isVisible():
                        btn_pos = event.globalPosition().toPoint()
                        # 获取各个按钮的全局区域
                        for btn in self.btn_container.findChildren(QPushButton):
                            if btn.isVisible():
                                btn_global_pos = btn.mapToGlobal(QPoint(0, 0))
                                btn_global_rect = btn.rect().translated(btn_global_pos)
                                if btn_global_rect.contains(btn_pos):
                                    # 如果命中了按钮，直接丢弃这个事件，绝对不触发后面的粘贴逻辑！
                                    # 注意：我们这里不需要 event.accept() 或者触发 btn.click，
                                    # 因为 QPushButton 自己有 mouseReleaseEvent 会处理 click 信号。
                                    # 我们只需要 return 阻止 list_item 的 click 即可。
                                    return
                            
                    # 使用 QTimer 延迟执行，防止在事件处理中途销毁自身导致崩溃卡死
                    QTimer.singleShot(0, lambda: self.app_instance.on_item_clicked(self.list_item))
                    event.accept()
        
        current_theme = self.get_current_effective_theme()
        
        # 预处理数据以进行排序
        filtered_items = []
        for item_data in self.history:
            timestamp = item_data.get("timestamp", time.time()) if isinstance(item_data, dict) else time.time()
            is_pinned = item_data.get("pinned", False) if isinstance(item_data, dict) else False
            
            # 兼容老数据：如果没有 type 属性但有 text 属性，或者是纯字符串，那就是 text
            if isinstance(item_data, dict):
                item_type = item_data.get("type")
                if not item_type and "text" in item_data:
                    item_type = "text"
            else:
                item_type = "text"
            
            is_image = (item_type == "image")
            is_file = (item_type in ["file", "document", "video", "audio", "folder"])
            
            # 按类型筛选
            if filter_type == "文本" and item_type != "text":
                continue
            if filter_type == "图片" and item_type != "image":
                continue
            if filter_type == "文件" and item_type != "file":
                continue
            if filter_type == "文档" and item_type != "document":
                continue
            if filter_type == "视频" and item_type != "video":
                continue
            if filter_type == "音频" and item_type != "audio":
                continue
            if filter_type == "文件夹" and item_type != "folder":
                continue
                
            # 组装用于过滤的显示文本
            display_text = ""
            if is_image:
                path = item_data.get("path")
                img_name = os.path.basename(path) if path else "未知图片"
                display_text = f"[图片] {img_name}"
            elif is_file:
                urls = item_data.get("urls", [])
                file_count = len(urls)
                if file_count > 0:
                    first_file = urls[0]
                    if first_file.startswith("file:///"):
                        from PyQt6.QtCore import QUrl
                        first_file = QUrl(first_file).toLocalFile()
                    file_name = os.path.basename(first_file)
                    
                    if item_type == "document":
                        prefix = "[文档]"
                    elif item_type == "video":
                        prefix = "[视频]"
                    elif item_type == "audio":
                        prefix = "[音频]"
                    elif item_type == "folder":
                        prefix = "[文件夹]"
                    else:
                        prefix = "[文件]"
                        
                    display_text = f"{prefix} {file_name}" + (f" 等 {file_count} 个文件" if file_count > 1 else "")
            else:
                display_text = item_data.get("text", "") if isinstance(item_data, dict) else str(item_data)
                
            if search_query and search_query not in display_text.lower():
                continue
                
            filtered_items.append({
                "data": item_data,
                "display_text": display_text,
                "is_image": is_image,
                "is_file": is_file,
                "timestamp": timestamp,
                "pinned": is_pinned,
                "type": item_type
            })
            
        # 排序：置顶的在前，然后按时间倒序
        filtered_items.sort(key=lambda x: (x["pinned"], x["timestamp"]), reverse=True)
        
        # 渲染列表
        for item_info in filtered_items:
            item_data = item_info["data"]
            display_text = item_info["display_text"]
            timestamp = item_info["timestamp"]
            is_pinned = item_info["pinned"]
            item_type = item_info["type"]
            is_image = item_info["is_image"]
            is_file = item_info["is_file"]
            
            if is_image:
                path = item_data.get("path")
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, item_data)
                
                widget = HistoryItemWidget(self, item, text=display_text, image_path=path, timestamp=timestamp, is_pinned=is_pinned, theme=current_theme)
                viewport_width = self.list_widget.viewport().width() - 12
                if viewport_width > 0:
                    widget.setFixedWidth(viewport_width)
                
                self.list_widget.addItem(item)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.setItemWidget(item, widget)
            elif is_file:
                urls = item_data.get("urls", [])
                file_count = len(urls)
                if file_count == 0:
                    continue
                    
                first_file_name = os.path.basename(urls[0])
                if file_count > 1:
                    display_text = f"[文件] {first_file_name} 等 {file_count} 个文件"
                else:
                    if item_type == "folder":
                        display_text = f"[文件夹] {first_file_name}"
                    elif item_type == "document":
                        display_text = f"[文档] {first_file_name}"
                    elif item_type == "video":
                        display_text = f"[视频] {first_file_name}"
                    elif item_type == "audio":
                        display_text = f"[音频] {first_file_name}"
                    else:
                        display_text = f"[文件] {first_file_name}"
                
                if search_query and search_query not in display_text.lower():
                    continue
                    
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, item_data)
                item.setForeground(QColor(0, 0, 0, 0)) 
                
                pixmap = None
                if file_count == 1 and item_type == "video":
                    video_path = urls[0]
                    if not hasattr(self, 'thumbnail_cache'):
                        self.thumbnail_cache = {}
                    if video_path in self.thumbnail_cache:
                        pixmap = self.thumbnail_cache[video_path]
                    else:
                        try:
                            import shutil
                            import tempfile
                            temp_video_path = os.path.join(tempfile.gettempdir(), f"temp_main_preview_{hash(video_path)}.mp4")
                            shutil.copy2(video_path, temp_video_path)
                            
                            cap = cv2.VideoCapture(temp_video_path)
                            if cap.isOpened():
                                # 跳过前面几帧，取更有代表性的一帧
                                cap.set(cv2.CAP_PROP_POS_FRAMES, min(30, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)/2)))
                                ret, frame = cap.read()
                                if not ret: # 如果失败，尝试取第一帧
                                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                    ret, frame = cap.read()
                                if ret:
                                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                    h, w, ch = frame.shape
                                    bytes_per_line = ch * w
                                    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                                    # 为了防止被垃圾回收导致花屏，需要强制拷贝（copy）
                                    base_pixmap = QPixmap.fromImage(qimg.copy())
                                    
                                    # 绘制视频播放器居中叠加图标
                                    pixmap = QPixmap(base_pixmap.size())
                                    pixmap.fill(Qt.GlobalColor.transparent)
                                    painter = QPainter(pixmap)
                                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                                    painter.drawPixmap(0, 0, base_pixmap)
                                    
                                    cx = pixmap.width() / 2
                                    cy = pixmap.height() / 2
                                    # 半透明黑底圆 (回归经典纯粹的播放按钮)
                                    painter.setBrush(QColor(0, 0, 0, 160))
                                    painter.setPen(Qt.PenStyle.NoPen)
                                    painter.drawEllipse(QPointF(cx, cy), 28, 28)
                                    
                                    # 白色播放三角
                                    painter.setBrush(QColor(255, 255, 255, 255))
                                    triangle = QPainterPath()
                                    # 调整三角比例，使其更符合标准审美
                                    triangle.moveTo(cx - 6, cy - 10)
                                    triangle.lineTo(cx + 12, cy)
                                    triangle.lineTo(cx - 6, cy + 10)
                                    triangle.closeSubpath()
                                    painter.drawPath(triangle)
                                    painter.end()
                                    
                                    self.thumbnail_cache[video_path] = pixmap
                                cap.release()
                                
                            try:
                                if os.path.exists(temp_video_path):
                                    os.remove(temp_video_path)
                            except:
                                pass
                        except Exception as e:
                            if 'painter' in locals() and painter.isActive():
                                painter.end()
                            pass
                
                widget = HistoryItemWidget(self, item, text=display_text, pixmap=pixmap, video_path=video_path if file_count == 1 and item_type == "video" else None, timestamp=timestamp, is_pinned=is_pinned, theme=current_theme)
                viewport_width = self.list_widget.viewport().width() - 12
                if viewport_width > 0:
                    widget.setFixedWidth(viewport_width)
                
                self.list_widget.addItem(item)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.setItemWidget(item, widget)
                
            else:
                text = item_data.get("text", "") if isinstance(item_data, dict) else item_data
                if search_query and search_query not in text.lower():
                    continue
                    
                display_text = text.strip()
                lines = display_text.split('\n')
                if len(lines) > 8:
                    display_text = '\n'.join(lines[:8]) + "\n..."
                elif len(display_text) > 300:
                    display_text = display_text[:300] + "..."
                    
                item = QListWidgetItem(text)
                # 关键修复：统一将完整的字典数据（包含timestamp等）存入UserRole，方便精准删除
                item.setData(Qt.ItemDataRole.UserRole, item_data)
                item.setForeground(QColor(0, 0, 0, 0)) 
                
                widget = HistoryItemWidget(self, item, text=text, timestamp=timestamp, is_pinned=is_pinned, theme=current_theme)
                viewport_width = self.list_widget.viewport().width() - 12
                if viewport_width > 0:
                    widget.setFixedWidth(viewport_width)
                
                self.list_widget.addItem(item)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.setItemWidget(item, widget)

        # 恢复滚动条状态，避免刷新后跳动
        self.list_widget.verticalScrollBar().setValue(scroll_val)
        
        # 强制重绘，消除残影
        self.list_widget.viewport().update()

    def _sync_bottom_area(self):
        """布局稳定后：校验底部提示状态"""
        self._update_footer_end_state()

    def _update_footer_end_state(self):
        """当滚动到底部（或内容不足一屏）且有记录时，底部提示改为"已显示全部记录" """
        if not hasattr(self, "list_widget") or not hasattr(self, "footer_hint"):
            return
        lw = self.list_widget
        if lw.count() == 0:  # 无实际记录
            self.footer_hint.set_end_state(False)
            return
        sb = lw.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum()
        self.footer_hint.set_end_state(at_bottom)

    def toggle_window(self):
        if self.isVisible():
            if self.stacked_widget.currentIndex() == 2 and hasattr(self, 'settings_widget'):
                if getattr(self.settings_widget, 'has_unsaved_changes', False):
                    dialog = CustomSaveConfirmDialog(
                        "保存提示", "您有未保存的设置，是否要保存并关闭？", 
                        theme=self.get_current_effective_theme(), 
                        parent=self
                    )
                    dialog.exec()
                    
                    if dialog.result_action == "save":
                        self.settings_widget.save_settings()
                        self.hide()
                    elif dialog.result_action == "discard":
                        self.settings_widget.has_unsaved_changes = False
                        self.hide()
                    return
            self.hide()
        else:
            self.show_window()

    def on_snippet_phrase_clicked(self, data):
        if self.config.get("hide_after_copy", True):
            self.hide()
        mime_data = QMimeData()
        
        item_type = data.get("type", "text")
        content = data.get("content", "")
        remark = data.get("remark", "")
        
        # 将备注文字放入剪贴板的纯文本部分
        if remark:
            mime_data.setText(remark)
            
        if item_type == "image":
            if isinstance(content, str) and os.path.exists(content):
                image = QImage(content)
                mime_data.setImageData(image)
                mime_data.setUrls([QUrl.fromLocalFile(content)])
                try:
                    with open(content, "rb") as f:
                        png_data = f.read()
                        mime_data.setData("image/png", QByteArray(png_data))
                except Exception:
                    pass
        elif item_type in ["file", "video"]:
            paths = content if isinstance(content, list) else [content]
            urls = [QUrl.fromLocalFile(p) for p in paths if os.path.exists(p)]
            if urls:
                mime_data.setUrls(urls)
        elif item_type == "text":
            # 如果是纯文本类型，文本内容本身就是 content
            mime_data.setText(str(content))
            
        QApplication.clipboard().setMimeData(mime_data)
        
        # 无论是否隐藏窗口，都触发系统的自动粘贴
        self.do_paste_action()
        
    def do_paste_action(self):
        def do_paste():
            # 如果没有隐藏窗口，需要将焦点交还给目标窗口才能粘贴
            if not self.config.get("hide_after_copy", True):
                try:
                    import win32gui
                    import win32process
                    import win32api
                    import time
                    if hasattr(self, 'previous_hwnd') and self.previous_hwnd:
                        current_thread = win32api.GetCurrentThreadId()
                        target_thread, _ = win32process.GetWindowThreadProcessId(self.previous_hwnd)
                        if current_thread != target_thread:
                            win32process.AttachThreadInput(current_thread, target_thread, True)
                            win32gui.SetForegroundWindow(self.previous_hwnd)
                            win32gui.SetFocus(self.previous_hwnd)
                            win32process.AttachThreadInput(current_thread, target_thread, False)
                        else:
                            win32gui.SetForegroundWindow(self.previous_hwnd)
                            win32gui.SetFocus(self.previous_hwnd)
                        # 给目标窗口一点时间来准备接收输入
                        time.sleep(0.05)
                except Exception as e:
                    print("Restore focus failed:", e)

            try:
                import win32api
                import win32con
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                win32api.keybd_event(ord('V'), 0, 0, 0)
                win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            except ImportError:
                keyboard.send('ctrl+v')
        
        QTimer.singleShot(15, do_paste)
        
        theme = self.get_current_effective_theme()
        self.toast = Toast("已复制并自动粘贴", parent=None, theme=theme)
        center_pos = self.geometry().center()
        QTimer.singleShot(50, lambda: self.toast.show_toast(center_pos))
        
    def show_window(self):
        # 如果窗口不可见，先同步一次主题
        if not self.isVisible():
            self.apply_theme()
            self.search_input.clear()
            
        self.show()
        self.raise_()
        self.activateWindow()
        
        # 获取焦点必须在窗口可见后
        self.search_input.setFocus()
        
        # 布局稳定后校验底部提示状态
        QTimer.singleShot(50, self._sync_bottom_area)

    def show_item_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        # 匹配主题样式
        theme = self.get_current_effective_theme()
        if theme == "dark":
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    border: 1px solid #313244;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 32px 8px 12px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #313244;
                    color: #89b4fa;
                }
                QMenu::icon {
                    padding-left: 10px;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 32px 8px 12px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #eff1f5;
                    color: #1e66f5;
                }
                QMenu::icon {
                    padding-left: 10px;
                }
            """)
            
        delete_action = QAction("删除此条记录", self)
        delete_action.setIcon(create_svg_icon(SVG_TRASH, 16))
        delete_action.triggered.connect(lambda: self.delete_single_item(item))
        
        menu.addAction(delete_action)
        menu.exec(self.list_widget.viewport().mapToGlobal(position))

    def delete_single_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        
        # 从界面中提前获取当前的 row
        row = self.list_widget.row(item)
        
        # 从历史记录列表中找到并移除对应项
        target_item = None
        for h in self.history:
            if h == data:
                target_item = h
                break
            # Fallback 比较逻辑（防止因为 PyQt 数据转换导致的不等）
            elif isinstance(h, dict) and isinstance(data, dict):
                if h.get("type") == "image" and data.get("type") == "image":
                    if h.get("path") == data.get("path") and h.get("timestamp") == data.get("timestamp"):
                        target_item = h
                        break
                elif h.get("text") == data.get("text") and h.get("timestamp") == data.get("timestamp"):
                    target_item = h
                    break
            elif isinstance(h, dict) and not isinstance(data, dict):
                if h.get("text") == data:
                    target_item = h
                    break
            elif not isinstance(h, dict) and h == data:
                target_item = h
                break
                
        # 无论底层是否找到，UI层面我们强制移除！
        # 标记不需要复制剪贴板
        self.ignore_change = True
        
        if row >= 0:
            self.list_widget.takeItem(row)
                
        if target_item:
            try:
                self.history.remove(target_item)
            except ValueError:
                pass # 如果万一不在列表里，忽略异常
                
            # 如果是图片，顺便清理本地文件
            if isinstance(target_item, dict) and target_item.get("type") == "image":
                try:
                    if not target_item.get("is_external"):
                        os.remove(target_item.get("path"))
                except:
                    pass
                    
            self.save_history()
            
        # 额外增加一种强制清理模式：如果通过上面精准匹配没找到，
        # 且是因为某种异常数据导致的，我们可以根据它在界面的索引(row)直接尝试去底层列表里删掉它
        # （因为列表显示的顺序和底层 history 是一一对应的）
        elif row >= 0 and row < len(self.history):
            try:
                fallback_item = self.history[row]
                self.history.pop(row)
                if isinstance(fallback_item, dict) and fallback_item.get("type") == "image":
                    try:
                        if not fallback_item.get("is_external"):
                            os.remove(fallback_item.get("path"))
                    except:
                        pass
                self.save_history()
            except Exception:
                pass
        
        # 清除最后一次复制的缓存记录，防止删除后立刻再次复制相同内容被当成重复项忽略
        self.last_text = ""
        self.last_image_hash = ""
        self.ignore_change = False

    def on_item_clicked(self, item):
        # 由于禁用了选中状态，我们手动清理焦点即可
        self.list_widget.clearFocus()
        
        data = item.data(Qt.ItemDataRole.UserRole)
        self.ignore_change = True
        
        target_item = None
        mime_data = QMimeData()
        
        if isinstance(data, dict):
            item_type = data.get("type")
            if item_type == "image":
                path = data.get("path")
                if path and os.path.exists(path):
                    image = QImage(path)
                    mime_data.setImageData(image)
                    mime_data.setUrls([QUrl.fromLocalFile(path)])
                self.last_image_hash = data.get("hash", "")
                self.last_text = ""
                for h in self.history:
                    if isinstance(h, dict) and h.get("type") == "image" and h.get("path") == path:
                        target_item = h
                        break
            elif item_type in ["file", "document", "video", "audio", "folder"]:
                urls = [QUrl.fromLocalFile(p) for p in data.get("urls", [])]
                mime_data.setUrls(urls)
                self.last_image_hash = data.get("hash", "")
                self.last_text = ""
                for h in self.history:
                    if isinstance(h, dict) and h.get("type") == item_type and h.get("hash") == data.get("hash"):
                        target_item = h
                        break
            elif item_type == "text":
                text = data.get("text", "")
                self.last_text = text
                self.last_image_hash = ""
                mime_data.setText(text)
                for h in self.history:
                    if isinstance(h, dict) and h.get("type") == "text" and h.get("text") == text:
                        target_item = h
                        break
            else:
                # 兼容非常旧的数据结构
                text = data.get("text", "")
                self.last_text = text
                self.last_image_hash = ""
                mime_data.setText(text)
                for h in self.history:
                    if isinstance(h, dict) and h.get("text") == text:
                        target_item = h
                        break
        else:
            text = data if not isinstance(data, dict) else data.get("text", "")
            self.last_text = text
            self.last_image_hash = ""
            mime_data.setText(text)
            for h in self.history:
                if (h.get("text") if isinstance(h, dict) else h) == text:
                    target_item = h
                    break
                    
        self.clipboard.setMimeData(mime_data)
                    
        if target_item:
            self.history.remove(target_item)
            if isinstance(target_item, dict):
                target_item["timestamp"] = time.time()
            else:
                target_item = {"text": data, "timestamp": time.time()}
            self.history.insert(0, target_item)
            
        # 在触发隐藏和粘贴前，彻底清除列表的焦点状态
        self.list_widget.clearSelection()
        self.list_widget.clearFocus()
            
        # 根据设置决定是否隐藏窗口和自动粘贴
        if self.config.get("hide_after_copy", True):
            # 优化点 1: 隐藏窗口必须放在最前面，这样底层目标窗口才能尽早获得焦点！
            self.hide()
            
        # 无论是否隐藏，都触发自动粘贴
        self.do_paste_action()
        
        # 优化点 3: 将耗时的 IO 操作 (保存历史、刷新列表) 放到最后异步执行，绝对不能阻塞粘贴
        QTimer.singleShot(100, self.update_list)
        QTimer.singleShot(150, self.save_history)

    def confirm_and_clear_history(self):
        theme = self.get_current_effective_theme()
        dialog = ConfirmDialog(None, theme)
        screen = QApplication.primaryScreen().geometry()
        dialog.move(screen.center() - dialog.rect().center())
        dialog.exec()
        if dialog.result_btn:
            self.clear_history()

    def clear_history(self):
        # 彻底清空前，先将本地保存的图片文件一并删除
        for item in self.history:
            if isinstance(item, dict) and item.get("type") == "image":
                try:
                    if not item.get("is_external") and os.path.exists(item.get("path")):
                        os.remove(item.get("path"))
                except:
                    pass
        
        self.history.clear()
        self.last_text = ""
        self.last_image_hash = ""
        self.update_list()
        self.save_history()

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
if __name__ == "__main__":
    # 启用高 DPI 缩放支持，确保打包后与源码运行的高清显示效果完全一致
    import os
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    
    if "--quit" in sys.argv:
        socket = QLocalSocket()
        socket.connectToServer("KjjClipboardManagerUniqueLock_Server")
        if socket.waitForConnected(500):
            socket.write(b"QUIT_APP")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
        sys.exit(0)

    # 使用 QLocalServer 替代 QSharedMemory 实现防止多开并唤醒旧窗口
    socket = QLocalSocket()
    socket.connectToServer(f"{APP_ID}_Server")
    if socket.waitForConnected(500):
        # 已经有实例运行，发送消息让其显示窗口
        socket.write(b"SHOW_WINDOW")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0)
        
    # 如果没有实例运行，启动服务器
    server = QLocalServer()
    QLocalServer.removeServer(f"{APP_ID}_Server")
    server.listen(f"{APP_ID}_Server")

    # 强制使用 Fusion 风格，确保打包后与源码运行环境一致，防止滚动条样式退化和布局挤压
    app.setStyle("Fusion")

    # 为整个应用程序全局应用自定义样式，根除任何焦点虚线框
    app.setStyle(NoFocusStyle("Fusion"))
    app.setQuitOnLastWindowClosed(False) 
    window = ClipboardApp()
    
    # 监听其他实例的唤醒请求
    def handle_new_connection():
        client = server.nextPendingConnection()
        if client:
            if client.waitForReadyRead(500):
                msg = client.readAll().data()
                if msg == b"SHOW_WINDOW":
                    window.show_window()
                elif msg == b"QUIT_APP":
                    if hasattr(window, 'tray_icon'):
                        window.tray_icon.hide()
                    QApplication.instance().quit()
            client.disconnectFromServer()
            
    server.newConnection.connect(handle_new_connection)

    window.show_window()
    sys.exit(app.exec())