import time
import random
import urllib.parse
import re
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

        print(f"\n🚀 Buscando: {scientific_name}")

        link = self._tentar_google(scientific_name)

        if not link:
            print("⚠ Google falhou. Tentando Bing...")
            link = self._tentar_bing(scientific_name)

        if link:
            print(f"✅ Link encontrado: {link}")
            return link
        else:
            print("❌ Nenhum link encontrado.")
            self.driver.save_screenshot("erro_tela.png")
            return None

    # ==================================================
    # GOOGLE
    # ==================================================

    def _tentar_google(self, term):

        try:
            query = f'site:wikiaves.com.br "{term}"'
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            print(f"🔎 Google: {url}")
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
            print("⏳ Google não retornou resultados válidos.")
            return None
        except Exception as e:
            print(f"Erro Google: {e}")
            return None

    # ==================================================
    # BING
    # ==================================================

    def _tentar_bing(self, term):

        try:
            query = f'site:wikiaves.com.br "{term}"'
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"

            print(f"🔎 Bing: {url}")
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
            print("⏳ Bing não retornou resultados válidos.")
            return None
        except Exception as e:
            print(f"Erro Bing: {e}")
            return None

    # ==================================================
    # EXTRAÇÃO DAS SEÇÕES ESPECÍFICAS
    # ==================================================

    def extrair_dados_especie(self, url):

        print(f"📖 Extraindo dados de: {url}")

        self.driver.get(url)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "h2"))
        )

        html = self.driver.page_source
        soup = BeautifulSoup(html, "lxml")

        dados = {}

        # 🔹 Nome Comum (Título Principal h1)
        # Refinado v0.8.4.3: IDs dinâmicos no WikiAves exigem busca por classe ou tag genérica
        tag_h1 = soup.find("h1", class_="sectionedit1") or soup.find("h1", id="titulo") or soup.find("h1")
        
        if tag_h1:
             # O .strip() no get_text previne espaços e quebras indesejadas
             dados["nome_comum"] = tag_h1.get_text(separator=" ", strip=True)
        else:
             dados["nome_comum"] = "Não encontrado"

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
        # 🔹 Nome em Inglês (v0.8.3)
        sec_ingles = soup.find("h2", string=lambda t: t and "Nome em Inglês" in t)
        if sec_ingles:
            # O nome em inglês costuma vir como um text node logo após o h2
            proximo = sec_ingles.next_sibling
            if proximo and isinstance(proximo, str):
                dados["nome_ingles"] = proximo.strip()
            elif sec_ingles.next_element:
                # Tenta pegar o próximo elemento se não for string direta
                texto_ingles = sec_ingles.find_next(string=True)
                if texto_ingles:
                    dados["nome_ingles"] = texto_ingles.strip()
                else:
                    dados["nome_ingles"] = "Não encontrado"
        # v0.8.4.2: Garantir que o link de origem seja persistido
        dados["link_origem"] = url

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
