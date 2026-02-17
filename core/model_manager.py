import os
import requests
from pathlib import Path

class ModelManager:
    # Google's "Birds V1" TFLite model (trained on iNaturalist)
    # Actually MobileNet based, but often referred to in these contexts.
    # Using the standard accessible URLs.
    URL_MODEL = "https://raw.githubusercontent.com/google-coral/project-bird-feeder/master/bird_feeder/model/aiy_vision_classifier_birds_V1_3.tflite"
    URL_LABELS = "https://raw.githubusercontent.com/google-coral/project-bird-feeder/master/bird_feeder/model/aiy_birds_V1_labelmap.csv"
    
    def __init__(self):
        self.assets_dir = Path(__file__).parent.parent / "assets" / "models"
        self.model_path = self.assets_dir / "birds_model.tflite"
        self.labels_path = self.assets_dir / "birds_labels.csv"
        
        # Garantir que a pasta existe
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def check_resources(self):
        """Retorna True se todos os arquivos necessários existem."""
        return self.model_path.exists() and self.labels_path.exists()

    def download_resources(self, callback=None):
        """
        Baixa o modelo e os labels.
        callback(str): Função para receber mensagens de progresso/porcentagem.
        """
        try:
            print(f'[MODELO] Iniciando download de recursos...')
            print(f'[MODELO] Pasta de destino: {self.assets_dir}')
            
            self._download_file(self.URL_MODEL, self.model_path, "Modelo IA", callback)
            self._download_file(self.URL_LABELS, self.labels_path, "Labels", callback)
            return True
        except Exception as e:
            print(f'[MODELO] Erro crítico no download: {e}')
            if callback:
                callback(f"Erro no download: {e}")
            return False

    def _download_file(self, url, dest_path, description, callback):
        if dest_path.exists():
            print(f'[MODELO] Arquivo já existe: {dest_path}')
            return

        print(f'[MODELO] Baixando: {url}')
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, stream=True, headers=headers)
            print(f'[MODELO] Status Code: {response.status_code}')
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            if callback:
                callback(f"Baixando {description} (0%)...")
    
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and callback:
                            percent = int((downloaded / total_size) * 100)
                            # Otimização: emitir a cada 5% ou similar poderia ser bom, mas aqui vamos simples
                            if percent % 10 == 0:
                                callback(f"Baixando {description} ({percent}%)...")
                                
            if callback:
                callback(f"{description} pronto.")
            print(f'[MODELO] Download concluído: {dest_path}')
            
        except Exception as e:
            print(f'[MODELO] Falha ao baixar {url}: {e}')
            raise e
