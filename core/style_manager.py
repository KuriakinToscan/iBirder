class StyleManager:
    @staticmethod
    def get_global_stylesheet():
        return """
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QCheckBox {
                color: #374151;
                font-family: 'Segoe UI';
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #374151;
                border: 1px solid #374151;
                image: url(none); /* Opcional: SVG interno do QT lida s/ SVG */
            }
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
            QPushButton.secundario {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
            }
            QPushButton.secundario:hover {
                background-color: #E5E7EB;
                color: #111827;
                border-color: #9CA3AF;
            }
        """

    @staticmethod
    def is_windows_dark_mode() -> bool:
        import winreg
        try:
            registry_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(registry_key, "AppsUseLightTheme")
            winreg.CloseKey(registry_key)
            return value == 0
        except OSError:
            return False # Default to false if registry not found
