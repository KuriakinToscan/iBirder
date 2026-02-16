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
        etimo_text = None # Inicialização para evitar UnboundLocalError
        
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
                
                # v0.10.17: Verificação de Título (CAPTCHA check)
                if soup_google.title:
                    print(f"[WIKIAVES] Título da página do Google: {soup_google.title.string}")

                # Extração do Link (v0.10.17: Universal Selector)
                import urllib.parse
                for a in soup_google.find_all('a', href=True):
                    href = a['href']
                    if "wikiaves.com.br/wiki/" in href:
                        # Limpeza de redirecionamento do Google
                        if "/url?q=" in href:
                            href = href.split("/url?q=")[1].split("&")[0]
                            href = urllib.parse.unquote(href)
                        
                        wa_link = href
                        print(f"[TRACE 2] Link extraído do Google: {wa_link}")
                        break
                
                # Debug Dump se falhar
                if not wa_link:
                     try:
                        import os
                        os.makedirs("temp", exist_ok=True)
                        with open("temp/google_results_debug.html", "w", encoding="utf-8") as f:
                            f.write(resp_google.text)
                        print("[DEBUG] HTML da busca Google salvo em temp/google_results_debug.html")
                     except Exception: 
                        pass
            else:
                print(f"[ERRO WIKIAVES] Falha na busca Google ({resp_google.status_code})")
            
            if not wa_link:
                # Nova Regra: Se o Google não retornar um link de WikiAves, o worker deve emitir um erro amigável e encerrar
                print("[ERRO WIKIAVES] Link não encontrado no Google. Encerrando busca.")
                return

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

            # 4. Extração da Etimologia (Refinada v0.10.16: Text Search Global)
            print(f"[WIKIAVES] Analisando a página: {wa_link}")
            
            # Procure por qualquer elemento que contenha a frase gatilho
            # Busca em p, div, strong, span
            trigger_element = soup_wa.find(lambda tag: tag.name in ['p', 'div', 'strong', 'span'] and "seu nome científico significa" in tag.text.lower())
            
            if trigger_element:
                print("[TRACE 6] Frase gatilho encontrada.")
                # Pegue o texto completo do container pai se o elemento for inline (strong/span) ou se o texto for muito curto
                full_text = trigger_element.get_text(" ", strip=True)
                
                if len(full_text) < 60 or trigger_element.name in ['strong', 'b', 'span']:
                     if trigger_element.parent:
                         full_text = trigger_element.parent.get_text(" ", strip=True)
                
                # Use o split... mas com segurança de case
                import re
                # Regex para pegar o que vem depois de "significa" (ignorando case e dois pontos)
                match = re.search(r"significa[:\s]*(.*)", full_text, re.IGNORECASE | re.DOTALL)
                
                if match:
                    etimo_text = match.group(1).strip()
                else:
                    # Fallback split simples
                    parts = full_text.lower().split("significa")
                    if len(parts) > 1:
                        # Recupera o texto original usando o tamanho da parte anterior
                        start_index = len(parts[0]) + len("significa")
                        etimo_text = full_text[start_index:].lstrip(": ").strip()
                    else:
                        etimo_text = full_text

                # Limpeza final de pontuação inicial residual
                etimo_text = etimo_text.lstrip(":.- ").strip()
                if etimo_text:
                    etimo_text = etimo_text[0].upper() + etimo_text[1:]
                    
                print(f"[WIKIAVES] Sucesso! Texto extraído: {etimo_text[:50]}...")
            else:
                print("[ERRO WIKIAVES] Frase 'Seu nome científico significa' não encontrada na página.")

            if etimo_text and len(etimo_text) > 10:
                self.etymology_found.emit(etimo_text)

        except Exception as e:
            import traceback
            error_msg = f"Falha fatal no worker: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERRO FATAL WIKIAVES] {error_msg}")
            self.error_occurred.emit("Informações de etimologia temporariamente indisponíveis (WikiAves offline).")
