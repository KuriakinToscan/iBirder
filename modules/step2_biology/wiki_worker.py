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


from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QThread, Signal
import logging
from modules.step2_biology.wiki_scraper import BuscadorWikiAves
from core.taxon_service import get_taxon

class BuscadorWorker(QThread):
    info_found = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name

    def _nome_comum_pt(self):
        """Nome popular em português do iNaturalist, usado para montar a URL direta do WikiAves."""
        try:
            return get_taxon(self.scientific_name).nome_comum_pt
        except Exception as e:
            logging.debug(f"Nome popular indisponível no iNaturalist: {e}")
            return None

    def run(self):
        # Validação de segurança
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            logging.warning(f"Busca Wiki abortada: Nome '{self.scientific_name}' inválido.")
            self.error_occurred.emit("Identificação inconclusiva. Aguardando entrada manual.")
            return

        # Buscadores separados: cada thread do pool usa sua própria sessão HTTP
        bot_wiki = BuscadorWikiAves()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                # O link do eBird é buscado em paralelo com o WikiAves
                futuro_ebird = pool.submit(lambda: BuscadorWikiAves().buscar_link_ebird(self.scientific_name))
                link = bot_wiki.buscar_link_wikiaves(self.scientific_name, self._nome_comum_pt())
                dados = bot_wiki.extrair_dados_especie(link) if link else None
                try:
                    link_ebird = futuro_ebird.result(timeout=30)
                except Exception as e:
                    logging.debug(f"Busca do link eBird falhou: {e}")
                    link_ebird = None

            if dados is None:
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                return

            dados['link_origem'] = link
            if link_ebird:
                dados['link_ebird'] = link_ebird
                logging.debug(f"Link eBird encontrado: {link_ebird}")
            dados['original_scientific_name'] = self.scientific_name
            self.info_found.emit(dados)

        except Exception as e:
            logging.error(f"Erro na busca do WikiAves: {e}")
            self.error_occurred.emit(str(e))
        finally:
            bot_wiki.fechar()
