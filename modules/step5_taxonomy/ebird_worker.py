import os
import requests
import traceback
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
        # Validação de segurança v0.6.1
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            print(f"[eBird Worker] Busca abortada: Nome '{self.scientific_name}' inválido.")
            return

        print(f"[eBird Worker] Iniciando processamento para {self.scientific_name}")
        
        # Transição API-Free (v0.8.0): eBird API desativada para autonomia total do usuário.
        is_fallback = True
        resultados = {
            "nome_ingles": "Desconhecido",
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
                print(f"[eBird Worker] Buscando taxonomia no iNaturalist para {self.scientific_name}...")
                inat_url = f"https://api.inaturalist.org/v1/taxa?q={self.scientific_name}&is_active=true&rank=species"
                resp_inat = requests.get(inat_url, timeout=10)
                
                if resp_inat.status_code == 200:
                    data = resp_inat.json()
                    if data.get("results") and len(data["results"]) > 0:
                        taxon = data["results"][0]
                        taxon_id = taxon.get("id")
                        resultados["nome_ingles"] = taxon.get("english_common_name", "Desconhecido")
                        
                        # Transição v0.8.1: Busca profunda por ID para garantir ancestrais (Ordem/Familia)
                        try:
                            inat_id_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
                            resp_id = requests.get(inat_id_url, timeout=5)
                            if resp_id.status_code == 200:
                                data_id = resp_id.json()
                                if data_id.get("results"):
                                    taxon_full = data_id["results"][0]
                                    ancestors = taxon_full.get("ancestors", [])
                                    for anc in ancestors:
                                        rank = anc.get("rank", "")
                                        if rank == "order":
                                            resultados["ordem"] = anc.get("name", "Desconhecida").capitalize()
                                        elif rank == "family":
                                            resultados["familia"] = anc.get("name", "Desconhecida").capitalize()
                        except Exception as e_id:
                            print(f"[eBird Worker] Erro na busca por ID: {e_id}")
                            
                        # Link eBird v0.8.7 -> v0.8.9
                        # O link real é agora capturado pelo BuscadorWorker na Etapa 2.
                        # NÃO definir como vazio aqui para não sobrescrever o dado correto no estado global.
                        
                        resultados["raridade_regional"] = "Não Avaliado (Fallback iNaturalist)"
                    else:
                        resultados["raridade_regional"] = "Espécie não encontrada (iNaturalist)"
                else:
                    resultados["raridade_regional"] = "Inconclusivo (Falha no Fallback)"
            except Exception as e:
                print(f"[eBird Worker] Erro no Fallback iNaturalist: {e}")
                resultados["raridade_regional"] = "Erro de Conexão (Fallback)"

        # Emite os metadados finais
        self.finished.emit(resultados)
