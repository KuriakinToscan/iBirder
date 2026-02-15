from google import genai
from google.genai import types
import keyring
import json
import re
from pathlib import Path
from PIL import Image # Pillow para abrir imagem se necessário
from .interfaces import IdentificadorAve
from .erros import ChaveApiFaltandoErro

class IdentificadorNuvem(IdentificadorAve):
    def __init__(self):
        # Nome do serviço no keyring
        self.servico_keyring = "iBirder_Gemini_Key" 

    def _obter_chave_api(self):
        chave = keyring.get_password(self.servico_keyring, "user")
        if not chave:
            raise ChaveApiFaltandoErro("Chave de API do Google não encontrada no keyring.")
        return chave

    def identificar(self, caminho_imagem: str) -> dict:
        chave_api = self._obter_chave_api()
        
        # Cliente do novo SDK
        client = genai.Client(api_key=chave_api)

        imagem_path = Path(caminho_imagem)
        if not imagem_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {caminho_imagem}")

        # Preparar Imagem
        img = Image.open(caminho_imagem)

        prompt = """
        Identifique a espécie desta ave.
        Responda APENAS um JSON no seguinte formato, sem markdown ou explicações adicionais:
        {
            "nome_cientifico": "Genus species",
            "nome_comum": "Nome em Português (se possível)",
            "confianca": 0.95,
            "familia": "FamilyName"
        }
        """

        try:
            # Novo método generate_content
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[img, prompt]
            )
            
            # Limpar resposta (remover blocos de código Markdown se houver)
            texto_limpo = self._limpar_markdown_json(response.text)
            
            dados = json.loads(texto_limpo)
            return dados

        except Exception as e:
            # Fallback em caso de erro grave
            return {
                "erro": f"Falha na API Google GenAI: {str(e)}",
                "detalhes": str(e)
            }

    def _limpar_markdown_json(self, texto: str) -> str:
        """
        Remove formatação Markdown de blocos de código (```json ... ```) 
        para evitar erros no json.loads.
        """
        if not texto: return "{}"
        padrao = r"```json\s*(.*?)\s*```"
        match = re.search(padrao, texto, re.DOTALL)
        if match:
            return match.group(1)
        return texto.strip()
