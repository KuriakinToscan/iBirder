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


def test_slug_remove_acentos_e_espacos():
    assert ws.slug_wikiaves("Sabiá-laranjeira") == "sabia-laranjeira"
    assert ws.slug_wikiaves("João-de-barro") == "joao-de-barro"
    assert ws.slug_wikiaves("Tico tico") == "tico-tico"
    assert ws.slug_wikiaves(None) is None


def test_links_duckduckgo_desembrulha_uddg():
    html = ('<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.wikiaves.com.br%2Fwiki%2Fbem-te-vi&rut=x">r</a>'
            '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Febird.org%2Fspecies%2Fgrekis%3Fsiteid%3D1">e</a>')
    assert ws.extrair_links(html, "wikiaves.com.br/wiki/") == ["https://www.wikiaves.com.br/wiki/bem-te-vi"]
    assert ws.extrair_links(html, "ebird.org/species/") == ["https://ebird.org/species/grekis"]


def test_links_bing_decodifica_base64():
    enc = base64.urlsafe_b64encode(b"https://www.wikiaves.com.br/wiki/bem-te-vi").decode().rstrip("=")
    html = f'<a href="https://www.bing.com/ck/a?!&&p=abc&u=a1{enc}&ntb=1">r</a>'
    assert ws.extrair_links(html, "wikiaves.com.br/wiki/") == ["https://www.wikiaves.com.br/wiki/bem-te-vi"]


def test_pagina_corresponde_exige_nome_cientifico():
    assert ws.pagina_corresponde(WIKI_HTML, "Pitangus sulphuratus")
    assert not ws.pagina_corresponde("<html>outra ave</html>", "Pitangus sulphuratus")
    assert not ws.pagina_corresponde(None, "Pitangus sulphuratus")


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
