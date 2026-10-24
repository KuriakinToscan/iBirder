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

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from core.paths import APP_DIR

class EXIFManager:
    """
    Gerencia a gravação de metadados utilizando o binário industrial ExifTool.
    Garante persistência robusta e suporte a caracteres especiais via argfiles.
    """
    
    def __init__(self):
        self.exiftool_path = str(APP_DIR / "assets" / "exiftool" / "exiftool.exe")
        
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
        
        # Registro anterior do iBirder na foto: suas tags são removidas antes da nova gravação
        from modules.step6_persistence.registro_ibirder import ler_registro, ler_nome_preservado
        # Nome original do arquivo: o já preservado (foto renomeada antes) ou o nome atual
        registro = ler_registro(caminho_imagem)
        preservado = ler_nome_preservado(caminho_imagem) or (registro or {}).get("nome_original")
        comandos = self._gerar_comandos(dados, opcoes, gps_existente=tem_gps, registro_anterior=registro,
                                        nome_original=preservado or os.path.basename(caminho_imagem),
                                        gravar_preservado=not ler_nome_preservado(caminho_imagem))
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

    def gravar_nome_original_sidecar(self, caminho_raw):
        """
        Grava o nome original do RAW no .xmp que o acompanha (IMG_1234.CR3 -> IMG_1234.xmp),
        criando o .xmp se ele não existir. O RAW nunca é alterado.
        Retorna (caminho do .xmp, criado agora) ou None em caso de falha.
        """
        from modules.step6_persistence.registro_ibirder import nome_preservado
        caminho_raw = Path(caminho_raw)
        sidecar = caminho_raw.with_suffix(".xmp")
        existia = sidecar.exists()
        if existia:
            try:
                if nome_preservado(sidecar.read_text(encoding="utf-8", errors="ignore")):
                    return sidecar, False  # já tem o nome original: não sobrescreve
            except OSError:
                pass
        try:
            resultado = subprocess.run(
                [self.exiftool_path, "-charset", "filename=utf8", "-overwrite_original",
                 f"-XMP-xmpMM:PreservedFileName={caminho_raw.name}", str(sidecar)],
                capture_output=True, text=True, encoding="utf-8")
        except Exception as e:
            logging.error(f"Falha ao gravar o nome original em {sidecar.name}: {e}")
            return None
        if resultado.returncode != 0:
            logging.error(f"Erro ExifTool no sidecar {sidecar.name}: {resultado.stderr}")
            return None
        logging.info(f"Nome original de {caminho_raw.name} gravado em {sidecar.name}"
                     + ("" if existia else " (criado)"))
        return sidecar, not existia

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

    # Valores que significam "sem informação" e nunca devem ir para a foto
    VALORES_VAZIOS = {"", "n/a", "n/d", "desconhecida", "desconhecido", "não encontrado", "não identificado",
                      "não identificada", "não informado", "não mapeado", "fora de área mapeada",
                      "dados de bioma não carregados", "erro no processamento", "não disponível"}

    # Categorias reconhecidas para gravar o status nacional (ICMBio)
    # Categorias da lista nacional (Portaria MMA nº 148/2022) que são gravadas na foto
    CATEGORIAS_NACIONAIS = {"Extinta", "Extinta na Natureza", "Criticamente em Perigo", "Em Perigo",
                            "Vulnerável", "Criticamente em Perigo (Provavelmente Extinta)",
                            "Regionalmente Extinta (Extinta no Brasil)"}

    @classmethod
    def _valido(cls, valor):
        return valor is not None and str(valor).strip().lower() not in cls.VALORES_VAZIOS \
            and not str(valor).lower().startswith(("erro", "não disponível", "informação não disponível"))

    def _gerar_comandos(self, dados, opcoes, gps_existente=False, registro_anterior=None, agora=None,
                        nome_original=None, gravar_preservado=True):
        """
        Mapeia dados para Hierarchical Keywords (Seções iBirder) e Darwin Core.
        Respeita as escolhas do diálogo de gravação (opcoes: campo -> bool; campo ausente = gravar)
        e nunca grava valores desconhecidos (ex.: endemismo não informado não vira "Não endêmico").
        """
        from datetime import datetime
        from core.config import APP_VERSION
        agora = agora or datetime.now()
        cmds = []

        # 0. Reprocessamento: remove o que o iBirder gravou antes (tags hierárquicas e as
        #    palavras-chave planas derivadas delas), para não acumular valores antigos.
        if registro_anterior:
            for tag in registro_anterior.get("tags", []):
                for grupo in ("XMP-lr", "XMP-mwg-rs"):
                    cmds.append(f"-{grupo}:HierarchicalSubject-={tag}")
            antigos = registro_anterior.get("dados", {})
            for chave in (("Taxonomia", "CommonName"), ("Taxonomia", "ScientificName"), ("Taxonomia", "Family"),
                          ("Taxonomia", "Order"), ("Geografia", "Endemism")):
                if antigos.get(chave):
                    for tag in ("Keywords", "Subject"):
                        cmds.append(f"-{tag}-={antigos[chave]}")

        def usar(campo, valor):
            """Valor a gravar, ou None se o usuário desmarcou o campo ou o valor é desconhecido."""
            return valor if opcoes.get(campo, True) and self._valido(valor) else None

        # 0. Preparação de Dados
        nome_cientifico = usar("nome_cientifico", dados.get("nome_cientifico"))
        nome_comum = usar("nome_comum", dados.get("nome_comum"))
        nome_ingles = usar("nome_ingles", dados.get("nome_ingles"))
        genero_bruto = (dados.get("nome_cientifico") or "").split(" ")[0] or None
        genero = usar("genero", genero_bruto)
        familia = usar("familia", dados.get("familia"))
        ordem = usar("ordem", dados.get("ordem"))
        classe = usar("classe", dados.get("classe"))
        pais = usar("pais", dados.get("pais"))
        estado = usar("estado", dados.get("estado"))
        municipio = usar("municipio", dados.get("municipio"))
        bioma = usar("bioma", dados.get("bioma"))

        # Endemismo: só "Sim"/"Não" confirmados (antes, desconhecido virava "Não endêmico")
        end_raw = str(dados.get("endemismo", "")).strip().lower()
        endemismo_fmt = None
        if opcoes.get("endemismo", True):
            if end_raw in ("sim", "yes", "true", "endêmica", "endemica", "endemic"):
                endemismo_fmt = "Endêmico do Brasil"
            elif end_raw in ("não", "nao", "no", "false"):
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
            """Cria a árvore iBirder -> Seção -> Atributo -> Valor (Lightroom e digiKam)."""
            if valor:
                tag = f"iBirder|{subs}|{chave}|{valor}"
                # "-=" antes de "+=" evita duplicar a tag ao gravar a mesma foto mais de uma vez
                for grupo in ("XMP-lr", "XMP-mwg-rs"):
                    cmds.append(f"-{grupo}:HierarchicalSubject-={tag}")
                    cmds.append(f"-{grupo}:HierarchicalSubject+={tag}")

        # Subseção Taxonomia
        add_hier("Taxonomia", "ScientificName", nome_cientifico)
        add_hier("Taxonomia", "CommonName", nome_comum)
        add_hier("Taxonomia", "EnglishName", nome_ingles)
        add_hier("Taxonomia", "Genus", genero)
        add_hier("Taxonomia", "Family", familia)
        add_hier("Taxonomia", "Order", ordem)
        add_hier("Taxonomia", "Class", classe)

        # Subseção Geografia
        add_hier("Geografia", "Country", pais)
        add_hier("Geografia", "State", estado)
        add_hier("Geografia", "City", municipio)
        add_hier("Geografia", "Biome", bioma)
        add_hier("Geografia", "Endemism", endemismo_fmt)

        # 3. PADRÃO CIENTÍFICO: Darwin Core (DWC)
        # No ExifTool os termos taxonômicos do DwC ficam na estrutura Taxon (TaxonScientificName...).
        # Os nomes antigos (XMP-dwc:ScientificName...) não existem e eram ignorados em silêncio.
        if nome_cientifico: cmds.append(f"-XMP-dwc:TaxonScientificName={nome_cientifico}")
        if genero:          cmds.append(f"-XMP-dwc:TaxonGenus={genero}")
        if familia:         cmds.append(f"-XMP-dwc:TaxonFamily={familia}")
        if ordem:           cmds.append(f"-XMP-dwc:TaxonOrder={ordem}")
        if classe:          cmds.append(f"-XMP-dwc:TaxonClass={classe}")
        if nome_comum:      cmds.append(f"-XMP-dwc:TaxonVernacularName={nome_comum}")

        # 4. Palavras-chave Planas (Compatibilidade Windows)
        keywords = ["iBirder"] + [k for k in (nome_comum, nome_cientifico, familia, ordem, endemismo_fmt) if k]
        cmds.append(f"-XPKeywords={'; '.join(keywords)}")
        for kw in keywords:
            # "-=" antes de "+=" evita duplicar a palavra-chave em gravações repetidas
            for tag in ("Keywords", "Subject"):
                cmds.append(f"-{tag}-={kw}")
                cmds.append(f"-{tag}+={kw}")

        # 5. Conservação: comentário e subseção hierárquica (só valores conhecidos)
        comentarios = []
        iucn = dados.get("iucn_status")
        if opcoes.get("iucn_status", True) and self._valido(iucn) and not str(iucn).startswith(("Espécie não", "Não Avaliado / Seguro")):
            comentarios.append(f"IUCN: {iucn}")
            add_hier("Conservacao", "IUCN", iucn)
        nacional = dados.get("categoria_icmbio")
        if opcoes.get("status_icmbio", True) and nacional in self.CATEGORIAS_NACIONAIS:
            comentarios.append(f"Brasil (Portaria MMA 148/2022): {nacional}")
            add_hier("Conservacao", "Brasil", nacional)
        cites = dados.get("status_cites")
        if opcoes.get("status_cites", True) and str(cites or "").startswith("Anexo"):
            comentarios.append(f"CITES: {cites}")
            add_hier("Conservacao", "CITES", cites)

        # 5b. Quando e com qual versão a foto foi processada (lido no aviso de "foto já processada")
        add_hier("Registro", "Data", agora.strftime("%Y-%m-%d %H:%M"))
        add_hier("Registro", "Versao", APP_VERSION)
        # Nome original do arquivo: visível no Explorer (Comentários) e como filtro no Lightroom/digiKam
        if nome_original:
            comentarios.append(f"Arquivo original: {nome_original}")
            add_hier("Arquivo", "NomeOriginal", nome_original)

        assinatura = f"Registrado via iBirder v{APP_VERSION} em {agora.strftime('%d/%m/%Y %H:%M')}."
        final_comment = ". ".join(comentarios) + ". " + assinatura if comentarios else assinatura
        cmds.append(f"-XPComment={final_comment}")
        cmds.append(f"-UserComment={final_comment}")

        # 6. GPS Condicional
        if opcoes.get("coord_gps") and not gps_existente:
            lat = dados.get("latitude") or dados.get("lat")
            lon = dados.get("longitude") or dados.get("lon")
            if lat is not None and lon is not None:
                lat, lon = float(lat), float(lon)
                # O EXIF ignora o sinal: o hemisfério precisa ir explícito nas tags Ref
                cmds.append(f"-GPSLatitude={abs(lat)}")
                cmds.append(f"-GPSLatitudeRef={'S' if lat < 0 else 'N'}")
                cmds.append(f"-GPSLongitude={abs(lon)}")
                cmds.append(f"-GPSLongitudeRef={'W' if lon < 0 else 'E'}")
        elif gps_existente:
            logging.debug("GPS original detectado na imagem. Preservando coordenadas existentes.")

        # 7. Nome original do arquivo no campo padrão da Adobe (só na primeira gravação)
        if nome_original and gravar_preservado:
            cmds.append(f"-XMP-xmpMM:PreservedFileName={nome_original}")

        # 8. Finalização
        # Não gravar Creator/Software: sobrescreviam o autor da foto (dc:creator, preenchido
        # pelo Lightroom) e a versão do firmware da câmera. A origem fica no UserComment.
        cmds.append("-overwrite_original")
        
        return cmds
