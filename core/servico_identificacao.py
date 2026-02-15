from .interfaces import IdentificadorAve

class ServicoIdentificacao:
    def __init__(self, estrategia: IdentificadorAve):
        self._estrategia = estrategia

    def definir_estrategia(self, estrategia: IdentificadorAve):
        """Alterna a estratégia de identificação (Local ou Nuvem)."""
        self._estrategia = estrategia

    def identificar(self, caminho_imagem: str) -> dict:
        """Executa a identificação usando a estratégia atual."""
        return self._estrategia.identificar(caminho_imagem)
