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
        # Import time for safety delay
        import time
        
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
            
            # 2. Estratégia de Busca Google (v0.10.15)
            # Busca: inurl:wikiaves.com.br "{nome_cientifico}"
            print(f"[TRACE 1] Pesquisando no Google: inurl:wikiaves.com.br {self.raw_name}")
            
            # Google Search URL
            encoded_query = f"inurl:wikiaves.com.br+{self.species_name}"
            google_url = f"https://www.google.com/search?q={encoded_query}"
            
            print(f"[WIKIAVES] Buscando URL correta via Google: {google_url}")
            resp_google = requests.get(google_url, headers=headers, timeout=10)
            
            wa_link = None
            if resp_google.status_code == 200:
                soup_google = BeautifulSoup(resp_google.text, 'html.parser')
                
                # Extração do Link (v0.10.15)
                # Google structure varies, looking for <a href="..."> that contains wikiaves.com.br/wiki/
                for a in soup_google.find_all('a', href=True):
                    href = a['href']
                    # Filtra links válidos do WikiAves (evita google.com/url?q=...)
                    if "wikiaves.com.br/wiki/" in href:
                        # Limpa redirecionamentos do Google se houver
                        if href.startswith("/url?q="):
                            href = href.split("/url?q=")[1].split("&")[0]
                        
                        wa_link = href
                        print(f"[TRACE 2] Link encontrado no Google: {wa_link}")
                        break
            else:
                print(f"[ERRO WIKIAVES] Falha na busca Google ({resp_google.status_code})")
            
            if not wa_link:
                # Fallback: Tentar acesso direto (antigo) se Google falhar
                print("[TRACE 2] Link não encontrado no Google. Tentando acesso direto (fallback)...")
                nome_direto = self.species_name.replace("+", "_").replace(" ", "_").lower()
                wa_link = f"https://www.wikiaves.com.br/wiki/{nome_direto}"

            # Segurança: Delay para evitar bloqueio
            time.sleep(2)

            # 3. Acessar Página da Espécie
            print(f"[TRACE 3] Acessando página da espécie: {wa_link}...")
            resp_wa = requests.get(wa_link, headers=headers, timeout=10)
            print(f"[TRACE 3] Resposta recebida. Status Code: {resp_wa.status_code}")
            
            # v0.10.14: Debug Raw Dump (Mantido)
            try:
                import os
                os.makedirs("temp", exist_ok=True)
                with open("temp/full_page_debug.html", "w", encoding="utf-8") as f:
                    f.write(resp_wa.text)
                # print(f"[DEBUG] HTML bruto salvo em temp/full_page_debug.html") 
            except Exception:
                pass

            soup_wa = None
            if resp_wa.status_code == 200:
                print("[TRACE 4] Iniciando BeautifulSoup no conteúdo HTML...")
                soup_wa = BeautifulSoup(resp_wa.text, 'html.parser')
            else:
                 print(f"[ERRO WIKIAVES] Falha ao acessar página da espécie ({resp_wa.status_code})")
                 return

            if not soup_wa:
                return

            # 4. Extração da Etimologia (Refinada v0.10.13: CSS Selectors + Text Match)
            print("[WIKIAVES] Analisando estrutura div.level2...")
            # Tenta encontrar o container específico sugerido (div.level2 > p)
            div_content = soup_wa.find("div", class_="level2")
            
            # Fallback para mks_text se level2 não existir
            if not div_content:
                 div_content = soup_wa.find("div", class_="mks_text")

            extracted = False
            full_text = ""
            
            if div_content:
                # Debug Dump (Mantido)
                try:
                    import os
                    with open("temp/debug_wikiaves.html", "w", encoding="utf-8") as f:
                        f.write(div_content.prettify())
                except Exception:
                    pass

                print("[TRACE 6] Div encontrada. Buscando parágrafo de etimologia...")
                # Procura parágrafo com o trigger dentro do container
                for p in div_content.find_all("p"):
                    text_p = p.get_text(" ", strip=True)
                    text_lower = text_p.lower()
                    if "nome científico significa" in text_lower or "nome cientifica significa" in text_lower:
                        # Achou parágrafo alvo
                        full_text = text_p
                        extracted = True
                        print(f"[TRACE 7] Parágrafo localizado: {text_p[:50]}...")
                        break
            
            if not extracted:
                 print("[TRACE 6] Parágrafo não encontrado no container. Tentando busca global...")
                 # Fallback Global
                 target = soup_wa.find(string=re.compile("Seu nome cientifica significa|Seu nome científico significa", re.IGNORECASE))
                 if target:
                      full_text = target.parent.get_text(" ", strip=True)
                      extracted = True
                      print("[TRACE 7] Texto localizado via busca global.")

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
            print(f"[ERRO FATAL WIKIAVES] {error_msg}")
            self.error_occurred.emit("Informações de etimologia temporariamente indisponíveis (WikiAves offline).")
