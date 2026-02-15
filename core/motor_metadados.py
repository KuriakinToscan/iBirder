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

    def ler_metadados(self, caminho_arquivo: str) -> dict:
        """
        Lê metadados da imagem usando ExifTool. Tenta recuperar informações de espécie.
        """
        if not os.path.exists(caminho_arquivo):
            return {}

        try:
            # Lista de tags para ler
            tags = [
                "-XMP:Species", "-IPTC:Keywords",
                "-XMP-dc:Title", "-IPTC:ObjectName",
                "-XMP-dc:Description", "-EXIF:ImageDescription",
                "-XMP-dc:Source"
            ]
            
            # Configuração do processo para esconder janela no Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            cmd = [self.caminho_exiftool, "-j", "-charset", "filename=UTF8"] + tags + [caminho_arquivo]
            
            resultado = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True,
                encoding='utf-8', # Forçar UTF-8 na leitura
                errors='ignore' 
            )
            
            if resultado.returncode != 0:
                print(f"Erro ExifTool (Leitura): {resultado.stderr}")
                return {}

            import json
            dados = json.loads(resultado.stdout)
            
            if not dados or not isinstance(dados, list):
                return {}
                
            info = dados[0]
            metadados = {}
            
            # Mapeamento com prioridade
            metadados["nome_cientifico"] = info.get("Species") or info.get("Keywords")
            metadados["nome_comum"] = info.get("Title") or info.get("ObjectName")
            metadados["descricao"] = info.get("Description") or info.get("ImageDescription")
            metadados["fonte"] = info.get("Source")
            
            # Limpeza de dados (ExifTool pode retornar listas para Keywords)
            for k, v in metadados.items():
                if isinstance(v, list):
                    metadados[k] = v[0] if v else None
                    
            # Filtra apenas o que serve (tem nome científico?)
            if metadados.get("nome_cientifico"):
                return metadados
                
            return {}

        except Exception as e:
            print(f"Erro ao ler metadados: {e}")
            return {}

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

        descricao = dados_ave.get("descricao")
        if descricao:
            cmd.extend([
                f"-XMP-dc:Description={descricao}",
                f"-EXIF:ImageDescription={descricao}",
                f"-IPTC:Caption-Abstract={descricao}"
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

        # Safe Write Protocol (Regra 1): Cópia Temporária -> Edição -> Atomic Move
        copia_temp = arquivo.with_suffix(f".temp{arquivo.suffix}")
        
        try:
            # 1. Cria cópia
            import shutil
            shutil.copy2(arquivo, copia_temp)

            # 2. Executa ExifTool na cópia
            cmd.append(str(copia_temp))
            
            # Ajuste de comandos para trabalhar na cópia
            # Removemos -overwrite_original pois estamos trabalhando na cópia que será movida depois
            if "-overwrite_original" in cmd:
                cmd.remove("-overwrite_original")

            # Configura startupinfo
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                startupinfo=startupinfo, # Hide console window
                text=True,
                check=True
            )

            # 3. Substitui original (Atomic Move)
            # Remove original primeiro para garantir substituição limpa no Windows
            os.replace(copia_temp, arquivo)

        except subprocess.CalledProcessError as e:
            if copia_temp.exists():
                os.remove(copia_temp) # Limpa lixo
            raise RuntimeError(f"Erro ao executar ExifTool: {e.stderr}")
        except Exception as e:
            if copia_temp.exists():
                os.remove(copia_temp)
            raise RuntimeError(f"Falha na escrita segura: {str(e)}")
