from PySide6.QtCore import QThread, Signal
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import re

class INaturalistWorker(QThread):
    # Renomeando sinal para ser mais genérico, embora o slot na UI ainda espere um dict
    # Vou manter a estrutura do dict para compatibilidade com o slot da UI
    info_found = Signal(dict) 
    error_occurred = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name

    def run(self):
        print(f"[INATURALIST] Worker iniciado para: {self.species_name}")
        
        resultado = {
            "descricao": "Carregando...",
            "link_fonte": "",
            "nome_comum": None,
            "etimologia": None, # Mantendo chaves para compatibilidade, mesmo que vazias
            "nome_ingles": None,
            "familia": None,
            "ordem": None,
            "conservacao": None,
            "imagem_url": None
        }
        
        try:
            from core.inaturalist_client import INaturalistClient
            client = INaturalistClient()
            desc, common_name, url_fonte = client.get_species_info(self.species_name)
            
            resultado["descricao"] = desc
            resultado["link_fonte"] = url_fonte
            if common_name:
                resultado["nome_comum"] = common_name
            
            print(f"[INATURALIST] Dados recuperados. Comprimento desc: {len(desc)}")

            self.info_found.emit(resultado)

        except Exception as e:
            print(f"[ERRO FATAL INATURALIST] {e}")
            resultado["descricao"] = f"Erro ao buscar dados: {str(e)}"
            self.info_found.emit(resultado)

