import sys
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QPushButton, 
                                 QHBoxLayout, QLabel, QFrame)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QColor
from core.style_manager import StyleManager

class ManualUsuarioDialog(QDialog):
    """
    Diálogo elegante contendo o manual de instruções formal do iBirder.
    Utiliza HTML/CSS para uma apresentação premium e profissional.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guia do Usuário - iBirder")
        self.resize(850, 650)
        self._configurar_ui()
        
    def _configurar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header do Manual
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #F9FAFB; border-bottom: 1px solid #E5E7EB;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)
        
        lbl_title = QLabel("Manual de Instruções e Fluxo Científico")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #111827; border: none;")
        header_layout.addWidget(lbl_title)
        
        layout.addWidget(header)
        
        # Área de Conteúdo
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setFrameShape(QFrame.NoFrame)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                padding: 30px;
                line-height: 160%;
            }
        """)
        
        conteudo_html = self._gerar_conteudo()
        self.browser.setHtml(conteudo_html)
        layout.addWidget(self.browser)
        
        # Footer com botão de fechar
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background-color: #F9FAFB; border-top: 1px solid #E5E7EB;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_close = QPushButton("Entendido")
        btn_close.setFixedSize(120, 36)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4338CA;
            }
        """)
        btn_close.clicked.connect(self.accept)
        
        footer_layout.addStretch()
        footer_layout.addWidget(btn_close)
        layout.addWidget(footer)
        
        # Aplicar Tema da Janela (Title Bar)
        StyleManager.setup_window_theme(self)

    def _gerar_conteudo(self):
        return f"""
        <html>
        <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #374151;
                font-size: 14px;
            }}
            h1 {{ color: #111827; font-size: 24px; margin-bottom: 10px; }}
            h2 {{ color: #1F2937; font-size: 18px; margin-top: 25px; border-bottom: 2px solid #EEF2FF; padding-bottom: 5px; }}
            h3 {{ color: #4F46E5; font-size: 16px; margin-top: 20px; }}
            p {{ margin-bottom: 15px; text-align: justify; }}
            ul {{ margin-bottom: 15px; }}
            li {{ margin-bottom: 8px; }}
            .destaque {{ color: #4F46E5; font-weight: bold; }}
            .alerta {{ background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 10px; margin: 15px 0; }}
            .badge {{ background-color: #EEF2FF; color: #4338CA; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        </style>
        </head>
        <body>
            <h1>Bem-vindo ao iBirder</h1>
            <p>O <b>iBirder</b> é uma estação de trabalho ornitológica avançada, desenhada para auxiliar pesquisadores e entusiastas na identificação, catalogação e preservação de registros de aves. Este sistema integra inteligência artificial de última geração com bases de dados globais e ferramentas de geoprocessamento.</p>
            
            <h2>1. Como Iniciar uma Análise</h2>
            <p>O fluxo de trabalho principal inicia-se com o carregamento de uma fotografia:</p>
            <ul>
                <li><b>Carregamento:</b> Clique no painel central ou arraste uma foto (.jpg) para dentro do aplicativo.</li>
                <li><b>Identificação Automática:</b> O "Cérebro Digital" processará a imagem localmente para sugerir a espécie.</li>
                <li><b>Confirmação:</b> Após a sugestão, os dados biográficos e geográficos serão carregados em cascata.</li>
            </ul>

            <div class="alerta">
                <b>Privacidade e Segurança:</b> Todo o processamento visual ocorre em sua máquina. O iBirder não envia suas fotos originais para servidores externos durante a identificação.
            </div>

            <h2>2. Entendendo as Etapas do Processamento</h2>
            <p>O aplicativo opera em um pipeline científico dividido em seis fases fundamentais:</p>
            
            <h3><span class="badge">Etapa 1</span> Identificação Visual</h3>
            <p>Utiliza uma rede neural treinada para reconhecer padrões de plumagem, bico e silhueta. Mostra o nível de confiança estatística da análise.</p>

            <h3><span class="badge">Etapa 2</span> Biografia e Etimologia</h3>
            <p>Busca informações taxonômicas e o significado do nome científico em fontes consagradas como WikiAves e iNaturalist.</p>

            <h3><span class="badge">Etapa 3</span> Geografia e Conservação</h3>
            <p>Cruza os dados de localização (GPS) da foto com mapas de biomas e o Status de Conservação da IUCN e ICMBio.</p>

            <h3><span class="badge">Etapa 4</span> Vocalização</h3>
            <p>Monitora e recupera gravações de áudio da espécie no Xeno-Canto, permitindo a conferência auditiva diretamente no mapa.</p>

            <h3><span class="badge">Etapa 5</span> Listas de Referência</h3>
            <p>Sincroniza com o eBird para fornecer contexto taxonômico global e links para fontes oficiais.</p>

            <h3><span class="badge">Etapa 6</span> Escrita de Metadados (EXIF)</h3>
            <p>A fase final onde todas as informações coletadas podem ser gravadas permanentemente dentro do arquivo da foto, utilizando o padrão industrial de Darwin Core.</p>

            <h2>3. Recursos Avançados</h2>
            <h3>Interação com o Mapa</h3>
            <p>O mapa é dinâmico. Pontos azuis indicam locais onde a espécie foi gravada. Ao clicar em um ponto, você pode ouvir a vocalização e ver detalhes do autor da gravação.</p>

            <h3>Drag-and-Drop de Exportação</h3>
            <p>Você pode arrastar a foto identificada diretamente do iBirder para pastas do seu computador ou softwares de edição (como Lightroom ou DigiKam). O iBirder otimizará o arquivo automaticamente para garantir a integridade dos dados.</p>

            <h2>4. Suporte a Caracteres Especiais</h2>
            <p>O iBirder foi construído para respeitar a rica ortografia da língua portuguesa e os nomes latinos da ciência, utilizando codificação UTF-8 em todos os processos de escrita e exibição.</p>
            
            <p style="margin-top: 40px; font-size: 12px; color: #9CA3AF; text-align: center;">
                iBirder - Tecnologia Nacional a Serviço da Conservação das Aves<br>
                Versão v0.9.x
            </p>
        </body>
        </html>
        """
