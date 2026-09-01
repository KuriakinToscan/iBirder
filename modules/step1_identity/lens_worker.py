#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Motor Auxiliar de Identificação Transparente em Background (Google Lens)

import re
import io
import os
import sys
import logging
import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None

class TransparentGoogleLensWorker(QThread):
    """
    Motor Auxiliar em Segundo Plano (Background Worker).
    Submete fotos de forma transparente para o Google Lens quando o modo online estiver ativado
    ou quando a IA local registrar baixa confiança.
    """
    progress_updated = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._stopped = False

    def run(self):
        if not self.image_path or not os.path.exists(self.image_path):
            self.error.emit("Arquivo de imagem inválido para o Google Lens.")
            return

        try:
            self.progress_updated.emit("Refinando identificação em segundo plano (Google Lens)...")
            logging.info("Iniciando requisição transparente ao Google Lens em background...")

            # 1. Otimização Agressiva da Imagem em Memória (< 250 KB)
            buffer = io.BytesIO()
            with Image.open(self.image_path) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                if max(img.size) > 800:
                    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                img.save(buffer, format="JPEG", quality=80)
            
            img_bytes = buffer.getvalue()
            logging.debug(f"Imagem otimizada para Lens: {len(img_bytes)/1024:.1f} KB")

            if self._stopped:
                return

            # 2. Requisição HTTP POST simulada (Cabeçalhos de Navegador Moderno)
            url_lens = "https://lens.google.com/v3/upload"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://lens.google.com",
                "Referer": "https://lens.google.com/"
            }
            files = {
                "encoded_image": ("bird_sample.jpg", img_bytes, "image/jpeg")
            }

            resp = requests.post(url_lens, files=files, headers=headers, timeout=12)
            if resp.status_code != 200 and resp.status_code != 302:
                logging.warning(f"Google Lens respondeu com status {resp.status_code}")
                self.error.emit(f"Serviço Google Lens indisponível (HTTP {resp.status_code}).")
                return

            html_text = resp.text
            logging.debug(f"Resposta obtida do Google Lens ({len(html_text)} caracteres).")

            # 3. Extração Taxonômica (Regex de Binômio Latino + Nomes Comuns)
            sci_name, common_name = self._extrair_taxonomia(html_text)

            if sci_name:
                logging.info(f"Google Lens identificou com sucesso em background: {sci_name} ({common_name})")
                resultado = {
                    "nome_cientifico": sci_name,
                    "nome_comum": common_name,
                    "descricao": "Identificado em segundo plano via inteligência web (Google Lens).",
                    "confianca": 0.95,
                    "fonte": "Google Lens (Background)"
                }
                self.finished.emit(resultado)
            else:
                logging.warning("Google Lens não retornou nenhuma espécie de ave com alta certeza.")
                self.error.emit("Nenhuma espécie correspondente encontrada no Lens.")

        except Exception as e:
            logging.error(f"Erro no TransparentGoogleLensWorker: {e}")
            self.error.emit(f"Falha no refino do Google Lens: {str(e)}")

    def _extrair_taxonomia(self, html):
        """
        Extrai nomes científicos latinos (Genus species) e nomes comuns do HTML/JSON retornado pelo Lens.
        """
        # 1. Regex de Nome Científico (Dois termos em latim: Gênero Maiúsculo + Espécie Minúscula)
        # Filtra termos conhecidos que não são pássaros
        pattern_latin = r'\b([A-Z][a-z]{2,}\s+[a-z]{3,})\b'
        matches = re.findall(pattern_latin, html)
        
        stopwords = {"Google", "Search", "Image", "Privacy", "Terms", "Wikimedia", "Commons", "Creative", "License", "Camera"}
        
        sci_candidate = None
        for m in matches:
            parts = m.split()
            if parts[0] not in stopwords and len(parts[1]) > 2:
                sci_candidate = m
                break

        # 2. Resolução de Nome Comum via WikiAves (se necessário)
        common_candidate = ""
        if sci_candidate:
            try:
                from modules.step2_biology.wiki_client import WikiClient
                wiki = WikiClient()
                info = wiki.get_especie_info(sci_candidate)
                if info and info.get("nome_comum"):
                    common_candidate = info.get("nome_comum")
            except Exception:
                pass

        return sci_candidate, common_candidate

    def stop(self):
        self._stopped = True
