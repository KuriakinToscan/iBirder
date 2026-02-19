from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QMessageBox, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from core.geo_utils import search_location

class SearchLocationWorker(QThread):
    results_found = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        try:
            results = search_location(self.query)
            self.results_found.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))

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
        self.search_worker = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # --- Busca ---
        lbl_instrucao = QLabel("Digite o nome da cidade ou local:")
        lbl_instrucao.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_instrucao)
        
        container_busca = QHBoxLayout()
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText("Ex: Parque Ibirapuera, São Paulo...")
        self.input_busca.returnPressed.connect(self._buscar)
        
        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setCursor(Qt.PointingHandCursor)
        self.btn_buscar.clicked.connect(self._buscar)
        
        container_busca.addWidget(self.input_busca)
        container_busca.addWidget(self.btn_buscar)
        layout.addLayout(container_busca)
        
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

    def _buscar(self):
        query = self.input_busca.text().strip()
        if not query: return
        
        self.lista_resultados.clear()
        self.lista_resultados.addItem("Buscando...")
        self.btn_buscar.setEnabled(False)
        
        # Safe Reassignment Logic
        if self.search_worker is not None:
            if self.search_worker.isRunning():
                self.search_worker.requestInterruption()
                self.search_worker.quit()
                self.search_worker.wait()
            self.search_worker.deleteLater()
            
        self.search_worker = SearchLocationWorker(query, parent=self)
        self.search_worker.results_found.connect(self._ao_receber_resultados)
        self.search_worker.error_occurred.connect(self._ao_erro_busca)
        self.search_worker.start()

    def _ao_receber_resultados(self, resultados):
        self.btn_buscar.setEnabled(True)
        self.lista_resultados.clear()
        
        if not resultados:
            self.lista_resultados.addItem("Nenhum local encontrado.")
            return

        for res in resultados:
            item_text = res['address']
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, res) # Guarda o dict completo
            self.lista_resultados.addItem(item)

    def _ao_erro_busca(self, erro_msg):
        self.btn_buscar.setEnabled(True)
        self.lista_resultados.clear()
        self.lista_resultados.addItem(f"Erro: {erro_msg}")
        QMessageBox.warning(self, "Erro na Busca", erro_msg)
            
    def _item_selecionado(self, item):
        dados = item.data(Qt.UserRole)
        if dados:
            self.input_lat.setText(str(dados['lat']))
            self.input_lon.setText(str(dados['lon']))
            self.selected_coords = (dados['lat'], dados['lon'])
            self.btn_confirmar.setEnabled(True)
            
    def _confirmar(self):
        # Permite edição manual também
        try:
            lat = float(self.input_lat.text().replace(',', '.'))
            lon = float(self.input_lon.text().replace(',', '.'))
            self.selected_coords = (lat, lon)
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Erro", "Coordenadas inválidas.")

    def get_coordinates(self):
        return self.selected_coords
