#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

from PySide6.QtCore import QThread, Signal
import logging
import urllib.parse
try:
    import requests
except ImportError:
    logging.critical("Biblioteca requests não instalada!")
    requests = None
import traceback
from pathlib import Path

class ReferenceImageWorker(QThread):
    # Alterado v0.8.8: Emite (caminho_imagem, creditos, url_fonte)
    image_found = Signal(str, str, str) 
    search_failed = Signal()

    def __init__(self, species_name, parent=None):
        super().__init__(parent)
        self.species_name = species_name
        self.local_path = None # Adicionado v0.8.8

    def run(self):
        if not requests:
            self.search_failed.emit()
            return
            
        try:
            logging.info(f"Iniciando busca de imagem de referência para: {self.species_name}")
            
            # 1. API iNaturalist (v1/taxa)
            # Docs: https://api.inaturalist.org/v1/docs/#!/Taxa/get_taxa
            url = "https://api.inaturalist.org/v1/taxa"
            params = {
                'q': self.species_name,
                'is_active': 'true',
                'rank': 'species',
                'per_page': 1
            }
            # Boa prática: User-Agent descritivo
            headers = {
                "User-Agent": "iBirder/1.0 (apenas uso pessoal didatico)"
            }
            
            logging.debug(f"Consultando API iNaturalist: {url}")
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            
            # Verificação de Resultados
            if not data.get('results'):
                logging.debug("Espécie não encontrada no iNaturalist.")
                self.search_failed.emit()
                return
            
            result = data['results'][0]
            default_photo = result.get('default_photo')
            
            if not default_photo: # Mantido o check para default_photo antes de tentar extrair img_url
                logging.debug("Espécie encontrada, mas sem foto padrão.")
                self.search_failed.emit()
                return

            # Extração de Dados e Upscale de Resolução (v0.3.44)
            img_url = default_photo.get('original_url') or default_photo.get('large_url') or default_photo.get('medium_url')
            if img_url and 'medium' in img_url:
                 img_url = img_url.replace('medium', 'original')
                 
            # Fallback para atribuição se não existir
            attribution = default_photo.get('attribution', '(c) iNaturalist')
            
            # Limpeza v0.3.15: Remover info redundante de upload
            if attribution and ", uploaded by" in attribution:
                try:
                    attribution = attribution.split(", uploaded by")[0]
                except:
                    pass
            
            if not img_url:
                self.search_failed.emit()
                return

            logging.debug(f"Imagem encontrada: {img_url}")
            logging.debug(f"Créditos: {attribution}")

            # URL da Fonte (iNaturalist)
            inat_id = result.get('id')
            source_url = f"https://www.inaturalist.org/taxa/{inat_id}" if inat_id else ""

            # 2. Baixar Imagem
            img_data = requests.get(img_url, headers=headers, timeout=10).content
            
            from core.paths import TEMP_DIR
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            save_path = TEMP_DIR / "reference_bird.jpg"
            self.local_path = str(save_path) # Adicionado v0.8.8
            
            with open(save_path, "wb") as f:
                f.write(img_data)
                
            self.image_found.emit(self.local_path, attribution, source_url)
            logging.info("Busca de imagem de referência concluída.")

        except Exception as e:
            logging.error(f"Falha na busca de imagem de referência: {e}")
            self.search_failed.emit()
