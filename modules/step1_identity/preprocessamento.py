#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme
#  publicada pela Free Software Foundation, tanto a versão 3 da
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil,
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR.
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

"""
Redução da foto para a identificação (etapa 1).

- O modelo local recebe 224x224 px. A foto é aberta já reduzida (no JPEG, a própria
  decodificação reduz em 1/2, 1/4 ou 1/8 com ``Image.draft``), mantendo o lado maior
  com pelo menos ``LADO_MIN_ABERTURA`` px (4x a entrada do modelo, folga para o LANCZOS).
  Numa foto de 6000x4000 px isso decodifica 1500x1000 px em vez de 24 Mpx.
- Depois a foto inteira é esticada para 224x224 px (sem recorte), como o modelo foi treinado.
  Na avaliação de 14/11/2026 (200 fotos do iNaturalist de 110 espécies que o modelo conhece,
  tools/avaliar_identificacao.py), esticar acertou 46,0% no top-1 contra 41,5% com borda cinza
  (letterbox): 15 x 6 fotos discordantes, McNemar p = 0,078. ``letterbox`` fica para comparação.
- Para a nuvem (iNaturalist, Google Vision), a cópia enviada tem no máximo
  ``LADO_NUVEM`` px no lado maior, em JPEG qualidade ``QUALIDADE_NUVEM``.

Sem Qt: testável sem interface (tests/test_preprocessamento.py).
"""

import io
import logging
from typing import Tuple, Union
from pathlib import Path

from PIL import Image, ImageOps

LADO_MIN_ABERTURA = 896      # 4x a entrada de 224 px do modelo
LADO_NUVEM = 1024            # lado maior da cópia enviada à nuvem
QUALIDADE_NUVEM = 85         # qualidade JPEG da cópia enviada à nuvem
COR_BORDA = (128, 128, 128)  # cinza médio: vira ~0 na normalização [-1, 1]

Caminho = Union[str, Path]


def abrir_reduzida(caminho: Caminho, lado_min: int = LADO_MIN_ABERTURA) -> Image.Image:
    """
    Abre a foto em RGB, girada pela tag EXIF Orientation, com o lado maior >= ``lado_min``
    (ou o tamanho original, se for menor). A proporção é sempre preservada.

    No JPEG, ``draft`` escolhe a maior redução na decodificação (1/2, 1/4, 1/8) que ainda
    deixa a imagem com pelo menos o tamanho pedido: menos memória e menos tempo.
    """
    with Image.open(caminho) as img:
        largura, altura = img.size
        maior = max(largura, altura)
        if img.format == "JPEG" and maior > lado_min:
            escala = lado_min / maior
            pedido = (max(1, round(largura * escala)), max(1, round(altura * escala)))
            img.draft("RGB", pedido)
            if img.size != (largura, altura):
                logging.debug(f"Foto aberta reduzida: {largura}x{altura} -> {img.size[0]}x{img.size[1]} px.")
        img = ImageOps.exif_transpose(img).convert("RGB")

    # Formatos sem redução na decodificação (PNG...): reduz aqui, mantendo o lado mínimo
    if max(img.size) > 2 * lado_min:
        img.thumbnail((2 * lado_min, 2 * lado_min), Image.Resampling.LANCZOS)
    return img


def letterbox(img: Image.Image, largura: int, altura: int,
              cor_borda: Tuple[int, int, int] = COR_BORDA) -> Image.Image:
    """
    Reduz ``img`` até caber em ``largura`` x ``altura`` sem deformar e completa o restante
    com ``cor_borda``, centralizando a imagem.
    """
    if largura <= 0 or altura <= 0:
        raise ValueError(f"Tamanho de entrada inválido: {largura}x{altura}")
    escala = min(largura / img.width, altura / img.height)
    novo = (max(1, round(img.width * escala)), max(1, round(img.height * escala)))
    reduzida = img.resize(novo, Image.Resampling.LANCZOS)
    quadro = Image.new("RGB", (largura, altura), cor_borda)
    quadro.paste(reduzida, ((largura - novo[0]) // 2, (altura - novo[1]) // 2))
    return quadro


def esticar(img: Image.Image, largura: int, altura: int) -> Image.Image:
    """Redimensiona a foto inteira para ``largura`` x ``altura``, sem recorte (a proporção muda)."""
    if largura <= 0 or altura <= 0:
        raise ValueError(f"Tamanho de entrada inválido: {largura}x{altura}")
    return img.resize((largura, altura), Image.Resampling.LANCZOS)


def preparar_para_modelo(caminho: Caminho, largura: int, altura: int) -> Image.Image:
    """Foto pronta para a entrada do modelo local: aberta reduzida e esticada, sem recorte."""
    return esticar(abrir_reduzida(caminho), largura, altura)


def jpeg_para_nuvem(caminho: Caminho, lado: int = LADO_NUVEM, qualidade: int = QUALIDADE_NUVEM) -> bytes:
    """Cópia JPEG da foto com o lado maior <= ``lado`` px, para envio às APIs de nuvem."""
    img = abrir_reduzida(caminho, lado_min=lado)
    img.thumbnail((lado, lado), Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    img.save(saida, format="JPEG", quality=qualidade)
    logging.debug(f"Cópia para a nuvem: {img.size[0]}x{img.size[1]} px, {len(saida.getvalue()) / 1024:.0f} kB.")
    return saida.getvalue()
