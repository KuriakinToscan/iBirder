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
from core import http
from core.taxon_service import get_taxon

class ReferenceImageWorker(QThread):
    # Alterado v0.8.8: Emite (caminho_imagem, creditos, url_fonte)
    image_found = Signal(str, str, str) 
    search_failed = Signal()

    def __init__(self, species_name, parent=None):
        super().__init__(parent)
        self.species_name = species_name
        self.local_path = None # Adicionado v0.8.8

    def run(self):
        try:
            logging.info(f"Iniciando busca de imagem de referência para: {self.species_name}")

            # 1. Taxon do iNaturalist (TaxonService: cache compartilhado com as outras etapas)
            taxon = get_taxon(self.species_name)
            if not taxon.found:
                logging.debug("Espécie não encontrada no iNaturalist.")
                self.search_failed.emit()
                return

            default_photo = taxon.default_photo
            if not default_photo:
                logging.debug("Espécie encontrada, mas sem foto padrão.")
                self.search_failed.emit()
                return

            # Extração de Dados e Upscale de Resolução (v0.3.44)
            img_url = default_photo.get('original_url') or default_photo.get('large_url') or default_photo.get('medium_url')
            if img_url and 'medium' in img_url:
                 img_url = img_url.replace('medium', 'original')
            if not img_url:
                self.search_failed.emit()
                return

            # Limpeza v0.3.15: Remover info redundante de upload
            attribution = default_photo.get('attribution') or '(c) iNaturalist'
            attribution = attribution.split(", uploaded by")[0]

            logging.debug(f"Imagem encontrada: {img_url}")
            logging.debug(f"Créditos: {attribution}")

            # 2. Baixar Imagem
            resp = http.get(img_url, timeout=10)
            resp.raise_for_status()
            
            from core.paths import TEMP_DIR
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            save_path = TEMP_DIR / "reference_bird.jpg"
            self.local_path = str(save_path) # Adicionado v0.8.8
            
            with open(save_path, "wb") as f:
                f.write(resp.content)
                
            self.image_found.emit(self.local_path, attribution, taxon.url)
            logging.info("Busca de imagem de referência concluída.")

        except Exception as e:
            logging.error(f"Falha na busca de imagem de referência: {e}")
            self.search_failed.emit()
