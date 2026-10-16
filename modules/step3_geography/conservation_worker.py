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

from core.taxon_service import get_taxon, PLACE_BRASIL
import logging
from PySide6.QtCore import QThread, Signal

class NationalConservationWorker(QThread):
    """
    Etapa 3C: dados de conservação, todos via iNaturalist (TaxonService):
    1. Endemismo/ocorrência no Brasil (establishment_means do lugar Brasil)
    2. Status nacional, quando o iNaturalist tiver a lista brasileira (raro; a lista
       oficial do ICMBio/MMA ainda não é integrada -> "Não disponível")
    3. CITES (Comércio Internacional)
    """
    finished = Signal(dict)
    error_occurred = Signal(str)

    # Dicionário de Tradução de Status (Sigla -> Extenso em Português)
    TRADUCAO_STATUS = {
        "EX": "Extinta",
        "EW": "Extinta na Natureza",
        "CR": "Criticamente em Perigo",
        "EN": "Em Perigo",
        "VU": "Vulnerável",
        "NT": "Quase Ameaçada",
        "LC": "Pouco Preocupante",
        "DD": "Dados Insuficientes",
        "NE": "Não Avaliada"
    }

    def __init__(self, scientific_name, country="Brazil", parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.country = country or "Brazil"

    def run(self):
        logging.info(f"Iniciando análise de conservação nacional para: {self.scientific_name}")
        
        results = {
            # A lista nacional (ICMBio/MMA) ainda não é integrada: não afirmar "Não Avaliado"
            "status_icmbio": "Não disponível",
            "status_cites": "Não disponível",  # o iNaturalist quase nunca traz os anexos da CITES
            "endemismo": "Não informado",
            "msg_distribuicao": "Distribuição padrão",
            "is_brazil": self.country.lower() in ["brazil", "brasil"]
        }

        try:
            # 1. Busca CITES (Global)
            self._fetch_cites_status(results)

            # 2. Endemismo e status nacional (iNaturalist, lugar Brasil)
            if results["is_brazil"]:
                self._fetch_brazilian_data(results)
            else:
                results["status_icmbio"] = "Não disponível (registro fora do Brasil)"
            
            self.finished.emit(results)
        except Exception as e:
            logging.error(f"Erro no ConservationWorker: {e}")
            self.error_occurred.emit(str(e))

    def _fetch_cites_status(self, results):
        """Busca status na API do Species+/CITES (Simulação/Fallback iNaturalist)."""
        # Em v1.1 usamos o iNaturalist como proxy para CITES quando disponível
        # (TaxonService: mesmo taxon já buscado pelas outras etapas, sem nova requisição)
        try:
            cites = get_taxon(self.scientific_name).status_por_autoridade("CITES")
            if cites:
                results["status_cites"] = f"Anexo {cites.get('status')}"
        except Exception as e:
            logging.debug(f"CITES indisponível: {e}")

    def _fetch_brazilian_data(self, results):
        """
        Endemismo e status nacional a partir do iNaturalist (TaxonService, lugar Brasil = 6878).
        Até a v1.2 esta consulta usava o place_id 6857 (Reino Unido) e um campo que a API não
        devolve, então toda espécie saía "não endêmica" e o ICMBio sempre "Não Avaliado".
        """
        try:
            taxon = get_taxon(self.scientific_name)
            ocorrencia = taxon.ocorrencia_brasil
            results["endemismo"] = {"endemic": "Sim", "native": "Não", "introduced": "Não"}.get(ocorrencia, "Não informado")
            results["ocorrencia_brasil"] = {"endemic": "Endêmica do Brasil", "native": "Nativa",
                                            "introduced": "Introduzida"}.get(ocorrencia, "Não informada")

            # O iNaturalist raramente tem a lista nacional brasileira; quando tiver, usamos
            nacional = taxon.status_no_lugar(PLACE_BRASIL)
            if nacional:
                sigla = str(nacional.get("status", "")).upper()
                results["status_icmbio"] = self.TRADUCAO_STATUS.get(sigla, nacional.get("status"))
        except Exception as e:
            logging.debug(f"Dados nacionais indisponíveis: {e}")

    @staticmethod
    def traduzir_iucn(sigla):
        """Utilitário para traduzir siglas IUCN para extenso."""
        sigla_clean = sigla.split('(')[0].strip().upper() if sigla else "NE"
        return NationalConservationWorker.TRADUCAO_STATUS.get(sigla_clean, sigla)
