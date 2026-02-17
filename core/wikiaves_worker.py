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
        print(f"[WIKIAVES] Worker iniciado para: {self.species_name}")
        
        resultado = {
            "descricao": "Descrição indisponível.",
            "link_wikiaves": "",
            "etimologia": None,
            "nome_ingles": None,
            "familia": None,
            "ordem": None,
            "conservacao": None,
            "nome_comum": None,
            "imagem_url": None
        }
        
        try:
            # 1. Obter Descrição e Link via JSON API (Prioridade Máxima / Blindado)
            from core.wikiaves_client import WikiAvesClient
            client = WikiAvesClient()
            desc, url_fonte = client.get_description(self.species_name)
            
            resultado["descricao"] = desc
            resultado["link_wikiaves"] = url_fonte
            
            desc_len = len(desc) if desc else 0
            print(f"[WIKIAVES] Cliente retornou: {desc_len} chars, URL: {url_fonte}")

            # 2. Tentar Scraping Legado para Etimologia/Dados Extras (Opcional)
            # Se falhar, não impede o retorno da descrição.
            try:
                if url_fonte and "wikiaves.com.br/wiki/" in url_fonte:
                    # Reutiliza a URL descoberta pelo cliente seguro
                    self._executar_legado(url_fonte, resultado)
                else:
                     # Tenta busca manual se o cliente não achou URL (improvável)
                     # Mantendo compatibilidade com lógica antiga apenas se necessário
                     pass
            except Exception as e_legado:
                 print(f"[WIKIAVES] Erro no scraping legado (não crítico): {e_legado}")

            # 3. Emitir Resultado
            self.etymology_found.emit(resultado)

        except Exception as e:
            print(f"[ERRO FATAL WIKIAVES] {e}")
            # Emite o que temos (pelo menos a descrição dita 'indisponível')
            self.etymology_found.emit(resultado)

    def _executar_legado(self, url, resultado):
        """Executa lógica parecida com a original para extrair etimologia da URL conhecida."""
        # Configuração de Sessão Rápida
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
             'Referer': 'https://www.wikiaves.com.br/'
        })
        
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            dados_extras = self._parse_page(soup, url)
            # Mescla dados extras se existirem
            for k, v in dados_extras.items():
                if v:
                    resultado[k] = v

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
