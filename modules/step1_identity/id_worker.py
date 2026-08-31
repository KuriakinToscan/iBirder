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
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None

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
            # Carrega imagem original em memória e aplica rotação EXIF se houver
            img = Image.open(self.image_path).convert('RGB')
            img = ImageOps.exif_transpose(img)
            
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
                 # Em vez de erro, retornamos um resultado "Inconclusivo" para a UI tratar
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
