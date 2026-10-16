#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Teste real do WikiAves (sem abrir a interface do iBirder).

Para cada espécie, mede e registra:
  1. a busca interna do WikiAves (getTaxonsJSON.php) e o primeiro resultado;
  2. o fallback por DuckDuckGo/Bing, se a busca interna falhar;
  3. a extração dos dados da página da espécie;
  4. o link do eBird pela taxonomia embarcada.

Uso (na pasta do iBirder):
    python tools/testar_wikiaves.py              # Chrome invisível (como no app)
    python tools/testar_wikiaves.py --visivel    # Chrome visível, para observar
    python tools/testar_wikiaves.py "Nome cientifico" "Outro nome"

Gera tools/relatorio_wikiaves.txt (e HTMLs das falhas em tools/falhas_wikiaves/)
para enviar de volta e analisar.
"""

import json
import logging
import platform
import sys
import time
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ESPECIES_PADRAO = [
    "Pitangus sulphuratus",      # bem-te-vi (referência)
    "Turdus rufiventris",        # sabiá-laranjeira (acento e hífen no nome popular)
    "Furnarius rufus",           # joão-de-barro
    "Ramphastos toco",           # tucanuçu
    "Rupornis magnirostris",     # gavião-carijó (está nos rótulos do modelo)
    "Aramus guarauna",           # carão
    "Zonotrichia capensis",      # tico-tico
    "Haemorhous cassinii",       # ave norte-americana: deve dar "não encontrado"
]

PASTA_FALHAS = RAIZ / "tools" / "falhas_wikiaves"
RELATORIO = RAIZ / "tools" / "relatorio_wikiaves.txt"
linhas = []


def out(msg=""):
    print(msg)
    linhas.append(msg)


def salvar_html(bot, nome):
    try:
        PASTA_FALHAS.mkdir(parents=True, exist_ok=True)
        caminho = PASTA_FALHAS / f"{nome}.html"
        caminho.write_text(bot.driver.page_source, encoding="utf-8")
        return caminho.name
    except Exception:
        return "(não salvo)"


def testar_especie(bot, ws, ebird_taxonomy, sci):
    from selenium.webdriver.common.by import By
    res = {"especie": sci, "rota": None, "ok": False}
    slug = sci.replace(" ", "_")
    out(f"\n=== {sci} ===")

    # 1. Busca interna do WikiAves
    t = time.time()
    url_busca = f"{ws.WIKIAVES_URL}/getTaxonsJSON.php?term={sci.replace(' ', '%20')}"
    link = None
    try:
        bot._abrir(url_busca)
        desafio = ws.em_desafio_cloudflare(bot.driver.title, bot.driver.page_source)
        texto = bot.driver.find_element(By.TAG_NAME, "body").text
        try:
            resultados = ws.parse_json_da_pagina(texto)
        except ValueError:
            resultados = None
        out(f"  [1] Busca interna ({time.time() - t:.1f}s) | título: {bot.driver.title!r} | Cloudflare pendente: {desafio}")
        if resultados:
            out(f"      {len(resultados)} resultado(s). Primeiro (bruto): {json.dumps(resultados[0], ensure_ascii=False)[:300]}")
            escolhido = ws.escolher_resultado_busca(resultados, sci)
            if escolhido:
                link = f"{ws.WIKIAVES_URL}/wiki/{escolhido['wid']}"
                res["rota"] = "busca interna"
                out(f"      Escolhido: {escolhido.get('label')} -> {link}")
            else:
                out("      Nenhum resultado com o campo 'wid' (formato inesperado!)")
        else:
            out(f"      Sem JSON. Início da resposta: {texto[:200]!r} | HTML salvo: {salvar_html(bot, slug + '_busca')}")
    except Exception as e:
        out(f"  [1] Busca interna FALHOU: {e!r}")

    # 2. Fallback por buscadores
    if not link:
        t = time.time()
        query = f'site:wikiaves.com.br "{sci}"'
        link = bot._buscar_duckduckgo(query, "wikiaves.com.br/wiki/")
        rota = "DuckDuckGo"
        if not link:
            link = bot._buscar_bing(query, "wikiaves.com.br/wiki/")
            rota = "Bing"
        out(f"  [2] Fallback ({time.time() - t:.1f}s): {link or 'nenhum link'}")
        if link:
            res["rota"] = rota

    # 3. Extração
    if link:
        t = time.time()
        try:
            dados = bot.extrair_dados_especie(link)
            res["ok"] = True
            out(f"  [3] Extração OK ({time.time() - t:.1f}s)")
            for k, v in dados.items():
                v = str(v)
                out(f"      {k:20} {v[:90] + '…' if len(v) > 90 else v}")
        except Exception as e:
            out(f"  [3] Extração FALHOU ({time.time() - t:.1f}s): {e!r} | HTML salvo: {salvar_html(bot, slug + '_pagina')}")

    # 4. eBird (taxonomia embarcada)
    eb = ebird_taxonomy.buscar(sci)
    out(f"  [4] eBird: {eb['link'] + ' (' + eb['common_name'] + ')' if eb else 'não está na tabela'}")
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    visivel = "--visivel" in sys.argv
    especies = args or ESPECIES_PADRAO

    logging.basicConfig(level=logging.WARNING)
    out(f"Teste WikiAves | {time.strftime('%d/%m/%Y %H:%M')} | Python {platform.python_version()} | {platform.platform()}")
    out(f"Modo do Chrome: {'visível' if visivel else 'invisível (headless, igual ao app)'}")

    try:
        import selenium
        out(f"Selenium {selenium.__version__}")
        from modules.step2_biology import wiki_scraper as ws
        from modules.step5_taxonomy import ebird_taxonomy
    except ImportError as e:
        out(f"\nDependência faltando: {e}\nInstale com: pip install selenium webdriver-manager beautifulsoup4 lxml")
        return 1

    t = time.time()
    try:
        bot = ws.BuscadorBlindado(headless=not visivel)
    except Exception as e:
        out(f"\nNÃO FOI POSSÍVEL ABRIR O CHROME: {e!r}\nO Google Chrome está instalado?")
        out(traceback.format_exc())
        return 1
    out(f"Chrome {bot.driver.capabilities.get('browserVersion')} aberto em {time.time() - t:.1f}s")

    resultados = []
    inicio = time.time()
    try:
        for sci in especies:
            try:
                resultados.append(testar_especie(bot, ws, ebird_taxonomy, sci))
            except Exception as e:
                out(f"  ERRO inesperado: {e!r}")
                resultados.append({"especie": sci, "rota": None, "ok": False})
    finally:
        bot.fechar()

    out("\n=== RESUMO ===")
    for r in resultados:
        out(f"  {'OK   ' if r['ok'] else 'FALHA'} {r['especie']:28} via {r['rota'] or '-'}")
    ok = sum(r["ok"] for r in resultados)
    out(f"\n{ok}/{len(resultados)} espécies extraídas em {time.time() - inicio:.0f}s "
        f"({sum(r['rota'] == 'busca interna' for r in resultados)} pela busca interna do WikiAves).")
    RELATORIO.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório salvo em: {RELATORIO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
