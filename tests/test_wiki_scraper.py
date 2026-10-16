"""Testes offline do buscador do WikiAves (rodar com: python -m pytest tests)."""
import base64
from modules.step2_biology import wiki_scraper as ws

WIKI_HTML = """<html><body>
<h1 class="sectionedit1">Bem-te-vi</h1>
<h2>Nome em Inglês</h2>Great Kiskadee
<h2 id="nome_cientifico">Nome Científico</h2><div class="level2"><p>Pitangus sulphuratus  vem do tupi
 pitanguá</p></div>
<h2 id="caracteristicas">Características</h2><div class="level2"><p>Mede cerca de
 22 cm.</p><p>outro</p></div>
<a href="/wiki/lista_vermelha_iucn">IUCN</a><a href="/wiki/lista_vermelha_iucn">Pouco preocupante</a>
<table><tr><td>Ordem:</td><td>Passeriformes</td></tr><tr><td>Família:</td><td>Tyrannidae</td></tr></table>
</body></html>"""


def test_links_duckduckgo_desembrulha_uddg():
    html = ('<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.wikiaves.com.br%2Fwiki%2Fbem-te-vi&rut=x">r</a>'
            '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Febird.org%2Fspecies%2Fgrekis%3Fsiteid%3D1">e</a>')
    assert ws.extrair_links(html, "wikiaves.com.br/wiki/") == ["https://www.wikiaves.com.br/wiki/bem-te-vi"]
    assert ws.extrair_links(html, "ebird.org/species/") == ["https://ebird.org/species/grekis"]


def test_links_bing_decodifica_base64():
    enc = base64.urlsafe_b64encode(b"https://www.wikiaves.com.br/wiki/bem-te-vi").decode().rstrip("=")
    html = f'<a href="https://www.bing.com/ck/a?!&&p=abc&u=a1{enc}&ntb=1">r</a>'
    assert ws.extrair_links(html, "wikiaves.com.br/wiki/") == ["https://www.wikiaves.com.br/wiki/bem-te-vi"]


def test_parse_pagina_especie():
    assert ws.parse_pagina_especie(WIKI_HTML) == {
        "nome_comum": "Bem-te-vi",
        "nome_ingles": "Great Kiskadee",
        "etimologia": "Pitangus sulphuratus vem do tupi pitanguá",
        "caracteristicas": "Mede cerca de 22 cm.",
        "status_conservacao": "Pouco preocupante",
        "ordem": "Passeriformes",
        "familia": "Tyrannidae",
    }


# Formato do getTaxonsJSON.php (campos usados: wid = página na wiki, label = nome científico)
TAXONS = [
    {"id": "11000", "wid": "bem-te-vi-rajado", "label": "Myiodynastes maculatus", "nome": "bem-te-vi-rajado"},
    {"id": "11001", "wid": "bem-te-vi", "label": "Pitangus sulphuratus", "nome": "bem-te-vi"},
]


def test_busca_wikiaves_usa_primeiro_resultado():
    assert ws.escolher_resultado_busca(TAXONS, "Tyrannus melancholicus")["wid"] == "bem-te-vi-rajado"


def test_busca_wikiaves_prefere_nome_cientifico_identico():
    assert ws.escolher_resultado_busca(TAXONS, "pitangus sulphuratus ")["wid"] == "bem-te-vi"


def test_busca_wikiaves_sem_resultados():
    assert ws.escolher_resultado_busca([], "Pitangus sulphuratus") is None
    assert ws.escolher_resultado_busca(None, "Pitangus sulphuratus") is None


def test_json_exibido_pelo_chrome():
    import json
    bruto = json.dumps(TAXONS)
    assert ws.parse_json_da_pagina(bruto) == TAXONS
    assert ws.parse_json_da_pagina(f"<html><body><pre>{bruto}</pre></body></html>") == TAXONS
    assert ws.parse_json_da_pagina("<html>Just a moment...</html>") is None


def test_detecta_desafio_cloudflare_em_qualquer_idioma():
    assert ws.em_desafio_cloudflare("Just a moment...", "")
    assert ws.em_desafio_cloudflare("Um momento…", "")
    assert ws.em_desafio_cloudflare("", "<script>window._cf_chl_opt={}</script>")
    assert not ws.em_desafio_cloudflare("Bem-te-vi | Wiki Aves", "<h1>Bem-te-vi</h1>")


def test_rejeita_pagina_que_nao_e_de_especie():
    assert ws.dados_de_especie_validos(ws.parse_pagina_especie(WIKI_HTML))
    desafio = "<html><body><h1>www.wikiaves.com.br</h1><h2>Verificando se você é humano</h2></body></html>"
    assert not ws.dados_de_especie_validos(ws.parse_pagina_especie(desafio))
