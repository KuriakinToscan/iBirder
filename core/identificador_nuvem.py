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
        Analise esta imagem cuidadosamente.
        1. Se a imagem NÃO for de uma ave (ex: cachorro, gato, objeto, pessoa), retorne APENAS:
        {"erro": "nao_ave"}
        
        2. Se FOR uma ave, identifique a espécie com alta precisão e retorne APENAS um JSON válido no seguinte formato:
        {
            "nome_cientifico": "Genus species",
            "nome_comum": "Nome popular oficial em Português do Brasil",
            "familia": "Família científica",
            "confianca": 0.99,
            "descricao": "Uma breve descrição visual e comportamental da ave em Português, com no máximo 20 palavras."
        }
        Responda APENAS o JSON, sem markdown.
        """

        try:
            # Novo método generate_content
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=[img, prompt]
            )
            
            # Limpar resposta (remover blocos de código Markdown se houver)
            texto_limpo = self._limpar_markdown_json(response.text)
            
            dados = json.loads(texto_limpo)
            
            # Tratamento de "Não-Ave" (v0.3.7)
            if "erro" in dados and dados["erro"] == "nao_ave":
                return {
                    "erro": "Não consegui identificar uma ave nesta foto.",
                    "detalhes": "A inteligência artificial analisou a imagem e não encontrou características de aves. Certifique-se de que a imagem está clara e contém um pássaro."
                }
                
            return dados

        except Exception as e:
            msg_erro = str(e)
            
            # Tratamento Amigável de Erro 429 (Cota/Busy) (v0.3.7/v0.3.8)
            if "429" in msg_erro:
                return {
                    "erro": "O servidor de inteligência está ocupado.",
                    "detalhes": "Tente novamente em um minuto. (Erro 429 - Limite de Requisições)"
                }
            
            return {
                "erro": f"Falha na API Google GenAI: {msg_erro}",
                "detalhes": msg_erro
            }

    def consultar_especie(self, nome_cientifico: str) -> dict:
        """
        Consulta informações sobre uma espécie pelo nome científico (v0.4.0).
        """
        chave_api = self._obter_chave_api()
        client = genai.Client(api_key=chave_api)
        
        prompt = f"""
        Você é um ornitólogo especialista.
        Forneça o Nome Comum (em Português do Brasil), Família e uma Descrição de até 20 palavras em Português para a espécie "{nome_cientifico}".
        
        Se a espécie não existir ou o nome estiver muito errado, retorne APENAS:
        {{"erro": "Especie não encontrada"}}
        
        Caso contrário, retorne APENAS um JSON válido neste formato:
        {{
            "nome_cientifico": "{nome_cientifico}",
            "nome_comum": "Nome popular em Pt-BR",
            "familia": "Família científica",
            "confianca": "Validado Manualmente",
            "descricao": "Descrição visual e comportamental breve."
        }}
        Sem markdown.
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=[prompt]
            )
            
            texto_limpo = self._limpar_markdown_json(response.text)
            dados = json.loads(texto_limpo)
            
            if "erro" in dados:
                return {"erro": "Espécie não encontrada. Verifique a grafia e tente novamente."}
                
            return dados
            
        except Exception as e:
            msg_erro = str(e)
            if "429" in msg_erro:
                return {
                    "erro": "O servidor de inteligência está ocupado.",
                    "detalhes": "Tente novamente em um minuto."
                }
            return {
                "erro": f"Falha na busca manual: {msg_erro}",
                "detalhes": msg_erro
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
