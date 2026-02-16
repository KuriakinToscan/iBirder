from PySide6.QtCore import QThread, Signal
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None
import traceback
from pathlib import Path

class ReferenceImageWorker(QThread):
    image_found = Signal(str)
    search_failed = Signal()

    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name

    def run(self):
        if not requests or not BeautifulSoup:
            self.search_failed.emit()
            return
            
        try:
            # 1. Busca no DuckDuckGo para achar link do eBird
            # Simula browser real
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            search_query = f"site:ebird.org/species {self.species_name} photo"
            search_url = f"https://html.duckduckgo.com/html/?q={search_query}"
            
            print(f"[REF] Buscando espécie: {self.species_name}")
            resp = requests.get(search_url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Encontrar primeiro link que contenha /species/
            species_url = None
            for link in soup.find_all('a', href=True):
                href = link['href']
                if "ebird.org/species/" in href:
                    species_url = href
                    break
            
            if not species_url:
                # print("[WORKER] Link da espécie não encontrado.")
                self.search_failed.emit()
                return

            print(f"[REF] URL encontrada: {species_url}")
            
            # 2. Acessar página da espécie
            resp_spec = requests.get(species_url, headers=headers, timeout=10)
            print(f"[REF] Status Code da página: {resp_spec.status_code}")
            soup_spec = BeautifulSoup(resp_spec.text, 'html.parser')
            
            # 3. Encontrar imagem
            img_url = None
            
            # Tentativa 1: Meta Tag (Mais confiável)
            meta_og = soup_spec.find("meta", property="og:image")
            if meta_og:
                img_url = meta_og.get("content")
            
            # Tentativa 2: Seletores CSS Específicos (Backup)
            if not img_url:
                div = soup_spec.find("div", class_="AspectRatioContent") 
                if not div:
                     div = soup_spec.find("div", class_="Species-media-button")
                
                if div:
                    img_tag = div.find("img")
                    if img_tag:
                        img_url = img_tag.get("src")
                        if img_tag.get("srcset"):
                            parts = img_tag.get("srcset").split(",")
                            if parts:
                                last_part = parts[-1].strip().split(" ")[0]
                                if last_part.startswith("http"):
                                    img_url = last_part
            
            print(f"[REF] Imagem encontrada? {bool(img_url)}")

            if not img_url:
                # print("[WORKER] Imagem não encontrada na página.")
                self.search_failed.emit()
                return

            # 4. Baixar Imagem
            # print(f"[WORKER] Baixando: {img_url}")
            img_data = requests.get(img_url, headers=headers, timeout=10).content
            
            temp_dir = Path(__file__).parent.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            save_path = temp_dir / "reference_bird.jpg"
            
            with open(save_path, "wb") as f:
                f.write(img_data)
                
            self.image_found.emit(str(save_path))

        except Exception as e:
            print(f"[ERRO REF] Falha na busca: {e}")
            self.search_failed.emit()
