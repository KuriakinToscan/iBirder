import requests
import logging
import json
import urllib.parse
from PySide6.QtCore import QThread, Signal, QSettings

class EBirdWorker(QThread):
    finished = Signal(dict)

    def __init__(self, scientific_name, lat=None, lon=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.lat = lat
        self.lon = lon

    def run(self):
        # Validação de segurança
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            logging.warning(f"Busca eBird/Taxonomia abortada: Nome '{self.scientific_name}' inválido.")
            return

        logging.info(f"Iniciando Etapa 5-Taxonomia para {self.scientific_name}")
        
        # Transição API-Free (v0.8.0): eBird API desativada para autonomia total do usuário.
        is_fallback = True
        resultados = {
            "classe": "Aves",
            "ordem": "Desconhecida",
            "familia": "Desconhecida",
            "ebird_code": "",
            "raridade_regional": "Não Avaliado",
            "link_ebird": ""
        }

        # Fallback iNaturalist
        if is_fallback:
            try:
                logging.debug(f"Buscando taxonomia no iNaturalist para {self.scientific_name}...")
                inat_url = "https://api.inaturalist.org/v1/taxa"
                params = {
                    "q": self.scientific_name,
                    "is_active": "true",
                    "rank": "species"
                }
                resp_inat = requests.get(inat_url, params=params, timeout=10)
                
                if resp_inat.status_code == 200:
                    data = resp_inat.json()
                    if data.get("results") and len(data["results"]) > 0:
                        taxon = data["results"][0]
                        # resultados["nome_ingles"] = taxon.get("english_common_name", "Desconhecido")
                        
                        # Procurar Ordem e Família nos ancestrais
                        ancestors = taxon.get("ancestors", [])
                        for anc in ancestors:
                             rank = anc.get("rank", "")
                             if rank == "order":
                                  resultados["ordem"] = anc.get("name", "Desconhecida").capitalize()
                             elif rank == "family":
                                  resultados["familia"] = anc.get("name", "Desconhecida").capitalize()
                                  
                        resultados["raridade_regional"] = "Não Avaliado (Fallback iNaturalist)"
                    else:
                        resultados["raridade_regional"] = "Espécie não encontrada (iNaturalist)"
                else:
                    resultados["raridade_regional"] = "Inconclusivo (Falha no Fallback)"
            except Exception as e:
                logging.error(f"Erro no Fallback Taxonomia iNaturalist: {e}")
                resultados["raridade_regional"] = "Erro de Conexão (Fallback)"

        # Emite os metadados finais
        self.finished.emit(resultados)
