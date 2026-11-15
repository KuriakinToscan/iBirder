#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Avaliação da IA local com fotos de espécie conhecida (sem abrir a interface do iBirder).

Para cada foto, roda o modelo local três vezes (esticada, esticada e espelhada, com borda) e
compara estas variantes ("modos"):
  - "espremida": a foto inteira esticada para 224x224, sem recorte, com as 965 espécies (referência);
  - "espelho": média das probabilidades da foto esticada e da espelhada na horizontal (TTA);
  - "brasil": só as espécies com registro no Brasil (assets/conservacao/aves_registradas_brasil.csv),
    com as probabilidades renormalizadas entre elas (prior geográfico simples; o que o app usa
    para fotos do Brasil e, por padrão, sem GPS);
  - "espelho+brasil": as duas coisas juntas;
  - "borda": proporção preservada e borda cinza até 224x224 (letterbox, só para comparação).
e registra em que posição a espécie correta aparece no ranking de cada modo.

Com --bioclip, compara também o BioCLIP (imageomics/bioclip, ViT-B/16, licença MIT), sem treino
(zero-shot), entre as espécies registradas no Brasil e com a foto inteira esticada (sem recorte):
  - "bioclip": textos "a photo of <nome científico>.";
  - "bioclip-misto": nome científico e nome em inglês do eBird;
  - "bioclip-fp16": como "bioclip-misto", com os pesos do codificador de imagem em FP16;
  - "bioclip-int8": como "bioclip-misto", com as matrizes de peso em INT8 por canal de saída (só os
    pesos; o resto em FP16), o formato que caberia no limite de 100 MB.
As duas últimas simulam o arredondamento dos pesos (a conta roda em FP32): medem o acerto que o
formato comprimido teria; o tamanho é o do arquivo nesse formato.
Exige, só no ambiente de teste: pip install open_clip_torch torch torchvision (o primeiro uso
baixa ~600 MB do Hugging Face). O relatório traz o tempo médio por foto e o tamanho do modelo.

Com --bioclip-litert <pasta>, roda o BioCLIP já convertido para LiteRT por
tools/converter_bioclip_litert.py (só com o ai-edge-litert do app, sem torch), como o app rodaria:
  - "litert-int8": pesos INT8 por canal, conta em FP32;
  - "litert-int8d": INT8 dinâmico (ativações quantizadas na hora, mais rápido);
  - "litert-fp32": só se a pasta tiver o .tflite FP32.
Aqui o tempo e o tamanho são os reais do arquivo .tflite.

De onde vem a espécie correta (a "verdade"):
  - com --csv: planilha com as colunas "arquivo" e "especie" (nome científico ou nome em inglês do eBird);
  - sem --csv: o nome científico que o iBirder gravou na foto (iBirder|Taxonomia|ScientificName).
    ATENÇÃO: use só fotos cuja espécie você conferiu. Se a espécie gravada veio da própria IA
    sem conferência, a avaliação fica viciada a favor do modelo.

Relatório:
  - acerto top-1 e top-3, com intervalo de confiança de 95% (Wilson), no total e só entre as
    espécies que o modelo conhece (965 espécies; ~230 ocorrem no Brasil);
  - cada modo contra a referência "espremida", nas mesmas fotos (teste exato de McNemar);
  - tabela de limiares de confiança: fração das fotos aceitas sem nuvem e acerto entre elas,
    com o menor limiar que atinge a precisão alvo (--precisao-alvo, padrão 0,90).

Uso (na pasta do iBirder, no ambiente conda "ibirder-teste"):
    python tools/avaliar_identificacao.py "D:\\Fotos\\Aves conferidas"
    python tools/avaliar_identificacao.py "D:\\Fotos" --recursivo
    python tools/avaliar_identificacao.py "D:\\Fotos" --csv especies.csv
    python tools/avaliar_identificacao.py "D:\\amostra_inat" --baixar-inat 300   # amostra do iNaturalist

Saídas (nada sai do computador; nenhuma foto é alterada):
    tools/relatorio_avaliacao.txt   resumo para enviar de volta
    tools/avaliacao_por_foto.csv    uma linha por foto e modo (sem caminho completo, só o nome)
"""

import argparse
import csv
import logging
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

EXTENSOES = (".jpg", ".jpeg", ".png")
REFERENCIA = "espremida"
MODOS_BIOCLIP = ("bioclip", "bioclip-misto", "bioclip-fp16", "bioclip-int8")
MODOS_LITERT = ("litert-int8", "litert-int8d", "litert-mundo", "litert-fp32")
BIOCLIP_HUB = "hf-hub:imageomics/bioclip"
MODOS = ("espremida", "espelho", "brasil", "espelho+brasil", "borda")
LIMIARES = [round(0.30 + 0.05 * i, 2) for i in range(14)]  # 0,30 a 0,95
SAIDA_RELATORIO = RAIZ / "tools" / "relatorio_avaliacao.txt"
SAIDA_CSV = RAIZ / "tools" / "avaliacao_por_foto.csv"


# ------------------------------------------------------------------ estatística (sem dependências)

def wilson(acertos: int, n: int, z: float = 1.959964) -> Tuple[float, float]:
    """Intervalo de confiança de Wilson (95%) para uma proporção. (0, 0) se n = 0."""
    if n <= 0:
        return 0.0, 0.0
    p = acertos / n
    denominador = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denominador
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominador
    return max(0.0, centro - margem), min(1.0, centro + margem)


def mcnemar_exato(so_a: int, so_b: int) -> float:
    """
    Valor-p bilateral do teste exato de McNemar: ``so_a`` fotos que só o modo A acertou e
    ``so_b`` que só o B acertou (binomial com p = 0,5 nos pares discordantes).
    """
    n = so_a + so_b
    if n == 0:
        return 1.0
    k = min(so_a, so_b)
    cauda = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * cauda)


# ------------------------------------------------------------------ dados

@dataclass
class Resultado:
    """Predição de um modo para uma foto."""
    arquivo: str
    verdade: str
    modo: str
    top: List[Tuple[str, float]]       # (espécie, confiança) em ordem decrescente
    posicao: Optional[int]             # 1 = top-1; None se a espécie não está no ranking guardado
    conhecida: bool                    # a espécie correta está entre as classes do modelo

    @property
    def confianca(self) -> float:
        return self.top[0][1] if self.top else 0.0

    def acertou(self, k: int) -> bool:
        return self.posicao is not None and self.posicao <= k


@dataclass
class Metricas:
    n: int = 0
    top1: int = 0
    top3: int = 0
    conhecidas: int = 0
    top1_conhecidas: int = 0
    top3_conhecidas: int = 0
    por_arquivo: Dict[str, bool] = field(default_factory=dict)


def calcular_metricas(resultados: Iterable[Resultado]) -> Metricas:
    m = Metricas()
    for r in resultados:
        m.n += 1
        m.top1 += r.acertou(1)
        m.top3 += r.acertou(3)
        m.por_arquivo[r.arquivo] = r.acertou(1)
        if r.conhecida:
            m.conhecidas += 1
            m.top1_conhecidas += r.acertou(1)
            m.top3_conhecidas += r.acertou(3)
    return m


def analisar_limiares(resultados: Sequence[Resultado], limiares: Sequence[float] = LIMIARES):
    """[(limiar, aceitas, acertos entre as aceitas)] — aceitas = confiança do top-1 >= limiar."""
    tabela = []
    for t in limiares:
        aceitas = [r for r in resultados if r.confianca >= t]
        tabela.append((t, len(aceitas), sum(r.acertou(1) for r in aceitas)))
    return tabela


def limiar_sugerido(tabela, precisao_alvo: float, minimo_aceitas: int = 10) -> Optional[float]:
    """Menor limiar cuja precisão entre as aceitas atinge o alvo (com pelo menos ``minimo_aceitas`` fotos)."""
    for t, aceitas, acertos in tabela:
        if aceitas >= minimo_aceitas and acertos / aceitas >= precisao_alvo:
            return t
    return None


# ------------------------------------------------------------------ verdade (espécie correta)

def especie_canonica(nome: str) -> Optional[str]:
    """Nome científico (gênero + espécie) na grafia do catálogo eBird; aceita nome em inglês."""
    from core.catalogo_especies import resolver_nome
    if not nome or not nome.strip():
        return None
    canonico = resolver_nome(nome)
    if canonico:
        return canonico
    partes = nome.split()
    return f"{partes[0].capitalize()} {partes[1].lower()}" if len(partes) >= 2 else None


def ler_csv_verdade(caminho: Path) -> Dict[str, str]:
    """{nome do arquivo em minúsculas: espécie} a partir das colunas 'arquivo' e 'especie' (; ou ,)."""
    texto = caminho.read_text(encoding="utf-8-sig")
    dialeto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;\t")
    leitor = csv.DictReader(texto.splitlines(), dialect=dialeto)
    colunas = {c.lower().strip(): c for c in (leitor.fieldnames or [])}
    if "arquivo" not in colunas or "especie" not in colunas:
        raise ValueError(f"{caminho.name}: a planilha precisa das colunas 'arquivo' e 'especie'.")
    verdade = {}
    for linha in leitor:
        # PureWindowsPath aceita \ e /: a coluna pode trazer o caminho completo do Windows
        arquivo = PureWindowsPath((linha[colunas["arquivo"]] or "").strip()).name.lower()
        especie = (linha[colunas["especie"]] or "").strip()
        if arquivo and especie:
            verdade[arquivo] = especie
    return verdade


def verdade_gravada(caminho: Path) -> Optional[str]:
    """Nome científico gravado pelo iBirder na foto, ou None."""
    from modules.step6_persistence.registro_ibirder import ler_registro
    registro = ler_registro(caminho)
    if not registro:
        return None
    return registro["dados"].get(("Taxonomia", "ScientificName"))


def listar_fotos(pasta: Path, recursivo: bool) -> List[Path]:
    padrao = "**/*" if recursivo else "*"
    return sorted(p for p in pasta.glob(padrao) if p.is_file() and p.suffix.lower() in EXTENSOES)


# ------------------------------------------------------------------ modelo

class Modelo:
    """MobileNetV2 "Birds V1" (IA local até a v1.4; hoje referência), com rótulos 'Gênero espécie'."""

    def __init__(self):
        from core.model_manager import ModelManager
        from modules.step1_identity.id_worker import formatar_rotulo, tflite
        if tflite is None:
            raise RuntimeError("LiteRT (ai-edge-litert) não está instalado neste ambiente.")
        manager = ModelManager()
        if not (manager.model_path.is_file() and manager.labels_path.is_file()):
            raise RuntimeError(f"MobileNetV2 (referência) não encontrado em {manager.assets_dir}.")
        self.interpretador = tflite.Interpreter(model_path=str(manager.model_path))
        self.interpretador.allocate_tensors()
        self.entrada = self.interpretador.get_input_details()[0]
        self.saida = self.interpretador.get_output_details()[0]
        self.altura, self.largura = int(self.entrada["shape"][1]), int(self.entrada["shape"][2])
        with open(manager.labels_path, encoding="utf-8") as f:
            linhas = [linha.strip() for linha in f if linha.strip()]
        self.rotulos = [formatar_rotulo(linha.split(",", 1)[1] if "," in linha else linha) for linha in linhas]
        self.especies = set(self.rotulos)
        self.tempo_s, self.fotos = 0.0, 0  # só a rede, no modo do app (sem abrir a foto)
        self.tamanho_mb = manager.model_path.stat().st_size / 1e6

    def imagem(self, caminho: Path, modo: str):
        """Entrada do modelo: "borda" (letterbox), "espremida" (esticada) ou "espelhada" (esticada e espelhada)."""
        from PIL import ImageOps
        from modules.step1_identity.preprocessamento import abrir_reduzida, esticar, letterbox
        img = abrir_reduzida(caminho)
        if modo == "borda":
            return letterbox(img, self.largura, self.altura)
        esticada = esticar(img, self.largura, self.altura)
        return ImageOps.mirror(esticada) if modo == "espelhada" else esticada

    def probabilidades(self, imagem):
        """Vetor de probabilidades (uma por rótulo) para uma imagem já no tamanho da entrada."""
        import numpy as np
        dados = np.array(imagem, dtype=self.entrada["dtype"])
        if self.entrada["dtype"] == np.float32:
            dados = (dados - 127.5) / 127.5
        self.interpretador.set_tensor(self.entrada["index"], np.expand_dims(dados, 0))
        self.interpretador.invoke()
        saida = np.squeeze(self.interpretador.get_tensor(self.saida["index"])).astype(np.float64)
        if self.saida["dtype"] == np.uint8:
            saida = saida / 255.0
        return saida

    def rankings(self, caminho: Path, permitidas: Optional[set] = None) -> Dict[str, List[Tuple[str, float]]]:
        """Ranking de cada modo de ``MODOS`` (três inferências por foto)."""
        imagem = self.imagem(caminho, "espremida")
        inicio = time.perf_counter()
        esticada = self.probabilidades(imagem)
        self.tempo_s += time.perf_counter() - inicio
        self.fotos += 1
        media = (esticada + self.probabilidades(self.imagem(caminho, "espelhada"))) / 2
        borda = self.probabilidades(self.imagem(caminho, "borda"))
        return {
            "espremida": ranking_por_especie(self.rotulos, esticada),
            "espelho": ranking_por_especie(self.rotulos, media),
            "brasil": ranking_por_especie(self.rotulos, esticada, permitidas),
            "espelho+brasil": ranking_por_especie(self.rotulos, media, permitidas),
            "borda": ranking_por_especie(self.rotulos, borda),
        }


def ranking_por_especie(rotulos: Sequence[str], saida, permitidas: Optional[set] = None) -> List[Tuple[str, float]]:
    """O mesmo ranking do app (id_worker.ranking_por_especie); ``permitidas`` em minúsculas."""
    from modules.step1_identity.id_worker import ranking_por_especie as ranking_do_app
    return ranking_do_app(rotulos, saida, permitidas)


def especies_brasil() -> set:
    """Espécies (gênero + espécie, em minúsculas) com registro no Brasil, da lista embarcada."""
    from modules.step3_geography.listas_conservacao import especies_registradas_brasil
    return especies_registradas_brasil()


class ModeloBioclip:
    """
    BioCLIP zero-shot: compara o embedding da foto com o de um texto por espécie candidata.
    A foto é aberta reduzida e esticada para 224x224 como no app (sem o recorte central padrão
    do open_clip) e normalizada com a média e o desvio do CLIP.
    """

    def __init__(self, especies: Sequence[str], nomes_ingles: Optional[Dict[str, str]] = None,
                 nome_modelo: str = BIOCLIP_HUB, pretrained: Optional[str] = None):
        import copy
        import open_clip
        import torch
        self.torch = torch
        logging.info(f"Carregando o BioCLIP ({nome_modelo}); o primeiro uso baixa ~600 MB...")
        self.modelo, _, _ = open_clip.create_model_and_transforms(nome_modelo, pretrained=pretrained)
        self.modelo.eval()
        tokenizador = open_clip.get_tokenizer(nome_modelo)
        self.especies = list(especies)
        self.conjunto = set(self.especies)
        self.media = torch.tensor(open_clip.OPENAI_DATASET_MEAN).view(3, 1, 1)
        self.desvio = torch.tensor(open_clip.OPENAI_DATASET_STD).view(3, 1, 1)
        self.escala = float(self.modelo.logit_scale.detach().exp().item())
        textos = {
            "bioclip": textos_bioclip(self.especies, nomes_ingles, misto=False),
            "bioclip-misto": textos_bioclip(self.especies, nomes_ingles, misto=True),
        }
        self.embeddings_texto = {modo: self._codificar_textos(tokenizador, lista) for modo, lista in textos.items()}
        self.visual_fp16, mb_fp16 = comprimir_pesos(copy.deepcopy(self.modelo.visual), "fp16")
        self.visual_int8, mb_int8 = comprimir_pesos(copy.deepcopy(self.modelo.visual), "int8")
        self.tamanho_mb = {"bioclip": _tamanho_mb(self.modelo.visual), "bioclip-fp16": mb_fp16,
                           "bioclip-int8": mb_int8}
        self.tempo_s = {"bioclip": 0.0}
        self.fotos = 0

    def _codificar_textos(self, tokenizador, textos: List[str], lote: int = 256):
        torch = self.torch
        partes = []
        with torch.no_grad():
            for i in range(0, len(textos), lote):
                emb = self.modelo.encode_text(tokenizador(textos[i:i + lote]))
                partes.append(emb / emb.norm(dim=-1, keepdim=True))
        return torch.cat(partes)

    def _tensor(self, caminho: Path):
        import numpy as np
        from modules.step1_identity.preprocessamento import abrir_reduzida, esticar
        torch = self.torch
        img = esticar(abrir_reduzida(caminho), 224, 224)
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
        return ((x - self.media) / self.desvio).unsqueeze(0)

    def _ranking(self, embedding, embeddings_texto) -> List[Tuple[str, float]]:
        emb = embedding / embedding.norm(dim=-1, keepdim=True)
        probabilidades = (self.escala * emb @ embeddings_texto.T).softmax(dim=-1).squeeze(0).tolist()
        return sorted(zip(self.especies, probabilidades), key=lambda item: item[1], reverse=True)

    def rankings(self, caminho: Path) -> Dict[str, List[Tuple[str, float]]]:
        torch = self.torch
        x = self._tensor(caminho)
        with torch.no_grad():
            inicio = time.perf_counter()
            emb = self.modelo.encode_image(x)
            self.tempo_s["bioclip"] += time.perf_counter() - inicio
            emb16 = self.visual_fp16(x)
            emb8 = self.visual_int8(x)
        self.fotos += 1
        return {
            "bioclip": self._ranking(emb, self.embeddings_texto["bioclip"]),
            "bioclip-misto": self._ranking(emb, self.embeddings_texto["bioclip-misto"]),
            "bioclip-fp16": self._ranking(emb16, self.embeddings_texto["bioclip-misto"]),
            "bioclip-int8": self._ranking(emb8, self.embeddings_texto["bioclip-misto"]),
        }


def textos_bioclip(especies: Sequence[str], nomes_ingles: Optional[Dict[str, str]] = None,
                   misto: bool = True) -> List[str]:
    """Texto de cada espécie para o BioCLIP: só o nome científico, ou com o nome em inglês (misto)."""
    nomes_ingles = nomes_ingles or {}
    if not misto:
        return [f"a photo of {sp}." for sp in especies]
    return [f"a photo of {sp} with common name {nomes_ingles[sp]}." if nomes_ingles.get(sp)
            else f"a photo of {sp}." for sp in especies]


class ModeloBioclipLitert:
    """
    BioCLIP convertido para LiteRT (tools/converter_bioclip_litert.py), rodado pelo mesmo código do
    app (modules/step1_identity/bioclip.py): foto inteira esticada para 224x224, RGB de 0 a 1.
    Modos "litert-*" entre as aves do Brasil; "litert-mundo" (INT8 dinâmico) entre todas as espécies
    do catálogo, como o app faz com fotos de GPS fora do Brasil.
    """

    ARQUIVOS = {"litert-int8": "bioclip_imagem_int8.tflite", "litert-int8d": "bioclip_imagem_int8d.tflite",
                "litert-fp32": "bioclip_imagem_fp32.tflite"}

    def __init__(self, pasta: Path, threads: Optional[int] = None):
        from modules.step1_identity.bioclip import ClassificadorBioclip
        from modules.step1_identity.id_worker import tflite
        if tflite is None:
            raise RuntimeError("LiteRT (ai-edge-litert) não está instalado neste ambiente.")
        pasta = Path(pasta)
        self.classificadores = {}
        self.tamanho_mb: Dict[str, float] = {}
        for modo, nome in self.ARQUIVOS.items():
            caminho = pasta / nome
            if caminho.is_file():
                self.classificadores[modo] = ClassificadorBioclip(pasta, tflite.Interpreter, threads, nome)
                self.tamanho_mb[modo] = caminho.stat().st_size / 1e6
        if not self.classificadores:
            raise FileNotFoundError(f"Nenhum bioclip_imagem_*.tflite em {pasta}.")
        base = next(iter(self.classificadores.values()))
        self.threads = base.threads
        self.especies = [base.especies[i] for i in base.indices_brasil]
        self.conjunto = set(self.especies)
        self.total_mundo = len(base.especies)
        self.tempo_s = {modo: 0.0 for modo in self.classificadores}
        self.fotos = 0

    @staticmethod
    def entrada(caminho: Path):
        """Foto aberta reduzida, esticada para 224x224, float32 [1,224,224,3] de 0 a 1."""
        from modules.step1_identity.bioclip import ClassificadorBioclip
        from modules.step1_identity.preprocessamento import abrir_reduzida, esticar
        return ClassificadorBioclip.preparar(esticar(abrir_reduzida(caminho), 224, 224))

    def rankings(self, caminho: Path) -> Dict[str, List[Tuple[str, float]]]:
        x = self.entrada(caminho)
        resultado = {}
        for modo, classificador in self.classificadores.items():
            inicio = time.perf_counter()
            emb = classificador.embedding(x)
            self.tempo_s[modo] += time.perf_counter() - inicio
            resultado[modo] = classificador.ranking(emb, so_brasil=True)
            if modo == "litert-int8d":
                resultado["litert-mundo"] = classificador.ranking(emb, so_brasil=False)
        self.fotos += 1
        return resultado


def comprimir_pesos(modulo, formato: str):
    """
    Arredonda os pesos de ``modulo`` como se fossem guardados em ``formato`` e devolve
    (módulo, tamanho em MB nesse formato):
      - "fp16": todos os parâmetros em meia precisão (2 bytes);
      - "int8": matrizes de peso (Linear, Conv e projeções da atenção) em INT8 simétrico por canal de
        saída, com uma escala FP16 por canal; os demais parâmetros em FP16.
    """
    import torch
    total_bytes = 0
    with torch.no_grad():
        for nome, parametro in modulo.named_parameters():
            matriz = parametro.ndim >= 2 and nome.split(".")[-1].endswith("weight")
            if formato == "int8" and matriz:
                linhas = parametro.reshape(parametro.shape[0], -1)
                escala = (linhas.abs().amax(dim=1, keepdim=True) / 127).clamp(min=1e-12)
                quantizada = (linhas / escala).round().clamp(-127, 127) * escala
                parametro.copy_(quantizada.reshape(parametro.shape))
                total_bytes += parametro.numel() + 2 * parametro.shape[0]
            else:
                parametro.copy_(parametro.half().float())
                total_bytes += 2 * parametro.numel()
    return modulo, total_bytes / 1e6


def _tamanho_mb(modulo) -> float:
    """Tamanho do state_dict serializado (aproxima o arquivo que iria para o app)."""
    import io
    import torch
    buffer = io.BytesIO()
    torch.save(modulo.state_dict(), buffer)
    return buffer.tell() / 1e6


def candidatas_bioclip() -> Tuple[List[str], Dict[str, str]]:
    """
    Espécies registradas no Brasil, na grafia do catálogo eBird quando houver (a mesma da espécie
    correta), e o nome em inglês de cada uma.
    """
    from core.catalogo_especies import carregar
    especies, ingles = [], {}
    for item in carregar():
        if item["no_brasil"]:
            nome = " ".join(item["nome_cientifico"].split()[:2])
            if nome not in ingles:
                especies.append(nome)
                ingles[nome] = item.get("nome_ingles", "")
    return especies, ingles


def candidatas_mundo() -> Tuple[List[str], Dict[str, str], List[bool]]:
    """
    Todas as espécies do catálogo (eBird embarcado + registradas no Brasil), na ordem do catálogo:
    (espécies, nomes em inglês, tem registro no Brasil). Para fotos com GPS fora do Brasil.
    """
    from core.catalogo_especies import carregar
    especies, ingles, brasil = [], {}, []
    indice = {}
    for item in carregar():
        nome = " ".join(item["nome_cientifico"].split()[:2])
        if nome in indice:
            brasil[indice[nome]] = brasil[indice[nome]] or bool(item["no_brasil"])
            continue
        indice[nome] = len(especies)
        especies.append(nome)
        ingles[nome] = item.get("nome_ingles", "")
        brasil.append(bool(item["no_brasil"]))
    return especies, ingles, brasil


def avaliar_foto(modelo: Modelo, caminho: Path, verdade: str, guardar: int = 10,
                 permitidas: Optional[set] = None, bioclip: Optional[ModeloBioclip] = None,
                 litert: Optional[ModeloBioclipLitert] = None) -> List[Resultado]:
    resultados = []
    rankings = [(modelo.rankings(caminho, permitidas), modelo.especies)]
    if bioclip is not None:
        rankings.append((bioclip.rankings(caminho), bioclip.conjunto))
    if litert is not None:
        rankings.append((litert.rankings(caminho), litert.conjunto))
    for por_modo, conhecidas in rankings:
        for modo, ranking in por_modo.items():
            nomes = [nome for nome, _ in ranking]
            posicao = nomes.index(verdade) + 1 if verdade in nomes else None
            resultados.append(Resultado(caminho.name, verdade, modo, ranking[:guardar], posicao,
                                        verdade in conhecidas))
    return resultados


# ------------------------------------------------------------------ relatório

def _pct(acertos: int, n: int) -> str:
    if n == 0:
        return "    -"
    baixo, alto = wilson(acertos, n)
    return f"{100 * acertos / n:5.1f}% (IC95% {100 * baixo:.1f}-{100 * alto:.1f}%)"


DESCRICAO_MODOS = {
    "espremida": "sem prior, como até a v1.4",
    "espelho": "média com a foto espelhada",
    "brasil": "só espécies do Brasil, o que o app usa",
    "espelho+brasil": "espelho e só Brasil",
    "borda": "letterbox, só comparação",
    "bioclip": "BioCLIP zero-shot, nomes científicos, aves do Brasil",
    "bioclip-misto": "BioCLIP zero-shot, nome científico + inglês",
    "bioclip-fp16": "BioCLIP misto com pesos em FP16",
    "bioclip-int8": "BioCLIP misto com pesos em INT8 por canal",
    "litert-int8": "BioCLIP em LiteRT, pesos INT8, conta em FP32",
    "litert-int8d": "BioCLIP em LiteRT, INT8 dinâmico, o que o app usa",
    "litert-mundo": "BioCLIP em LiteRT, INT8 dinâmico, todas as ~11 mil espécies (GPS fora do Brasil)",
    "litert-fp32": "BioCLIP em LiteRT, FP32",
}


def _tabela_limiar(resultados: Sequence[Resultado], modo: str, n: int, precisao_alvo: float,
                   limiar_atual: float) -> List[str]:
    """Linhas da tabela de limiares de um modo, com o limiar atual marcado e o sugerido."""
    tabela = analisar_limiares(resultados)
    sugerido = limiar_sugerido(tabela, precisao_alvo)
    linhas = [f"== Limiar de confiança (modo {modo}: {DESCRICAO_MODOS.get(modo, modo)}) ==",
              "  Aceitas = confiança do top-1 >= limiar. Com nuvem configurada o app sempre a consulta;",
              "  sem nuvem, abaixo do piso marcado a identificação é inconclusiva.",
              "  Limiar | Aceitas        | Acerto entre as aceitas"]
    for t, aceitas, acertos in tabela:
        marca = "  <- piso da sugestão offline" if abs(t - limiar_atual) < 1e-9 else ""
        linhas.append(f"  {t:6.2f} | {aceitas:4d} ({100 * aceitas / max(n, 1):5.1f}%) | {_pct(acertos, aceitas)}{marca}")
    linhas.append("")
    if sugerido is None:
        linhas.append(f"  Nenhum limiar atingiu {100 * precisao_alvo:.0f}% de acerto com 10 fotos ou mais.")
    else:
        linhas.append(f"  Menor limiar com acerto >= {100 * precisao_alvo:.0f}%: {sugerido:.2f}")
    return linhas + [""]


def comparar_com_referencia(m: Metricas, ref: Metricas) -> Tuple[int, int, float]:
    """(fotos que só o modo acertou, fotos que só a referência acertou, valor-p de McNemar) no top-1."""
    so_modo = sum(1 for k, ok in m.por_arquivo.items() if ok and not ref.por_arquivo.get(k))
    so_ref = sum(1 for k, ok in ref.por_arquivo.items() if ok and not m.por_arquivo.get(k))
    return so_modo, so_ref, mcnemar_exato(so_modo, so_ref)


def montar_relatorio(resultados: List[Resultado], ignoradas: Dict[str, int], precisao_alvo: float,
                     duracao_s: float, limiar_atual: float = 0.30, fora_do_brasil: int = 0,
                     custos: Optional[List[Tuple[str, float, float]]] = None) -> str:
    from core.config import APP_VERSION
    linhas = [f"Avaliação da IA local do iBirder (v{APP_VERSION}) - {time.strftime('%d/%m/%Y %H:%M')}",
              f"Duração: {duracao_s:.0f} s", ""]
    modos = [modo for modo in MODOS + MODOS_BIOCLIP + MODOS_LITERT if any(r.modo == modo for r in resultados)]
    por_modo = {modo: [r for r in resultados if r.modo == modo] for modo in modos}
    metricas = {modo: calcular_metricas(lista) for modo, lista in por_modo.items()}
    ref = metricas[REFERENCIA]
    n = ref.n
    linhas.append(f"Fotos avaliadas: {n}")
    for motivo, quantidade in ignoradas.items():
        if quantidade:
            linhas.append(f"Fotos ignoradas ({motivo}): {quantidade}")
    especies = {r.verdade for r in por_modo[REFERENCIA]}
    linhas.append(f"Espécies diferentes: {len(especies)}; conhecidas pelo modelo: {ref.conhecidas} fotos de {n}")
    if fora_do_brasil:
        linhas.append(f"Fotos cuja espécie correta não está na lista do Brasil (o modo 'brasil' nunca acerta): "
                      f"{fora_do_brasil}")
    linhas.append("")

    for modo in modos:
        m = metricas[modo]
        linhas += [f"== Modo {modo} ({DESCRICAO_MODOS.get(modo, modo)}) ==",
                   f"  Top-1, todas as fotos:            {_pct(m.top1, m.n)}",
                   f"  Top-3, todas as fotos:            {_pct(m.top3, m.n)}",
                   f"  Top-1, só espécies conhecidas:    {_pct(m.top1_conhecidas, m.conhecidas)}",
                   f"  Top-3, só espécies conhecidas:    {_pct(m.top3_conhecidas, m.conhecidas)}", ""]

    linhas += [f"== Cada modo x {REFERENCIA} (top-1, mesmas fotos; teste exato de McNemar) ==",
               "  Modo            | Só o modo acertou | Só a referência acertou | p"]
    for modo in modos:
        if modo == REFERENCIA:
            continue
        so_modo, so_ref, p = comparar_com_referencia(metricas[modo], ref)
        marca = "  (significativo a 5%)" if p < 0.05 else ""
        linhas.append(f"  {modo:<15} | {so_modo:17d} | {so_ref:23d} | {p:.3f}{marca}")
    linhas.append("")

    # O LiteRT deve reproduzir o BioCLIP do PyTorch: compara nas mesmas fotos quando os dois rodaram
    litert = [modo for modo in MODOS_LITERT if modo in metricas]
    if litert and "bioclip-misto" in metricas:
        linhas += ["== LiteRT x bioclip-misto (PyTorch FP32; top-1, mesmas fotos; McNemar) ==",
                   "  Modo            | Só o LiteRT acertou | Só o PyTorch acertou | p"]
        for modo in litert:
            so_modo, so_ref, p = comparar_com_referencia(metricas[modo], metricas["bioclip-misto"])
            marca = "  (significativo a 5%)" if p < 0.05 else ""
            linhas.append(f"  {modo:<15} | {so_modo:19d} | {so_ref:20d} | {p:.3f}{marca}")
        linhas.append("")

    if custos:
        linhas += ["== Custo de cada modelo (CPU deste computador) ==",
                   "  Modelo                           | Tempo médio por foto | Tamanho"]
        for nome, tempo_ms, tamanho_mb in custos:
            linhas.append(f"  {nome:<32} | {tempo_ms:17.0f} ms | {tamanho_mb:6.1f} MB")
        linhas += ["  (Tempo só da rede, sem abrir a foto. BioCLIP PyTorch: medido em FP32 para as três versões,",
                   "   tamanho do codificador de imagem no formato de cada versão. BioCLIP LiteRT: tempo e",
                   "   tamanho reais do arquivo .tflite.)", ""]

    for modo in (REFERENCIA, "brasil", "bioclip-misto", "bioclip-int8", "litert-int8", "litert-int8d",
                 "litert-mundo"):
        if modo in por_modo:
            linhas += _tabela_limiar(por_modo[modo], modo, n, precisao_alvo, limiar_atual)
    linhas += ["Observações:",
               "- IC95% de Wilson. Com poucas fotos o intervalo é largo: prefira 200+ fotos.",
               "- Espécie correta tirada do registro do iBirder só vale se você conferiu a identificação.",
               "- Espécies que o modelo não conhece nunca acertam: veja a linha 'só espécies conhecidas'.",
               "- No modo 'brasil' a confiança é renormalizada entre as espécies do Brasil: tende a subir.",
               "- Nos modos BioCLIP, 'conhecida' = espécie entre as candidatas registradas no Brasil.",
               "- 'litert-mundo' em fotos do Brasil mede o custo de ~11 mil candidatas (fotos de fora do país)."]
    return "\n".join(linhas) + "\n"


def gravar_csv(resultados: List[Resultado], caminho: Path) -> None:
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["arquivo", "especie_correta", "modo", "conhecida_pelo_modelo", "posicao",
                           "top1", "confianca_top1", "top2", "top3"])
        for r in resultados:
            nomes = [nome for nome, _ in r.top[:3]] + ["", "", ""]
            escritor.writerow([r.arquivo, r.verdade, r.modo, "sim" if r.conhecida else "não",
                               r.posicao or "", nomes[0], f"{r.confianca:.4f}".replace(".", ","), nomes[1], nomes[2]])


# ------------------------------------------------------------------ execução

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Avalia a IA local do iBirder com fotos de espécie conhecida.")
    parser.add_argument("pasta", type=Path, help="pasta com as fotos (JPG/PNG)")
    parser.add_argument("--csv", type=Path, help="planilha com as colunas 'arquivo' e 'especie'")
    parser.add_argument("--recursivo", action="store_true", help="incluir subpastas")
    parser.add_argument("--precisao-alvo", type=float, default=0.90, help="acerto mínimo do limiar sugerido (0-1)")
    parser.add_argument("--baixar-inat", type=int, default=0, metavar="N",
                        help="antes de avaliar, baixa N fotos de aves do Brasil do iNaturalist (grau de "
                             "pesquisa, licença aberta) para a pasta (tools/amostra_inaturalist.py)")
    parser.add_argument("--limite", type=int, default=0, help="avaliar só as N primeiras fotos (teste rápido)")
    parser.add_argument("--bioclip", action="store_true",
                        help="comparar também o BioCLIP zero-shot (exige open_clip_torch e torch)")
    parser.add_argument("--bioclip-litert", type=Path, metavar="PASTA",
                        help="rodar o BioCLIP convertido para LiteRT (pasta gerada por "
                             "tools/converter_bioclip_litert.py); não exige torch")
    parser.add_argument("--threads", type=int, default=None,
                        help="núcleos da CPU para o BioCLIP LiteRT (padrão: o mesmo do app)")
    parser.add_argument("--relatorio", type=Path, default=SAIDA_RELATORIO)
    parser.add_argument("--saida-csv", type=Path, default=SAIDA_CSV)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.baixar_inat:
        from tools.amostra_inaturalist import baixar_amostra
        logging.info(f"Baixando {args.baixar_inat} fotos do iNaturalist para {args.pasta}...")
        try:
            args.csv = baixar_amostra(args.pasta, total=args.baixar_inat)
        except Exception as e:
            logging.error(f"Falha ao baixar a amostra do iNaturalist: {e}")
            return 2
    if not args.pasta.is_dir():
        logging.error(f"Pasta não encontrada: {args.pasta}")
        return 2
    try:
        verdades_csv = ler_csv_verdade(args.csv) if args.csv else None
    except (OSError, ValueError, csv.Error) as e:
        logging.error(f"Não foi possível ler a planilha: {e}")
        return 2

    fotos = listar_fotos(args.pasta, args.recursivo)
    if args.limite:
        fotos = fotos[:args.limite]
    if not fotos:
        logging.error("Nenhuma foto JPG/PNG na pasta.")
        return 2
    logging.info(f"{len(fotos)} fotos encontradas. Carregando o modelo...")
    try:
        modelo = Modelo()
    except Exception as e:
        logging.error(f"Falha ao carregar o modelo: {e}")
        return 2
    try:
        permitidas = especies_brasil()
    except (OSError, KeyError) as e:
        logging.error(f"Não foi possível ler a lista de aves do Brasil: {e}")
        return 2
    if not permitidas:
        logging.error("A lista de aves do Brasil (assets/conservacao) está vazia ou ausente.")
        return 2
    bioclip = None
    if args.bioclip:
        try:
            especies, ingles = candidatas_bioclip()
            bioclip = ModeloBioclip(especies, ingles)
        except ImportError:
            logging.error("BioCLIP: instale no ambiente de teste: pip install open_clip_torch torch torchvision")
            return 2
        except Exception as e:
            logging.error(f"Falha ao carregar o BioCLIP: {e}")
            return 2
        logging.info(f"BioCLIP pronto: {len(especies)} espécies candidatas.")
    litert = None
    if args.bioclip_litert:
        try:
            litert = ModeloBioclipLitert(args.bioclip_litert, threads=args.threads)
        except Exception as e:
            logging.error(f"Falha ao carregar o BioCLIP LiteRT de {args.bioclip_litert}: {e}")
            return 2
        logging.info(f"BioCLIP LiteRT pronto: {', '.join(litert.classificadores)}; {len(litert.especies)} "
                     f"espécies do Brasil, {litert.total_mundo} no total; {litert.threads} núcleo(s).")

    inicio = time.time()
    resultados: List[Resultado] = []
    ignoradas = {"sem espécie conhecida": 0, "erro de leitura": 0}
    for i, foto in enumerate(fotos, 1):
        bruto = verdades_csv.get(foto.name.lower()) if verdades_csv is not None else verdade_gravada(foto)
        verdade = especie_canonica(bruto) if bruto else None
        if not verdade:
            ignoradas["sem espécie conhecida"] += 1
            continue
        try:
            resultados += avaliar_foto(modelo, foto, verdade, permitidas=permitidas, bioclip=bioclip,
                                       litert=litert)
        except Exception as e:
            ignoradas["erro de leitura"] += 1
            logging.warning(f"  {foto.name}: {e}")
            continue
        if i % 20 == 0 or i == len(fotos):
            logging.info(f"  {i}/{len(fotos)} fotos ({time.time() - inicio:.0f} s)")

    if not resultados:
        logging.error("Nenhuma foto com espécie conhecida. Use --csv ou fotos gravadas pelo iBirder.")
        return 1
    from modules.step1_identity.id_worker import LIMIAR_SUGESTAO
    fora = sum(1 for r in resultados if r.modo == REFERENCIA and r.verdade.lower() not in permitidas)
    custos = [("MobileNetV2 atual", 1000 * modelo.tempo_s / max(modelo.fotos, 1), modelo.tamanho_mb)]
    if bioclip is not None:
        tempo_ms = 1000 * bioclip.tempo_s["bioclip"] / max(bioclip.fotos, 1)
        for modo, nome in (("bioclip", "BioCLIP FP32"), ("bioclip-fp16", "BioCLIP FP16"),
                           ("bioclip-int8", "BioCLIP INT8 por canal")):
            custos.append((nome, tempo_ms, bioclip.tamanho_mb[modo]))
    if litert is not None:
        nomes = {"litert-int8": "LiteRT INT8 (só pesos)", "litert-int8d": "LiteRT INT8 dinâmico",
                 "litert-fp32": "LiteRT FP32"}
        for modo in litert.classificadores:
            custos.append((f"{nomes[modo]} ({litert.threads} núcl.)",
                           1000 * litert.tempo_s[modo] / max(litert.fotos, 1), litert.tamanho_mb[modo]))
    relatorio = montar_relatorio(resultados, ignoradas, args.precisao_alvo, time.time() - inicio,
                                 LIMIAR_SUGESTAO, fora_do_brasil=fora, custos=custos)
    # Com BOM: o "type" do PowerShell e o Bloco de Notas antigo leem os acentos certos
    args.relatorio.write_text(relatorio, encoding="utf-8-sig")
    gravar_csv(resultados, args.saida_csv)
    print("\n" + relatorio)
    logging.info(f"Relatório: {args.relatorio}\nPor foto:  {args.saida_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
