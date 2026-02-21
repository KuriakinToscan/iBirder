import os
from PySide6.QtWidgets import QLabel, QCheckBox, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt, QSettings
from core.config import carregar_config, salvar_config
from ui.base.base_dialog import BaseDialog

class StartupStatusDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(title="Status de Funcionalidades (Aviso)", parent=parent)
        self.setFixedSize(450, 220)
        
        lbl_titulo = QLabel("<b>Algumas funcionalidades avançadas estão desativadas:</b>")
        self.main_layout.addWidget(lbl_titulo)
        
        lbl_info = QLabel(
             "• <b>Status de Conservação Global:</b> Ausente (Falta Chave IUCN)<br>"
             "• <b>Frequência Regional e Taxonomia Avançada:</b> Ausente (Falta Chave eBird)<br><br>"
             "O iBirder continuará funcionando perfeitamente usando o iNaturalist como base de dados primária.<br>"
             "Para habilitar esses recursos no futuro, acesse <i>Ferramentas > Configurações de Avisos de API</i>."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #4B5563; font-size: 12px; line-height: 1.4;")
        self.main_layout.addWidget(lbl_info)
        
        self.main_layout.addStretch()
        
        # Checkbox silenciador
        self.chk_silenciar = QCheckBox("Reconheço que faltam chaves. Não mostrar novamente.", self)
        self.main_layout.addWidget(self.chk_silenciar)
        
        # Botões Rodapé
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_ok = QPushButton("Entendi, Iniciar o iBirder")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._aceitar)
        layout_botoes.addWidget(btn_ok)
        
        self.main_layout.addLayout(layout_botoes)

    def _aceitar(self):
        if self.chk_silenciar.isChecked():
             cfg = carregar_config()
             cfg["mostrar_alerta_boot_api"] = False
             salvar_config(cfg)
        self.accept()

    @staticmethod
    def verificar_e_exibir(parent):
        """Método helper que avalia a necessidade de abrir o modal."""
        cfg = carregar_config()
        if not cfg.get("mostrar_alerta_boot_api", True):
             return # Usuário já silenciou

        settings = QSettings("iBirder", "App")
        iucn_key = settings.value("iucn_api_key", os.environ.get("TOKEN_IUCN", "")).strip()
        ebird_key = settings.value("ebird_api_key", os.environ.get("EBIRD_API_KEY", "")).strip()
        
        # Se ambas existem, não precisa de aviso
        if iucn_key and ebird_key:
             return
             
        # Se falta pelo menos uma, mostra o Porteiro
        dlg = StartupStatusDialog(parent)
        dlg.exec()
