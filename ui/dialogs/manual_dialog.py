import sys
import os
from pathlib import Path
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
        
        lbl_title = QLabel("Manual de Instruções")
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
                background-color: #374151;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1F2937;
            }
        """)
        btn_close.clicked.connect(self.accept)
        
        footer_layout.addStretch()
        footer_layout.addWidget(btn_close)
        layout.addWidget(footer)
        
        # Aplicar Tema da Janela (Title Bar)
        StyleManager.setup_window_theme(self)

    def _gerar_conteudo(self):
        # Caminho do arquivo de guia
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).parent.parent.parent
            
        guia_path = base_dir / "guia_do_usuario.md"
        
        if not guia_path.exists():
            return "<html><body><h1>Erro</h1><p>Arquivo guia_do_usuario.md não encontrado.</p></body></html>"
            
        try:
            with open(guia_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            return self._parse_markdown(md_content)
        except Exception as e:
            return f"<html><body><h1>Erro ao ler guia</h1><p>{str(e)}</p></body></html>"

    def _parse_markdown(self, md):
        import re
        
        # Estilos CSS Premium (Charcoal #374151)
        css = """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
            body {
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                color: #374151;
                font-size: 14px;
                line-height: 1.6;
                background-color: #FFFFFF;
                padding: 10px;
            }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #111827; font-size: 26px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }
            h2 { color: #111827; font-size: 20px; font-weight: 700; margin-top: 35px; margin-bottom: 20px; border-bottom: 1px solid #F3F4F6; padding-bottom: 8px; }
            h3 { color: #374151; font-size: 17px; font-weight: 700; margin-top: 25px; margin-bottom: 15px; }
            
            p { margin-bottom: 16px; text-align: justify; color: #4B5563; }
            
            .step-card { 
                background: #FFFFFF; 
                border: 1px solid #E5E7EB; 
                border-radius: 12px; 
                padding: 18px 22px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            .step-header { display: flex; align-items: center; margin-bottom: 12px; }
            .step-number { 
                background: #F3F4F6; color: #374151; width: 32px; height: 32px; 
                border-radius: 8px; display: inline-flex; align-items: center; justify-content: center;
                font-size: 14px; font-weight: 800; margin-right: 15px;
                border: 1px solid #E5E7EB;
                flex-shrink: 0;
            }
            .step-title { font-weight: 700; color: #111827; font-size: 17px; line-height: 1.2; }
            
            .tip-box { 
                background-color: #ECFDF5; 
                border-left: 4px solid #10B981; 
                padding: 16px; 
                margin: 25px 0; 
                border-radius: 0 8px 8px 0;
            }
            .tip-title { color: #065F46; font-weight: 700; font-size: 13px; text-transform: uppercase; margin-bottom: 8px; display: block; }
            
            .alerta { 
                background-color: #FFFBEB; 
                border: 1px solid #FEF3C7; 
                padding: 16px; 
                margin: 25px 0; 
                border-radius: 8px;
                color: #92400E;
            }

            ul { margin-bottom: 16px; padding-left: 20px; }
            li { margin-bottom: 8px; color: #4B5563; }
            b, strong { color: #111827; font-weight: 700; }
            i, em { color: #6B7280; }
            hr { border: 0; border-top: 1px solid #F3F4F6; margin: 40px 0; }
            
            .footer-text { 
                margin-top: 60px; 
                padding-top: 20px;
                border-top: 1px solid #F3F4F6;
                font-size: 12px; 
                color: #9CA3AF; 
                text-align: center; 
                font-style: italic;
            }
        </style>
        """

        def process_inline(text):
            # Negrito
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Itálico
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            return text

        lines = md.split('\n')
        html_output = [f"<html><head>{css}</head><body><div class='container'>"]
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # 1. H1
            if line.startswith('# '):
                html_output.append(f"<h1>{process_inline(line[2:])}</h1>")
            
            # 2. H2
            elif line.startswith('## '):
                html_output.append(f"<h2>{process_inline(line[3:])}</h2>")
                
            # 3. Cards de Etapa (Tratamento especial para capturar parágrafos múltiplos)
            elif line.startswith('### [ETAPA'):
                match = re.search(r'\[ETAPA (\d+)\] (.*)', line)
                if match:
                    num, title = match.groups()
                    i += 1
                    # Captura parágrafos seguintes até o próximo header
                    content_segments = []
                    curr_segment = ""
                    
                    while i < len(lines) and not lines[i].strip().startswith('#'):
                        l = lines[i].strip()
                        if not l:
                            if curr_segment:
                                content_segments.append(curr_segment)
                                curr_segment = ""
                        else:
                            curr_segment += " " + l
                        i += 1
                    
                    if curr_segment:
                        content_segments.append(curr_segment)
                    
                    # Constrói o HTML do card com parágrafos internos
                    p_tags = "".join([f"<p style='font-size: 13px; margin-bottom: 10px; color: #4B5563;'>{process_inline(s.strip())}</p>" for s in content_segments])
                    
                    html_output.append(f"""
                    <div class="step-card">
                        <div class="step-header">
                            <span class="step-number">{num}</span>
                            <span class="step-title">{process_inline(title)}</span>
                        </div>
                        {p_tags}
                    </div>
                    """)
                    i -= 1 # Volta um passo para o loop principal processar o header que interrompeu
            
            # 4. H3 Simples ou Temas
            elif line.startswith('### '):
                title = line[4:]
                # Remove colchetes se houver [TEMA A] etc
                title = re.sub(r'\[.*?\]', '', title).strip()
                html_output.append(f"<h3>{process_inline(title)}</h3>")
            
            # 5. Listas
            elif line.startswith('- ') or (line[0].isdigit() and line[1:3] == '. '):
                html_output.append("<ul>")
                while i < len(lines) and (lines[i].strip().startswith('- ') or (lines[i].strip() and lines[i].strip()[0].isdigit() and lines[i].strip()[1:3] == '. ')):
                    l = lines[i].strip()
                    prefix_len = 2 if l.startswith('- ') else 3
                    html_output.append(f"<li>{process_inline(l[prefix_len:])}</li>")
                    i += 1
                html_output.append("</ul>")
                i -= 1
                
            # 6. Boxes de Dica / Importante
            elif line.startswith('> **DICA PRO:'):
                content = line.replace('> **DICA PRO:', '').strip()
                html_output.append(f"""
                <div class="tip-box">
                    <span class="tip-title">Dica Pro</span>
                    {process_inline(content)}
                </div>
                """)
            elif line.startswith('> [!IMPORTANT]'):
                content = ""
                i += 1
                while i < len(lines) and lines[i].strip().startswith('>'):
                    content += lines[i].strip().replace('>', '').replace('[!IMPORTANT]', '').strip() + " "
                    i += 1
                html_output.append(f"<div class='alerta'><b>Nota Importante:</b> {process_inline(content.strip())}</div>")
                i -= 1
                
            # 7. HR e Parágrafos Normais
            elif line == '---':
                html_output.append("<hr>")
            else:
                html_output.append(f"<p>{process_inline(line)}</p>")
                
            i += 1

        html_output.append("</div></body></html>")
        return "\n".join(html_output)


