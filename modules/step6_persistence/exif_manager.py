"""
Módulo de Persistência EXIF (v0.9.0 - ExifTool Edition)

Responsável por gravar as informações processadas (Etapas 1 a 5)
diretamente nos metadados da imagem original através do ExifTool (XMP Customizado).
"""
import json
import subprocess
import os
import sys
from pathlib import Path

class EXIFManager:
    def __init__(self, caminho_caderneta=None):
        self.caminho_caderneta = caminho_caderneta
        
        # Localiza dinamicamente o exiftool.exe em ./assets/exiftool/
        # Funciona no dev e no ambiente compilado do PyInstaller
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.exiftool_path = os.path.join(base_path, "assets", "exiftool", "exiftool.exe")
        self.exiftool_config_path = os.path.join(base_path, "assets", "exiftool_ibirder.config")
        
        if not os.path.exists(self.exiftool_path):
            print(f"[EXIFManager] ERRO: ExifTool não encontrado no caminho esperado: {self.exiftool_path}")

    def obter_dados_caderneta(self):
        """Lê os dados formatados diretamente do arquivo físico (JSON) da sessão."""
        if not self.caminho_caderneta or not Path(self.caminho_caderneta).exists():
            return {}
        try:
            with open(self.caminho_caderneta, 'r', encoding='utf-8') as f:
                dados_lista = json.load(f)
            if isinstance(dados_lista, list) and len(dados_lista) > 0:
                return dados_lista[-1]
            return {}
        except Exception as e:
            print(f"[EXIFManager] Erro ao ler caderneta ({self.caminho_caderneta}): {e}")
            return {}

    def escrever_metadados_completos(self, caminho_imagem, opcoes_selecionadas, tem_gps_nativo):
        """
        Injeta os dados da sessão nos metadados da imagem usando o ExifTool.
        Grava tanto no formato legado (Windows) quanto em namespace XMP customizado (XMP-iBirder).
        """
        if not os.path.exists(self.exiftool_path):
            raise FileNotFoundError(f"Motor ExifTool ausente em {self.exiftool_path}")
            
        dados = self.obter_dados_caderneta()
        if not dados:
            raise ValueError("Falha ao obter dados exclusivamente do arquivo físico da caderneta de campo.")
            
        opcoes = opcoes_selecionadas
        
        # Montagem dos Comandos Iniciais (Silencioso, sobrescreve o original)
        cmd = [self.exiftool_path]
        if hasattr(self, 'exiftool_config_path') and os.path.exists(self.exiftool_config_path):
            cmd.extend(["-config", self.exiftool_config_path])
        cmd.extend(["-m", "-overwrite_original", "-charset", "utf8"])
        
        args = []
        
        # Helper: Se o usuário escolheu uma opção, retorna o dado; senão, ignore.
        def pegar_dado(chave, fallback=""):
            return str(dados.get(chave, fallback)) if opcoes.get(chave) else None
            
        # -------------------------------------------------------------
        # 1. BLOCO LEGADO DO WINDOWS E PADRÃO (Visível na aba Propriedades)
        # -------------------------------------------------------------
        partes_nome = []
        nc = pegar_dado("nome_comum")
        nsci = pegar_dado("nome_cientifico")
        if nc: partes_nome.append(nc)
        if nsci: partes_nome.append(f"({nsci})")
        titulo_exif = " ".join(partes_nome).strip()
        assunto_exif = nc if nc else titulo_exif
        
        if titulo_exif:
            args.extend([f"-XPTitle={titulo_exif}", f"-ImageDescription={titulo_exif} - iBirder", f"-Title={titulo_exif}"])
        if assunto_exif:
            args.extend([f"-XPSubject={assunto_exif}", f"-Subject={assunto_exif}"])
            
        # Palavras-chave genéricas
        keywords = [k for k in [nc, nsci, pegar_dado("familia"), pegar_dado("ordem"), pegar_dado("classe"), pegar_dado("endemismo")] if k]
        keywords.append("iBirder")
        for kw in keywords:
            args.extend([f"-Keywords={kw}", f"-Subject={kw}"]) # Windows usa XPKeywords/Keywords e XMP Subject
            
        args.extend([f"-XPKeywords={'; '.join(keywords)}"])
        args.extend(["-Software=iBirder"]) # Removido -Rating=5 e RatingPercent=99
        
        # Comentário legível condensado genérico
        coment = []
        iucn, icm, cites = pegar_dado("iucn_status"), pegar_dado("status_icmbio"), pegar_dado("status_cites")
        if iucn: coment.append(f"IUCN: {iucn}")
        if icm: coment.append(f"Nacional: {icm}")
        if cites: coment.append(f"CITES: {cites}")
        
        locais = [l for l in [pegar_dado("pais"), pegar_dado("estado"), pegar_dado("municipio"), pegar_dado("bioma")] if l]
        if locais: coment.append("Local: " + " / ".join(locais))
        
        str_coment = ". ".join(coment) + ". Via iBirder." if coment else "Via iBirder."
        args.extend([f"-XPComment={str_coment}", f"-UserComment={str_coment}"])

        # -------------------------------------------------------------
        # 2. BLOCO CUSTOMIZADO XMP-eBirder (Subseções Hierárquicas/Structs)
        # Injeta Structs JSON-like nas subseções do Namespace eBirder
        # -------------------------------------------------------------
        
        # Subseção: Identificacao
        id_fields = []
        if nc: id_fields.append(f"NomeComum='{nc}'")
        if nsci: id_fields.append(f"NomeCientifico='{nsci}'")
        if pegar_dado("nome_ingles"): id_fields.append(f"NomeIngles='{pegar_dado('nome_ingles')}'")
        if id_fields: args.append(f"-XMP-eBirder:Identificacao={{{', '.join(id_fields)}}}")
        
        # Subseção: Taxonomia
        tax_fields = []
        if nsci: 
            genero = nsci.split()[0]
            tax_fields.append(f"Genero='{genero}'")
        if pegar_dado("familia"): tax_fields.append(f"Familia='{pegar_dado('familia')}'")
        if pegar_dado("ordem"): tax_fields.append(f"Ordem='{pegar_dado('ordem')}'")
        if pegar_dado("classe"): tax_fields.append(f"Classe='{pegar_dado('classe')}'")
        if tax_fields: args.append(f"-XMP-eBirder:Taxonomia={{{', '.join(tax_fields)}}}")
        
        # Subseção: Conservacao
        cons_fields = []
        if iucn: cons_fields.append(f"StatusGlobal='{iucn}'")
        if icm: cons_fields.append(f"StatusNacional='{icm}'")
        if cites: cons_fields.append(f"CITES='{cites}'")
        if cons_fields: args.append(f"-XMP-eBirder:Conservacao={{{', '.join(cons_fields)}}}")
        
        # Subseção: Localizacao e Geografia / DadosGeograficos
        geo_fields = []
        if pegar_dado("bioma"): geo_fields.append(f"Bioma='{pegar_dado('bioma')}'")
        if pegar_dado("endemismo"): geo_fields.append(f"Endemismo='{pegar_dado('endemismo')}'")
        if pegar_dado("municipio"): geo_fields.append(f"Municipio='{pegar_dado('municipio')}'")
        if pegar_dado("estado"): geo_fields.append(f"Estado='{pegar_dado('estado')}'")
        if pegar_dado("pais"): geo_fields.append(f"Pais='{pegar_dado('pais')}'")
        
        # -------------------------------------------------------------
        # 3. GRAVAÇÃO CONDICIONAL DE COORDENADAS GEOGRÁFICAS EXIF/GPS
        # -------------------------------------------------------------
        if opcoes.get("coord_gps") and not tem_gps_nativo:
            lat = dados.get("latitude")
            lon = dados.get("longitude")
            if lat is not None and lon is not None:
                lat_ref = "N" if lat >= 0 else "S"
                lon_ref = "E" if lon >= 0 else "W"
                args.extend([
                    f"-GPSLatitude={abs(lat)}",
                    f"-GPSLatitudeRef={lat_ref}",
                    f"-GPSLongitude={abs(lon)}",
                    f"-GPSLongitudeRef={lon_ref}"
                ])
                # Grava na struct Exclusiva do XMP
                geo_fields.append(f"CoordenadaLocal='{lat},{lon}'")
                
        if geo_fields: args.append(f"-XMP-eBirder:DadosGeograficos={{{', '.join(geo_fields)}}}")

        import tempfile
        import uuid
        
        # Utiliza "Argfile" (Arquivo de argumentos do ExifTool) 
        # Isso salva da corrupção de string via Pipeline do CMD do Windows
        args_filepath = os.path.join(tempfile.gettempdir(), f"exif_args_{uuid.uuid4().hex}.txt")
        try:
            with open(args_filepath, 'w', encoding='utf-8') as f:
                for arg in args:
                    f.write(arg + '\n')
            
            cmd.extend(["-@", args_filepath])
            cmd.append(caminho_imagem)
            
            # Executa o Subprocess invisível no Windows (creationflags)
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                encoding='utf-8' # Força string utf8 p/ saída stderr/stdout
            )
            if resultado.returncode != 0 and "1 image files updated" not in resultado.stdout:
                 print(f"[EXIFManager] Aviso ExifTool: {resultado.stderr}")
                 return False
            return True
            
        except Exception as e:
            print(f"[EXIFManager] Falha Crítica ao chamar ExifTool: {e}")
            raise Exception(f"Erro ExifTool subprocess: {e}")
        finally:
            if os.path.exists(args_filepath):
                try: 
                    os.remove(args_filepath)
                except: 
                    pass
