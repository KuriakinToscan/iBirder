# iBirder - Guia do Usuário

## Bem-vindo ao iBirder
### Estação ornitológica para identificar, contextualizar e catalogar fotografias de aves.

O **iBirder** transforma uma fotografia de ave em um registro organizado. Ele sugere a espécie, reúne informações de bases científicas (WikiAves, iNaturalist, eBird, GBIF, IUCN), mostra o contexto geográfico do registro e grava tudo nos metadados da foto, prontos para o Lightroom, o digiKam ou o Windows Explorer.

A identificação acontece **no seu computador**, com uma rede neural (**BioCLIP**, da Imageomics, treinada com milhões de fotos de seres vivos). As demais informações vêm da internet. Quando a IA local fica em dúvida, o iBirder pode, **se você configurar uma chave**, pedir uma segunda opinião ao iNaturalist ou ao Google Vision.

> **Saiba o alcance da IA local:** ela considera as cerca de **1.760 aves com registro no Brasil** e, em testes com fotos do iNaturalist, acertou a espécie na 1ª opção em **cerca de metade** das fotos. Confira sempre com a foto de referência, as vocalizações e a descrição, e use a **nuvem (iNaturalist)**, a **Busca Manual** ou o **Google Lens** quando necessário.

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
A IA local analisa a ave e mostra o **nome científico** e a **Certeza** (por exemplo, `92.3% (BioCLIP (Local))`). Se você roda o iBirder pelo código-fonte, a primeira identificação baixa o modelo (cerca de 90 MB); o instalador já o traz.

Se você configurou uma chave da nuvem (veja a seção 4), o iBirder **sempre** confirma a espécie na nuvem, porque a certeza da IA local não basta para separar acerto de erro. Sem nuvem (ou sem internet), o resultado local aparece como **sugestão**, com um aviso em amarelo para você conferir, e as outras candidatas como botões. Se a certeza local ficar abaixo de 30%, a identificação aparece como **inconclusiva**. Nesse caso:

- digite parte do nome científico ou do nome em inglês no campo **Nome Científico** (atalho **Ctrl+K**) e escolha uma das sugestões, ou digite o nome completo e pressione Enter; ou
- use o botão **Pesquisar com Google Lens**: a página do Lens abre no navegador; arraste a foto do iBirder para ela. **Nesse caso, a foto é enviada ao Google.**

Os **candidatos** sugeridos pela IA aparecem como botões, com a certeza de cada um: clique em um deles para buscar as informações dessa espécie.

**Aves do Brasil ou do mundo:** para fotos com GPS no Brasil, e para fotos sem GPS, a IA local considera só as espécies com registro no país (cerca de 1.760, lista do iNaturalist já instalada). Para fotos com GPS no exterior, ela considera as cerca de 11 mil espécies do mundo. Se você fotografa no exterior com uma câmera sem GPS, desmarque **Fotos sem GPS: considerar só aves do Brasil** em **Configurações (⚙)**.

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

### [ETAPA 8] Publicar no iNaturalist (opcional)
Clique em **Publicar no iNaturalist** para criar uma observação na **sua conta** do iNaturalist com a foto, a espécie, a data de captura e o local.

Antes do envio, uma janela mostra tudo o que será publicado:

- **Localização pública:** *Aberta* mostra a coordenada exata; *Ocultada* mostra um ponto aleatório numa área de cerca de 0,2° × 0,2° (a coordenada real fica guardada e só é compartilhada com quem você autorizar no iNaturalist); *Privada* não mostra nenhuma localização. Para espécies ameaçadas da lista nacional (CR, EN, VU) ou do Anexo I da CITES, o iBirder **sugere ocultar**.
- **Licença da observação:** o padrão é **CC BY**, que permite o reúso dos dados com crédito e o envio ao GBIF. Também há CC BY-NC e CC0.
- **Licença da foto:** segue a configuração da sua conta no iNaturalist. Recomendamos **CC BY-NC**.
- **Descrição:** texto livre, que pode ser editado.

Marque **"Conferi a espécie, a data e o local, e a foto é de minha autoria"** para liberar o botão **Publicar**. A identificação automática pode errar, e a observação fica pública.

Na primeira publicação, o navegador abre a página do iNaturalist para você **autorizar o iBirder**. Sua senha é digitada só no site do iNaturalist e nunca passa pelo iBirder. Depois disso, o iBirder lembra a autorização e só pede de novo quando ela expirar.

Ao terminar, o número da observação é gravado na foto (*iBirder > Publicacao > iNaturalist*). Se você tentar publicar a mesma foto de novo, o iBirder avisa, para não duplicar a observação.

> A foto precisa ter a **data de captura** (EXIF) e estar em **JPG ou PNG**. Sem localização, a observação é publicada, mas não chega ao grau de pesquisa do iNaturalist.

> **WikiAves:** os Termos de Uso do WikiAves proíbem envio automatizado. A publicação lá continua sendo feita por você, pelo site.

---

## 3. Botões do topo

- **Recarregar (↻):** limpa a análise atual.
- **Ajuda (?):** abre um menu com **Manual do usuário**, **Verificar atualizações**, **Copiar diagnóstico** (informações técnicas para enviar ao suporte, sem as suas chaves de API) e **Abrir pasta de logs**.
- **Configurações (⚙):** aparência (modo claro ou escuro, paleta de cores e layout), fotos sem GPS (considerar só aves do Brasil), chaves de API da identificação em nuvem e o aviso de novas versões.

### Atalhos de teclado

- **Ctrl+O:** abrir uma foto.
- **Ctrl+S:** gravar os dados na fotografia (quando o botão Gravar está liberado).
- **Ctrl+K:** ir para o campo **Nome Científico** e buscar uma espécie.
- **Ctrl+Shift+O:** abrir uma pasta na fila de fotos (layouts **Trilha**, **Mesa de luz**, **Quadro da sessão**, **Foco** e **Mesa de trabalho**).
- **←** e **→:** foto anterior e seguinte da pasta (layouts **Mesa de luz** e **Foco**).
- No layout **Foco**: **I** abre e fecha a ficha, **F** mostra ou esconde a fila, **+**, **−** e **0** dão zoom na foto (ou a roda do mouse), **?** ou **F1** mostra a lista de atalhos e **Esc** fecha o que estiver aberto.
- **Alt+→** e **Alt+←:** avançar e voltar uma etapa (layout **Trilha**).

### Aparência

Em **Configurações (⚙) > Aparência**, o **Modo** escolhe entre claro e escuro:

- **Igual ao Windows:** o iBirder acompanha o modo do Windows (Configurações > Personalização > Cores) e muda sozinho, com o programa aberto, quando o Windows muda.
- **Claro** ou **Escuro:** fica sempre assim, qualquer que seja o modo do Windows.

A **Paleta de cores** escolhe as cores, e cada uma tem versão clara e escura:

- **Off-White:** o visual de sempre, cinza-grafite.
- **Clean:** letras mais leves e verde-petróleo só nos botões principais.
- **Clássico:** papel creme e títulos com serifa, como num guia de campo.
- **Gralha-azul:** azul sobre fundo neutro.
- **Sabiá:** ferrugem, a cor do peito do sabiá-laranjeira, sobre fundo areia.
- **Alto contraste:** preto, branco e amarelo, para quem enxerga pouco.

As bolinhas ao lado de cada paleta mostram o fundo, os quadros e a cor dos botões no modo em uso. No modo escuro, o mapa também fica escuro; os pinos e as cores de densidade não mudam.

No mesmo quadro, **Layout** escolhe a arrumação da tela:

- **Trilha** (padrão de quem instala a partir da v1.6): um assistente em cinco etapas, **Escolher a foto › Identificar › Conferir a espécie › Conhecer a ave › Gravar e publicar**, com a trilha sempre à vista à esquerda e um botão principal por tela. Abrir uma foto já leva à identificação, e o resultado já leva à conferência. **Continuar** avança, **Voltar** retorna sem apagar nada, e as etapas já liberadas podem ser abertas direto pela trilha. Na primeira etapa dá para abrir uma pasta inteira, como na Mesa de trabalho. Na etapa Conferir, as espécies mais prováveis aparecem com foto de referência; **É esta** confirma e segue.
- **Cartões de escolha:** a sua foto ao lado das três espécies mais prováveis, cada uma com uma foto de referência do iNaturalist (com o nome do autor e a licença). Compare a plumagem e o bico e clique em **É esta**; se não for nenhuma, digite o nome no campo abaixo dos cartões. A ficha da espécie abre em seguida, com o mapa e os botões de gravar e publicar. **Trocar espécie** volta aos cartões.
- **Mesa de luz:** para uma pasta inteira, como num editor de fotos: a foto grande no centro, a fila numa tira embaixo e, à direita, a identificação e as seções da ficha, que abrem uma por vez. As setas **←** e **→** trocam de foto; **Pular** e **Ir para a próxima ao gravar** ficam na tira.
- **Quadro da sessão:** a pasta da saída de campo em colunas: **Na fila**, **Conferindo agora**, **Gravadas** e **Puladas**, com o número de espécies e de fotos gravadas. A foto aberta aparece numa gaveta à direita (abas **Conferir** e **Ficha**); **Fechar** recolhe a gaveta, e um clique duplo no cartão da foto a traz de volta. Em **Sessões anteriores**, um clique reabre uma pasta usada antes.
- **Foco:** a foto ocupa a janela, com zoom pela roda do mouse e arrasto. O resultado fica numa faixa sobre a foto, com **Ficha ›** e o botão de gravar; a ficha (comparar com a referência, sobre, classificação, mapa e sons) entra pela direita. Com uma pasta aberta, a fila aparece à esquerda. Feito para quem usa o teclado: o botão **? Atalhos** lista as teclas.
- **Painel completo:** tudo visível numa grade de três colunas, com rolagem.
- **Fluxo guiado:** uma etapa por vez. A barra no alto mostra **Foto › Identificação › Conferir › Gravar** e diz o que fazer em seguida; descrição, classificação, mapa e sons ficam em abas, sem rolar a janela.
- **Ficha compacta:** tudo numa tela, em três colunas (fotos; ficha da espécie; mapa e sons), cada coluna com rolagem própria.
- **Mesa de trabalho:** para uma pasta inteira de fotos, como a de uma saída de campo (veja abaixo).

Modo, paleta e layout mudam na hora, enquanto você escolhe. **Animações** liga ou desliga o deslizar das gavetas (desligue em computadores lentos ou se o movimento incomodar). **Salvar** mantém a escolha; **Cancelar** volta ao que estava antes.

### Mesa de trabalho: uma pasta em fila

1. Escolha o layout **Mesa de trabalho** e clique em **Abrir pasta...** no painel **Fila de fotos** (ou **Ctrl+Shift+O**).
2. O iBirder lista as fotos JPG e PNG da pasta (sem subpastas), com miniaturas, e confere quais já têm dados gravados pelo iBirder: essas aparecem como **✓ Já tinha registro** e ficam fora da fila.
3. A primeira foto pendente abre sozinha. Confira a espécie e clique em **Gravar Dados na Fotografia** (**Ctrl+S**).
4. Com **Ir para a próxima ao gravar** marcado, a próxima foto pendente abre logo depois da gravação, sem o aviso de sucesso a cada foto. A lista mostra cada foto como **✓ Gravada**, com a espécie e o novo nome, se ela foi renomeada.
5. **Pular** deixa a foto para depois. Para voltar a qualquer foto, clique duas vezes nela na lista.

> A identificação continua sendo feita uma foto por vez, a que está aberta: o iBirder não consulta o WikiAves em lote.

### Novas versões

Ao abrir, o iBirder confere no GitHub, no máximo uma vez por dia, se há versão nova. Quando há, aparece uma janela com as novidades e os botões **Baixar instalador**, **Ver no GitHub**, **Lembrar depois** e **Ignorar esta versão**, e um aviso fica na barra inferior. Para atualizar, baixe e execute o instalador: suas configurações e chaves de API são mantidas.

- Para conferir na hora, use **Ajuda (?) > Verificar atualizações**.
- Para desligar o aviso, desmarque **"Avisar quando houver nova versão do iBirder"** na engrenagem (⚙).

---

## 4. Identificação em nuvem (opcional)

Com uma chave configurada, o iBirder confirma toda identificação no **iNaturalist** (recomendado, grátis) e, se preciso, no **Google Cloud Vision** (exige conta com faturamento no Google Cloud). Você usa as **suas próprias chaves**, e só uma cópia reduzida da foto (até 1024 pixels, sem metadados) é enviada.

Para configurar, clique na **engrenagem (⚙)** e depois em **"Como obter essas chaves? (passo a passo)"**. O botão **Testar Chaves** diz exatamente o que falta quando algo não está certo.

> **DICA PRO:** no Brasil, configurar o iNaturalist faz bastante diferença, porque a IA local acerta cerca de metade das fotos e a nuvem confirma a espécie.

---

## 5. Privacidade: o que sai do seu computador

- **A foto:** só sai se você usar a identificação em nuvem (cópia reduzida, para o serviço configurado) ou o Google Lens.
- **As coordenadas:** são enviadas ao OpenStreetMap (Nominatim) para descobrir país, estado e município.
- **O nome da espécie:** é enviado ao WikiAves, iNaturalist, GBIF e eBird para buscar as informações.
- **Chaves de API:** ficam só no seu computador e nunca aparecem nos logs nem no diagnóstico.
- **Publicação no iNaturalist:** só acontece quando você clica em **Publicar** e confirma. São enviados a foto original (com os metadados), a espécie, a data, as coordenadas e a descrição, para a sua conta. A autorização fica guardada só no seu computador.
- **Novas versões:** a consulta ao GitHub informa só a versão do iBirder em uso (como em qualquer acesso à internet, o GitHub recebe o seu endereço IP). Pode ser desligada na engrenagem (⚙).

---

## 6. Solução de problemas

- **"WikiAves inacessível no momento":** verifique se o Google Chrome está instalado e se há internet. As outras informações continuam disponíveis.
- **Aviso "Sugestão da IA local":** confira a espécie com a foto de referência e as outras candidatas, ou configure o iNaturalist para a confirmação automática.
- **Ave vagante ou foto do exterior sem GPS:** a IA local só sugere aves com registro no Brasil. Use a Busca Manual, ou desmarque a opção de fotos sem GPS em Configurações (⚙).
- **Identificação inconclusiva em espécie comum:** a foto pode estar distante, escura ou com a ave encoberta. Use a Busca Manual ou configure o iNaturalist.
- **Vocalização não toca:** a janela mostra o motivo e o botão **Abrir no navegador**.
- **Erro ao testar as chaves:** siga a mensagem do botão **Testar Chaves** e o passo a passo da engrenagem (⚙).
- **Publicação no iNaturalist:** "porta 8913 ocupada" significa que outro programa usa a porta do retorno da autorização: feche-o e tente de novo. Se a foto não for enviada, a observação já existe: anexe a foto pela página da observação, sem publicar de novo. Se aparecer "Publicação indisponível", esta versão do iBirder ainda não foi registrada no iNaturalist.
- **Qualquer outro problema:** use **Ajuda (?) > Copiar diagnóstico** e envie o texto ao suporte.
