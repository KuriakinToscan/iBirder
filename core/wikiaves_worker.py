from PySide6.QtCore import QThread, Signal
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import re

class WikiAvesWorker(QThread):
    etymology_found = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name.replace(" ", "+") # URL friendly for search
        self.raw_name = species_name

    def run(self):
        print(f"[WIKIAVES] Worker iniciado para: {self.species_name}")
        if not BeautifulSoup:
            msg = "Biblioteca BeautifulSoup não instalada."
            print(f"[ERRO WIKIAVES] {msg}")
            self.error_occurred.emit("Erro interno: dependência ausente (bs4).")
            return

        try:
            # 1. Configuração (Emulação Chrome 120)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            # 2. Estratégia de Acesso Direto (Prioridade)
            # URL: https://www.wikiaves.com.br/wiki/genero_especie
            nome_direto = self.species_name.replace("+", "_").replace(" ", "_").lower()
            url_direta = f"https://www.wikiaves.com.br/wiki/{nome_direto}"
            
            print(f"[WIKIAVES] Tentando acesso direto via Chrome emulação: {url_direta}")
            
            resp_wa = requests.get(url_direta, headers=headers, timeout=10)
            soup_wa = None
            
            if resp_wa.status_code == 200:
                print("[WIKIAVES] Acesso direto com sucesso (200 OK).")
                soup_wa = BeautifulSoup(resp_wa.text, 'html.parser')
            else:
                print(f"[WIKIAVES] Acesso direto falhou ({resp_wa.status_code}). Tentando busca fallback...")
                
                # --- Fallback: Busca via DuckDuckGo (Código Antigo) ---
                # v0.10.11: InURL Search
                query = f'inurl:wikiaves.com.br "{self.raw_name}"'
                search_url = f"https://html.duckduckgo.com/html/?q={query}"
                try:
                    resp = requests.get(search_url, headers=headers, timeout=10)
                    
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        wa_link = None
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            if "wikiaves.com.br/" in href and "search" not in href and "uddg=" not in href:
                                wa_link = href
                                break
                        
                        if wa_link:
                            print(f"[WIKIAVES] Link encontrado via busca: {wa_link}")
                            resp_wa = requests.get(wa_link, headers=headers, timeout=10)
                            if resp_wa.status_code == 200:
                                soup_wa = BeautifulSoup(resp_wa.text, 'html.parser')
                except Exception as e_search:
                     print(f"[WIKIAVES] Erro na busca DuckDuckGo: {e_search}")

            if not soup_wa:
                print("[ERRO WIKIAVES] Não foi possível acessar a página da espécie.")
                return

            # 3. Extração da Etimologia (Refinada v0.10.11: CSS Selectors)
            print("[WIKIAVES] Analisando estrutura div.level2...")
            etimo_text = ""
            
            # Tenta encontrar o container específico sugerido (div.level2 > p)
            div_content = soup_wa.find("div", class_="level2")
            
            # Fallback para mks_text se level2 não existir
            if not div_content:
                 div_content = soup_wa.find("div", class_="mks_text")

            extracted = False
            full_text = ""
            
            if div_content:
                # Procura parágrafo com o trigger dentro do container
                 for p in div_content.find_all("p"):
                    text_p = p.get_text(" ", strip=True)
                    if "nome científico significa" in text_p or "nome cientifica significa" in text_p:
                        # Achou parágrafo alvo
                        full_text = text_p
                        extracted = True
                        break
            
            if not extracted:
                 # Fallback Global: Busca no soup inteiro se containers falharem
                 target = soup_wa.find(string=re.compile("Seu nome cientifica significa|Seu nome científico significa", re.IGNORECASE))
                 if target:
                      full_text = target.parent.get_text(" ", strip=True)
                      extracted = True

            if extracted:
                # Lógica de limpeza unificada
                # Regex para pegar o que vem depois de "significa"
                match = re.search(r"significa[:\s]*(.*)", full_text, re.IGNORECASE | re.DOTALL)
                if match:
                    etimo_text = match.group(1).strip()
                else:
                     # Split simples como fallback do regex
                     etimo_text = full_text.split("significa", 1)[-1].strip()
                
                # Limpeza final de pontuação inicial residual
                etimo_text = etimo_text.lstrip(":.- ").strip()
                if etimo_text:
                    etimo_text = etimo_text[0].upper() + etimo_text[1:]
                    
                print(f"[WIKIAVES] Sucesso! Texto extraído: {etimo_text[:50]}...")
            else:
                print("[ERRO WIKIAVES] Parágrafo de etimologia não encontrado na página.")

            if etimo_text and len(etimo_text) > 10:
                self.etymology_found.emit(etimo_text)

        except Exception as e:
            import traceback
            error_msg = f"Falha fatal no worker: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERRO WIKIAVES] {error_msg}")
            self.error_occurred.emit("Informações de etimologia temporariamente indisponíveis (WikiAves offline).")
