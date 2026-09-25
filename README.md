# iBirder 🐦
**IA para Birdwatching — Inteligência Artificial local a serviço da ciência cidadã.**

## 📖 Sobre o Projeto
O **iBirder** é uma ferramenta de código aberto desenvolvida para ornitólogos, observadores de aves e fotógrafos de natureza. Com sua inovadora arquitetura **Híbrida (Edge AI + Nuvem)**, o sistema prioriza o processamento local, mas pode recorrer de forma inteligente às APIs do iNaturalist e Google Vision para fotos complexas, garantindo a maior taxa de acerto possível.

## ✨ Principais Diferenciais
- **Identificação em Cascata**: Prioriza a IA Local (Custo e latência zero). Se a confiança for baixa, tenta a nuvem (iNaturalist API) e, por fim, o Google Cloud Vision (v1.1+).
- **Privacidade e Controle (BYOK)**: O processamento de imagem ocorre na sua máquina por padrão. As chamadas em nuvem requerem as suas próprias chaves de API (Bring Your Own Key).
- **Otimizado para o Brasil**: Integração profunda com o **WikiAves** para etimologia e contexto biológico da nossa biodiversidade.
- **Persistência Científica**: Gravação de metadados nos padrões **EXIF/XMP**, **Darwin Core (DWC)** e palavras-chave hierárquicas.

## 🌟 Novidades na v1.1
- **Compilação e Performance**: Migração do gerenciador de pacotes para `uv`, acelerando massivamente o tempo de build e isolando dependências.
- **Refatoração de Diretórios**: Implementação inteligente do `APP_DIR`, resolvendo problemas de caminhos de arquivos empacotados (`sys._MEIPASS`) no Windows, garantindo que logos e manuais carreguem sempre e o ExifTool rode de forma imaculada.
- **Identidade Visual**: Limpeza e padronização da UI, com adoção de ícones *line-art* SVG premium, eliminando fontes de emojis legadas do sistema.
- **Cleaner Core**: Remoção de códigos de limpeza temporária inoperantes ou redundantes.

## 🛠️ Tecnologias e Fontes
O iBirder integra as bibliotecas biológicas e tecnologias mais respeitadas do ecossistema científico:

- **AI Engine**: Rede Neural **EfficientNet-V1.3** (Google Research).
- **Interface**: Desenvolvido em **Python 3.12** com **PySide6**.
- **Mapas & Geo**: **Folium**, **OpenStreetMap** e geocodificação via **Nominatim**.
- **Fontes de Dados**:
  - **WikiAves**: Etimologia e Biologia (Brasil).
  - **iNaturalist**: Taxonomia e Validação Visual.
  - **eBird (Cornell Lab)**: Nomenclatura Global.
  - **GBIF**: Mapas de densidade de ocorrência.
  - **IUCN & ICMBio (SALVE)**: Status de conservação e ameaça.
  - **Xeno-Canto**: Vocalizações e registros sonoros.
- **Motor de Metadados**: **ExifTool** (Phil Harvey).

## 🚀 Instalação e Uso

### Para Usuários (Windows)
1. Baixe a versão mais recente em [Releases](https://github.com/KuriakinToscan/iBirder/releases).
2. Execute o instalador `Instalador_iBirder_v1.1_FIX.exe`.
3. O app permite abrir fotos via "Arraste e Solte" ou diretamente pelo botão direito no Windows Explorer.

### Para Desenvolvedores
Recomendamos o uso do `uv` para o gerenciamento ultrarrápido de pacotes virtuais.
1. Clone o repositório ou baixe o `.zip`.
2. Abra o terminal (PowerShell) na pasta do projeto e crie o ambiente com `uv`: `uv venv`.
3. Ative o ambiente virtual no PowerShell com: `.\.venv\Scripts\Activate.ps1`.
4. Instale as dependências com: `uv pip install -r requirements.txt`.
5. Execute: `python main.py`.

## ⚖️ Licença
Este software é distribuído sob a licença **GNU GPL v3**.

---
*Desenvolvido por Kuriakin Toscan | 2026*
