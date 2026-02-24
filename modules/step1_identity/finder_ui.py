from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QLabel
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QSize

MANUAL_TEXTO = """
<h2>📖 Guia de Utilização do iBirder</h2>
<p>O <b>iBirder</b> é uma ferramenta de auxílio à identificação ornitológica que utiliza Inteligência Artificial avançada para analisar espécies a partir de fotografias.</p>

<h3>1. Identificação Visual (Por Imagem)</h3>
<p>Para analisar um registro fotográfico:</p>
<ul>
    <li><b>Arraste e Solte:</b> Mova o arquivo da foto diretamente para a área central tracejada.</li>
    <li><b>Seleção de Arquivo:</b> Ou clique no botão "Nova Identificação" para buscar a imagem em suas pastas.</li>
</ul>
<p><i>Dica: O sistema processa melhor imagens com boa iluminação e foco claro na ave.</i></p>

<h3>2. Validação Taxonômica (Busca Manual)</h3>
<p>Se você já possui o nome da espécie e deseja confirmar dados ou obter a descrição:</p>
<ol>
    <li>Digite o <b>Nome Científico</b> (ex: <i>Zonotrichia capensis</i>) no campo de busca.</li>
    <li>Clique no ícone da <b>Lupa</b>. O sistema retornará a classificação e detalhes técnicos.</li>
</ol>

<h3>3. Requisitos do Sistema</h3>
<ul>
    <li><b>Conexão:</b> Este software opera conectado aos servidores de IA em nuvem. Uma conexão ativa com a internet é necessária para processar as identificações.</li>
    <li><b>Precisão:</b> Embora a IA seja extremamente capaz, recomenda-se sempre cruzar os dados com guias de campo para registros científicos definitivos.</li>
</ul>
"""

class JanelaManual(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual do Usuário")
        self.setFixedSize(500, 600)
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
            QTextBrowser { border: none; background-color: #FFFFFF; color: #333333; font-family: "Segoe UI"; font-size: 14px; padding: 10px; }
            QPushButton { background-color: #444444; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #222222; }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 20)
        
        # Conteúdo Texto
        self.texto = QTextBrowser()
        self.texto.setHtml(MANUAL_TEXTO)
        self.texto.setOpenExternalLinks(True)
        layout.addWidget(self.texto)
        
        # Botão Fechar
        btn_fechar = QPushButton("Entendi")
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.setFixedWidth(120)
        btn_fechar.clicked.connect(self.accept)
        
        layout.addWidget(btn_fechar, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)
