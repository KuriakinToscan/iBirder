# iBirder 🐦
**IA para Birdwatching — Inteligência Artificial local a serviço da ciência cidadã.**

## 📖 Sobre o Projeto
O **iBirder** é uma ferramenta de código aberto desenvolvida para ornitólogos, observadores de aves e fotógrafos de natureza. Com foco em **Edge AI**, o sistema processa identificações de espécies e metadados de forma 100% local, garantindo privacidade e velocidade sem depender de servidores externos ou conexão constante à internet.

## ✨ Principais Diferenciais
- **Privacidade Total (Edge AI)**: O processamento de imagem ocorre na sua máquina. Suas fotos originais nunca saem do seu computador para fins de identificação.
- **Otimizado para o Brasil**: Integração profunda com o **WikiAves** para etimologia e contexto biológico da nossa biodiversidade.
- **Identificação Global**: Modelo treinado sobre a base do **iNaturalist Vision**, reconhecendo espécies validadas por especialistas no mundo todo.
- **Persistência Científica**: Gravação de metadados nos padrões **EXIF/XMP**, **Darwin Core (DWC)** e palavras-chave hierárquicas.

## 🛠️ Tecnologias e Fontes
O iBirder integra as bibliotecas biológicas e tecnologias mais respeitadas do ecossistema científico:

- **AI Engine**: Rede Neural **EfficientNet-V1.3** (Google Research).
- **Interface**: Desenvolvido em **Python 3.13** com **PySide6**.
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
2. Execute o instalador `iBirder_v1.0.3_Setup.exe`.
3. O app permite abrir fotos via "Arraste e Solte" ou diretamente pelo botão direito no Windows Explorer.

### Para Desenvolvedores
```bash
# Clone o repositório
git clone https://github.com/KuriakinToscan/iBirder.git

# Crie e ative o ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute o aplicativo
python main.py

# Scripts de ML Ops (Pipeline de Dados iNaturalist AWS)
python scripts/etl_inaturalist_aws.py
python scripts/train_neotropical_model.py
```

## 🧠 Roadmap do Modelo Neotropical (v1.1.0)
- **Base de Treinamento**: iNaturalist Open Data (AWS S3) + GBIF.
- **Espécies Cobertas**: 1.980+ espécies de aves brasileiras.
- **Validação Geoespacial**: Cruzamento de biomas em tempo real (Pampa, Cerrado, Mata Atlântica, Caatinga, Amazônia, Pantanal).

## ⚖️ Licença
Este software é distribuído sob a licença **GNU GPL v3**.

---
*Desenvolvido por Kuriakin Toscan | 2026*
