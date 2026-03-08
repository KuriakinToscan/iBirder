# iBirder 🐦

**Transforme fotografias em registros científicos completos de forma automática, local e segura.**

O **iBirder** é uma ferramenta de código aberto projetada para automatizar o fluxo de trabalho de ornitólogos, observadores de aves e fotógrafos de natureza. Ele utiliza Inteligência Artificial de ponta para identificar espécies e enriquecer metadados fotográficos, transformando imagens simples em dados científicos prontos para catalogação.

---

## ✨ Principais Diferenciais

* **Edge AI (Privacidade Total):** Todo o processamento de imagem é realizado localmente no seu computador. Suas fotos nunca são enviadas para a nuvem para fins de identificação.
* **Otimizado para o Brasil:** Integração com o **WikiAves** para fornecer contexto biológico e etimológico específico da biodiversidade brasileira.
* **Inteligência Global:** Modelo treinado sobre a base do **iNaturalist Vision**, reconhecendo milhões de padrões de espécies de aves validados mundialmente.
* **Persistência Científica:** Gravação automática de dados nos padrões **EXIF/XMP** e **Darwin Core (DWC)**, garantindo compatibilidade com softwares de edição e gerenciamento de fotografias.

---

## 🚀 Como Funciona?

O iBirder simplifica o complexo processo de catalogação em um fluxo fluido:

1.  **Diagnóstico:** Ao carregar uma foto, o sistema extrai dados de GPS e data. Caso não existam, você pode definir a localização em um mapa interativo.
2.  **Identificação:** A rede neural **EfficientNet-V1.3** analisa a imagem localmente e sugere a espécie com base na confiança estatística.
3.  **Enriquecimento:** O software consulta bases como **GBIF, IUCN e WikiAves** para buscar status de conservação (ICMBio/CITES), biomas e até vocalizações (Xeno-Canto).
4.  **Gravação:** Com um clique, todas as informações são injetadas no arquivo original, organizadas em árvores hierárquicas de palavras-chave.

---

## 🛠️ Instalação e Requisitos

### Pré-requisitos
* **Python 3.9+**
* **ExifTool** (Obrigatório para a manipulação de metadados)

### Instalação
1. Clone o repositório:
   ```bash
   git clone [https://github.com/seu-usuario/ibirder.git](https://github.com/seu-usuario/ibirder.git)
   cd ibirder
