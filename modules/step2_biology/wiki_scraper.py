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

import requests
import urllib.parse
import re
import logging
import unicodedata
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

class BuscadorBlindado:
    """
    Buscador ultra-rápido via requisições HTTP seguras (Requests + BeautifulSoup).
    Elimina a dependência de browsers como o Selenium/Chrome.
    Resolve a URL do WikiAves através do nome popular gerado via iNaturalist API.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _slugify(self, text):
        if not text: return ""
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        return re.sub(r'[-\s]+', '-', text)

    def buscar_link_wikiaves(self, scientific_name):
        logging.info(f"Buscando no WikiAves: {scientific_name}")
        try:
            # 1. Obter nome popular em Português na API iNaturalist
            url_inat = f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(scientific_name)}&locale=pt-BR&rank=species"
            resp = self.session.get(url_inat, timeout=5)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    common = results[0].get('preferred_common_name')
                    if common:
                        slug = self._slugify(common)
                        wiki_url = f"https://www.wikiaves.com.br/wiki/{slug}"
                        
                        # 2. Validar se a página existe no WikiAves
                        r_wiki = self.session.get(wiki_url, timeout=5)
                        if r_wiki.status_code == 200:
                            soup = BeautifulSoup(r_wiki.text, 'lxml')
                            h1 = soup.find('h1')
                            if h1 and "topico ainda nao existe" not in unicodedata.normalize('NFD', h1.get_text()).lower():
                                logging.info(f"Link WikiAves encontrado via Slug ({common}): {wiki_url}")
                                return wiki_url

            # 3. Fallback: DuckDuckGo HTML POST (sem JS/Selenium)
            ddg_url = "https://html.duckduckgo.com/html/"
            r_ddg = self.session.post(ddg_url, data={'q': f'site:wikiaves.com.br "{scientific_name}"'}, timeout=5)
            if r_ddg.status_code == 200:
                soup_ddg = BeautifulSoup(r_ddg.text, 'lxml')
                for a in soup_ddg.find_all('a', class_='result__url', href=True):
                    href = a['href']
                    if 'wikiaves.com.br/wiki/' in href and not any(x in href for x in ['especies', 'comunicados', 'regras']):
                        clean_href = href.split('&')[0]
                        logging.info(f"Link WikiAves encontrado via DuckDuckGo: {clean_href}")
                        return clean_href
        except Exception as e:
            logging.error(f"Erro na busca de link WikiAves: {e}")
            
        logging.warning(f"Nenhum link WikiAves encontrado para {scientific_name}.")
        return None

    def buscar_link_ebird(self, scientific_name):
        logging.info(f"Buscando eBird: {scientific_name}")
        try:
            clean_code = scientific_name.replace(' ', '').lower()
            ebird_url = f"https://ebird.org/species/{clean_code}"
            return ebird_url
        except Exception as e:
            logging.error(f"Erro ao buscar eBird: {e}")
            return None

    def extrair_dados_especie(self, url):
        logging.debug(f"Extraindo dados de: {url}")
        dados = {}
        try:
            resp = self.session.get(url, timeout=8)
            if resp.status_code != 200:
                return dados
                
            soup = BeautifulSoup(resp.text, "lxml")

            # 🔹 Nome Comum (Título Principal h1)
            tag_h1 = soup.find("h1", class_="sectionedit1") or soup.find("h1", id="titulo") or soup.find("h1")
            dados["nome_comum"] = tag_h1.get_text(separator=" ", strip=True) if tag_h1 else "Não encontrado"

            # 🔹 Nome em Inglês
            h2_ingles = soup.find("h2", string=lambda t: t and "Nome em Inglês" in t)
            if h2_ingles and h2_ingles.next_sibling:
                dados["nome_ingles"] = str(h2_ingles.next_sibling).strip()
            else:
                dados["nome_ingles"] = "Desconhecido"

            # 🔹 Etimologia (Nome científico)
            sec_nome = soup.find("h2", id="nome_cientifico")
            if sec_nome:
                div_nome = sec_nome.find_next("div", class_="level2")
                if div_nome:
                    texto_limpo = div_nome.get_text(separator=" ", strip=True)
                    dados["etimologia"] = re.sub(r'\s+', ' ', texto_limpo)
                else:
                    dados["etimologia"] = "Não encontrado"
            else:
                dados["etimologia"] = "Não encontrado"

            # 🔹 Características
            sec_carac = soup.find("h2", id="caracteristicas")
            if sec_carac:
                div_carac = sec_carac.find_next("div", class_="level2")
                if div_carac:
                    paragrafo = div_carac.find("p")
                    if paragrafo:
                        texto_raw = paragrafo.get_text(separator=" ", strip=True)
                        dados["caracteristicas"] = re.sub(r'\s+', ' ', texto_raw)
                    else:
                        dados["caracteristicas"] = "Descrição não disponível."
                else:
                    dados["caracteristicas"] = "Não encontrado"
            else:
                dados["caracteristicas"] = "Não encontrado"

            # 🔹 Estado de Conservação (Fallback IUCN)
            dados["status_conservacao"] = "Não encontrado"
            links_iucn = soup.find_all("a", href=lambda href: href and "lista_vermelha_iucn" in href.lower())
            for link in links_iucn:
                texto = link.get_text(strip=True)
                if texto and "IUCN" not in texto.upper():
                    dados["status_conservacao"] = texto
                    break

            # 🔹 Taxonomia: Ordem e Família
            dados["ordem"] = "Desconhecida"
            dados["familia"] = "Desconhecida"
            todas_as_celulas = soup.find_all("td")
            for i, td in enumerate(todas_as_celulas):
                texto_celula = td.get_text(strip=True)
                if "Ordem:" in texto_celula and i + 1 < len(todas_as_celulas):
                    dados["ordem"] = todas_as_celulas[i+1].get_text(strip=True)
                elif "Família:" in texto_celula and i + 1 < len(todas_as_celulas):
                    dados["familia"] = todas_as_celulas[i+1].get_text(strip=True)

        except Exception as e:
            logging.error(f"Erro ao extrair dados da espécie em {url}: {e}")

        return dados

    def fechar(self):
        """Método de interface para desacoplamento sem necessidade de fechar drivers externos."""
        pass
