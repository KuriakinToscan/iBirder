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

def limpar_temp_inteligente():
    """Remove arquivos temporários e logs de sessão segura ao fechar."""
    folder = 'temp'
    if not os.path.exists(folder):
        return
        
    # Lista tudo na pasta temp
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        # Preserva session.log se necessário (lógica já tratada no logger/main, 
        # mas aqui limpamos o resto ou se o logger já liberou)
        # Nota: O main.py vai chamar esta função via atexit.
        # Se main.py definir lógica condicional, ele deve chamar logger.cleanup antes ou depois.
        # Aqui vamos fazer uma limpeza geral "safe".
        if filename == "session.log":
            continue # Deixa o logger cuidar do session.log (cleanup_session_log)

        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Erro ao limpar {file_path}: {e}")
