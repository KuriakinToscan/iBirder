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
from core.paths import APP_DIR

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
        StyleManager.estilizar(header, "background-color: var(--superficie_alt); border-bottom: 1px solid var(--borda_suave);")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)
        
        lbl_title = QLabel("Manual de Instruções")
        StyleManager.estilizar(lbl_title, "font-size: 18px; font-weight: bold; color: var(--texto); border: none;")
        header_layout.addWidget(lbl_title)
        
        layout.addWidget(header)
        
        # Área de Conteúdo
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setFrameShape(QFrame.NoFrame)
        StyleManager.estilizar(self.browser, """
            QTextBrowser {
                background-color: var(--superficie);
                padding: 30px;
                line-height: 160%;
            }
        """)
        
        conteudo_html = self._gerar_conteudo()
        self.browser.setHtml(StyleManager.render(conteudo_html))
        layout.addWidget(self.browser)
        
        # Footer com botão de fechar
        footer = QFrame()
        footer.setFixedHeight(60)
        StyleManager.estilizar(footer, "background-color: var(--superficie_alt); border-top: 1px solid var(--borda_suave);")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_close = QPushButton("Entendido")
        btn_close.setFixedSize(120, 36)
        btn_close.setCursor(Qt.PointingHandCursor)
        StyleManager.estilizar(btn_close, """
            QPushButton {
                background-color: var(--destaque);
                color: var(--texto_destaque);
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: var(--destaque_hover);
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
        guia_path = APP_DIR / "guia_do_usuario.md"
        logo_path = Path(StyleManager.caminho_logo())  # logo na cor do tema
        
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
        
        # Estilos CSS com tokens do tema (renderizados em setHtml)
        css = """
        <style>
            body {
                font-family: 'var(--fonte)', 'Segoe UI', Arial, sans-serif;
                color: var(--texto);
                font-size: 14px;
                line-height: 1.6;
                background-color: var(--superficie);
                padding: 10px;
            }
            .container { max-width: 800px; margin: 0 auto; }
            
            /* Cabeçalho de Marca Sincronizado */
            .header-table { 
                width: 100%; 
                background-color: var(--superficie); 
                border-bottom: 2px solid var(--hover); 
                margin-bottom: 40px; 
                padding: 15px 0;
            }
            .brand-title { 
                font-size: 52px; 
                font-weight: 300; 
                font-style: italic;
                color: var(--texto_secundario); 
                margin: 0;
                letter-spacing: -2px;
            }
            
            h2 { 
                color: var(--texto); 
                font-size: 19px; 
                font-weight: 700; 
                margin-top: 40px; 
                margin-bottom: 20px; 
                border-left: 4px solid var(--destaque);
                padding-left: 12px;
            }
            h3 { color: var(--titulo_sessao); font-size: 16px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; }
            
            p { margin-bottom: 18px; text-align: justify; color: var(--texto_secundario); line-height: 1.7; }
            
            .step-card { 
                background: var(--superficie); 
                border: 1px solid var(--borda_suave); 
                border-radius: 12px; 
                padding: 20px 24px;
                margin-bottom: 25px;
            }
            .step-header { margin-bottom: 15px; }
            .step-number { 
                background: var(--destaque); color: var(--texto_destaque); 
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 13px; font-weight: 800;
                margin-right: 12px;
            }
            .step-title { font-weight: 700; color: var(--texto); font-size: 17px; }
            
            .tip-box { 
                background-color: var(--sucesso_fundo); 
                border-left: 4px solid var(--enfase); 
                padding: 18px; 
                margin: 30px 0; 
            }
            .tip-title { color: var(--sucesso_texto); font-weight: 800; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; display: block; }
            
            .alerta { 
                background-color: var(--alerta_fundo); 
                border-left: 4px solid var(--alerta_borda); 
                padding: 18px; 
                margin: 30px 0; 
                color: var(--alerta_texto);
            }

            ul, ol { margin-bottom: 18px; padding-left: 25px; }
            li { margin-bottom: 10px; color: var(--texto_secundario); line-height: 1.6; }
            b, strong { color: var(--texto); font-weight: 700; }
            i, em { color: var(--texto_suave); }
            hr { border: 0; border-top: 1px solid var(--borda_suave); margin: 45px 0; }
            
            .footer-info { 
                margin-top: 60px; 
                padding: 40px;
                background-color: var(--superficie);
                border-top: 1px solid var(--borda_suave);
                text-align: center;
            }
            .github-link { 
                color: var(--texto);
                font-weight: 700;
                text-decoration: none;
                font-size: 13px;
                padding: 6px 15px;
            }
            .credits {
                font-size: 12px;
                color: var(--texto_suave);
                margin-top: 20px;
                font-style: italic;
            }
        </style>
        """

        def process_inline(text):
            # Código `assim` (antes do negrito/itálico para não interpretar * dentro do código)
            text = re.sub(r'`([^`]+)`', r'<code style="background:var(--hover); padding:1px 4px;">\1</code>', text)
            # Links [texto](https://...) — abertos no navegador (setOpenExternalLinks)
            text = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" style="color:var(--link);">\1</a>', text)
            # Negrito
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Itálico
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            return text

        item_lista = re.compile(r'^(- |\d+\. )')

        def render_bloco(linhas):
            """Conteúdo de um card: parágrafos, listas e avisos (> ...)."""
            partes = []
            j = 0
            while j < len(linhas):
                l = linhas[j].strip()
                if not l:
                    j += 1
                elif item_lista.match(l):
                    tag = "ul" if l.startswith('- ') else "ol"
                    itens = []
                    while j < len(linhas) and item_lista.match(linhas[j].strip()):
                        itens.append(f"<li>{process_inline(item_lista.sub('', linhas[j].strip(), count=1))}</li>")
                        j += 1
                    partes.append(f"<{tag}>{''.join(itens)}</{tag}>")
                elif l.startswith('>'):
                    texto = []
                    while j < len(linhas) and linhas[j].strip().startswith('>'):
                        texto.append(linhas[j].strip().lstrip('>').strip())
                        j += 1
                    partes.append(f"<div class='alerta'>{process_inline(' '.join(texto))}</div>")
                else:
                    texto = []
                    while (j < len(linhas) and linhas[j].strip() and not item_lista.match(linhas[j].strip())
                           and not linhas[j].strip().startswith('>')):
                        texto.append(linhas[j].strip())
                        j += 1
                    partes.append(f"<p style='font-size: 13px; margin-bottom: 10px; color: var(--texto_secundario);'>{process_inline(' '.join(texto))}</p>")
            return "".join(partes)

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
                    conteudo = []
                    # O card vai até o próximo título ou separador
                    while i < len(lines) and not lines[i].strip().startswith('#') and lines[i].strip() != '---':
                        conteudo.append(lines[i])
                        i += 1

                    html_output.append(f"""
                    <div class="step-card">
                        <div class="step-header">
                            <span class="step-number">{num}</span>
                            <span class="step-title">{process_inline(title)}</span>
                        </div>
                        {render_bloco(conteudo)}
                    </div>
                    """)
                    i -= 1
            
            # 4. H3 Simples
            elif line.startswith('### '):
                html_output.append(f"<h3>{process_inline(line[4:].strip())}</h3>")
            
            # 5. Listas
            elif item_lista.match(line):
                numerada = not line.startswith('- ')
                html_output.append("<ol>" if numerada else "<ul>")
                while i < len(lines) and item_lista.match(lines[i].strip()):
                    l = lines[i].strip()
                    html_output.append(f"<li>{process_inline(item_lista.sub('', l, count=1))}</li>")
                    i += 1
                html_output.append("</ol>" if numerada else "</ul>")
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
                
            # 6b. Citações comuns (> ...) viram caixa de aviso
            elif line.startswith('>'):
                content = ""
                while i < len(lines) and lines[i].strip().startswith('>'):
                    content += lines[i].strip().lstrip('>').strip() + " "
                    i += 1
                html_output.append(f"<div class='alerta'>{process_inline(content.strip())}</div>")
                i -= 1

            # 7. HR e Parágrafos Normais
            elif line == '---':
                html_output.append("<hr>")
            else:
                html_output.append(f"<p>{process_inline(line)}</p>")
                
            i += 1

        # Rodapé com GitHub e Créditos
        from core.config import APP_VERSION
        html_output.append(f"""
            <div class="footer-info">
                <b>iBirder — IA para Birdwatching</b><br>
                <a href="https://github.com/KuriakinToscan/iBirder" class="github-link">github.com/KuriakinToscan/iBirder</a>
                <div class="credits">
                    Desenvolvido por Kuriakin Toscan<br>
                    kuriakin.toscan@gmail.com<br>
                    Versão {APP_VERSION} | © 2026 iBirder Project
                </div>
            </div>
        """)
        
        html_output.append("</div></body></html>")
        return "\n".join(html_output)


