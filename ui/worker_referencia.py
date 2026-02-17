from PySide6.QtCore import QThread, Signal
try:
    import requests
except ImportError:
    print("[ERRO CRITICO] Biblioteca requests não instalada!")
    requests = None
import traceback
from pathlib import Path

class ReferenceImageWorker(QThread):
    # Alterado v0.8.8: Emite (caminho_imagem, creditos, url_fonte)
    image_found = Signal(str, str, str) 
    search_failed = Signal()

    def __init__(self, species_name):
        super().__init__()
        self.species_name = species_name

    def run(self):
        if not requests:
            self.search_failed.emit()
            return
            
        try:
            print(f"[WORKER] Iniciando busca iNaturalist para: {self.species_name}")
            
            # 1. API iNaturalist (v1/taxa)
            # Docs: https://api.inaturalist.org/v1/docs/#!/Taxa/get_taxa
            url = "https://api.inaturalist.org/v1/taxa"
            params = {
                'q': self.species_name,
                'rank': 'species',
                'per_page': 1
            }
            # Boa prática: User-Agent descritivo
            headers = {
                "User-Agent": "iBirder/1.0 (apenas uso pessoal didatico)"
            }
            
            print(f"[WORKER] Consultando API: {url}")
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            
            # Verificação de Resultados
            if not data.get('results'):
                print("[WORKER] Espécie não encontrada no iNaturalist.")
                self.search_failed.emit()
                return
            
            result = data['results'][0]
            default_photo = result.get('default_photo')
            
            if not default_photo:
                print("[WORKER] Espécie encontrada, mas sem foto padrão.")
                self.search_failed.emit()
                return

            # Extração de Dados
            img_url = default_photo.get('medium_url')
            # Fallback para atribuição se não existir
            attribution = default_photo.get('attribution', '(c) iNaturalist')
            
            if not img_url:
                self.search_failed.emit()
                return

            print(f"[WORKER] Imagem encontrada: {img_url}")
            print(f"[WORKER] Créditos: {attribution}")

            # URL da Fonte (iNaturalist)
            inat_id = result.get('id')
            source_url = f"https://www.inaturalist.org/taxa/{inat_id}" if inat_id else ""

            # 2. Baixar Imagem
            img_data = requests.get(img_url, headers=headers, timeout=10).content
            
            temp_dir = Path(__file__).parent.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            save_path = temp_dir / "reference_bird.jpg"
            
            with open(save_path, "wb") as f:
                f.write(img_data)
                
            self.image_found.emit(str(save_path), attribution, source_url)
            print("--- WORKER FINALIZADO COM SUCESSO ---")

        except Exception as e:
            print(f"[ERRO REF] Falha na busca API: {e}")
            self.search_failed.emit()
