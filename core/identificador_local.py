import os
import json
import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None
from PIL import Image
from .interfaces import IdentificadorAve

class IdentificadorLocal(IdentificadorAve):
    def __init__(self, caminho_modelo: str = "models/model.onnx", caminho_labels: str = "assets/labels.txt", caminho_json: str = "assets/aves_locais.json"):
        # Nota: Mudamos padrão para ONNX para compatibilidade OpenCV
        self.caminho_modelo = caminho_modelo
        self.caminho_labels = caminho_labels
        self.caminho_json = caminho_json
        self.net = None 
        self.labels = []
        self.dados_offline = []
        
        if cv2:
            self._carregar_modelo()
        else:
            print("Aviso: OpenCV não encontrado. IA Offline indisponível.")
            
        self._carregar_dados_offline()

    def _carregar_dados_offline(self):
        if os.path.exists(self.caminho_json):
            try:
                with open(self.caminho_json, 'r', encoding='utf-8') as f:
                    self.dados_offline = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar JSON offline: {e}")
        else:
            print("Criando base de dados local padrão...")
            self.dados_offline = [
                {
                    "nome_cientifico": "Pyrocephalus rubinus",
                    "nome_comum": "Príncipe",
                    "familia": "Tyrannidae",
                    "descricao": "Pequeno passeriforme de plumagem vermelha vibrante e dorso escuro."
                },
                {
                    "nome_cientifico": "Zonotrichia capensis",
                    "nome_comum": "Tico-tico",
                    "familia": "Passerellidae",
                    "descricao": "Ave conhecida pelo seu topete cinza e colar ferrugíneo."
                },
                {
                    "nome_cientifico": "Pitangus sulphuratus",
                    "nome_comum": "Bem-te-vi",
                    "familia": "Tyrannidae",
                    "descricao": "Máscara facial preta e branca e ventre amarelo vivo."
                }
            ]
            try:
                os.makedirs(os.path.dirname(self.caminho_json), exist_ok=True)
                with open(self.caminho_json, 'w', encoding='utf-8') as f:
                    json.dump(self.dados_offline, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Erro ao criar base padrão: {e}")

    def consultar_especie(self, nome_cientifico: str) -> dict:
        nome_busca = nome_cientifico.lower().strip()
        for ave in self.dados_offline:
            if nome_busca in ave["nome_cientifico"].lower():
                return {
                    "nome_cientifico": ave["nome_cientifico"],
                    "nome_comum": ave["nome_comum"],
                    "familia": ave["familia"],
                    "confianca": "Validado Offline",
                    "descricao": ave["descricao"]
                }
        return {"erro": "Espécie não encontrada na base local."}

    def _carregar_modelo(self):
        if os.path.exists(self.caminho_modelo):
            try:
                # OpenCV DNN (v0.6.3)
                self.net = cv2.dnn.readNet(self.caminho_modelo)
            except Exception as e:
                print(f"Erro ao carregar modelo OpenCV: {e}")
                self.net = None
        else:
            self.net = None # Falha silenciosa na inicialização
        
        if os.path.exists(self.caminho_labels):
            with open(self.caminho_labels, 'r', encoding='utf-8') as f:
                self.labels = [linha.strip() for linha in f.readlines()]

    def identificar(self, caminho_imagem: str) -> dict:
        # Tratamento Silencioso (v0.6.3)
        if not cv2:
             return {
                "aviso_silencioso": "Modo Offline: Bibliotecas de Visão não instaladas.",
                "detalhes": "Instale 'opencv-python' ou use o instalador."
            }
            
        if not self.net or not os.path.exists(self.caminho_modelo):
            return {
                "aviso_silencioso": "Modo Offline: Identificação por imagem requer pacote adicional.",
                "detalhes": "Acesse Configurações para baixar."
            }

        try:
            # Pré-processamento OpenCV
            image = cv2.imread(caminho_imagem)
            if image is None:
                 return {"erro": "Erro ao ler imagem."}
                 
            blob = cv2.dnn.blobFromImage(image, 1.0/127.5, (224, 224), (127.5, 127.5, 127.5), swapRB=True, crop=False)
            self.net.setInput(blob)
            preds = self.net.forward()
            
            # Pós-processamento (Softmax e TopK)
            scores = preds[0]
            probs = self._softmax(scores)
            top_k_indices = np.argsort(probs)[-3:][::-1]

            candidatos = []
            for idx in top_k_indices:
                label = self.labels[idx] if idx < len(self.labels) else f"Species {idx}"
                candidatos.append({
                    "nome_cientifico": label,
                    "confianca": float(probs[idx])
                })

            return {
                "melhor_taxa": candidatos[0],
                "top_3": candidatos
            }
        except Exception as e:
            # Erro técnico ainda pode ser retornado se falhar no meio
            return {
                "erro": "Erro técnico na IA",
                "detalhes": str(e)
            }

    def _softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)
