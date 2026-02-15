import sys
import os
import subprocess
from pathlib import Path
from .erros import ErroArquivoInvalido

class MotorMetadados:
    def __init__(self):
        self.caminho_exiftool = self._obter_caminho_exiftool()

    def _obter_caminho_exiftool(self) -> str:
        """
        Localiza o binário do ExifTool de forma inteligente (Script vs Frozen).
        """
        if getattr(sys, 'frozen', False):
            # Se estiver rodando como .exe (PyInstaller)
            base_path = Path(sys._MEIPASS)
        else:
            # Se estiver rodando como script .py
            # Assume que assets está na raiz do projeto, dois níveis acima de core/motor_metadados.py?
            # core/motor_metadados.py -> core/ -> raiz/ -> assets/
            base_path = Path(__file__).parent.parent / 'assets'

        # Nome do executável (assumindo Windows conforme contexto do usuário)
        exiftool_path = base_path / 'exiftool.exe'

        if not exiftool_path.exists():
            # Fallback: Tenta procurar na pasta de trabalho atual (caso execute da raiz)
            cwd_path = Path.cwd() / 'assets' / 'exiftool.exe'
            if cwd_path.exists():
                return str(cwd_path)

            raise FileNotFoundError(
                f"ExifTool não encontrado em: {exiftool_path}\n"
                "Por favor, certifique-se de que o 'exiftool.exe' está na pasta 'assets'."
            )

        return str(exiftool_path)

    def inserir_metadados(self, caminho_arquivo: str, dados_ave: dict):
        """
        Insere metadados na imagem usando ExifTool via subprocess.
        
        Args:
            caminho_arquivo (str): Caminho absoluto da imagem.
            dados_ave (dict): Dicionário com dados da ave.
                              Chaves esperadas: 'nome_cientifico', 'nome_comum', 'fonte',
                              'gps_latitude', 'gps_longitude' (opcionais).
        
        Raises:
            ErroArquivoInvalido: Se o arquivo não existir ou não for gravável.
            RuntimeError: Se o ExifTool falhar.
        """
        arquivo = Path(caminho_arquivo)

        if not arquivo.exists():
             raise ErroArquivoInvalido(f"Arquivo não encontrado: {caminho_arquivo}")
        
        # Verifica permissão de escrita
        if not os.access(caminho_arquivo, os.W_OK):
             raise ErroArquivoInvalido(f"Arquivo não é gravável: {caminho_arquivo}")

        # Comandos do ExifTool
        # -overwrite_original: Sobrescreve o arquivo (assumindo que já é uma cópia segura)
        # -P: Preserva data de modificação do arquivo
        # -m: Ignora avisos menores
        # -q: Silencioso
        cmd = [
            self.caminho_exiftool,
            "-overwrite_original", 
            "-P",
            "-q",
            "-m",
            "-charset", "filename=UTF8" # Garante compatibilidade com acentos nos nomes de arquivo
        ]

        # Mapeamento de Tags
        nome_cientifico = dados_ave.get("nome_cientifico")
        if nome_cientifico:
            cmd.extend([
                f"-XMP:Species={nome_cientifico}",
                f"-IPTC:Keywords={nome_cientifico}",
                f"-XMP-dc:Subject={nome_cientifico}"
            ])

        nome_comum = dados_ave.get("nome_comum")
        if nome_comum:
            cmd.extend([
                f"-XMP-dc:Title={nome_comum}",
                f"-IPTC:ObjectName={nome_comum}"
            ])
            
        fonte = dados_ave.get("fonte")
        if fonte:
            cmd.extend([
                 f"-XMP-dc:Source={fonte}"
            ])

        # GPS (Opcional)
        # ExifTool é esperto o suficiente para gerenciar refs se passarmos os valores assinados
        # Mas para garantir, passamos os valores
        lat = dados_ave.get("gps_latitude")
        lon = dados_ave.get("gps_longitude")
        
        # Apenas grava se ambos estiverem presentes e forem números válidos
        if lat is not None and lon is not None:
             cmd.extend([
                 f"-EXIF:GPSLatitude={lat}",
                 f"-EXIF:GPSLatitudeRef={lat}",
                 f"-EXIF:GPSLongitude={lon}",
                 f"-EXIF:GPSLongitudeRef={lon}"
             ])

        # Adiciona o arquivo alvo ao comando
        cmd.append(str(arquivo))

        # Configura startupinfo para esconder janela do CMD no Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            # Executa o comando
            # encoding='utf-8' é importante para suportar caracteres especiais nos metadados
            resultado = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True,
                check=True # Lança CalledProcessError se retorno != 0
            )
        except subprocess.CalledProcessError as e:
            # Captura erro do ExifTool e relança como erro de runtime
            raise RuntimeError(f"Erro ao executar ExifTool: {e.stderr}")
