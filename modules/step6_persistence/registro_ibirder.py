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


"""
Leitura do registro que o próprio iBirder grava nas fotos.

Detecta fotos já processadas a partir de:
- palavras-chave hierárquicas "iBirder|Seção|Chave|Valor" (XMP lr/mwg-rs:hierarchicalSubject);
- comentário EXIF "Registrado via iBirder" (UserComment).

A partir da v1.3 também é gravado "iBirder|Registro|Data|AAAA-MM-DD HH:MM" e
"iBirder|Registro|Versao|x.y". Fotos gravadas por versões anteriores não têm data.

Só usa o Pillow (sem ExifTool): rápido o bastante para rodar a cada foto aberta.
"""

import html
import logging
import re
from datetime import datetime
from pathlib import Path

from PIL import Image

PREFIXO = "iBirder|"

# Rótulos legíveis para as chaves gravadas (exif_manager)
ROTULOS = {
    ("Taxonomia", "ScientificName"): "Nome científico",
    ("Taxonomia", "CommonName"): "Nome comum",
    ("Taxonomia", "EnglishName"): "Nome em inglês",
    ("Taxonomia", "Genus"): "Gênero",
    ("Taxonomia", "Family"): "Família",
    ("Taxonomia", "Order"): "Ordem",
    ("Taxonomia", "Class"): "Classe",
    ("Geografia", "Country"): "País",
    ("Geografia", "State"): "Estado",
    ("Geografia", "City"): "Município",
    ("Geografia", "Biome"): "Bioma",
    ("Geografia", "Endemism"): "Endemismo",
    ("Conservacao", "IUCN"): "IUCN",
    ("Conservacao", "Brasil"): "Lista nacional (MMA)",
    ("Conservacao", "CITES"): "CITES",
}
SECOES = {"Taxonomia": "Espécie", "Geografia": "Local", "Conservacao": "Conservação"}


def _xmp_bruto(img):
    """Pacote XMP como texto (JPEG/WebP: info['xmp']; PNG: chave XML:com.adobe.xmp; TIFF: tag 700)."""
    dado = img.info.get("xmp") or img.info.get("XML:com.adobe.xmp")
    if dado is None and hasattr(img, "tag_v2"):
        dado = img.tag_v2.get(700)
    if isinstance(dado, (bytes, bytearray)):
        dado = dado.decode("utf-8", "ignore")
    return dado or ""


def _comentario_exif(img):
    try:
        bruto = img.getexif().get_ifd(0x8769).get(0x9286)  # ExifIFD -> UserComment
    except Exception:
        return ""
    if isinstance(bruto, (bytes, bytearray)):
        cabecalho, corpo = bytes(bruto[:8]), bytes(bruto[8:])
        if cabecalho.startswith(b"UNICODE"):
            for codificacao in ("utf-16-be", "utf-16-le"):
                texto = corpo.decode(codificacao, "ignore")
                if "iBirder" in texto:
                    return texto.strip("\x00 ")
            return corpo.decode("utf-16-le", "ignore").strip("\x00 ")
        return corpo.decode("utf-8", "ignore").strip("\x00 ")
    return str(bruto or "")


def tags_ibirder(xmp):
    """Lista de tags 'iBirder|...' do XMP, sem repetição (lr e mwg-rs gravam as mesmas)."""
    vistas = []
    for item in re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", xmp, flags=re.S):
        valor = html.unescape(item.strip())
        if valor.startswith(PREFIXO) and valor not in vistas:
            vistas.append(valor)
    return vistas


def nome_preservado(xmp):
    """Nome original do arquivo (XMP xmpMM:PreservedFileName, gravado pelo iBirder e pelo Lightroom)."""
    m = (re.search(r'xmpMM:PreservedFileName="([^"]*)"', xmp)
         or re.search(r"<xmpMM:PreservedFileName>(.*?)</xmpMM:PreservedFileName>", xmp, flags=re.S))
    return html.unescape(m.group(1).strip()) if m else None


def ler_nome_preservado(caminho):
    try:
        with Image.open(caminho) as img:
            return nome_preservado(_xmp_bruto(img))
    except Exception:
        return None


def ler_registro(caminho):
    """
    Retorna None se a foto nunca foi processada pelo iBirder; senão um dict com:
      tags (lista bruta), dados {(seção, chave): valor}, data (datetime|None),
      versao (str|None), comentario (str), modificado_em (datetime do arquivo),
      nome_original (str|None: nome do arquivo antes de ser renomeado).
    """
    try:
        with Image.open(caminho) as img:
            xmp = _xmp_bruto(img)
            comentario = _comentario_exif(img)
    except Exception as e:
        logging.debug(f"Não foi possível ler metadados de {caminho}: {e}")
        return None

    tags = tags_ibirder(xmp)
    if not tags and "via iBirder" not in comentario:
        return None

    dados = {}
    for tag in tags:
        partes = tag.split("|", 3)
        if len(partes) == 4:
            dados[(partes[1], partes[2])] = partes[3]

    data = None
    if ("Registro", "Data") in dados:
        try:
            data = datetime.strptime(dados[("Registro", "Data")], "%Y-%m-%d %H:%M")
        except ValueError:
            pass
    try:
        modificado = datetime.fromtimestamp(Path(caminho).stat().st_mtime)
    except OSError:
        modificado = None

    return {"tags": tags, "dados": dados, "data": data, "versao": dados.get(("Registro", "Versao")),
            "comentario": comentario, "modificado_em": modificado, "nome_original": nome_preservado(xmp)}


def resumo_legivel(registro):
    """[(seção legível, [(rótulo, valor), ...]), ...] na ordem Espécie, Local, Conservação."""
    grupos = []
    for secao, titulo in SECOES.items():
        itens = [(ROTULOS.get((secao, chave), chave), valor)
                 for (s, chave), valor in registro["dados"].items() if s == secao]
        if itens:
            grupos.append((titulo, itens))
    return grupos


def descrever_quando(registro):
    if registro.get("data"):
        texto = registro["data"].strftime("%d/%m/%Y às %H:%M")
        return texto + (f" (iBirder v{registro['versao']})" if registro.get("versao") else "")
    if registro.get("modificado_em"):
        return ("data não registrada (gravado por versão anterior à 1.3); arquivo modificado em "
                + registro["modificado_em"].strftime("%d/%m/%Y às %H:%M"))
    return "data não registrada (gravado por versão anterior à 1.3)"
