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
Fonte única de dados taxonômicos do iNaturalist.

Antes, imagem de referência, IUCN, CITES, taxonomia e fallbacks faziam cada um
suas próprias chamadas a /v1/taxa (7 a 9 requisições por espécie). Agora uma
busca + um detalhe são feitos uma única vez por espécie e reaproveitados por
todas as etapas, inclusive quando rodam em paralelo.
"""

import logging
import threading
from core import http

INAT_API = "https://api.inaturalist.org/v1"

_cache = {}
_cache_lock = threading.Lock()
_key_locks = {}


class TaxonInfo:
    """Visão simplificada do taxon. Campos ausentes ficam None."""

    def __init__(self, search_result, detail):
        self.search = search_result or {}
        self.detail = detail or {}

    @property
    def found(self):
        return bool(self.search)

    @property
    def id(self):
        return self.search.get("id")

    @property
    def nome_comum_pt(self):
        # A busca é feita com locale=pt-BR, então preferred_common_name vem em português
        return self.search.get("preferred_common_name")

    @property
    def nome_ingles(self):
        return self.detail.get("english_common_name")

    @property
    def default_photo(self):
        return self.search.get("default_photo") or self.detail.get("default_photo")

    @property
    def conservation_statuses(self):
        return self.detail.get("conservation_statuses") or self.search.get("conservation_statuses") or []

    @property
    def url(self):
        return f"https://www.inaturalist.org/taxa/{self.id}" if self.id else ""

    def ancestor(self, rank):
        for anc in self.detail.get("ancestors", []):
            if anc.get("rank") == rank:
                return anc.get("name")
        return None

    def status_por_autoridade(self, trecho):
        """Primeiro status de conservação cuja autoridade contém `trecho` (ex.: 'IUCN', 'CITES')."""
        trecho = trecho.upper()
        for s in self.conservation_statuses:
            if trecho in (s.get("authority") or "").upper():
                return s
        return None


def _buscar(sci_name):
    session = http.get_session()
    resp = session.get(
        f"{INAT_API}/taxa",
        params={"q": sci_name, "is_active": "true", "rank": "species", "per_page": 1, "locale": "pt-BR"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return TaxonInfo(None, None)

    search = results[0]
    detail = None
    try:
        # O detalhe traz ancestrais (ordem/família), nome em inglês e todos os status de conservação
        resp_d = session.get(f"{INAT_API}/taxa/{search['id']}", timeout=10)
        if resp_d.status_code == 200:
            detail = (resp_d.json().get("results") or [None])[0]
    except Exception as e:
        logging.warning(f"[TaxonService] Detalhe indisponível para {sci_name}: {e}")
    return TaxonInfo(search, detail)


def get_taxon(sci_name):
    """
    Retorna TaxonInfo da espécie (com cache em memória e thread-safe).
    Lança exceção em erro de rede, para que cada etapa decida a mensagem a exibir.
    Resultados de erro não ficam em cache, permitindo nova tentativa.
    """
    key = (sci_name or "").strip().lower()
    if not key:
        return TaxonInfo(None, None)

    with _cache_lock:
        if key in _cache:
            return _cache[key]
        key_lock = _key_locks.setdefault(key, threading.Lock())

    # Etapas paralelas pedindo a mesma espécie esperam a primeira busca terminar
    with key_lock:
        with _cache_lock:
            if key in _cache:
                return _cache[key]
        info = _buscar(sci_name)
        with _cache_lock:
            _cache[key] = info
        logging.debug(f"[TaxonService] {sci_name}: id={info.id} (cache populado)")
        return info


def clear_cache():
    with _cache_lock:
        _cache.clear()
        _key_locks.clear()
