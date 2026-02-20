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
        print(f"[eBird Worker] Iniciando processamento para {self.scientific_name}")
        
        settings = QSettings("iBirder", "App")
        token = settings.value("ebird_api_key", "").strip()
        
        if not token:
             token = os.environ.get("EBIRD_API_KEY", "")

        is_fallback = False
        
        resultados = {
            "nome_ingles": "Desconhecido",
            "classe": "Aves",
            "ordem": "Desconhecida",
            "familia": "Desconhecida",
            "ebird_code": "",
            "raridade_regional": "Não Avaliado",
            "link_ebird": ""
        }

        if token:
            try:
                print("[eBird Worker] Consultando API eBird Taxonomia...")
                quoted_sci = urllib.parse.quote(self.scientific_name)
                tax_url = f"https://api.ebird.org/v2/ref/taxonomy/ebird?sciName={quoted_sci}&fmt=json"
                
                resp_tax = requests.get(tax_url, timeout=10)
                if resp_tax.status_code == 200:
                    tax_data = resp_tax.json()
                    if tax_data and len(tax_data) > 0:
                        taxon = tax_data[0]
                        resultados["nome_ingles"] = taxon.get("comName", "Desconhecido")
                        resultados["ordem"] = taxon.get("order", "Desconhecida").capitalize()
                        resultados["familia"] = taxon.get("familyComName", "Desconhecida").capitalize()
                        resultados["ebird_code"] = taxon.get("speciesCode", "")
                        resultados["link_ebird"] = f"https://ebird.org/species/{resultados['ebird_code']}"
                        
                        # Cálculo de Raridade Regional
                        if self.lat is not None and self.lon is not None and resultados["ebird_code"]:
                            print("[eBird Worker] Calculando Frequência Regional...")
                            headers = {"X-eBirdApiToken": token}
                            # Busca registros recentes em 50km nos últimos 30 dias
                            geo_url = f"https://api.ebird.org/v2/data/obs/geo/recent?lat={self.lat}&lng={self.lon}&dist=50&back=30"
                            resp_geo = requests.get(geo_url, headers=headers, timeout=10)
                            
                            if resp_geo.status_code == 200:
                                geo_data = resp_geo.json()
                                
                                # Extrai todos os locais únicos (Hotspots/Locais Pessoais)
                                locs_totais = set(obs.get('locId') for obs in geo_data if obs.get('locId'))
                                total_locais = len(locs_totais)
                                
                                # Locais onde a nossa espécie apareceu
                                locs_especie = set(obs.get('locId') for obs in geo_data if obs.get('speciesCode') == resultados["ebird_code"])
                                count_especie = len(locs_especie)
                                
                                if total_locais > 0:
                                    freq = (count_especie / total_locais) * 100
                                    freq_formatada = f"{freq:.1f}%"
                                    
                                    if freq < 5:
                                        resultados["raridade_regional"] = f"Rara ({freq_formatada} de presença local)"
                                    elif 5 <= freq <= 20:
                                        resultados["raridade_regional"] = f"Incomum ({freq_formatada} de presença local)"
                                    else:
                                        resultados["raridade_regional"] = f"Comum ({freq_formatada} de presença local)"
                                else:
                                     resultados["raridade_regional"] = "Sem dados recentes na região"
                            else:
                                 resultados["raridade_regional"] = "Erro ao calcular raridade"
                        else:
                            resultados["raridade_regional"] = "Geolocalização indisponível"
                    else:
                        print("[eBird Worker] Espécie não encontrada na taxonomia Clements/eBird.")
                        is_fallback = True
                else:
                    print(f"[eBird Worker] Erro na API eBird Taxonomia: {resp_tax.status_code}")
                    is_fallback = True
                    
            except Exception as e:
                print(f"[eBird Worker] Erro GERAL no eBird: {e}")
                is_fallback = True
        else:
            print("[eBird Worker] Chave eBird ausente. Usando Fallback iNaturalist.")
            is_fallback = True

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
                        resultados["nome_ingles"] = taxon.get("english_common_name", "Desconhecido")
                        
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
                print(f"[eBird Worker] Erro no Fallback iNaturalist: {e}")
                resultados["raridade_regional"] = "Erro de Conexão (Fallback)"

        # Emite os metadados finais
        self.finished.emit(resultados)
