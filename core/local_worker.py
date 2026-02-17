import sys
import numpy as np
import time
from PySide6.QtCore import QThread, Signal
from PIL import Image

try:
    import tensorflow as tf
except ImportError:
    # Fallback/Mock para ambiente de desenvolvimento se TF não instalar
    tf = None

from core.model_manager import ModelManager

class LocalIdentificationWorker(QThread):
    progress_updated = Signal(str)
    identification_complete = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self._stopped = False
        self.min_confidence = 0.50 # 50% threshold

    def run(self):
        if not tf:
             self.error_occurred.emit("TensorFlow não está instalado. Reinicie o app.")
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

            # 2. Carregar Modelo
            self.progress_updated.emit("Carregando cérebro digital...")
            start_time = time.time()
            
            # Load TFLite model and allocate tensors.
            interpreter = tf.lite.Interpreter(model_path=str(manager.model_path))
            interpreter.allocate_tensors()

            # Get input and output tensors.
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            # 3. Processar Imagem
            self.progress_updated.emit("Analisando imagem...")
            
            # Check expected shape
            height = input_details[0]['shape'][1]
            width = input_details[0]['shape'][2]
            
            img = Image.open(self.image_path).convert('RGB')
            img = img.resize((width, height))
            
            # Check input type (float vs int)
            input_type = input_details[0]['dtype']
            img_array = np.array(img, dtype=input_type)
            
            # Normalization
            if input_type == np.float32:
                # Standard normalization for MobileNet models: (img - 127.5) / 127.5
                img_array = (np.float32(img_array) - 127.5) / 127.5

            # Add batch dimension
            input_data = np.expand_dims(img_array, axis=0)

            # 4. Inferência
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()

            output_data = interpreter.get_tensor(output_details[0]['index'])
            results = np.squeeze(output_data)

            # 5. Interpretar Resultados
            top_k = results.argsort()[-1:][::-1] # Pegar o top 1
            idx = top_k[0]
            confidence = float(results[idx])
            
            # Se for uint8, desnormalizar confiança (0-255 -> 0.0-1.0)
            if output_details[0]['dtype'] == np.uint8:
                confidence = confidence / 255.0

            elapsed = time.time() - start_time
            print(f"[IA] Inferência local em {elapsed:.2f}s. Confiança: {confidence:.2f}")

            if confidence < self.min_confidence:
                 self.error_occurred.emit("Não foi possível identificar com certeza.")
                 return

            # Carregar Labels
            labels = self._load_labels(manager.labels_path)
            
            # Ajuste para Background Class (geralmente index 0 em modelos Object Detection, 
            # mas em classificação varia). 
            # O bird_V1_1.csv geralmente começa com id 0.
            
            if idx in labels:
                label_name = labels[idx]
                
                # Resultado
                resultado = {
                    "nome_cientifico": label_name,
                    "nome_comum": "Analisando...", 
                    "descricao": "Identificado localmente (MobileNet V1).",
                    "confianca": float(confidence)
                }
                
                self.identification_complete.emit(resultado)
            else:
                self.error_occurred.emit(f"Erro: Índice {idx} não encontrado nos labels.")

        except Exception as e:
            self.error_occurred.emit(f"Erro na análise: {str(e)}")

    def _emit_download_progress(self, msg):
        if not self._stopped:
            self.progress_updated.emit(msg)

    def _load_labels(self, path):
        """Lê o CSV de labels e retorna dict {id: nome}."""
        labels = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("id"): continue
                
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        # id,name
                        labels[int(parts[0])] = parts[1]
                    except ValueError:
                        pass
        return labels

    def stop(self):
        self._stopped = True
