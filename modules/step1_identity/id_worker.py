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
from PySide6.QtCore import QThread, Signal
import numpy as np
from PIL import Image
import requests
import base64
import json
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

# Global Cache for TFLite Interpreter
_interpreter_cache = None

def get_current_interpreter():
    global _interpreter_cache
    return _interpreter_cache

def free_interpreter_cache():
    """Gatilho dinâmico invocado pelo Orchestrator pós Hot-Swap para resetar o Cérebro."""
    global _interpreter_cache
    _interpreter_cache = None
    logging.debug("Cache do Interpretador limpo para recarga OTA.")

class LocalIdentificationWorker(QThread):
    """
    Motor de Identificação Local (Etapa 1).
    Realiza a inferência de IA usando modelos TFLite treinados na base do iNaturalist.
    Gerencia:
    1. Download e cache automático de modelos (ModelManager).
    2. Pré-processamento de imagem (Resize, Normalização).
    3. Inferência local sem necessidade de internet pós-download.
    4. Rollback automático em caso de corrupção do modelo recebido via OTA.
    """
    progress_updated = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._stopped = False
        self.min_confidence = 0.70 # 70% threshold

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
            start_time = time.time()
            if _interpreter_cache is None:
                self.progress_updated.emit("Carregando cérebro digital...")
                _interpreter_cache = tflite.Interpreter(model_path=str(manager.model_path))
                _interpreter_cache.allocate_tensors()
                
                # O teste de alocação de tensores já foi feito no allocate_tensors() acima. 
                # Qualquer falha ali será capturada pelo except Exception.
            
            interpreter = _interpreter_cache

            # Get input and output tensors.
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            # 3. Processar Imagem
            self.progress_updated.emit("Analisando imagem...")
            
            # Check expected shape
            height = input_details[0]['shape'][1]
            width = input_details[0]['shape'][2]
            
            # 3. Pré-processamento
            # Carrega imagem original em memória (sem alterar arquivo)
            img = Image.open(self.image_path).convert('RGB')
            
            # Redimensionamento de Alta Qualidade (LANCZOS)
            # Crucial para manter detalhes de plumagem e bico ao reduzir para 224x224
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Check input type
            input_type = input_details[0]['dtype']
            img_array = np.array(img_resized, dtype=input_type) # Use img_resized here
            
            # Normalization
            if input_type == np.float32:
                 # Normalização padrão se for float (-1 a 1)
                 img_array = (np.float32(img_array) - 127.5) / 127.5

            # Adiciona dimensão de batch (Exemplo: [1, 224, 224, 3])
            input_data = np.expand_dims(img_array, axis=0)

            # 4. Inferência Assistida (Fase C: Robusta contra falhas de atualização)
            try:
                start_infer_time = time.time()
                interpreter.set_tensor(input_details[0]['index'], input_data)
                interpreter.invoke()
                infer_ms = (time.time() - start_infer_time) * 1000
                logging.debug(f"Inferência local (iNaturalist Vision) bem-sucedida em {infer_ms:.2f}ms.")
            except Exception as invoke_err:
                logging.critical(f"Falha crítica de inferência: {invoke_err}.")
                import shutil, os
                backup_dir = manager.assets_dir.parent / "models_back"
                if backup_dir.exists():
                    logging.warning("Modelo incompatível ou corrompido detectado. Revertendo para cópia de segurança...")
                    shutil.rmtree(manager.assets_dir)
                    os.rename(backup_dir, manager.assets_dir)
                    free_interpreter_cache()
                    self.error.emit("Falha ao usar a nova Inteligência. O aplicativo retornou automaticamente para a Versão Estável anterior.")
                    return
                else:
                    raise invoke_err

            # Interpretar Resultados (Classificação)
            output_data = interpreter.get_tensor(output_details[0]['index'])
            results = np.squeeze(output_data)
            
            if output_details[0]['dtype'] == np.uint8:
                 results = results / 255.0
            
            # Pegar Top-3
            top_k = results.argsort()[-3:][::-1]
            idx = top_k[0]
            confidence = float(results[idx])

            if confidence < self.min_confidence:
                 logging.info(f"Confiança local ({confidence*100:.1f}%) abaixo de {self.min_confidence*100:.0f}%. Iniciando cascata de IA (Nuvem).")
                 
                 # Fallback API (v1.1)
                 config = carregar_config()
                 inat_token = config.get("inat_api_token", "").strip()
                 google_key = config.get("google_vision_api_key", "").strip()
                 
                 # 1. Tenta iNaturalist API
                 if inat_token:
                     self.progress_updated.emit("Confiança local baixa. Consultando iNaturalist (Nuvem)...")
                     logging.info("Consultando iNaturalist Vision API...")
                     try:
                         inat_result = self._call_inat_api(self.image_path, inat_token)
                         if inat_result:
                             logging.info(f"Sucesso iNaturalist: {inat_result['nome_cientifico']} ({inat_result['confianca']*100:.1f}%)")
                             self.finished.emit(inat_result)
                             return
                         else:
                             logging.warning("iNaturalist não obteve resultado conclusivo ou ocorreu um erro de conexão.")
                     except Exception as e:
                         logging.error(f"Erro iNaturalist API (Exception): {e}")
                 else:
                     logging.info("Token iNaturalist ausente. Pulando primeira nuvem.")
                 
                 # 2. Tenta Google Vision API
                 if google_key:
                     self.progress_updated.emit("Consultando Google Cloud Vision...")
                     logging.info("Consultando Google Cloud Vision API...")
                     try:
                         gvis_result = self._call_google_vision(self.image_path, google_key)
                         if gvis_result:
                             logging.info(f"Sucesso Google Vision: {gvis_result['nome_cientifico']}")
                             self.finished.emit(gvis_result)
                             return
                         else:
                             logging.warning("Google Vision não obteve resultado conclusivo.")
                     except Exception as e:
                         logging.error(f"Erro Google Vision API (Exception): {e}")
                 else:
                     logging.info("Chave Google Vision ausente. Pulando segunda nuvem.")

                 # Se falhou tudo ou não tem chaves, retorna inconclusivo
                 logging.warning("Cascata esgotada. Retornando identificação Inconclusiva ao usuário.")
                 resultado = {
                    "nome_cientifico": "Identificação Inconclusiva",
                    "nome_comum": "",
                    "descricao": "A foto pode estar pouco nítida ou a ave está muito distante.",
                    "confianca": float(confidence),
                    "status_msg": "Baixa confiança"
                 }
                 self.finished.emit(resultado)
                 return

            # Carregar Labels
            labels = self._load_labels(manager.labels_path)
            logging.debug(f'Labels carregados: {len(labels)}')
            
            try:
                # Top-3 Format
                top3_results = []
                for i in top_k:
                    raw_label_i = labels[i]
                    clean_name_i = raw_label_i.split('(')[0].strip()
                    parts_i = clean_name_i.split()
                    if len(parts_i) >= 2:
                        label_name_i = f"{parts_i[0].capitalize()} {parts_i[1].lower()}"
                    else:
                        label_name_i = clean_name_i.capitalize()
                    top3_results.append({"nome_cientifico": label_name_i, "confianca": float(results[i])})
                
                # Resultado
                resultado = {
                    "nome_cientifico": top3_results[0]["nome_cientifico"],
                    "nome_comum": "", 
                    "descricao": "Identificado localmente (iNaturalist Vision).",
                    "confianca": float(confidence),
                    "top3": top3_results
                }
                
                self.finished.emit(resultado)
            except IndexError:
                self.error.emit(f"Erro: Índice {idx} fora dos limites ({len(labels)}).")

        except Exception as e:
            logging.error("Erro fatal na análise de imagem:", exc_info=True)
            self.error.emit(f"Erro na análise: {str(e)}")

    def _emit_download_progress(self, msg):
        if not self._stopped:
            self.progress_updated.emit(msg)

    def _load_labels(self, path):
        """Lê o TXT de labels (suporta formato 'id,nome' ou apenas 'nome')."""
        labels = []
        # Background class is handled by the model logic/mapping usually.
        # EfficientNet V1.3 often matches lines to IDs directly (0-indexed or 1-indexed depending on training).
        # We will load lines as is, but stripping ID headers if present.
        
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
        headers = {"Authorization": token if token.startswith("Bearer") else f"Bearer {token}"}
        
        import io
        from PIL import Image
        
        # Comprime a imagem em memória para não estourar limite da API (ex: 413 Entity Too Large)
        img = Image.open(image_path).convert('RGB')
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)
        img_bytes.seek(0)
        
        files = {"image": ("image.jpg", img_bytes, "image/jpeg")}
        response = requests.post(url, headers=headers, files=files, timeout=15)
            
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                best_match = data["results"][0]
                taxon = best_match.get("taxon", {})
                nome_cientifico = taxon.get("name", "")
                
                # Se achou algo válido e é um nome científico (duas palavras)
                if nome_cientifico and len(nome_cientifico.split()) >= 2:
                    return {
                        "nome_cientifico": nome_cientifico.capitalize(),
                        "nome_comum": "",
                        "descricao": "Identificado na nuvem (iNaturalist API).",
                        "confianca": float(best_match.get("vision_score", 0)) / 100.0,
                        "top3": [{"nome_cientifico": nome_cientifico.capitalize(), "confianca": 0.99}]
                    }
        else:
            logging.error(f"Erro iNaturalist API ({response.status_code}): {response.text[:200]}")
        return None

    def _call_google_vision(self, image_path, api_key):
        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        
        import io
        from PIL import Image
        img = Image.open(image_path).convert('RGB')
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)
        base64_img = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            
        payload = {
            "requests": [{
                "image": {"content": base64_img},
                "features": [
                    {"type": "WEB_DETECTION", "maxResults": 3},
                    {"type": "LABEL_DETECTION", "maxResults": 5}
                ]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            responses = data.get("responses", [{}])[0]
            
            best_name = None
            # Prioriza Web Detection entities que parecem nomes científicos
            web_entities = responses.get("webDetection", {}).get("webEntities", [])
            for entity in web_entities:
                desc = entity.get("description", "")
                if desc and len(desc.split()) == 2:
                    best_name = desc
                    break
            
            # Se não achou na Web Detection, pega a primeira Label
            if not best_name:
                labels = responses.get("labelAnnotations", [])
                if labels:
                    best_name = labels[0].get("description", "")
            
            if best_name:
                return {
                    "nome_cientifico": best_name.capitalize(),
                    "nome_comum": "",
                    "descricao": "Identificado na nuvem (Google Vision).",
                    "confianca": 0.85, # Valor estático alto já que é o último fallback
                    "top3": [{"nome_cientifico": best_name.capitalize(), "confianca": 0.85}]
                }
        else:
            logging.error(f"Erro Google Vision API ({response.status_code}): {response.text[:200]}")
        return None
