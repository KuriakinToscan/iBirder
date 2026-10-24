#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Renomeação da foto ao gravar os dados (v1.3).

Padrão: nome comum em PascalCase, sem acentos, + data de captura (EXIF):
    Sabiá-laranjeira, 16/10/2026  ->  SabiaLaranjeira_20261016.jpg
Nomes repetidos (fotos em sequência) recebem sufixo: BemTeVi_20261016_2.jpg.
Arquivos irmãos (RAW de mesmo nome e .xmp) podem ser renomeados junto.

O nome original fica na foto (XMP xmpMM:PreservedFileName, comentário e palavra-chave
iBirder|Arquivo|NomeOriginal), no .xmp do RAW e no histórico logs/renomeacoes.csv,
o que permite desfazer a renomeação.

Funções sem interface, para teste e reuso.
"""

import csv
import logging
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

PADROES = {
    "nome_data": "NomeComum_aaaammdd",
    "nome_data_hora": "NomeComum_aaaammdd_hhmmss",
    "cientifico_data": "NomeCientifico_aaaammdd",
}
PADRAO_PADRAO = "nome_data"

EXTENSOES_RAW = {".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".orf", ".rw2",
                 ".raf", ".dng", ".pef", ".srw", ".x3f", ".3fr", ".iiq", ".rwl"}

# Valores que não são nome de espécie (placeholders e falhas das etapas)
_NAO_NOMES = ("", "n/a", "n/d", "ave", "desconhecido", "desconhecida", "não encontrado",
              "identificação inconclusiva", "aguardando...")
_RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
_PROIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
TAMANHO_MAXIMO = 120


def sem_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def pascal_case(texto):
    """'Sabiá-laranjeira' -> 'SabiaLaranjeira'; 'joão-de-barro' -> 'JoaoDeBarro'."""
    partes = re.split(r"[^A-Za-z0-9]+", sem_acentos(texto or ""))
    return "".join(p[0].upper() + p[1:].lower() for p in partes if p)


def _nome_valido(nome):
    nome = (nome or "").strip()
    if nome.lower() in _NAO_NOMES or nome.lower().startswith(("não ", "erro", "falha")):
        return None
    return nome


def nome_comum(dados):
    """Nome comum (WikiAves; o orquestrador completa com o do iNaturalist); None se não houver."""
    return _nome_valido(dados.get("nome_comum"))


def nome_cientifico(dados):
    nome = _nome_valido(dados.get("nome_cientifico"))
    return nome if nome and len(nome.split()) >= 2 else None


def data_captura(caminho):
    """Data/hora de captura (EXIF DateTimeOriginal ou DateTimeDigitized); None se a foto não tiver."""
    try:
        from PIL import Image
        with Image.open(caminho) as img:
            exif_ifd = img.getexif().get_ifd(0x8769)
    except Exception as e:
        logging.debug(f"Sem EXIF legível em {caminho}: {e}")
        return None
    for tag in (0x9003, 0x9004):  # DateTimeOriginal, DateTimeDigitized
        valor = exif_ifd.get(tag)
        if isinstance(valor, bytes):
            valor = valor.decode("ascii", "ignore")
        try:
            return datetime.strptime(str(valor).strip("\x00 ")[:19], "%Y:%m:%d %H:%M:%S")
        except (TypeError, ValueError):
            continue
    return None


def sugerir_nome(dados, data, padrao=PADRAO_PADRAO):
    """
    Nome base (sem extensão) para o padrão escolhido. Sem data, termina em '_' para o
    usuário completar. None se não houver nome de espécie (ex.: identificação inconclusiva).
    """
    nome = nome_cientifico(dados) if padrao == "cientifico_data" else nome_comum(dados)
    if not nome:
        return None
    base = pascal_case(nome)
    if not data:
        return base + "_"
    base += "_" + data.strftime("%Y%m%d")
    if padrao == "nome_data_hora":
        base += "_" + data.strftime("%H%M%S")
    return base


def validar_nome(base):
    """Mensagem de erro para o nome digitado, ou None se ele for válido no Windows."""
    if not base or not base.strip():
        return "Digite um nome para o arquivo."
    if _PROIBIDOS.search(base):
        return 'O nome não pode conter \\ / : * ? " < > |'
    if base != base.strip() or base.endswith("."):
        return "O nome não pode começar ou terminar com espaço nem terminar com ponto."
    if base.split(".")[0].upper() in _RESERVADOS_WINDOWS:
        return "Esse nome é reservado pelo Windows."
    if len(base) > TAMANHO_MAXIMO:
        return f"Nome muito longo (máximo de {TAMANHO_MAXIMO} caracteres)."
    return None


def arquivos_irmaos(caminho):
    """
    RAW com o mesmo nome (IMG_1234.CR3 ao lado de IMG_1234.JPG) e arquivos .xmp
    (IMG_1234.xmp ou IMG_1234.JPG.xmp) na mesma pasta.
    """
    caminho = Path(caminho)
    irmaos = []
    try:
        vizinhos = list(caminho.parent.iterdir())
    except OSError:
        return []
    for f in vizinhos:
        if f.name == caminho.name or not f.is_file():
            continue
        mesmo_nome = f.stem == caminho.stem
        if (mesmo_nome and f.suffix.lower() in EXTENSOES_RAW | {".xmp"}) or \
                f.name.lower() == (caminho.name + ".xmp").lower():
            irmaos.append(f)
    return sorted(irmaos)


def _destino(origem, caminho_principal, base):
    """Novo caminho de um arquivo trocando o nome original da foto pela nova base."""
    return origem.with_name(base + origem.name[len(caminho_principal.stem):])


def _ocupado(destino, origem):
    """True se o destino já existe e não é o próprio arquivo (o Windows ignora maiúsculas)."""
    if not destino.exists():
        return False
    try:
        return not os.path.samefile(destino, origem)
    except OSError:
        return True


def nome_livre(caminho, base, irmaos=()):
    """Base disponível para a foto e seus irmãos: base, base_2, base_3..."""
    caminho = Path(caminho)
    arquivos = [caminho, *map(Path, irmaos)]
    candidato, n = base, 1
    while any(_ocupado(_destino(f, caminho, candidato), f) for f in arquivos):
        n += 1
        candidato = f"{base}_{n}"
    return candidato


def renomear(caminho, base, irmaos=()):
    """
    Renomeia a foto (e os irmãos) para a base indicada, com sufixo se necessário.
    Retorna (novo_caminho, [(antigo, novo), ...], [mensagens de falha dos irmãos]).
    Falha na foto principal lança OSError (ex.: arquivo aberto em outro programa).
    """
    caminho = Path(caminho)
    base = nome_livre(caminho, base, irmaos)
    novo = _destino(caminho, caminho, base)
    feitos, falhas = [], []
    if novo.name == caminho.name:
        return caminho, feitos, falhas
    os.rename(caminho, novo)
    feitos.append((caminho, novo))
    for irmao in map(Path, irmaos):
        destino = _destino(irmao, caminho, base)
        try:
            os.rename(irmao, destino)
            feitos.append((irmao, destino))
        except OSError as e:
            logging.warning(f"Não foi possível renomear {irmao.name}: {e}")
            falhas.append(f"{irmao.name}: {e.strerror or e}")
    for antigo, novo_nome in feitos:
        logging.info(f"Arquivo renomeado: {antigo.name} -> {novo_nome.name}")
    registrar_historico(feitos, "renomeado")
    return novo, feitos, falhas


# ---------------------------------------------------------------- Histórico e desfazer

def arquivo_historico():
    from core.paths import LOGS_DIR
    return Path(LOGS_DIR) / "renomeacoes.csv"


def registrar_historico(feitos, acao, arquivo=None):
    """Acrescenta as renomeações ao CSV (data; ação; pasta; nome antigo; nome novo)."""
    if not feitos:
        return
    arquivo = Path(arquivo) if arquivo else arquivo_historico()
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        novo_arquivo = not arquivo.exists()
        # utf-8-sig e ";" para abrir direto no Excel em português
        with open(arquivo, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            if novo_arquivo:
                w.writerow(["data", "acao", "pasta", "nome_antigo", "nome_novo"])
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for antigo, novo in feitos:
                w.writerow([agora, acao, str(Path(antigo).parent), Path(antigo).name, Path(novo).name])
    except OSError as e:
        logging.warning(f"Não foi possível atualizar o histórico de renomeações: {e}")


def desfazer_renomeacao(caminho, nome_original):
    """
    Volta a foto (e os arquivos irmãos renomeados junto) ao nome original.
    Nunca sobrescreve: se o nome original estiver ocupado, lança FileExistsError.
    Retorna (novo_caminho, [(antigo, novo), ...]).
    """
    caminho = Path(caminho)
    base = Path(nome_original).stem
    if base == caminho.stem:
        return caminho, []
    arquivos = [caminho, *arquivos_irmaos(caminho)]
    ocupados = [_destino(f, caminho, base).name for f in arquivos if _ocupado(_destino(f, caminho, base), f)]
    if ocupados:
        raise FileExistsError(f"já existe(m) na pasta: {', '.join(ocupados)}")
    feitos = []
    for f in arquivos:
        destino = _destino(f, caminho, base)
        os.rename(f, destino)
        feitos.append((f, destino))
        logging.info(f"Renomeação desfeita: {f.name} -> {destino.name}")
    registrar_historico(feitos, "desfeito")
    return feitos[0][1], feitos
