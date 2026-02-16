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

    def run(self):
        import time
        import re
        from urllib.parse import quote

        # Inicializa dicionário de resultados
        resultado = {
            "etimologia": None,
            "nome_ingles": None,
            "familia": None,
            "ordem": None,
            "mapa_url": None,
            "link_wikiaves": None,
            "conservacao": None,
            "imagem_url": None
        }
        
        print(f"[WIKIAVES] Worker iniciado para: {self.species_name}")
        if not BeautifulSoup:
            self.error_occurred.emit("Erro interno: dependência ausente (bs4).")
            return

        try:
            # 1. Configuração de Headers (Idêntico ao Código do Usuário)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.wikiaves.com.br/"
            }
            
            # 2. Estratégia de Conexão (Híbrida)
            
            # Passo A: Acesso Direto Rápido
            slug = self.species_name.lower().replace(" ", "_").strip()
            url_direta = f"https://www.wikiaves.com.br/wiki/{slug}"
            
            print(f"[TRACE 1] Tentando acesso direto: {url_direta}")
            resp = requests.get(url_direta, headers=headers, timeout=10)
            
            final_url = None
            soup_wa = None
            
            if resp.status_code == 200 and "/wiki/" in resp.url and "Página não encontrada" not in resp.text:
                 print(f"[TRACE 2] Acesso direto funcionou: {resp.url}")
                 final_url = resp.url
                 soup_wa = BeautifulSoup(resp.text, 'html.parser')
            else:
                 print(f"[TRACE 2] Acesso direto falhou ({resp.status_code}). Tentando busca...")
                 
                 # Passo B: Busca
                 # https://www.wikiaves.com.br/pesquisa.php?t=s&s={quote(self.species_name)}
                 search_url = f"https://www.wikiaves.com.br/pesquisa.php?t=s&s={quote(self.species_name)}"
                 print(f"[TRACE 3] Buscando: {search_url}")
                 
                 resp_search = requests.get(search_url, headers=headers, timeout=15)
                 
                 if "/wiki/" in resp_search.url:
                     # Redirecionamento automático
                     final_url = resp_search.url
                     soup_wa = BeautifulSoup(resp_search.text, 'html.parser')
                     print(f"[TRACE 4] Busca redirecionou para: {final_url}")
                 elif resp_search.status_code == 200:
                     # Lista de resultados ou erro
                     soup_search = BeautifulSoup(resp_search.text, 'html.parser')
                     # Tenta achar link de wiki
                     for a in soup_search.find_all('a', href=True):
                         if "/wiki/" in a['href']:
                             link = a['href']
                             if not link.startswith("http"):
                                 link = "https://www.wikiaves.com.br" + link
                             final_url = link
                             print(f"[TRACE 4] Link encontrado na busca: {final_url}")
                             
                             # Acessa a página
                             time.sleep(1)
                             r2 = requests.get(final_url, headers=headers, timeout=10)
                             if r2.status_code == 200:
                                 soup_wa = BeautifulSoup(r2.text, 'html.parser')
                             break
            
            if not soup_wa:
                print("[ERRO WIKIAVES] Espécie não encontrada.")
                self.error_occurred.emit("Espécie não encontrada no WikiAves.")
                return

            resultado["link_wikiaves"] = final_url
            
            # --- PARSING ROBUSTO (Baseado no Legacy) ---
            
            # A. Nome Comum (h1 com limpeza de small)
            h1 = soup_wa.find("h1")
            if h1:
                # Remove small se existir
                if h1.find("small"):
                    h1.find("small").decompose()
                # Opcional: extrair nome comum se quiser usar, mas o foco é etimologia/tech
                # nome_comum = h1.get_text(strip=True)

            # B. Taxonomia (Tabela id='taxonomia')
            try:
                table_tax = soup_wa.find("table", id="taxonomia")
                if table_tax:
                    for tr in table_tax.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 2:
                            item = tds[0].get_text(strip=True).replace(":", "")
                            val = tds[1].get_text(strip=True)
                            if "Ordem" in item:
                                resultado["ordem"] = val
                            elif "Família" in item:
                                resultado["familia"] = val
                print(f"[WIKIAVES] Taxonomia: {resultado['ordem']} / {resultado['familia']}")
            except Exception as e:
                print(f"[DEBUG] Erro taxonomia: {e}")

            # C. Nome em Inglês
            try:
                # Procura por strings 'Nome em Inglês'
                # Geralmente: <p><b>Nome em Inglês:</b> <i>Species Name</i> ...</p>
                # Ou texto solto
                tag_ing = soup_wa.find(string=re.compile("Nome em Inglês"))
                if tag_ing:
                     # Tenta pegar o elemento seguinte ou pai
                     parent = tag_ing.parent
                     # Navega até achar o nome (geralmente num <i> ou texto seguinte)
                     # No código legacy: "frequentemente em itálico"
                     # Tenta achar um <i> irmão ou sobrinho
                     
                     # Opção 1: Texto completo do container
                     full_line = parent.parent.get_text(" ", strip=True) 
                     if "Nome em Inglês" in full_line:
                         # Split
                         parts = full_line.split("Nome em Inglês")
                         if len(parts) > 1:
                             candidate = parts[1].replace(":", "").strip()
                             # Limpa "Also..." ou quebras
                             candidate = candidate.split("Also")[0].split("Ouça")[0].strip()
                             resultado["nome_ingles"] = candidate
                             print(f"[WIKIAVES] Nome Inglês: {candidate}")
            except Exception as e:
                print(f"[DEBUG] Erro nome inglês: {e}")

            # D. Status de Conservação
            try:
                # Procure por links contendo lista_vermelha_iucn dentro de tags h2 ou sup
                # Legacy: link com href contendo 'lista_vermelha_iucn'
                link_iucn = soup_wa.find("a", href=re.compile(r"lista_vermelha_iucn"))
                if link_iucn:
                    # Verifica se está dentro de h2 ou sup (opcional, mas o user pediu)
                    # Vamos pegar o texto do link ou imagem dentro
                    # O status geralmente está num title de imagem DENTRO do link ou próximo
                    
                    # No WikiAves atual, o status costuma estar no title da imagem status_xx.png
                    # Mas seguindo o pedido legacy: "Identifique o status da IUCN (ex: 'Pouco preocupante')"
                    
                    # Tenta pegar o title da imagem dentro do link
                    img_status = link_iucn.find("img")
                    if img_status and img_status.get("title"):
                        resultado["conservacao"] = img_status.get("title")
                    elif link_iucn.get_text(strip=True):
                         resultado["conservacao"] = link_iucn.get_text(strip=True)
                
                # Fallback imagem direta (muito comum)
                if not resultado["conservacao"]:
                     img_st = soup_wa.find("img", src=re.compile("status_"))
                     if img_st and img_st.get("title"):
                         resultado["conservacao"] = img_st.get("title")

                print(f"[WIKIAVES] Status: {resultado['conservacao']}")
            except Exception as e:
                print(f"[DEBUG] Erro conservação: {e}")

            # E. Mapa
            try:
                img_map = soup_wa.find("img", src=re.compile("mapaocorrencia.php"))
                if img_map:
                    src = img_map['src']
                    if not src.startswith("http"):
                        src = "https://www.wikiaves.com.br/" + src.lstrip("/")
                    # Ajuste de tamanho pedido: l=600&a=600
                    if "?" in src:
                        src += "&l=600&a=600"
                    else:
                        src += "?l=600&a=600"
                    resultado["mapa_url"] = src
                    print(f"[WIKIAVES] Mapa: {src}")
            except Exception as e:
                print(f"[DEBUG] Erro mapa: {e}")
                
            # F. Imagem Principal (og:image)
            try:
                meta_img = soup_wa.find("meta", property="og:image")
                if meta_img:
                    resultado["imagem_url"] = meta_img.get("content")
            except: pass

            # G. Etimologia (Mantendo nossa lógica robusta)
            print(f"[WIKIAVES] Extraindo etimologia...")
            etimo_text = None
            
            trigger_element = soup_wa.find(lambda tag: tag.name in ['p', 'div', 'strong', 'span'] and "seu nome científico significa" in tag.text.lower())
            
            if trigger_element:
                full_text = trigger_element.get_text(" ", strip=True)
                if len(full_text) < 60 or trigger_element.name in ['strong', 'b', 'span']:
                     if trigger_element.parent:
                         full_text = trigger_element.parent.get_text(" ", strip=True)
                
                match = re.search(r"significa[:\s]*(.*)", full_text, re.IGNORECASE | re.DOTALL)
                if match:
                    etimo_text = match.group(1).strip()
                else:
                    parts = full_text.lower().split("significa")
                    if len(parts) > 1:
                        etimo_text = full_text[len(parts[0]) + 9:].lstrip(": ").strip()
                    else:
                        etimo_text = full_text

                etimo_text = etimo_text.lstrip(":.- ").strip()
                if etimo_text:
                    etimo_text = etimo_text[0].upper() + etimo_text[1:]
                
                resultado["etimologia"] = etimo_text
                print(f"[WIKIAVES] Etimologia: {etimo_text[:30]}...")
            
            # Finalização
            if any(resultado.values()):
                self.etymology_found.emit(resultado)
            else:
                self.error_occurred.emit("Nenhum dado encontrado.")

        except Exception as e:
            import traceback
            error_msg = f"Falha fatal worker: {str(e)}"
            print(f"[ERRO FATAL] {traceback.format_exc()}")
            self.error_occurred.emit("Erro ao conectar ao WikiAves.")
