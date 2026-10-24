#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Catálogo de espécies para a busca rápida (Ctrl+K), sem internet.

Junta as tabelas já embarcadas:
  - assets/ebird_taxonomy.csv: todas as espécies do eBird (nome científico, nome em
    inglês, ordem, família);
  - assets/conservacao/aves_registradas_brasil.csv: espécies com registro de grau de
    pesquisa no Brasil (iNaturalist, place 6878), que aparecem primeiro.

Não há nome popular em português embarcado: a busca casa nome científico e nome em
inglês. O nome popular continua vindo do WikiAves depois da busca.
"""

import csv
import logging
import threading
import unicodedata

from core.paths import APP_DIR

CSV_EBIRD = APP_DIR / "assets" / "ebird_taxonomy.csv"
CSV_BRASIL = APP_DIR / "assets" / "conservacao" / "aves_registradas_brasil.csv"

_catalogo = None
_lock = threading.Lock()


def _chave(texto):
    """Minúsculas, sem acento e sem espaços repetidos (para comparar)."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def _especie(nome):
    return " ".join(_chave(nome).split()[:2])


def _ler_csv(caminho):
    try:
        with open(caminho, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError as e:
        logging.error(f"Catálogo de espécies: não foi possível ler {caminho}: {e}")
        return []


def carregar():
    """Lista de espécies (dicts), as registradas no Brasil primeiro, depois em ordem alfabética."""
    global _catalogo
    with _lock:
        if _catalogo is not None:
            return _catalogo
        no_brasil = {_especie(l["nome_cientifico"]) for l in _ler_csv(CSV_BRASIL)}
        vistos = set()
        catalogo = []
        for linha in _ler_csv(CSV_EBIRD):
            chave = _especie(linha.get("scientific_name"))
            if not chave or chave in vistos:
                continue
            vistos.add(chave)
            catalogo.append({
                "nome_cientifico": linha["scientific_name"],
                "nome_ingles": linha.get("common_name", ""),
                "familia": linha.get("family", ""),
                "no_brasil": chave in no_brasil,
                "_cientifico": _chave(linha["scientific_name"]),
                "_ingles": _chave(linha.get("common_name", "")),
            })
        # Registradas no Brasil sem correspondência no eBird (sinônimos) também entram
        for chave in sorted(no_brasil - vistos):
            nome = chave.capitalize()
            catalogo.append({"nome_cientifico": nome, "nome_ingles": "", "familia": "",
                             "no_brasil": True, "_cientifico": chave, "_ingles": ""})
        catalogo.sort(key=lambda e: (not e["no_brasil"], e["_cientifico"]))
        logging.debug(f"Catálogo de espécies: {len(catalogo)} ({sum(e['no_brasil'] for e in catalogo)} no Brasil).")
        _catalogo = catalogo
        return _catalogo


def buscar(texto, limite=12):
    """
    Espécies cujo nome científico ou em inglês contém todas as palavras digitadas.
    Ordem: começa com o texto > registrada no Brasil > alfabética. Texto com menos de
    2 letras não busca nada.
    """
    alvo = _chave(texto)
    if len(alvo) < 2:
        return []
    palavras = alvo.split()
    achados = []
    for especie in carregar():
        campos = (especie["_cientifico"], especie["_ingles"])
        if not all(any(p in c for c in campos) for p in palavras):
            continue
        comeca = any(c.startswith(alvo) for c in campos)
        achados.append((not comeca, not especie["no_brasil"], especie["_cientifico"], especie))
    achados.sort(key=lambda a: a[:3])
    return [a[3] for a in achados[:limite]]


def rotulo(especie):
    """Texto da sugestão: 'Turdus rufiventris — Rufous-bellied Thrush'."""
    if especie["nome_ingles"]:
        return f"{especie['nome_cientifico']} — {especie['nome_ingles']}"
    return especie["nome_cientifico"]
