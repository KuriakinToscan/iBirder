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
import numpy as np
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
from modules.step1_identity.preprocessamento import jpeg_para_nuvem, preparar_para_modelo

# Interpretador LiteRT em cache (carregar custa alguns segundos). Não é thread-safe: um worker
# substituído (troca de foto) pode continuar rodando enquanto o novo começa, então criação e
# inferência passam pela trava.
_interpreter_cache = None
_interpreter_lock = threading.Lock()

def formatar_rotulo(rotulo):
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


def avaliar_ocorrencia(top3, lat, lon):
    """
    (fora_da_area, alternativas): fora_da_area é True quando a foto é do Brasil e a espécie
    sugerida não tem registro no país; alternativas são os outros candidatos do top-3 que têm.
    Sem coordenadas, nada é afirmado.
    """
    if not top3 or not foto_no_brasil(lat, lon):
        return False, []
    from modules.step3_geography import listas_conservacao as listas
    if listas.total_registradas_brasil() == 0 or listas.registrada_no_brasil(top3[0]["nome_cientifico"]):
        return False, []
    alternativas = [c for c in top3[1:] if listas.registrada_no_brasil(c["nome_cientifico"])]
    return True, alternativas


def get_current_interpreter():
    return _interpreter_cache

class LocalIdentificationWorker(QThread):
    """
    Motor de Identificação Local (Etapa 1).
    Modelo: Google AIY Vision "Birds V1" (MobileNetV2 quantizado, TFLite), treinado com fotos
    do iNaturalist; 965 espécies do mundo todo (cerca de 230 ocorrem no Brasil).
    Abaixo de 70% de confiança, consulta a nuvem (iNaturalist e/ou Google Vision) se houver chave.
    Gerencia:
    1. Download do modelo se ausente (ModelManager; normalmente já vem no instalador).
    2. Pré-processamento (orientação EXIF, redução com a proporção preservada e borda até 224x224).
    3. Inferência local, sem internet.
    """
    progress_updated = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._stopped = False
        self.min_confidence = 0.70 # 70% threshold
        # Coordenadas da foto (definidas pelo orquestrador) para a checagem de ocorrência
        self.lat = None
        self.lon = None

    def run(self):
        global _interpreter_cache
        if not tflite:
             self.error.emit("TFLite Runtime não está instalado. Reinicie o app.")
             return

        try:
            # 1. Verificar Recursos
            self.progress_updated.emit("Verificando Inteligência Artificial...")
            manager = ModelManager()
            
            if not manager.check_resources():
                self.progress_updated.emit("Baixando modelo IA (apenas na 1ª vez)...")
                sucesso = manager.download_resources(callback=self._emit_download_progress)
                if not sucesso:
                    self.error.emit("Falha ao baixar modelo de IA.")
                    return

            if self._stopped:
                return

            # 2. Carregar Modelo (Instanciação do Interpretador com Cache Global)
            # O interpretador é mantido em memória (cache) para evitar o custo de carregamento 
            # de 4-6 segundos em cada nova identificação.
            with _interpreter_lock:
                if _interpreter_cache is None:
                    self.progress_updated.emit("Carregando cérebro digital...")
                    interpretador = tflite.Interpreter(model_path=str(manager.model_path))
                    interpretador.allocate_tensors()  # falha aqui cai no except geral
                    _interpreter_cache = interpretador
                interpreter = _interpreter_cache

            # Get input and output tensors.
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            # 3. Processar Imagem
            self.progress_updated.emit("Analisando imagem...")
            
            # Check expected shape
            height = input_details[0]['shape'][1]
            width = input_details[0]['shape'][2]
            
            # 3. Pré-processamento (preprocessamento.py): abre já reduzida, sem alterar o arquivo,
            # e leva o lado maior a 224 px com borda neutra, sem deformar a ave
            img_resized = preparar_para_modelo(self.image_path, width, height)
            
            # Check input type
            input_type = input_details[0]['dtype']
            img_array = np.array(img_resized, dtype=input_type) # Use img_resized here
            
            # Normalization
            if input_type == np.float32:
                 # Normalização padrão se for float (-1 a 1)
                 img_array = (np.float32(img_array) - 127.5) / 127.5

            # Adiciona dimensão de batch (Exemplo: [1, 224, 224, 3])
            input_data = np.expand_dims(img_array, axis=0)

            # 4. Inferência (set_tensor, invoke e get_tensor sob a mesma trava)
            with _interpreter_lock:
                start_infer_time = time.time()
                interpreter.set_tensor(input_details[0]['index'], input_data)
                interpreter.invoke()
                output_data = interpreter.get_tensor(output_details[0]['index'])
            infer_ms = (time.time() - start_infer_time) * 1000
            logging.debug(f"Inferência local bem-sucedida em {infer_ms:.2f}ms.")

            # Interpretar Resultados (Classificação)
            results = np.squeeze(output_data)
            
            if output_details[0]['dtype'] == np.uint8:
                 results = results / 255.0
            
            # Top-3 com nomes (rótulos na mesma ordem das saídas do modelo)
            top_k = results.argsort()[-3:][::-1]
            confidence = float(results[top_k[0]])
            labels = self._load_labels(manager.labels_path)
            if len(labels) <= int(top_k[0]):
                self.error.emit(f"Erro: Índice {top_k[0]} fora dos limites ({len(labels)}).")
                return
            top3_results = [{"nome_cientifico": formatar_rotulo(labels[i]), "confianca": float(results[i])}
                            for i in top_k]

            # Plausibilidade regional: a IA local conhece só ~230 das ~1.760 aves com registro no
            # Brasil e pode sugerir, com alta confiança, uma espécie que nunca ocorreu aqui.
            fora_da_area, alternativas = avaliar_ocorrencia(top3_results, self.lat, self.lon)

            if confidence < self.min_confidence or fora_da_area:
                if fora_da_area:
                    motivo = "Espécie sugerida sem registro no Brasil"
                    logging.info(f"{top3_results[0]['nome_cientifico']} ({confidence*100:.1f}%) sem registro no Brasil. "
                                 "Consultando a nuvem.")
                else:
                    motivo = "Confiança local baixa"
                    logging.info(f"Confiança local ({confidence*100:.1f}%) abaixo de {self.min_confidence*100:.0f}%. "
                                 "Iniciando cascata de IA (Nuvem).")
                resultado_nuvem = self._consultar_nuvem(motivo)
                if resultado_nuvem:
                    self.finished.emit(resultado_nuvem)
                    return

                if not fora_da_area:
                    # Se falhou tudo ou não tem chaves, retorna inconclusivo
                    logging.warning("Cascata esgotada. Retornando identificação Inconclusiva ao usuário.")
                    self.finished.emit({
                        "nome_cientifico": "Identificação Inconclusiva",
                        "nome_comum": "",
                        "descricao": "A foto pode estar pouco nítida ou a ave está muito distante.",
                        "confianca": confidence,
                        "top3": top3_results,
                        "status_msg": "Baixa confiança"
                    })
                    return

            resultado = {
                "nome_cientifico": top3_results[0]["nome_cientifico"],
                "nome_comum": "",
                "descricao": "Identificado localmente (iNaturalist Vision).",
                "confianca": confidence,
                "top3": top3_results,
                "modelo_ia": "MobileNetV2 (Local)"
            }
            if fora_da_area:
                # Sem nuvem disponível: mantém a sugestão, mas avisa e aponta alternativas plausíveis
                resultado["aviso_ocorrencia"] = (
                    f"{top3_results[0]['nome_cientifico']} não tem registro no Brasil (iNaturalist). "
                    "A IA local provavelmente não conhece esta ave: confira a identificação.")
                resultado["alternativas_brasil"] = alternativas
            self.finished.emit(resultado)

        except Exception as e:
            logging.error("Erro fatal na análise de imagem:", exc_info=True)
            self.error.emit(f"Erro na análise: {str(e)}")

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

    def _load_labels(self, path):
        """Lê o TXT de labels (suporta formato 'id,nome' ou apenas 'nome')."""
        labels = []
        # Uma linha por classe, na mesma ordem das 965 saídas do modelo (sem classe "background").
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Se tiver virgula (ex: 0,Passer domesticus), pega a parte do nome
                        name = line.split(',', 1)[1].strip() if ',' in line else line
                        labels.append(name)
        except Exception as e:
            logging.error(f"Erro ao ler labels: {e}")
            
        return labels

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
