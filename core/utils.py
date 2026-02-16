from pathlib import Path
from PIL import Image
import os

def otimizar_imagem(caminho_entrada: str, caminho_saida: str, max_tamanho: int = 800, qualidade: int = 65):
    """
    Otimização agressiva para evitar erro 429 (API Quota):
    - Converte RGB.
    - Remove metadata (EXIF) criando nova imagem.
    - Resize max 800px.
    - Save JPEG q=65, subsampling=0.
    """
    try:
        with Image.open(caminho_entrada) as img:
            # 1. Converter para RGB (sem exceção)
            img = img.convert("RGB")
            
            # 2. Sanitizar (Strip EXIF) - Metadados ocultos pesam muito
            # Cria nova imagem limpa e copia pixels
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
            return True
            
    except Exception as e:
        print(f"[ERRO] Falha ao otimizar imagem: {e}")
        return False
