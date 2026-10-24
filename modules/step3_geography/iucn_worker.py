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

MAPEAMENTO_IUCN = {
    "LC": "Pouco Preocupante (LC)",
    "NT": "Quase Ameaçada (NT)",
    "VU": "Vulnerável (VU)",
    "EN": "Em Perigo (EN)",
    "CR": "Criticamente em Perigo (CR)",
    "EW": "Extinta na Natureza (EW)",
    "EX": "Extinta (EX)",
    "DD": "Dados Insuficientes (DD)",
    "NE": "Não Avaliada (NE)"
}


class IUCNWorker(QThread):
    """
    Etapa 3A: status global da IUCN.
    A API da IUCN está desativada desde a v0.8.0 (API-Free); o status vem dos
    conservation_statuses do iNaturalist via TaxonService (cache compartilhado).
    """
    finished = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name

    def run(self):
        logging.info(f"Iniciando Etapa 3-IUCN para {self.scientific_name}")
        url_iucn = f"https://www.iucnredlist.org/search?query={self.scientific_name.replace(' ', '+')}&searchType=species"

        try:
            taxon = get_taxon(self.scientific_name)
            if not taxon.found:
                iucn_status = "Espécie não encontrada (iNaturalist)"
            elif not taxon.detail:
                iucn_status = "Erro nos detalhes (iNaturalist)"
            else:
                entry = taxon.status_por_autoridade("IUCN")
                if entry:
                    raw = (entry.get("status") or "NE").upper()
                    iucn_status = MAPEAMENTO_IUCN.get(raw, raw)
                else:
                    iucn_status = "Não Avaliado / Seguro"
        except Exception as e:
            logging.error(f"Erro no status IUCN (iNaturalist): {e}")
            iucn_status = "Erro de Conexão (Fallback)"

        logging.debug(f"Status IUCN Final: {iucn_status}")
        self.finished.emit({
            "iucn_status": iucn_status,
            "geojson_path": None,
            "link_iucn": url_iucn
        })
