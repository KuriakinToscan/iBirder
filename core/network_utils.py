import requests
import logging
import os

logger = logging.getLogger("core.network")

def upload_image_to_public_host(image_path):
    """
    Faz upload da imagem para um host temporário (tmpfiles.org)
    e retorna a URL pública direta.
    """
    url = "https://tmpfiles.org/api/v1/upload"
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, timeout=30)
            
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                page_url = data['data']['url']
                # Transformar URL de página em URL de download direto
                # Ex: https://tmpfiles.org/123/img.jpg -> https://tmpfiles.org/dl/123/img.jpg
                download_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                return download_url
            else:
                logger.error(f"Erro na API tmpfiles: {data}")
                raise Exception("Falha no upload (API Error)")
        else:
            logger.error(f"Erro HTTP {response.status_code}")
            raise Exception(f"Falha no upload (HTTP {response.status_code})")
            
    except Exception as e:
        logger.error(f"Erro de conexão: {e}")
        raise e
