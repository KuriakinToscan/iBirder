import sys
import time
from PySide6.QtWidgets import QApplication
from modules.step1_identity.id_worker import LocalIdentificationWorker

def run_test():
    app = QApplication(sys.argv)
    
    # Path indicated by user
    image_path = "C:/Users/98015753953/Desktop/iBirder/_lixo_refactor_v0.3.23/AmostraImagens/IMG_6075.JPG"
    
    worker = LocalIdentificationWorker(image_path)
    
    def on_finished(result):
        print(f"\n[TEST_RESULT] Identificação concluída: {result['nome_cientifico']} (Confiança: {result['confianca']:.2f})")
        app.quit()
        
    def on_error(err):
        print(f"\n[TEST_ERROR] Erro durante identificação: {err}")
        app.quit()
        
    def on_progress(msg):
        print(f"[TEST_PROGRESS] {msg}")

    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    worker.progress_updated.connect(on_progress)
    
    start_time = time.time()
    worker.start()
    
    app.exec()
    total_time = (time.time() - start_time) * 1000
    print(f"[TEST_TELEMETRY] Tempo total da Etapa 1: {total_time:.2f}ms")

if __name__ == "__main__":
    run_test()
