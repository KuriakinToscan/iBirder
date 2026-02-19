
from PySide6.QtCore import QThread, Signal
from core.buscador_blindado import BuscadorBlindado

class BuscadorWorker(QThread):
    info_found = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name):
        super().__init__()
        self.scientific_name = scientific_name

    def run(self):
        bot = None
        try:
            bot = BuscadorBlindado()
            link = bot.buscar_link_wikiaves(self.scientific_name)
            
            if link:
                dados = bot.extrair_dados_especie(link)
                # Injetar o nome original usado na busca para uso no GBIF
                # O WikiAves retorna a ETIMOLOGIA no campo 'nome_cientifico', o que quebra o GBIF.
                dados['original_scientific_name'] = self.scientific_name
                self.info_found.emit(dados)
            else:
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if bot:
                bot.fechar()
