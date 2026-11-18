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
Temas visuais do iBirder (v1.6: paleta x modo).

A aparência tem duas escolhas independentes, salvas no config.json:
- paleta ("tema"): cores, fontes e raios (Off-White, Clean, Clássico, Gralha-azul, Sabiá,
  Alto contraste);
- modo ("modo"): "sistema" (segue o Windows), "claro" ou "escuro".

Paleta + modo efetivo (claro ou escuro) = um `Tema`, o conjunto de tokens que a interface
usa. Estilos (QSS) e HTML dos rótulos são escritos com `var(--token)` e renderizados para o
tema ativo por `renderizar()`; trocar paleta ou modo = renderizar de novo.

Cada paleta declara só as cores-base de cada modo; os demais tokens (hover, seleção,
botões, barra de título, estados) são derivados por `derivar_tokens()` e podem ser
sobrescritos pela própria paleta. As versões claras das três paletas da v1.4 continuam
declaradas por inteiro, sem derivação.

Funções sem Qt, para teste e reuso.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

TEMA_PADRAO = "offwhite"

# Modo efetivo de um tema e preferência salva no config.json
MODOS = ("claro", "escuro")
PREFERENCIAS_MODO = ("sistema", "claro", "escuro")
MODO_PADRAO = "sistema"
NOMES_MODO = {"sistema": "Igual ao Windows", "claro": "Claro", "escuro": "Escuro"}

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

# Cores-base que toda paleta declara em cada modo (o resto é derivado)
TOKENS_BASE = ("fundo", "superficie", "borda", "texto", "texto_secundario", "texto_suave", "destaque")

_RE_VAR = re.compile(r"var\(--([a-z_]+)\)")


@dataclass(frozen=True)
class Tema:
    """Uma paleta resolvida num modo: identificador da paleta, nome, tokens e logo."""
    id: str                        # id da paleta (o mesmo nos dois modos)
    nome: str
    descricao: str
    logo: str                      # arquivo em assets/ (logo original recolorido)
    tokens: dict = field(default_factory=dict)
    modo: str = "claro"

    def __getitem__(self, chave):
        return self.tokens[chave]

    @property
    def escuro(self):
        return self.modo == "escuro"


@dataclass(frozen=True)
class Paleta:
    """Cores-base de cada modo, estilo (fontes e raios) e logo de cada modo."""
    id: str
    nome: str
    descricao: str
    estilo: dict
    claro: dict
    escuro: dict
    logo_claro: str
    logo_escuro: str
    # Cores do logo em duotone (sombra, luz) por modo, usadas por tools/gerar_logos.py.
    # None = usa o arquivo como está (o logo original do Off-White claro).
    cores_logo: dict = field(default_factory=dict)
    contraste_minimo: float = 4.5

    def tema(self, modo="claro"):
        return _resolver(self.id, modo if modo in MODOS else "claro")


# ---------------------------------------------------------------- cores ------

def _rgb(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def misturar(cor_a, cor_b, t):
    """Cor a (t=0) até cor b (t=1), em sRGB. Basta para tons de hover e seleção."""
    a, b = _rgb(cor_a), _rgb(cor_b)
    return _hex(a[i] + (b[i] - a[i]) * t for i in range(3))


def luminancia(cor_hex):
    """Luminância relativa (WCAG 2.1) de uma cor #RRGGBB."""
    canais = [int(cor_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(cor_a, cor_b):
    """Razão de contraste WCAG entre duas cores (1 a 21)."""
    la, lb = luminancia(cor_a), luminancia(cor_b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _melhor_texto_sobre(fundo, opcoes):
    """Entre as cores candidatas, a de maior contraste sobre o fundo."""
    return max(opcoes, key=lambda c: contraste(c, fundo))


# Estados (aviso, sucesso, erro): um par por modo, igual em todas as paletas salvo exceção
ESTADOS = {
    "claro": {
        "alerta_fundo": "#FFFBEB", "alerta_borda": "#F59E0B", "alerta_texto": "#92400E",
        "sucesso_fundo": "#D1FAE5", "sucesso_texto": "#065F46",
        "erro_fundo": "#FEE2E2", "erro_texto": "#B91C1C",
    },
    "escuro": {
        "alerta_fundo": "#2E2410", "alerta_borda": "#D99A2B", "alerta_texto": "#F5C878",
        "sucesso_fundo": "#10291F", "sucesso_texto": "#86DDB5",
        "erro_fundo": "#35171A", "erro_texto": "#F6A9A9",
    },
}


def derivar_tokens(base, modo):
    """
    Completa as cores-base de uma paleta com os tokens derivados. O que a paleta já
    declarou não é tocado (as paletas da v1.4 declaram tudo no modo claro).
    """
    t = dict(ESTADOS[modo])
    t.update(base)
    faltando = [k for k in TOKENS_BASE if k not in t]
    if faltando:
        raise ValueError(f"Cores-base faltando: {faltando}")
    s, x = t["superficie"], t["texto"]
    padrao = {
        "superficie_alt": misturar(s, t["fundo"], 0.5),
        "borda_suave": misturar(t["borda"], s, 0.5),
        "titulo_sessao": t["texto_secundario"],
        "hover": misturar(s, x, 0.06),
        "selecao": misturar(s, t["destaque"], 0.16),
        "enfase": t["destaque"],
        "link": t["destaque"],
    }
    for k, v in padrao.items():
        t.setdefault(k, v)
    t.setdefault("destaque_hover", misturar(t["destaque"], x, 0.18))
    t.setdefault("texto_destaque", _melhor_texto_sobre(t["destaque"], ["#FFFFFF", t["fundo"], "#000000"]))
    t.setdefault("botao_fundo", s)
    t.setdefault("botao_texto", x)
    t.setdefault("botao_borda", t["borda"])
    t.setdefault("botao_hover", t["hover"])
    t.setdefault("secundario_fundo", misturar(s, x, 0.08))
    t.setdefault("secundario_texto", x)
    t.setdefault("link_hover", misturar(t["link"], x, 0.25))
    t.setdefault("barra_titulo", s)
    t.setdefault("texto_barra_titulo", x)
    return t


# -------------------------------------------------------------- paletas ------

_OFFWHITE_CLARO = {
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
}

_OFFWHITE_ESCURO = {
    "fundo": "#15171B",
    "superficie": "#1E2126",
    "borda": "#3A3F48",
    "texto": "#E6E8EB",
    "texto_secundario": "#B7BDC6",
    "texto_suave": "#9BA2AC",
    "destaque": "#D7DBE0",
    "texto_destaque": "#15171B",
    "botao_fundo": "#D7DBE0",
    "botao_texto": "#15171B",
    "botao_borda": "#D7DBE0",
    "botao_hover": "#F3F4F6",
    "destaque_hover": "#F3F4F6",
    "selecao": "#343941",
    "link": "#7DB9F2",
    "enfase": "#34D399",
    "barra_titulo": "#1E2126",
}

_CLEAN_CLARO = {
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
}

_CLEAN_ESCURO = {
    "fundo": "#0F1514",
    "superficie": "#17201F",
    "borda": "#2E3B39",
    "texto": "#E5EDEB",
    "texto_secundario": "#B2C1BE",
    "texto_suave": "#93A4A1",
    "titulo_sessao": "#C3D1CE",
    "destaque": "#3BB8A8",
    "destaque_hover": "#5EC9BB",
    "texto_destaque": "#04201C",
    "link": "#5EC9BB",
    "enfase": "#5EC9BB",
    "sucesso_fundo": "#12302C",
    "sucesso_texto": "#8EDFD3",
}

_CLASSICO_CLARO = {
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
}

_CLASSICO_ESCURO = {
    "fundo": "#1B1915",
    "superficie": "#25221D",
    "borda": "#4A4438",
    "texto": "#EDE6D8",
    "texto_secundario": "#CABFA9",
    "texto_suave": "#ADA28C",
    "titulo_sessao": "#E0AE87",
    "destaque": "#94BBA3",
    "destaque_hover": "#ADCDB9",
    "texto_destaque": "#14201A",
    "botao_borda": "#8C7F66",
    "link": "#A9CDB6",
    "enfase": "#E0AE87",
    "barra_titulo": "#1E3328",
    "texto_barra_titulo": "#F5F0E6",
}

_GRALHA_CLARO = {
    "fundo": "#F4F6FA",
    "superficie": "#FFFFFF",
    "borda": "#DBE1EA",
    "texto": "#0F172A",
    "texto_secundario": "#475569",
    "texto_suave": "#5E6B7E",
    "destaque": "#1D4ED8",
    "destaque_hover": "#1E40AF",
    "link": "#1D4ED8",
    "botao_borda": "#CBD3DF",
}

_GRALHA_ESCURO = {
    "fundo": "#0E1320",
    "superficie": "#161D2E",
    "borda": "#2C3651",
    "texto": "#E5EAF3",
    "texto_secundario": "#B4BED0",
    "texto_suave": "#97A3B8",
    "destaque": "#7FA6F8",
    "texto_destaque": "#0B1530",
    "link": "#9DBBFA",
}

_SABIA_CLARO = {
    "fundo": "#FAF6F2",
    "superficie": "#FFFFFF",
    "borda": "#E8DED4",
    "texto": "#231A13",
    "texto_secundario": "#5C4D40",
    "texto_suave": "#6F6054",
    "titulo_sessao": "#8A3A12",
    "destaque": "#A4461A",
    "destaque_hover": "#863712",
    "link": "#9A4116",
    "enfase": "#C2611F",
    "botao_borda": "#D9CBBD",
}

_SABIA_ESCURO = {
    "fundo": "#17120E",
    "superficie": "#211A15",
    "borda": "#3F342B",
    "texto": "#F1E8DF",
    "texto_secundario": "#CEC0B2",
    "texto_suave": "#AFA093",
    "titulo_sessao": "#F0A472",
    "destaque": "#E58A4E",
    "texto_destaque": "#2A1406",
    "link": "#F0A472",
    "enfase": "#E58A4E",
}

_CONTRASTE_CLARO = {
    "fundo": "#FFFFFF",
    "superficie": "#FFFFFF",
    "superficie_alt": "#F2F2F2",
    "borda": "#000000",
    "borda_suave": "#4D4D4D",
    "texto": "#000000",
    "texto_secundario": "#1A1A1A",
    "texto_suave": "#333333",
    "titulo_sessao": "#000000",
    "hover": "#E6E6E6",
    "selecao": "#FFF27A",
    "destaque": "#000000",
    "destaque_hover": "#262626",
    "texto_destaque": "#FFE600",
    "botao_fundo": "#FFFFFF",
    "botao_texto": "#000000",
    "botao_borda": "#000000",
    "secundario_fundo": "#E6E6E6",
    "link": "#0000B3",
    "link_hover": "#000066",
    "enfase": "#000000",
    "alerta_texto": "#5C2A00",
    "sucesso_texto": "#023B2B",
    "erro_texto": "#7A0000",
    "barra_titulo": "#000000",
    "texto_barra_titulo": "#FFE600",
}

_CONTRASTE_ESCURO = {
    "fundo": "#000000",
    "superficie": "#000000",
    "superficie_alt": "#141414",
    "borda": "#FFFFFF",
    "borda_suave": "#B3B3B3",
    "texto": "#FFFFFF",
    "texto_secundario": "#F2F2F2",
    "texto_suave": "#D9D9D9",
    "titulo_sessao": "#FFE600",
    "hover": "#262626",
    "selecao": "#3D3700",
    "destaque": "#FFE600",
    "destaque_hover": "#FFF27A",
    "texto_destaque": "#000000",
    "botao_fundo": "#000000",
    "botao_texto": "#FFFFFF",
    "botao_borda": "#FFFFFF",
    "secundario_fundo": "#262626",
    "link": "#FFE600",
    "link_hover": "#FFF27A",
    "enfase": "#FFE600",
    "alerta_fundo": "#1F1600", "alerta_texto": "#FFD86B",
    "sucesso_fundo": "#002417", "sucesso_texto": "#9BF0C8",
    "erro_fundo": "#2B0000", "erro_texto": "#FFB3B3",
    "barra_titulo": "#000000",
    "texto_barra_titulo": "#FFE600",
}

_SEGOE = {"fonte": "Segoe UI", "fonte_titulo": "Segoe UI", "raio": 12, "raio_botao": 8, "altura_botao": 26}
_FIGTREE = {"fonte": "Figtree", "fonte_titulo": "Figtree", "raio": 12, "raio_botao": 8, "altura_botao": 32}

PALETAS = {p.id: p for p in (
    Paleta(
        id="offwhite", nome="Off-White",
        descricao="O visual clássico do iBirder: cinza-grafite sobre fundo claro.",
        estilo=_SEGOE, claro=_OFFWHITE_CLARO, escuro=_OFFWHITE_ESCURO,
        logo_claro="logo_ave.svg", logo_escuro="temas/logo_offwhite_escuro.png",
        cores_logo={"escuro": ("#F3F4F6", "#6B7280")},
    ),
    Paleta(
        id="clean", nome="Clean",
        descricao="Leve e moderno: fonte Figtree e verde-petróleo só nas ações principais.",
        estilo=_FIGTREE, claro=_CLEAN_CLARO, escuro=_CLEAN_ESCURO,
        logo_claro="temas/logo_clean.png", logo_escuro="temas/logo_clean_escuro.png",
        cores_logo={"claro": ("#134E4A", "#E6F4F1"), "escuro": ("#D5F2EC", "#3BB8A8")},
    ),
    Paleta(
        id="classico", nome="Clássico",
        descricao="Inspirado nos guias de campo: papel creme, títulos com serifa e verde-musgo.",
        estilo={"fonte": "Segoe UI", "fonte_titulo": "Georgia", "raio": 4, "raio_botao": 3, "altura_botao": 32},
        claro=_CLASSICO_CLARO, escuro=_CLASSICO_ESCURO,
        logo_claro="temas/logo_classico.png", logo_escuro="temas/logo_classico_escuro.png",
        cores_logo={"claro": ("#2E4A3B", "#F5F0E6"), "escuro": ("#F5F0E6", "#94BBA3")},
    ),
    Paleta(
        id="gralha", nome="Gralha-azul",
        descricao="Azul da gralha-azul, ave símbolo do Paraná, sobre fundo neutro.",
        estilo=_FIGTREE, claro=_GRALHA_CLARO, escuro=_GRALHA_ESCURO,
        logo_claro="temas/logo_gralha.png", logo_escuro="temas/logo_gralha_escuro.png",
        cores_logo={"claro": ("#1E3A8A", "#E8EEFC"), "escuro": ("#E5EAF3", "#7FA6F8")},
    ),
    Paleta(
        id="sabia", nome="Sabiá",
        descricao="Ferrugem do peito do sabiá-laranjeira, sobre fundo areia.",
        estilo=_FIGTREE, claro=_SABIA_CLARO, escuro=_SABIA_ESCURO,
        logo_claro="temas/logo_sabia.png", logo_escuro="temas/logo_sabia_escuro.png",
        cores_logo={"claro": ("#6B2C0E", "#FBEDE3"), "escuro": ("#F1E8DF", "#E58A4E")},
    ),
    Paleta(
        id="contraste", nome="Alto contraste",
        descricao="Preto, branco e amarelo, para baixa visão (contraste mínimo de 7:1).",
        estilo={"fonte": "Segoe UI", "fonte_titulo": "Segoe UI", "raio": 6, "raio_botao": 4, "altura_botao": 32},
        claro=_CONTRASTE_CLARO, escuro=_CONTRASTE_ESCURO,
        logo_claro="temas/logo_contraste.png", logo_escuro="temas/logo_contraste_escuro.png",
        cores_logo={"claro": ("#000000", "#FFFFFF"), "escuro": ("#FFFFFF", "#FFE600")},
        contraste_minimo=7.0,
    ),
)}


@lru_cache(maxsize=None)
def _resolver(id_paleta, modo):
    p = PALETAS[id_paleta]
    tokens = derivar_tokens(p.claro if modo == "claro" else p.escuro, modo)
    tokens.update(p.estilo)
    logo = p.logo_claro if modo == "claro" else p.logo_escuro
    return Tema(id=p.id, nome=p.nome, descricao=p.descricao, logo=logo, tokens=tokens, modo=modo)


# Compatibilidade (v1.4): temas claros por id
TEMAS = {id_paleta: _resolver(id_paleta, "claro") for id_paleta in PALETAS}

# Todas as combinações paleta x modo (para testes e prévias)
COMBINACOES = [_resolver(i, m) for i in PALETAS for m in MODOS]


def obter_tema(id_tema, modo="claro"):
    """Tema pela paleta e pelo modo efetivo; paleta desconhecida ou vazia cai no padrão."""
    id_paleta = id_tema if id_tema in PALETAS else TEMA_PADRAO
    return _resolver(id_paleta, modo if modo in MODOS else "claro")


def normalizar_preferencia_modo(valor):
    """Preferência de modo do config.json; valor desconhecido vira o padrão (sistema)."""
    return valor if valor in PREFERENCIAS_MODO else MODO_PADRAO


def modo_efetivo(preferencia, sistema_escuro):
    """'claro' ou 'escuro' a partir da preferência salva e do modo do sistema."""
    preferencia = normalizar_preferencia_modo(preferencia)
    if preferencia == "sistema":
        return "escuro" if sistema_escuro else "claro"
    return preferencia


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


def barra_titulo_escura(tema):
    """True se a barra de título deve usar o modo escuro do Windows (texto claro)."""
    return luminancia(tema["barra_titulo"]) < 0.4


def cor_bgr(cor_hex):
    """#RRGGBB -> inteiro 0x00BBGGRR, formato COLORREF da API DWM."""
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    return (b << 16) | (g << 8) | r
