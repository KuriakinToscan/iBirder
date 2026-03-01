
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
            link = bot.buscar_link_wikiaves(self.scientific_name)
            
            if link:
                dados = bot.extrair_dados_especie(link)
                dados['link_origem'] = link
                
                # Sincronização eBird v0.8.0 Heritage (v1.6.10)
                # O robô busca o eBird via Google logo após o WikiAves para garantir 100% de precisão.
                link_ebird = bot.buscar_link_ebird(self.scientific_name)
                if link_ebird:
                    dados['link_ebird'] = link_ebird
                    print(f"[WIKI] Link eBird robusto encontrado: {link_ebird}")
                
                dados['original_scientific_name'] = self.scientific_name
                self.info_found.emit(dados)
            else:
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if bot:
                bot.fechar()
