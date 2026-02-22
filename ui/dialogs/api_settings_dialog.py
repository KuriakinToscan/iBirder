from PySide6.QtWidgets import QCheckBox, QPushButton, QLabel, QHBoxLayout, QMessageBox, QLineEdit
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
        
        layout_xc = QHBoxLayout()
        layout_xc.addWidget(QLabel("\nChave de Acesso Xeno-canto:"))
        
        lbl_ajuda = QLabel("❓")
        lbl_ajuda.setToolTip("Esta chave permite que o iBirder se conecte à biblioteca de sons mundial")
        lbl_ajuda.setCursor(Qt.PointingHandCursor)
        lbl_ajuda.setStyleSheet("margin-top: 10px; font-size: 14px;")
        layout_xc.addWidget(lbl_ajuda)
        layout_xc.addStretch()
        
        self.main_layout.addLayout(layout_xc)
        
        self.txt_xc_key = QLineEdit(self)
        self.txt_xc_key.setEchoMode(QLineEdit.Password)
        self.txt_xc_key.setText(cfg.get("xc_api_key", ""))
        self.txt_xc_key.setPlaceholderText("Insira sua Chave de Acesso aqui...")
        self.txt_xc_key.textChanged.connect(self._validar_chave)
        self.main_layout.addWidget(self.txt_xc_key)
        
        # Validação inicial
        self._validar_chave(self.txt_xc_key.text())
        
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

    def _validar_chave(self, texto):
        # Validação simples para Dona Maria: se tem mais que 10 caracteres, assume formato ok
        if len(texto.strip()) >= 10:
            self.txt_xc_key.setProperty("class", "input-success")
        else:
            self.txt_xc_key.setProperty("class", "")
        
        # Forçar atualização de estilo do Qt
        self.txt_xc_key.style().unpolish(self.txt_xc_key)
        self.txt_xc_key.style().polish(self.txt_xc_key)

    def _salvar(self):
        cfg = carregar_config()
        cfg["mostrar_alerta_iucn"] = self.chk_iucn.isChecked()
        cfg["mostrar_alerta_ebird"] = self.chk_ebird.isChecked()
        cfg["xc_api_key"] = self.txt_xc_key.text().strip()
        salvar_config(cfg)
        
        QMessageBox.information(self, "Preferências Salvas", "As configurações de alertas foram registradas.\n\n(Será necessário reiniciar o app para ver os alertas ressurgirem).")
        self.accept()
