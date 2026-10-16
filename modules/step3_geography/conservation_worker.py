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
from modules.step3_geography import listas_conservacao as listas
import logging
from PySide6.QtCore import QThread, Signal

# Códigos numéricos de equivalência IUCN usados pelo iNaturalist em cada status regional
CATEGORIA_POR_CODIGO_IUCN = {
    5: "Dados Insuficientes", 10: "Pouco Preocupante", 20: "Quase Ameaçada", 30: "Vulnerável",
    40: "Em Perigo", 50: "Criticamente em Perigo", 60: "Extinta na Natureza", 70: "Extinta",
}


def outras_avaliacoes(statuses, estado=None):
    """
    Avaliações regionais/nacionais do iNaturalist além da IUCN global: listas estaduais
    brasileiras (ex.: Espírito Santo, 2019) e de outros países (Argentina, Uruguai...).
    Ordem: estado da foto, demais estados do Brasil, outros países.
    """
    estado = (estado or "").strip().lower()
    itens = []
    for st in statuses or []:
        lugar = st.get("place") or {}
        if not lugar:
            continue  # IUCN global: exibida separadamente
        nome_lugar = lugar.get("display_name") or lugar.get("name") or "?"
        brasil = lugar.get("id") == PLACE_BRASIL or nome_lugar.endswith(", BR") or nome_lugar == "Brazil"
        categoria = CATEGORIA_POR_CODIGO_IUCN.get(st.get("iucn"))
        itens.append({
            "lugar": nome_lugar.replace(", BR", " (BR)"),
            "categoria": categoria or str(st.get("status") or "?"),
            "status_original": st.get("status"),
            "autoridade": (st.get("authority") or "").strip(),
            "url": st.get("url") or "",
            "brasil": brasil,
            "estado_da_foto": bool(estado) and nome_lugar.lower().startswith(estado),
        })
    itens.sort(key=lambda i: (not i["estado_da_foto"], not i["brasil"], i["lugar"]))
    return itens


class NationalConservationWorker(QThread):
    """
    Etapa 3C: conservação e ocorrência no Brasil.
    1. Lista nacional (Portaria MMA nº 148/2022 / ICMBio) — tabela embarcada;
    2. CITES (Checklist oficial) — tabela embarcada;
    3. Endemismo/ocorrência no Brasil e outras avaliações regionais — iNaturalist (TaxonService).
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

    def __init__(self, scientific_name, country="Brazil", estado=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.country = country or "Brazil"
        self.estado = estado

    def run(self):
        logging.info(f"Iniciando análise de conservação nacional para: {self.scientific_name}")
        results = {
            "status_icmbio": "Não disponível",
            "status_cites": "Não disponível",
            "endemismo": "Não informado",
            "ocorrencia_brasil": "Não informada",
            "outras_avaliacoes": [],
            "is_brazil": self.country.lower() in ["brazil", "brasil"],
        }
        try:
            taxon = None
            try:
                taxon = get_taxon(self.scientific_name)
            except Exception as e:
                logging.debug(f"iNaturalist indisponível para conservação: {e}")

            # 1 e 2. Listas oficiais embarcadas (funcionam sem internet)
            inat_id = taxon.id if taxon else None
            results["status_icmbio"] = listas.descrever_status_nacional(self.scientific_name, inat_id)
            nacional = listas.status_nacional(self.scientific_name, inat_id)
            results["categoria_icmbio"] = nacional["categoria_extenso"] if nacional else None
            results["status_cites"] = listas.descrever_cites(self.scientific_name)

            # 3. iNaturalist: endemismo e outras avaliações
            if taxon and taxon.found:
                ocorrencia = taxon.ocorrencia_brasil
                results["endemismo"] = {"endemic": "Sim", "native": "Não", "introduced": "Não"}.get(ocorrencia, "Não informado")
                results["ocorrencia_brasil"] = {"endemic": "Endêmica do Brasil", "native": "Nativa",
                                                "introduced": "Introduzida"}.get(ocorrencia, "Não informada")
                results["outras_avaliacoes"] = outras_avaliacoes(taxon.conservation_statuses, self.estado)

            self.finished.emit(results)
        except Exception as e:
            logging.error(f"Erro no ConservationWorker: {e}")
            self.error_occurred.emit(str(e))

    @staticmethod
    def traduzir_iucn(sigla):
        """Utilitário para traduzir siglas IUCN para extenso."""
        sigla_clean = sigla.split('(')[0].strip().upper() if sigla else "NE"
        return NationalConservationWorker.TRADUCAO_STATUS.get(sigla_clean, sigla)
