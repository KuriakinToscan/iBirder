#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

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
                        taxon_res = data["results"][0]
                        tax_id = taxon_res.get("id")
                        
                        # Segunda Chamada (v0.9.9): Busca por ID para obter Ancestors detalhados
                        if tax_id:
                             resp_detail = requests.get(f"https://api.inaturalist.org/v1/taxa/{tax_id}", timeout=5)
                             if resp_detail.status_code == 200 and resp_detail.json().get("results"):
                                  taxon = resp_detail.json()["results"][0]
                                  resultados["nome_ingles"] = taxon.get("english_common_name", "Desconhecido")
                                  
                                  # Procurar Ordem e Família nos ancestrais
                                  ancestors = taxon.get("ancestors", [])
                                  for anc in ancestors:
                                       rank = anc.get("rank", "")
                                       if rank == "order":
                                            resultados["ordem"] = anc.get("name", "Desconhecida").capitalize()
                                       elif rank == "family":
                                            resultados["familia"] = anc.get("name", "Desconhecida").capitalize()
                                  
                                  resultados["link_ebird"] = f"https://www.inaturalist.org/taxa/{tax_id}"
                        
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
