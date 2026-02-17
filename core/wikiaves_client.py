import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging
import re

class WikiAvesClient:
    BASE_URL = "https://www.wikiaves.com.br"
    SEARCH_ENDPOINT = "https://www.wikiaves.com.br/buscasimples.php"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.wikiaves.com.br/',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def _get_species_link(self, scientific_name):
        """
        Busca o link da espécie em buscasimples.php e valida se o link corresponde ao nome buscado.
        """
        try:
            # Limpa o nome e separa as partes (Genero e especie)
            sci_clean = scientific_name.strip().lower()
            parts = sci_clean.split()
            
            params = {'t': 's', 's': scientific_name}
            
            print(f"[WIKIAVES] Buscando: {scientific_name}...")
            response = requests.get(self.SEARCH_ENDPOINT, params=params, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"[WIKIAVES] Erro HTTP: {response.status_code}")
                return None
            
            # CASO 1: Redirecionamento Automático (Match Exato)
            if "/wiki/" in response.url and "buscasimples.php" not in response.url:
                # Verifica se não fomos jogados para uma página genérica (ex: wiki/aves)
                if "wiki/aves" not in response.url:
                    print(f"[WIKIAVES] Redirecionamento direto: {response.url}")
                    return response.url
            
            # CASO 2: Lista de Resultados
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text().lower()
                title = link.get('title', '').lower()
                
                # Filtra apenas links de wiki
                if "wiki/" in href:
                    # 1. Ignora links de sistema/taxonomia frequentes
                    if any(x in href for x in ["index.php", "dicionario", "midias", "mapa", "som", "aves", "pais", "estado"]):
                        continue
                        
                    # 2. CRITÉRIO DE OURO: O link precisa conter o nome da espécie (parcial ou total)
                    # Verifica se o 'epiteto específico' (ex: rubinus) está no texto do link ou no title
                    # Isso evita clicar em 'Passeriformes' ou 'Tyrannidae' no breadcrumb
                    if len(parts) > 1:
                        species_epithet = parts[1] # 'rubinus'
                        if species_epithet in text or species_epithet in title or species_epithet in href:
                            if not href.startswith("http"):
                                full_url = f"{self.BASE_URL}/{href.lstrip('/')}"
                            else:
                                full_url = href
                                
                            print(f"[WIKIAVES] Link validado (contém '{species_epithet}'): {full_url}")
                            return full_url
                    else:
                        # Se for só genero, tenta match direto
                        if sci_clean in text or sci_clean in title:
                            if not href.startswith("http"):
                                full_url = f"{self.BASE_URL}/{href.lstrip('/')}"
                            else:
                                full_url = href
                            return full_url
            
            print("[WIKIAVES] Nenhum link correspondente encontrado na lista de resultados.")
            return None
                
        except Exception as e:
            print(f"[WIKIAVES] Erro na busca: {e}")
            return None

    def get_description(self, scientific_name):
        target_url = self._get_species_link(scientific_name)
        
        if not target_url:
            return "Espécie não encontrada no WikiAves.", self.BASE_URL
        
        try:
            print(f"[WIKIAVES] Acessando página: {target_url}")
            response = requests.get(target_url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return "Erro ao carregar página.", target_url
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Lógica de Extração Refinada
            # Tenta pegar especificamente a div.level2 (conteúdo da espécie)
            content_div = soup.find('div', class_='level2')
            description = ""
            
            if content_div:
                paragraphs = content_div.find_all('p', recursive=False)
                for p in paragraphs:
                    text = p.get_text().strip()
                    # Filtra parágrafos de metadados
                    if len(text) > 40 and "DIMORFISMO" not in text and "Hierarquia" not in text:
                        description = text
                        break
            
            # Fallback: Se div.level2 falhar, procura em toda a página, mas com cuidado
            if not description:
                ps = soup.find_all('p')
                for p in ps:
                    t = p.get_text().strip()
                    if len(t) > 50 and "DIMORFISMO" not in t and "Hierarquia" not in t and "copyright" not in t.lower():
                        description = t
                        break
            
            if description:
                return f"{description}\n\nFonte: WikiAves (www.wikiaves.com.br)", target_url
            else:
                return "Descrição textual não disponível.", target_url
                
        except Exception as e:
            print(f"[WIKIAVES] Erro técnico: {e}")
            return f"Erro técnico ao extrair descrição: {str(e)}", target_url
