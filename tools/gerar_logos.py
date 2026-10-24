#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Gera o logo de cada tema a partir do logo original (ferramenta de manutenção).

Uso (na pasta do projeto):
    python tools/gerar_logos.py

O assets/logo_ave.svg é só uma imagem PNG embutida (pássaro e "iBirder" em tons de
cinza). Cada tema recebe uma cópia recolorida por duotone: a luminância de cada pixel
vira uma posição entre a cor de sombra e a cor de luz do tema. Desenho, transparência
e sombras ficam iguais ao original.

Saídas:
  assets/temas/logo_clean.png      (verde-petróleo)
  assets/temas/logo_classico.png   (verde-musgo)

Rode de novo só se o logo original ou as cores dos temas mudarem.
"""

import base64
import logging
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "assets" / "logo_ave.svg"
DESTINO = RAIZ / "assets" / "temas"

# tema -> (cor de sombra, cor de luz). O Off-White usa o original, sem cópia.
CORES_LOGO: dict[str, tuple[str, str]] = {
    "clean": ("#134E4A", "#E6F4F1"),
    "classico": ("#2E4A3B", "#F5F0E6"),
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def extrair_png(svg: Path) -> Image.Image:
    """Lê a primeira imagem PNG embutida (data URI base64) no SVG."""
    texto = svg.read_text(encoding="utf-8")
    m = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", texto)
    if not m:
        raise ValueError(f"Nenhum PNG embutido encontrado em {svg}")
    return Image.open(BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")


def _rgb(cor: str) -> tuple[int, int, int]:
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def duotone(img: Image.Image, sombra: str, luz: str) -> Image.Image:
    """
    Recolore a imagem: o pixel mais escuro do original vira `sombra`, o branco vira `luz`
    e os tons intermediários ficam entre os dois. O canal alfa é preservado.
    """
    lum = img.convert("L")
    minimo, _ = lum.getextrema()
    escala = 255 - minimo or 1
    s, l = _rgb(sombra), _rgb(luz)
    # Tabela por canal: luminância (0-255) -> valor do canal
    tabelas = []
    for c in range(3):
        tabelas.append([
            round(s[c] + (l[c] - s[c]) * min(max((v - minimo) / escala, 0.0), 1.0))
            for v in range(256)
        ])
    canais = [lum.point(t) for t in tabelas]
    resultado = Image.merge("RGB", canais).convert("RGBA")
    resultado.putalpha(img.getchannel("A"))
    return resultado


def main() -> int:
    try:
        original = extrair_png(ORIGEM)
    except (OSError, ValueError) as e:
        logging.error(f"Não foi possível ler o logo original: {e}")
        return 1
    DESTINO.mkdir(parents=True, exist_ok=True)
    for tema, (sombra, luz) in CORES_LOGO.items():
        saida = DESTINO / f"logo_{tema}.png"
        duotone(original, sombra, luz).save(saida, optimize=True)
        logging.info(f"{saida.relative_to(RAIZ)} gerado ({original.width}x{original.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
