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
Taxonomia do eBird embarcada (assets/ebird_taxonomy.csv).

Gerada a partir de https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=csv&cat=species
(endpoint público, sem chave). Permite montar o link ebird.org/species/<código>,
o nome em inglês, a ordem e a família sem internet e sem buscador.
"""

import csv
import logging
import threading
from core.paths import APP_DIR

CSV_PATH = APP_DIR / "assets" / "ebird_taxonomy.csv"

_tabela = None
_lock = threading.Lock()


def _normalizar(nome):
    # Subespécies ("Junco hyemalis caniceps") caem para gênero + espécie
    return " ".join((nome or "").lower().split()[:2])


def _carregar():
    global _tabela
    with _lock:
        if _tabela is None:
            tabela = {}
            try:
                with open(CSV_PATH, encoding="utf-8", newline="") as f:
                    for row in csv.DictReader(f):
                        tabela[_normalizar(row["scientific_name"])] = row
                logging.debug(f"Taxonomia eBird carregada: {len(tabela)} espécies.")
            except Exception as e:
                logging.error(f"Falha ao carregar taxonomia eBird ({CSV_PATH}): {e}")
            _tabela = tabela
    return _tabela


def buscar(scientific_name):
    """Retorna dict com scientific_name, common_name, species_code, order, family e link (ou None)."""
    row = _carregar().get(_normalizar(scientific_name))
    if not row:
        return None
    return {**row, "link": f"https://ebird.org/species/{row['species_code']}"}
