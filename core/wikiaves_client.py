import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging

class WikiAvesClient:
    BASE_URL = "https://www.wikiaves.com.br"
    SEARCH_API = "https://www.wikiaves.com.br/getBusca.php"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.wikiaves.com.br/',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def _get_species_link(self, scientific_name):
        """
        Busca o 'slug' da espécie usando a API de autocomplete do WikiAves.
        Retorna a URL completa da página ou None.
        """
        try:
            # Limpeza e encode do termo
            term = quote(scientific_name.strip())
            url = f"{self.SEARCH_API}?term={term}"
            
            print(f"[WIKIAVES] Buscando API: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # O retorno é uma lista de objetos: 
                    # [{'label': 'Verão', 'nome': 'Pyrocephalus rubinus', 'link': 'verao', ...}]
                    
                    if data and isinstance(data, list):
                        # 1. Tenta match exato no nome científico (campo 'nome' ou 'info')
                        for item in data:
                            info_str = str(item.get('nome', '')) + str(item.get('info', ''))
                            if scientific_name.lower() in info_str.lower():
                                return f"{self.BASE_URL}/wiki/{item['link']}"
                        
                        # 2. Fallback: Retorna o primeiro resultado se tiver link
                        if len(data) > 0 and 'link' in data[0]:
                            print(f"[WIKIAVES] Match exato não encontrado. Usando primeiro resultado: {data[0]['link']}")
                            return f"{self.BASE_URL}/wiki/{data[0]['link']}"
                except ValueError:
                    print("[WIKIAVES] Erro ao decodificar JSON da busca.")
            else:
                print(f"[WIKIAVES] Erro na API de busca: {response.status_code}")
                
        except Exception as e:
            print(f"[WIKIAVES] Exceção na busca: {e}")
            
        return None

    def get_description(self, scientific_name):
        """
        Obtém a descrição e a fonte da espécie.
        """
        target_url = self._get_species_link(scientific_name)
        
        if not target_url:
            return "Descrição não encontrada no WikiAves.", self.BASE_URL
        try:
            print(f"[WIKIAVES] Acessando página: {target_url}")
            response = requests.get(target_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return "Erro ao carregar página do WikiAves.", target_url
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estratégia de Extração baseada no HTML analisado
            # Procura pela div.level2 que contém o texto principal
            content_div = soup.find('div', class_='level2')
            
            description = ""
            
            if content_div:
                # Pega parágrafos diretos para evitar pegar legendas de fotos aninhadas
                paragraphs = content_div.find_all('p', recursive=False)
                
                for p in paragraphs:
                    text = p.get_text().strip()
                    # Filtra parágrafos inúteis (links internos, metadados)
                    if len(text) > 50 and "DIMORFISMO" not in text:
                        description = text
                        break
            
            if not description:
                # Fallback: Tenta pegar qualquer p dentro de .m-t-5 se level2 falhar
                fallback_div = soup.find('div', class_='m-t-5')
                if fallback_div:
                    paragraphs = fallback_div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 50:
                            description = text
                            break
            if description:
                # Adiciona a atribuição obrigatória
                return f"{description}\n\nFonte: WikiAves (www.wikiaves.com.br)", target_url
            else:
                return "Texto descritivo não localizado na página.", target_url
        except Exception as e:
            print(f"[WIKIAVES] Erro no scraping: {e}")
            return f"Erro ao processar dados: {str(e)}", target_url
