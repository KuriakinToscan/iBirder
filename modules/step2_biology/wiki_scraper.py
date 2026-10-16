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
Busca de dados biológicos no WikiAves.

O WikiAves fica atrás de uma proteção do Cloudflare que recusa requisições HTTP
simples (403 "Just a moment..."), por isso as páginas são abertas num Chrome
headless via Selenium, como nas versões anteriores. O fluxo é:

  1. Busca no próprio WikiAves (getTaxonsJSON.php?term=<nome científico>, o mesmo
     endpoint do campo de busca do site) e usa o primeiro resultado retornado
     (o de nome científico idêntico, se houver) -> /wiki/<wid>;
  2. Se a busca interna não retornar nada: DuckDuckGo e, depois, Bing (fluxo antigo);
  3. Extração dos dados da página da espécie.
"""

import json
import logging
import random
import time
import urllib.parse
import base64
import re
from bs4 import BeautifulSoup

WIKIAVES_URL = "https://www.wikiaves.com.br"
TEMPO_ESPERA_MAX = 12
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ==================================================
# FUNÇÕES PURAS (testáveis sem rede)
# ==================================================

def _decodificar_link_bing(href):
    """Links do Bing vêm como bing.com/ck/a?...&u=a1<base64url>; devolve a URL real."""
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        u = qs.get("u", [""])[0]
        if u.startswith("a1"):
            u = u[2:]
            return base64.urlsafe_b64decode(u + "=" * (-len(u) % 4)).decode("utf-8", "ignore")
    except Exception:
        pass
    return href


def extrair_links(html, trecho_url):
    """
    Extrai, em ordem, os links de resultado que contêm `trecho_url`,
    desembrulhando os redirecionamentos do DuckDuckGo (uddg=) e do Bing (u=a1...).
    """
    soup = BeautifulSoup(html, "lxml")
    vistos = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("//"):
            href = "https:" + href
        if "uddg=" in href:
            href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
        elif "bing.com/ck/a" in href:
            href = _decodificar_link_bing(href)
        if trecho_url in href:
            limpo = href.split("&")[0].split("?")[0].split("#")[0]
            if limpo not in vistos:
                vistos.append(limpo)
    return vistos


def parse_pagina_especie(html):
    """Extrai os campos da página de espécie do WikiAves (estrutura DokuWiki)."""
    soup = BeautifulSoup(html, "lxml")
    dados = {}

    # 🔹 Nome Comum (Título Principal h1 - v0.8.5)
    tag_h1 = soup.find("h1", class_="sectionedit1") or soup.find("h1", id="titulo") or soup.find("h1")
    dados["nome_comum"] = tag_h1.get_text(separator=" ", strip=True) if tag_h1 else "Não encontrado"

    # 🔹 Nome em Inglês (v0.8.5)
    dados["nome_ingles"] = "Desconhecido"
    h2_ingles = soup.find("h2", string=lambda t: t and "Nome em Inglês" in t)
    if h2_ingles and h2_ingles.next_sibling:
        texto = str(h2_ingles.next_sibling).strip()
        if texto:
            dados["nome_ingles"] = texto

    # 🔹 Etimologia (Que o WikiAves chama de nome_cientifico)
    dados["etimologia"] = "Não encontrado"
    sec_nome = soup.find("h2", id="nome_cientifico")
    if sec_nome and (div_nome := sec_nome.find_next("div", class_="level2")):
        dados["etimologia"] = re.sub(r"\s+", " ", div_nome.get_text(separator=" ", strip=True))

    # 🔹 Características (apenas o primeiro parágrafo; ignora players e botões)
    dados["caracteristicas"] = "Não encontrado"
    sec_carac = soup.find("h2", id="caracteristicas")
    if sec_carac and (div_carac := sec_carac.find_next("div", class_="level2")):
        paragrafo = div_carac.find("p")
        if paragrafo:
            dados["caracteristicas"] = re.sub(r"\s+", " ", paragrafo.get_text(separator=" ", strip=True))
        else:
            dados["caracteristicas"] = "Descrição não disponível."

    # 🔹 Estado de Conservação (Fallback IUCN)
    dados["status_conservacao"] = "Não encontrado"
    for link in soup.find_all("a", href=lambda h: h and "lista_vermelha_iucn" in h.lower()):
        texto = link.get_text(strip=True)
        if texto and "IUCN" not in texto.upper():
            dados["status_conservacao"] = texto
            break

    # 🔹 Taxonomia: o TD com o rótulo é seguido pelo TD com o valor (v1.6.3)
    dados["ordem"] = "Desconhecida"
    dados["familia"] = "Desconhecida"
    celulas = soup.find_all("td")
    for i, td in enumerate(celulas[:-1]):
        texto_celula = td.get_text(strip=True)
        if "Ordem:" in texto_celula:
            dados["ordem"] = celulas[i + 1].get_text(strip=True)
        elif "Família:" in texto_celula:
            dados["familia"] = celulas[i + 1].get_text(strip=True)

    return dados


def em_desafio_cloudflare(titulo, html):
    """Detecta a página intermediária do Cloudflare independentemente do idioma do título."""
    titulo = (titulo or "").lower()
    # "_cf_chl_opt" só existe na página de desafio; "challenge-platform" não serve,
    # pois o Cloudflare também injeta esse script em páginas normais.
    return "just a moment" in titulo or "um momento" in titulo or "_cf_chl_opt" in (html or "")


def dados_de_especie_validos(dados):
    """
    A página precisa ter ao menos etimologia ou características. Evita aceitar a tela
    do Cloudflare ("www.wikiaves.com.br") ou páginas que não são de espécie.
    """
    return any(dados.get(k) not in (None, "", "Não encontrado") for k in ("etimologia", "caracteristicas"))


def escolher_resultado_busca(resultados, scientific_name):
    """
    Escolhe o resultado da busca do WikiAves (lista de dicts com id, wid, label, nome...).
    Usa o primeiro resultado retornado; se algum tiver o nome científico idêntico, prefere esse.
    """
    especies = [r for r in (resultados or []) if isinstance(r, dict) and r.get("wid")]
    if not especies:
        return None
    alvo = scientific_name.strip().lower()
    return next((r for r in especies if (r.get("label") or "").strip().lower() == alvo), especies[0])


def parse_json_da_pagina(texto):
    """O Chrome exibe JSON dentro de <pre>; aceita tanto o texto puro quanto o HTML."""
    texto = (texto or "").strip()
    if texto.startswith("<"):
        texto = BeautifulSoup(texto, "lxml").get_text()
    inicio = min([i for i in (texto.find("["), texto.find("{")) if i >= 0], default=-1)
    if inicio < 0:
        return None
    return json.loads(texto[inicio:])


# ==================================================
# BUSCADOR (Chrome headless)
# ==================================================

def _criar_driver(headless=True):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_argument(f"user-agent={USER_AGENT}")

    # Mesmo caminho das versões anteriores (webdriver-manager); se falhar,
    # o Selenium Manager embutido no Selenium 4.6+ localiza/baixa o driver.
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        logging.debug(f"webdriver-manager indisponível ({e}). Usando Selenium Manager.")
        return webdriver.Chrome(options=options)


class BuscadorBlindado:

    def __init__(self, headless=True):
        from selenium.webdriver.support.ui import WebDriverWait
        self.driver = _criar_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, TEMPO_ESPERA_MAX)

    # ---------- utilitários ----------

    def _abrir(self, url):
        """Abre a URL e aguarda o desafio do Cloudflare ("Just a moment..."/"Um momento...") terminar."""
        self.driver.get(url)
        limite = time.time() + TEMPO_ESPERA_MAX
        while em_desafio_cloudflare(self.driver.title, self.driver.page_source) and time.time() < limite:
            time.sleep(0.5)

    def _espera_humana(self):
        time.sleep(random.uniform(2, 4))

    # ---------- 1. busca interna do WikiAves ----------

    def _buscar_no_wikiaves(self, scientific_name):
        from selenium.webdriver.common.by import By
        url = f"{WIKIAVES_URL}/getTaxonsJSON.php?term={urllib.parse.quote(scientific_name)}"
        try:
            logging.debug(f"Busca interna WikiAves: {url}")
            self._abrir(url)
            try:
                resultados = parse_json_da_pagina(self.driver.find_element(By.TAG_NAME, "body").text)
            except ValueError:
                resultados = None  # ainda não é JSON (ex.: desafio não concluído)
            resultado = escolher_resultado_busca(resultados, scientific_name)
            if resultado:
                logging.debug(f"Primeiro resultado WikiAves: {resultado.get('label')} -> {resultado.get('wid')}")
                return f"{WIKIAVES_URL}/wiki/{resultado['wid']}"
            logging.debug("Busca interna do WikiAves não retornou espécies.")
        except Exception as e:
            logging.debug(f"Busca interna do WikiAves falhou: {e}")
        return None

    # ---------- 2. buscadores externos (fluxo antigo) ----------

    def _buscar_externo(self, url_busca, trecho_url):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        try:
            logging.debug(f"Pesquisa: {url_busca}")
            self._abrir(url_busca)
            self._espera_humana()
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
            links = extrair_links(self.driver.page_source, trecho_url)
            return links[0] if links else None
        except Exception as e:
            logging.debug(f"Pesquisa falhou ({url_busca}): {e}")
            return None

    def _buscar_duckduckgo(self, query, trecho_url):
        return self._buscar_externo(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}", trecho_url)

    def _buscar_bing(self, query, trecho_url):
        return self._buscar_externo(f"https://www.bing.com/search?q={urllib.parse.quote(query)}", trecho_url)

    # ---------- API pública ----------

    def buscar_link_wikiaves(self, scientific_name):
        logging.info(f"Buscando no WikiAves: {scientific_name}")

        link = self._buscar_no_wikiaves(scientific_name)
        if not link:
            query = f'site:wikiaves.com.br "{scientific_name}"'
            link = (self._buscar_duckduckgo(query, "wikiaves.com.br/wiki/")
                    or self._buscar_bing(query, "wikiaves.com.br/wiki/"))

        if link:
            logging.info(f"Link WikiAves encontrado: {link}")
        else:
            logging.warning("Nenhum link WikiAves encontrado.")
        return link

    def buscar_link_ebird(self, scientific_name):
        """Fallback quando a espécie não está na taxonomia eBird embarcada."""
        logging.info(f"Buscando eBird: {scientific_name}")
        return self._buscar_duckduckgo(f'site:ebird.org "{scientific_name}"', "ebird.org/species/")

    def extrair_dados_especie(self, url):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        logging.debug(f"Extraindo dados de: {url}")
        self._abrir(url)
        if em_desafio_cloudflare(self.driver.title, self.driver.page_source):
            raise ConnectionError("WikiAves bloqueou o acesso (verificação do Cloudflare não concluída).")
        # Aguarda as seções da página de espécie, não qualquer <h2>
        self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "h2#nome_cientifico, h2#caracteristicas")))
        dados = parse_pagina_especie(self.driver.page_source)
        if not dados_de_especie_validos(dados):
            raise ValueError(f"A página {url} não contém dados de espécie.")
        return dados

    def fechar(self):
        try:
            self.driver.quit()
        except Exception:
            pass


# Nome usado na v1.2 (alias)
BuscadorWikiAves = BuscadorBlindado
