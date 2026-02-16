from PySide6.QtCore import QThread, Signal
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import re

class WikiAvesWorker(QThread):
    etymology_found = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name.replace(" ", "+") # URL friendly for search
        self.raw_name = species_name

    def run(self):
        if not BeautifulSoup:
            return

        try:
            # 1. Configuração
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # 2. Busca no DuckDuckGo HTML
            # site:wikiaves.com.br "Nome Cientifico"
            query = f'site:wikiaves.com.br "{self.raw_name}"'
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 3. Encontrar Link do WikiAves
            wa_link = None
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "wikiaves.com.br/" in href and "search" not in href:
                    # DuckDuckGo as vezes coloca o link dentro de um redirect
                    if "uddg=" in href:
                        # Tentar extrair do parametro ou apenas pegar o href
                        # Geralmente o href direto funciona no html.duckduckgo
                        pass
                    
                    wa_link = href
                    break
            
            if not wa_link:
                return

            # 4. Acessar WikiAves
            resp_wa = requests.get(wa_link, headers=headers, timeout=10)
            if resp_wa.status_code != 200:
                return
            
            soup_wa = BeautifulSoup(resp_wa.text, 'html.parser')
            
            # 5. Extração da Etimologia
            # Procurar texto "Seu nome científico significa"
            # O texto costuma estar em um span ou p. Vamos buscar pelo string.
            target = soup_wa.find(string=re.compile("Seu nome cientifica significa|Seu nome científico significa", re.IGNORECASE))
            
            etimo_text = ""
            
            if target:
                # O texto alvo é geralmente "Seu nome científico significa:"
                # O conteudo real vem depois ou está no parent.
                parent = target.parent
                # Pegar o texto completo do parágrafo/container
                full_text = parent.get_text(" ", strip=True)
                
                # Limpeza: Remover a frase gatilho e tudo antes dela
                # Ex: "Etimologia: Seu nome científico significa..." -> "do latim..."
                split_token = "significa"
                if split_token in full_text:
                     parts = full_text.split(split_token, 1)
                     if len(parts) > 1:
                         etimo_text = parts[1]
                else:
                    etimo_text = full_text
                    
                # Limpeza final de pontuação inicial
                etimo_text = etimo_text.lstrip(":").strip()
                # Capitalizar primeira letra
                if etimo_text:
                    etimo_text = etimo_text[0].upper() + etimo_text[1:]

            if etimo_text and len(etimo_text) > 10:
                self.etymology_found.emit(etimo_text)

        except Exception as e:
            # Falha silenciosa confoorme solicitado
            print(f"[WIKIAVES] Erro: {e}")
            pass
