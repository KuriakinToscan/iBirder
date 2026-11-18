#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
IA local do iBirder: BioCLIP (imageomics/bioclip, ViT-B/16, licença MIT) em LiteRT, INT8 dinâmico.

O BioCLIP não tem uma saída por espécie: ele transforma a foto num vetor (embedding) e compara
com o vetor do texto de cada espécie ("a photo of <nome científico> with common name <inglês>."),
calculado uma vez pelo tools/converter_bioclip_litert.py. A espécie mais parecida vence.

Arquivos (assets/models/bioclip/, baixados da Release "modelo-bioclip-N"; veja core/model_manager.py):
  bioclip_imagem_int8d.tflite  codificador de imagem: float32 [1,224,224,3] RGB 0-1 -> [1,512] (norma 1)
  bioclip_textos.npy           embeddings FP16 das espécies, uma linha por espécie
  bioclip_especies.txt         "nome científico<TAB>1" (com registro no Brasil) ou "<TAB>0"
  bioclip_info.json            escala dos logits e procedência

Medido em 14/11/2026 no Windows do usuário (tools/avaliar_identificacao.py, entre as aves do Brasil):
top-1 de 46,7% em 300 fotos do iNaturalist no Brasil (MobileNetV2 com prior Brasil: 16,3%) e de 59,5%
em 200 fotos de espécies que o MobileNetV2 conhecia (ele: 59,0%); 126 ms por foto, 88 MB.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

ARQUIVO_MODELO = "bioclip_imagem_int8d.tflite"
ARQUIVO_TEXTOS = "bioclip_textos.npy"
ARQUIVO_ESPECIES = "bioclip_especies.txt"
ARQUIVO_INFO = "bioclip_info.json"
TAMANHO_ENTRADA = 224


def ler_especies(caminho: Path) -> Tuple[List[str], np.ndarray]:
    """(nomes, máscara booleana "tem registro no Brasil"), na ordem das linhas de bioclip_textos.npy."""
    nomes, brasil = [], []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.rstrip("\r\n")
            if not linha.strip():
                continue
            nome, _, marca = linha.partition("\t")
            nomes.append(nome.strip())
            brasil.append(marca.strip() == "1")
    return nomes, np.array(brasil, dtype=bool)


def gravar_especies(caminho: Path, nomes: Sequence[str], brasil: Sequence[bool]) -> None:
    """Inverso de ``ler_especies``."""
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        for nome, no_brasil in zip(nomes, brasil):
            f.write(f"{nome}\t{1 if no_brasil else 0}\n")


def threads_padrao() -> int:
    """Núcleos para o LiteRT: metade dos lógicos (núcleos físicos, em geral), entre 1 e 4."""
    return max(1, min(4, (os.cpu_count() or 2) // 2))


class ClassificadorBioclip:
    """
    Codificador de imagem (LiteRT) + textos das espécies. Não é thread-safe: quem usa de mais de
    uma thread precisa de uma trava em volta de ``embedding`` (o id_worker usa _interpreter_lock).
    """

    def __init__(self, pasta: Path, interpreter_cls, threads: Optional[int] = None,
                 arquivo_modelo: str = ARQUIVO_MODELO):
        pasta = Path(pasta)
        info = json.loads((pasta / ARQUIVO_INFO).read_text(encoding="utf-8"))
        self.escala = float(info["escala_logits"])
        self.especies, self.brasil = ler_especies(pasta / ARQUIVO_ESPECIES)
        self.textos = np.load(pasta / ARQUIVO_TEXTOS).astype(np.float32)
        if self.textos.shape[0] != len(self.especies):
            raise ValueError(f"{ARQUIVO_TEXTOS} tem {self.textos.shape[0]} linhas e {ARQUIVO_ESPECIES} "
                             f"tem {len(self.especies)} espécies.")
        self.indices_brasil = np.flatnonzero(self.brasil)
        self.threads = threads or threads_padrao()
        self.interpretador = interpreter_cls(model_path=str(pasta / arquivo_modelo), num_threads=self.threads)
        self.interpretador.allocate_tensors()
        self._entrada = self.interpretador.get_input_details()[0]
        self._saida = self.interpretador.get_output_details()[0]
        logging.info(f"BioCLIP carregado: {len(self.especies)} espécies ({len(self.indices_brasil)} do Brasil), "
                     f"{self.threads} núcleo(s).")

    @staticmethod
    def preparar(imagem) -> np.ndarray:
        """Imagem PIL já esticada para 224x224 -> float32 [1,224,224,3] de 0 a 1."""
        dados = np.asarray(imagem.convert("RGB"), dtype=np.float32) / 255.0
        return np.expand_dims(dados, 0)

    def embedding(self, entrada: np.ndarray) -> np.ndarray:
        """Embedding da foto (vetor de norma 1)."""
        self.interpretador.set_tensor(self._entrada["index"], entrada)
        self.interpretador.invoke()
        emb = self.interpretador.get_tensor(self._saida["index"]).reshape(-1).astype(np.float32)
        return emb / max(float(np.linalg.norm(emb)), 1e-12)

    def ranking(self, emb: np.ndarray, so_brasil: bool = True) -> List[Tuple[str, float]]:
        """[(espécie, probabilidade)] decrescente: softmax de escala x cosseno entre as candidatas."""
        indices = self.indices_brasil if so_brasil else np.arange(len(self.especies))
        logits = self.escala * (self.textos[indices] @ emb)
        prob = np.exp(logits - logits.max())
        prob /= prob.sum()
        ordem = np.argsort(-prob)
        return [(self.especies[indices[i]], float(prob[i])) for i in ordem]
