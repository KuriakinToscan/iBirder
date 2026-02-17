import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import random
import time
import logging

class WikiAvesClient:
    BASE_URL = "https://www.wikiaves.com.br"
    # Endpoint correto para busca de formulário (confirmado)
    SEARCH_ENDPOINT = "https://www.wikiaves.com.br/buscasimples.php"

    def __init__(self):
        self.session = requests.Session()
        # Headers para emular navegador real (evita bloqueio)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.wikiaves.com.br/',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        self.session.headers.update(self.headers)

    def _random_delay(self):
        """Pequeno delay para não sobrecarregar o servidor (Ética de Scraping)."""
        if hasattr(time, 'sleep'):
            time.sleep(random.uniform(0.5, 1.5))

    def _get_species_link(self, scientific_name):
        """
        Busca a URL da espécie, lidando com redirecionamentos 302 ou listas HTML.
        """
        try:
            # Limpeza do nome para validação posterior
            parts = scientific_name.lower().split()
            # Se tiver 'Genero especie', valida 'especie'. Se só 'Genero', valida 'genero'.
            specific_epithet = parts[1] if len(parts) > 1 else parts[0]
            
            # Parâmetros padrão do formulário do WikiAves: 'termo' é o name do input?
            # O input name no HTML é 's' e 't=s'. O usuário mandou 'termo' na request.
            # Verificando a request do usuário: params = {'termo': scientific_name}
            # Se buscasimples.php aceita 'termo', OK. O código anterior usava 't=s' e 's=Nome'.
            # Vou confiar no código fornecido pelo usuário.
            params = {'termo': scientific_name}
            
            print(f"[WIKIAVES] Consultando: {self.SEARCH_ENDPOINT} com '{scientific_name}'")
            # allow_redirects=True segue o 302 se houver match exato
            response = self.session.get(self.SEARCH_ENDPOINT, params=params, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"[WIKIAVES] Erro HTTP: {response.status_code}")
                return None
            
            # CENÁRIO A: Redirecionamento Direto (Ideal)
            # Se a URL final contém '/wiki/' e não é uma busca, achamos!
            if "/wiki/" in response.url and "buscasimples.php" not in response.url:
                # Validação extra: O link não pode ser genérico (ex: wiki/aves)
                if "wiki/aves" not in response.url:
                    print(f"[WIKIAVES] Redirecionamento confirmado: {response.url}")
                    return response.url
            
            # CENÁRIO B: Lista de Resultados (Parsing)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text().lower()
                title = link.get('title', '').lower()
                
                # Filtra links que parecem ser de espécies
                if "wiki/" in href:
                    # 1. Ignora links administrativos/taxonomia
                    if any(x in href for x in ["index.php", "dicionario", "midias", "mapa", "som", "aves", "estado", "pais"]):
                        continue
                    
                    # 2. HEURÍSTICA DE VALIDAÇÃO:
                    # O link ou o texto dele PRECISA conter parte do nome científico (ex: 'rubinus')
                    if specific_epithet in href or specific_epithet in text or specific_epithet in title:
                        # Corrige URL relativa se necessário
                        clean_href = href
                        if not clean_href.startswith("http"):
                            clean_href = f"{self.BASE_URL}/{href.lstrip('/')}"
                            
                        print(f"[WIKIAVES] Link validado na lista: {clean_href}")
                        return clean_href
            
            print("[WIKIAVES] Nenhum link validado encontrado na lista.")
            return None
        except Exception as e:
            print(f"[WIKIAVES] Erro na busca de link: {e}")
            return None

    def get_description(self, scientific_name):
        self._random_delay()
        target_url = self._get_species_link(scientific_name)
        
        if not target_url:
            return "Espécie não encontrada no WikiAves.", self.BASE_URL
        
        try:
            print(f"[WIKIAVES] Extraindo conteúdo de: {target_url}")
            response = self.session.get(target_url, timeout=15)
            response.encoding = 'utf-8' # Força UTF-8 para acentos
            
            soup = BeautifulSoup(response.text, 'html.parser')
            description = ""
            
            # ESTRATÉGIA 1: Busca Semântica (div.level2)
            # Onde geralmente reside o texto principal
            content_div = soup.find('div', class_='level2')
            if content_div:
                paragraphs = content_div.find_all('p', recursive=False)
                for p in paragraphs:
                    text = p.get_text().strip()
                    # Filtra metadados e textos curtos
                    if len(text) > 50 and "DIMORFISMO" not in text:
                        description = text
                        break
            
            # ESTRATÉGIA 2: Heurística por Palavras-Chave (Fallback do Relatório)
            # Se a estratégia 1 falhar, procura em TODOS os parágrafos por medidas ("cm", "mede")
            if not description:
                print("[WIKIAVES] Estratégia 1 falhou. Tentando heurística de medidas...")
                all_ps = soup.find_all('p')
                for p in all_ps:
                    t = p.get_text().strip()
                    # Padrão típico de descrição: "Mede X cm..."
                    if ("mede" in t.lower() or "cm" in t.lower()) and len(t) > 40:
                        description = t
                        break
            
            if description:
                return f"{description}\n\nFonte: WikiAves (www.wikiaves.com.br)", target_url
            else:
                return "Descrição textual não disponível para esta espécie.", target_url
                
        except Exception as e:
            return f"Erro técnico na extração: {str(e)}", target_url
