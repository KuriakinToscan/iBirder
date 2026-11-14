#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Converte o codificador de imagem do BioCLIP (imageomics/bioclip, ViT-B/16, licença MIT) para
LiteRT (.tflite), o formato que o app já usa, e gera os textos das espécies candidatas.

O conversor (litert-torch) só existe para Linux e macOS: rode no GitHub Actions
(.github/workflows/converter-bioclip.yml, que publica a pasta como "Artifact") ou no WSL.
O resultado roda no Windows só com o ai-edge-litert do app: o avaliador o lê com
    python tools/avaliar_identificacao.py <fotos> --csv <planilha> --bioclip-litert <pasta>

Arquivos gerados na pasta de saída:
  bioclip_imagem_int8.tflite    pesos INT8 por canal, conta em FP32 ("só pesos")
  bioclip_imagem_int8d.tflite   pesos INT8 por canal, ativações quantizadas na hora (INT8 dinâmico)
  bioclip_imagem_fp32.tflite    só com --manter-fp32 (referência, ~345 MB)
  bioclip_textos.npy            embedding (FP16, normalizado) de cada espécie candidata
  bioclip_especies.txt          as espécies candidatas, na ordem das linhas de bioclip_textos.npy
  bioclip_info.json             escala dos logits, entrada, versões, checagem numérica e SHA-256

Entrada de cada .tflite: float32 [1, 224, 224, 3] (RGB de 0 a 1, foto inteira esticada, sem recorte);
a normalização do CLIP fica dentro do modelo. Saída: embedding [1, 512] já com norma 1.
Probabilidades: softmax(escala * embedding @ textos.T).

Uso (Linux/WSL, Python 3.12, fora do ambiente do app):
    pip install "torch<2.15" open_clip_torch litert-torch==0.10.0
    python tools/converter_bioclip_litert.py --saida bioclip_litert
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

BIOCLIP_HUB = "hf-hub:imageomics/bioclip"
TAMANHO_ENTRADA = 224
COSSENO_MINIMO = 0.99  # checagem com entradas aleatórias: abaixo disso a conversão é recusada
FORMATOS = ("int8", "int8d")


def criar_codificador(visual, media: Sequence[float], desvio: Sequence[float]):
    """
    Envolve o codificador de imagem do open_clip: recebe NHWC float32 de 0 a 1, aplica a
    normalização do CLIP e devolve o embedding com norma 1.
    """
    import torch

    class Codificador(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.visual = visual
            self.register_buffer("media", torch.tensor(media, dtype=torch.float32).view(1, 3, 1, 1))
            self.register_buffer("desvio", torch.tensor(desvio, dtype=torch.float32).view(1, 3, 1, 1))

        def forward(self, x):
            x = (x.permute(0, 3, 1, 2) - self.media) / self.desvio
            emb = self.visual(x)
            return emb / emb.norm(dim=-1, keepdim=True)

    return Codificador().eval()


def converter_fp32(codificador, destino: Path) -> Path:
    """Converte o codificador para .tflite em FP32 (litert-torch)."""
    import litert_torch
    import torch
    exemplo = (torch.rand(1, TAMANHO_ENTRADA, TAMANHO_ENTRADA, 3),)
    inicio = time.time()
    modelo = litert_torch.convert(codificador, exemplo)
    modelo.export(str(destino))
    logging.info(f"FP32 convertido em {time.time() - inicio:.0f} s: {destino.stat().st_size / 1e6:.1f} MB")
    return destino


def quantizar(origem: Path, destino: Path, formato: str) -> Path:
    """
    Quantiza o .tflite FP32 com o ai-edge-quantizer, pesos INT8 por canal:
      - "int8": só os pesos ficam em INT8; a conta continua em FP32;
      - "int8d": INT8 dinâmico (ativações quantizadas na hora), mais rápido na CPU.
    """
    from ai_edge_quantizer import quantizer, recipe
    receitas = {"int8": recipe.weight_only_wi8_afp32, "int8d": recipe.dynamic_wi8_afp32}
    if formato not in receitas:
        raise ValueError(f"Formato desconhecido: {formato} (use {', '.join(receitas)})")
    q = quantizer.Quantizer(str(origem))
    q.load_quantization_recipe(receitas[formato]())
    q.quantize().export_model(str(destino), overwrite=True)
    logging.info(f"{formato}: {destino.stat().st_size / 1e6:.1f} MB")
    return destino


def conferir_tflite(caminho: Path, codificador, entradas) -> float:
    """Menor cosseno entre o embedding do .tflite e o do PyTorch nas ``entradas`` (NHWC, 0 a 1)."""
    import numpy as np
    import torch
    from ai_edge_litert.interpreter import Interpreter
    interpretador = Interpreter(model_path=str(caminho))
    interpretador.allocate_tensors()
    entrada = interpretador.get_input_details()[0]
    saida = interpretador.get_output_details()[0]
    cossenos = []
    for x in entradas:
        interpretador.set_tensor(entrada["index"], x)
        interpretador.invoke()
        obtido = interpretador.get_tensor(saida["index"])
        with torch.no_grad():
            esperado = codificador(torch.from_numpy(x)).numpy()
        cossenos.append(float(np.sum(obtido * esperado)))
    return min(cossenos)


def codificar_textos(modelo, tokenizador, textos: List[str], lote: int = 256):
    """Embeddings normalizados dos textos (numpy float32, uma linha por texto)."""
    import torch
    partes = []
    with torch.no_grad():
        for i in range(0, len(textos), lote):
            emb = modelo.encode_text(tokenizador(textos[i:i + lote]))
            partes.append(emb / emb.norm(dim=-1, keepdim=True))
    return torch.cat(partes).numpy()


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _versoes() -> Dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version
    versoes = {}
    for pacote in ("torch", "open_clip_torch", "litert-torch", "ai-edge-quantizer", "ai-edge-litert"):
        try:
            versoes[pacote] = version(pacote)
        except PackageNotFoundError:
            versoes[pacote] = "?"
    return versoes


def converter(saida: Path, nome_modelo: str = BIOCLIP_HUB, pretrained: Optional[str] = None,
              formatos: Sequence[str] = FORMATOS, manter_fp32: bool = False,
              candidatas: Optional[Tuple[List[str], Dict[str, str]]] = None) -> Dict:
    """
    Gera os arquivos descritos no cabeçalho em ``saida`` e devolve o conteúdo de bioclip_info.json.
    ``candidatas`` (espécies, nomes em inglês) é para os testes; o padrão são as aves do Brasil.
    Levanta RuntimeError se algum .tflite divergir do PyTorch (cosseno < COSSENO_MINIMO).
    """
    import numpy as np
    import open_clip
    from tools.avaliar_identificacao import candidatas_bioclip, textos_bioclip

    saida.mkdir(parents=True, exist_ok=True)
    logging.info(f"Carregando {nome_modelo}...")
    modelo, _, _ = open_clip.create_model_and_transforms(nome_modelo, pretrained=pretrained)
    modelo.eval()
    tokenizador = open_clip.get_tokenizer(nome_modelo)

    especies, ingles = candidatas if candidatas is not None else candidatas_bioclip()
    logging.info(f"Codificando os textos de {len(especies)} espécies...")
    textos = codificar_textos(modelo, tokenizador, textos_bioclip(especies, ingles, misto=True))
    np.save(saida / "bioclip_textos.npy", textos.astype(np.float16))
    (saida / "bioclip_especies.txt").write_text("\n".join(especies) + "\n", encoding="utf-8")

    codificador = criar_codificador(modelo.visual, open_clip.OPENAI_DATASET_MEAN, open_clip.OPENAI_DATASET_STD)
    gerador = np.random.default_rng(0)
    entradas = [gerador.random((1, TAMANHO_ENTRADA, TAMANHO_ENTRADA, 3), dtype=np.float32) for _ in range(3)]

    fp32 = converter_fp32(codificador, saida / "bioclip_imagem_fp32.tflite")
    arquivos = {}
    try:
        for formato in formatos:
            arquivos[formato] = quantizar(fp32, saida / f"bioclip_imagem_{formato}.tflite", formato)
        if manter_fp32:
            arquivos["fp32"] = fp32
        checagem = {}
        for formato, caminho in [("fp32", fp32)] + list(arquivos.items()):
            if formato in checagem:
                continue
            checagem[formato] = round(conferir_tflite(caminho, codificador, entradas), 6)
            logging.info(f"Cosseno mínimo .tflite x PyTorch ({formato}): {checagem[formato]:.6f}")
    finally:
        if not manter_fp32 and fp32.exists():
            fp32.unlink()
    ruins = {f: c for f, c in checagem.items() if c < COSSENO_MINIMO}
    if ruins:
        raise RuntimeError(f"Conversão divergente do PyTorch (cosseno < {COSSENO_MINIMO}): {ruins}")

    info = {
        "modelo": nome_modelo,
        "licenca_modelo": "MIT (imageomics/bioclip)",
        "gerado_em": time.strftime("%Y-%m-%d %H:%M"),
        "entrada": "float32 [1,224,224,3], RGB 0-1, foto inteira esticada; normalização do CLIP dentro do modelo",
        "saida": "embedding [1,512] com norma 1",
        "escala_logits": float(modelo.logit_scale.detach().exp().item()),
        "textos": "a photo of <nome científico> with common name <nome em inglês do eBird>.",
        "especies": len(especies),
        "cosseno_minimo_tflite_x_pytorch": checagem,
        "arquivos": {f: {"arquivo": c.name, "mb": round(c.stat().st_size / 1e6, 1), "sha256": sha256(c)}
                     for f, c in arquivos.items()},
        "versoes": _versoes(),
    }
    (saida / "bioclip_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Converte o BioCLIP para LiteRT (.tflite) com pesos INT8.")
    parser.add_argument("--saida", type=Path, default=RAIZ / "tools" / "bioclip_litert")
    parser.add_argument("--modelo", default=BIOCLIP_HUB, help="nome do open_clip (padrão: o BioCLIP do Hugging Face)")
    parser.add_argument("--pretrained", default=None, help="pesos do open_clip (só para nomes que não são hf-hub)")
    parser.add_argument("--formatos", default=",".join(FORMATOS), help="int8 (só pesos), int8d (dinâmico)")
    parser.add_argument("--manter-fp32", action="store_true", help="guardar também o .tflite FP32 (~345 MB)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    formatos = [f.strip() for f in args.formatos.split(",") if f.strip()]
    try:
        info = converter(args.saida, args.modelo, args.pretrained, formatos, args.manter_fp32)
    except ImportError as e:
        logging.error(f"Falta uma biblioteca ({e}). Instale: pip install \"torch<2.15\" open_clip_torch "
                      "litert-torch==0.10.0 (só Linux/macOS)")
        return 2
    except Exception as e:
        logging.error(f"Falha na conversão: {e}")
        return 1
    logging.info(json.dumps(info, ensure_ascii=False, indent=2))
    logging.info(f"Pronto: {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
