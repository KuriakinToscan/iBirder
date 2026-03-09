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

import time
import random
import urllib.parse
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


# ==============================
# CONFIGURAÇÃO
# ==============================
AVES_ALVO = [
    "Turdus rufiventris",
]

TEMPO_ESPERA_MAX = 12
# ==============================


class BuscadorBlindado:

    def __init__(self):
        options = webdriver.ChromeOptions()

        # 🔹 NÍVEL 1 — Headless real (invisível)
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

        # Anti-detecção básica
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Reduz logs do Chrome
        options.add_argument("--log-level=3")
        options.add_argument("--disable-logging")

        # User-Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        self.wait = WebDriverWait(self.driver, TEMPO_ESPERA_MAX)

    # ==================================================
    # FUNÇÃO PRINCIPAL
    # ==================================================

    def buscar_link_wikiaves(self, scientific_name):

        logging.info(f"Buscando no WikiAves: {scientific_name}")

        link = self._tentar_google(scientific_name)

        if not link:
            logging.debug("Google falhou. Tentando Bing...")
            link = self._tentar_bing(scientific_name)

        if link:
            logging.info(f"Link WikiAves encontrado: {link}")
            return link
        else:
            logging.warning("Nenhum link WikiAves encontrado.")
            # self.driver.save_screenshot("erro_tela.png") # Removido para limpeza de lixo
            return None

    def buscar_link_ebird(self, scientific_name):
        logging.info(f"Buscando eBird: {scientific_name}")
        try:
            query = f'site:ebird.org "{scientific_name}"'
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            logging.debug(f"Google (eBird): {url}")
            self.driver.get(url)

            self._espera_humana()
            self._aceitar_consentimento_google()

            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'ebird.org/species/')]")
                )
            )

            links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href,'ebird.org/species/')]"
            )

            for l in links:
                href = l.get_attribute("href")
                if href and "ebird.org/species/" in href:
                    # Limpa parâmetros de busca se houver
                    clean_href = href.split("?")[0].split("#")[0]
                    return clean_href

            return None
        except Exception as e:
            logging.error(f"Erro ao buscar eBird: {e}")
            return None

    # ==================================================
    # GOOGLE
    # ==================================================

    def _tentar_google(self, term):

        try:
            query = f'site:wikiaves.com.br "{term}"'
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            logging.debug(f"Pesquisa Google: {url}")
            self.driver.get(url)

            self._espera_humana()
            self._aceitar_consentimento_google()

            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'wikiaves.com.br/wiki/')]")
                )
            )

            links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href,'wikiaves.com.br/wiki/')]"
            )

            for l in links:
                href = l.get_attribute("href")
                if href and "wikiaves.com.br/wiki/" in href:
                    return href.split("&")[0]

            return None

        except TimeoutException:
            logging.debug("Google não retornou resultados válidos (Timeout).")
            return None
        except Exception as e:
            logging.error(f"Erro no Scraper (Google): {e}")
            return None

    # ==================================================
    # BING
    # ==================================================

    def _tentar_bing(self, term):

        try:
            query = f'site:wikiaves.com.br "{term}"'
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"

            logging.debug(f"Pesquisa Bing: {url}")
            self.driver.get(url)

            self._espera_humana()

            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'wikiaves.com.br/wiki/')]")
                )
            )

            links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href,'wikiaves.com.br/wiki/')]"
            )

            for l in links:
                href = l.get_attribute("href")
                if href and "wikiaves.com.br/wiki/" in href:
                    return href.split("&")[0]

            return None

        except TimeoutException:
            logging.debug("Bing não retornou resultados válidos (Timeout).")
            return None
        except Exception as e:
            logging.error(f"Erro no Scraper (Bing): {e}")
            return None

    # ==================================================
    # EXTRAÇÃO DAS SEÇÕES ESPECÍFICAS
    # ==================================================

    def extrair_dados_especie(self, url):

        logging.debug(f"Extraindo dados de: {url}")

        self.driver.get(url)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "h2"))
        )

        html = self.driver.page_source
        soup = BeautifulSoup(html, "lxml")

        dados = {}

        # 🔹 Nome Comum (Título Principal h1 - v0.8.5)
        # O seletor foi atualizado para class sectionedit1 conforme estrutura real do WikiAves
        tag_h1 = soup.find("h1", class_="sectionedit1")
        if tag_h1:
             dados["nome_comum"] = tag_h1.get_text(separator=" ", strip=True)
        else:
             # Fallback para o id antigo ou seletor genérico
             tag_h1 = soup.find("h1", id="titulo") or soup.find("h1")
             dados["nome_comum"] = tag_h1.get_text(separator=" ", strip=True) if tag_h1 else "Não encontrado"

        # 🔹 Nome em Inglês (v0.8.5 - Novo campo capturado do WikiAves)
        h2_ingles = soup.find("h2", string=lambda t: t and "Nome em Inglês" in t)
        if h2_ingles:
            # Pega o conteúdo de texto imediatamente após o H2
            texto_prox = h2_ingles.next_sibling
            if texto_prox:
                dados["nome_ingles"] = str(texto_prox).strip()
            else:
                dados["nome_ingles"] = "Desconhecido"
        else:
            dados["nome_ingles"] = "Desconhecido"

        # 🔹 Etimologia (Que o WikiAves chama de nome_cientifico)
        sec_nome = soup.find("h2", id="nome_cientifico")
        if sec_nome:
            div_nome = sec_nome.find_next("div", class_="level2")
            if div_nome:
                # Normalização de espaços e quebras de linha (v0.4.9)
                texto_limpo = div_nome.get_text(separator=" ", strip=True)
                dados["etimologia"] = re.sub(r'\s+', ' ', texto_limpo)
            else:
                dados["etimologia"] = "Não encontrado"
        else:
            dados["etimologia"] = "Não encontrado"

        # 🔹 Características (Refinado: Apenas texto dentro da tag <p>)
        sec_carac = soup.find("h2", id="caracteristicas")
        if sec_carac:
            div_carac = sec_carac.find_next("div", class_="level2")
            if div_carac:
                # Pega APENAS o primeiro parágrafo. Ignora players de áudio e botões subsequentes.
                paragrafo = div_carac.find("p")
                
                if paragrafo:
                    # separator=" " garante que tags <br> virem espaços simples (v0.4.9)
                    texto_raw = paragrafo.get_text(separator=" ", strip=True)
                    # Regex para remover múltiplas quebras de linha e espaços extras
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

        # 🔹 Taxonomia: Ordem e Família (v1.6.3 - Refinado via Auditoria Browser)
        # O WikiAves atual organiza a taxonomia em uma tabela dentro de containers m-portlet
        dados["ordem"] = "Desconhecida"
        dados["familia"] = "Desconhecida"
        
        # Estratégia Robusta: Localizar o TD que contém o texto e pegar o próximo TD (que contém o link)
        todas_as_celulas = soup.find_all("td")
        for i, td in enumerate(todas_as_celulas):
            texto_celula = td.get_text(strip=True)
            if "Ordem:" in texto_celula and i + 1 < len(todas_as_celulas):
                valor_celula = todas_as_celulas[i+1].get_text(strip=True)
                dados["ordem"] = valor_celula
            elif "Família:" in texto_celula and i + 1 < len(todas_as_celulas):
                valor_celula = todas_as_celulas[i+1].get_text(strip=True)
                dados["familia"] = valor_celula

        return dados

    # ==================================================
    # UTILITÁRIOS
    # ==================================================

    def _espera_humana(self):
        time.sleep(random.uniform(2, 4))

    def _aceitar_consentimento_google(self):
        try:
            if "consent" in self.driver.current_url:
                botoes = self.driver.find_elements(By.TAG_NAME, "button")
                for b in botoes:
                    if "aceitar" in b.text.lower() or "accept" in b.text.lower():
                        b.click()
                        time.sleep(2)
                        break
        except:
            pass

    def fechar(self):
        self.driver.quit()
