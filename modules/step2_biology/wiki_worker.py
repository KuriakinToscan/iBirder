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


from PySide6.QtCore import QThread, Signal
import logging
from modules.step2_biology.wiki_scraper import BuscadorBlindado
from modules.step5_taxonomy import ebird_taxonomy

class BuscadorWorker(QThread):
    info_found = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name

    def run(self):
        # Validação de segurança
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            logging.warning(f"Busca Wiki abortada: Nome '{self.scientific_name}' inválido.")
            self.error_occurred.emit("Identificação inconclusiva. Aguardando entrada manual.")
            return

        bot = None
        try:
            bot = BuscadorBlindado()
            link = bot.buscar_link_wikiaves(self.scientific_name)
            
            if link:
                dados = bot.extrair_dados_especie(link, self.scientific_name)
                dados['link_origem'] = link
                
                # Link eBird: taxonomia embarcada (instantâneo, sem internet);
                # o buscador no navegador fica só para espécies ausentes da tabela.
                ebird = ebird_taxonomy.buscar(self.scientific_name)
                link_ebird = ebird["link"] if ebird else bot.buscar_link_ebird(self.scientific_name)
                if link_ebird:
                    dados['link_ebird'] = link_ebird
                    logging.debug(f"Link eBird encontrado: {link_ebird}")
                
                dados['original_scientific_name'] = self.scientific_name
                self.info_found.emit(dados)
            else:
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                
        except Exception as e:
            logging.error(f"Erro na busca do WikiAves: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if bot:
                bot.fechar()
