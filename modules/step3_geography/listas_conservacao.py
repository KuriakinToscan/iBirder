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
Listas de conservação e ocorrência embarcadas (assets/conservacao/), geradas por
tools/atualizar_listas_conservacao.py:

- Lista nacional de aves ameaçadas e extintas (Portaria MMA nº 148/2022 — ICMBio);
- Anexos da CITES (Checklist oficial);
- Espécies de aves com registro no Brasil (iNaturalist).

Consultas offline e instantâneas. A comparação usa o ID do táxon no iNaturalist quando
disponível (imune a diferenças de nomenclatura CBRO x iNaturalist) e, como reserva, o
nome científico e os sinônimos.
"""

import csv
import logging
import threading

from core.paths import APP_DIR

PASTA = APP_DIR / "assets" / "conservacao"
FONTE_NACIONAL = "Portaria MMA nº 148/2022"

_lock = threading.Lock()
_cache = {}


def _normalizar(nome):
    return " ".join((nome or "").lower().split())


def _especie(nome):
    """'Thamnophilus caerulescens cearensis' -> 'thamnophilus caerulescens'."""
    return " ".join(_normalizar(nome).split()[:2])


def _ler(arquivo):
    with _lock:
        if arquivo not in _cache:
            try:
                with open(PASTA / arquivo, encoding="utf-8", newline="") as f:
                    _cache[arquivo] = list(csv.DictReader(f))
            except OSError as e:
                logging.error(f"Lista de conservação ausente ({arquivo}): {e}")
                _cache[arquivo] = []
        return _cache[arquivo]


# ---------------------------------------------------------------- Lista nacional (ICMBio/MMA)

def status_nacional(nome, inat_id=None):
    """
    Status na lista oficial brasileira para a espécie (não para subespécies).
    Retorna dict (categoria, categoria_extenso, anexo, fonte) ou None se não consta.
    """
    alvo = _normalizar(nome)
    for linha in _ler("lista_nacional_aves_mma2022.csv"):
        if len(linha["nome_cientifico"].split()) > 2:
            continue  # subespécie: ver subespecies_ameacadas()
        mesmo_id = inat_id and linha.get("inat_id") and str(inat_id) == linha["inat_id"]
        mesmo_nome = alvo in (_normalizar(linha["nome_cientifico"]), _normalizar(linha.get("nome_inaturalist")))
        if mesmo_id or mesmo_nome:
            return {**linha, "fonte": FONTE_NACIONAL}
    return None


def subespecies_ameacadas(nome):
    """Subespécies da espécie que constam na lista nacional (ex.: Thamnophilus caerulescens cearensis)."""
    alvo = _especie(nome)
    return [linha for linha in _ler("lista_nacional_aves_mma2022.csv")
            if len(linha["nome_cientifico"].split()) > 2 and _especie(linha["nome_cientifico"]) == alvo]


def descrever_status_nacional(nome, inat_id=None):
    """Texto para a interface e para a foto."""
    st = status_nacional(nome, inat_id)
    if st:
        return f"{st['categoria_extenso']} ({st['categoria']})"
    subs = subespecies_ameacadas(nome)
    if subs:
        lista = ", ".join(f"{s['nome_cientifico']} ({s['categoria']})" for s in subs)
        return f"Não ameaçada; subespécie ameaçada: {lista}"
    return "Não ameaçada (não consta na lista oficial)"


# ---------------------------------------------------------------- CITES

def anexo_cites(nome):
    """Código do anexo ('I', 'II', 'III', 'I/II', 'I/NC'...) ou None se a espécie não é listada."""
    alvo = _normalizar(nome)
    for linha in _ler("cites_aves.csv"):
        nomes = [linha["nome_cientifico"]] + [s for s in linha.get("sinonimos", "").split("|") if s]
        if alvo in {_normalizar(n) for n in nomes}:
            return linha["anexo"]
    return None


def descrever_cites(nome):
    anexo = anexo_cites(nome)
    if not anexo:
        return "Não listada"
    partes = anexo.split("/")
    principais = [p for p in partes if p != "NC"]
    texto = ("Anexo " + principais[0]) if len(principais) == 1 else ("Anexos " + " e ".join(principais))
    if len(principais) > 1:
        texto += " (varia por população)"
    if "NC" in partes:
        texto += " (algumas populações não listadas)"
    return texto


# ---------------------------------------------------------------- Ocorrência no Brasil

def registrada_no_brasil(nome, inat_id=None):
    """True se a espécie tem registro de grau de pesquisa no Brasil no iNaturalist."""
    alvo = _especie(nome)
    for linha in _ler("aves_registradas_brasil.csv"):
        if (inat_id and str(inat_id) == linha["inat_id"]) or _especie(linha["nome_cientifico"]) == alvo:
            return True
    return False


def total_registradas_brasil():
    return len(_ler("aves_registradas_brasil.csv"))
