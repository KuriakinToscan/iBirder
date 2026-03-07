# iBirder - Guia do Usuário

## Bem-vindo ao iBirder
### Estação ornitológica inteligente para análise e catalogação de fotografias de aves.

O **iBirder** é uma plataforma avançada projetada para transformar fotografias em registros científicos completos. O sistema automatiza a identificação de espécies e enriquece cada registro fotográfico com dados de taxonomia, status de conservação e distribuição geográfica, fornecendo uma análise biológica completa em segundos.

Comprometido com a transparência e a segurança, o aplicativo baseia-se em tecnologias de **software livre** e opera sob o conceito de **Edge AI**. Isso significa que a inteligência artificial e a gravação de metadados ocorrem de forma **estritamente local** no computador onde o iBirder está instalado. Suas fotografias originais nunca são enviadas para a nuvem para fins de reconhecimento da espécie. O acesso à rede é utilizado exclusivamente para consultas em bibliotecas biológicas globais e carregamento de mapas, mantendo o controle total da privacidade e dos dados em suas mãos.

O iBirder utiliza a rede neural convolucional (CNN) **EfficientNet-V1.3**, uma das arquiteturas mais sofisticadas da atualidade para fazer a identificação de espécies de aves. EEsta IA foi selecionada por seu equilíbrio entre precisão, leveza e eficiência, permitindo que análises complexas de padrões de plumagem e silhueta das aves sejam realizadas diretamente no hardware do seu computador com tempo de processamento muito reduzido.

O modelo de indentificação foi treinado com a robusta base de dados do **iNaturalist Vision**, aprendendo a identificar as espécies de aves a partir de milhões de registros validados por especialistas e cientistas cidadãos ao redor do mundo. 
Embora o treinamento possua escala global, o iBirder é otimizado para a avifauna Brasileira, integrando-se ao **WikiAves** para oferecer o contexto biológico e etimológico específico da biodiversidade nacional.

---

## 1. Fluxo de Trabalho

Captura e Diagnóstico de Arquivo
O ciclo de identificação inicia-se com o carregamento da fotografia (via arraste ou seleção manual). Imediatamente, o iBirder realiza uma varredura nos metadados EXIF/XMP do arquivo para extrair as coordenadas geográficas (GPS), nome do autor e a data/hora original do registro. Se os dados de localização forem encontrados, o sistema projeta o ponto exato em um mapa global, e estabelecendo o contexto geográfico para as fases seguintes. Caso a imagem não possua georreferenciamento, o aplicativo sinaliza a ausência, permitindo que você defina o local manualmente antes de prosseguir.
O pin de localização da imagem  no mapa global é arrastável para que você possa fazer  manualmente o ajuste fino da localização

### Identificação por Visão Computacional
Nesta fase, o "cérebro" digital (**EfficientNet**) analisa os padrões morfológicos da ave — como cores de plumagem, formato do bico e silhueta para identificar a espécie da ave fotografada. O processamento é realizado localmente e apresenta a sugestão da espécie acompanhada de um nível de confiança estatística. Por padrão, foi estabelecido um limiar de confiança de 60%, e valores abaixo desse limiar resultam em identificação não conclusiva.
Caso a fotografia esteja fora de foco ou o sistema apresente baixa confiança, você pode utilizar o campo de **Busca Manual** para inserir o nome científico diretamente em seu campo ou usara ferramenta **Google Lens**. 
Ao clicar no botão do Google Lens, o aplicativo abre a página oficial de busca visual e copia automaticamente o caminho do arquivo para sua área de transferência. Basta arrastar a foto do iBirder ou colar (Ctrl+V) no navegador para obter uma identificação externa complementar.
Imediatamente após a identificação inicial, o sistema busca a validação taxonômica completa, recuperando dados de **Classe**,**Ordem**, **Família**, **Gênero**  e **Nomenclatura (Nomes comuns em Português e Inglês)**. Essas informações são extraídas de bases científicas globais e nacionais como **WikiAves**, **iNaturalist** e **eBird**, garantindo que a identificação visual seja sustentada por uma classificação biológica precisa e rigorosa.

### Análise Geográfica e Biomas
Nesta etapa, o iBirder transforma o dado sobre a localizaão do registro fotográfico em contexto ecológico. O processo ocorre em quatro frentes:
1.  **Geocodificação Reversa**: Utilizando a API **Nominatim (OpenStreetMap)**, as coordenadas extraídas da foto são convertidas em endereços estruturados (**País, Estado e Município**).
2.  **Detecção de Biomas**: O sistema realiza um cruzamento geométrico local entre a localização do registro e polígonos geográficos dos biomas brasileiros, delimitados pelo IBGE. Isso permite identificar instantaneamente em qual **Bioma** (Ex: Mata Atlântica, Cerrado, Pantanal) a ave foi fotografada.
3.  **Distribuição da Espécie (GBIF)**: O mapa projeta camadas de densidade histórica do **Global Biodiversity Information Facility**, mostrando áreas de ocorrência confirmada da ave em escala global através de polígonos de densidade (Hexbins).
4.  **Verificação de Endemismo**: O iBirder realiza um cruzamento de dados com catálogos taxonômicos oficiais (como o **JBRJ** e **iNaturalist**) para verificar se a espécie é **endêmica** do Brasil. 

### Enriquecimento de Dados e Sincronização
Uma vez confirmada a espécie e o contexto geográfico, o iBirder inicia uma sequência de consultas a bases de dados biológicas. O sistema recupera a etimologia do nome científico, descrições morfológicas detalhadas extraídas do WikiAves e vocalizações de referência oriundas do **Xeno-Canto** e **iNaturalist**. 
A seleção de vocalizações segue uma lógica de camadas concêntricas, priorizando registros do mesmo Município, seguido pelo Estado, proximidade geográfica (raio de 150km), Território Nacional e, por fim, Global. São selecionados os 3 melhores áudios que combinam maior proximidade com o local do registro fotográfico e qualidade técnica da gravação da vocalização baseada na avaliação da gravação feita pelo usuários da plataforma iNaturalist. 
Todos estes dados são consolidados em tempo real na interface, permitindo que você valide a identificação visual através da conferência auditiva e da descrição da espécie extraida do **WikiAves**.

### Status de Conservação e Ameaças
Nesta fase, o iBirder identifica o grau de vulnerabilidade da espécie através de uma tripla checagem em bancos de dados de conservação:
1.  **IUCN Red List**: Consulta ao status global de ameaça (ex: Pouco Preocupante, Vulnerável, Em Perigo) da **União Internacional para a Conservação da Natureza**.
2.  **ICMBio (Sistema SALVE)**: Para espécies em território brasileiro, o sistema cruza dados com a base oficial do **ICMBio**, fornecendo o status nacional detalhado e específico para a biodiversidade brasileira.
3.  **Convenção CITES**: Verificação do enquadramento da espécie nos anexos da **CITES**, que regula o comércio internacional de espécies da flora e fauna selvagens em perigo.

### Persistência Científica e Metadados
A última fase do fluxo é a imortalização do registro através da gravação de metadados no registro fotográfico original. Ao clicar em **"Gravar Dados na Fotografia"**, o iBirder utiliza o motor **ExifTool** para injetar as informações diretamente no arquivo original.
O processo segue padrões rigorosos de interoperabilidade:
1.  **Darwin Core (DWC)**: Gravação da taxonomia completa (Classe, Ordem, Família, Gênero e Espécie) seguindo o padrão internacional de intercâmbio de dados biológicos.
2.  **Keywords Hierárquicas (XMP-lr)**: Organização dos dados em "árvores" (ex: *iBirder > Taxonomia > Família > Thraupidae*). Isso permite que suas fotos sejam filtradas automaticamente em softwares profissionais como **Adobe Lightroom**, **Adobe Bridge** e **DigiKam**.
3.  **Geografia e Conservação**: Além das coordenadas GPS (opcionais), são gravados o **Bioma**, **Endemismo** e os status de ameaça da **IUCN** e **ICMBio**.
4.  **Segurança e Integridade**: O sistema utiliza codificação UTF-8 via *argfiles*, garantindo que nomes científicos e acentuações da língua portuguesa não sofram corrupção.




