import sys
from PyQt6.QtWidgets import QApplication, QComboBox
app = QApplication(sys.argv)
c = QComboBox()
c.addItems(['A', 'B'])
c.setStyleSheet('''QComboBox { background: red; } QComboBox::down-arrow { image: url('data:image/svg+xml;utf8,<svg></svg>'); }''')
c.show()
# sys.exit(app.exec())
