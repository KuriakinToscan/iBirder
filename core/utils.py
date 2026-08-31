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

from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import os
import sys
import logging
from core.paths import BASE_DIR, IS_FROZEN

def otimizar_imagem(caminho_entrada: str, caminho_saida: str, max_tamanho: int = 800, qualidade: int = 65):
    """
    Otimização agressiva para evitar erro 429 (API Quota) e excesso de telemetria:
    - Converte para RGB.
    - Remove metadados (Strip EXIF) para reduzir o peso da requisição.
    - Redimensiona para no máximo 800px preservando a proporção.
    """
    try:
        with Image.open(caminho_entrada) as img:
            # 1. Converter para RGB (Garante compatibilidade com JPEG)
            img = img.convert("RGB")
            
            # 2. Sanitizar (Strip EXIF) - Metadados ocultos podem ser pesados
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            
            # 3. Redimensionar (Max 800px)
            largura, altura = clean_img.size
            if max(largura, altura) > max_tamanho:
                ratio = max_tamanho / max(largura, altura)
                nova_largura = int(largura * ratio)
                nova_altura = int(altura * ratio)
                clean_img = clean_img.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
            
            # 4. Salvar Otimizado
            os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
            clean_img.save(caminho_saida, "JPEG", quality=qualidade, subsampling=0, optimize=True)
            
            return caminho_saida
            
    except Exception as e:
        logging.error(f"Falha ao otimizar imagem: {e}")
        raise e

def otimizar_imagem_para_exif(caminho_entrada, qualidade=90):
    """
    Cria uma cópia de alta qualidade para gravação de metadados.
    Evita manipular o arquivo original de 20MB+ diretamente no ExifTool
    para garantir maior estabilidade no Windows.
    """
    try:
        temp_output_path = Path(caminho_entrada).parent / f"temp_{Path(caminho_entrada).name}"
        with Image.open(caminho_entrada) as img:
            img = img.convert("RGB")
            img.save(temp_output_path, "JPEG", quality=qualidade, optimize=True)
        return temp_output_path
    except Exception as e:
        logging.error(f"Falha ao preparar imagem para EXIF: {e}")
        raise e

def limpar_temp_inteligente():
    """
    Realiza a faxina de arquivos temporários e logs antigos.
    - Remove rascunhos de fotos otimizadas.
    - Chamado automaticamente no encerramento (atexit) via main.py.
    """
    temp_dir = BASE_DIR / "temp"
    if not temp_dir.exists():
        return
        
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        
        # O session.log é gerido pelo cleanup_session_log do logger.py
        if filename == "session.log":
            continue

        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)
        except Exception as e:
            logging.error(f"Erro ao limpar {file_path}: {e}")
