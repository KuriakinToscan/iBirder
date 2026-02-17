import os
import requests
from pathlib import Path

class ModelManager:
    # Google's "Birds V1" TFLite model (trained on iNaturalist)
    # Using the official TF Hub URL for V1.3
    URL_MODEL = "https://tfhub.dev/google/lite-model/aiy/vision/classifier/birds_V1/3?lite-format=tflite"
    URL_LABELS = "https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt"
    
    def __init__(self):
        self.assets_dir = Path(__file__).parent.parent / "assets" / "models"
        self.model_path = self.assets_dir / "birds_model.tflite"
        self.labels_path = self.assets_dir / "birds_labels.txt"
        
        # Garantir que a pasta existe
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def check_resources(self):
        """Retorna True se todos os arquivos necessários existem e são válidos."""
        # Se o modelo existir mas for pequeno (< 15MB), provavelmente é o MobileNet V2 antigo.
        # O EfficientNet/V1.3 costuma ter ~30MB. Vamos forçar o re-download.
        if self.model_path.exists():
            size_mb = self.model_path.stat().st_size / (1024 * 1024)
            if size_mb < 15:
                print(f"[MODELO] Arquivo existente é muito pequeno ({size_mb:.2f} MB). Removendo para baixar versão correta...")
                try:
                    os.remove(self.model_path)
                    if self.labels_path.exists():
                        os.remove(self.labels_path)
                except Exception as e:
                    print(f"[MODELO] Erro ao remover arquivo antigo: {e}")
                return False

        return self.model_path.exists() and self.labels_path.exists()

    def download_resources(self, callback=None):
        """
        Baixa o modelo e os labels.
        callback(str): Função para receber mensagens de progresso/porcentagem.
        """
        try:
            print(f'[MODELO] Iniciando download de recursos...')
            print(f'[IA] Baixando EfficientNet V1.3 oficial do TensorFlow Hub...')
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
        print(f'[MODELO] Fonte atualizada: {url}')
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # allow_redirects=True is default, but explicit for clarity/requirement matching
            response = requests.get(url, stream=True, headers=headers, allow_redirects=True)
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
