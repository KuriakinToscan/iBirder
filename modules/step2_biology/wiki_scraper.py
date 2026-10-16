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
Busca de dados biológicos no WikiAves sem navegador.

Até a v1.1 esta etapa abria um Chrome invisível (Selenium) a cada espécie, com
esperas artificiais de 2–4 s, e exigia o Google Chrome instalado. Agora tudo é
feito com requisições HTTP diretas (requests + BeautifulSoup), na ordem:

  1. URL direta do WikiAves montada a partir do nome popular em português
     (vindo do iNaturalist), validada pela presença do nome científico na página;
  2. DuckDuckGo (versão HTML);
  3. Bing;
  4. Último recurso: Selenium/Chrome, somente se estiverem instalados.
"""

import base64
import logging
import re
import unicodedata
import urllib.parse
from bs4 import BeautifulSoup
from core import http

WIKIAVES_BASE = "https://www.wikiaves.com.br/wiki/"
TIMEOUT = 10


# ==================================================
# FUNÇÕES PURAS (testáveis sem rede)
# ==================================================

def slug_wikiaves(nome_comum):
    """'Sabiá-laranjeira' -> 'sabia-laranjeira' (padrão das URLs do WikiAves)."""
    if not nome_comum:
        return None
    texto = unicodedata.normalize("NFKD", nome_comum).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return texto or None


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


def pagina_corresponde(html, scientific_name):
    """Confere se a página do WikiAves é mesmo da espécie (evita homônimos de nome popular)."""
    return bool(html) and scientific_name.lower() in html.lower()


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


# ==================================================
# BUSCADOR
# ==================================================

class BuscadorWikiAves:

    def __init__(self):
        self.session = http.get_session()
        self._html_cache = {}

    def _get_html(self, url):
        if url in self._html_cache:
            return self._html_cache[url]
        resp = self.session.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        self._html_cache[url] = resp.text
        return resp.text

    # ---------- Buscadores ----------

    def _buscar_duckduckgo(self, query, trecho_url):
        try:
            resp = self.session.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=TIMEOUT)
            if resp.status_code == 200:
                return extrair_links(resp.text, trecho_url)
            logging.debug(f"DuckDuckGo respondeu {resp.status_code}.")
        except Exception as e:
            logging.debug(f"DuckDuckGo falhou: {e}")
        return []

    def _buscar_bing(self, query, trecho_url):
        try:
            resp = self.session.get("https://www.bing.com/search", params={"q": query}, timeout=TIMEOUT)
            if resp.status_code == 200:
                return extrair_links(resp.text, trecho_url)
            logging.debug(f"Bing respondeu {resp.status_code}.")
        except Exception as e:
            logging.debug(f"Bing falhou: {e}")
        return []

    # ---------- API pública ----------

    def buscar_link_wikiaves(self, scientific_name, nome_comum_pt=None):
        logging.info(f"Buscando no WikiAves: {scientific_name}")

        # 1. URL direta pelo nome popular (1 requisição, sem buscador)
        slug = slug_wikiaves(nome_comum_pt)
        if slug:
            url = WIKIAVES_BASE + slug
            try:
                if pagina_corresponde(self._get_html(url), scientific_name):
                    logging.info(f"Link WikiAves (URL direta): {url}")
                    return url
            except Exception as e:
                logging.debug(f"URL direta do WikiAves falhou: {e}")

        # 2 e 3. Buscadores, validando cada candidato
        query = f'site:wikiaves.com.br "{scientific_name}"'
        for buscador in (self._buscar_duckduckgo, self._buscar_bing):
            for link in buscador(query, "wikiaves.com.br/wiki/")[:3]:
                try:
                    if pagina_corresponde(self._get_html(link), scientific_name):
                        logging.info(f"Link WikiAves encontrado: {link}")
                        return link
                except Exception as e:
                    logging.debug(f"Candidato {link} falhou: {e}")

        # 4. Último recurso: navegador (somente se Selenium e Chrome estiverem disponíveis)
        link = _buscar_link_via_navegador(scientific_name)
        if link:
            return link

        logging.warning("Nenhum link WikiAves encontrado.")
        return None

    def buscar_link_ebird(self, scientific_name):
        logging.info(f"Buscando eBird: {scientific_name}")
        query = f'site:ebird.org "{scientific_name}"'
        for buscador in (self._buscar_duckduckgo, self._buscar_bing):
            links = buscador(query, "ebird.org/species/")
            if links:
                return links[0]
        return None

    def extrair_dados_especie(self, url):
        logging.debug(f"Extraindo dados de: {url}")
        html = self._get_html(url)
        if not html:
            raise ConnectionError(f"Não foi possível carregar {url}")
        return parse_pagina_especie(html)

    def fechar(self):
        self._html_cache.clear()


# Compatibilidade com o nome antigo
BuscadorBlindado = BuscadorWikiAves


def _buscar_link_via_navegador(scientific_name):
    """Fallback opcional com Chrome headless. Ignorado se Selenium/Chrome não existirem."""
    try:
        from selenium import webdriver
    except ImportError:
        return None

    driver = None
    try:
        logging.info("Buscas HTTP falharam. Tentando via navegador (Selenium)...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--log-level=3")
        options.add_argument(f"user-agent={http.BROWSER_UA}")
        # O Selenium 4.6+ localiza/baixa o driver sozinho (Selenium Manager)
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(TIMEOUT)
        query = urllib.parse.quote(f'site:wikiaves.com.br "{scientific_name}"')
        driver.get(f"https://html.duckduckgo.com/html/?q={query}")
        links = extrair_links(driver.page_source, "wikiaves.com.br/wiki/")
        return links[0] if links else None
    except Exception as e:
        logging.debug(f"Fallback via navegador indisponível: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
