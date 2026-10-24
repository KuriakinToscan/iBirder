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
Temas visuais do iBirder (v1.4).

Cada tema é um conjunto de tokens (cores, fontes, raios). A interface nunca usa cor
fixa: estilos (QSS) e HTML dos rótulos são escritos com `var(--token)` e renderizados
para o tema ativo por `renderizar()`. Trocar de tema = renderizar de novo.

Funções sem Qt, para teste e reuso.
"""

import re
from dataclasses import dataclass, field

TEMA_PADRAO = "offwhite"

# Tokens obrigatórios em todo tema (cores em #RRGGBB)
TOKENS_COR = (
    "fundo",               # fundo da janela
    "superficie",          # cards, campos, menus
    "superficie_alt",      # caixas preenchidas dentro dos cards
    "borda",
    "borda_suave",
    "texto",
    "texto_secundario",    # rótulos ("Nome Comum:")
    "texto_suave",         # placeholders, notas
    "titulo_sessao",       # títulos de seção ("Taxonomia")
    "hover",
    "selecao",
    "botao_fundo",         # botão comum
    "botao_texto",
    "botao_borda",
    "botao_hover",
    "destaque",            # botão principal (classe "primario"), marcadores
    "destaque_hover",
    "texto_destaque",      # texto sobre "destaque"
    "secundario_fundo",    # botão da classe "secundario"
    "secundario_texto",
    "link",
    "link_hover",
    "enfase",              # faixas e detalhes decorativos
    "alerta_fundo",
    "alerta_borda",
    "alerta_texto",
    "sucesso_fundo",
    "sucesso_texto",
    "erro_fundo",
    "erro_texto",
    "barra_titulo",        # barra de título do Windows (DWM)
    "texto_barra_titulo",
)
TOKENS_TEXTO = ("fonte", "fonte_titulo")
TOKENS_NUMERO = ("raio", "raio_botao", "altura_botao")

_RE_VAR = re.compile(r"var\(--([a-z_]+)\)")


@dataclass(frozen=True)
class Tema:
    """Um tema visual: identificador, nome exibido, tokens e arquivo do logo."""
    id: str
    nome: str
    descricao: str
    logo: str                      # arquivo em assets/ (logo original recolorido)
    tokens: dict = field(default_factory=dict)

    def __getitem__(self, chave):
        return self.tokens[chave]


OFFWHITE = Tema(
    id="offwhite",
    nome="Off-White",
    descricao="O visual clássico do iBirder: cinza-grafite sobre fundo claro.",
    logo="logo_ave.svg",
    tokens={
        "fundo": "#F0F2F5",
        "superficie": "#FFFFFF",
        "superficie_alt": "#F9FAFB",
        "borda": "#D1D5DB",
        "borda_suave": "#E5E7EB",
        "texto": "#1F2937",
        "texto_secundario": "#4B5563",
        "texto_suave": "#6B7280",
        "titulo_sessao": "#4B5563",
        "hover": "#F3F4F6",
        "selecao": "#E5E7EB",
        "botao_fundo": "#374151",
        "botao_texto": "#FFFFFF",
        "botao_borda": "#374151",
        "botao_hover": "#1F2937",
        "destaque": "#374151",
        "destaque_hover": "#1F2937",
        "texto_destaque": "#FFFFFF",
        "secundario_fundo": "#E5E7EB",
        "secundario_texto": "#374151",
        "link": "#005FA8",
        "link_hover": "#004C87",
        "enfase": "#10B981",
        "alerta_fundo": "#FFFBEB",
        "alerta_borda": "#F59E0B",
        "alerta_texto": "#92400E",
        "sucesso_fundo": "#D1FAE5",
        "sucesso_texto": "#065F46",
        "erro_fundo": "#FEE2E2",
        "erro_texto": "#B91C1C",
        "barra_titulo": "#374151",
        "texto_barra_titulo": "#FFFFFF",
        "fonte": "Segoe UI",
        "fonte_titulo": "Segoe UI",
        "raio": 12,
        "raio_botao": 8,
        "altura_botao": 26,
    },
)

CLEAN = Tema(
    id="clean",
    nome="Clean",
    descricao="Leve e moderno: fundo branco, fonte Figtree e verde-petróleo só nas ações principais.",
    logo="temas/logo_clean.png",
    tokens={
        "fundo": "#F7F8FA",
        "superficie": "#FFFFFF",
        "superficie_alt": "#F7F8FA",
        "borda": "#E1E4E8",
        "borda_suave": "#EEF0F3",
        "texto": "#111827",
        "texto_secundario": "#4B5563",
        "texto_suave": "#6B7280",
        "titulo_sessao": "#374151",
        "hover": "#F1F3F5",
        "selecao": "#E3F2EF",
        "botao_fundo": "#FFFFFF",
        "botao_texto": "#1F2937",
        "botao_borda": "#D5D9DF",
        "botao_hover": "#F1F3F5",
        "destaque": "#0F766E",
        "destaque_hover": "#115E59",
        "texto_destaque": "#FFFFFF",
        "secundario_fundo": "#F1F3F5",
        "secundario_texto": "#1F2937",
        "link": "#0F766E",
        "link_hover": "#115E59",
        "enfase": "#0F766E",
        "alerta_fundo": "#FFFBEB",
        "alerta_borda": "#F59E0B",
        "alerta_texto": "#92400E",
        "sucesso_fundo": "#E3F2EF",
        "sucesso_texto": "#0B5A53",
        "erro_fundo": "#FEE2E2",
        "erro_texto": "#B91C1C",
        "barra_titulo": "#FFFFFF",
        "texto_barra_titulo": "#111827",
        "fonte": "Figtree",
        "fonte_titulo": "Figtree",
        "raio": 12,
        "raio_botao": 8,
        "altura_botao": 32,
    },
)

CLASSICO = Tema(
    id="classico",
    nome="Clássico",
    descricao="Inspirado nos guias de campo: papel creme, títulos com serifa e verde-musgo.",
    logo="temas/logo_classico.png",
    tokens={
        "fundo": "#EFE9DC",
        "superficie": "#FBF8F1",
        "superficie_alt": "#F5F0E6",
        "borda": "#CFC4AE",
        "borda_suave": "#DDD3BF",
        "texto": "#2B2A26",
        "texto_secundario": "#5A5346",
        "texto_suave": "#6B6355",
        "titulo_sessao": "#7A4B2A",
        "hover": "#F1EBDD",
        "selecao": "#E6DFCF",
        "botao_fundo": "#FBF8F1",
        "botao_texto": "#2B2A26",
        "botao_borda": "#8C7F66",
        "botao_hover": "#F1EBDD",
        "destaque": "#2E4A3B",
        "destaque_hover": "#1E3328",
        "texto_destaque": "#F5F0E6",
        "secundario_fundo": "#E6DFCF",
        "secundario_texto": "#2B2A26",
        "link": "#2E4A3B",
        "link_hover": "#1E3328",
        "enfase": "#7A4B2A",
        "alerta_fundo": "#FBF1DC",
        "alerta_borda": "#B7791F",
        "alerta_texto": "#7A4B2A",
        "sucesso_fundo": "#E4EBDD",
        "sucesso_texto": "#2E4A3B",
        "erro_fundo": "#F6E0DA",
        "erro_texto": "#8E2A1B",
        "barra_titulo": "#2E4A3B",
        "texto_barra_titulo": "#F5F0E6",
        "fonte": "Segoe UI",
        "fonte_titulo": "Georgia",
        "raio": 4,
        "raio_botao": 3,
        "altura_botao": 32,
    },
)

TEMAS = {t.id: t for t in (OFFWHITE, CLEAN, CLASSICO)}


def obter_tema(id_tema):
    """Tema pelo identificador; desconhecido ou vazio cai no padrão (Off-White)."""
    return TEMAS.get(id_tema or TEMA_PADRAO, TEMAS[TEMA_PADRAO])


def renderizar(texto, tema):
    """
    Troca cada `var(--token)` pelo valor do token no tema.
    Números viram pixels ("raio" -> "12px"). Token inexistente fica como está
    (o teste de temas acusa qualquer var(--...) que sobrar).
    """
    def _valor(m):
        if m.group(1) not in tema.tokens:
            return m.group(0)
        valor = tema.tokens[m.group(1)]
        return f"{valor}px" if isinstance(valor, int) else str(valor)
    return _RE_VAR.sub(_valor, texto)


def luminancia(cor_hex):
    """Luminância relativa (WCAG 2.1) de uma cor #RRGGBB."""
    canais = [int(cor_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(cor_a, cor_b):
    """Razão de contraste WCAG entre duas cores (1 a 21)."""
    la, lb = luminancia(cor_a), luminancia(cor_b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def barra_titulo_escura(tema):
    """True se a barra de título deve usar o modo escuro do Windows (texto claro)."""
    return luminancia(tema["barra_titulo"]) < 0.4


def cor_bgr(cor_hex):
    """#RRGGBB -> inteiro 0x00BBGGRR, formato COLORREF da API DWM."""
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    return (b << 16) | (g << 8) | r
