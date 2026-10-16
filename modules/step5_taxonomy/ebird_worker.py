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


import logging
from PySide6.QtCore import QThread, Signal
from core.taxon_service import get_taxon


class EBirdWorker(QThread):
    """
    Etapa 5: taxonomia (ordem, família, nome em inglês).
    A API do eBird está desativada desde a v0.8.0 (API-Free); os dados vêm do
    iNaturalist via TaxonService (cache compartilhado com as demais etapas).
    """
    finished = Signal(dict)

    def __init__(self, scientific_name, lat=None, lon=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.lat = lat
        self.lon = lon

    def run(self):
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            logging.warning(f"Busca eBird/Taxonomia abortada: Nome '{self.scientific_name}' inválido.")
            return

        logging.info(f"Iniciando Etapa 5-Taxonomia para {self.scientific_name}")
        resultados = {
            "classe": "Aves",
            "ordem": "Desconhecida",
            "familia": "Desconhecida",
            "ebird_code": "",
            "raridade_regional": "Não Avaliado",
            "link_ebird": ""
        }

        try:
            taxon = get_taxon(self.scientific_name)
            if taxon.found:
                if taxon.detail:
                    resultados["nome_ingles"] = taxon.nome_ingles or "Desconhecido"
                    if ordem := taxon.ancestor("order"):
                        resultados["ordem"] = ordem.capitalize()
                    if familia := taxon.ancestor("family"):
                        resultados["familia"] = familia.capitalize()
                    resultados["link_ebird"] = taxon.url
                resultados["raridade_regional"] = "Não Avaliado (Fallback iNaturalist)"
            else:
                resultados["raridade_regional"] = "Espécie não encontrada (iNaturalist)"
        except Exception as e:
            logging.error(f"Erro no Fallback Taxonomia iNaturalist: {e}")
            resultados["raridade_regional"] = "Erro de Conexão (Fallback)"

        self.finished.emit(resultados)
