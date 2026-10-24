#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Fila de fotos de uma pasta, para o layout "Mesa de trabalho" (v1.4).

A pessoa abre uma pasta e trabalha uma foto por vez: identifica, confere, grava e vai
para a próxima. A fila só guarda a ordem e a situação de cada foto; a identificação
continua sendo a da janela, uma foto de cada vez (não há identificação em lote: a etapa
do WikiAves não pode virar operação em massa, item 13.3 dos termos de uso do site).

Funções sem Qt, para teste e reuso.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

# Os mesmos formatos do seletor de arquivo da janela
EXTENSOES = (".jpg", ".jpeg", ".png")

# Situação de cada foto
PENDENTE = "pendente"        # ainda não gravada nesta sessão
GRAVADA = "gravada"          # dados gravados agora, pela fila
JA_GRAVADA = "ja_gravada"    # já tinha registro do iBirder ao abrir a pasta
PULADA = "pulada"            # a pessoa pulou

SITUACOES = (PENDENTE, GRAVADA, JA_GRAVADA, PULADA)


@dataclass
class ItemFila:
    caminho: Path
    situacao: str = PENDENTE
    especie: str = ""        # nome científico gravado (quando houver)

    @property
    def nome(self):
        return self.caminho.name


def _ordem_natural(caminho):
    """IMG_2.jpg antes de IMG_10.jpg, sem diferença de maiúsculas."""
    return [int(parte) if parte.isdigit() else parte for parte in re.split(r"(\d+)", caminho.name.lower())]


def listar_fotos(pasta):
    """Fotos da pasta (sem subpastas), em ordem natural do nome. Pasta inválida: lista vazia."""
    try:
        arquivos = [c for c in Path(pasta).iterdir() if c.is_file() and c.suffix.lower() in EXTENSOES]
    except OSError as e:
        logging.error(f"Fila de fotos: não foi possível ler a pasta {pasta}: {e}")
        return []
    return sorted(arquivos, key=_ordem_natural)


class FilaFotos:
    """Fotos de uma pasta, a foto atual e a situação de cada uma."""

    def __init__(self, pasta=None, caminhos=None):
        self.pasta = Path(pasta) if pasta else None
        if caminhos is None:
            caminhos = listar_fotos(pasta) if pasta else []
        self.itens = [ItemFila(Path(c)) for c in caminhos]
        self.atual = None  # índice da foto aberta (None: a foto aberta não é da fila)

    def __len__(self):
        return len(self.itens)

    def indice_de(self, caminho):
        """Índice da foto na fila, ou None."""
        if not caminho:
            return None
        alvo = Path(caminho)
        for i, item in enumerate(self.itens):
            if item.caminho == alvo:
                return i
        return None

    def marcar(self, indice, situacao, caminho=None, especie=None):
        """Muda a situação de uma foto (e o caminho, se ela foi renomeada ao gravar)."""
        if situacao not in SITUACOES:
            raise ValueError(f"Situação desconhecida: {situacao}")
        item = self.itens[indice]
        item.situacao = situacao
        if caminho:
            item.caminho = Path(caminho)
        if especie is not None:
            item.especie = especie

    def proxima(self, depois_de=None):
        """
        Índice da próxima foto pendente depois de `depois_de` (padrão: a atual), voltando
        ao início da fila se preciso; a própria foto de partida não conta. None quando não
        sobra nenhuma outra pendente.
        """
        if not self.itens:
            return None
        inicio = self.atual if depois_de is None else depois_de
        total = len(self.itens)
        if inicio is None:
            ordem = range(total)
        else:
            ordem = [(inicio + passo) % total for passo in range(1, total)]
        for i in ordem:
            if self.itens[i].situacao == PENDENTE:
                return i
        return None

    def contagem(self):
        """Quantas fotos há em cada situação."""
        contagem = {s: 0 for s in SITUACOES}
        for item in self.itens:
            contagem[item.situacao] += 1
        return contagem

    def resumo(self):
        """Texto curto: '3 de 12 gravadas · 2 já tinham registro · 1 pulada'."""
        if not self.itens:
            return "Nenhuma foto na fila"
        c = self.contagem()
        partes = [f"{c[GRAVADA]} de {len(self.itens)} gravadas"]
        if c[JA_GRAVADA]:
            partes.append(f"{c[JA_GRAVADA]} já {'tinha' if c[JA_GRAVADA] == 1 else 'tinham'} registro")
        if c[PULADA]:
            partes.append(f"{c[PULADA]} {'pulada' if c[PULADA] == 1 else 'puladas'}")
        return " · ".join(partes)
