import google.generativeai as genai
import keyring
import json
import re
from pathlib import Path
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
        genai.configure(api_key=chave_api)

        # Modelo recomendado: gemini-1.5-flash (rápido e barato/gratuito)
        model = genai.GenerativeModel('gemini-1.5-flash')

        imagem_path = Path(caminho_imagem)
        if not imagem_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {caminho_imagem}")

        # Carregar imagem para a API (upload temporário)
        myfile = genai.upload_file(imagem_path)

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

        response = model.generate_content([myfile, prompt])
        
        # Limpar resposta (remover blocos de código Markdown se houver)
        texto_limpo = self._limpar_markdown_json(response.text)
        
        try:
            dados = json.loads(texto_limpo)
            return dados
        except json.JSONDecodeError:
            # Fallback em caso de erro grave no JSON, retorna texto cru para debug
            return {
                "erro": "Falha ao decodificar JSON da API",
                "resposta_crua": response.text
            }

    def _limpar_markdown_json(self, texto: str) -> str:
        """
        Remove formatação Markdown de blocos de código (```json ... ```) 
        para evitar erros no json.loads.
        """
        padrao = r"```json\s*(.*?)\s*```"
        match = re.search(padrao, texto, re.DOTALL)
        if match:
            return match.group(1)
        # Se não tiver markdown, tenta retornar o texto original limpo
        return texto.strip()
