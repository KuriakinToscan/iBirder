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
        self.min_confidence = 0.70 # 70% threshold

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
            
            # Redimensionamento com LANCZOS (Melhor qualidade)
            img = Image.open(self.image_path).convert('RGB')
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Check input type
            input_type = input_details[0]['dtype']
            img_array = np.array(img, dtype=input_type)
            
            # Normalization
            if input_type == np.float32:
                 # Normalização padrão se for float (-1 a 1)
                 img_array = (np.float32(img_array) - 127.5) / 127.5

            # Add batch dimension
            input_data = np.expand_dims(img_array, axis=0)

            # 4. Inferência
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()

            # 5. Interpretar Resultados (EfficientDet-Lite Output Tensors)
            if len(output_details) >= 3:
                # Lógica EfficientDet (Object Detection)
                # 0: Boxes, 1: Classes, 2: Scores, 3: Count
                classes = interpreter.get_tensor(output_details[1]['index'])[0] # Class indices
                scores = interpreter.get_tensor(output_details[2]['index'])[0] # Confidence scores
                
                # Pegar a detecção com maior score
                best_idx = np.argmax(scores)
                idx = int(classes[best_idx])
                confidence = float(scores[best_idx])
                
                print(f"[IA] EfficientDet: Melhor classe {idx} com score {confidence:.2f}")
                
            else:
                # Fallback para Classificação (EfficientNet/MobileNet)
                output_data = interpreter.get_tensor(output_details[0]['index'])
                results = np.squeeze(output_data)
                top_k = results.argsort()[-1:][::-1]
                idx = top_k[0]
                confidence = float(results[idx])
                
                # Se for uint8, desnormalizar (0-255 -> 0.0-1.0)
                if output_details[0]['dtype'] == np.uint8:
                     confidence = confidence / 255.0
                print(f"[IA] Classifier: Classe {idx} com score {confidence:.2f}")

            elapsed = time.time() - start_time
            print(f"[IA] Inferência local em {elapsed:.2f}s. Confiança: {confidence:.2f}")

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
                # EfficientDet-Lite geralmente usa índices diretos.
                label_name = labels[idx] 
                
                # Resultado
                resultado = {
                    "nome_cientifico": label_name,
                    "nome_comum": "Analisando...", 
                    "descricao": "Identificado localmente (EfficientDet-Lite).",
                    "confianca": float(confidence)
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
