"""
Módulo de Persistência EXIF (v0.3.22 - Placeholder)

Este módulo será responsável por gravar as informações processadas (Etapas 1 a 5)
diretamente nos metadados da imagem original, tornando-a um arquivo científico autossuficiente.

Escopo de Metadados Futuro:
- XPTitle / ImageDescription: Nome Comum + Nome Científico.
- GPSLatitude / GPSLongitude: Coordenadas confirmadas na Etapa 3.
- Artist / Author: Nome do usuário (configurável).
- UserComment: JSON simplificado com Status IUCN, Link eBird e Código da Espécie.
"""

class EXIFManager:
    def __init__(self):
        pass

    def escrever_metadados_completos(self, caminho_imagem, dados_sessao):
        """
        Injeta os dados consolidados da sessão nos metadados EXIF da imagem.
        (Implementação futura)
        """
        pass
