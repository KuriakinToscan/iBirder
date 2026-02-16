from PySide6.QtCore import QThread, Signal
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import re

class WikiAvesWorker(QThread):
    etymology_found = Signal(dict) 
    error_occurred = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name
        self.raw_name = species_name

class WikiAvesWorker(QThread):
    etymology_found = Signal(dict) 
    error_occurred = Signal(str)
    
    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name
        self.raw_name = species_name

    def run(self):
        import time
        from urllib.parse import quote
        
        print(f"[WIKIAVES] Worker iniciado para: {self.species_name}")
        if not BeautifulSoup:
            self.error_occurred.emit("Erro interno: dependência ausente (bs4).")
            return

        try:
            # 1. Configuração de Sessão e Headers (Baseado no Relatório Técnico)
            session = requests.Session()
            
            # Headers completos para mimetizar um navegador real (Chrome)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://www.wikiaves.com.br/'
            }
            session.headers.update(headers)
            
            # 2. Estratégia de Conexão (v0.15.2: Fix URL & API Fallback)
            # URL de busca correta: index.php?t=s&s={termo} (Seguindo o relatório)
            search_url = f"https://www.wikiaves.com.br/index.php?t=s&s={quote(self.species_name)}"
            print(f"[TRACE 1] Iniciando busca via Session: {search_url}")
            
            resp = session.get(search_url, timeout=15)
            
            final_url = None
            soup_wa = None
            
            # Caso A: Redirect automático para /wiki/ (Sucesso)
            if "/wiki/" in resp.url and resp.status_code == 200:
                 final_url = resp.url
                 soup_wa = BeautifulSoup(resp.text, 'html.parser')
                 print(f"[TRACE 2] Redirecionamento automático detectado: {final_url}")
            
            # Caso B: API Fallback ("Pulo do Gato")
            else:
                 print(f"[TRACE 2] Redirect falhou (URL: {resp.url}). Tentando API getBusca...")
                 api_url = f"https://www.wikiaves.com.br/getBusca.php?tm=s&t=s&term={quote(self.species_name)}"
                 try:
                     r_api = session.get(api_url, timeout=10)
                     if r_api.status_code == 200 and r_api.text.strip().startswith("["):
                         data = r_api.json()
                         if data and isinstance(data, list) and len(data) > 0:
                             item = data[0]
                             if "link" in item:
                                 link = item["link"]
                                 if not link.startswith("http"):
                                     link = "https://www.wikiaves.com.br/" + link.lstrip("/")
                                 
                                 print(f"[TRACE 3] Link encontrado via API: {link}")
                                 final_url = link
                                 
                                 time.sleep(1.5) # Delay ético (Relatório sugere ~1.5s)
                                 r_page = session.get(final_url, timeout=10)
                                 if r_page.status_code == 200:
                                     soup_wa = BeautifulSoup(r_page.text, 'html.parser')
                 except Exception as e:
                     print(f"[DEBUG] Erro na API getBusca: {e}")

            if not soup_wa:
                # Debug Dump
                
                # Debug Dump (v0.15.2)
                try:
                    import os
                    debug_path = "temp/search_fail_debug.html"
                    os.makedirs("temp", exist_ok=True)
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    print(f"[DEBUG] HTML salvo em {debug_path}")
                except Exception as ex:
                    print(f"[DEBUG] Falha ao salvar dump: {ex}")
                
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                return

            # 3. Parsing (Método Auxiliar v0.15.1)
            dados = self._parse_page(soup_wa, final_url)
            
            if any(dados.values()):
                self.etymology_found.emit(dados)
            else:
                self.error_occurred.emit("Nenhum dado encontrado.")

        except Exception as e:
            import traceback
            print(f"[ERRO FATAL] {traceback.format_exc()}")
            self.error_occurred.emit("Erro ao conectar ao WikiAves.")

    def _parse_page(self, soup, url):
        """Extrai dados da página seguindo lógica robusta do serviço legado."""
        import re
        
        resultado = {
            "etimologia": None,
            "nome_ingles": None,
            "familia": None,
            "ordem": None,
            "mapa_url": None,
            "link_wikiaves": url,
            "conservacao": None,
            "imagem_url": None,
            "nome_comum": None
        }

        # A. Nome Comum (h1)
        try:
            h1 = soup.find("h1")
            if h1:
                # Remove small (autor/data)
                if h1.find("small"):
                     h1.find("small").decompose()
                resultado["nome_comum"] = h1.get_text(strip=True)
        except: pass

        # B. Taxonomia (Tabela)
        try:
            table = soup.find("table", id="taxonomia")
            if table:
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 2:
                        key = tds[0].get_text(strip=True).replace(":", "")
                        val = tds[1].get_text(strip=True)
                        if "Ordem" in key:
                            resultado["ordem"] = val
                        elif "Família" in key:
                            resultado["familia"] = val
        except: pass

        # C. Nome em Inglês
        try:
            # Procura texto "Nome em Inglês"
            tag = soup.find(string=re.compile("Nome em Inglês"))
            if tag:
                # Geralmente: parent=<b>, parent.parent includes <i>Name</i>
                # Tenta pegar todo o texto do container pai
                container = tag.parent.parent
                text = container.get_text(" ", strip=True)
                # Parse: "Nome em Inglês: Name"
                if "Nome em Inglês" in text:
                    parts = text.split("Nome em Inglês")
                    if len(parts) > 1:
                        # Limpa sufixos comuns como "Ouça" ou "Also"
                        val = parts[1].replace(":", "").strip()
                        val = val.split("Ouça")[0].split("Also")[0].strip()
                        resultado["nome_ingles"] = val
        except: pass

        # D. Mapa (Imagem ou ID)
        try:
            # 1. Tenta imagem direta
            img_map = soup.find("img", src=re.compile("mapaocorrencia.php"))
            if img_map:
                src = img_map['src']
                if not src.startswith("http"):
                    src = "https://www.wikiaves.com.br/" + src.lstrip("/")
                
                # Ajuste de tamanho
                if "l=600" not in src:
                    sep = "&" if "?" in src else "?"
                    src += f"{sep}l=600&a=600"
                
                resultado["mapa_url"] = src
            else:
                # 2. Fallback: Tenta achar ID da espécie para montar URL
                # Procura links tipo "mapa.php?s=123"
                link_map = soup.find("a", href=re.compile(r"mapa\.php\?s="))
                if link_map:
                    href = link_map['href']
                    match_id = re.search(r"s=(\d+)", href)
                    if match_id:
                        sp_id = match_id.group(1)
                        resultado["mapa_url"] = f"https://www.wikiaves.com.br/mapaocorrencia.php?s={sp_id}&l=600&a=600"
        except: pass

        # E. Conservação (IUCN)
        try:
            # Procura link para lista vermelha
            link_iucn = soup.find("a", href=re.compile("lista_vermelha_iucn"))
            if link_iucn:
                # Tenta texto em negrito dentro (padrão legado)
                b_tag = link_iucn.find("b")
                if b_tag:
                    resultado["conservacao"] = b_tag.get_text(strip=True)
                else:
                    # Tenta title de imagem dentro
                    img = link_iucn.find("img")
                    if img and img.get("title"):
                        resultado["conservacao"] = img.get("title")
            
            # Fallback: Imagem de status solta
            if not resultado["conservacao"]:
                img_st = soup.find("img", src=re.compile("status_"))
                if img_st and img_st.get("title"):
                    resultado["conservacao"] = img_st.get("title")
        except: pass

        # F. Imagem Principal
        try:
            og_img = soup.find("meta", property="og:image")
            if og_img:
                resultado["imagem_url"] = og_img.get("content")
        except: pass

        # G. Etimologia (Lógica Robusta v0.10.16)
        try:
            etimo_text = None
            trigger = soup.find(lambda tag: tag.name in ['p', 'div', 'strong', 'span'] and "seu nome científico significa" in tag.text.lower())
            
            if trigger:
                full_text = trigger.get_text(" ", strip=True)
                # Escalar para pai se necessário
                if len(full_text) < 60 or trigger.name in ['strong', 'b', 'span']:
                    if trigger.parent:
                        full_text = trigger.parent.get_text(" ", strip=True)
                
                match = re.search(r"significa[:\s]*(.*)", full_text, re.IGNORECASE | re.DOTALL)
                if match:
                    etimo_text = match.group(1).strip()
                else:
                    parts = full_text.lower().split("significa")
                    if len(parts) > 1:
                        # Pega o restante da string
                        etimo_text = full_text[len(parts[0]) + 9:].lstrip(": ").strip()
                    else:
                        etimo_text = full_text

                if etimo_text:
                    etimo_text = etimo_text.lstrip(":.- ").strip()
                    if etimo_text:
                        etimo_text = etimo_text[0].upper() + etimo_text[1:]
                    
                resultado["etimologia"] = etimo_text
        except: pass
        
        return resultado
