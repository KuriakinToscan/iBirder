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
            # 1. Configuração de Headers (Simulando Navegador Real)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.google.com/"
            }
            
            # 2. Estratégia de Conexão (Híbrida)
            
            # Passo A: Acesso Direto (Fast Path)
            slug = self.species_name.lower().replace(" ", "_").strip()
            url_direta = f"https://www.wikiaves.com.br/wiki/{slug}"
            
            print(f"[TRACE 1] Tentando acesso direto: {url_direta}")
            # Requests segue redirects por padrão
            resp = requests.get(url_direta, headers=headers, timeout=10)
            
            final_url = None
            soup_wa = None
            
            # Verifica se caiu na página certa (wiki) e não é 404 customizado ('Página não encontrada')
            if resp.status_code == 200 and "/wiki/" in resp.url and "Página não encontrada" not in resp.text:
                 print(f"[TRACE 2] Acesso direto funcionou: {resp.url}")
                 final_url = resp.url
                 soup_wa = BeautifulSoup(resp.text, 'html.parser')
            else:
                 print(f"[TRACE 2] Acesso direto incerto ({resp.status_code}). Tentando busca...")
                 
                 # Passo B: Busca (Fallback)
                 search_url = f"https://www.wikiaves.com.br/pesquisa.php?t=s&s={quote(self.species_name)}"
                 print(f"[TRACE 3] Buscando: {search_url}")
                 
                 resp_search = requests.get(search_url, headers=headers, timeout=15)
                 
                 # Caso 1: Redirecionamento automático para wiki
                 if "/wiki/" in resp_search.url:
                     final_url = resp_search.url
                     soup_wa = BeautifulSoup(resp_search.text, 'html.parser')
                     print(f"[TRACE 4] Busca redirecionou para: {final_url}")
                     
                 # Caso 2: Lista de resultados
                 elif resp_search.status_code == 200:
                     soup_search = BeautifulSoup(resp_search.text, 'html.parser')
                     # Tenta achar link de wiki nos resultados
                     for a in soup_search.find_all('a', href=True):
                         if "/wiki/" in a['href']:
                             link = a['href']
                             if not link.startswith("http"):
                                 link = "https://www.wikiaves.com.br" + link
                             final_url = link
                             print(f"[TRACE 4] Link encontrado na busca: {final_url}")
                             
                             time.sleep(1) # Delay gentil
                             r2 = requests.get(final_url, headers=headers, timeout=10)
                             if r2.status_code == 200:
                                 soup_wa = BeautifulSoup(r2.text, 'html.parser')
                             break
            
            if not soup_wa:
                print("[ERRO WIKIAVES] Espécie não encontrada.")
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                return

            # 3. Parsing (Método Auxiliar)
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
