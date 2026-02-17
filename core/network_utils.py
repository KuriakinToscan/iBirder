import requests
import logging
import os

logger = logging.getLogger("core.network")

def upload_image_to_public_host(image_path):
    """
    Faz upload da imagem para o Catbox.moe e retorna a URL direta.
    Requisito: URL direta (.jpg/.png) para pleno funcionamento do Google Lens.
    """
    url = "https://catbox.moe/user/api.php"
    
    try:
        with open(image_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, files=files, data=data, timeout=30)
            
        if response.status_code == 200:
            return response.text.strip() # Catbox retorna a URL raw no corpo
        else:
            logger.error(f"Erro HTTP Catbox {response.status_code}")
            raise Exception(f"Falha no upload (HTTP {response.status_code})")
            
    except Exception as e:
        logger.error(f"Erro de conexão: {e}")
        raise e
