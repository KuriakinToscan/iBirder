import os
import json
import numpy as np
import onnxruntime as ort
from PIL import Image
from pathlib import Path
from .interfaces import IdentificadorAve

class IdentificadorLocal(IdentificadorAve):
    def __init__(self, caminho_modelo: str = "assets/model.onnx", caminho_labels: str = "assets/labels.txt", caminho_json: str = "assets/aves_locais.json"):
        self.caminho_modelo = caminho_modelo
        self.caminho_labels = caminho_labels
        self.caminho_json = caminho_json
        self.sessao = None
        self.labels = []
        self.dados_offline = []
        self._carregar_modelo()
        self._carregar_dados_offline()

    def _carregar_dados_offline(self):
        if os.path.exists(self.caminho_json):
            try:
                with open(self.caminho_json, 'r', encoding='utf-8') as f:
                    self.dados_offline = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar JSON offline: {e}")
        else:
            # Criar base padrão se não existir (v0.5.2)
            print("Criando base de dados local padrão...")
            self.dados_offline = [
                {
                    "nome_cientifico": "Pyrocephalus rubinus",
                    "nome_comum": "Príncipe",
                    "familia": "Tyrannidae",
                    "descricao": "Pequeno passeriforme de plumagem vermelha vibrante e dorso escuro, comum em áreas abertas."
                },
                {
                    "nome_cientifico": "Zonotrichia capensis",
                    "nome_comum": "Tico-tico",
                    "familia": "Passerellidae",
                    "descricao": "Ave muito conhecida pelo seu topete cinza e colar ferrugíneo, adaptada a diversos ambientes."
                },
                {
                    "nome_cientifico": "Pitangus sulphuratus",
                    "nome_comum": "Bem-te-vi",
                    "familia": "Tyrannidae",
                    "descricao": "Uma das aves mais populares, com máscara facial preta e branca e ventre amarelo vivo."
                }
            ]
            try:
                # Garantir que diretório existe
                os.makedirs(os.path.dirname(self.caminho_json), exist_ok=True)
                with open(self.caminho_json, 'w', encoding='utf-8') as f:
                    json.dump(self.dados_offline, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Erro ao criar base padrão: {e}")

    def consultar_especie(self, nome_cientifico: str) -> dict:
        """
        Busca offline baseada em JSON local (v0.5.0).
        """
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
        # Verifica se o modelo existe
        if os.path.exists(self.caminho_modelo):
            try:
                self.sessao = ort.InferenceSession(self.caminho_modelo)
            except Exception as e:
                print(f"Erro ao carregar modelo ONNX: {e}")
                self.sessao = None
        
        # Carrega labels se existirem
        if os.path.exists(self.caminho_labels):
            with open(self.caminho_labels, 'r', encoding='utf-8') as f:
                self.labels = [linha.strip() for linha in f.readlines()]

    def identificar(self, caminho_imagem: str) -> dict:
        if not self.sessao:
            # Placeholder se o modelo não estiver carregado
            return {
                "erro": "Modelo local não encontrado ou inválido.",
                "sugestao": "Baixe o modelo em assets/ ou use o modo Online.",
                "top_k": []
            }

        imagem = self._processar_imagem(caminho_imagem)
        
        # Inferência
        input_name = self.sessao.get_inputs()[0].name
        output_name = self.sessao.get_outputs()[0].name
        result = self.sessao.run([output_name], {input_name: imagem})
        
        # Processar resultados (softmax e top k)
        scores = result[0][0]
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

    def _processar_imagem(self, caminho_imagem: str):
        # Pré-processamento padrão EfficientNet (224x224, normalização)
        img = Image.open(caminho_imagem).convert('RGB')
        img = img.resize((224, 224))
        img_data = np.array(img).astype('float32')
        
        # Normalização (exemplo simples, ajustar conforme modelo específico)
        img_data = img_data / 255.0
        # Transpor para formato (N, C, H, W) se necessário, o padrão ONNX costuma pedir
        img_data = np.transpose(img_data, (2, 0, 1))
        img_data = np.expand_dims(img_data, axis=0) # Batch size 1
        
        return img_data

    def _softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)
