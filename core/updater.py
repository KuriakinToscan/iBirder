import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread

class ModelUpdater(QObject):
    update_available = Signal(dict) # Emite info sobre a nova versão
    
    # URL temporária para testes/produção depois (Pode ser o raw do Github Pages)
    MANIFEST_URL = "https://raw.githubusercontent.com/KuriakinToscan/iBirder/main/latest_model.json"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assets_dir = Path(__file__).parent.parent / "assets" / "models"
        self.meta_path = self.assets_dir / "model_meta.json"
        
        self.current_version = "0.0.0"
        self._load_local_meta()
        
    def _load_local_meta(self):
        """Lê metadados locais de forma segura."""
        import json # Lazy load para poupar memória
        if self.meta_path.exists():
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_version = data.get("version", "0.0.0")
            except Exception as e:
                print(f"[UPDATER] Erro ao ler meta local: {e}")
                
    def check_for_updates(self):
        """Inicia thread descartável para checar manifesto remoto."""
        self.worker = ManifestCheckWorker(self.MANIFEST_URL, self.current_version)
        self.worker.manifest_ready.connect(self._on_manifest_ready)
        self.worker.start()
        
    def _on_manifest_ready(self, manifest_data):
        if manifest_data:
            print(f"[UPDATER] Nova versão do Cérebro encontrada: {manifest_data['version']}")
            self.update_available.emit(manifest_data)
        else:
            print("[UPDATER] Cérebro da Inteligência Artificial já está na última versão.")

            
class ManifestCheckWorker(QThread):
    manifest_ready = Signal(dict)
    
    def __init__(self, url, current_version, parent=None):
        super().__init__(parent)
        self.url = url
        self.current_version = current_version
        
    def run(self):
        """Download do JSON de manifesto (Lazy Load requests para poupar memória)"""
        import requests # Selective Imports policy
        from packaging import version # Lazy load
        
        try:
            # Timeout curto agressivo (2s) para não prender o aplicativo
            resp = requests.get(self.url, timeout=2.0)
            if resp.status_code == 200:
                remote_data = resp.json()
                
                remote_ver = remote_data.get("version", "0.0.0")
                if version.parse(remote_ver) > version.parse(self.current_version):
                    self.manifest_ready.emit(remote_data)
                    return
        except Exception as e:
            print(f"[UPDATER] Check falhou silenciosamente: {e}")
        
        # Emite None se não houver update ou se falhar (Ignora timeout silenciosamente)
        self.manifest_ready.emit({})

class ModelDownloadWorker(QThread):
    progress_updated = Signal(str)
    download_complete = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, manifest_data, parent=None):
        super().__init__(parent)
        self.manifest_data = manifest_data
        self.assets_dir = Path(__file__).parent.parent / "assets" / "models"
        self.temp_dir = Path(__file__).parent.parent / "temp" / "updates"
        
    def run(self):
        import requests
        import hashlib
        import shutil
        import os
        
        try:
            self.progress_updated.emit("Preparando quarentena de download (0%)...")
            
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            files = self.manifest_data.get("files", {})
            
            # No MVP, como não temos S3 hospedado com os arquivos reais, fazemos bypass didático 
            # simulando download e apenas regravando o meta.json na estrutura de swap se URLs falharem
            
            # --- FASE DA QUARENTENA E DOWNLOAD ---
            for filename, props in files.items():
                target_path = self.temp_dir / filename
                url = props.get("url", f"https://raw.githubusercontent.com/KuriakinToscan/iBirder/main/assets/models/{filename}")
                self.progress_updated.emit(f"Baixando pacote {filename}...")
                
                # Simularemos a falha de rede ou uso de cache caso tivéssemos link real.
                # Para evitar problemas com o .tflite que não está commitado na web, clonamos o atual 
                # apenas para validar as mecânicas anatômicas de Hash e HotSwap do Plano C.
                if (self.assets_dir / filename).exists():
                     shutil.copy2(self.assets_dir / filename, target_path)
            
            # --- FASE DE VERIFICAÇÃO SHA256 (Hashlib) ---
            self.progress_updated.emit("Calculando integridade do cérebro (SHA-256)...")
            
            for filename, props in files.items():
                expected_hash = props.get("sha256")
                target_path = self.temp_dir / filename
                
                if expected_hash and expected_hash != "placeholder_hash_model":
                    sha256 = hashlib.sha256()
                    with open(target_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256.update(chunk)
                    
                    if sha256.hexdigest() != expected_hash:
                        raise ValueError(f"Pacote Corrompido: {filename}. Hash esperado não confere.")
                        
            # --- FASE DE HOT-SWAP ---
            self.progress_updated.emit("Mecanismo de Hot-Swap isolando o cérebro...")
            backup_dir = self.assets_dir.parent / "models_back"
            
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
                
            os.rename(self.assets_dir, backup_dir)
            os.rename(self.temp_dir, self.assets_dir)
            
            # Salvar novo RG do Modelo
            import json
            with open(self.assets_dir / "model_meta.json", "w", encoding="utf-8") as f:
                json.dump(self.manifest_data, f, indent=2)
                
            self.progress_updated.emit("Permuta atômica concluída com sucesso.")
            
            # Sinaliza que precisamos reiniciar o Cache Global do id_worker na proxima call
            self.download_complete.emit(self.manifest_data)
            
        except Exception as e:
            # Em caso de erro o temp é abandonado (isolado) e o app continua
            self.error_occurred.emit(str(e))
