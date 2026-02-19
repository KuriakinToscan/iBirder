from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QMessageBox, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon
from core.geo_utils import search_location

class BuscaWorker(QThread):
    finished = Signal(list)
    
    def __init__(self, query):
        super().__init__()
        self.query = query
        
    def run(self):
        resultados = search_location(self.query)
        self.finished.emit(resultados)

class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Definir Localização Manualmente")
        self.setFixedWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #F0F2F5; }
            QLabel { color: #374151; font-family: "Segoe UI"; }
            QLineEdit, QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
                color: #374151;
            }
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #1F2937; }
        """)
        
        self.selected_coords = None # (lat, lon)
        self.timer_busca = QTimer()
        self.timer_busca.setSingleShot(True)
        self.timer_busca.timeout.connect(self._executar_busca)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # --- Busca ---
        lbl_instrucao = QLabel("Digite o nome da cidade ou local:")
        lbl_instrucao.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_instrucao)
        
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText("Ex: Parque Ibirapuera, São Paulo... (Busca automática)")
        self.input_busca.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input_busca)
        
        # --- Resultados ---
        lbl_resultados = QLabel("Resultados:")
        layout.addWidget(lbl_resultados)
        
        self.lista_resultados = QListWidget()
        self.lista_resultados.itemClicked.connect(self._item_selecionado)
        layout.addWidget(self.lista_resultados)
        
        # --- Coordenadas ---
        container_coords = QHBoxLayout()
        
        self.input_lat = QLineEdit()
        self.input_lat.setPlaceholderText("Latitude")
        
        self.input_lon = QLineEdit()
        self.input_lon.setPlaceholderText("Longitude")
        
        container_coords.addWidget(QLabel("Lat:"))
        container_coords.addWidget(self.input_lat)
        container_coords.addWidget(QLabel("Lon:"))
        container_coords.addWidget(self.input_lon)
        layout.addLayout(container_coords)
        
        # --- Confirmar ---
        self.btn_confirmar = QPushButton("Confirmar Localização")
        self.btn_confirmar.setCursor(Qt.PointingHandCursor)
        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.clicked.connect(self._confirmar)
        layout.addWidget(self.btn_confirmar)
        
    def _on_text_changed(self):
        self.timer_busca.start(1000) # 1s debounce
        
    def _executar_busca(self):
        query = self.input_busca.text().strip()
        if len(query) < 3: return
        
        self.lista_resultados.clear()
        self.lista_resultados.addItem("Buscando...")
        
        self.worker = BuscaWorker(query)
        self.worker.finished.connect(self._on_busca_finished)
        self.worker.start()
        
    def _on_busca_finished(self, resultados):
        self.lista_resultados.clear()
        if not resultados:
            self.lista_resultados.addItem("Nenhum local encontrado.")
            return

        for res in resultados:
            item = QListWidgetItem(res['address'])
            item.setData(Qt.UserRole, res)
            self.lista_resultados.addItem(item)
            
    def _item_selecionado(self, item):
        dados = item.data(Qt.UserRole)
        if dados:
            self.input_lat.setText(str(dados['lat']))
            self.input_lon.setText(str(dados['lon']))
            self.selected_coords = (dados['lat'], dados['lon'])
            self.btn_confirmar.setEnabled(True)
            
    def _confirmar(self):
        try:
            lat = float(self.input_lat.text().replace(',', '.'))
            lon = float(self.input_lon.text().replace(',', '.'))
            self.selected_coords = (lat, lon)
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Erro", "Coordenadas inválidas.")

    def get_coordinates(self):
        return self.selected_coords
