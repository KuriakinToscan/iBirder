#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Gera as tabelas embarcadas de conservação e ocorrência (ferramenta de manutenção).

Uso (na pasta do projeto, com internet; exige o pdftotext do poppler-utils):
    python tools/atualizar_listas_conservacao.py

Saídas:
  assets/conservacao/lista_nacional_aves_mma2022.csv
      Aves da Portaria MMA nº 148/2022 (Anexo 2: ameaçadas e extintas), com o ID do
      táxon no iNaturalist para comparar por ID (imune a sinônimos CBRO x iNaturalist).
  assets/conservacao/cites_aves.csv
      Espécies de aves com anexo da CITES (Checklist oficial, speciesplus.net), com
      sinônimos. O anexo já considera listagens herdadas de gênero/família/ordem.
  assets/conservacao/aves_registradas_brasil.csv
      Espécies de aves com registro "grau de pesquisa" no Brasil (iNaturalist, place 6878),
      usadas para avisar quando a IA local sugere uma espécie sem registro no país.

Rode novamente quando houver nova portaria, nova reunião da CITES (CoP) ou periodicamente
para a lista de ocorrência.
"""

import csv
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets" / "conservacao"
PORTARIA_URL = "https://www.gov.br/icmbio/pt-br/assuntos/centros-de-pesquisa/aves-silvestres/arquivos/portaria-148-2022.pdf"
CITES_URL = "https://www.speciesplus.net/checklist/taxon_concepts.json"
INAT = "https://api.inaturalist.org/v1"
PLACE_BRASIL = 6878
UA = {"User-Agent": "iBirder-manutencao (https://github.com/KuriakinToscan/iBirder)"}

CATEGORIAS = {"VU": "Vulnerável", "EN": "Em Perigo", "CR": "Criticamente em Perigo",
              "CR (PEX)": "Criticamente em Perigo (Provavelmente Extinta)", "EW": "Extinta na Natureza",
              "EX": "Extinta", "RE": "Regionalmente Extinta (Extinta no Brasil)"}


def baixar_json(url, cabecalhos=None, tentativas=4):
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={**UA, **(cabecalhos or {})})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as e:
            if n == tentativas - 1:
                raise
            print(f"   nova tentativa ({e.__class__.__name__})...")
            time.sleep(3 * (n + 1))


# ---------------------------------------------------------------- MMA / ICMBio

def extrair_portaria(pdf):
    texto = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    linhas = texto.splitlines()
    linha_re = re.compile(r'^\s*(\d+)\s*(\*)?\s+([A-Z][a-z]+formes)\s+([A-Z][a-z]+idae)\s+(.+?)\s+'
                          r'(CR \(PEX\)|CR|EN|VU|EW|EX|RE)\s*$')
    grupo_re = re.compile(r'^\s{5,}([A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{4,})\s*$')

    def secao(inicio, fim):
        grupo, saida = None, []
        for linha in linhas[inicio:fim]:
            m = linha_re.match(linha)
            g = grupo_re.match(linha)
            if g and not m:
                grupo = g.group(1).strip()
            elif m and grupo == "AVES":
                saida.append(m.groups())
        return saida

    a1 = next(i for i, l in enumerate(linhas) if "ANEXO I. LISTA OFICIAL DA FAUNA BRASILEIRA AMEAÇADA" in l)
    a2 = next(i for i, l in enumerate(linhas) if "ANEXO II. LISTA OFICIAL DE ESPÉCIES EXTINTAS DA FAUNA" in l and i > a1)
    a3 = next(i for i, l in enumerate(linhas) if l.strip() == "ANEXO 3" and i > a2)
    ameacadas, extintas = secao(a1, a2), secao(a2, a3)
    numeros = sorted(int(x[0]) for x in ameacadas)
    if numeros != list(range(numeros[0], numeros[-1] + 1)):
        raise RuntimeError("Numeração das aves ameaçadas incompleta: revise o formato do PDF.")
    return ameacadas, extintas


# Nomes da portaria (CBRO) que a busca do iNaturalist não encontra como sinônimo
EQUIVALENTES_INAT = {
    "Urubitinga coronata": "Buteogallus coronatus",
    "Hydropsalis candicans": "Eleothreptus candicans",
}


def _radical(epiteto):
    """Epíteto sem a terminação de gênero (dominicanus/dominicana, spilopterus/spiloptera)."""
    return re.sub(r"(us|um|a|is|e)$", "", epiteto.lower())


def inat_id(nome):
    """
    ID do táxon no iNaturalist para o nome (a busca aceita sinônimos).
    - Subespécie só casa com subespécie: cair para a espécie marcaria a espécie inteira
      como ameaçada (a portaria lista 51 subespécies de aves).
    - O último epíteto precisa ser igual: aceita mudança de gênero (Amadonastur lacernulatus
      -> Buteogallus lacernulatus) e de gênero gramatical (Xolmis dominicanus -> Heteroxolmis
      dominicana), mas não táxons agrupados pelo iNaturalist (Thalasseus
      acuflavidus -> T. sandvicensis) nem outra subespécie da mesma espécie.
    Sem ID, o app compara só pelo nome.
    """
    busca = EQUIVALENTES_INAT.get(nome, nome)
    rank = "subspecies" if len(nome.split()) > 2 else "species"
    d = baixar_json(f"{INAT}/taxa?" + urllib.parse.urlencode({"q": busca, "is_active": "true", "per_page": 10}))
    for r in d.get("results", []):
        if (r.get("rank") == rank and r.get("iconic_taxon_name") == "Aves"
                and _radical(r["name"].split()[-1]) == _radical(busca.split()[-1])):
            return r["id"], r["name"]
    return "", ""


def gerar_mma():
    print("1/3 Lista nacional (Portaria MMA 148/2022)...")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "portaria148.pdf"
        urllib.request.urlretrieve(PORTARIA_URL, pdf)
        ameacadas, extintas = extrair_portaria(pdf)
    linhas = []
    for anexo, itens in (("I - Ameaçadas", ameacadas), ("II - Extintas", extintas)):
        for _, _, ordem, familia, nome, cat in itens:
            tid, nome_inat = inat_id(nome)
            linhas.append([nome, ordem, familia, cat, CATEGORIAS[cat], anexo, tid, nome_inat])
            time.sleep(1)
    with open(DESTINO / "lista_nacional_aves_mma2022.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nome_cientifico", "ordem", "familia", "categoria", "categoria_extenso", "anexo",
                    "inat_id", "nome_inaturalist"])
        w.writerows(linhas)
    sem_id = [l[0] for l in linhas if not l[6]]
    print(f"   {len(linhas)} aves ({len(ameacadas)} ameaçadas, {len(extintas)} extintas); sem ID no iNaturalist: {sem_id}")


# ---------------------------------------------------------------- CITES

def gerar_cites():
    print("2/3 CITES (Checklist oficial)...")
    todos, pagina = [], 1
    while True:
        d = baixar_json(CITES_URL + "?" + urllib.parse.urlencode(
            {"scientific_name": "Aves", "per_page": 500, "page": pagina, "show_synonyms": 1, "show_english": 1}),
            {"Accept": "application/json"})[0]
        lote = d.get("animalia") or []
        todos += lote
        if not lote or len(todos) >= d["total_cnt"]:
            break
        pagina += 1
        time.sleep(1)
    especies = [x for x in todos if x.get("class_name") == "Aves" and x["rank_name"] in ("SPECIES", "SUBSPECIES")
                and x.get("current_listing")]
    with open(DESTINO / "cites_aves.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nome_cientifico", "anexo", "sinonimos", "nome_ingles"])
        for x in sorted(especies, key=lambda x: x["full_name"]):
            w.writerow([x["full_name"], x["current_listing"], "|".join(x.get("synonyms") or []),
                        (x.get("english_names") or [""])[0]])
    print(f"   {len(especies)} espécies/subespécies de aves com anexo")


# ---------------------------------------------------------------- Ocorrência no Brasil

def gerar_ocorrencia_brasil():
    print("3/3 Aves com registro no Brasil (iNaturalist)...")
    linhas, pagina = [], 1
    while True:
        d = baixar_json(f"{INAT}/observations/species_counts?" + urllib.parse.urlencode(
            {"place_id": PLACE_BRASIL, "taxon_id": 3, "rank": "species", "quality_grade": "research",
             "per_page": 500, "page": pagina}))
        for r in d["results"]:
            linhas.append([r["taxon"]["name"], r["taxon"]["id"], r["count"]])
        if pagina * 500 >= d["total_results"]:
            break
        pagina += 1
        time.sleep(1)
    with open(DESTINO / "aves_registradas_brasil.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nome_cientifico", "inat_id", "observacoes"])
        w.writerows(sorted(linhas))
    print(f"   {len(linhas)} espécies")


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    etapas = {"mma": gerar_mma, "cites": gerar_cites, "brasil": gerar_ocorrencia_brasil}
    for nome in (sys.argv[1:] or etapas):
        etapas[nome]()
    print("Concluído. Rode os testes (python -m pytest tests) antes de versionar.")
