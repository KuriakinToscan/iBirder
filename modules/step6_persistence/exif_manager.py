import sys
import os
import subprocess
import tempfile
import logging
from pathlib import Path

class EXIFManager:
    """
    Gerencia a gravação de metadados utilizando o binário industrial ExifTool.
    Garante persistência robusta e suporte a caracteres especiais via argfiles.
    """
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS)
        else:
            # Sobe 3 níveis: step6_persistence -> modules -> root
            base_dir = Path(__file__).resolve().parent.parent.parent
            
        self.exiftool_path = str(base_dir / "assets" / "exiftool" / "exiftool.exe")
        
    def escrever_metadados_completos(self, caminho_imagem, dados, opcoes):
        """
        Gatilho Mestre de Escrita.
        - caminho_imagem: Path absoluto do arquivo JPG.
        - dados: Dicionário vindo da caderneta de campo (Orchestrator).
        - opcoes: Preferências do usuário (Gravar GPS, Gravar Tags, etc).
        
        Utiliza o padrão Darwin Core (DWC) para taxonomia científica e 
        Hierarchical Keywords (XMP-lr) para árvore de filtros em softwares de gestão.
        """
        if not os.path.exists(self.exiftool_path):
            raise FileNotFoundError(f"Binário ExifTool não encontrado em: {self.exiftool_path}")

        # Lógica de GPS Condicional
        tem_gps = self._verificar_gps_existente(caminho_imagem)
        
        comandos = self._gerar_comandos(dados, opcoes, gps_existente=tem_gps)
        if not comandos:
            return True

        argfile_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.args', delete=False, encoding='utf-8') as f:
                for cmd in comandos:
                    f.write(f"{cmd}\n")
                argfile_path = f.name

            # Chamada industrial ao ExifTool via Subprocess
            # O uso de '-@' com argfile previne quebras de string em nomes científicos complexos
            # ou biomas com caracteres UTF-8 no Windows Shell.
            resultado = subprocess.run(
                [self.exiftool_path, "-charset", "filename=utf8", "-@", argfile_path, caminho_imagem],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            if argfile_path and os.path.exists(argfile_path): os.remove(argfile_path)

            if resultado.returncode != 0:
                logging.error(f"Erro ExifTool: {resultado.stderr}")
                return False
                
            logging.info(f"Metadados iBirder gravados com sucesso em {Path(caminho_imagem).name}")
            return True

        except Exception as e:
            logging.error(f"Falha crítica na gravação EXIF: {e}")
            if argfile_path and os.path.exists(argfile_path): os.remove(argfile_path)
            return False

    def _verificar_gps_existente(self, caminho_imagem):
        """Retorna True se a imagem já possuir tags de GPS."""
        try:
            resultado = subprocess.run(
                [self.exiftool_path, "-GPSLatitude", "-GPSLongitude", caminho_imagem],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            # ExifTool retorna algo como "GPS Latitude : 10 deg..."
            return "GPS Latitude" in resultado.stdout
        except:
            return False

    def _gerar_comandos(self, dados, opcoes, gps_existente=False):
        """Mapeia dados para Hierarchical Keywords (Seções iBirder) e Darwin Core."""
        cmds = []
        
        # 0. Preparação de Dados
        nome_comum = dados.get("nome_comum", "Ave")
        nome_cientifico = dados.get("nome_cientifico", "Aves")
        nome_ingles = dados.get("nome_ingles", "")
        genero = nome_cientifico.split(' ')[0] if ' ' in nome_cientifico else nome_cientifico
        familia = dados.get("familia", "")
        ordem = dados.get("ordem", "")
        classe = dados.get("classe", "")
        
        # Formatação de Endemismo
        end_raw = str(dados.get("endemismo", "")).lower()
        if any(x in end_raw for x in ["sim", "yes", "true", "endemica"]):
            endemismo_fmt = "Endêmico do Brasil"
        else:
            endemismo_fmt = "Não endêmico do Brasil"

        # 1. Título e Descrição (Sincronia Universal)
        titulo = f"{nome_comum} ({nome_cientifico})" if nome_comum and nome_cientifico else (nome_comum or nome_cientifico)
        if titulo:
            cmds.append(f"-XPTitle={titulo}")
            cmds.append(f"-Title={titulo}")
            cmds.append(f"-Description={titulo} - Identificado via iBirder")
            cmds.append(f"-ImageDescription={titulo}")

        # 2. SEÇÃO iBirder: Tags Hierárquicas (Visível como Árvore no digiKam/Lightroom)
        # Formato: iBirder|Subseção|Chave|Valor
        def add_hier(subs, chave, valor):
            """
            Auxiliar para criar tags hierárquicas compatíveis com Lightroom e digiKam.
            Cria uma estrutura: iBirder -> Seção -> Atributo -> Valor
            """
            if valor and valor != "N/A":
                cmds.append(f"-XMP-lr:HierarchicalSubject+=iBirder|{subs}|{chave}|{valor}")
                cmds.append(f"-XMP-mwg-rs:HierarchicalSubject+=iBirder|{subs}|{chave}|{valor}")

        # Subseção Taxonomia
        add_hier("Taxonomia", "ScientificName", nome_cientifico)
        add_hier("Taxonomia", "CommonName", nome_comum)
        add_hier("Taxonomia", "EnglishName", nome_ingles)
        add_hier("Taxonomia", "Genus", genero)
        add_hier("Taxonomia", "Family", familia)
        add_hier("Taxonomia", "Order", ordem)
        add_hier("Taxonomia", "Class", classe)

        # Subseção Geografia
        add_hier("Geografia", "Country", dados.get("pais"))
        add_hier("Geografia", "State", dados.get("estado"))
        add_hier("Geografia", "City", dados.get("municipio"))
        add_hier("Geografia", "Biome", dados.get("bioma"))
        add_hier("Geografia", "Endemism", endemismo_fmt)

        # 3. PADRÃO CIENTÍFICO: Darwin Core (DWC)
        if nome_cientifico: cmds.append(f"-XMP-dwc:ScientificName={nome_cientifico}")
        if genero:          cmds.append(f"-XMP-dwc:Genus={genero}")
        if familia:         cmds.append(f"-XMP-dwc:Family={familia}")
        if ordem:           cmds.append(f"-XMP-dwc:Order={ordem}")
        if classe:          cmds.append(f"-XMP-dwc:Class={classe}")
        if nome_comum:      cmds.append(f"-XMP-dwc:VernacularName={nome_comum}")

        # 4. Palavras-chave Planas (Compatibilidade Windows)
        keywords = ["iBirder"]
        for k in [nome_comum, nome_cientifico, familia, ordem, endemismo_fmt]:
            if k and k != "N/A": keywords.append(k)
        
        kw_string = "; ".join(keywords)
        if kw_string:
            cmds.append(f"-XPKeywords={kw_string}")
            for kw in keywords:
                cmds.append(f"-Keywords+={kw}")
                cmds.append(f"-Subject+={kw}")

        # 5. Comentários e Status
        comentarios = []
        if opcoes.get("iucn_status"): comentarios.append(f"IUCN: {dados.get('iucn_status','')}")
        if opcoes.get("status_icmbio"): comentarios.append(f"ICMBio: {dados.get('status_icmbio','')}")
        
        final_comment = ". ".join(comentarios) + ". Registrado via iBirder." if comentarios else "Registrado via iBirder."
        cmds.append(f"-XPComment={final_comment}")
        cmds.append(f"-UserComment={final_comment}")

        # 6. GPS Condicional
        if opcoes.get("coord_gps") and not gps_existente:
            lat = dados.get("latitude") or dados.get("lat")
            lon = dados.get("longitude") or dados.get("lon")
            if lat is not None and lon is not None:
                cmds.append(f"-GPSLatitude={lat}")
                cmds.append(f"-GPSLongitude={lon}")
                cmds.append("-GPSLatitudeRef#")
                cmds.append("-GPSLongitudeRef#")
        elif gps_existente:
            logging.debug("GPS original detectado na imagem. Preservando coordenadas existentes.")

        # 7. Finalização
        cmds.append("-Software=iBirder")
        cmds.append("-Creator=iBirder User")
        cmds.append("-overwrite_original")
        
        return cmds
