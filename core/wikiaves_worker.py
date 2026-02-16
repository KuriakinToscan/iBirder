from PySide6.QtCore import QThread, Signal
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import re

class WikiAvesWorker(QThread):
    # v0.13.0: Alterado para emitir dicionário com múltiplos dados
    etymology_found = Signal(dict) 
    error_occurred = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name.replace(" ", "+") # URL friendly for search
        self.raw_name = species_name

    def run(self):
        # Import time for safety delay
        import time
        import re
        
        # Inicializa dicionário de resultados
        resultado = {
            "etimologia": None,
            "nome_ingles": None,
            "familia": None,
            "ordem": None,
            "mapa_url": None,
            "link_wikiaves": None
        }
        
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
            
            # 2. Estratégia de Busca Interna (v0.13.0)
            # URL: https://www.wikiaves.com.br/pesquisa.php?t=s&s={nome_cientifico}
            search_url = f"https://www.wikiaves.com.br/pesquisa.php?t=s&s={self.species_name}"
            print(f"[TRACE 1] Iniciando busca interna: {search_url}")
            
            # Requests segue redirects automaticamente por padrão
            resp_search = requests.get(search_url, headers=headers, timeout=15)
            print(f"[TRACE 2] Resposta recebida. Status: {resp_search.status_code}. URL Final: {resp_search.url}")

            wa_link = resp_search.url
            
            # Verifica se foi redirecionado para uma página de espécie (/wiki/)
            if "/wiki/" in wa_link:
                print(f"[WIKIAVES] Redirecionamento direto para: {wa_link}")
                resultado["link_wikiaves"] = wa_link
            else:
                # Se não redirecionou, analisa o resultado da busca (pode ser uma lista ou página de erro)
                soup_search = BeautifulSoup(resp_search.text, 'html.parser')
                # Tenta achar o primeiro link de espécie na lista de resultados
                found_link = None
                for a in soup_search.find_all('a', href=True):
                    if "/wiki/" in a['href']:
                        found_link = a['href']
                        if not found_link.startswith("http"):
                            found_link = "https://www.wikiaves.com.br" + found_link
                        break
                
                if found_link:
                    wa_link = found_link
                    print(f"[WIKIAVES] Link encontrado na lista de busca: {wa_link}")
                    resultado["link_wikiaves"] = wa_link
                    # Acessa a página encontrada
                    time.sleep(1)
                    resp_search = requests.get(wa_link, headers=headers, timeout=15)
                else:
                    print("[ERRO WIKIAVES] Espécie não encontrada na busca interna.")
                    self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                    return

            if resp_search.status_code != 200:
                 print(f"[ERRO WIKIAVES] Falha ao acessar página da espécie ({resp_search.status_code})")
                 return

            soup_wa = BeautifulSoup(resp_search.text, 'html.parser')

            # --- EXTRAÇÃO DE DADOS (v0.13.0) ---

            # A. Nome em Inglês
            try:
                english_tag = soup_wa.find(string=re.compile("Nome em Inglês:"))
                if english_tag:
                    parent_text = english_tag.parent.parent.get_text(" ", strip=True)
                    if "Nome em Inglês:" in parent_text:
                        english_name = parent_text.split("Nome em Inglês:")[-1].strip()
                        english_name = english_name.split("Also")[0].strip() 
                        resultado["nome_ingles"] = english_name
                        print(f"[WIKIAVES] Nome em Inglês: {english_name}")
            except Exception as e:
                print(f"[DEBUG] Erro extraindo nome inglês: {e}")

            # B. Taxonomia (Família e Ordem)
            try:
                tabela_tax = soup_wa.find("table", id="taxonomia")
                if tabela_tax:
                    rows = tabela_tax.find_all("tr")
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 2:
                            label = cols[0].get_text(strip=True).replace(":", "")
                            value = cols[1].get_text(strip=True)
                            
                            if "Ordem" in label:
                                resultado["ordem"] = value
                            elif "Família" in label:
                                resultado["familia"] = value
                    
                    print(f"[WIKIAVES] Taxonomia: Ordem={resultado['ordem']}, Família={resultado['familia']}")
            except Exception as e:
                print(f"[DEBUG] Erro extraindo taxonomia: {e}")

            # C. Mapa de Ocorrência
            try:
                img_map = soup_wa.find("img", src=re.compile("mapaocorrencia.php"))
                if img_map:
                    src = img_map['src']
                    if not src.startswith("http"):
                        src = "https://www.wikiaves.com.br/" + src.lstrip("/")
                    resultado["mapa_url"] = src
                    print(f"[WIKIAVES] Mapa encontrado: {src}")
            except Exception as e:
                print(f"[DEBUG] Erro extraindo mapa: {e}")

            # D. Status de Conservação (IUCN) v0.14.0
            try:
                # Procura pela imagem do status ou texto próximo
                img_status = soup_wa.find("img", src=re.compile("status_"))
                if img_status and img_status.get("title"):
                    resultado["conservacao"] = img_status.get("title")
                    print(f"[WIKIAVES] Conservação (Img Title): {resultado['conservacao']}")
                
                if not resultado.get("conservacao"):
                    status_tag = soup_wa.find(string=re.compile("Estado de Conservação:"))
                    if status_tag:
                         parent_text = status_tag.parent.parent.get_text(" ", strip=True)
                         if "Estado de Conservação:" in parent_text:
                             status = parent_text.split("Estado de Conservação:")[-1].strip()
                             resultado["conservacao"] = status
                             print(f"[WIKIAVES] Conservação (Texto): {status}")

            except Exception as e:
                 print(f"[DEBUG] Erro extraindo conservação: {e}")

            # E. Etimologia (Lógica Refinada v0.10.16)
            print(f"[WIKIAVES] Extraindo etimologia...")
            etimo_text = None
            
            trigger_element = soup_wa.find(lambda tag: tag.name in ['p', 'div', 'strong', 'span'] and "seu nome científico significa" in tag.text.lower())
            
            if trigger_element:
                full_text = trigger_element.get_text(" ", strip=True)
                
                if len(full_text) < 60 or trigger_element.name in ['strong', 'b', 'span']:
                     if trigger_element.parent:
                         full_text = trigger_element.parent.get_text(" ", strip=True)
                
                import re
                match = re.search(r"significa[:\s]*(.*)", full_text, re.IGNORECASE | re.DOTALL)
                
                if match:
                    etimo_text = match.group(1).strip()
                else:
                    parts = full_text.lower().split("significa")
                    if len(parts) > 1:
                        start_index = len(parts[0]) + len("significa")
                        etimo_text = full_text[start_index:].lstrip(": ").strip()
                    else:
                        etimo_text = full_text

                etimo_text = etimo_text.lstrip(":.- ").strip()
                if etimo_text:
                    etimo_text = etimo_text[0].upper() + etimo_text[1:]
                
                resultado["etimologia"] = etimo_text
                print(f"[WIKIAVES] Etimologia extraída: {etimo_text[:50]}...")
            else:
                 print("[ERRO WIKIAVES] Etimologia não encontrada.")

            # Emite o sinal se tiver pelo menos algum dado útil
            if any(resultado.values()):
                self.etymology_found.emit(resultado)
            else:
                self.error_occurred.emit("Nenhum dado encontrado no WikiAves.")

        except Exception as e:
            import traceback
            error_msg = f"Falha fatal no worker: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERRO FATAL WIKIAVES] {error_msg}")
            self.error_occurred.emit("WikiAves indisponível.")
