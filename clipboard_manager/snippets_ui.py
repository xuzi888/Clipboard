import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QInputDialog,
    QMessageBox, QSplitter, QFrame, QMenu, QDialog, QLineEdit, QTextEdit,
    QGraphicsDropShadowEffect, QComboBox, QGraphicsView, QGraphicsScene,
    QAbstractItemView, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QFont, QAction, QCursor, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray
from snippets_manager import SnippetsManager

SVG_FOLDER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>'
SVG_SCENE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect></svg>'
SVG_PHRASE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><path d="M13 8H7"></path><path d="M17 12H7"></path></svg>'
SVG_PLUS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>'
SVG_IMAGE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>'
SVG_FILE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>'

SVG_TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'
SVG_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'
SVG_PLAY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon></svg>'
SVG_ZOOM = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>'

_svg_cache = {}

def create_svg_icon(svg_str, size=24, color=None):
    cache_key = (svg_str, size, color)
    if cache_key in _svg_cache:
        return QIcon(_svg_cache[cache_key])
        
    if color and 'currentColor' in svg_str:
        svg_str = svg_str.replace('currentColor', color)
    elif 'currentColor' in svg_str:
        svg_str = svg_str.replace('currentColor', '#000000')
    
    renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
    
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
    return QIcon(pixmap)

class CustomInputDialog(QDialog):
    def __init__(self, title, label_text, text="", multiline=False, theme="light", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.theme = theme
        self.multiline = multiline
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # 标题
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        container_layout.addWidget(title_lbl)
        
        # 提示文本
        desc_lbl = QLabel(label_text)
        desc_lbl.setFont(QFont("Microsoft YaHei", 10))
        container_layout.addWidget(desc_lbl)
        
        # 输入框
        if multiline:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(text)
            self.input_field.setMinimumHeight(120)
        else:
            self.input_field = QLineEdit()
            self.input_field.setText(text)
            self.input_field.setMinimumHeight(36)
        self.input_field.setFont(QFont("Microsoft YaHei", 10))
        container_layout.addWidget(self.input_field)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setObjectName("OkBtn")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.validate_and_accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        self.update_theme(theme)
        self.resize(420, 280 if multiline else 200)

    def update_theme(self, theme=None):
        if theme:
            self.theme = theme
        bg_color = "#1e1e2e" if self.theme == "dark" else "#ffffff"
        text_color = "#cdd6f4" if self.theme == "dark" else "#4c4f69"
        border_color = "#313244" if self.theme == "dark" else "#dce0e8"
        input_bg = "#181825" if self.theme == "dark" else "#f2f4f8"
        btn_bg = "#313244" if self.theme == "dark" else "#e6e9ef"
        btn_hover = "#45475a" if self.theme == "dark" else "#ccd0da"
        
        ok_bg = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        ok_color = "#11111b" if self.theme == "dark" else "#ffffff"
        ok_hover = "#b4befe" if self.theme == "dark" else "#7287fd"
        
        self.setStyleSheet(f"""
            #Container {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QLineEdit, QTextEdit {{
                background-color: {input_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px;
                outline: none;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {ok_bg};
            }}
            QPushButton {{
                padding: 6px 16px;
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 10pt;
            }}
            QPushButton#AttachBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QPushButton#AttachBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#CancelBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#OkBtn {{
                background-color: {ok_bg};
                color: {ok_color};
                border: none;
                font-weight: bold;
            }}
            QPushButton#OkBtn:hover {{
                background-color: {ok_hover};
            }}
        """)

    def get_text(self):
        if self.multiline:
            return self.input_field.toPlainText()
        return self.input_field.text()

    def validate_and_accept(self):
        text = self.get_text().strip()
        if not text:
            CustomAlertDialog("提示", "内容不能为空！", theme=self.theme, parent=self).exec()
            return
        self.accept()

class CustomConfirmDialog(QDialog):
    def __init__(self, title, text, theme="light", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.theme = theme
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
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
        self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setObjectName("OkBtn")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        self.update_theme(theme)
        self.resize(360, 160)

    def update_theme(self, theme=None):
        if theme:
            self.theme = theme
        bg_color = "#1e1e2e" if self.theme == "dark" else "#ffffff"
        text_color = "#cdd6f4" if self.theme == "dark" else "#4c4f69"
        border_color = "#313244" if self.theme == "dark" else "#dce0e8"
        btn_bg = "#313244" if self.theme == "dark" else "#e6e9ef"
        btn_hover = "#45475a" if self.theme == "dark" else "#ccd0da"
        
        # 危险操作用红色系
        ok_bg = "#f38ba8" if self.theme == "dark" else "#d20f39"
        ok_color = "#11111b" if self.theme == "dark" else "#ffffff"
        ok_hover = "#eba0ac" if self.theme == "dark" else "#e64553"
        
        self.setStyleSheet(f"""
            #Container {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                padding: 6px 16px;
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 10pt;
            }}
            QPushButton#AttachBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QPushButton#AttachBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#CancelBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#OkBtn {{
                background-color: {ok_bg};
                color: {ok_color};
                border: none;
                font-weight: bold;
            }}
            QPushButton#OkBtn:hover {{
                background-color: {ok_hover};
            }}
        """)

class CustomAlertDialog(QDialog):
    def __init__(self, title, text, theme="light", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.theme = theme
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
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
        
        self.btn_ok = QPushButton("我知道了")
        self.btn_ok.setObjectName("OkBtn")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_ok)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        self.update_theme(theme)
        self.resize(360, 160)

    def update_theme(self, theme=None):
        if theme:
            self.theme = theme
        bg_color = "#1e1e2e" if self.theme == "dark" else "#ffffff"
        text_color = "#cdd6f4" if self.theme == "dark" else "#4c4f69"
        border_color = "#313244" if self.theme == "dark" else "#dce0e8"
        
        ok_bg = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        ok_color = "#11111b" if self.theme == "dark" else "#ffffff"
        ok_hover = "#b4befe" if self.theme == "dark" else "#7287fd"
        
        self.setStyleSheet(f"""
            #Container {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                padding: 6px 16px;
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 10pt;
            }}
            QPushButton#OkBtn {{
                background-color: {ok_bg};
                color: {ok_color};
                border: none;
                font-weight: bold;
            }}
            QPushButton#OkBtn:hover {{
                background-color: {ok_hover};
            }}
            QPushButton#AddInlineBtn {{
                background-color: {ok_bg};
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton#AddInlineBtn:hover {{
                background-color: {ok_hover};
            }}
        """)

class ImageGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1 / 1.15, 1 / 1.15)

class ImageViewerDialog(QDialog):
    def __init__(self, image_path, parent=None, theme="light"):
        super().__init__(parent)
        self.setWindowTitle("图片预览 (滚轮缩放，拖拽平移)")
        self.resize(800, 600)
        
        bg_color = "#1e1e2e" if theme == "dark" else "#f2f4f8"
        self.setStyleSheet(f"background-color: {bg_color};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = ImageGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.pixmap = QPixmap(image_path)
        self.scene.addPixmap(self.pixmap)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.view)

    def showEvent(self, event):
        super().showEvent(event)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class PhraseWizardDialog(QDialog):
    def __init__(self, manager, theme="light", default_scene="", default_group="", default_phrase="", is_edit=False, default_type="text", edit_content="", parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("编辑快捷短语" if is_edit else "新建快捷短语")
        self.theme = theme
        if is_edit:
            self.edit_content = edit_content
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = QWidget()
        self.container.setObjectName("Container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # 标题
        title_lbl = QLabel("编辑快捷短语" if is_edit else "新建快捷短语")
        title_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        container_layout.addWidget(title_lbl)
        
        # 场景选择
        scene_lbl = QLabel("选择场景:")
        scene_lbl.setFont(QFont("Microsoft YaHei", 10))
        
        scene_layout = QHBoxLayout()
        scene_layout.setSpacing(10)
        self.scene_combo = QComboBox()
        self.scene_combo.setMinimumHeight(36)
        self.scene_combo.setFont(QFont("Microsoft YaHei", 10))
        
        self.btn_add_scene = QPushButton()
        self.btn_add_scene.setIcon(create_svg_icon(SVG_PLUS, 18, "#ffffff" if self.theme == "dark" else "#ffffff"))
        self.btn_add_scene.setObjectName("AddInlineBtn")
        self.btn_add_scene.setFixedSize(36, 36)
        self.btn_add_scene.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_scene.setToolTip("新建场景")
        self.btn_add_scene.clicked.connect(self.on_add_scene_inline)
        
        scene_layout.addWidget(self.scene_combo)
        scene_layout.addWidget(self.btn_add_scene)
        
        container_layout.addWidget(scene_lbl)
        container_layout.addLayout(scene_layout)
        
        # 分组选择
        group_lbl = QLabel("选择分组:")
        group_lbl.setFont(QFont("Microsoft YaHei", 10))
        
        group_layout = QHBoxLayout()
        group_layout.setSpacing(10)
        self.group_combo = QComboBox()
        self.group_combo.setMinimumHeight(36)
        self.group_combo.setFont(QFont("Microsoft YaHei", 10))
        
        self.btn_add_group = QPushButton()
        self.btn_add_group.setIcon(create_svg_icon(SVG_PLUS, 18, "#ffffff" if self.theme == "dark" else "#ffffff"))
        self.btn_add_group.setObjectName("AddInlineBtn")
        self.btn_add_group.setFixedSize(36, 36)
        self.btn_add_group.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_group.setToolTip("新建分组")
        self.btn_add_group.clicked.connect(self.on_add_group_inline)
        
        group_layout.addWidget(self.group_combo)
        group_layout.addWidget(self.btn_add_group)
        
        container_layout.addWidget(group_lbl)
        container_layout.addLayout(group_layout)
        
        # 短语输入
        self.phrase_lbl = QLabel("内容:")
        self.phrase_lbl.setFont(QFont("Microsoft YaHei", 10))
        
        self.phrase_input = QTextEdit()
        if default_phrase and default_type == "text":
            self.phrase_input.setText(default_phrase)
        self.phrase_input.setPlaceholderText("请输入短语内容...")
        self.phrase_input.setMinimumHeight(100)
        self.phrase_input.setFont(QFont("Microsoft YaHei", 10))
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        
        self.file_paths = []
        self.file_type = default_type
        
        self.btn_attach = QPushButton(" 选择文件/图片")
        self.btn_attach.setObjectName("AttachBtn")
        self.btn_attach.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_attach.clicked.connect(self.on_attach_file)
        if is_edit:
            self.btn_attach.hide()
            
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.phrase_lbl)
        file_layout.addStretch()
        file_layout.addWidget(self.btn_attach)
        
        self.file_label = QPushButton("")
        self.file_label.setObjectName("FileLabel")
        self.file_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.file_label.hide()
        
        container_layout.addLayout(file_layout)
        container_layout.addWidget(self.phrase_input)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.preview_label.mouseReleaseEvent = self.on_preview_clicked
        self.preview_label.setToolTip("点击打开文件")
        self.preview_label.hide()
        container_layout.addWidget(self.preview_label)
        
        container_layout.addWidget(self.file_label)
        
        if default_type != "text":
            self.phrase_input.hide()
            self.phrase_lbl.setText("备注:")
            
            # 使用备注作为文本框内容
            if default_phrase:
                self.phrase_input.setText(default_phrase)
            self.phrase_input.setPlaceholderText("可以在此输入针对该附件的备注信息...")
            self.phrase_input.show()
            
            # 在编辑状态下，传递过来的通常是内容（即文件路径）
            if hasattr(self, 'edit_content'):
                self.default_phrase = self.edit_content
                if default_type in ["image", "video"]:
                    self.show_preview(self.edit_content, default_type)
                else:
                    self.file_label.setIcon(create_svg_icon(SVG_FILE, 18, file_color))
                    self.file_label.setText(f" 已选择文件: {self.edit_content}")
                    self.file_label.show()
            else:
                self.default_phrase = default_phrase
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setObjectName("OkBtn")
        self.btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        self.update_theme()
        self.resize(450, 480)

        # 关联事件
        self.scene_combo.currentIndexChanged.connect(self.on_scene_changed)
        
        # 初始化数据
        self.refresh_scenes(default_scene)
        self.on_scene_changed()
        
        g_idx = self.group_combo.findText(default_group)
        if g_idx >= 0:
            self.group_combo.setCurrentIndex(g_idx)

    def refresh_scenes(self, select_text=""):
        self.scene_combo.blockSignals(True)
        self.scene_combo.clear()
        for s in self.manager.get_scenes():
            self.scene_combo.addItem(s["name"], s)
        self.scene_combo.blockSignals(False)
        
        idx = self.scene_combo.findText(select_text)
        if idx >= 0:
            self.scene_combo.setCurrentIndex(idx)
        elif self.scene_combo.count() > 0:
            self.scene_combo.setCurrentIndex(0)
            
        self.on_scene_changed()

    def on_preview_clicked(self, event):
        if hasattr(self, 'current_preview_file') and self.current_preview_file:
            import os
            try:
                ext = os.path.splitext(self.current_preview_file)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                    viewer = ImageViewerDialog(self.current_preview_file, self, theme=self.theme)
                    viewer.exec()
                else:
                    os.startfile(self.current_preview_file)
            except Exception as e:
                print(f"Failed to open file: {e}")

    def on_add_scene_inline(self):
        dialog = CustomInputDialog("新建场景", "请输入场景名称:", theme=self.theme, parent=self)
        if dialog.exec():
            name = dialog.get_text().strip()
            if name:
                for s in self.manager.get_scenes():
                    if s["name"] == name:
                        CustomAlertDialog("提示", "该场景已存在！", theme=self.theme, parent=self).exec()
                        return
                
                # 创建新场景
                self.manager.add_scene(name)
                
                # 通知父组件(SnippetsUI)刷新外层树
                if hasattr(self.parent(), "load_tree"):
                    self.parent().load_tree()
                    
                # 重新刷新当前下拉框，并选中新建的场景
                self.refresh_scenes(name)

    def on_add_group_inline(self):
        scene_data = self.scene_combo.currentData()
        if not scene_data:
            CustomAlertDialog("提示", "请先选择或创建一个场景！", theme=self.theme, parent=self).exec()
            return
            
        dialog = CustomInputDialog("新建分组", "请输入分组名称:", theme=self.theme, parent=self)
        if dialog.exec():
            name = dialog.get_text().strip()
            if name:
                for i in range(self.group_combo.count()):
                    if self.group_combo.itemText(i) == name:
                        CustomAlertDialog("提示", "该分组已存在！", theme=self.theme, parent=self).exec()
                        return
                
                # 在manager中创建分组
                self.manager.add_group(scene_data["id"], name)
                
                # 通知父组件(SnippetsUI)刷新外层树
                if hasattr(self.parent(), "load_tree"):
                    self.parent().load_tree()
                
                # 重要：从manager获取最新数据，因为scene_data是缓存的旧对象
                latest_scenes = self.manager.get_scenes()
                for s in latest_scenes:
                    if s["id"] == scene_data["id"]:
                        # 更新scene_combo里的UserRole数据
                        idx = self.scene_combo.currentIndex()
                        self.scene_combo.setItemData(idx, s)
                        break
                        
                # 刷新分组下拉框并选中新建的组
                self.on_scene_changed()
                g_idx = self.group_combo.findText(name)
                if g_idx >= 0:
                    self.group_combo.setCurrentIndex(g_idx)

    def on_scene_changed(self):
        self.group_combo.clear()
        scene_data = self.scene_combo.currentData()
        if scene_data and "groups" in scene_data:
            for g in scene_data["groups"]:
                self.group_combo.addItem(g["name"], g)

    def update_theme(self, theme=None):
        if theme:
            self.theme = theme
        bg_color = "#1e1e2e" if self.theme == "dark" else "#ffffff"
        text_color = "#cdd6f4" if self.theme == "dark" else "#4c4f69"
        border_color = "#313244" if self.theme == "dark" else "#dce0e8"
        input_bg = "#181825" if self.theme == "dark" else "#f2f4f8"
        btn_bg = "#313244" if self.theme == "dark" else "#e6e9ef"
        btn_hover = "#45475a" if self.theme == "dark" else "#ccd0da"
        
        ok_bg = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        ok_color = "#11111b" if self.theme == "dark" else "#ffffff"
        ok_hover = "#b4befe" if self.theme == "dark" else "#7287fd"
        
        file_bg = "rgba(137, 180, 250, 0.15)" if self.theme == "dark" else "rgba(30, 102, 245, 0.1)"
        file_border = "rgba(137, 180, 250, 0.3)" if self.theme == "dark" else "rgba(30, 102, 245, 0.2)"
        file_color = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        
        svg_color = text_color.replace("#", "%23")
        self.btn_attach.setIcon(create_svg_icon(SVG_FILE, 16, text_color))
        self.setStyleSheet(f"""
            #Container {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton#FileLabel {{
                background-color: {file_bg};
                color: {file_color};
                border: 1px solid {file_border};
                border-radius: 8px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 11pt;
                text-align: center;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {input_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px;
                outline: none;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{svg_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>');
                width: 14px;
                height: 14px;
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {text_color};
                selection-background-color: {ok_bg};
                selection-color: {ok_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                outline: none;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {ok_bg};
            }}
            QPushButton {{
                padding: 6px 16px;
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 10pt;
            }}
            QPushButton#AttachBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QPushButton#AttachBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#CancelBtn {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#OkBtn {{
                background-color: {ok_bg};
                color: {ok_color};
                border: none;
                font-weight: bold;
            }}
            QPushButton#OkBtn:hover {{
                background-color: {ok_hover};
            }}
            QPushButton#AddInlineBtn {{
                background-color: {ok_bg};
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton#AddInlineBtn:hover {{
                background-color: {ok_hover};
            }}
        """)

    def show_preview(self, file_path, f_type):
        self.current_preview_file = file_path
        import os
        from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPainterPath, QFont
        from PyQt6.QtCore import Qt, QPointF
        
        if f_type == "image":
            pm = QPixmap(file_path)
            if not pm.isNull():
                scaled = pm.scaled(380, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
                self.preview_label.show()
                self.file_label.hide()
            else:
                self.file_label.setIcon(create_svg_icon(SVG_IMAGE, 18, "#89b4fa" if self.theme == "dark" else "#1e66f5"))
                self.file_label.setText(f" 已选择图片: {os.path.basename(file_path)}")
                self.file_label.show()
                self.preview_label.hide()
        elif f_type == "video":
            self.preview_label.hide()
            try:
                import cv2
                import tempfile
                import shutil
                
                # 尝试直接打开
                cap = cv2.VideoCapture(file_path)
                temp_video_path = None
                
                if not cap.isOpened() or not cap.read()[0]:
                    if cap.isOpened():
                        cap.release()
                    # 失败则使用无中文的临时目录（解决中文路径问题）
                    ext = os.path.splitext(file_path)[1]
                    safe_dir = os.environ.get('PUBLIC', tempfile.gettempdir())
                    temp_video_path = os.path.join(safe_dir, f"temp_preview_{os.getpid()}_{hash(file_path)}{ext}")
                    try:
                        shutil.copy2(file_path, temp_video_path)
                        cap = cv2.VideoCapture(temp_video_path)
                    except Exception as e:
                        print(f"Copy to safe dir failed: {e}")
                else:
                    # 如果直接打开并且读到了第一帧，为了后续统一处理，重新打开或者seek
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                if cap.isOpened():
                    # 尝试读取帧，多读几次以跳过片头黑屏或损坏帧
                    ret, frame = cap.read()
                    if not ret:
                        for _ in range(60):
                            ret, frame = cap.read()
                            if ret: break
                            
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame.shape
                        bytes_per_line = ch * w
                        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        pm = QPixmap.fromImage(qimg.copy())
                        scaled = pm.scaled(380, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    else:
                        # 如果确实读不到帧，画一个纯黑色的兜底封面
                        scaled = QPixmap(380, 150)
                        scaled.fill(QColor(30, 30, 30))
                        
                    target = QPixmap(scaled.size())
                    target.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(target)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.drawPixmap(0, 0, scaled)
                    
                    cx = target.width() / 2
                    cy = target.height() / 2
                    painter.setBrush(QColor(0, 0, 0, 160))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(cx, cy), 20, 20)
                    
                    painter.setBrush(QColor(255, 255, 255, 255))
                    triangle = QPainterPath()
                    triangle.moveTo(cx - 4, cy - 7)
                    triangle.lineTo(cx + 8, cy)
                    triangle.lineTo(cx - 4, cy + 7)
                    triangle.closeSubpath()
                    painter.drawPath(triangle)
                    
                    # 如果是兜底封面，加上文字提示
                    if not ret:
                        painter.setPen(QColor(200, 200, 200))
                        painter.setFont(QFont("Microsoft YaHei", 10))
                        painter.drawText(target.rect(), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "无法解析视频预览")
                        
                    painter.end()
                    
                    self.preview_label.setPixmap(target)
                    self.preview_label.show()
                    self.file_label.hide()
                        
                    cap.release()
                else:
                    # 画一个纯黑色的兜底封面
                    scaled = QPixmap(380, 150)
                    scaled.fill(QColor(30, 30, 30))
                    target = QPixmap(scaled.size())
                    target.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(target)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.drawPixmap(0, 0, scaled)
                    cx = target.width() / 2
                    cy = target.height() / 2
                    painter.setBrush(QColor(0, 0, 0, 160))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(cx, cy), 20, 20)
                    painter.setBrush(QColor(255, 255, 255, 255))
                    triangle = QPainterPath()
                    triangle.moveTo(cx - 4, cy - 7)
                    triangle.lineTo(cx + 8, cy)
                    triangle.lineTo(cx - 4, cy + 7)
                    triangle.closeSubpath()
                    painter.drawPath(triangle)
                    painter.setPen(QColor(200, 200, 200))
                    painter.setFont(QFont("Microsoft YaHei", 10))
                    painter.drawText(target.rect(), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "无法解析视频预览")
                    painter.end()
                    self.preview_label.setPixmap(target)
                    self.preview_label.show()
                    self.file_label.hide()
                    
                # 清理临时文件
                if temp_video_path and os.path.exists(temp_video_path):
                    try:
                        os.remove(temp_video_path)
                    except:
                        pass
            except Exception as e:
                print(f"Video preview error: {e}")
                scaled = QPixmap(380, 150)
                scaled.fill(QColor(30, 30, 30))
                target = QPixmap(scaled.size())
                target.fill(Qt.GlobalColor.transparent)
                painter = QPainter(target)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.drawPixmap(0, 0, scaled)
                cx = target.width() / 2
                cy = target.height() / 2
                painter.setBrush(QColor(0, 0, 0, 160))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), 20, 20)
                painter.setBrush(QColor(255, 255, 255, 255))
                triangle = QPainterPath()
                triangle.moveTo(cx - 4, cy - 7)
                triangle.lineTo(cx + 8, cy)
                triangle.lineTo(cx - 4, cy + 7)
                triangle.closeSubpath()
                painter.drawPath(triangle)
                painter.setPen(QColor(200, 200, 200))
                painter.setFont(QFont("Microsoft YaHei", 10))
                painter.drawText(target.rect(), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "无法解析视频预览")
                painter.end()
                self.preview_label.setPixmap(target)
                self.preview_label.show()
                self.file_label.hide()
        
        # 强制更新布局
        self.preview_label.updateGeometry()
        self.file_label.updateGeometry()

    def on_attach_file(self):
        from PyQt6.QtWidgets import QFileDialog
        import mimetypes
        import os
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "All Files (*)")
        if files:
            self.file_paths = files
            if len(files) == 1:
                ext = os.path.splitext(files[0])[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                    self.file_type = "image"
                elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
                    self.file_type = "video"
                else:
                    self.file_type = "file"
            else:
                self.file_type = "file"
                
            self.phrase_input.hide()
            self.phrase_lbl.hide()
            
            if self.file_type in ["image", "video"]:
                self.file_label.hide()
                self.show_preview(files[0], self.file_type)
            else:
                self.preview_label.hide()
                if len(files) == 1:
                    self.file_label.setIcon(create_svg_icon(SVG_FILE, 18, "#89b4fa" if self.theme == "dark" else "#1e66f5"))
                    self.file_label.setText(f" 已选择文件: {os.path.basename(files[0])}")
                else:
                    self.file_label.setIcon(create_svg_icon(SVG_FOLDER, 18, "#89b4fa" if self.theme == "dark" else "#1e66f5"))
                    self.file_label.setText(f" 已选择 {len(files)} 个附件")
                self.file_label.show()
                
            # 无论什么类型，都显示备注输入框
            self.phrase_lbl.setText("备注:")
            self.phrase_lbl.show()
            self.phrase_input.setPlaceholderText("可以在此输入针对该附件的备注信息...")
            self.phrase_input.show()

    def get_data(self):
        if self.file_paths:
            content = self.file_paths if len(self.file_paths) > 1 else self.file_paths[0]
            t = self.file_type
        else:
            if hasattr(self, 'default_phrase') and self.file_type != "text":
                content = self.default_phrase
                t = self.file_type
            else:
                content = self.phrase_input.toPlainText().strip()
                t = "text"
            
        return {
            "scene": self.scene_combo.currentText().strip(),
            "group": self.group_combo.currentText().strip(),
            "phrase": content,
            "type": t,
            "remark": ""
        }

    def validate_and_accept(self):
        data = self.get_data()
        if not data["scene"]:
            CustomAlertDialog("提示", "请先选择或新建一个场景！", theme=self.theme, parent=self).exec()
            return
        if not data["group"]:
            CustomAlertDialog("提示", "请先选择或新建一个分组！", theme=self.theme, parent=self).exec()
            return
        if not data["phrase"]:
            CustomAlertDialog("提示", "内容不能为空！", theme=self.theme, parent=self).exec()
            return
        self.accept()

class PhraseListWidget(QListWidget):
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

class SnippetsUI(QWidget):
    phrase_clicked = pyqtSignal(dict)  # 信号：当短语被点击时，发射短语数据字典（含type和content）

    def __init__(self, theme="light", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme = theme
        self.manager = SnippetsManager()
        
        self.init_ui()
        self.load_tree()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 15, 5, 0)
        main_layout.setSpacing(6)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 5, 0)
        
        self.title_label = QLabel("快捷短语")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.title_label.setMinimumHeight(30)
        title_layout.addWidget(self.title_label, 1)
        
        from PyQt6.QtWidgets import QPushButton
        from main import SVG_CLOSE, create_svg_icon
        close_btn_snippets = QPushButton("")
        close_btn_snippets.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff" if self.theme == "dark" else "#1e1e2e"))
        close_btn_snippets.setObjectName("CloseButton")
        close_btn_snippets.setFixedSize(28, 28)
        close_btn_snippets.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn_snippets.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn_snippets.clicked.connect(self.window().hide)
        title_layout.addWidget(close_btn_snippets)
        
        main_layout.addLayout(title_layout)
        
        # 使用 QSplitter 分割左右两侧
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- 左侧：分组和场景 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 5, 10)
        left_layout.setSpacing(10)
        
        left_header = QHBoxLayout()
        left_title = QLabel("场景分组")
        left_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        left_header.addWidget(left_title)
        left_header.addStretch()
        
        self.btn_add_scene = QPushButton(" 场景")
        scene_color = "#cba6f7" if self.theme == "dark" else "#8839ef"
        self.btn_add_scene.setIcon(create_svg_icon(SVG_SCENE, 16, scene_color))
        self.btn_add_scene.setObjectName("AddSceneBtn")
        self.btn_add_scene.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_scene.clicked.connect(self.on_add_scene)
        left_header.addWidget(self.btn_add_scene)
        
        left_layout.addLayout(left_header)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(18, 18)) # 设置树形列表图标大小
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        left_layout.addWidget(self.tree)
        
        self.empty_tree_label = QLabel("暂无场景分组\n\n请点击上方按钮新建场景")
        self.empty_tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_tree_label.setFont(QFont("Microsoft YaHei", 10))
        
        border_color = "#313244" if self.theme == "dark" else "#dce0e8"
        text_color = "#a6adc8" if self.theme == "dark" else "#7c7f93"
        self.empty_tree_label.setStyleSheet(f"color: {text_color}; border: 1px solid {border_color}; border-radius: 6px;")
        
        self.empty_tree_label.hide()
        left_layout.addWidget(self.empty_tree_label)
        
        self.btn_add_group = QPushButton(" 分组")
        group_color = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        self.btn_add_group.setIcon(create_svg_icon(SVG_FOLDER, 16, group_color))
        self.btn_add_group.setObjectName("AddGroupBtn")
        self.btn_add_group.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_group.clicked.connect(self.on_add_group)
        left_layout.addWidget(self.btn_add_group)
        
        # --- 右侧：短语列表 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 15, 0, 0)
        right_layout.setSpacing(6)
        
        right_header = QHBoxLayout()
        right_header.setContentsMargins(0, 0, 8, 0)
        self.right_title = QLabel("短语列表")
        self.right_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        self.btn_add_phrase = QPushButton(" 新建短语")
        self.btn_add_phrase.setIcon(create_svg_icon(SVG_PLUS, 16, "#11111b" if self.theme == "dark" else "#ffffff"))
        self.btn_add_phrase.setObjectName("AddPhraseBtn")
        self.btn_add_phrase.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_phrase.clicked.connect(self.on_add_phrase)
        
        right_header.addWidget(self.right_title)
        right_header.addStretch()
        right_header.addWidget(self.btn_add_phrase)
        
        right_layout.addLayout(right_header)
        
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(16, 8, 8, 8)
        search_layout.setSpacing(8)

        from main import SVG_SEARCH
        self.search_icon_label = QLabel()
        self.search_icon_label.setPixmap(create_svg_icon(SVG_SEARCH, 16, "#cdd6f4" if self.theme == "dark" else "#4c4f69").pixmap(16, 16))
        self.search_icon_label.setObjectName("SearchIcon")
        search_layout.addWidget(self.search_icon_label)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("搜索短语...")
        self.search_input.setMinimumHeight(28)
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.search_scope_combo = QComboBox()
        self.search_scope_combo.setObjectName("FilterCombo")
        self.search_scope_combo.addItem("全局搜索", "all")
        # 默认只显示全局搜索，根据左侧选中状态动态添加/显示当前场景、当前分组
        self.search_scope_combo.setMinimumHeight(28)
        self.search_scope_combo.setMinimumWidth(85)
        # currentIndexChanged.connect trigger causes focus loss / interaction issues
        # Use activated to only trigger when user selects, avoiding programmatic loop
        self.search_scope_combo.activated.connect(self._on_combo_activated)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_scope_combo)
        
        self.search_container = QWidget()
        self.search_container.setObjectName("SearchContainer")
        self.search_container.setLayout(search_layout)

        search_wrapper = QHBoxLayout()
        search_wrapper.setContentsMargins(0, 0, 8, 0)
        search_wrapper.addWidget(self.search_container)
        
        right_layout.addLayout(search_wrapper)
        
        self.phrase_list = PhraseListWidget()
        self.phrase_list.setObjectName("PhraseListWidget")
        self.phrase_list.setContentsMargins(0, 0, 0, 0)
        self.phrase_list.setSpacing(6)
        self.phrase_list.setIconSize(QSize(16, 16))
        self.phrase_list.setWordWrap(True)
        self.phrase_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.phrase_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.phrase_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.phrase_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.phrase_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.phrase_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.phrase_list.setFrameShape(QFrame.Shape.NoFrame)
        self.phrase_list.setFrameShadow(QFrame.Shadow.Plain)
        self.phrase_list.setLineWidth(0)
        self.phrase_list.viewport().setAutoFillBackground(False)
        self.phrase_list.viewport().setStyleSheet("background-color: transparent;")
        self.phrase_list.setStyleSheet("QListWidget { padding-right: 6px; border: none; outline: none; background: transparent; } QListWidget::item { border: none; outline: none; } QListWidget::item:focus { border: none; outline: none; }")
        self.phrase_list.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        
        self.phrase_list.customContextMenuRequested.connect(self.on_phrase_context_menu)
        self.phrase_list.itemClicked.connect(self.on_phrase_clicked)
        
        # 添加占位提示标签，放在短语列表所在的位置
        from PyQt6.QtWidgets import QStackedWidget
        self.right_stack = QStackedWidget()
        
        # 页面0：提示文字
        self.empty_hint_label = QLabel("暂无场景分组\n\n请点击左上角按钮新建场景" if not self.manager.get_scenes() else "请在左侧选择一个场景分组")
        self.empty_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint_label.setFont(QFont("Microsoft YaHei", 12))
        self.right_stack.addWidget(self.empty_hint_label)
        
        # 页面1：真实的短语列表
        self.right_stack.addWidget(self.phrase_list)
        
        right_layout.addWidget(self.right_stack)
        
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([150, 250])
        
        main_layout.addWidget(self.splitter)
        self.update_theme(self.theme)

    def update_theme(self, theme):
        try:
            from main import SVG_CLOSE, create_svg_icon
        except ImportError:
            pass
            
        self.theme = theme
        
        if hasattr(self, 'empty_tree_label'):
            border_color = "#313244" if self.theme == "dark" else "#dce0e8"
            text_color = "#a6adc8" if self.theme == "dark" else "#7c7f93"
            self.empty_tree_label.setStyleSheet(f"color: {text_color}; border: 1px solid {border_color}; border-radius: 6px;")
        
        # 更新按钮图标颜色
        scene_color = "#cba6f7" if self.theme == "dark" else "#8839ef"
        group_color = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        self.btn_add_group.setIcon(create_svg_icon(SVG_FOLDER, 16, group_color))
        self.btn_add_scene.setIcon(create_svg_icon(SVG_SCENE, 16, scene_color))
        self.btn_add_phrase.setIcon(create_svg_icon(SVG_PLUS, 16, "#11111b" if self.theme == "dark" else "#ffffff"))
        
        # 刷新所有项目的theme
        if hasattr(self, 'phrase_list'):
            for i in range(self.phrase_list.count()):
                item = self.phrase_list.item(i)
                widget = self.phrase_list.itemWidget(item)
                if hasattr(widget, 'update_theme'):
                    widget.update_theme(theme)
                    
        # 刷新树控件的theme
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            widget = self.tree.itemWidget(item, 0)
            if hasattr(widget, 'update_theme'):
                widget.update_theme(theme)
            iterator += 1
        
        # 刷新子窗口的关闭按钮颜色
        close_btn = self.findChild(QPushButton, "CloseButton")
        if close_btn:
            close_btn.setIcon(create_svg_icon(SVG_CLOSE, 16, "#ffffff" if self.theme == "dark" else "#1e1e2e"))
        
        if theme == "dark":
            self.setStyleSheet("""
                SnippetsUI {
                    background-color: transparent;
                }
                QTreeWidget {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding-right: 10px;
                }
                QTreeWidget::item {
                    padding: 4px;
                    color: #cdd6f4;
                }
                QTreeWidget::item:selected {
                    background-color: #313244;
                    color: #cdd6f4;
                }
                QListWidget {
                    border: 0px;
                    outline: 0px;
                    background-color: transparent;
                    padding-right: 10px;
                }
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 14px;
                    margin: 0px;
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
                    border: none;
                    background: transparent;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
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
                QLabel { color: #cdd6f4; }
                QPushButton#AddGroupBtn, QPushButton#AddSceneBtn {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton#AddGroupBtn:hover, QPushButton#AddSceneBtn:hover {
                    background-color: #45475a;
                }
                QPushButton#AddPhraseBtn {
                    background-color: #89b4fa;
                    color: #11111b;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton#AddPhraseBtn:hover {
                    background-color: #b4befe;
                }
                #TitleLabel {
                    color: #cdd6f4;
                }
                QLineEdit {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLineEdit:focus {
                    border: 1px solid #89b4fa;
                }
                QComboBox {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 6px;
                    padding: 4px 8px;
                    padding-right: 20px;
                }
                QComboBox:hover {
                    border: 1px solid #89b4fa;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 24px;
                }
                QComboBox::down-arrow {
                    image: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    color: #cdd6f4;
                    selection-background-color: rgba(137, 180, 250, 0.15);
                    outline: none;
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
                }
                #FilterCombo {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    border-left: 1px solid #45475a;
                    padding: 4px 8px;
                    padding-right: 20px;
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
                QSplitter::handle {
                    background-color: transparent;
                }
            """)
            self.empty_hint_label.setStyleSheet("color: #6c7086;")
        else:
            self.setStyleSheet("""
                SnippetsUI {
                    background-color: transparent;
                }
                QTreeWidget {
                    background-color: transparent;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 6px;
                    padding-right: 10px;
                }
                QTreeWidget::item {
                    padding: 4px;
                    color: #4c4f69;
                }
                QTreeWidget::item:selected {
                    background-color: #ccd0da;
                    color: #4c4f69;
                }
                QListWidget {
                    border: 0px;
                    outline: 0px;
                    background-color: transparent;
                    padding-right: 10px;
                }
                QScrollBar:vertical {
                    border: none;
                    background: transparent;
                    width: 14px;
                    margin: 0px;
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
                    border: none;
                    background: transparent;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
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
                QLabel { color: #4c4f69; }
                QPushButton#AddGroupBtn, QPushButton#AddSceneBtn {
                    background-color: #e6e9ef;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton#AddGroupBtn:hover, QPushButton#AddSceneBtn:hover {
                    background-color: #ccd0da;
                }
                QPushButton#AddPhraseBtn {
                    background-color: #1e66f5;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton#AddPhraseBtn:hover {
                    background-color: #89b4fa;
                }
                #TitleLabel {
                    color: #4c4f69;
                }
                QLineEdit {
                    background-color: #f2f4f8;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLineEdit:focus {
                    border: 1px solid #1e66f5;
                }
                QComboBox {
                    background-color: #f2f4f8;
                    color: #4c4f69;
                    border: 1px solid #dce0e8;
                    border-radius: 6px;
                    padding: 4px 8px;
                    padding-right: 20px;
                }
                QComboBox:hover {
                    border: 1px solid #1e66f5;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 24px;
                }
                QComboBox::down-arrow {
                    image: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    border: 1px solid #dce0e8;
                    border-radius: 4px;
                    color: #4c4f69;
                    selection-background-color: rgba(30, 102, 245, 0.1);
                    outline: none;
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
                }
                #FilterCombo {
                    background-color: transparent;
                    color: #4c4f69;
                    border: none;
                    border-left: 1px solid #ccd0da;
                    padding: 4px 8px;
                    padding-right: 20px;
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
                    background-color: #ffffff;
                    border: 1px solid #dce0e8;
                    border-radius: 4px;
                    color: #4c4f69;
                    selection-background-color: rgba(30, 102, 245, 0.1);
                    outline: none;
                }
                QSplitter::handle {
                    background-color: transparent;
                }
            """)
            self.empty_hint_label.setStyleSheet("color: #8c8fa1;")

    def load_tree(self):
        self.tree.clear()
        scenes = self.manager.get_scenes()
        
        if not scenes:
            self.tree.hide()
            self.empty_tree_label.show()
        else:
            self.tree.show()
            self.empty_tree_label.hide()
            
        scene_color = "#cba6f7" if self.theme == "dark" else "#8839ef"
        group_color = "#89b4fa" if self.theme == "dark" else "#1e66f5"
        for s in scenes:
            s_item = QTreeWidgetItem([s["name"]])
            s_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "scene", "id": s["id"]})
            s_item.setIcon(0, create_svg_icon(SVG_SCENE, 18, scene_color))
            for g in s.get("groups", []):
                g_item = QTreeWidgetItem([g["name"]])
                g_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "id": g["id"], "scene_id": s["id"]})
                g_item.setIcon(0, create_svg_icon(SVG_FOLDER, 18, group_color))
                s_item.addChild(g_item)
            self.tree.addTopLevelItem(s_item)
        self.tree.expandAll()

    def _render_phrases(self, phrases):
        from PyQt6.QtGui import QImage, QPainterPath
        from PyQt6.QtCore import QTimer
        
        class PhraseItemWidget(QWidget):
            def __init__(self, ui_instance, list_item, phrase_data, theme="light"):
                super().__init__()
                self.ui_instance = ui_instance
                self.list_item = list_item
                self.phrase_data = phrase_data
                self.theme = theme
                self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                
                item_type = phrase_data.get("type", "text")
                content = phrase_data["content"]
                remark = phrase_data.get("remark", "")
                
                self.setObjectName("PhraseCard")
                self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                self.setProperty("hover", False)
                
                card_bg = "#313244" if theme == "dark" else "#ffffff"
                card_hover = "#45475a" if theme == "dark" else "#f2f4f8"
                border_color = "#313244" if theme == "dark" else "#e6e9ef"
                hover_border = "#89b4fa" if theme == "dark" else "#b4befe"
                
                self.setStyleSheet(f"""
                    #PhraseCard {{ background-color: {card_bg}; border-radius: 10px; border: 1px solid {border_color}; }}
                    #PhraseCard[hover="true"] {{ background-color: {card_hover}; border: 1px solid {hover_border}; }}
                """)
                
                layout = QVBoxLayout(self)
                layout.setContentsMargins(16, 12, 16, 12)
                layout.setSpacing(8)
                
                import os
                display_text = ""
                pixmap = None
                video_path = None
                image_path = None
                
                # -------------------------
                # 1. 顶部 Header (图标 + 时间/提示 + 操作按钮)
                # -------------------------
                header_layout = QHBoxLayout()
                header_layout.setSpacing(8)
                
                type_icon = QLabel()
                type_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                
                if item_type == "image":
                    display_text = f"[图片] {os.path.basename(content) if isinstance(content, str) else ''}"
                    image_path = content
                    icon_color = "#a6e3a1" if theme == "dark" else "#40a02b"
                    type_icon.setPixmap(create_svg_icon(SVG_IMAGE, 14, icon_color).pixmap(14, 14))
                elif item_type == "video":
                    display_text = f"[视频] {os.path.basename(content) if isinstance(content, str) else ''}"
                    video_path = content
                    icon_color = "#f9e2af" if theme == "dark" else "#df8e1d"
                    type_icon.setPixmap(create_svg_icon(SVG_PLAY, 14, icon_color).pixmap(14, 14))
                elif item_type == "file":
                    if isinstance(content, list):
                        display_text = f"[文件] {os.path.basename(content[0])} 等{len(content)}个文件"
                    else:
                        display_text = f"[文件] {os.path.basename(content)}"
                    icon_color = "#89b4fa" if theme == "dark" else "#1e66f5"
                    type_icon.setPixmap(create_svg_icon(SVG_FILE, 14, icon_color).pixmap(14, 14))
                else:
                    display_text = content
                    icon_color = "#89b4fa" if theme == "dark" else "#1e66f5"
                    type_icon.setPixmap(create_svg_icon(SVG_PHRASE, 14, icon_color).pixmap(14, 14))
                    
                header_layout.addWidget(type_icon)
                header_layout.addStretch()
                
                # 仅在搜索结果中显示该短语所属的场景和分组（右对齐显示）
                if phrase_data.get("_is_search") and phrase_data.get("_scene_name") and phrase_data.get("_group_name"):
                    time_text = f"{phrase_data['_scene_name']} > {phrase_data['_group_name']}"
                    time_lbl = QLabel(time_text)
                    time_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    time_lbl.setFont(QFont("Microsoft YaHei", 9))
                    if theme == "dark":
                        time_lbl.setStyleSheet("color: #a6adc8;")
                    else:
                        time_lbl.setStyleSheet("color: #9ca0b0;")
                    header_layout.addWidget(time_lbl)
                    
                # 显示创建日期
                timestamp = phrase_data.get("created_at")
                if timestamp:
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                    date_lbl = QLabel(date_str)
                    date_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    date_lbl.setFont(QFont("Microsoft YaHei", 9))
                    if theme == "dark":
                        date_lbl.setStyleSheet("color: #a6adc8; margin-left: 8px;")
                    else:
                        date_lbl.setStyleSheet("color: #9ca0b0; margin-left: 8px;")
                    header_layout.addWidget(date_lbl)
                
                # 右侧操作按钮组 (Hover时显示)
                self.btn_container = QWidget()
                self.btn_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                btn_layout = QHBoxLayout(self.btn_container)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                btn_layout.setSpacing(4)
                
                if item_type in ["text", "file", "image", "video"]:
                    edit_btn = QPushButton()
                    btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    edit_btn.setIcon(create_svg_icon(SVG_EDIT, 14, btn_color))
                    edit_btn.setFixedSize(24, 24)
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    edit_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(137, 180, 250, 0.2)' if theme == 'dark' else 'rgba(30, 102, 245, 0.1)'}; }}")
                    edit_btn.clicked.connect(lambda: self.ui_instance.on_phrase_context_menu_action("edit", self.list_item, self.phrase_data))
                    btn_layout.addWidget(edit_btn)
                
                del_btn = QPushButton()
                del_btn.setIcon(create_svg_icon(SVG_TRASH, 14, "#f38ba8" if theme == "dark" else "#d20f39"))
                del_btn.setFixedSize(24, 24)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                del_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; border-radius: 4px; }} QPushButton:hover {{ background-color: {'rgba(243, 139, 168, 0.2)' if theme == 'dark' else 'rgba(210, 15, 57, 0.1)'}; }}")
                del_btn.clicked.connect(lambda: self.ui_instance.on_phrase_context_menu_action("delete", self.list_item, self.phrase_data))
                btn_layout.addWidget(del_btn)
                
                self.btn_container.hide()
                sp = self.btn_container.sizePolicy()
                sp.setRetainSizeWhenHidden(True)
                self.btn_container.setSizePolicy(sp)
                
                header_layout.addWidget(self.btn_container)
                layout.addLayout(header_layout)
                
                # -------------------------
                # 2. 预处理媒体资源
                # -------------------------
                if item_type == "video":
                    if not hasattr(self.ui_instance, 'thumbnail_cache'):
                        self.ui_instance.thumbnail_cache = {}
                    if video_path in self.ui_instance.thumbnail_cache:
                        pixmap = self.ui_instance.thumbnail_cache[video_path]
                    else:
                        try:
                            import cv2
                            cap = cv2.VideoCapture(video_path)
                            if cap.isOpened():
                                cap.set(cv2.CAP_PROP_POS_FRAMES, min(30, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)/2)))
                                ret, frame = cap.read()
                                if not ret:
                                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                    ret, frame = cap.read()
                                if ret:
                                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                    h, w, ch = frame.shape
                                    bytes_per_line = ch * w
                                    qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                                    base_pixmap = QPixmap.fromImage(qimg.copy())
                                    
                                    pixmap = QPixmap(base_pixmap.size())
                                    pixmap.fill(Qt.GlobalColor.transparent)
                                    painter = QPainter(pixmap)
                                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                                    painter.drawPixmap(0, 0, base_pixmap)
                                    
                                    cx = pixmap.width() / 2
                                    cy = pixmap.height() / 2
                                    painter.setBrush(QColor(0, 0, 0, 160))
                                    painter.setPen(Qt.PenStyle.NoPen)
                                    painter.drawEllipse(QPointF(cx, cy), 28, 28)
                                    
                                    painter.setBrush(QColor(255, 255, 255, 255))
                                    triangle = QPainterPath()
                                    triangle.moveTo(cx - 6, cy - 10)
                                    triangle.lineTo(cx + 12, cy)
                                    triangle.lineTo(cx - 6, cy + 10)
                                    triangle.closeSubpath()
                                    painter.drawPath(triangle)
                                    painter.end()
                                    
                                    self.ui_instance.thumbnail_cache[video_path] = pixmap
                                cap.release()
                        except Exception:
                            if 'painter' in locals() and painter.isActive():
                                painter.end()
                            pass
                elif item_type == "file":
                    if isinstance(content, list):
                        display_text = f"[文件] {os.path.basename(content[0])} 等{len(content)}个文件"
                    else:
                        display_text = f"[文件] {os.path.basename(content)}"
                else:
                    display_text = content
                
                if item_type != "text" and remark:
                    display_text += f" - {remark}"
                    
                # 文本标题
                text_lbl = QLabel(display_text)
                text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                text_lbl.setFont(QFont("Microsoft YaHei", 10))
                text_lbl.setWordWrap(True)
                text_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                text_lbl.setStyleSheet(f"color: {'#cdd6f4' if theme == 'dark' else '#4c4f69'}; line-height: 1.4;")
                layout.addWidget(text_lbl)
                
                # 媒体预览区域
                if image_path or pixmap:
                    class ClickableLabel(QLabel):
                        singleClicked = pyqtSignal()
                        def mouseReleaseEvent(self, event):
                            if event.button() == Qt.MouseButton.LeftButton:
                                self.singleClicked.emit()
                                event.accept()
                            else:
                                super().mouseReleaseEvent(event)
                    
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
                        
                        # 单击图片：触发点击事件
                        img_lbl.singleClicked.connect(lambda: self.ui_instance.on_phrase_clicked(self.list_item))
                        layout.addWidget(img_lbl)
                    else:
                        if item_type == "image":
                            img_lbl.setText("[图片已失效]")
                            img_lbl.setStyleSheet("color: #a6adc8; font-style: italic;")
                            layout.addWidget(img_lbl)
                            
            def update_theme(self, theme):
                self.theme = theme
                card_bg = "#313244" if theme == "dark" else "#ffffff"
                card_hover = "#45475a" if theme == "dark" else "#f2f4f8"
                border_color = "#313244" if theme == "dark" else "#dce0e8"
                hover_border = "#89b4fa" if theme == "dark" else "#b4befe"
                
                self.setStyleSheet(f"""
                    #PhraseCard {{ background-color: {card_bg}; border-radius: 10px; border: 1px solid {border_color}; }}
                    #PhraseCard[hover="true"] {{ background-color: {card_hover}; border: 1px solid {hover_border}; }}
                """)
                self.style().unpolish(self)
                self.style().polish(self)
                
                text_color = "#cdd6f4" if theme == "dark" else "#4c4f69"
                remark_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                
                # Update inner elements if they exist
                for child in self.findChildren(QLabel):
                    if child.font().pointSize() == 10:
                        child.setStyleSheet(f"color: {text_color}; line-height: 1.4;")
                
                # Update buttons
                btn_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                hover_color = 'rgba(137, 180, 250, 0.2)' if theme == 'dark' else 'rgba(30, 102, 245, 0.1)'
                for btn_name in ['copy_btn', 'edit_btn', 'del_btn']:
                    if hasattr(self, btn_name):
                        btn = getattr(self, btn_name)
                        icon_svg = SVG_CLIPBOARD if btn_name == 'copy_btn' else (SVG_EDIT if btn_name == 'edit_btn' else SVG_TRASH)
                        if btn_name == 'del_btn':
                            icon_color = "#f38ba8" if theme == "dark" else "#d20f39"
                            btn.setIcon(create_svg_icon(icon_svg, 16, icon_color))
                            btn.setStyleSheet(f"QPushButton {{ background: transparent; border-radius: 6px; padding: 6px; }} QPushButton:hover {{ background-color: {'rgba(243, 139, 168, 0.2)' if theme == 'dark' else 'rgba(210, 15, 57, 0.1)'}; }}")
                        else:
                            btn.setIcon(create_svg_icon(icon_svg, 16, btn_color))
                            btn.setStyleSheet(f"QPushButton {{ background: transparent; border-radius: 6px; padding: 6px; }} QPushButton:hover {{ background-color: {hover_color}; }}")
            
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
                
            def mouseReleaseEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    if hasattr(self, 'btn_container') and self.btn_container.isVisible():
                        btn_pos = event.globalPosition().toPoint()
                        for btn in self.btn_container.findChildren(QPushButton):
                            if btn.isVisible():
                                btn_global_pos = btn.mapToGlobal(QPoint(0, 0))
                                btn_global_rect = btn.rect().translated(btn_global_pos)
                                if btn_global_rect.contains(btn_pos):
                                    return
                                    
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.ui_instance.on_phrase_clicked(self.list_item))
                    event.accept()

        for p in phrases:
            p_item = QListWidgetItem()
            p_item.setData(Qt.ItemDataRole.UserRole, p)
            
            widget = PhraseItemWidget(self, p_item, p, theme=self.theme)
            viewport_width = self.phrase_list.viewport().width() - 12
            if viewport_width > 0:
                widget.setFixedWidth(viewport_width)
            
            self.phrase_list.addItem(p_item)
            p_item.setSizeHint(widget.sizeHint())
            self.phrase_list.setItemWidget(p_item, widget)

    def _on_combo_activated(self, index):
        """专门处理下拉框用户手动点击选择事件"""
        # 如果搜索框为空，用户切换下拉框时，尝试在左侧树结构跳转
        text = self.search_input.text().strip()
        scope = self.search_scope_combo.itemData(index)
        
        if not text:
            if not getattr(self, '_updating_combo_programmatically', False):
                self._updating_combo_programmatically = True
                
                # 当下拉框被选择且搜索框为空时，强制更新一下树的选择，
                # 但要注意阻止它又触发回 on_tree_selection_changed，虽然 clearSelection 会触发一次，但没关系
                if scope == "all":
                    self.tree.clearSelection()
                elif scope == "scene":
                    # 获取当前选中项（如果有）
                    selected_items = self.tree.selectedItems()
                    if selected_items:
                        item = selected_items[0]
                        data = item.data(0, Qt.ItemDataRole.UserRole)
                        if data["type"] == "group":
                            parent = item.parent()
                            if parent:
                                self.tree.clearSelection()
                                self.tree.setCurrentItem(parent)
                                parent.setSelected(True)
                    else:
                        # 如果当前什么都没选，但下拉了“当前场景”，则选中第一个场景
                        if self.tree.topLevelItemCount() > 0:
                            first_scene = self.tree.topLevelItem(0)
                            self.tree.clearSelection()
                            self.tree.setCurrentItem(first_scene)
                            first_scene.setSelected(True)
                elif scope == "group":
                    selected_items = self.tree.selectedItems()
                    if selected_items:
                        item = selected_items[0]
                        data = item.data(0, Qt.ItemDataRole.UserRole)
                        # 如果当前选中了场景，切换到分组，我们需要选中它的第一个子分组（如果有的话）
                        if data["type"] == "scene":
                            if item.childCount() > 0:
                                first_child = item.child(0)
                                self.tree.clearSelection()
                                self.tree.setCurrentItem(first_child)
                                first_child.setSelected(True)
                    else:
                        # 如果什么都没选，切到分组，选中第一个场景的第一个分组
                        if self.tree.topLevelItemCount() > 0:
                            first_scene = self.tree.topLevelItem(0)
                            if first_scene.childCount() > 0:
                                first_group = first_scene.child(0)
                                self.tree.clearSelection()
                                self.tree.setCurrentItem(first_group)
                                first_group.setSelected(True)
                    
                self._updating_combo_programmatically = False
        else:
            # 搜索框有内容时触发重新搜索
            self.on_search_changed(text)

    def on_search_changed(self, text):
        if getattr(self, '_updating_combo_programmatically', False):
            return
            
        query = text.strip().lower()
        
        # 获取当前的搜索范围
        scope = self.search_scope_combo.currentData()
        
        # 即使查询为空，如果是修改了下拉框条件也应该响应，
        # 所以我们去掉对空 query 就直接返回的限制。
        # 但如果是真的什么都没搜，并且下拉框也不是"全局搜索"时，应该恢复左侧树选择的状态。
        if not query:
            # 只有当之前有搜索内容现在清空了，或者当前是在搜索状态，才恢复树的视图
            if getattr(self, '_last_search_query', '') != '' or self.right_title.text() == "搜索结果":
                self._last_search_query = ''
                self.on_tree_selection_changed()
            return
            
        self._last_search_query = query
        self.phrase_list.clear()
        self.right_title.setText("搜索结果")
        self.right_stack.setCurrentIndex(1)
        
        current_scene_id = None
        current_group_id = None
        
        selected = self.tree.selectedItems()
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data["type"] == "group":
                current_scene_id = data["scene_id"]
                current_group_id = data["id"]
            elif data["type"] == "scene":
                current_scene_id = data["id"]
        
        phrases = []
        for s in self.manager.get_scenes():
            if scope in ("scene", "group") and current_scene_id and s["id"] != current_scene_id:
                continue
                
            for g in s.get("groups", []):
                if scope == "group" and current_group_id and g["id"] != current_group_id:
                    continue
                    
                for p in g.get("phrases", []):
                    content = p.get("content", "")
                    remark = p.get("remark", "")
                    content_str = str(content).lower()
                    remark_str = remark.lower()
                    scene_str = str(s.get("name", "")).lower()
                    group_str = str(g.get("name", "")).lower()
                    if query in content_str or query in remark_str or query in scene_str or query in group_str:
                        p_copy = p.copy()
                        p_copy["_scene_id"] = s["id"]
                        p_copy["_group_id"] = g["id"]
                        p_copy["_scene_name"] = s["name"]
                        p_copy["_group_name"] = g["name"]
                        p_copy["_is_search"] = True
                        phrases.append(p_copy)
                        
        self._render_phrases(phrases)

    def on_tree_selection_changed(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        
        selected = self.tree.selectedItems()
        self.phrase_list.clear()
        
        # 恢复默认提示文本
        if not self.manager.get_scenes():
            self.empty_hint_label.setText("暂无场景分组\n\n请点击左上角按钮新建场景")
        else:
            self.empty_hint_label.setText("请在左侧选择一个场景分组")
            
        # 动态更新下拉框选项
        self._updating_combo_programmatically = True
        self.search_scope_combo.blockSignals(True)
        self.search_scope_combo.clear()
        self.search_scope_combo.addItem("全局搜索", "all")
        
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data["type"] == "scene":
                self.search_scope_combo.addItem("当前场景", "scene")
            elif data["type"] == "group":
                self.search_scope_combo.addItem("当前分组", "group")
                self.search_scope_combo.addItem("当前场景", "scene")
        self.search_scope_combo.blockSignals(False)
        self._updating_combo_programmatically = False
        
        if not selected:
            self.right_title.setText("短语列表")
            self.right_stack.setCurrentIndex(0)  # 显示提示
            
            # 当没有选中任何项时，默认设置搜索范围为“全局搜索”
            if not getattr(self, '_updating_combo_programmatically', False):
                self._updating_combo_programmatically = True
                self.search_scope_combo.blockSignals(True)
                idx = self.search_scope_combo.findData("all")
                if idx >= 0 and self.search_scope_combo.currentIndex() != idx:
                    self.search_scope_combo.setCurrentIndex(idx)
                self.search_scope_combo.blockSignals(False)
                self._updating_combo_programmatically = False
            return
            
        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        # 自动切换搜索范围 (仅在搜索框为空时自动切换，避免打断用户的筛选意图)
        if not hasattr(self, 'search_input') or not self.search_input.text().strip():
            if not getattr(self, '_updating_combo_programmatically', False):
                # 标记我们正在进行程序内部更新下拉框，不触发搜索回调
                self._updating_combo_programmatically = True
                
                # 直接根据当前的 item type 去设置下拉框状态
                if data["type"] == "group":
                    idx = self.search_scope_combo.findData("group")
                    if idx >= 0 and self.search_scope_combo.currentIndex() != idx:
                        self.search_scope_combo.blockSignals(True)
                        self.search_scope_combo.setCurrentIndex(idx)
                        self.search_scope_combo.blockSignals(False)
                elif data["type"] == "scene":
                    idx = self.search_scope_combo.findData("scene")
                    if idx >= 0 and self.search_scope_combo.currentIndex() != idx:
                        self.search_scope_combo.blockSignals(True)
                        self.search_scope_combo.setCurrentIndex(idx)
                        self.search_scope_combo.blockSignals(False)
                        
                self._updating_combo_programmatically = False
                
        if data["type"] == "group":
            self.right_title.setText(f"{item.text(0)} - 短语")
            self.right_stack.setCurrentIndex(1)  # 显示列表
            phrases = self.manager.get_phrases(data["scene_id"], data["id"])
            scene_name = item.parent().text(0) if item.parent() else ""
            group_name = item.text(0)
            enhanced_phrases = []
            for p in phrases:
                p_copy = p.copy()
                p_copy["_scene_id"] = data["scene_id"]
                p_copy["_group_id"] = data["id"]
                p_copy["_scene_name"] = scene_name
                p_copy["_group_name"] = group_name
                enhanced_phrases.append(p_copy)
            self._render_phrases(enhanced_phrases)
        elif data["type"] == "scene":
            self.right_title.setText(f"{item.text(0)} - 分组列表")
            self.right_stack.setCurrentIndex(1)  # 显示列表
            
            scene_id = data["id"]
            groups = []
            for s in self.manager.get_scenes():
                if s["id"] == scene_id:
                    groups = s.get("groups", [])
                    break
                    
            if not groups:
                self.empty_hint_label.setText("当前场景暂无分组，请先新建分组")
                self.right_stack.setCurrentIndex(0)
                return
                
            from PyQt6.QtCore import QTimer
            class GroupItemWidget(QWidget):
                def __init__(self, ui_instance, list_item, group_data, theme="light"):
                    super().__init__()
                    self.ui_instance = ui_instance
                    self.list_item = list_item
                    self.group_data = group_data
                    self.theme = theme
                    self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    
                    self.setObjectName("GroupCard")
                    self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                    self.setProperty("hover", False)
                    
                    card_bg = "#313244" if theme == "dark" else "#ffffff"
                    card_hover = "#45475a" if theme == "dark" else "#f2f4f8"
                    border_color = "#313244" if theme == "dark" else "#dce0e8"
                    hover_border = "#89b4fa" if theme == "dark" else "#b4befe"
                    
                    self.setStyleSheet(f"""
                        #GroupCard {{ background-color: {card_bg}; border-radius: 10px; border: 1px solid {border_color}; }}
                        #GroupCard[hover="true"] {{ background-color: {card_hover}; border: 1px solid {hover_border}; }}
                    """)
                    
                    layout = QHBoxLayout(self)
                    layout.setContentsMargins(16, 16, 16, 16)
                    layout.setSpacing(16)
                    
                    folder_icon = QLabel()
                    icon_color = "#89b4fa" if theme == "dark" else "#1e66f5"
                    folder_icon.setPixmap(create_svg_icon(SVG_FOLDER, 28, icon_color).pixmap(28, 28))
                    layout.addWidget(folder_icon)
                    
                    name_layout = QVBoxLayout()
                    name_layout.setSpacing(4)
                    name_layout.setContentsMargins(0, 0, 0, 0)
                    
                    name_lbl = QLabel(group_data["name"])
                    name_lbl.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
                    name_lbl.setStyleSheet(f"color: {'#cdd6f4' if theme == 'dark' else '#4c4f69'};")
                    name_layout.addWidget(name_lbl)
                    
                    count_lbl = QLabel(f"{group_data.get('phrase_count', 0)} 个短语")
                    count_lbl.setFont(QFont("Microsoft YaHei", 9))
                    count_lbl.setStyleSheet(f"color: {'#a6adc8' if theme == 'dark' else '#8c8fa1'};")
                    name_layout.addWidget(count_lbl)
                    
                    layout.addLayout(name_layout)
                    layout.addStretch()
                    
                    arrow_lbl = QLabel(">")
                    arrow_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
                    arrow_lbl.setStyleSheet("color: #8c8fa1;")
                    layout.addWidget(arrow_lbl)
                    
                def update_theme(self, theme):
                    self.theme = theme
                    card_bg = "#313244" if theme == "dark" else "#ffffff"
                    card_hover = "#45475a" if theme == "dark" else "#f2f4f8"
                    border_color = "#313244" if theme == "dark" else "#dce0e8"
                    hover_border = "#89b4fa" if theme == "dark" else "#b4befe"
                    
                    self.setStyleSheet(f"""
                        #GroupCard {{ background-color: {card_bg}; border-radius: 10px; border: 1px solid {border_color}; }}
                        #GroupCard[hover="true"] {{ background-color: {card_hover}; border: 1px solid {hover_border}; }}
                    """)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    
                    # Update internal elements
                    text_color = "#cdd6f4" if theme == "dark" else "#4c4f69"
                    sub_color = "#a6adc8" if theme == "dark" else "#8c8fa1"
                    icon_color = "#89b4fa" if theme == "dark" else "#1e66f5"
                    for child in self.findChildren(QLabel):
                        if child.font().pointSize() == 11:
                            child.setStyleSheet(f"color: {text_color};")
                        elif child.font().pointSize() == 9:
                            child.setStyleSheet(f"color: {sub_color};")
                        elif child.pixmap() and not child.pixmap().isNull():
                            child.setPixmap(create_svg_icon(SVG_FOLDER, 28, icon_color).pixmap(28, 28))
                    
                def enterEvent(self, event):
                    self.setProperty("hover", True)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    super().enterEvent(event)
                    
                def leaveEvent(self, event):
                    self.setProperty("hover", False)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    super().leaveEvent(event)
                    
                def mouseReleaseEvent(self, event):
                    if event.button() == Qt.MouseButton.LeftButton:
                        QTimer.singleShot(0, lambda: self.ui_instance.on_phrase_clicked(self.list_item))
                        event.accept()

            for g in groups:
                g_item = QListWidgetItem()
                phrase_count = len(g.get("phrases", []))
                g_data = {"type": "group_nav", "id": g["id"], "scene_id": scene_id, "name": g["name"], "phrase_count": phrase_count}
                g_item.setData(Qt.ItemDataRole.UserRole, g_data)
                
                widget = GroupItemWidget(self, g_item, g_data, theme=self.theme)
                viewport_width = self.phrase_list.viewport().width() - 12
                if viewport_width > 0:
                    widget.setFixedWidth(viewport_width)
                self.phrase_list.addItem(g_item)
                g_item.setSizeHint(widget.sizeHint())
                self.phrase_list.setItemWidget(g_item, widget)
        else:
            self.right_title.setText("短语列表")
            self.right_stack.setCurrentIndex(0)  # 显示提示

    def on_add_scene(self):
        dialog = CustomInputDialog("新建场景", "请输入场景名称:", theme=self.theme, parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if name.strip():
                self.manager.add_scene(name.strip())
                self.load_tree()

    def on_add_group(self):
        if not self.manager.get_scenes():
            CustomAlertDialog("提示", "当前没有任何场景，请先新建场景！", theme=self.theme, parent=self).exec()
            return
            
        selected = self.tree.selectedItems()
        if not selected:
            CustomAlertDialog("提示", "请先在左侧选择一个场景！", theme=self.theme, parent=self).exec()
            return
        
        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        scene_id = data["id"] if data["type"] == "scene" else data["scene_id"]
        
        dialog = CustomInputDialog("新建分组", "请输入分组名称:", theme=self.theme, parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if name.strip():
                self.manager.add_group(scene_id, name.strip())
                self.load_tree()

    def on_add_phrase(self):
        # 尝试获取当前选中的场景和分组作为默认值
        default_scene = ""
        default_group = ""
        selected = self.tree.selectedItems()
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data["type"] == "scene":
                default_scene = item.text(0)
            elif data["type"] == "group":
                default_group = item.text(0)
                parent_item = item.parent()
                if parent_item:
                    default_scene = parent_item.text(0)
        
        dialog = PhraseWizardDialog(self.manager, theme=self.theme, default_scene=default_scene, default_group=default_group, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            scene_name = data["scene"]
            group_name = data["group"]
            phrase_content = data["phrase"]
            
            # 查找场景
            scene_id = None
            for s in self.manager.get_scenes():
                if s["name"] == scene_name:
                    scene_id = s["id"]
                    break
                    
            # 查找分组
            group_id = None
            if scene_id:
                for s in self.manager.get_scenes():
                    if s["id"] == scene_id:
                        for g in s.get("groups", []):
                            if g["name"] == group_name:
                                group_id = g["id"]
                                break
                        break
            
            if scene_id and group_id:
                # 添加短语
                self.manager.add_phrase(scene_id, group_id, phrase_content, data.get("type", "text"), data.get("remark", ""))
                
                # 刷新树
                self.load_tree()
                
                # 尝试选中刚才的组
                self.select_group_in_tree(scene_id, group_id)

    def select_group_in_tree(self, scene_id, group_id):
        for i in range(self.tree.topLevelItemCount()):
            s_item = self.tree.topLevelItem(i)
            s_data = s_item.data(0, Qt.ItemDataRole.UserRole)
            if s_data["id"] == scene_id:
                for j in range(s_item.childCount()):
                    g_item = s_item.child(j)
                    g_data = g_item.data(0, Qt.ItemDataRole.UserRole)
                    if g_data["id"] == group_id:
                        self.tree.setCurrentItem(g_item)
                        return

    def get_menu_style(self):
        if self.theme == "dark":
            return """
                QMenu {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    padding: 6px;
                    margin: 8px;
                }
                QMenu::item {
                    color: #cdd6f4;
                    padding: 8px 30px 8px 30px;
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
            """
        else:
            return """
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #dce0e8;
                    border-radius: 8px;
                    padding: 6px;
                    margin: 8px;
                }
                QMenu::item {
                    color: #4c4f69;
                    padding: 8px 30px 8px 30px;
                    border-radius: 6px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #ccd0da;
                    color: #4c4f69;
                }
                QMenu::icon {
                    padding-left: 10px;
                }
            """

    def on_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(self.get_menu_style())
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40) if self.theme == "light" else QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        
        edit_action = QAction("重命名", self)
        del_action = QAction("删除", self)
        menu.addAction(edit_action)
        menu.addAction(del_action)
        
        action = menu.exec(self.tree.mapToGlobal(pos))
        if action == edit_action:
            dialog = CustomInputDialog("重命名", "请输入新名称:", text=item.text(0), theme=self.theme, parent=self)
            if dialog.exec():
                new_name = dialog.get_text()
                if new_name.strip():
                    if data["type"] == "scene":
                        self.manager.edit_scene(data["id"], new_name.strip())
                    else:
                        self.manager.edit_group(data["scene_id"], data["id"], new_name.strip())
                    self.load_tree()
        elif action == del_action:
            dialog = CustomConfirmDialog("确认删除", f"确定要删除 '{item.text(0)}' 吗？", theme=self.theme, parent=self)
            if dialog.exec():
                if data["type"] == "scene":
                    self.manager.delete_scene(data["id"])
                else:
                    self.manager.delete_group(data["scene_id"], data["id"])
                self.load_tree()
                self.phrase_list.clear()

    def on_phrase_context_menu_action(self, action_type, list_item, phrase_data):
        phrase_id = phrase_data["id"]
        
        scene_id = phrase_data.get("_scene_id")
        group_id = phrase_data.get("_group_id")
        scene_name = phrase_data.get("_scene_name", "")
        group_name = phrase_data.get("_group_name", "")
        
        if not scene_id or not group_id:
            selected_tree = self.tree.selectedItems()
            if not selected_tree: return
            tree_data = selected_tree[0].data(0, Qt.ItemDataRole.UserRole)
            scene_id = tree_data["scene_id"]
            group_id = tree_data["id"]
            scene_name = selected_tree[0].parent().text(0) if selected_tree[0].parent() else ""
            group_name = selected_tree[0].text(0)
        
        if action_type == "edit":
            default_scene = scene_name
            default_group = group_name
            
            # 针对文件/图片等媒体类型，将 remark (如果有) 传递给 default_phrase 用于文本框，内容本身(路径)传递给 edit_content 用于预览
            if phrase_data.get("type", "text") != "text":
                edit_text = phrase_data.get("remark", "")
                edit_content = phrase_data["content"]
            else:
                edit_text = phrase_data["content"]
                edit_content = ""
                
            dialog = PhraseWizardDialog(self.manager, theme=self.theme, default_scene=default_scene, default_group=default_group, default_phrase=edit_text, is_edit=True, default_type=phrase_data.get("type", "text"), edit_content=edit_content, parent=self)
            if dialog.exec():
                data = dialog.get_data()
                scene_name = data["scene"]
                group_name = data["group"]
                
                # 对于非文本，只允许修改备注（和移动分组），不允许通过文本框替换原始的文件路径/数据
                if phrase_data.get("type", "text") != "text":
                    new_content = phrase_data["content"] # 保持文件路径不变
                    # 借用 data["phrase"] （用户在文本框修改的内容） 作为新的 remark
                    new_remark = data["phrase"] 
                else:
                    new_content = data["phrase"]
                    new_remark = ""
                
                if not scene_name or not group_name:
                    CustomAlertDialog("提示", "场景和分组不能为空！", theme=self.theme, parent=self).exec()
                    return
                if phrase_data.get("type", "text") == "text" and not new_content:
                    CustomAlertDialog("提示", "文本内容不能为空！", theme=self.theme, parent=self).exec()
                    return
                    
                # 查找场景
                new_scene_id = None
                for s in self.manager.get_scenes():
                    if s["name"] == scene_name:
                        new_scene_id = s["id"]
                        break
                        
                # 查找分组
                new_group_id = None
                if new_scene_id:
                    for s in self.manager.get_scenes():
                        if s["id"] == new_scene_id:
                            for g in s.get("groups", []):
                                if g["name"] == group_name:
                                    new_group_id = g["id"]
                                    break
                            break
                            
                if new_scene_id and new_group_id:
                    self.manager.edit_phrase(scene_id, group_id, phrase_id, new_content, new_scene_id, new_group_id, new_remark=new_remark)
                    self.load_tree()
                    self.select_group_in_tree(new_scene_id, new_group_id)
                    if hasattr(self, 'search_input') and self.search_input.text().strip():
                        self.on_search_changed(self.search_input.text())
        elif action_type == "delete":
            dialog = CustomConfirmDialog("确认删除", "确定要删除这条短语吗？", theme=self.theme, parent=self)
            if dialog.exec():
                self.manager.delete_phrase(scene_id, group_id, phrase_id)
                if hasattr(self, 'search_input') and self.search_input.text().strip():
                    self.on_search_changed(self.search_input.text())
                else:
                    self.on_tree_selection_changed()

    def on_phrase_context_menu(self, pos):
        item = self.phrase_list.itemAt(pos)
        if not item: return
        phrase_data = item.data(Qt.ItemDataRole.UserRole)
        
        if phrase_data.get("type") == "group_nav":
            return # 分组导航卡片不显示此右键菜单
            
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(self.get_menu_style())
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40) if self.theme == "light" else QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        
        edit_action = QAction("编辑", self)
        del_action = QAction("删除", self)
        menu.addAction(edit_action)
        menu.addAction(del_action)
        
        action = menu.exec(self.phrase_list.mapToGlobal(pos))
        if action == edit_action:
            self.on_phrase_context_menu_action("edit", item, phrase_data)
        elif action == del_action:
            self.on_phrase_context_menu_action("delete", item, phrase_data)

    def on_phrase_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "group_nav":
            self.select_group_in_tree(data["scene_id"], data["id"])
        else:
            self.phrase_clicked.emit(data)
