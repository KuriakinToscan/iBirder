# Mapeamento de Elementos da Interface (Janela Principal)

Os elementos visuais da tela inicial do aplicativo `iBirder` estão rigidamente divididos em três grupos, visando obedecer às diretrizes arquiteturais e estéticas do sistema:

---

## 1. CABEÇALHO (Layout Header)
Contêiner principal do topo da aplicação, englobador de branding e controles de estado globais.

* **Logo da Aplicação (`lbl_logo`)**: Exibe o ícone ou logotipo oficial da aplicação (`logo_ave.svg`) na margem superior esquerda.
* **Slogan / Subtítulo (`lbl_slogan`)**: Exibe o texto "IA para Birdwatching", complementando a marca visualmente (O texto "iBirder" verde foi removido).
* **Botão Recarregar (`btn_reload`)**: Posicionado à direita, permite limpar e resetar toda a interface de pesquisa.
* **Botão Ajuda (`btn_ajuda`)**: Dispara a abertura do manual de instruções (`JanelaManual`).

---

## 2. CARDS (Grupos de Informação)
Placas lógicas ou cartões (QFrames com Sombra) contendo bordas delineadas que concentram os dados informativos e as mídias. **Nenhum botão de ação compõe a estrutura interna desses Cards.**

O padrão geométrico e visual consolidado para *todos* os mini-cards informativos laterais é exato, replicado do modelo de "Dados Geográficos":
- Container: Base Branca
- Sombra Tênue: `QGraphicsDropShadowEffect(blur=20, offset=(0,5), alpha=20)`
- Margens Internas: Topo `18px`, Laterais e Base `12px`.
- Título da Sessão: Destacado com padding bottom base de controle.

### Cards Superiores
* **Card da Imagem Pesquisada (`card_user`)**: Área principal de visualização (`ImageCardWidget`) e _drag and drop_ da fotografia original fornecida pelo usuário.
* **Card da Imagem de Referência (`card_ref`)**: Painel (`ImageCardWidget`) que exibe visualmente uma ave da espécie identificada na internet, servindo de amostra comparativa.

### Coluna Direita (Resultados Individuais e Sem Fundo Contêiner)
Não existe mais um contêiner gigante abraçando o painel direito. Os blocos de resultados empilham-se como mini-cards ou cartões modulares:

* **Card de Identificação (`grupo_resultados`)**: Card primário com sombreamento individual que abriga:
  - **Identificação da Busca**: O Input Manual de pesquisa (`input_especie`) acionado com lupa.
  - **Nome Científico (`lbl_titulo_nc`)**: Padronizado em itálico ou destacado.
  - **Nome Comum e Inglês (`lbl_nome_comum` e `lbl_nome_ingles`)**: Linha de texto simples do nome popular e inglês. Ambos nascem afixados com a instrução ("*Aguardando a identificação...*") em itálico até que a IA e os extratores assíncronos (eBird) a preencham. O `lbl_nome_ingles` utiliza fonte secundária (cinza) para destaque.
* **Card de Etimologia (`grupo_etimologia`)**: Possui seu próprio painel e sombra e é inteiramente dedicado para documentar a procedência onomástica do termo científico, comportando o campo longo de texto (`txt_etimologia`) e o sub-box com detalhes (`frame_etimologia`).
* **Card de Taxonomia (`grupo_taxonomia`)**: Novo card posicionado imediatamente após a etimologia. Formata hierarquicamente a base biológica em (Classe, Ordem, Família e Gênero) oriundos da caderneta de campo do eBird, exibindo os dados com espaçamento ampliado de 150%. 
* **Card de Status de Conservação (`grupo_conservacao`)**: Card que herda os espaçamentos padrão, inserido logo antes dos Dados Geográficos e reservado (aguardando injeção futura) para descrever métricas de risco da espécie identificada.
* **Card de Dados Geográficos (`grupo_geo`)**: Moldura dedicada, autônoma, para os registros textuais biológicos, estado de conservação ou sumário de localização textual (`lbl_geo_details`).
* **Card de Vocalizações (`grupo_audio`)**: Espaço de mídia autônomo e envolto em seu próprio frame com sombra (`lbl_audio_placeholder`) por onde tocará a vocalização primária.

### Bloco Inferior (Card Único / Área)
* **Descrição da Espécie (`txt_descricao`)**: Amplo campo de texto _RichText_ (apenas leitura) contendo toda a base descritiva do WikiAves, flutuando abaixo da linha de imagens principal.
* **Mapa Geográfico (`map_principal`)**: O visualizador Folium (`MapWidget`) que plota os pinos de incidência, ocorrência e áudios globais.

---

## 3. BOTÕES (Acionadores de Eventos Soltos)
As ações do sistema habitam restritamente fora dos sub-painéis "Cards", flutuando isoladamente no fundo invisível ou em layouts ("Gaps") de espaçamento entre os cartões. O estilo de todos esses componentes de botão principal é definido com o **Padrão Extra-Slim (Altura fixa máxima de 26px e bold)** unificados pela folha de estilo global.

* **Botões Relacionados às Imagens (Acoplados Abaixo dos Cards Superiores):**
  - **Pesquisar com Google Lens (`btn_google_lens`)**: Subjacente à Imagem do Usuário.
  - **Abrir Fonte (`btn_fonte`)**: Alocado sob a Imagem de Referência.

* **Botões de Encaminhamento Direto (Flutuando logo após o término do Card de "Identificação Biológica" e anterior ao Card de "Etimologia"):**
  - **Botão WikiAves (`btn_wiki`)**: Aciona enciclopédia rústica WikiAves baseado no binomial formatado.
  - **Botão eBird (`btn_ebird`)**: Consulta no eBird os dados da espécie detectada.
  - **Botão Google (`btn_google`)**: Executa busca aberta online.

* **Botão Analítico Separado:**
  - **Botão Gravar Dados na Fotografia (`btn_gravar_exif`)**: Confirma a análise isoladamente no fluxo, solto sob a última seção.

* **Botões do Bloco Inferior:**
  - **Botão Nova Identificação (`btn_nova`)**: Alinhado perfeitamente logo após a leitura "Descrição da Espécie". Remete à reabertura do seletor, zerando a aplicação para o próximo input.
