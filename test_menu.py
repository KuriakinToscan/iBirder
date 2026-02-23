import sys
from PySide6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget
from core.style_manager import StyleManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(StyleManager.get_global_stylesheet())
    
    window = QWidget()
    layout = QVBoxLayout(window)
    
    line_edit = QLineEdit()
    line_edit.setPlaceholderText("Clique com o botão direito aqui...")
    line_edit.setFixedSize(300, 40)
    
    layout.addWidget(line_edit)
    window.show()
    
    sys.exit(app.exec())
