from google import genai
from google.genai import types
import keyring
import json
import re
from pathlib import Path
from PIL import Image # Pillow para abrir imagem se necessário
from .interfaces import IdentificadorAve
from .erros import ChaveApiFaltandoErro
from .utils import otimizar_imagem

class IdentificadorNuvem(IdentificadorAve):
    def __init__(self):
        # Nome do serviço no keyring
        self.servico_keyring = "iBirder_Gemini_Key" 

    def _obter_chave_api(self):
        chave = keyring.get_password(self.servico_keyring, "user")
        if not chave:
            raise ChaveApiFaltandoErro("Chave de API do Google não encontrada no keyring.")
        return chave

    def testar_conexao(self) -> bool:
        """
        Testa a conectividade com a API do Gemini (v0.7.3).
        Retorna True se sucesso, False se falha.
        """
        try:
            chave_api = self._obter_chave_api()
            client = genai.Client(api_key=chave_api)
            # Teste leve: gerar algo simples
            client.models.generate_content(
                model='gemini-2.0-flash', 
                contents="Oi",
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=5
                )
            )
            return True
        except Exception as e:
            print(f"[CONEXAO] Falha no teste de API: {e}")
            return False

    def _gerar_conteudo_com_retry(self, client, model, contents, config=None, tentativas=3):
        """
        Tenta gerar conteúdo com lógica de retry (backoff) para erros de servidor ocupado (v0.7.3).
        """
        import time

        for i in range(tentativas):
            try:
                return client.models.generate_content(
                    model=model, 
                    contents=contents,
                    config=config
                )
            except Exception as e:
                erro_str = str(e)
                # Verifica erros típicos de sobrecarga: 429 (Too Many Requests), 503 (Service Unavailable)
                eh_ultimo = (i == tentativas - 1)
                if ("429" in erro_str or "503" in erro_str or "occup" in erro_str.lower() or "busy" in erro_str.lower()) and not eh_ultimo:
                    print(f"[RETRY] Servidor ocupado (Tentativa {i+1}/{tentativas}). Aguardando 2s...")
                    time.sleep(2)
                    continue
                else:
                    raise e 

    def identificar(self, caminho_imagem: str) -> dict:
        chave_api = self._obter_chave_api()
        client = genai.Client(api_key=chave_api)

        imagem_path = Path(caminho_imagem)
        if not imagem_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {caminho_imagem}")

        # v0.8.2: Otimização de Imagem (Resize/Compress) para economizar cota (Tier 1)
        temp_path = Path(__file__).parent.parent / "temp" / "temp_upload.jpg"
        
        # Tenta otimizar, se falhar usa a original
        if otimizar_imagem(caminho_imagem, str(temp_path)):
             img = Image.open(temp_path)
        else:
             img = Image.open(caminho_imagem)

        prompt = """
        Atue como um ornitólogo sênior. Analise a imagem fornecida. Identifique a espécie com precisão taxonômica.
        
        1. Se a imagem NÃO for de uma ave, retorne APENAS: {"erro": "nao_ave"}
        
        2. Se FOR uma ave, retorne APENAS um JSON estrito com as chaves:
        {
            "nome_cientifico": "Genus species",
            "nome_comum": "Nome popular oficial em Português do Brasil",
            "familia": "Família científica",
            "confianca": 0.99,
            "descricao_detalhada": "Descrição técnica mencionando plumagem e características chave, em Português, máx 30 palavras."
        }
        """

        try:
            # v0.7.3: Retry Logic
            response = self._gerar_conteudo_com_retry(
                client, 
                'gemini-2.0-flash', 
                [img, prompt]
            )
            
            texto_limpo = self._limpar_markdown_json(response.text)
            dados = json.loads(texto_limpo)
            
            # v0.7.5: Mapeamento de Compatibilidade
            if "descricao_detalhada" in dados:
                dados["descricao"] = dados["descricao_detalhada"]
            
            if "erro" in dados and dados["erro"] == "nao_ave":
                return {
                    "erro": "Não consegui identificar uma ave nesta foto.",
                    "detalhes": "A inteligência artificial analisou a imagem e não encontrou características de aves. Certifique-se de que a imagem está clara e contém um pássaro."
                }
                
            return dados

        except Exception as e:
            msg_erro = str(e)
            if "429" in msg_erro or "503" in msg_erro:
                return {
                    "erro": "Servidor Ocupado (Cota Excedida)",
                    "detalhes": "Aguardando liberação do servidor... Tente novamente em alguns segundos."
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
        Atue como um ornitólogo sênior. 
        Analise a espécie "{nome_cientifico}".
        Forneça dados com precisão taxonômica.
        
        Se a espécie não existir ou o nome estiver muito errado, retorne APENAS:
        {{"erro": "Especie não encontrada"}}
        
        Caso contrário, retorne APENAS um JSON estrito com as chaves:
        {{
            "nome_cientifico": "{nome_cientifico}",
            "nome_comum": "Nome popular oficial em Pt-BR",
            "familia": "Família científica",
            "confianca": "Validado Manualmente",
            "descricao_detalhada": "Descrição técnica mencionando plumagem e características chave, em Português, máx 30 palavras."
        }}
        """
        
        try:
            # v0.7.3: Retry Logic
            response = self._gerar_conteudo_com_retry(
                client, 
                'gemini-2.0-flash', 
                [prompt]
            )
            
            texto_limpo = self._limpar_markdown_json(response.text)
            dados = json.loads(texto_limpo)
            
            # v0.7.5: Mapeamento de Compatibilidade
            if "descricao_detalhada" in dados:
                dados["descricao"] = dados["descricao_detalhada"]
            
            if "erro" in dados:
                return {"erro": "Espécie não encontrada. Verifique a grafia e tente novamente."}
                
            return dados
            
        except Exception as e:
            msg_erro = str(e)
            if "429" in msg_erro or "503" in msg_erro:
                return {
                    "erro": "Conexão Instável (Servidor Ocupado)",
                    "detalhes": "Alta demanda no servidor de IA. Aguarde um momento."
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
