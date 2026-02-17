import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

class WikiAvesClient:
    """
    Cliente robusto para scraping direcionado do WikiAves.
    Baseado em engenharia reversa do HTML v0.2.1.
    """
    BASE_URL = "https://www.wikiaves.com.br"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': self.BASE_URL
        })

    def _get_page_url(self, scientific_name):
        """
        Descobre a URL da página da espécie através da API getBusca.
        Retorna o sufixo do link (ex: 'joao-de-barro') ou None.
        """
        try:
            # Ação: GET em getBusca.php
            term = quote(scientific_name)
            url = f"{self.BASE_URL}/getBusca.php?tm=s&t=s&term={term}"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    # Retorno: campo 'link' do primeiro resultado
                    # O campo link geralmente vem como "http://www.wikiaves.com.br/joao-de-barro" ou apenas "joao-de-barro"
                    # O user disse que retorna "joao-de-barro" no exemplo, mas a API costuma retornar full URL ou relative.
                    # Vamos tratar ambos.
                    link = data[0].get("link")
                    if link:
                        return link.split('/')[-1] # Garante pegar só o slug final
            return None
        except Exception as e:
            print(f"[WikiAvesClient] Erro ao buscar URL: {e}")
            return None

    def get_description(self, scientific_name):
        """
        Obtém a descrição e a URL da fonte para uma espécie.
        Retorna tupla (descricao, url_fonte).
        """
        try:
            # Passo 1: Descobrir Link
            slug = self._get_page_url(scientific_name)
            if not slug:
                return "Espécie não encontrada no WikiAves.", ""

            # Passo 2: Montar URL
            url_fonte = f"{self.BASE_URL}/wiki/{slug}"
            
            # Passo 3: GET e Scraping
            resp = self.session.get(url_fonte, timeout=15)
            if resp.status_code != 200:
                return "Erro ao carregar página da espécie.", url_fonte

            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Lógica de Extração Atualizada (Targeted .level2)
            description = "Descrição indisponível."
            
            # Alvo direto identificado no HTML fornecido
            content_div = soup.find('div', class_='level2')
            
            if content_div:
                # Pega todos os parágrafos diretos
                paragraphs = content_div.find_all('p', recursive=False)
                for p in paragraphs:
                    text = p.get_text().strip()
                    # Filtra parágrafos vazios ou que sejam apenas títulos de metadados
                    if len(text) > 50 and "DIMORFISMO" not in text:
                        description = text
                        break # Pega apenas o primeiro parágrafo robusto
            
            return description, url_fonte

        except Exception as e:
            print(f"[WikiAvesClient] Erro no scraping: {e}")
            return f"Erro ao obter descrição: {str(e)}", ""
