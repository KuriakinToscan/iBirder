#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Licença GNU GPL v3 (veja main.py)

"""
Estado da identificação em curso (v1.4).

Um só lugar diz em que etapa está a foto atual (sem foto, identificando, conferir,
gravada...), para os layouts mostrarem isso cada um a seu modo: a barra de etapas do
Fluxo guiado, o status de cada foto da fila na Mesa de trabalho.

O estado acompanha os sinais do Orchestrator (identificação concluída ou com erro);
a janela informa o que só ela sabe: foto aberta, busca manual, gravação e limpeza.
Os dados completos continuam na janela e no SessionLogger; aqui fica só o resumo.
"""

from PySide6.QtCore import QObject, Signal

# Etapas, na ordem do fluxo
SEM_FOTO = "sem_foto"            # nada aberto
IDENTIFICANDO = "identificando"  # IA local / nuvem trabalhando
CONFERIR = "conferir"            # espécie sugerida (ou digitada): falta conferir e gravar
INCONCLUSIVA = "inconclusiva"    # IA sem certeza: a pessoa precisa indicar a espécie
GRAVADA = "gravada"              # dados gravados na foto
ERRO = "erro"                    # falha na identificação

ETAPAS = (SEM_FOTO, IDENTIFICANDO, CONFERIR, INCONCLUSIVA, GRAVADA, ERRO)


class EstadoIdentificacao(QObject):
    """Resumo da identificação atual; emite `etapa_alterada` a cada mudança de etapa."""

    etapa_alterada = Signal(str)
    alterado = Signal()  # qualquer mudança (etapa, espécie, caminho)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.etapa = SEM_FOTO
        self.caminho = None
        self.nome_cientifico = None
        self.confianca = None
        self.manual = False  # espécie digitada pela pessoa, não sugerida pela IA
        self.mensagem_erro = ""

    # --- Sinais do Orchestrator ---

    def conectar(self, orchestrator):
        """Acompanha a identificação feita pelo Orchestrator."""
        orchestrator.step1_identificacao_concluida.connect(self.identificacao_concluida)
        orchestrator.step1_identificacao_erro.connect(self.identificacao_com_erro)

    def identificacao_concluida(self, dados):
        dados = dados or {}
        status = dados.get("status_msg", "")
        self.confianca = dados.get("confianca")
        self.manual = False
        self.mensagem_erro = ""
        inconclusiva = "Inconclusiva" in status or "Baixa" in status or not dados.get("nome_cientifico")
        self.nome_cientifico = None if inconclusiva else dados.get("nome_cientifico")
        self._mudar(INCONCLUSIVA if inconclusiva else CONFERIR)

    def identificacao_com_erro(self, mensagem=""):
        self.mensagem_erro = mensagem or ""
        self._mudar(ERRO)

    # --- Informados pela janela ---

    def foto_aberta(self, caminho):
        """Foto nova: a identificação começa."""
        self._limpar_resultado()
        self.caminho = caminho
        self._mudar(IDENTIFICANDO)

    def especie_digitada(self, nome_cientifico):
        """Busca manual: a espécie vem da pessoa (com ou sem foto aberta)."""
        self.nome_cientifico = nome_cientifico
        self.confianca = None
        self.manual = True
        self.mensagem_erro = ""
        self._mudar(CONFERIR)

    def gravada(self, caminho=None):
        """Dados gravados na foto (o caminho muda se a foto foi renomeada)."""
        if caminho:
            self.caminho = caminho
        self._mudar(GRAVADA)

    def limpar(self, manter_foto=False):
        """Volta ao início; com manter_foto, a foto continua aberta para uma nova busca."""
        self._limpar_resultado()
        if not manter_foto:
            self.caminho = None
        self._mudar(IDENTIFICANDO if manter_foto and self.caminho else SEM_FOTO)

    # --- Internos ---

    def _limpar_resultado(self):
        self.nome_cientifico = None
        self.confianca = None
        self.manual = False
        self.mensagem_erro = ""

    def _mudar(self, etapa):
        anterior, self.etapa = self.etapa, etapa
        if etapa != anterior:
            self.etapa_alterada.emit(etapa)
        self.alterado.emit()
