
from PySide6.QtCore import QThread, Signal
from modules.step2_biology.wiki_scraper import BuscadorBlindado

class BuscadorWorker(QThread):
    info_found = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name

    def run(self):
        # Validação de segurança v0.6.1
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            print(f"[WIKI] Busca abortada: Nome '{self.scientific_name}' é considerado inválido/inconclusivo.")
            self.error_occurred.emit("Identificação inconclusiva. Aguardando entrada manual.")
            return

        bot = None
        try:
            bot = BuscadorBlindado()
            link_wiki = bot.buscar_link_wikiaves(self.scientific_name)
            
            # Novo v0.8.6: Captura de Link eBird real via automação
            link_ebird = bot.buscar_link_ebird(self.scientific_name)
            
            if link_wiki:
                dados = bot.extrair_dados_especie(link_wiki)
                # Injetar o nome original usado na busca para uso no GBIF
                dados['original_scientific_name'] = self.scientific_name
                
                # Injetar link do eBird se encontrado
                if link_ebird:
                    dados['link_ebird'] = link_ebird
                    
                self.info_found.emit(dados)
            else:
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if bot:
                bot.fechar()
