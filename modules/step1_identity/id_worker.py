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
import logging
import threading
from PySide6.QtCore import QThread, Signal
import requests
import base64
from core.config import carregar_config

try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        # Fallback/Mock para ambiente de desenvolvimento se TFLite não instalar
        tflite = None

from core.model_manager import ModelManager
from modules.step1_identity.bioclip import TAMANHO_ENTRADA, ClassificadorBioclip
from modules.step1_identity.preprocessamento import jpeg_para_nuvem, preparar_para_modelo

# Classificador (BioCLIP em LiteRT) em cache: carregar custa alguns segundos. O interpretador não é
# thread-safe: um worker substituído (troca de foto) pode continuar rodando enquanto o novo começa,
# então criação e inferência passam pela trava.
_classificador_cache = None
_interpreter_lock = threading.Lock()
MODELO_IA = "BioCLIP (Local)"


def carregar_classificador(progresso=None):
    """
    O ClassificadorBioclip em cache; na primeira vez baixa o modelo se faltar (quem roda pelo ZIP;
    o instalador já o traz). None se o download falhar.
    """
    global _classificador_cache
    with _interpreter_lock:
        if _classificador_cache is None:
            manager = ModelManager()
            if not manager.check_resources():
                if progresso:
                    progresso("Baixando o modelo de IA (~90 MB, só na 1ª vez)...")
                if not manager.download_resources(callback=progresso):
                    return None
            if progresso:
                progresso("Carregando cérebro digital...")
            _classificador_cache = ClassificadorBioclip(manager.bioclip_dir, tflite.Interpreter)
        return _classificador_cache

def formatar_rotulo(rotulo):  # rótulos do MobileNetV2 (referência da avaliação)
    """'Haemorhous cassinii (Cassin's Finch)' -> 'Haemorhous cassinii' (subespécie cai para a espécie)."""
    partes = rotulo.split('(')[0].strip().split()
    return f"{partes[0].capitalize()} {partes[1].lower()}" if len(partes) >= 2 else " ".join(partes).capitalize()


def foto_no_brasil(lat, lon):
    """True/False se as coordenadas caem nos biomas brasileiros (IBGE); None se não houver coordenadas."""
    if lat is None or lon is None:
        return None
    from modules.step3_geography.geo_analyst import GeoAnalyst
    bioma = GeoAnalyst().get_biome(lat, lon)
    if bioma == "Dados de Bioma não carregados":
        return None
    return bioma != "Fora de área mapeada"


def usar_prior_brasil(lat, lon, sem_gps_brasil=True):
    """
    True se a IA local deve considerar só as aves com registro no Brasil: foto com GPS no Brasil,
    ou foto sem GPS quando ``sem_gps_brasil`` (opção "ia_sem_gps_brasil" do config.json, padrão
    ligada). Foto com GPS fora do Brasil usa todas as ~11 mil espécies do catálogo.
    """
    no_brasil = foto_no_brasil(lat, lon)
    return sem_gps_brasil if no_brasil is None else no_brasil


def ranking_por_especie(rotulos, saida, permitidas=None):
    """
    Só para o MobileNetV2 (referência da avaliação, até a v1.4).
    [(espécie, confiança)] em ordem decrescente: a maior saída de cada espécie (rótulos de
    subespécie caem na espécie). Com ``permitidas`` (gênero + espécie em minúsculas), só essas
    entram e as confianças são renormalizadas para somar 1 entre elas. Em 14/11/2026 (200 fotos
    do iNaturalist de espécies conhecidas pelo modelo), isso subiu o top-1 de 48,0% para 59,0%
    (22 x 0 fotos discordantes; tools/avaliar_identificacao.py, modo "brasil").
    """
    por_especie = {}
    for rotulo, valor in zip(rotulos, saida):
        if permitidas is not None and rotulo.lower() not in permitidas:
            continue
        por_especie[rotulo] = max(por_especie.get(rotulo, 0.0), float(valor))
    if permitidas is not None:
        total = sum(por_especie.values())
        if total > 0:
            por_especie = {nome: valor / total for nome, valor in por_especie.items()}
    return sorted(por_especie.items(), key=lambda item: item[1], reverse=True)


# A IA local não decide sozinha quando há nuvem configurada: na amostra geral de 14/11/2026
# (300 fotos do iNaturalist no Brasil), o BioCLIP acertou 46,7% e, mesmo com confiança >= 0,95,
# 85% (abaixo dos 90% pedidos). Sem nuvem, abaixo deste piso a identificação é inconclusiva;
# acima, vira uma sugestão para a pessoa conferir.
LIMIAR_SUGESTAO = 0.30

class LocalIdentificationWorker(QThread):
    """
    Motor de Identificação Local (Etapa 1).
    Modelo: BioCLIP (imageomics/bioclip, licença MIT) em LiteRT INT8 dinâmico, sem treino para o
    iBirder (zero-shot): compara a foto com o texto de cada espécie (modules/step1_identity/bioclip.py).
    Candidatas: as ~1.760 aves do Brasil ou, com GPS fora do país, as ~11 mil do catálogo.
    Com nuvem configurada (iNaturalist e/ou Google Vision), a nuvem é sempre consultada; sem ela,
    o resultado local é uma sugestão a conferir (ou inconclusivo abaixo de ``LIMIAR_SUGESTAO``).
    Gerencia:
    1. Download do modelo se ausente (ModelManager; normalmente já vem no instalador).
    2. Pré-processamento (orientação EXIF, redução e foto inteira esticada para 224x224).
    3. Inferência local, sem internet (~0,1 s por foto).
    """
    progress_updated = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._stopped = False
        # Coordenadas da foto (definidas pelo orquestrador) para o prior Brasil
        self.lat = None
        self.lon = None

    def run(self):
        if not tflite:
            self.error.emit("TFLite Runtime não está instalado. Reinicie o app.")
            return

        try:
            self.progress_updated.emit("Verificando Inteligência Artificial...")
            classificador = carregar_classificador(self._emit_download_progress)
            if classificador is None:
                self.error.emit("Falha ao baixar o modelo de IA. Confira a internet e tente de novo.")
                return
            if self._stopped:
                return

            # Pré-processamento (preprocessamento.py): abre já reduzida, sem alterar o arquivo,
            # e estica a foto inteira para 224x224, sem recorte
            self.progress_updated.emit("Analisando imagem...")
            entrada = classificador.preparar(
                preparar_para_modelo(self.image_path, TAMANHO_ENTRADA, TAMANHO_ENTRADA))

            # Inferência sob a trava (o interpretador LiteRT não é thread-safe)
            with _interpreter_lock:
                inicio = time.time()
                emb = classificador.embedding(entrada)
            logging.debug(f"Inferência local (BioCLIP) em {(time.time() - inicio) * 1000:.0f} ms.")

            # Candidatas: aves do Brasil para fotos daqui (ou sem GPS, pela opção do config.json);
            # todas as espécies do catálogo para fotos com GPS fora do Brasil
            config = carregar_config()
            so_brasil = usar_prior_brasil(self.lat, self.lon, bool(config.get("ia_sem_gps_brasil", True)))
            ranking = classificador.ranking(emb, so_brasil=so_brasil)
            top3_results = [{"nome_cientifico": nome, "confianca": conf} for nome, conf in ranking[:3]]
            confidence = top3_results[0]["confianca"] if top3_results else 0.0
            logging.info(f"IA local: {top3_results[0]['nome_cientifico'] if top3_results else '-'} "
                         f"({confidence*100:.1f}%) entre {'as aves do Brasil' if so_brasil else 'todas as espécies'}.")

            # Com nuvem configurada, ela sempre decide (a confiança local não basta para dispensá-la)
            if self._nuvem_configurada(config):
                resultado_nuvem = self._consultar_nuvem("Confirmando a espécie")
                if resultado_nuvem:
                    self.finished.emit(resultado_nuvem)
                    return

            if confidence < LIMIAR_SUGESTAO:
                logging.warning("Sem nuvem e com confiança local baixa. Retornando identificação Inconclusiva.")
                self.finished.emit({
                    "nome_cientifico": "Identificação Inconclusiva",
                    "nome_comum": "",
                    "descricao": "A foto pode estar pouco nítida ou a ave está muito distante.",
                    "confianca": confidence,
                    "top3": top3_results,
                    "status_msg": "Baixa confiança"
                })
                return

            self.finished.emit({
                "nome_cientifico": top3_results[0]["nome_cientifico"],
                "nome_comum": "",
                "descricao": "Sugestão da IA local (BioCLIP), sem confirmação da nuvem.",
                "confianca": confidence,
                "top3": top3_results,
                "modelo_ia": MODELO_IA,
                "status_msg": "Sugestão local",
                "aviso_sugestao": ("Sugestão da IA local, sem confirmação da nuvem: confira a espécie "
                                   "(a IA local acerta cerca de metade das fotos)."),
            })

        except Exception as e:
            logging.error("Erro fatal na análise de imagem:", exc_info=True)
            self.error.emit(f"Erro na análise: {str(e)}")

    @staticmethod
    def _nuvem_configurada(config):
        """True se há token do iNaturalist ou chave do Google Vision no config.json."""
        from core.diagnostico_apis import normalizar_token_inat
        return bool(normalizar_token_inat(config.get("inat_api_token", ""))
                    or config.get("google_vision_api_key", "").strip())

    def _consultar_nuvem(self, motivo):
        """Cascata de nuvem (iNaturalist e depois Google Vision) com as chaves do usuário."""
        config = carregar_config()
        from core.diagnostico_apis import normalizar_token_inat
        inat_token = normalizar_token_inat(config.get("inat_api_token", ""))
        google_key = config.get("google_vision_api_key", "").strip()

        if inat_token:
            self.progress_updated.emit(f"{motivo}. Consultando iNaturalist (Nuvem)...")
            try:
                resultado = self._call_inat_api(self.image_path, inat_token)
                if resultado:
                    logging.info(f"Sucesso iNaturalist: {resultado['nome_cientifico']} ({resultado['confianca']*100:.1f}%)")
                    return resultado
                logging.warning("iNaturalist não obteve resultado conclusivo ou ocorreu um erro de conexão.")
            except Exception as e:
                logging.error(f"Erro iNaturalist API (Exception): {e}")
        else:
            logging.info("Token iNaturalist ausente. Pulando primeira nuvem.")

        if google_key:
            self.progress_updated.emit("Consultando Google Cloud Vision...")
            try:
                resultado = self._call_google_vision(self.image_path, google_key)
                if resultado:
                    logging.info(f"Sucesso Google Vision: {resultado['nome_cientifico']}")
                    return resultado
                logging.warning("Google Vision não obteve resultado conclusivo.")
            except Exception as e:
                logging.error(f"Erro Google Vision API (Exception): {e}")
        else:
            logging.info("Chave Google Vision ausente. Pulando segunda nuvem.")
        return None

    def _emit_download_progress(self, msg):
        if not self._stopped:
            self.progress_updated.emit(msg)

    def stop(self):
        self._stopped = True

    def _call_inat_api(self, image_path, token):
        url = "https://api.inaturalist.org/v1/computervision/score_image"
        headers = {"Authorization": f"Bearer {token}"}

        import io

        # Cópia reduzida (lado maior 1024 px, JPEG 85) para não estourar o limite da API (413)
        files = {"image": ("image.jpg", io.BytesIO(jpeg_para_nuvem(image_path)), "image/jpeg")}
        response = requests.post(url, headers=headers, files=files, timeout=15)

        if response.status_code == 200:
            return interpretar_resposta_inat(response.json())
        logging.error(f"Erro iNaturalist API ({response.status_code}): {response.text[:200]}")
        return None

    def _call_google_vision(self, image_path, api_key):
        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

        base64_img = base64.b64encode(jpeg_para_nuvem(image_path)).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": base64_img},
                "features": [
                    {"type": "WEB_DETECTION", "maxResults": 10},
                    {"type": "LABEL_DETECTION", "maxResults": 10}
                ]
            }]
        }

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return interpretar_resposta_google(response.json())
        logging.error(f"Erro Google Vision API ({response.status_code}): {response.text[:200]}")
        return None


# --- Respostas da nuvem (funções puras, testadas em tests/test_cascata_nuvem.py) ---

# O Google Vision não devolve probabilidade de espécie: valor fixo, como antes da v1.4
CONFIANCA_GOOGLE = 0.85


def interpretar_resposta_inat(data):
    """
    Resultado da etapa 1 a partir da resposta do score_image do iNaturalist, ou None.
    Só aceita espécie (ou subespécie, reduzida à espécie) de ave: táxon com
    iconic_taxon_name "Aves" ou presente no catálogo eBird embarcado. O top-3 é o real,
    com o vision_score de cada resultado.
    """
    from core.catalogo_especies import resolver_nome
    candidatos = []
    for resultado in (data or {}).get("results", []):
        taxon = resultado.get("taxon") or {}
        nome = (taxon.get("name") or "").strip()
        if len(nome.split()) < 2:
            continue  # gênero, família...: não é espécie
        canonico = resolver_nome(nome)
        if not canonico:
            if taxon.get("iconic_taxon_name") != "Aves":
                logging.debug(f"iNaturalist: '{nome}' descartado (não é ave do catálogo).")
                continue
            partes = nome.split()
            canonico = f"{partes[0].capitalize()} {partes[1].lower()}"
        if any(c["nome_cientifico"] == canonico for c in candidatos):
            continue  # subespécies da mesma espécie
        candidatos.append({"nome_cientifico": canonico,
                           "confianca": float(resultado.get("vision_score", 0)) / 100.0})
    if not candidatos:
        return None
    return {
        "nome_cientifico": candidatos[0]["nome_cientifico"],
        "nome_comum": "",
        "descricao": "Identificado na nuvem (iNaturalist API).",
        "confianca": candidatos[0]["confianca"],
        "top3": candidatos[:3],
        "modelo_ia": "iNaturalist API (Nuvem)"
    }


def interpretar_resposta_google(data):
    """
    Resultado da etapa 1 a partir da resposta do Google Vision, ou None.
    Percorre as entidades web e depois os rótulos e só aceita o que o catálogo eBird
    reconhece como espécie de ave (nome científico ou nome em inglês). Rótulos genéricos
    como "Bird" ou "Beak" são descartados.
    """
    from core.catalogo_especies import resolver_nome
    resposta = ((data or {}).get("responses") or [{}])[0]
    textos = [e.get("description", "") for e in resposta.get("webDetection", {}).get("webEntities", [])]
    textos += [r.get("description", "") for r in resposta.get("labelAnnotations", [])]
    nomes = []
    for texto in textos:
        nome = resolver_nome(texto)
        if nome and nome not in nomes:
            nomes.append(nome)
    if not nomes:
        logging.info(f"Google Vision sem espécie reconhecível: {', '.join(t for t in textos if t)[:200]}")
        return None
    return {
        "nome_cientifico": nomes[0],
        "nome_comum": "",
        "descricao": "Identificado na nuvem (Google Vision).",
        "confianca": CONFIANCA_GOOGLE,
        "top3": [{"nome_cientifico": n, "confianca": CONFIANCA_GOOGLE} for n in nomes[:3]],
        "modelo_ia": "Google Vision API (Nuvem)"
    }
