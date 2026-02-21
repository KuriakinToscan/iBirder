from abc import ABC, abstractmethod

class IdentificadorAve(ABC):
    @abstractmethod
    def identificar(self, caminho_imagem: str) -> dict:
        """
        Identifica a ave na imagem fornecida.

        Args:
            caminho_imagem (str): Caminho absoluto para o arquivo de imagem.

        Returns:
            dict: Dicionário contendo os dados da identificação.
                  Espera-se chaves como 'nome_cientifico', 'confianca', etc.
        """
        pass
