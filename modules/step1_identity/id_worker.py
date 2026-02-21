import sys
import numpy as np
import time
from PySide6.QtCore import QThread, Signal
from PIL import Image

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    # Fallback/Mock para ambiente de desenvolvimento se TFLite não instalar
    tflite = None

from core.model_manager import ModelManager

# Global Cache for TFLite Interpreter
_interpreter_cache = None

class LocalIdentificationWorker(QThread):
    progress_updated = Signal(str)
    identification_complete = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._stopped = False
        self.min_confidence = 0.70 # 70% threshold

    def run(self):
        global _interpreter_cache
        if not tflite:
             self.error_occurred.emit("TFLite Runtime não está instalado. Reinicie o app.")
             return

        try:
            # 1. Verificar Recursos
            self.progress_updated.emit("Verificando Inteligência Artificial...")
            manager = ModelManager()
            
            if not manager.check_resources():
                self.progress_updated.emit("Baixando modelo IA (apenas na 1ª vez)...")
                sucesso = manager.download_resources(callback=self._emit_download_progress)
                if not sucesso:
                    self.error_occurred.emit("Falha ao baixar modelo de IA.")
                    return

            if self._stopped:
                return

            # 2. Carregar Modelo (Cache Global)
            start_time = time.time()
            if _interpreter_cache is None:
                self.progress_updated.emit("Carregando cérebro digital...")
                _interpreter_cache = tflite.Interpreter(model_path=str(manager.model_path))
                _interpreter_cache.allocate_tensors()
            
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

            # Add batch dimension
            input_data = np.expand_dims(img_array, axis=0)

            # Inferência
            start_infer_time = time.time()
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            infer_ms = (time.time() - start_infer_time) * 1000
            print(f"[IA TELEMETRY] Inferência local (iNaturalist Vision) bem-sucedida em {infer_ms:.2f}ms.")

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
                    "nome_comum": "Não foi possível identificar com segurança",
                    "descricao": "A foto pode estar pouco nítida ou a ave está muito distante.",
                    "confianca": float(confidence),
                    "status_msg": "Baixa confiança"
                 }
                 self.identification_complete.emit(resultado)
                 return

            # Carregar Labels
            labels = self._load_labels(manager.labels_path)
            print(f'[IA] Labels carregados: {len(labels)}')
            
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
                    "nome_comum": "Analisando...", 
                    "descricao": "Identificado localmente (iNaturalist Vision).",
                    "confianca": float(confidence),
                    "top3": top3_results
                }
                
                self.identification_complete.emit(resultado)
            except IndexError:
                self.error_occurred.emit(f"Erro: Índice {idx} fora dos limites ({len(labels)}).")

        except Exception as e:
            print("-" * 50)
            print("[ERRO FATAL] Detalhes da falha no download/inferência:")
            import traceback
            traceback.print_exc()
            print("-" * 50)
            self.error_occurred.emit(f"Erro na análise: {str(e)}")

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
            print(f"[IA] Erro ao ler labels: {e}")
            
        return labels

    def stop(self):
        self._stopped = True
