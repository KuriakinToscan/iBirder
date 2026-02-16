from pathlib import Path
from PIL import Image
import os

def otimizar_imagem(caminho_entrada: str, caminho_saida: str, max_tamanho: int = 1024, qualidade: int = 80):
    """
    Redimensiona e comprime a imagem para otimizar upload.
    - Max 1024px no maior lado.
    - Converte para JPEG (remove metadados).
    - Qualidade 80%.
    """
    try:
        with Image.open(caminho_entrada) as img:
            # Converter para RGB (caso seja PNG com transparência)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Redimensionar se necessário
            largura, altura = img.size
            if max(largura, altura) > max_tamanho:
                ratio = max_tamanho / max(largura, altura)
                nova_largura = int(largura * ratio)
                nova_altura = int(altura * ratio)
                img = img.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
            
            # Garantir diretório de saída
            os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
            
            # Salvar otimizado
            img.save(caminho_saida, "JPEG", quality=qualidade, optimize=True)
            return True
    except Exception as e:
        print(f"[ERRO] Falha ao otimizar imagem: {e}")
        return False
