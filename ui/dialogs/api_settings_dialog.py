from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, 
                               QMessageBox, QFormLayout)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from core.config import carregar_config, salvar_config
from core.paths import APP_DIR
import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

class APISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações de API (Integrações)")
        self.resize(500, 230)
        
        self.config = carregar_config()
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.input_inat = QLineEdit()
        self.input_inat.setPlaceholderText("Cole seu token JWT do iNaturalist aqui")
        self.input_inat.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        
        self.input_google = QLineEdit()
        self.input_google.setPlaceholderText("Cole sua chave de API do Google Cloud Vision aqui")
        self.input_google.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        
        form_layout.addRow(QLabel("Token iNaturalist (Opcional):"), self.input_inat)
        form_layout.addRow(QLabel("Chave Google Vision (Opcional):"), self.input_google)
        
        layout.addLayout(form_layout)
        
        # Link de Ajuda
        self.lbl_help = QLabel('<a href="#help" style="color: #66b2ff;">Como obter essas chaves?</a>')
        self.lbl_help.linkActivated.connect(self._show_help)
        layout.addWidget(self.lbl_help)
        
        # Botoes
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("Testar Chaves")
        self.btn_save = QPushButton("Salvar")
        self.btn_cancel = QPushButton("Cancelar")
        
        btn_layout.addWidget(self.btn_test)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.btn_test.clicked.connect(self.test_keys)
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_cancel.clicked.connect(self.reject)
        
    def test_keys(self):
        inat_token = self.input_inat.text().strip()
        google_key = self.input_google.text().strip()
        
        if not inat_token and not google_key:
            QMessageBox.warning(self, "Aviso", "Por favor, insira ao menos uma chave para testar.")
            return
            
        import traceback
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        msg = []
        
        try:
            if inat_token:
                headers = {"Authorization": inat_token if inat_token.startswith("Bearer") else f"Bearer {inat_token}"}
                resp = requests.get("https://api.inaturalist.org/v1/users/me", headers=headers, timeout=5)
                if resp.status_code == 200:
                    msg.append("✅ iNaturalist: Sucesso! Token válido.")
                else:
                    msg.append(f"❌ iNaturalist: Falhou (Erro {resp.status_code}). Verifique seu Token.")
                    
            if google_key:
                url = f"https://vision.googleapis.com/v1/images:annotate?key={google_key}"
                payload = {"requests": []} # Payload vazio deve retornar 400 Bad Request se a key for válida, 403 se for inválida
                resp = requests.post(url, json=payload, timeout=5)
                # 400 Bad Request -> API Key is valid, but payload is bad. This means auth passed.
                # 200 OK -> API Key is valid, but shouldn't happen with empty payload.
                if resp.status_code in (200, 400):
                    msg.append("✅ Google Vision: Sucesso! Chave válida.")
                else:
                    msg.append(f"❌ Google Vision: Falhou (Erro {resp.status_code}). Verifique sua Chave.")
        except Exception as e:
            msg.append(f"❌ Erro de Conexão: {str(e)}")
            
        QApplication.restoreOverrideCursor()
        
        QMessageBox.information(self, "Resultado do Teste", "\n\n".join(msg))
        
    def _show_help(self):
        from PySide6.QtWidgets import QTextBrowser
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajuda: APIs em Nuvem")
        dialog.resize(600, 450)
        layout = QVBoxLayout(dialog)
        
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        try:
            path = APP_DIR / "manual_apis_nuvem.md"
            if not path.exists():
                path = APP_DIR / "guia_do_usuario.md"
            with open(path, "r", encoding="utf-8") as f:
                browser.setMarkdown(f.read())
        except Exception:
            browser.setPlainText("Não foi possível carregar as instruções. Consulte o arquivo na pasta do aplicativo.")
            
        layout.addWidget(browser)
        dialog.exec()
        
    def load_data(self):
        self.input_inat.setText(self.config.get("inat_api_token", ""))
        self.input_google.setText(self.config.get("google_vision_api_key", ""))
        
    def save_settings(self):
        self.config["inat_api_token"] = self.input_inat.text().strip()
        self.config["google_vision_api_key"] = self.input_google.text().strip()
        salvar_config(self.config)
        QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso.")
        self.accept()
