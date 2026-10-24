from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, 
                               QMessageBox, QFormLayout, QCheckBox, QGroupBox,
                               QRadioButton, QButtonGroup)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from core.config import carregar_config, salvar_config
from core.paths import APP_DIR
import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from core.style_manager import StyleManager
from core.temas import TEMAS, TEMA_PADRAO
from ui.layouts import LAYOUTS, LAYOUT_PADRAO, LAYOUTS_PLANEJADOS

class APISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.resize(520, 520)
        
        self.config = carregar_config()
        # Tema salvo: a escolha é aplicada na hora (prévia) e desfeita se o diálogo for cancelado
        self._tema_salvo = self.config.get("tema") or TEMA_PADRAO
        # Layout salvo: idem, aplicado na janela principal (parent) enquanto a pessoa escolhe
        self._layout_salvo = self.config.get("layout") or LAYOUT_PADRAO
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        # Aparência (v1.4): um botão por tema de core/temas.py e um por layout de ui/layouts/
        grupo_tema = QGroupBox("Aparência")
        layout_tema = QVBoxLayout(grupo_tema)
        lbl_cores = QLabel("Tema (cores e fontes)")
        lbl_cores.setProperty("class", "lbl-titulo-sessao")
        layout_tema.addWidget(lbl_cores)
        self.grupo_botoes_tema = QButtonGroup(self)
        self.botoes_tema = {}
        for tema in TEMAS.values():
            botao = QRadioButton(tema.nome)
            botao.setToolTip(tema.descricao)
            botao.setCursor(Qt.PointingHandCursor)
            botao.toggled.connect(lambda marcado, t=tema.id: marcado and self._previa_tema(t))
            self.grupo_botoes_tema.addButton(botao)
            self.botoes_tema[tema.id] = botao
            layout_tema.addWidget(botao)

        lbl_arrumacao = QLabel("Layout (arrumação da tela)")
        lbl_arrumacao.setProperty("class", "lbl-titulo-sessao")
        layout_tema.addWidget(lbl_arrumacao)
        self.grupo_botoes_layout = QButtonGroup(self)
        self.botoes_layout = {}
        for item in LAYOUTS.values():
            botao = QRadioButton(item.nome)
            botao.setToolTip(item.descricao)
            botao.setCursor(Qt.PointingHandCursor)
            botao.toggled.connect(lambda marcado, l=item.id: marcado and self._previa_layout(l))
            self.grupo_botoes_layout.addButton(botao)
            self.botoes_layout[item.id] = botao
            layout_tema.addWidget(botao)
        for id_layout, nome, descricao in LAYOUTS_PLANEJADOS:
            if id_layout in LAYOUTS:
                continue
            botao = QRadioButton(f"{nome} (em breve)")
            botao.setToolTip(descricao)
            botao.setEnabled(False)
            self.grupo_botoes_layout.addButton(botao)
            layout_tema.addWidget(botao)

        lbl_tema = QLabel("Tema e layout são aplicados na hora, sem reiniciar o iBirder.")
        lbl_tema.setProperty("class", "lbl-placeholder")
        layout_tema.addWidget(lbl_tema)
        layout.addWidget(grupo_tema)

        lbl_apis = QLabel("Integrações em nuvem")
        lbl_apis.setProperty("class", "lbl-titulo-sessao")
        layout.addWidget(lbl_apis)
        
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
        self.lbl_help = QLabel()
        StyleManager.definir_texto(self.lbl_help, '<a href="#help" style="color: var(--link);">Como obter essas chaves? (passo a passo)</a>')
        self.lbl_help.linkActivated.connect(self._show_help)
        layout.addWidget(self.lbl_help)

        # Aviso de novas versões (core/verificacao_versao.py)
        self.chk_atualizacoes = QCheckBox("Avisar quando houver nova versão do iBirder (verifica uma vez por dia)")
        layout.addWidget(self.chk_atualizacoes)
        
        # Botoes
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("Testar Chaves")
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("class", "primario")
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
        from core.diagnostico_apis import normalizar_token_inat
        inat_token = normalizar_token_inat(self.input_inat.text())
        google_key = self.input_google.text().strip()
        self.input_inat.setText(inat_token)

        if not inat_token and not google_key:
            QMessageBox.warning(self, "Aviso", "Por favor, insira ao menos uma chave para testar.")
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        msg = []
        
        from core.diagnostico_apis import diagnosticar_google_vision, diagnosticar_inaturalist
        from core import http

        if inat_token:
            try:
                headers = {"Authorization": f"Bearer {inat_token}"}
                resp = http.get_session().get("https://api.inaturalist.org/v1/users/me", headers=headers, timeout=10)
                ok, texto = diagnosticar_inaturalist(resp.status_code)
            except Exception as e:
                ok, texto = False, f"Sem conexão com o iNaturalist ({e.__class__.__name__})."
            msg.append(f"{'✅' if ok else '❌'} iNaturalist: {texto}")

        if google_key:
            try:
                # Requisição vazia: valida a chave e o acesso à API sem consumir a cota gratuita
                url = f"https://vision.googleapis.com/v1/images:annotate?key={google_key}"
                resp = requests.post(url, json={"requests": []}, timeout=10)
                try:
                    corpo = resp.json()
                except ValueError:
                    corpo = {}
                ok, texto = diagnosticar_google_vision(resp.status_code, corpo)
            except Exception as e:
                ok, texto = False, f"Sem conexão com o Google ({e.__class__.__name__})."
            msg.append(f"{'✅' if ok else '❌'} Google Vision: {texto}")

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
        self.chk_atualizacoes.setChecked(bool(self.config.get("verificar_atualizacoes", True)))
        botao = self.botoes_tema.get(self._tema_salvo) or self.botoes_tema[TEMA_PADRAO]
        botao.blockSignals(True)  # marcar o tema salvo não é uma prévia
        botao.setChecked(True)
        botao.blockSignals(False)
        botao = self.botoes_layout.get(self._layout_salvo) or self.botoes_layout[LAYOUT_PADRAO]
        botao.blockSignals(True)
        botao.setChecked(True)
        botao.blockSignals(False)

    def _layout_escolhido(self):
        for id_layout, botao in self.botoes_layout.items():
            if botao.isChecked():
                return id_layout
        return self._layout_salvo

    def _previa_layout(self, id_layout):
        """Arruma a janela principal no layout marcado, para a pessoa ver antes de salvar."""
        janela = self.parent()
        if janela is not None and hasattr(janela, "_aplicar_layout"):
            janela._aplicar_layout(id_layout)

    def _tema_escolhido(self):
        for id_tema, botao in self.botoes_tema.items():
            if botao.isChecked():
                return id_tema
        return self._tema_salvo

    def _previa_tema(self, id_tema):
        """Aplica o tema marcado na hora, para a pessoa ver antes de salvar."""
        StyleManager.apply_theme(QApplication.instance(), tema=id_tema)

    def reject(self):
        # Cancelar (ou fechar no X) desfaz a prévia do tema
        if StyleManager.tema_atual().id != self._tema_salvo:
            StyleManager.apply_theme(QApplication.instance(), tema=self._tema_salvo)
        if self._layout_escolhido() != self._layout_salvo:
            self._previa_layout(self._layout_salvo)
        super().reject()
        
    def save_settings(self):
        from core.diagnostico_apis import normalizar_token_inat
        self.config["inat_api_token"] = normalizar_token_inat(self.input_inat.text())
        self.config["google_vision_api_key"] = self.input_google.text().strip()
        # Relê antes de salvar: a verificação de versão pode ter gravado campos com o diálogo aberto
        atual = carregar_config()
        atual.update({
            "inat_api_token": self.config["inat_api_token"],
            "google_vision_api_key": self.config["google_vision_api_key"],
            "verificar_atualizacoes": self.chk_atualizacoes.isChecked(),
            "tema": self._tema_escolhido(),
            "layout": self._layout_escolhido(),
        })
        self.config = atual
        salvar_config(self.config)
        self._tema_salvo = self.config["tema"]
        self._layout_salvo = self.config["layout"]
        QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso.")
        self.accept()
