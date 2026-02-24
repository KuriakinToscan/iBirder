# Auditoria Detalhada de Busca iNaturalist v0.9.2

## Contexto do Usuário
- **Espécie**: `Zonotrichia capensis`
- **Local**: `Rosário do Sul, Rio Grande do Sul`
- **Coordenadas**: `-30.109521666666666, -54.948303333333335`

## 1. Sintaxe de Busca (API)
A requisição utiliza a API v1 do iNaturalist:
```http
GET https://api.inaturalist.org/v1/observations?taxon_name=Zonotrichia+capensis&sounds=true&per_page=200&order_by=votes
```

## 2. Todos os Resultados Retornados (Bruto)
Foram retornados **200** registros da API.

| ID | Lugar (place_guess) | Latitude | Longitude | Favoritos |
|---|---|---|---|---|
| 177236735 | Belgrano, CABA, Argentina | -34.5373420027 | -58.4444976171 | 1 |
| 262582195 | Salta, Salta, AR | -24.772210057 | -65.3498436482 | 1 |
| 78540173 | Tanicuchi, Ecuador | -0.7541342627 | -78.6646869779 | 1 |
| 134435577 | Coronel Brandsen, Provincia de Buenos Aires,  | -35.1677760888 | -58.237378411 | 1 |
| 78907821 | Conjuno El Inca, Quito 170138, Ecuador | -0.1554405 | -78.4714332 | 1 |
| 60655645 | Unnamed Road, Las Cabras, O'Higgins, Chile | -34.172141 | -71.4620317 | 1 |
| 98399558 | Belisario Quevedo, Ecuador | -0.19210972 | -78.52464135 | 1 |
| 153892076 | Location: 18.990000, -70.927000 | 18.9900151689 | -70.9270098433 | 1 |
| 115900574 | WWJQ+R34, Empalme, San José, 10101, Costa Ric | 9.9321333548 | -84.0623526648 | 1 |
| 80533720 | Usme, Bogotá, Colombia | 4.4947754941 | -74.0816936642 | 1 |
| 100291417 | Campoalegre, Huila, Colombia | 2.6603819451 | -75.2693778276 | 1 |
| 253998343 | Ruta T-350, Valdivia, Región de Los Ríos, CL | -39.8132622414 | -73.3975798811 | 0 |
| 256651123 | Santa Cruz, AR | -50.3346145955 | -72.339560461 | 0 |
| 255914648 | Santa Cruz, AR | -50.3249404739 | -72.2690450053 | 0 |
| 255999408 | Puerto Montt, Los Lagos, Chile | -41.461745 | -72.9040583333 | 0 |
| 258585252 | Arroio do Padre - RS, 96155-000, Brasil | -31.448236582 | -52.4587880438 | 0 |
| 64305071 | La Armenia, Quito, Ecuador | -0.2622804921 | -78.4754791123 | 0 |
| 156241475 | Antiguo Country, Chapinero, Bogotá, Bogota, C | 4.67146199 | -74.05473536 | 0 |
| 158041832 | 08145, Perú | -13.1746606386 | -71.5868138149 | 0 |
| 158956300 | Medellín, Palmitas, Medellín, Antioquia, Colo | 6.3318642 | -75.6791906 | 0 |
| 235443581 | Br. Cdad. Universitaria, Teusaquillo, Bogotá, | 4.6362483 | -74.088265 | 0 |
| 178088803 | Raposos - State of Minas Gerais, Brazil | -19.9830110137 | -43.8105371792 | 0 |
| 176179923 | Carrera 116a #89 a 30 int 10 103 Carrera 116a | 4.7210356637 | -74.1155907512 | 0 |
| 103483546 | Duitama, Boyacá, Colombia | 5.8651121598 | -73.0310281366 | 0 |
| 120590205 | Tulio Garzon, Quito, Pichincha, EC | -0.1856565267 | -78.3463956892 | 0 |
| 117399268 | Montetik | 16.6832373402 | -92.5927897455 | 0 |
| 41910045 | San Pedro, Misiones, Argentina | -26.6237510971 | -54.1053927266 | 0 |
| 99536731 | La Capital, Santa Fe, Argentina | -31.699175557 | -60.7509247939 | 0 |
| 42432528 | Colón 2130, Santo Tome (Dpto. La Capital), Sa | -31.6681287711 | -60.7643775721 | 0 |
| 43467259 | Santo Tomás, Heredia, Santo Domingo, Costa Ri | 9.9806637959 | -84.0820140711 | 0 |
| 324489880 | XX29+2MC, San José, Mata de Plátano, Costa Ri | 9.95029905 | -84.03054877 | 0 |
| 317249866 | Estrada Gonçalves/ Costas km 4 Dos Onças - Co | -22.658656 | -45.887146 | 0 |
| 103576694 | 15082, Perú | -12.0495554838 | -77.0606840774 | 0 |
| 109450963 | Antiguo Country, Chapinero, Bogotá, Bogota, C | 4.6737180229 | -74.0546191111 | 0 |
| 112081011 | Section 01, Rocha, UY | -34.3559028405 | -54.4073416115 | 0 |
| 113941283 | Calle 20A, Bogotá, DC, CO | 4.6682579303 | -74.1362875142 | 0 |
| 113838898 | Pueblo Viejo, Fontibón, Bogotá, Colombia | 4.679762 | -74.165303 | 0 |
| 166619632 | Rio Grande do Norte, BR | -5.9385382698 | -35.2384037748 | 0 |
| 71159269 | San José Province, Copey District, Costa Rica | 9.5533874603 | -83.8091183323 | 0 |
| 89759687 | Calle 89, Bogotá, DC, CO | 4.6727348305 | -74.0509600752 | 0 |
| 296552372 | YBY Natureza Condomínio Reserva | -5.9306941999 | -35.223514773 | 0 |
| 10302448 | Tarragona, Bogotá, Bogota, Colombia | 4.6646863411 | -74.1150257799 | 0 |
| 77057565 | La Calera, Cundinamarca, Colombia | 4.752636436 | -73.9970317483 | 0 |
| 74138745 | Latacunga, EC-CT, EC | -0.7576178137 | -78.6647553742 | 0 |
| 73165611 | Tanicuchi, Ecuador | -0.7493234643 | -78.6601962894 | 0 |
| 77437059 | CIUDAD BOLIVAR: Humedal El Tunjo | 4.5760676683 | -74.1479241103 | 0 |
| 129691060 | Calle 59, Bogotá, CO | 4.6470124042 | -74.0696564969 | 0 |
| 129905783 | Santa Fe, Argentina | -31.6094057151 | -60.7242688011 | 0 |
| 189162408 | 6482+7JX, 15800 Departamento de Canelones, Ur | -34.7832614 | -55.89903697 | 0 |
| 194584208 | San Martín Department, Corrientes Province, A | -28.5118529358 | -57.0985088498 | 0 |
| 211467650 | Ciudad Salitre, Teusaquillo, Bogotá, Colombia | 4.6563411 | -74.1136213 | 0 |
| 151158267 | Patagones, Provincia de Buenos Aires, Argenti | -39.6775116667 | -62.4971716667 | 0 |
| 212205764 | 100 meters north of the Gas Station, Puntaren | 10.3130011 | -84.811415 | 0 |
| 61390275 | Camet, Provincia de Buenos Aires, Argentina | -37.8883263488 | -57.609760426 | 0 |
| 65818218 | Villa Ballester | -34.5491407957 | -58.5588197038 | 0 |
| 279517273 | Quito, EC-PI, EC | -0.2289121817 | -78.5186461785 | 0 |
| 92488462 | Centro Histórico, Quito, Ecuador | -0.2222142807 | -78.5156215123 | 0 |
| 98830447 | Latacunga, Ecuador | -0.752176538 | -78.6659486423 | 0 |
| 97279691 | Jardín Botánico de Bogotá José Celestino Muti | 4.6681030883 | -74.1000942886 | 0 |
| 94730939 | Chapicuy, Departamento de Paysandú, Uruguay | -31.5190658352 | -57.9085939005 | 0 |
| 44574067 | Vista Hermosa, Trujillo, Perú | -8.1189041929 | -79.041451849 | 0 |
| 103090114 | Peru | -12.1480324005 | -77.1723466367 | 0 |
| 140922575 | Tababela, Quito, Ecuador | -0.1831853715 | -78.3412855878 | 0 |
| 142312681 | JardÍn Japonés, Buenos Aires, Buenos Aires, A | -34.5748913384 | -58.4090994672 | 0 |
| 143897272 | Villa Mercedes y alrededores, Provincia de Sa | -33.68692768 | -65.4293382392 | 0 |
| 144613725 | Galicia, Buenos Aires, Ciudad Autonoma de Bue | -34.6046092501 | -58.4503769875 | 0 |
| 204178221 | San Vicente, Antioquia, Colombia | 6.332367555 | -75.3067701682 | 0 |
| 144978838 | Cosanga, Ecuador | -0.5902043 | -77.8786039 | 0 |
| 206007536 | Jaramillo, Chiriquí Province, Panama | 8.7703489 | -82.3777335 | 0 |
| 141317737 | Las Heras, AR-MZ, AR | -32.77055638 | -70.08525931 | 0 |
| 202833996 | Tupuraya, Cochabamba, Bolivia | -17.37280198 | -66.13817346 | 0 |
| 195536579 | Talagante, Región Metropolitana, Chile | -33.5326650422 | -70.8066133047 | 0 |
| 194912526 | Pueblo Rico, Risaralda, Colombia | 5.2446783 | -76.1005516 | 0 |
| 196432402 | Puerto Montt, Los Lagos, Chile | -41.4617381617 | -72.9038011562 | 0 |
| 192696557 | Kennedy, Bogotá, Colombia | 4.6549660551 | -74.1624521697 | 0 |
| 195042811 | San Vicente, Antioquia, Colombia | 6.3321549539 | -75.3064885363 | 0 |
| 143566032 | Biedma, AR-CH, AR | -42.69515083 | -64.1795103 | 0 |
| 241650368 | Universidad Nacional De Colombia - Sede Bogot | 4.6424668562 | -74.0819686745 | 0 |
| 243792148 | Arroio Grande - RS, 96330-000, Brasil | -31.9020730213 | -52.6533011036 | 0 |
| 244416634 | Bogotá, D.C. , CO-CU, CO | 4.6075100033 | -74.053759547 | 0 |
| 250779904 | Belgrano, Cdad. Autónoma de Buenos Aires, Arg | -34.5439742037 | -58.440330103 | 0 |
| 221325709 | Toay, La Pampa, Argentina | -36.6781569429 | -64.3918243423 | 0 |
| 331066453 | Itatiaia - State of Rio de Janeiro, Brazil | -22.4441282227 | -44.6002156506 | 0 |
| 330009701 | Manizales, Caldas, Colombia | 5.0676056734 | -75.5288248788 | 0 |
| 328777233 | Playa Rica-Ranchería, Rionegro, Antioquia, CO | 6.1732150761 | -75.4356720075 | 0 |
| 324331475 | Marcos Juárez, AR-CB, AR | -32.7005605347 | -62.109440916 | 0 |
| 39979068 | Pastaza, EC-PA, EC | -1.4865006041 | -78.0070123449 | 0 |
| 338302697 | Ciriguari, Cañasgordas, Antioquia, Colombia | 6.71055686 | -75.98873549 | 0 |
| 195504426 | Cautín, CL-AR, CL | -38.6324808916 | -72.2126431129 | 0 |
| 137513932 | Santo Tomé, Santa Fe, Argentina | -31.6615512581 | -60.7607782558 | 0 |
| 196928111 | Cabaceiras - PB, Brasil | -7.4152129794 | -36.3544874066 | 0 |
| 97550438 | San Vicente, O'Higgins, Chile | -34.54711265 | -71.22590158 | 0 |
| 83515140 | Santa Margarita, Colina, Región Metropolitana | -33.2602391107 | -70.6286362701 | 0 |
| 314560416 | Yerba Buena, ensenada. La Higuera, Coquimbo,  | -29.5717905791 | -71.2945707142 | 0 |
| 35755888 | Gil Ramírez Dávalos, Cuenca, Ecuador | -2.8910841962 | -79.0136256069 | 0 |
| 36033480 | Valeria del Mar, Buenos Aires, Argentina | -37.1404219 | -56.8986951 | 0 |
| 96223902 | Diamante, Entre Ríos, Argentina | -31.8369445941 | -60.5633810163 | 0 |
| 92295593 | Latacunga, Ecuador | -0.7536552707 | -78.6653385433 | 0 |
| 37664366 | Meu Jardim Vila Sao Francisco, Cruz Alta - RS | -28.6505345488 | -53.593698606 | 0 |
| 100724900 | VXJ5+CCF, Trujillo 13011, Perú | -8.1189098354 | -79.0417066589 | 0 |
| 163960441 | Antiguo Country, Chapinero, Bogotá, Bogota, C | 4.67440169 | -74.0556229 | 0 |
| 157354363 | Prolongación le los Insurgentes, San Cristóba | 16.7141860631 | -92.6350415313 | 0 |
| 202151881 | San José Province, Copey District, Costa Rica | 9.640967 | -83.911689 | 0 |
| 142110866 | Chapéu do Sol - Paraty | -23.0032194635 | -44.5693005976 | 0 |
| 211851544 | Urb Santa Maria, Amarilis 10002, Perú | -9.9125561 | -76.2274526 | 0 |
| 64385297 | Oe20G Y N82, Quito 170134, Ecuador | -0.0905733333 | -78.525765 | 0 |
| 63670568 | Int. Alvear, La Pampa, Argentina | -35.2323438273 | -63.6020899802 | 0 |
| 63986153 | Flores, CABA, Argentina | -34.6237501311 | -58.4613601014 | 0 |
| 63054000 | San Cristóbal, Bogotá, Colombia | 4.5623004322 | -74.0980271452 | 0 |
| 161025896 | Cumbayá, Quito, Ecuador | -0.2067913096 | -78.4199412785 | 0 |
| 216528868 | Elqui, CL-CO, CL | -29.9821665228 | -71.3998899188 | 0 |
| 221696330 | P.º Ávila, 1050, La Guaira, Venezuela | 10.5421135 | -66.8747209 | 0 |
| 216652415 | Calle 5A, Bogotá, Bogotá, CO | 4.6289170883 | -74.1388253195 | 0 |
| 79728070 | Caracas, Ciudad Bolívar, Bogotá, Bogota, Colo | 4.5817301212 | -74.0920349211 | 0 |
| 77053733 | La Calera, Cundinamarca, Colombia | 4.7528790095 | -73.996722959 | 0 |
| 77059732 | La Calera, Cundinamarca, Colombia | 4.7528222085 | -73.9966787025 | 0 |
| 76749254 | colombia, bogotá calle 3ra No 78 k 67 | 4.673587 | -74.087484 | 0 |
| 75380300 | Tanicuchi, Ecuador | -0.7539277504 | -78.6651000381 | 0 |
| 89339763 | Jardín dodoísta | 4.6642570543 | -74.1171455949 | 0 |
| 55967176 | Tibasosa, Boyacá, Colombia | 5.7775729953 | -73.0221176895 | 0 |
| 113827769 | ボリビア ラパス マクロディストリト・スール | -16.55515645 | -68.07048384 | 0 |
| 110913599 | Latacunga, Ecuador | -0.7536303389 | -78.6648562425 | 0 |
| 111088688 | FVWF+HGR, La Paz, Bolivia | -16.50322838 | -68.12629275 | 0 |
| 234027569 | Colegio Internacional Montessori, Ciudad de G | 14.5684733176 | -90.4594120794 | 0 |
| 235297606 | Parambu - CE, 63680-000, Brasil | -6.2462833099 | -40.8039218592 | 0 |
| 177416346 | Parque Nacional Enrique Olaya Herrera, Bogotá | 4.6243332655 | -74.0648983419 | 0 |
| 240687690 | Belgrano R, Cdad. Autónoma de Buenos Aires, A | -34.5716340054 | -58.4735747084 | 0 |
| 302834871 | Funes, Santa Fe, Argentina | -32.9128579185 | -60.8537365124 | 0 |
| 245753037 | Urb. Palomino, Lima, Perú | -12.0620769494 | -77.071374692 | 0 |
| 308767163 | Billinghurst, Provincia de Buenos Aires, Arge | -34.5683683256 | -58.5866633605 | 0 |
| 305646970 | De Guadalupe, Valle de Bravo, Méx., Mexique | 19.1965246623 | -100.1158212125 | 0 |
| 313327473 | Carabelas, Puente Aranda, Bogotá, Bogota, Col | 4.6033491629 | -74.1151689738 | 0 |
| 325269954 | Cd Bolívar, Antioquia, Colombia | 5.8517810992 | -76.1047273577 | 0 |
| 326647381 | P.j Mariscal Ramon Castilla, Cerro Colorado 0 | -16.3915118177 | -71.5667662995 | 0 |
| 327840731 | Boa Nova, BR-BA, BR | -14.3199912 | -40.25052713 | 0 |
| 268409407 | Cómbita, CO-BY, CO | 5.5521883333 | -73.3573783333 | 0 |
| 263778211 | XRWR+5H8, Heredia, Flores, Bougainvillea, Cos | 9.9952646764 | -84.158635838 | 0 |
| 326023039 | Manuel Burbano, Quito, Pichincha, EC | -0.1903214899 | -78.3524249403 | 0 |
| 277336637 | Toay, La Pampa, Argentina | -36.678275 | -64.3918266667 | 0 |
| 331915216 | Division, San José, División, Costa Rica | 9.5118065 | -83.7101562 | 0 |
| 334508108 | CL 49 Sur - KR 81D Sur, Bosa, Bogotá, Colombi | 4.6227291771 | -74.1737685353 | 0 |
| 279461288 | Gral Manuel Belgrano, Misiones, Argentina | -25.5317658902 | -54.1355231588 | 0 |
| 255208391 | Calle Paraíso del Quetzal, Dota, San Jose, CR | 9.6446828973 | -83.8503673797 | 0 |
| 311138844 | Billinghurst, Provincia de Buenos Aires, Arge | -34.5684942632 | -58.5864565397 | 0 |
| 251318920 | B1702 Ciudadela, Buenos Aires Province, Argen | -34.6507232384 | -58.5301563247 | 0 |
| 290636459 | Costa Rica | 9.8017899477 | -84.1633558103 | 0 |
| 45373932 | La Capilla, Villa de Leyva, Boyacá, Colombia | 5.706169 | -73.476737 | 0 |
| 102237077 | Colonia del Sacramento, Colonia Department, U | -34.4607189 | -57.8339099 | 0 |
| 109543118 | Pérez Zeledón, CR-SJ, CR | 9.583171363 | -83.7978186392 | 0 |
| 109015417 | Latacunga, EC-CT, EC | -0.7435546704 | -78.6721466531 | 0 |
| 103269357 | 15300 La Floresta, Canelones Department, Urug | -34.7604508373 | -55.6931124949 | 0 |
| 103207592 | Quilombo | -31.5227713089 | -52.4711165205 | 0 |
| 43128603 | Unnamed Road, Cochabamba, Bolivia | -17.3722772679 | -66.1923384921 | 0 |
| 123670827 | Chivatá, Boyacá, CO | 5.5822568369 | -73.2796130031 | 0 |
| 128318000 | Huiliches, Neuquén, Argentina | -39.9521208967 | -71.0634737692 | 0 |
| 131891029 | Santo Tomé, Santa Fe, Argentina | -31.6615578867 | -60.7608195671 | 0 |
| 192070599 | Rio dos Cedros, BR-SC, BR | -26.5545216667 | -49.3720283333 | 0 |
| 126814007 | Latacunga, Ecuador | -0.7268391709 | -78.6492703625 | 0 |
| 116967055 | Paradero de Buses Sotrandes y Cootrasuba, Bog | 4.7599690678 | -74.1026792675 | 0 |
| 116225723 | Vela, Ambato, Ecuador | -1.2475875121 | -78.6269846893 | 0 |
| 296255537 | Centro, Arroio do Padre - RS, 96155-000, Bras | -31.4421381503 | -52.4194033808 | 0 |
| 282954810 | Pujilí, EC-CT, EC | -0.869705 | -78.91099 | 0 |
| 339868456 | Pine Beach, Punta del Este, Departamento de M | -34.950162297 | -54.9406905636 | 0 |
| 338736804 | Quito, EC-PI, EC | -0.2874669012 | -78.503722323 | 0 |
| 63324776 | Republica del Canada, Usme, Bogota, Colombia | 4.5391585 | -74.0867952 | 0 |
| 61043482 | Loma de Imbaud, Yerba Buena, Tucumán, Argenti | -26.8035027666 | -65.3198412039 | 0 |
| 64622686 | Las Casas, Quito 170129, Ecuador | -0.18888652 | -78.5070515 | 0 |
| 62055190 | Urb la Riviera de Monterrico, La Molina 15024 | -12.0721237987 | -76.9498635828 | 0 |
| 66207694 | Canal Boyacá | 4.664246361 | -74.1183257668 | 0 |
| 192802995 | Lago Buenos Aires, Santa Cruz, Argentina | -47.2409370398 | -71.1923185363 | 0 |
| 121306846 | Latacunga, Ecuador | -0.7536657416 | -78.664794213 | 0 |
| 121178306 | Latacunga, Ecuador | -0.7535714332 | -78.6649112558 | 0 |
| 118282175 | Latacunga, Ecuador | -0.7558836011 | -78.663530933 | 0 |
| 196204750 | Puerto Montt, Los Lagos, Chile | -41.46300272 | -72.89982367 | 0 |
| 279691278 | San Justo, Córdoba, Argentina | -30.9400587621 | -62.7053768591 | 0 |
| 325273785 | Punta Arenas, Magallanes y la Antártica Chile | -53.1577271658 | -70.9204534308 | 0 |
| 331651197 | Pudahuel, Santiago Metropolitan Region, Chile | -33.4152911797 | -70.7987057687 | 0 |
| 335772680 | V339+RQX Parque Infantil Residencial El Molin | 9.85434208 | -83.93057642 | 0 |
| 276797053 | Sucre, Bolivia | -19.043791093 | -65.271809296 | 0 |
| 107399466 | Jardín dodoísta | 4.6642570543 | -74.1171455949 | 0 |
| 114021926 | Localización: 6,326441 -75,655573 | 6.3264410159 | -75.6555730104 | 0 |
| 108617890 | Quito, Ecuador | -0.1893733955 | -78.3531196335 | 0 |
| 94529038 | Latacunga, Ecuador | -0.753688362 | -78.664789107 | 0 |
| 37172815 | Rió Grande, AR-TF, AR | -53.68339027 | -67.88157455 | 0 |
| 94809778 | Cordoba, Suba, Bogotá, Bogota, Colombia | 4.7077351488 | -74.067183584 | 0 |
| 91553856 | Mangabeiras, Belo Horizonte - MG, Brasil | -19.9520797069 | -43.9057979939 | 0 |
| 98703292 | São João Novo, São Roque - SP, Brasil | -23.57371168 | -47.0631666 | 0 |
| 169877205 | Maipú, Maipu, Santiago Metropolitan Region, C | -33.5311349563 | -70.8040493354 | 0 |
| 194321555 | Parque Nacional Torres del Paine, Torres del  | -51.0274336874 | -73.0399975173 | 0 |
| 223117289 | Elqui, CL-CO, CL | -29.9297756343 | -71.2039690906 | 0 |
| 158803328 | Chicó Reservado, Localidad de Chapinero, Bogo | 4.67523144 | -74.04626689 | 0 |
| 191011409 | MHP3+7WV, Sangolquí 171103, Équateur | -0.313885 | -78.4452116667 | 0 |
| 192114066 | Rua Via Veneza, Campo Largo, PR, BR | -25.4577309752 | -49.5015526604 | 0 |
| 133707146 | Antiguo Country, Chapinero, Bogotá, Bogota, C | 4.6741023442 | -74.0562328937 | 0 |
| 187139482 | Villa de Leyva, Boyacá, Colombia | 5.63790915 | -73.51952079 | 0 |
| 192694235 | Kennedy, Bogotá, Colombia | 4.6549451468 | -74.1624061572 | 0 |
| 182545386 | Heredia, Barva, 40205, Costa Rica | 10.0127823037 | -84.1118719429 | 0 |
| 324929659 | n.a89, UY-DU, UY | -33.2892112292 | -56.4328010923 | 0 |
| 322865428 | Urb San Martin, Pueblo Libre, Perú | -12.0696018759 | -77.0660880581 | 0 |
| 257736525 | San Vicente, Antioquia, Colombia | 6.3295264236 | -75.3070015088 | 0 |

## 3. Processamento de Ranking Geográfico
Aplicando lógica de 5 camadas (Mun > UF > 150km > Brasil > Global)...

| Posição | ID | Distância | Camada Requerida | Motivo | Link Registro |
|---|---|---|---|---|---|
| Top 1 | 258585252 | 280.6km | **C1** | ESTADO | [Ver Rebgistro](https://www.inaturalist.org/observations/258585252) |
| Top 2 | 243792148 | 295.9km | **C1** | ESTADO | [Ver Rebgistro](https://www.inaturalist.org/observations/243792148) |
| Top 3 | 37664366 | 208.7km | **C1** | ESTADO | [Ver Rebgistro](https://www.inaturalist.org/observations/37664366) |
| Descartado | 296255537 | 283.4km | **C1** | ESTADO | [Ver Rebgistro](https://www.inaturalist.org/observations/296255537) |
| Descartado | 178088803 | 1587.7km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/178088803) |
| Descartado | 317249866 | 1224.2km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/317249866) |
| Descartado | 166619632 | 3387.8km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/166619632) |
| Descartado | 331066453 | 1337.0km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/331066453) |
| Descartado | 196928111 | 3182.6km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/196928111) |
| Descartado | 235297606 | 3038.0km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/235297606) |
| Descartado | 327840731 | 2312.6km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/327840731) |
| Descartado | 192070599 | 673.7km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/192070599) |
| Descartado | 91553856 | 1583.5km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/91553856) |
| Descartado | 98703292 | 1067.2km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/98703292) |
| Descartado | 192114066 | 744.5km | **C3** | BRASIL | [Ver Rebgistro](https://www.inaturalist.org/observations/192114066) |
| Descartado | 177236735 | 591.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/177236735) |
| Descartado | 262582195 | 1184.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/262582195) |
| Descartado | 78540173 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/78540173) |
| Descartado | 134435577 | 641.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/134435577) |
| Descartado | 78907821 | 4157.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/78907821) |
| Descartado | 60655645 | 1617.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/60655645) |
| Descartado | 98399558 | 4157.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/98399558) |
| Descartado | 153892076 | 5721.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/153892076) |
| Descartado | 115900574 | 5432.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/115900574) |
| Descartado | 80533720 | 4353.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/80533720) |
| Descartado | 100291417 | 4235.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/100291417) |
| Descartado | 253998343 | 1991.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/253998343) |
| Descartado | 256651123 | 2675.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/256651123) |
| Descartado | 255914648 | 2671.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/255914648) |
| Descartado | 255999408 | 2046.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/255999408) |
| Descartado | 64305071 | 4147.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/64305071) |
| Descartado | 156241475 | 4369.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/156241475) |
| Descartado | 158041832 | 2543.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/158041832) |
| Descartado | 158956300 | 4616.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/158956300) |
| Descartado | 235443581 | 4368.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/235443581) |
| Descartado | 176179923 | 4377.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/176179923) |
| Descartado | 103483546 | 4440.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/103483546) |
| Descartado | 120590205 | 4146.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/120590205) |
| Descartado | 117399268 | 6582.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/117399268) |
| Descartado | 41910045 | 396.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/41910045) |
| Descartado | 99536731 | 581.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/99536731) |
| Descartado | 42432528 | 581.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/42432528) |
| Descartado | 43467259 | 5438.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/43467259) |
| Descartado | 324489880 | 5432.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/324489880) |
| Descartado | 103576694 | 3037.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/103576694) |
| Descartado | 109450963 | 4370.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/109450963) |
| Descartado | 112081011 | 474.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/112081011) |
| Descartado | 113941283 | 4373.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/113941283) |
| Descartado | 113838898 | 4376.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/113838898) |
| Descartado | 71159269 | 5382.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/71159269) |
| Descartado | 89759687 | 4369.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/89759687) |
| Descartado | 296552372 | 3389.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/296552372) |
| Descartado | 10302448 | 4372.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/10302448) |
| Descartado | 77057565 | 4375.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/77057565) |
| Descartado | 74138745 | 4114.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/74138745) |
| Descartado | 73165611 | 4115.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/73165611) |
| Descartado | 77437059 | 4365.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/77437059) |
| Descartado | 129691060 | 4368.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/129691060) |
| Descartado | 129905783 | 575.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/129905783) |
| Descartado | 189162408 | 527.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/189162408) |
| Descartado | 194584208 | 273.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/194584208) |
| Descartado | 211467650 | 4371.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/211467650) |
| Descartado | 151158267 | 1266.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/151158267) |
| Descartado | 212205764 | 5514.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/212205764) |
| Descartado | 61390275 | 899.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/61390275) |
| Descartado | 65818218 | 598.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/65818218) |
| Descartado | 279517273 | 4153.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/279517273) |
| Descartado | 92488462 | 4154.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/92488462) |
| Descartado | 98830447 | 4115.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/98830447) |
| Descartado | 97279691 | 4371.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/97279691) |
| Descartado | 94730939 | 323.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/94730939) |
| Descartado | 44574067 | 3502.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/44574067) |
| Descartado | 103090114 | 3038.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/103090114) |
| Descartado | 140922575 | 4146.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/140922575) |
| Descartado | 142312681 | 593.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/142312681) |
| Descartado | 143897272 | 1065.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/143897272) |
| Descartado | 144613725 | 598.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/144613725) |
| Descartado | 204178221 | 4597.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/204178221) |
| Descartado | 144978838 | 4080.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/144978838) |
| Descartado | 206007536 | 5223.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/206007536) |
| Descartado | 141317737 | 1464.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/141317737) |
| Descartado | 202833996 | 1814.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/202833996) |
| Descartado | 195536579 | 1544.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/195536579) |
| Descartado | 194912526 | 4531.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/194912526) |
| Descartado | 196432402 | 2046.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/196432402) |
| Descartado | 192696557 | 4373.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/192696557) |
| Descartado | 195042811 | 4597.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/195042811) |
| Descartado | 143566032 | 1622.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/143566032) |
| Descartado | 241650368 | 4368.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/241650368) |
| Descartado | 244416634 | 4363.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/244416634) |
| Descartado | 250779904 | 592.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/250779904) |
| Descartado | 221325709 | 1140.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/221325709) |
| Descartado | 330009701 | 4484.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/330009701) |
| Descartado | 328777233 | 4588.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/328777233) |
| Descartado | 324331475 | 738.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/324331475) |
| Descartado | 39979068 | 4006.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/39979068) |
| Descartado | 338302697 | 4669.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/338302697) |
| Descartado | 195504426 | 1841.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/195504426) |
| Descartado | 137513932 | 580.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/137513932) |
| Descartado | 97550438 | 1604.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/97550438) |
| Descartado | 83515140 | 1522.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/83515140) |
| Descartado | 314560416 | 1576.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/314560416) |
| Descartado | 35755888 | 3946.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/35755888) |
| Descartado | 36033480 | 802.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/36033480) |
| Descartado | 96223902 | 568.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/96223902) |
| Descartado | 92295593 | 4115.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/92295593) |
| Descartado | 100724900 | 3502.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/100724900) |
| Descartado | 163960441 | 4370.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/163960441) |
| Descartado | 157354363 | 6587.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/157354363) |
| Descartado | 202151881 | 5396.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/202151881) |
| Descartado | 142110866 | 1298.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/142110866) |
| Descartado | 211851544 | 3147.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/211851544) |
| Descartado | 64385297 | 4166.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/64385297) |
| Descartado | 63670568 | 989.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/63670568) |
| Descartado | 63986153 | 600.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/63986153) |
| Descartado | 63054000 | 4361.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/63054000) |
| Descartado | 161025896 | 4149.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/161025896) |
| Descartado | 216528868 | 1582.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/216528868) |
| Descartado | 221696330 | 4697.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/221696330) |
| Descartado | 216652415 | 4369.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/216652415) |
| Descartado | 79728070 | 4362.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/79728070) |
| Descartado | 77053733 | 4375.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/77053733) |
| Descartado | 77059732 | 4375.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/77059732) |
| Descartado | 76749254 | 4371.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/76749254) |
| Descartado | 75380300 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/75380300) |
| Descartado | 89339763 | 4372.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/89339763) |
| Descartado | 55967176 | 4431.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/55967176) |
| Descartado | 113827769 | 2013.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/113827769) |
| Descartado | 110913599 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/110913599) |
| Descartado | 111088688 | 2021.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/111088688) |
| Descartado | 234027569 | 6256.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/234027569) |
| Descartado | 177416346 | 4365.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/177416346) |
| Descartado | 240687690 | 596.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/240687690) |
| Descartado | 302834871 | 640.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/302834871) |
| Descartado | 245753037 | 3037.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/245753037) |
| Descartado | 308767163 | 602.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/308767163) |
| Descartado | 305646970 | 7308.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/305646970) |
| Descartado | 313327473 | 4366.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/313327473) |
| Descartado | 325269954 | 4590.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/325269954) |
| Descartado | 326647381 | 2277.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/326647381) |
| Descartado | 268409407 | 4424.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/268409407) |
| Descartado | 263778211 | 5444.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/263778211) |
| Descartado | 326023039 | 4146.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/326023039) |
| Descartado | 277336637 | 1140.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/277336637) |
| Descartado | 331915216 | 5372.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/331915216) |
| Descartado | 334508108 | 4371.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/334508108) |
| Descartado | 279461288 | 515.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/279461288) |
| Descartado | 255208391 | 5393.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/255208391) |
| Descartado | 311138844 | 602.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/311138844) |
| Descartado | 251318920 | 606.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/251318920) |
| Descartado | 290636459 | 5427.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/290636459) |
| Descartado | 45373932 | 4445.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/45373932) |
| Descartado | 102237077 | 554.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/102237077) |
| Descartado | 109543118 | 5384.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/109543118) |
| Descartado | 109015417 | 4116.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/109015417) |
| Descartado | 103269357 | 521.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/103269357) |
| Descartado | 103207592 | 284.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/103207592) |
| Descartado | 43128603 | 1818.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/43128603) |
| Descartado | 123670827 | 4423.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/123670827) |
| Descartado | 128318000 | 1825.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/128318000) |
| Descartado | 131891029 | 580.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/131891029) |
| Descartado | 126814007 | 4116.7km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/126814007) |
| Descartado | 116967055 | 4381.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/116967055) |
| Descartado | 116225723 | 4068.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/116225723) |
| Descartado | 282954810 | 4120.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/282954810) |
| Descartado | 339868456 | 538.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/339868456) |
| Descartado | 338736804 | 4147.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/338736804) |
| Descartado | 63324776 | 4358.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/63324776) |
| Descartado | 61043482 | 1078.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/61043482) |
| Descartado | 64622686 | 4156.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/64622686) |
| Descartado | 62055190 | 3026.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/62055190) |
| Descartado | 66207694 | 4372.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/66207694) |
| Descartado | 192802995 | 2359.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/192802995) |
| Descartado | 121306846 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/121306846) |
| Descartado | 121178306 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/121178306) |
| Descartado | 118282175 | 4114.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/118282175) |
| Descartado | 196204750 | 2046.1km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/196204750) |
| Descartado | 279691278 | 748.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/279691278) |
| Descartado | 325273785 | 2871.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/325273785) |
| Descartado | 331651197 | 1541.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/331651197) |
| Descartado | 335772680 | 5417.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/335772680) |
| Descartado | 276797053 | 1611.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/276797053) |
| Descartado | 107399466 | 4372.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/107399466) |
| Descartado | 114021926 | 4614.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/114021926) |
| Descartado | 108617890 | 4146.8km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/108617890) |
| Descartado | 94529038 | 4115.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/94529038) |
| Descartado | 37172815 | 2821.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/37172815) |
| Descartado | 94809778 | 4374.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/94809778) |
| Descartado | 169877205 | 1543.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/169877205) |
| Descartado | 194321555 | 2766.5km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/194321555) |
| Descartado | 223117289 | 1563.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/223117289) |
| Descartado | 158803328 | 4369.9km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/158803328) |
| Descartado | 191011409 | 4141.2km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/191011409) |
| Descartado | 133707146 | 4370.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/133707146) |
| Descartado | 187139482 | 4440.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/187139482) |
| Descartado | 192694235 | 4373.6km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/192694235) |
| Descartado | 182545386 | 5443.3km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/182545386) |
| Descartado | 324929659 | 380.4km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/324929659) |
| Descartado | 322865428 | 3036.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/322865428) |
| Descartado | 257736525 | 4597.0km | **C4** | GLOBAL | [Ver Rebgistro](https://www.inaturalist.org/observations/257736525) |

## Conclusão da Simulação
O sistema selecionou **3** áudios prioritários.
Primeiro áudio: `https://static.inaturalist.org/sounds/1286377.mp3?1736969907`