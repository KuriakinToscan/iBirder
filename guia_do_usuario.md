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

**Foto já processada:** se a foto já tiver dados gravados pelo iBirder, uma janela mostra **o que foi gravado** (espécie, local, conservação, comentário) e **quando** (data e versão do iBirder). Escolha **Processar novamente** para refazer a análise ou **Ignorar** para deixar a foto como está. Ao gravar de novo, os dados antigos do iBirder são substituídos, sem duplicar.

### [ETAPA 2] Identificação da espécie
A IA local analisa a ave e mostra o **nome científico** e a **Certeza** (por exemplo, `92.3% (MobileNetV2 (Local))`).

Se a certeza ficar **abaixo de 70%**, o iBirder consulta a nuvem, caso você tenha configurado uma chave (veja a seção 4). Se ainda assim não houver resultado confiável, a identificação aparece como **inconclusiva**. Nesse caso:

- digite o nome científico no campo de **Busca Manual** e clique na lupa; ou
- use o botão **Pesquisar com Google Lens**: a página do Lens abre no navegador; arraste a foto do iBirder para ela. **Nesse caso, a foto é enviada ao Google.**

Os **candidatos** sugeridos pela IA aparecem como links: clique em um deles para buscar as informações dessa espécie.

**Aviso de região:** se a foto foi tirada no Brasil e a IA sugerir uma espécie **sem registro no país** (por exemplo, uma ave da América do Norte), o iBirder tenta a nuvem e, sem ela, mostra um aviso em amarelo com os candidatos que ocorrem no Brasil. A verificação usa uma lista de cerca de 1.750 espécies com registro no Brasil (iNaturalist), já instalada.

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
- **Brasil (ICMBio/MMA):** lista oficial de espécies ameaçadas (**Portaria MMA nº 148/2022**), já instalada e consultada sem internet. Mostra a categoria (ex.: *Vulnerável (VU)*), "Não ameaçada" ou, quando só uma subespécie está na lista, qual é ela.
- **CITES:** anexo da convenção sobre comércio internacional (*Anexo I*, *II* ou *III*), conforme o Checklist oficial da CITES, também já instalado.
- **Outras avaliações (iNaturalist):** listas estaduais brasileiras e de outros países, com link para a fonte. A lista do **estado da foto** aparece primeiro, marcada com ★.

As listas instaladas são atualizadas a cada nova versão do iBirder.

### [ETAPA 7] Gravar na fotografia
Clique em **Gravar Dados na Fotografia** e escolha os campos que deseja gravar. Só os campos marcados e com informação conhecida são gravados.

O iBirder usa o **ExifTool** e grava:

- **Darwin Core** (`dwc:scientificName`, `dwc:family`, `dwc:order`...), padrão internacional de dados de biodiversidade;
- **palavras-chave hierárquicas** (ex.: *iBirder > Taxonomia > Family > Tyrannidae*), que viram filtros no Lightroom e no digiKam;
- **título, descrição e palavras-chave** visíveis no Windows Explorer;
- **coordenadas GPS**, apenas se a foto ainda não tiver GPS próprio;
- **data da gravação e versão do iBirder**, usadas para avisar quando a foto for aberta de novo.

**Renomear o arquivo (opcional):** marque **Renomear o arquivo** no mesmo diálogo. O nome sugerido segue o padrão **NomeComum_aaaammdd**, com o nome comum sem acentos e cada palavra começando com maiúscula, e a data de captura da foto:

- *Sabiá-laranjeira*, foto de 16/10/2026 → `SabiaLaranjeira_20261016.jpg`
- outra foto do mesmo dia → `SabiaLaranjeira_20261016_2.jpg` (o iBirder nunca sobrescreve um arquivo)

Também há os padrões com a hora (`NomeComum_aaaammdd_hhmmss`) e com o nome científico (`NomeCientifico_aaaammdd`). O nome pode ser editado antes de gravar, e a prévia mostra o nome final. Se a foto não tiver data de captura, complete a data no nome. Arquivos RAW e `.xmp` com o mesmo nome da foto podem ser renomeados junto. O iBirder lembra a sua escolha para as próximas fotos.

**O nome original nunca se perde.** Ele fica guardado:

- nos **comentários** da foto ("Arquivo original: IMG_0042.jpg"), visíveis em *Propriedades > Detalhes* no Windows;
- na palavra-chave *iBirder > Arquivo > NomeOriginal*, para buscar a foto pelo nome da câmera no Lightroom ou no digiKam;
- no campo padrão de nome original (*Preserved File Name*) da foto e do `.xmp` do RAW, que o iBirder cria se não existir (o arquivo RAW em si nunca é alterado);
- no histórico `renomeacoes.csv`, na pasta de logs (**Ajuda (?) > Abrir pasta de logs**), que abre no Excel.

Antes de renomear, o iBirder confere se o nome original foi mesmo gravado na foto. Para **voltar ao nome original**, abra a foto no iBirder: o aviso de foto já processada mostra o botão **Desfazer renomeação**, que também volta o RAW e o `.xmp`.

> **Usa o Lightroom?** Renomeie pelo próprio Lightroom: um arquivo renomeado fora dele aparece como "ausente" no catálogo.

> **O arquivo original é alterado.** Mantenha um backup das suas fotos. O iBirder não altera o autor da foto nem os dados da câmera, e gravar duas vezes a mesma foto não duplica as palavras-chave.

---

## 3. Botões do topo

- **Recarregar (↻):** limpa a análise atual.
- **Ajuda (?):** abre um menu com **Manual do usuário**, **Verificar atualizações**, **Copiar diagnóstico** (informações técnicas para enviar ao suporte, sem as suas chaves de API) e **Abrir pasta de logs**.
- **Configurações (⚙):** aparência (tema), chaves de API da identificação em nuvem e o aviso de novas versões.

### Aparência

Em **Configurações (⚙) > Aparência**, escolha um dos três temas:

- **Off-White:** o visual de sempre, cinza-grafite sobre fundo claro.
- **Clean:** fundo branco, letras mais leves e verde-petróleo só nos botões principais.
- **Clássico:** papel creme e títulos com serifa, como num guia de campo.

No mesmo quadro, **Layout** escolhe a arrumação da tela. Hoje há o **Painel completo** (tudo visível numa grade de três colunas); os layouts **Fluxo guiado**, **Ficha compacta** e **Mesa de trabalho** chegam nas próximas versões.

Tema e layout mudam na hora, enquanto você escolhe. **Salvar** mantém a escolha; **Cancelar** volta ao que estava antes.

### Novas versões

Ao abrir, o iBirder confere no GitHub, no máximo uma vez por dia, se há versão nova. Quando há, aparece uma janela com as novidades e os botões **Baixar instalador**, **Ver no GitHub**, **Lembrar depois** e **Ignorar esta versão**, e um aviso fica na barra inferior. Para atualizar, baixe e execute o instalador: suas configurações e chaves de API são mantidas.

- Para conferir na hora, use **Ajuda (?) > Verificar atualizações**.
- Para desligar o aviso, desmarque **"Avisar quando houver nova versão do iBirder"** na engrenagem (⚙).

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
- **Novas versões:** a consulta ao GitHub informa só a versão do iBirder em uso (como em qualquer acesso à internet, o GitHub recebe o seu endereço IP). Pode ser desligada na engrenagem (⚙).

---

## 6. Solução de problemas

- **"WikiAves inacessível no momento":** verifique se o Google Chrome está instalado e se há internet. As outras informações continuam disponíveis.
- **Aviso "sem registro no Brasil":** confira os candidatos sugeridos ou use a Busca Manual; se a ave for realmente uma raridade (vagante), mantenha a identificação.
- **Identificação inconclusiva em espécie comum:** a espécie pode não estar entre as que a IA local conhece. Use a Busca Manual ou configure o iNaturalist.
- **Vocalização não toca:** a janela mostra o motivo e o botão **Abrir no navegador**.
- **Erro ao testar as chaves:** siga a mensagem do botão **Testar Chaves** e o passo a passo da engrenagem (⚙).
- **Qualquer outro problema:** use **Ajuda (?) > Copiar diagnóstico** e envie o texto ao suporte.
