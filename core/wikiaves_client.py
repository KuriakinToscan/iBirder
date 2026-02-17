import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging
import re

class WikiAvesClient:
    BASE_URL = "https://www.wikiaves.com.br"
    # Endpoint confirmado pelo usuário
    SEARCH_ENDPOINT = "https://www.wikiaves.com.br/buscasimples.php"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.wikiaves.com.br/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def _get_species_link(self, scientific_name):
        """
        Busca o link da espécie enviando o termo para buscasimples.php.
        """
        try:
            # Parâmetros padrão da busca do WikiAves:
            # t = s (provavelmente 'search' ou 'simple')
            # s = termo da busca
            # A chave correta é apenas 't=s' e 's=termo' conforme PHP
            # url final: buscasimples.php?t=s&s=Nome+Cientifico
            
            params = {
                't': 's', 
                's': scientific_name.strip()
            }
            
            # Construindo URL manualmente para garantir ordem se necessario, mas requests faz isso bem.
            print(f"[WIKIAVES] Consultando Backend: {self.SEARCH_ENDPOINT} com parametros: {params}")
            
            # allow_redirects=True é vital. Se houver match, o PHP vai dar 302 para /wiki/ave
            response = requests.get(self.SEARCH_ENDPOINT, params=params, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"[WIKIAVES] Erro HTTP: {response.status_code}")
                return None
            
            # Verifica URL final após redirecionamentos
            final_url = response.url
            if "/wiki/" in final_url and "buscasimples.php" not in final_url:
                print(f"[WIKIAVES] Match exato (Redirect): {final_url}")
                return final_url
            
            # Se não redirecionou, parseia a lista de resultados
            # Pode ter retornado a propria pagina de busca com resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                # Filtra links de espécie válidos
                # Geralmente links para especies sao relativos ou absolutos contendo /wiki/
                if "wiki/" in href or href.startswith("./wiki/"): 
                    # Ignorar links de sistema
                    if not any(x in href for x in ["index.php", "dicionario", "midias", "mapa", "som", "termos", "login"]):
                        # Normaliza URL
                        if not href.startswith("http"):
                            # href pode ser ./wiki/ave ou wiki/ave
                            clean_href = href.lstrip("./")
                            href = f"{self.BASE_URL}/{clean_href}"
                        
                        print(f"[WIKIAVES] Link na lista de resultados: {href}")
                        return href
            
            print("[WIKIAVES] Nenhum link de espécie encontrado na lista.")
            return None
                
        except Exception as e:
            print(f"[WIKIAVES] Erro fatal na busca: {e}")
            return None

    def get_description(self, scientific_name):
        # 1. Obter URL
        url_busca = self._get_species_link(scientific_name)
        
        target_url = url_busca if url_busca else None
        
        if not target_url:
            return "Espécie não encontrada via busca simples.", self.BASE_URL

        # 2. Extrair Conteúdo
        try:
            print(f"[WIKIAVES] Extraindo texto de: {target_url}")
            response = requests.get(target_url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return "Erro ao carregar página da espécie.", target_url

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estratégia Principal: div.level2 (Conteúdo principal)
            content_div = soup.find('div', class_='level2')
            description = ""
            
            if content_div:
                paragraphs = content_div.find_all('p', recursive=False)
                for p in paragraphs:
                    text = p.get_text().strip()
                    # Ignora metadados e textos curtos ou títulos disfarçados
                    if len(text) > 50 and "DIMORFISMO" not in text:
                        description = text
                        break
            
            # Fallback para layouts antigos ou estrutura diferente
            if not description:
                # Tenta pegar qualquer p com texto substancial
                ps = soup.find_all('p')
                for p in ps:
                    t = p.get_text().strip()
                    if len(t) > 60 and "DIMORFISMO" not in t:
                        description = t
                        break
            
            if description:
                # Adiciona créditos
                return f"{description}\n\nFonte: WikiAves (www.wikiaves.com.br)", target_url
            else:
                return "Descrição textual não disponível na página.", target_url

        except Exception as e:
            return f"Erro técnico no scraping: {str(e)}", target_url
