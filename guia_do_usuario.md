# iBirder - Guia do Usuário

## Bem-vindo ao iBirder
### Estação ornitológica para identificar, contextualizar e catalogar fotografias de aves.

O **iBirder** transforma uma fotografia de ave em um registro organizado. Ele sugere a espécie, reúne informações de bases científicas (WikiAves, iNaturalist, eBird, GBIF, IUCN), mostra o contexto geográfico do registro e grava tudo nos metadados da foto, prontos para o Lightroom, o digiKam ou o Windows Explorer.

A identificação acontece **no seu computador**, com uma rede neural (**MobileNetV2**, modelo "Birds V1" do Google, treinado com fotos do **iNaturalist**). As demais informações vêm da internet. Quando a IA local fica em dúvida, o iBirder pode, **se você configurar uma chave**, pedir uma segunda opinião ao iNaturalist ou ao Google Vision.

> **Saiba o alcance da IA local:** ela reconhece **965 espécies de aves do mundo todo** (a maioria da América do Norte). Cerca de **230 delas ocorrem no Brasil**. Para as demais espécies, a sugestão local pode ser inconclusiva ou incorreta: confira sempre com a foto de referência, as vocalizações e a descrição, e use a **nuvem (iNaturalist)**, a **Busca Manual** ou o **Google Lens** quando necessário.

---

## 1. Requisitos

- **Windows 10 ou 11 (64 bits).**
- **Google Chrome instalado:** usado, sem abrir janelas, para consultar o WikiAves.
- **Internet:** necessária para mapas, WikiAves, vocalizações e dados de conservação. A identificação local e a gravação dos metadados funcionam sem internet.

---

## 2. Passo a passo

### [ETAPA 1] Abrir a fotografia
Arraste a foto para a área **Imagem Pesquisada** ou clique em **Nova Identificação**. Também é possível usar **Abrir com > iBirder** no Windows Explorer.

O iBirder lê os metadados da foto: **coordenadas GPS**, **autor** e **data/hora** do registro. Fotos verticais são analisadas na orientação correta.

### [ETAPA 2] Identificação da espécie
A IA local analisa a ave e mostra o **nome científico** e a **Certeza** (por exemplo, `92.3% (MobileNetV2 (Local))`).

Se a certeza ficar **abaixo de 70%**, o iBirder consulta a nuvem, caso você tenha configurado uma chave (veja a seção 4). Se ainda assim não houver resultado confiável, a identificação aparece como **inconclusiva**. Nesse caso:

- digite o nome científico no campo de **Busca Manual** e clique na lupa; ou
- use o botão **Pesquisar com Google Lens**: a página do Lens abre no navegador; arraste a foto do iBirder para ela. **Nesse caso, a foto é enviada ao Google.**

### [ETAPA 3] Localização e mapa
Com GPS na foto, o pino vermelho marca o local no mapa. Sem GPS, aparece o aviso **"Sem dados de localização, indique manualmente aqui"**: clique nele e pesquise o local pelo nome.

**Arraste o pino** para ajustar o local; os dados geográficos e as vocalizações são recalculados. No canto do mapa, escolha as camadas **Mapa** ou **Satélite** e ative **Dist. Geográfica (GBIF)** (densidade de registros da espécie) e **Vocalizações** (local das gravações).

O card **Dados Geográficos** mostra país, estado e município (OpenStreetMap), o **bioma** (polígonos do IBGE, calculado no próprio computador) e se a espécie é **endêmica do Brasil**, nativa ou introduzida (iNaturalist).

### [ETAPA 4] Informações da espécie
Ao mesmo tempo, o iBirder busca:

- **WikiAves:** nome popular, nome em inglês, etimologia e características. A busca usa o próprio WikiAves e confere o nome científico; espécies que não existem no WikiAves não recebem dados de outra ave.
- **Taxonomia:** classe, ordem, família e gênero (iNaturalist), nome em inglês e link oficial do **eBird** (tabela com 11 mil espécies, já instalada).
- **Imagem de referência:** foto da espécie no iNaturalist, com os créditos do autor.

Se o WikiAves estiver indisponível, os campos mostram o aviso e as demais informações continuam normalmente.

### [ETAPA 5] Vocalizações
O iBirder seleciona **3 gravações do iNaturalist**, priorizando as mais próximas do local da foto: mesmo município, mesmo estado, até 150 km, Brasil e, por fim, outros países. Entre as próximas, ficam as mais bem avaliadas.

Clique em uma vocalização para abrir os detalhes: o player toca gravações **M4A, MP3 e WAV**, e o botão **Abrir Registro** leva à observação original no iNaturalist.

### [ETAPA 6] Conservação
- **IUCN (global):** categoria da Lista Vermelha (via iNaturalist).
- **ICMBio (nacional) e CITES:** aparecem como **"Não disponível"** nesta versão, pois essas listas ainda não estão integradas. Consulte o [SALVE/ICMBio](https://salve.icmbio.gov.br) e o [Species+ (CITES)](https://speciesplus.net) quando precisar dessas informações.

### [ETAPA 7] Gravar na fotografia
Clique em **Gravar Dados na Fotografia** e escolha os campos que deseja gravar. Só os campos marcados e com informação conhecida são gravados.

O iBirder usa o **ExifTool** e grava:

- **Darwin Core** (`dwc:scientificName`, `dwc:family`, `dwc:order`...), padrão internacional de dados de biodiversidade;
- **palavras-chave hierárquicas** (ex.: *iBirder > Taxonomia > Family > Tyrannidae*), que viram filtros no Lightroom e no digiKam;
- **título, descrição e palavras-chave** visíveis no Windows Explorer;
- **coordenadas GPS**, apenas se a foto ainda não tiver GPS próprio.

> **O arquivo original é alterado.** Mantenha um backup das suas fotos. O iBirder não altera o autor da foto nem os dados da câmera, e gravar duas vezes a mesma foto não duplica as palavras-chave.

---

## 3. Botões do topo

- **Recarregar (↻):** limpa a análise atual.
- **Ajuda (?):** abre um menu com **Manual do usuário**, **Copiar diagnóstico** (informações técnicas para enviar ao suporte, sem as suas chaves de API) e **Abrir pasta de logs**.
- **Configurações (⚙):** chaves de API da identificação em nuvem.

---

## 4. Identificação em nuvem (opcional)

Quando a IA local tem menos de 70% de certeza, o iBirder pode consultar o **iNaturalist** (recomendado, grátis) e o **Google Cloud Vision** (exige conta com faturamento no Google Cloud). Você usa as **suas próprias chaves**, e só uma cópia reduzida da foto (até 800 pixels, sem metadados) é enviada.

Para configurar, clique na **engrenagem (⚙)** e depois em **"Como obter essas chaves? (passo a passo)"**. O botão **Testar Chaves** diz exatamente o que falta quando algo não está certo.

> **DICA PRO:** no Brasil, configurar o iNaturalist faz bastante diferença, porque a IA local conhece só uma parte das espécies brasileiras.

---

## 5. Privacidade: o que sai do seu computador

- **A foto:** só sai se você usar a identificação em nuvem (cópia reduzida, para o serviço configurado) ou o Google Lens.
- **As coordenadas:** são enviadas ao OpenStreetMap (Nominatim) para descobrir país, estado e município.
- **O nome da espécie:** é enviado ao WikiAves, iNaturalist, GBIF e eBird para buscar as informações.
- **Chaves de API:** ficam só no seu computador e nunca aparecem nos logs nem no diagnóstico.

---

## 6. Solução de problemas

- **"WikiAves inacessível no momento":** verifique se o Google Chrome está instalado e se há internet. As outras informações continuam disponíveis.
- **Identificação inconclusiva em espécie comum:** a espécie pode não estar entre as que a IA local conhece. Use a Busca Manual ou configure o iNaturalist.
- **Vocalização não toca:** a janela mostra o motivo e o botão **Abrir no navegador**.
- **Erro ao testar as chaves:** siga a mensagem do botão **Testar Chaves** e o passo a passo da engrenagem (⚙).
- **Qualquer outro problema:** use **Ajuda (?) > Copiar diagnóstico** e envie o texto ao suporte.
