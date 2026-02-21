from PySide6.QtWidgets import QCheckBox, QPushButton, QLabel, QHBoxLayout, QMessageBox
from ui.base.base_dialog import BaseDialog
from core.config import carregar_config, salvar_config

class APISettingsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(title="Configurações de Avisos de API", parent=parent)
        self.setFixedSize(300, 150)
        
        self.main_layout.addWidget(QLabel("Quais alertas ocultos deseja reexibir?"))
        
        cfg = carregar_config()
        
        self.chk_iucn = QCheckBox("Mostrar Alerta IUCN", self)
        self.chk_iucn.setChecked(cfg.get("mostrar_alerta_iucn", True))
        
        self.chk_ebird = QCheckBox("Mostrar Alerta eBird", self)
        self.chk_ebird.setChecked(cfg.get("mostrar_alerta_ebird", True))
        
        self.main_layout.addWidget(self.chk_iucn)
        self.main_layout.addWidget(self.chk_ebird)
        
        self.main_layout.addStretch()
        
        # Botões Rodapé
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setProperty("class", "secundario")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_salvar = QPushButton("Salvar Preferências")
        btn_salvar.clicked.connect(self._salvar)
        
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_salvar)
        
        self.main_layout.addLayout(layout_botoes)

    def _salvar(self):
        cfg = carregar_config()
        cfg["mostrar_alerta_iucn"] = self.chk_iucn.isChecked()
        cfg["mostrar_alerta_ebird"] = self.chk_ebird.isChecked()
        salvar_config(cfg)
        
        QMessageBox.information(self, "Preferências Salvas", "As configurações de alertas foram registradas.\n\n(Será necessário reiniciar o app para ver os alertas ressurgirem).")
        self.accept()
