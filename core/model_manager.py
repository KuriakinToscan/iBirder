import requests
from pathlib import Path
import logging

class ModelManager:
    # Google's "Birds V1" TFLite model (trained on iNaturalist)
    # Using the official TF Hub URL for V1.3
    URL_MODEL = "https://tfhub.dev/google/lite-model/aiy/vision/classifier/birds_V1/3?lite-format=tflite"
    URL_LABELS = "https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt"
    
    def __init__(self):
        self.assets_dir = Path(__file__).parent.parent / "assets" / "models"
        self.model_path = self.assets_dir / "inat_vision_small.tflite"
        self.labels_path = self.assets_dir / "inat_labels.txt"
        
        # Garantir que a pasta existe
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def check_resources(self):
        return self.model_path.exists() and self.labels_path.exists()

    def download_resources(self, callback=None):
        """
        Baixa o modelo e os labels.
        callback(str): Função para receber mensagens de progresso/porcentagem.
        """
        try:
            logging.info('Iniciando download de recursos do modelo...')
            logging.debug('Baixando EfficientNet V1.3 oficial do TensorFlow Hub...')
            logging.debug(f'Pasta de destino: {self.assets_dir}')
            
            self._download_file(self.URL_MODEL, self.model_path, "Modelo IA", callback)
            self._download_file(self.URL_LABELS, self.labels_path, "Labels", callback)
            return True
        except Exception as e:
            logging.error(f'Erro crítico no download: {e}')
            if callback:
                callback(f"Erro no download: {e}")
            return False

    def _download_file(self, url, dest_path, description, callback):
        if dest_path.exists():
            logging.debug(f'Arquivo já existe: {dest_path}')
            return

        logging.info(f'Baixando: {description} de {url}')
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # allow_redirects=True is default, but explicit for clarity/requirement matching
            response = requests.get(url, stream=True, headers=headers, allow_redirects=True)
            logging.debug(f'Status Code: {response.status_code}')
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
            logging.info(f'Download concluído: {dest_path}')
            
        except Exception as e:
            logging.error(f'Falha ao baixar {url}: {e}')
            raise e
