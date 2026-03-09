# iBirder - Guia do Usuário

## Bem-vindo ao iBirder
### Estação ornitológica inteligente para análise e catalogação de fotografias de aves.

O **iBirder** é uma plataforma de ponta desenvolvida para converter fotografias em registros científicos rigorosos. O sistema automatiza a identificação de espécies e enriquece cada imagem com dados taxonômicos, status de conservação e distribuição geográfica, entregando uma análise biológica completa em instantes. Ao integrar essas informações diretamente aos metadados EXIF/XMP, o iBirder otimiza a organização e a catalogação de acervos fotográficos ornitológicos.

Priorizando a transparência e segurança, o **iBirder** é construído sobre tecnologias de **software livre** e opera sob o conceito de **Edge AI**. Isso garante que tanto o processamento de inteligência artificial quanto a gravação de metadados ocorram de forma estritamente local. Suas fotografias originais nunca saem do seu computador para fins de identificação. O acesso à rede é restrito a consultas em bibliotecas biológicas globais e carregamento de mapas, assegurando que a privacidade e o controle total dos dados permaneçam sempre em suas mãos.

O iBirder utiliza a rede neural convolucional (CNN) **EfficientNet-V1.3** desenvolvida pelo Google Research, e foi escolhida devido ao seu equilíbrio entre precisão, leveza e eficiência. Esta IA é poderosa o suficiente para distinguir espécies muito parecidas, mas leve o suficiente para rodar no seu computador sem precisar de supercomputadores ou internet.


O **modelo de identificação** foi treinado com a robusta base de dados do **iNaturalist Vision**, um dos sistemas de inteligência artificial mais respeitados no mundo científico por ser "treinado por humanos para ajudar humanos", aprendendo a reconhecer espécies a partir de milhões de registros do **iNaturalist** validados por especialistas e cientistas cidadãos ao redor do mundo. 
Embora conte com essa escala global, o iBirder é otimizado para a avifauna brasileira, integrando-se ao **WikiAves** que é a maior plataforma de observação de aves do Brasil para oferecer o contexto biológico e etimológico específico da nossa biodiversidade.
---

## 1. Fluxo de Trabalho

### Captura e Diagnóstico de Arquivo
O ciclo de identificação inicia-se com o carregamento da fotografia (via arraste ou seleção manual). Imediatamente, o iBirder realiza uma varredura nos metadados EXIF/XMP do arquivo para extrair as coordenadas geográficas (GPS), nome do autor e a data/hora original do registro. Se os dados de localização forem encontrados, o sistema projeta o ponto exato em um mapa global, estabelecendo o contexto geográfico para as fases seguintes. 
Caso a imagem não possua dados de localização geográfica (coordenadas), o aplicativo sinaliza a ausência ao usuário, permitindo que você defina o local manualmente antes de prosseguir.
O marcador de localização da imagem  no mapa global é arrastável para que você possa fazer manualmente o ajuste fino da localização.

### Identificação por Visão Computacional
Nesta fase, a **Inteligência Artificial (EfficientNet)** analisa os padrões morfológicos da ave,  como cores de plumagem, formato do bico e silhueta para identificar a espécie da ave fotografada. O processamento é realizado localmente e apresenta a sugestão da espécie identificada pala **IA**, acompanhada da indicação do nível de confiança estatística (%) desta identificação. Por padrão, foi estabelecido um limiar de confiança de 60%, e valores abaixo desse limiar resultam em identificação não conclusiva.
Nestes casos, o usuário pode utilizar o campo de **Busca Manual** para informar o nome científico do animal ou usar a ferramenta **Google Lens**. 
Ao clicar no botão do Google Lens, o aplicativo abre a página oficial de busca visual e copia automaticamente o caminho do arquivo para sua área de transferência. Basta arrastar a foto do iBirder ou colar (Ctrl+V) no navegador para obter uma identificação externa complementar. **Ao usar esta funcionalidade seu arquivo é remetido para processamento na nuvem do Google.**
Imediatamente após a identificação da espécie, o sistema busca a validação taxonômica completa, recuperando dados de **Classe**,**Ordem**, **Família**, **Gênero** e **Nomenclatura (Nomes comuns em Português e Inglês)**. Essas informações são extraídas de bases científicas globais e nacionais como **WikiAves**, **iNaturalist** e **eBird**, garantindo que a identificação visual seja sustentada por uma classificação biológica precisa e rigorosa.

### Análise Geográfica e Biomas
Nesta etapa, o iBirder transforma o dado sobre a localização do registro fotográfico em contexto ecológico. O processo ocorre em quatro frentes:
a.  **Geocodificação Reversa**: Utilizando a API **Nominatim (OpenStreetMap)**, as coordenadas extraídas da foto são convertidas em endereços estruturados (**País, Estado e Município**).
b.  **Detecção de Biomas**: O sistema realiza um cruzamento geométrico local entre a localização do registro e polígonos geográficos dos biomas brasileiros, delimitados pelo IBGE. Isso permite identificar instantaneamente em qual **Bioma** (Ex: Mata Atlântica, Cerrado, Pantanal) a ave foi fotografada.
c.  **Distribuição da Espécie (GBIF)**: O mapa projeta camadas de densidade histórica do **Global Biodiversity Information Facility**, mostrando áreas de ocorrência confirmada da ave em escala global através de polígonos de densidade (Hexbins).
d.  **Verificação de Endemismo**: O iBirder realiza um cruzamento de dados com catálogos taxonômicos oficiais (como o **JBRJ** e **iNaturalist**) para verificar se a espécie é **endêmica** do Brasil. 

### Enriquecimento de Dados e Sincronização
Uma vez confirmada a espécie e o contexto geográfico, o iBirder inicia uma sequência de consultas a bases de dados biológicas. O sistema recupera a etimologia do nome científico, descrições morfológicas detalhadas extraídas do **WikiAves** e vocalizações de referência oriundas do **Xeno-Canto** e **iNaturalist**. 
A seleção de vocalizações segue uma lógica de camadas concêntricas, tendo como referência a localização do registro fotográfico. O sistema prioriza registros de vocalizações feitas no mesmo Município, seguido pelo Estado, proximidade geográfica (raio de 150km), Território Nacional e, por fim, Global. São selecionados os 3 melhores áudios que combinam maior proximidade com o local do registro fotográfico e qualidade técnica da gravação da vocalização baseadas nas avaliações feitas pelos usuários da plataforma iNaturalist. 
Todos estes dados são consolidados em tempo real na interface, permitindo que você valide a identificação visual através da conferência auditiva e da descrição da espécie, possibilitando que o usuário valide a identificação da espécie fotografada com maior segurança e acurácia.

### Status de Conservação e Ameaças
Nesta fase, o iBirder identifica o grau de vulnerabilidade da espécie através de uma tripla checagem em bancos de dados de conservação:
1.  **IUCN Red List**: Consulta ao status global de ameaça (ex: Pouco Preocupante, Vulnerável, Em Perigo) da **União Internacional para a Conservação da Natureza**.
2.  **ICMBio (Sistema SALVE)**: Para espécies em território brasileiro, o sistema cruza dados com a base na Lista Oficial da Fauna Brasileira Ameaçada de Extinção do **ICMBio**, fornecendo o status nacional detalhado e específico para a biodiversidade brasileira.
3.  **Convenção CITES**: Verificação do enquadramento da espécie nos anexos da **CITES**, que regula o comércio internacional de espécies da flora e fauna selvagens em perigo.

### Persistência Científica e Metadados
A última fase do fluxo é a gravação das informações nos metadados do registro fotográfico original. Ao clicar em **"Gravar Dados na Fotografia"**, o iBirder utiliza o Software **ExifTool** para injetar as informações diretamente no arquivo original.
As informações salvas incluem a taxonomia completa (nomes científico, comum e em inglês, além de classe, ordem, família e gênero), dados geográficos (país, estado, município e bioma), status de conservação (IUCN, ICMBio e CITES) e detalhes sobre o endemismo. 
Ao clicar em "Gravar Dados na Fotografia", um diálogo de configuração é exibido, permitindo que você selecione individualmente quais campos deseja gravar. 
É importante destacar que o sistema possui uma trava de segurança que detecta a presença de coordenadas de localização (GPS) originais da imagem; caso existam, elas são protegidas e não serão sobrescritas, garantindo a integridade dos dados geográficos primários capturados por sua câmera no momento do registro.

Este processo de gravação segue padrões rigorosos de interoperabilidade:
1.  **Darwin Core (DWC)**: Gravação da taxonomia completa (Classe, Ordem, Família, Gênero e Espécie) seguindo o padrão internacional de intercâmbio de dados biológicos.
2.  **Keywords Hierárquicas (XMP-lr)**: Organização dos dados em "árvores" (ex: *iBirder > Taxonomia > Família > Thraupidae*). Isso permite que suas fotos sejam filtradas automaticamente em softwares profissionais de edição e gerenciamento de imagens.
3.  **Segurança e Integridade**: O sistema utiliza codificação UTF-8 via *argfiles*, garantindo que nomes científicos e acentuações da língua portuguesa não sofram corrupção.

O iBirder atua como o facilitador definitivo entre o momento do clique em campo e a organização final do seu acervo. Ao assumir o trabalho pesado de pesquisa taxonômica e preenchimento manual de metadados, a plataforma devolve ao fotógrafo o que ele tem de mais valioso: o tempo. É a ferramenta que remove as barreiras técnicas entre a fotografia e o dado científico, permitindo que você se concentre no que realmente importa — a observação das aves e a arte de fotografar — enquanto o sistema garante que cada registro esteja organizado, enriquecido e pronto para o futuro.