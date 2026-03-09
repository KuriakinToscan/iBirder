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
        # Caminhos base
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).parent.parent.parent
            
        guia_path = base_dir / "guia_do_usuario.md"
        logo_path = base_dir / "assets" / "logo_ave_escuro.svg"
        
        # Converte Path para URL de arquivo local para o Qt
        logo_url = logo_path.as_uri() if logo_path.exists() else ""
        
        if not guia_path.exists():
            return "<html><body><h1>Erro</h1><p>Arquivo guia_do_usuario.md não encontrado.</p></body></html>"
            
        try:
            with open(guia_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            return self._parse_markdown(md_content, logo_url)
        except Exception as e:
            return f"<html><body><h1>Erro ao ler guia</h1><p>{str(e)}</p></body></html>"

    def _parse_markdown(self, md, logo_url=""):
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
            
            /* Cabeçalho de Marca Sincronizado */
            .header-table { 
                width: 100%; 
                background-color: #FFFFFF; 
                border-bottom: 2px solid #F3F4F6; 
                margin-bottom: 40px; 
                padding: 15px 0;
            }
            .brand-title { 
                font-size: 52px; 
                font-weight: 300; 
                font-style: italic;
                color: #4B5563; 
                margin: 0;
                letter-spacing: -2px;
            }
            
            h2 { 
                color: #111827; 
                font-size: 19px; 
                font-weight: 700; 
                margin-top: 40px; 
                margin-bottom: 20px; 
                border-left: 4px solid #374151;
                padding-left: 12px;
            }
            h3 { color: #374151; font-size: 16px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; }
            
            p { margin-bottom: 18px; text-align: justify; color: #4B5563; line-height: 1.7; }
            
            .step-card { 
                background: #FFFFFF; 
                border: 1px solid #E5E7EB; 
                border-radius: 12px; 
                padding: 20px 24px;
                margin-bottom: 25px;
            }
            .step-header { margin-bottom: 15px; }
            .step-number { 
                background: #374151; color: #FFFFFF; 
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 13px; font-weight: 800;
                margin-right: 12px;
            }
            .step-title { font-weight: 700; color: #111827; font-size: 17px; }
            
            .tip-box { 
                background-color: #F0FDF4; 
                border-left: 4px solid #22C55E; 
                padding: 18px; 
                margin: 30px 0; 
            }
            .tip-title { color: #166534; font-weight: 800; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; display: block; }
            
            .alerta { 
                background-color: #FFFBEB; 
                border-left: 4px solid #F59E0B; 
                padding: 18px; 
                margin: 30px 0; 
                color: #92400E;
            }

            ul { margin-bottom: 18px; padding-left: 25px; }
            li { margin-bottom: 10px; color: #4B5563; line-height: 1.6; }
            b, strong { color: #111827; font-weight: 700; }
            i, em { color: #64748B; }
            hr { border: 0; border-top: 1px solid #F1F5F9; margin: 45px 0; }
            
            .footer-info { 
                margin-top: 60px; 
                padding: 40px;
                background-color: #FFFFFF;
                border-top: 1px solid #F1F5F9;
                text-align: center;
            }
            .github-link { 
                color: #334155;
                font-weight: 700;
                text-decoration: none;
                font-size: 13px;
                padding: 6px 15px;
            }
            .credits {
                font-size: 12px;
                color: #94A3B8;
                margin-top: 20px;
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
        
        # Inserção do Cabeçalho usando Tabela (compatível com Qt)
        # Spacer td de 240px garante o afastamento no motor limitado do Qt
        logo_html = f'<td width="120" valign="middle"><img src="{logo_url}" height="84"></td>' if logo_url else ""
        spacer_html = '<td width="120"></td>' if logo_url else ""
        
        html_output.append(f"""
            <table class="header-table" cellpadding="0" cellspacing="0">
                <tr>
                    {logo_html}
                    {spacer_html}
                    <td valign="middle" align="left">
                        <div class="brand-title">IA para Birdwatching</div>
                    </td>
                </tr>
            </table>
        """)
            
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Pula o H1 pois já usamos no cabeçalho
            if line.startswith('# '):
                i += 1
                continue
            
            # 2. H2
            if line.startswith('## '):
                html_output.append(f"<h2>{process_inline(line[3:])}</h2>")
                
            # 3. Cards de Etapa
            elif line.startswith('### [ETAPA'):
                match = re.search(r'\[ETAPA (\d+)\] (.*)', line)
                if match:
                    num, title = match.groups()
                    i += 1
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
                    i -= 1
            
            # 4. H3 Simples
            elif line.startswith('### '):
                html_output.append(f"<h3>{process_inline(line[4:].strip())}</h3>")
            
            # 5. Listas
            elif line.strip() and (line.startswith('- ') or (line[0].isdigit() and line[1:3] == '. ')):
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

        # Rodapé com GitHub e Créditos
        html_output.append("""
            <div class="footer-info">
                <b>iBirder — Tecnologia Nacional a Serviço da Ciência Cidadã</b><br>
                <a href="https://github.com/KuriakinToscan/iBirder" class="github-link">github.com/KuriakinToscan/iBirder</a>
                <div class="credits">
                    Desenvolvido por Kuriakin Toscan<br>
                    kuriakin.toscan@gmail.com<br>
                    Versão 1.0 | © 2026 iBirder Project
                </div>
            </div>
        """)
        
        html_output.append("</div></body></html>")
        return "\n".join(html_output)


