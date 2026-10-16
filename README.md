# iBirder 🐦
**IA para Birdwatching — Inteligência Artificial local a serviço da ciência cidadã.**

## 📖 Sobre o Projeto
O **iBirder** é uma ferramenta de código aberto para observadores de aves, ornitólogos e fotógrafos de natureza. Ele sugere a espécie a partir de uma foto, reúne informações de bases científicas, mostra o contexto geográfico do registro e grava tudo nos metadados da imagem.

A identificação roda **no seu computador**. Quando a IA local fica em dúvida, o app pode consultar o iNaturalist ou o Google Vision, usando as **suas** chaves de API.

## ✨ Principais Recursos
- **Identificação em cascata**: IA local primeiro (sem custo e sem internet). Abaixo de 70% de certeza, consulta o iNaturalist e, por fim, o Google Cloud Vision, se houver chaves configuradas.
- **Privacidade (BYOK)**: a foto só sai do computador na consulta à nuvem (cópia reduzida) ou no Google Lens, por ação do usuário.
- **Integração com o WikiAves**: nome popular, etimologia e características das espécies brasileiras.
- **Contexto geográfico**: município, estado, bioma (IBGE), endemismo no Brasil, mapa de ocorrência (GBIF) e vocalizações próximas ao local da foto.
- **Conservação**: IUCN, lista nacional (Portaria MMA 148/2022), CITES e avaliações estaduais e de outros países (iNaturalist).
- **Metadados científicos**: Darwin Core, palavras-chave hierárquicas (Lightroom/digiKam) e campos do Windows, com escolha dos campos a gravar.

## 🌟 Novidades na v1.3
- **Conservação completa**: lista nacional oficial (**Portaria MMA nº 148/2022**, ICMBio) e anexos da **CITES** embarcados, consultados sem internet. Novas **outras avaliações** do iNaturalist: listas estaduais (a do estado da foto em destaque) e de outros países.
- **Foto já processada**: ao abrir uma foto que já tem dados do iBirder, o app mostra o que foi gravado e quando, e pergunta se deve processar novamente ou ignorar.
- **Aviso de região**: se a IA local sugerir uma espécie sem registro no Brasil para uma foto do Brasil, o app consulta a nuvem ou avisa e mostra os candidatos que ocorrem no país (clicáveis).
- **Instalador menor**: partes do Qt que o app não usa (QML, 3D, gráficos, traduções do navegador interno) ficam de fora.

## 🌟 Novidades na v1.2
- **WikiAves mais rápido e preciso**: busca interna do próprio WikiAves, com validação do nome científico. Aves que não existem no WikiAves não recebem mais dados de outra espécie.
- **Etapas em paralelo**: biologia, geografia e taxonomia rodam ao mesmo tempo; uma falha no WikiAves não interrompe as demais etapas nem bloqueia a gravação.
- **Vocalizações**: novo player nativo que toca M4A, MP3 e WAV (antes, gravações M4A, quase metade das do iNaturalist, não tocavam).
- **Dados corrigidos**: endemismo no Brasil passa a vir do iNaturalist (antes, toda espécie saía "não endêmica"); ICMBio e CITES aparecem como "Não disponível" em vez de valores enganosos.
- **Metadados corrigidos**: Darwin Core gravado de fato; GPS no hemisfério correto; palavras-chave sem duplicação; os campos desmarcados no diálogo não são mais gravados; o autor da foto e os dados da câmera não são mais sobrescritos.
- **Mapa incremental**: carregado uma única vez, GBIF em segundo plano; arrastar o pino e clicar nos áudios voltaram a funcionar.
- **eBird embarcado**: link oficial, código e nome em inglês de 11 mil espécies sem internet.
- **Chaves de API**: novo passo a passo para leigos (inclui o faturamento exigido pelo Google) e botão **Testar Chaves** que explica o erro; antes, uma chave inválida do Google aparecia como válida.
- **Estabilidade**: resultados de uma foto anterior não se misturam com a atual; logs com rotação, chaves mascaradas e **Copiar diagnóstico** no menu de ajuda.
- **Segurança**: chaves de API não são mais distribuídas no instalador.
- **Build automático**: testes, autoteste do executável e instalador gerados pelo GitHub Actions.

## ⚠️ Limitações conhecidas
- A IA local reconhece **965 espécies do mundo todo**, das quais cerca de **230 ocorrem no Brasil**. Para as demais, a identificação local pode ser inconclusiva ou errada: use a nuvem (iNaturalist), a Busca Manual ou o Google Lens.
- As listas embarcadas (MMA, CITES, ocorrência no Brasil) refletem a data da versão; são atualizadas com `tools/atualizar_listas_conservacao.py`.
- O token do iNaturalist expira em cerca de 24 horas.

## 🛠️ Tecnologias e Fontes
- **IA local**: **MobileNetV2** quantizada (modelo "Birds V1" do Google AIY Vision, treinado com o iNaturalist), executada com o **LiteRT** (TensorFlow Lite).
- **Interface**: **Python 3.12** e **PySide6** (Qt 6).
- **Mapas e geografia**: **Leaflet** (embarcado), **OpenStreetMap**, **Nominatim** e polígonos de biomas do **IBGE**.
- **Fontes de dados**:
  - **WikiAves**: nome popular, etimologia e características.
  - **iNaturalist**: taxonomia, imagem de referência, vocalizações, status IUCN, avaliações regionais e endemismo no Brasil.
  - **MMA/ICMBio**: Portaria MMA nº 148/2022 (lista oficial embarcada).
  - **CITES**: Checklist oficial (Species+), embarcado.
  - **eBird / Clements (Cornell Lab)**: códigos, nomes em inglês e links oficiais (tabela embarcada).
  - **GBIF**: mapas de densidade de ocorrência.
- **Metadados**: **ExifTool** (Phil Harvey).

## 🚀 Instalação e Uso

### Para usuários (Windows 10/11, 64 bits)
1. Instale o **Google Chrome**, se ainda não tiver (usado para consultar o WikiAves).
2. Baixe o instalador mais recente em [Releases](https://github.com/KuriakinToscan/iBirder/releases) e execute `Instalador_iBirder_v1.3.exe`.
3. Abra uma foto arrastando-a para a janela, pelo botão **Nova Identificação** ou por **Abrir com > iBirder** no Windows Explorer.
4. (Opcional) Configure a identificação em nuvem na **engrenagem (⚙)**. O passo a passo está em [manual_apis_nuvem.md](manual_apis_nuvem.md).

O guia completo está no app (botão **?** > **Manual do usuário**) e em [guia_do_usuario.md](guia_do_usuario.md).

### Para desenvolvedores
Com `uv` (recomendado):
1. Clone o repositório.
2. `uv venv` e ative com `.\.venv\Scripts\Activate.ps1` (PowerShell).
3. `uv pip install -r requirements.txt`
4. `python main.py`

Também funciona em ambientes **conda** ou **venv**: basta `pip install -r requirements.txt` no ambiente ativo.

- **Testes**: `pip install pytest` e `python -m pytest tests`. Os testes não acessam a rede; os do mapa com QtWebEngine rodam com `IBIRDER_TESTES_GUI=1`.
- **Autoteste do app**: `python main.py --smoke-test` abre o app e verifica modelo, ExifTool, biomas, eBird, listas de conservação, áudio e mapa.
- **Teste real do WikiAves**: `python tools/testar_wikiaves.py` (o WikiAves bloqueia servidores; rode no seu computador).
- **Listas de conservação**: `python tools/atualizar_listas_conservacao.py [mma|cites|brasil]` regenera `assets/conservacao/` (exige internet e o `pdftotext`).
- **Build local**: `build.ps1` (PyInstaller + Inno Setup 6, se instalado).
- **Chaves de API**: ficam no `config.json` local, ignorado pelo Git. Use `config.example.json` como modelo.

### Publicar uma versão
1. Atualize `APP_VERSION` em `core/config.py` (única fonte da versão).
2. Integre na `main` e crie a tag: `git tag v1.3` e `git push origin v1.3`.
3. O GitHub Actions testa, gera o instalador e cria a Release automaticamente. A tag precisa ser igual a `v` + `APP_VERSION`.

## ⚖️ Licença
Este software é distribuído sob a licença **GNU GPL v3**. Componentes de terceiros: ExifTool (Artistic/GPL), Leaflet (BSD-2), PySide6/Qt (LGPL), modelo Birds V1 do Google (Apache 2.0).

---
*Desenvolvido por Kuriakin Toscan | 2026*
