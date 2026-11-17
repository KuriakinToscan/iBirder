from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, 
                               QMessageBox, QFormLayout, QCheckBox,
                               QRadioButton, QButtonGroup, QWidget, QTabWidget, QFrame,
                               QGridLayout, QGraphicsOpacityEffect)
from core.config import carregar_config, salvar_config
from core.paths import APP_DIR
import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QPixmap
from core.style_manager import StyleManager
from core.temas import PALETAS, TEMA_PADRAO, PREFERENCIAS_MODO, NOMES_MODO, obter_tema, normalizar_preferencia_modo
from ui.layouts import LAYOUTS, LAYOUT_PADRAO, LAYOUTS_PLANEJADOS

LARGURA_MINIATURA_LAYOUT = 176
ALTURA_MINIATURA_LAYOUT = 110


class CartaoLayout(QFrame):
    """Miniatura de um layout com o botão de escolha; clicar no cartão marca o botão."""

    def __init__(self, id_layout, nome, descricao, disponivel=True, parent=None):
        super().__init__(parent)
        self.setObjectName("cartao_layout")
        self.setToolTip(descricao)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.miniatura = QLabel()
        self.miniatura.setFixedSize(LARGURA_MINIATURA_LAYOUT, ALTURA_MINIATURA_LAYOUT)
        self.miniatura.setScaledContents(True)
        caminho = APP_DIR / "assets" / "layouts" / f"{id_layout}.png"
        if caminho.exists():
            self.miniatura.setPixmap(QPixmap(str(caminho)))
        layout.addWidget(self.miniatura)
        self.botao = QRadioButton(nome if disponivel else f"{nome} (em breve)")
        self.botao.setToolTip(descricao)
        self.botao.setEnabled(disponivel)
        layout.addWidget(self.botao)
        if disponivel:
            self.setCursor(Qt.PointingHandCursor)
            self.botao.setCursor(Qt.PointingHandCursor)
        else:
            efeito = QGraphicsOpacityEffect(self.miniatura)
            efeito.setOpacity(0.45)
            self.miniatura.setGraphicsEffect(efeito)
        self.botao.toggled.connect(self._marcar)

    def mousePressEvent(self, evento):
        if self.botao.isEnabled():
            self.botao.setChecked(True)
        super().mousePressEvent(evento)

    def _marcar(self, marcado):
        self.setProperty("selecionado", "true" if marcado else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class APISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.resize(980, 640)
        
        self.config = carregar_config()
        # Tema salvo: a escolha é aplicada na hora (prévia) e desfeita se o diálogo for cancelado
        self._tema_salvo = self.config.get("tema") if self.config.get("tema") in PALETAS else TEMA_PADRAO
        self._modo_salvo = normalizar_preferencia_modo(self.config.get("modo"))
        # Layout salvo: idem, aplicado na janela principal (parent) enquanto a pessoa escolhe
        self._layout_salvo = self.config.get("layout") or LAYOUT_PADRAO
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.abas = QTabWidget()
        layout.addWidget(self.abas, 1)

        # Aparência (v1.6): modo (claro/escuro), paleta de cores (core/temas.py) e layout
        # (ui/layouts/), três escolhas independentes aplicadas na hora como prévia
        pagina_aparencia = QWidget()
        layout_aparencia = QHBoxLayout(pagina_aparencia)
        layout_aparencia.setSpacing(24)
        coluna_cores = QWidget()
        coluna_cores.setMinimumWidth(300)
        layout_tema = QVBoxLayout(coluna_cores)
        layout_tema.setContentsMargins(0, 0, 0, 0)
        lbl_modo = QLabel("Modo")
        lbl_modo.setProperty("class", "lbl-titulo-sessao")
        layout_tema.addWidget(lbl_modo)
        linha_modo = QHBoxLayout()
        self.grupo_botoes_modo = QButtonGroup(self)
        self.botoes_modo = {}
        for modo in PREFERENCIAS_MODO:
            botao = QRadioButton(NOMES_MODO[modo])
            botao.setCursor(Qt.PointingHandCursor)
            botao.toggled.connect(lambda marcado: marcado and self._previa_tema())
            self.grupo_botoes_modo.addButton(botao)
            self.botoes_modo[modo] = botao
            linha_modo.addWidget(botao)
        linha_modo.addStretch()
        layout_tema.addLayout(linha_modo)

        lbl_cores = QLabel("Paleta de cores")
        lbl_cores.setProperty("class", "lbl-titulo-sessao")
        layout_tema.addWidget(lbl_cores)
        self.grupo_botoes_tema = QButtonGroup(self)
        self.botoes_tema = {}
        self._amostras = {}  # paleta -> rótulos com as cores de amostra
        for paleta in PALETAS.values():
            linha = QWidget()
            layout_linha = QHBoxLayout(linha)
            layout_linha.setContentsMargins(0, 0, 0, 0)
            layout_linha.setSpacing(6)
            botao = QRadioButton(paleta.nome)
            botao.setToolTip(paleta.descricao)
            botao.setCursor(Qt.PointingHandCursor)
            botao.toggled.connect(lambda marcado: marcado and self._previa_tema())
            self.grupo_botoes_tema.addButton(botao)
            self.botoes_tema[paleta.id] = botao
            layout_linha.addWidget(botao)
            layout_linha.addStretch()
            amostras = []
            for _ in range(3):
                amostra = QLabel()
                amostra.setFixedSize(16, 16)
                amostra.setToolTip(paleta.descricao)
                layout_linha.addWidget(amostra)
                amostras.append(amostra)
            self._amostras[paleta.id] = amostras
            layout_tema.addWidget(linha)
        self._pintar_amostras()
        StyleManager.sinal_tema_alterado().connect(self._ao_mudar_tema)

        lbl_tema = QLabel("Modo, paleta e layout são aplicados na hora, sem reiniciar o iBirder.")
        lbl_tema.setWordWrap(True)
        lbl_tema.setProperty("class", "lbl-placeholder")
        layout_tema.addWidget(lbl_tema)
        layout_tema.addStretch()
        layout_aparencia.addWidget(coluna_cores)

        # Layouts em cartões com miniatura (assets/layouts/<id>.png); os planejados, desativados
        coluna_layouts = QWidget()
        layout_layouts = QVBoxLayout(coluna_layouts)
        layout_layouts.setContentsMargins(0, 0, 0, 0)
        lbl_arrumacao = QLabel("Layout (arrumação da tela)")
        lbl_arrumacao.setProperty("class", "lbl-titulo-sessao")
        layout_layouts.addWidget(lbl_arrumacao)
        grade = QGridLayout()
        grade.setSpacing(10)
        self.grupo_botoes_layout = QButtonGroup(self)
        self.botoes_layout = {}
        itens = [(item.id, item.nome, item.descricao, True) for item in LAYOUTS.values()]
        itens += [(i, n, d, False) for i, n, d in LAYOUTS_PLANEJADOS if i not in LAYOUTS]
        for posicao, (id_layout, nome, descricao, disponivel) in enumerate(itens):
            cartao = CartaoLayout(id_layout, nome, descricao, disponivel)
            self.grupo_botoes_layout.addButton(cartao.botao)
            if disponivel:
                cartao.botao.toggled.connect(lambda marcado, l=id_layout: marcado and self._previa_layout(l))
                self.botoes_layout[id_layout] = cartao.botao
            grade.addWidget(cartao, posicao // 3, posicao % 3)
        layout_layouts.addLayout(grade)
        layout_layouts.addStretch()
        layout_aparencia.addWidget(coluna_layouts, 1)
        self.abas.addTab(pagina_aparencia, "Aparência")

        pagina_geral = QWidget()
        layout_geral = QVBoxLayout(pagina_geral)

        # Identificação (prior Brasil da IA local; modules/step1_identity/id_worker.py)
        lbl_ident = QLabel("Identificação")
        lbl_ident.setProperty("class", "lbl-titulo-sessao")
        layout_geral.addWidget(lbl_ident)
        self.chk_sem_gps_brasil = QCheckBox("Fotos sem GPS: considerar só aves do Brasil")
        self.chk_sem_gps_brasil.setToolTip(
            "A IA local acerta mais quando considera só as aves com registro no Brasil.\n"
            "Desmarque se você fotografa aves no exterior com uma câmera sem GPS.\n"
            "Fotos com GPS seguem a localização, com esta opção marcada ou não.")
        layout_geral.addWidget(self.chk_sem_gps_brasil)

        lbl_apis = QLabel("Integrações em nuvem")
        lbl_apis.setProperty("class", "lbl-titulo-sessao")
        layout_geral.addWidget(lbl_apis)
        
        form_layout = QFormLayout()
        
        self.input_inat = QLineEdit()
        self.input_inat.setPlaceholderText("Cole seu token JWT do iNaturalist aqui")
        self.input_inat.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        
        self.input_google = QLineEdit()
        self.input_google.setPlaceholderText("Cole sua chave de API do Google Cloud Vision aqui")
        self.input_google.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        
        form_layout.addRow(QLabel("Token iNaturalist (Opcional):"), self.input_inat)
        form_layout.addRow(QLabel("Chave Google Vision (Opcional):"), self.input_google)
        
        layout_geral.addLayout(form_layout)
        
        # Link de Ajuda
        self.lbl_help = QLabel()
        StyleManager.definir_texto(self.lbl_help, '<a href="#help" style="color: var(--link);">Como obter essas chaves? (passo a passo)</a>')
        self.lbl_help.linkActivated.connect(self._show_help)
        layout_geral.addWidget(self.lbl_help)

        # Aviso de novas versões (core/verificacao_versao.py)
        self.chk_atualizacoes = QCheckBox("Avisar quando houver nova versão do iBirder (verifica uma vez por dia)")
        layout_geral.addWidget(self.chk_atualizacoes)
        
        layout_geral.addStretch()
        self.abas.addTab(pagina_geral, "Identificação e nuvem")

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
        
        # "Testar Chaves" só faz sentido na aba das integrações
        self.abas.currentChanged.connect(lambda indice: self.btn_test.setVisible(indice == 1))
        self.btn_test.setVisible(self.abas.currentIndex() == 1)
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
        self.chk_sem_gps_brasil.setChecked(bool(self.config.get("ia_sem_gps_brasil", True)))
        for botao in (self.botoes_tema.get(self._tema_salvo) or self.botoes_tema[TEMA_PADRAO],
                      self.botoes_modo[self._modo_salvo]):
            botao.blockSignals(True)  # marcar o que está salvo não é uma prévia
            botao.setChecked(True)
            botao.blockSignals(False)
        botao = self.botoes_layout.get(self._layout_salvo) or self.botoes_layout[LAYOUT_PADRAO]
        botao.blockSignals(True)
        botao.setChecked(True)
        botao.blockSignals(False)
        cartao = botao.parentWidget()
        if isinstance(cartao, CartaoLayout):
            cartao._marcar(True)

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

    def _modo_escolhido(self):
        for modo, botao in self.botoes_modo.items():
            if botao.isChecked():
                return modo
        return self._modo_salvo

    def _previa_tema(self):
        """Aplica paleta e modo marcados na hora, para a pessoa ver antes de salvar."""
        StyleManager.apply_theme(QApplication.instance(), tema=self._tema_escolhido(), modo=self._modo_escolhido())

    def _ao_mudar_tema(self, _id_tema):
        self._pintar_amostras()

    def _pintar_amostras(self):
        """Amostra de cada paleta (fundo, superfície e destaque) no modo em uso agora."""
        modo = "escuro" if StyleManager.modo_escuro() else "claro"
        borda = StyleManager.cor("borda")
        for id_paleta, amostras in self._amostras.items():
            tema = obter_tema(id_paleta, modo)
            for amostra, token in zip(amostras, ("fundo", "superficie", "destaque")):
                amostra.setStyleSheet(f"background-color: {tema[token]}; border: 1px solid {borda}; border-radius: 8px;")

    def reject(self):
        # Cancelar (ou fechar no X) desfaz a prévia de paleta e modo
        if (StyleManager.tema_atual().id, StyleManager.modo_preferido()) != (self._tema_salvo, self._modo_salvo):
            StyleManager.apply_theme(QApplication.instance(), tema=self._tema_salvo, modo=self._modo_salvo)
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
            "ia_sem_gps_brasil": self.chk_sem_gps_brasil.isChecked(),
            "tema": self._tema_escolhido(),
            "modo": self._modo_escolhido(),
            "layout": self._layout_escolhido(),
        })
        self.config = atual
        salvar_config(self.config)
        self._tema_salvo = self.config["tema"]
        self._modo_salvo = self.config["modo"]
        self._layout_salvo = self.config["layout"]
        QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso.")
        self.accept()
