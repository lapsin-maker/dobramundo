# Dobramundo

![Logo do Dobramundo](docs/logo.jpg)

**Dobre o papel, voe e transforme a cidade.** Exergame sério de voo em que a criança pilota, com o próprio corpo, um avião de papel reciclado.

## Prévia — sprint 2: aquarela em movimento

Água e terreno avançam em perspectiva, e árvores e construções das margens passam pelo avião: o voo não fica sobre uma pintura parada. Manaus e Petrolina têm três estágios, com arte regional em aquarela, 11 aviões pintados, piloto personalizável, resíduos circulares e benefícios hexagonais. A vila começa colorida e poluída e ganha energia limpa, hortas e natureza integrada às construções. O primeiro voo oferece treino visual opcional; as compras mostram o terreno antes e a obra depois. Veja [implementação, capturas e validação](docs/DIRECAO_AQUARELA.md) e os [prompts da sprint](assets/watercolor/generation-sprint2.json).

## Novidades da versão 1.4

- **Papel e aquarela:** a direção de arte segue a logo. Os sprites recebem um filtro de papel (`tools/stylize.py`), com sombreamento em degraus, contorno de tinta azul-marinho e grão de papel, e os cartões das telas têm sombra e textura de papel. As fontes Fredoka, Nunito e Patrick Hand são embutidas no jogo, sob licença OFL.
- **Vila como diorama:** morros, rio com ponte, caminhos e um largo central onde o avião pousa. As cinco casas passam de industriais a solarpunk, uma a uma, conforme a vila avança.
- **Abertura em livro ilustrado:** quatro páginas, da cidade cinzenta ao lançamento do avião, com um rastro de aquarela nas cores da logo.
- **Piloto mais completo:** proporções de criança, 10 tons de pele, 12 estilos de cabelo, roupas, óculos, acessórios, aparelho auditivo e cadeira de rodas. A tela Piloto abre na primeira execução e tem o botão "Surpresa!".
- **Céu e fases:** sol e nuvens de papel no céu limpo. A fumaça de cada fase é tingida pelo bioma: úmida e cinza-azulada em Manaus, ocre em Petrolina. As fases ganham peças regionais, silhuetas da cidade no horizonte e cenário em quarteirões.
- **Coleta:** cada resíduo coletado deixa um respingo de aquarela na sua cor.
- **Ajustes:** HUD do voo mais discreto, pintura padrão "Liso", permanência padrão de 2,0 s (ajustável de 1,0 a 3,5 s) e logo com a proporção correta nas telas.

## Novidades da versão 1.3.1

- **Licença:** o jogo passa a ser código aberto sob Creative Commons Atribuição 4.0 (CC BY 4.0), como pede o item 4.6 do regulamento da jam (ver [Licenças](#licenças)). O `LICENSE` vai no repositório, no executável e no cartucho, e os créditos do jogo citam a licença e o modelo de pose usado.

## Novidades da versão 1.3

- **Núcleo separado da plataforma:** o jogo sem plataforma fica no núcleo (`core.py`). O executável (`app.py`) cuida da janela, do som, do relógio, da tela cheia e da orientação da imagem, e o cartucho do console T-TEA (`cartridge.py`) usa o mesmo núcleo.
- **Cartucho para o console T-TEA:** todos os segmentos funcionam no console. Com os pés, o avião e o cursor seguem o ponto da projeção onde a criança pisa; com tronco, mãos ou cabeça, os pontos vêm da câmera do console. O perfil fica no armazenamento do jogador. Veja [Console T-TEA (cartucho)](#console-t-tea-cartucho).
- **Projeção e chão:** a opção "Projeção e chão", em Opções (só no executável), gira a imagem em 0°, 90°, 180° ou 270° e espelha. Com quatro alvos numerados e uma foto da webcam, o jogo aprende onde está a projeção no chão, e então onde a criança pisa vira a posição do avião. A antiga opção "Girar 180°" é migrada para essa tela.
- **Cursor à frente:** a distância do cursor à frente dos dedos vai de 0 a 35% (padrão 12%).
- **Controle confortável:** cabeça, mãos e tronco só aceitam a posição neutra quando o segmento está parado. Com "Centrar sozinho" (padrão), a posição neutra é refeita sozinha depois de 3 segundos sem o segmento. As mãos usam o centro da palma.
- **Seleção mais tolerante:** o botão em seleção cresce 30 px de cada lado, e sair dele por até 0,5 s não zera a contagem.
- **Opções reorganizadas:** "Projeção e chão", "Centrar sozinho", "Trocar cima/baixo" e "Trocar lados" (inverte esquerda e direita).

## Novidades da versão 1.2

- **Controle por posição:** com o controle corporal, o corpo indica o ponto em que o avião deve ficar, e o avião vai até lá suavemente. Ficar parado mantém o avião parado. A opção "Controle do avião", em Opções, volta ao controle por velocidade.
- **Momento de foco:** perto de uma batida, o tempo desacelera e uma seta indica o movimento que desvia do obstáculo. Acertar rende pontos e um desvio guiado. Pode ser desligado em Opções.
- **Abertura didática:** o começo do voo apresenta uma coisa de cada vez, com legendas que ensinam cada manobra.
- **Sensação de voo:** o avião tremula como papel e inclina o nariz ao subir. A opção "Efeitos fortes (clarão, tremor)" desliga clarões e tremores da tela.
- **Medida de movimento:** o resultado mostra o tempo em movimento, os alcances percorridos e os momentos de foco acertados. Cada voo entra no histórico do perfil, para o supervisor ou o terapeuta acompanhar.
- **Equilíbrio recalibrado:** a simulação de `tools/balance.py` passou a pegar de fato 4 de cada 10 resíduos (antes pegava menos, porque reaproveitava decisões). Com isso, a transformação por coleta e os custos da vila e das peças foram recalibrados para que a fase continue durando cerca de 4 minutos.

## O jogo

O Dobramundo é um exergame sério de voo, com proposta terapêutica. A criança pilota um avião de papel reciclado sobre cidades brasileiras poluídas e, a cada voo, as transforma em cidades solarpunk integradas à natureza do seu bioma. O nome une a dobradura de papel à transformação do mundo, como na canção *Aquarela*, popularizada por Toquinho.

O jogo atende ao console T-TEA, com projeção no chão e controle pelos pés, mas não se restringe a ele: pode ser projetado em mesas e paredes ou exibido em monitores, e o controle pode ser feito pelos pés, pelo tronco, por uma das mãos ou pela cabeça. Destina-se a crianças neurodiversas e com deficiências motoras, visuais, sensoriais ou do neurodesenvolvimento, oferecendo a cada uma um modo de interação compatível.

Projeto da Liga de Psiquiatria e Neurociências – CENSUPEG, desenvolvido para a 3ª ExerGame JAM LARVA/UDESC 2026. Versão 1.4.0.

### Tema e objetivo

O jogo trata a sustentabilidade em duas escalas:

- **Ambiental:** adota o paradigma solarpunk, vertente que imagina sociedades tecnológicas, movidas a energia renovável e integradas à natureza. O percurso segue a trilogia vaporpunk, dieselpunk e solarpunk, da cidade dieselpunk à solarpunk (Lodi-Ribeiro, 2012).
- **Pessoal:** atividade corporal regular, prazerosa e acessível.

O objetivo não é restaurar uma natureza intocada, mas construir uma cidade em que a natureza integra a vida urbana. Na abertura, uma criança dobra um jornal em avião numa metrópole poluída. A cada voo, os resíduos recolhidos viram recursos que desenvolvem a vila-base e o avião.

### Objetivos de Desenvolvimento Sustentável

| ODS | Nome | Relação com o jogo |
|---|---|---|
| 3 | Saúde e Bem-Estar | Atividade física e estímulo sensório-motor |
| 7 | Energia Limpa e Acessível | Microgeração solar |
| 10 | Redução das Desigualdades | Acessibilidade |
| 11 | Cidades e Comunidades Sustentáveis | Cidade integrada à natureza |
| 12 | Consumo e Produção Responsáveis | Resíduos como recursos |
| 15 | Vida Terrestre | Biomas brasileiros |

## Fases

A versão atual tem duas fases, cada uma numa cidade brasileira do seu bioma:

| Fase | Cidade | Peças exigidas para a 3ª estrela |
|---|---|---|
| Amazônia | Manaus (AM) | Estabilizador, nível 1 |
| Caatinga | Petrolina (PE) | Leme, nível 1, e Quilha, nível 1 |

- Petrolina abre quando a criança conquista pelo menos 1 estrela em Manaus.
- Cerrado, Mata Atlântica, Pantanal e Pampa aparecem no mapa como "Em breve".
- A paisagem de cada fase tem três estágios: cidade industrial (dieselpunk), despertar ecológico e cidade solarpunk. Eles se sucedem aos 33,3% e aos 66,7% de transformação.
- No estágio industrial, peças regionais (guindaste, termelétrica e contêineres em Manaus; torres de transmissão, caixas d'água e galpões em Petrolina) se misturam às estruturas do kit, e silhuetas da cidade regional aparecem no horizonte.
- O céu das fases poluídas é tingido pelo bioma: cinza e úmido em Manaus, ocre e seco em Petrolina.
- O cenário é organizado em quarteirões, com vãos entre eles, em vez de uma fila contínua de peças.

## Como se joga

Cada partida segue o ciclo **vila-base, mapa, voo e resultado**. Na vila, a criança escolhe a fase e o modo no mapa. No voo, o avião decola da vila, coleta resíduos e power-ups, desvia de obstáculos e acumula transformação. No resultado, estrelas e recursos vão para o perfil, e a criança volta à vila para construir melhorias e peças.

### Primeira execução

Na primeira execução, a criança começa com um **piloto neutro** e escolhe sua aparência. Depois vêm o **Aviso ao supervisor**, quando necessário, a **Calibração**, se o controle for corporal, e a **vila**. Na primeira decolagem pelo mapa, um treino opcional ensina movimento, coleta e os três desvios com pictogramas e prática sem perda de vidas. O treino pode ser pulado ou repetido em Opções. A história fica disponível em Opções ("Ver a abertura"), e o personagem pode ser modificado pelo botão Piloto da vila.

A abertura é um livro ilustrado de quatro páginas: uma cidade cinzenta e cheia de fumaça; uma criança que encontra um jornal na rua; a dobradura do avião, passo a passo, sobre uma mesa de papel, com a legenda de cada dobra; e o lançamento, com um rastro de aquarela nas cores da logo enquanto a cidade ganha cor.

### Resíduos e recursos

Há quatro tipos de resíduo, com as cores da coleta seletiva da Resolução CONAMA nº 275/2001: papel (azul), plástico (vermelho), metal (amarelo) e vidro (verde). Eles aparecem em três alturas da pista. Cada coleta gera recursos para a vila e para as peças do avião: 4 recursos por coleta no modo Normal e 1 no modo Difícil. Resíduos têm moldura circular e objeto pintado; benefícios têm moldura hexagonal; obstáculos têm volume e silhueta próprios. Ao coletar, um respingo opcional de aquarela na cor do resíduo marca o ponto.

### Obstáculos

Cada tipo de obstáculo pede uma manobra:

- **Obstáculo baixo:** passar por cima.
- **Portal:** passar por baixo.
- **Torre:** desviar para o lado.

### Abertura didática

No Normal, o começo de cada voo apresenta uma coisa de cada vez. Nos primeiros segundos, só há resíduos, com a legenda "Pegue os resíduos!". Depois vêm um obstáculo baixo, um portal e uma torre, cada um sozinho na faixa do meio, com a legenda correspondente ("Passe por cima!", "Passe por baixo!" ou "Desvie para o lado!") e um resíduo no caminho certo, que mostra a resposta. O sorteio normal começa por volta dos 22 segundos. No Difícil, a abertura aparece só no primeiro voo de cada fase.

### Momento de foco

Quando um obstáculo vai atingir o avião em poucos instantes e a criança ainda não reagiu, o mundo passa a andar a 12% da velocidade normal. Uma seta aparece junto do avião, com um pedido em destaque: "SUBA!" para obstáculo baixo, "DESÇA!" para portal, "PARA A ESQUERDA!" ou "PARA A DIREITA!" para torre. Uma barra mostra o tempo restante, que é de 1,8 segundo no Normal e de 1,2 segundo no Difícil.

- **Acerto ("Boa!"):** o avião faz um desvio guiado até um ponto seguro, o obstáculo não bate e a criança ganha 50 pontos.
- **Erro ("Quase!"):** o tempo volta ao normal, e o obstáculo só bate se o avião continuar no caminho.

Só conta o movimento feito depois que a seta aparece. Os momentos ocorrem no máximo a cada 9 segundos (o primeiro, após 5 segundos) e não aparecem com escudo, invulnerabilidade ou no modo de demonstração; os obstáculos da abertura didática sempre têm o seu momento. A opção "Momento de foco (câmera lenta)", em Opções, desliga o recurso.

### Power-ups

- **Escudo:** 6 segundos sem colisões.
- **Ímã:** 7 segundos atraindo resíduos das faixas vizinhas.
- **Reparo:** devolve uma vida perdida. Com as vidas cheias, adiciona 2% à transformação da cidade.

### Vidas

A criança tem três vidas. Cada colisão consome uma delas, seguida de 1,25 segundo de invulnerabilidade, e zera o combo. Sem vidas, o voo termina.

### Transformação e estrelas

A transformação da cidade vai de 0% a 100%, começando em 5%. Ao atingir os limiares, a criança ganha estrelas:

- 1 estrela aos 33,3%, no despertar ecológico;
- 2 estrelas aos 66,7%, na cidade solarpunk;
- 3 estrelas com a cidade completa (100%), desde que as peças exigidas pela fase estejam instaladas no avião. Sem elas, a conclusão rende 2 estrelas, e a tela de resultado indica quais peças faltam.

Ao chegar a 100%, o avião segue planando por 3 segundos para a criança ver a cidade.

### Modos de jogo

A dificuldade é a primeira escolha do mapa, em dois cartões grandes: **Normal** (mais calmo) e **Difícil** (mais rápido, com combo). O modo atual também aparece na vila e no painel do voo.

| | Normal | Difícil |
|---|---|---|
| Velocidade | Metade da velocidade-base (170 unidades/s) | Velocidade plena (340 unidades/s) |
| Resíduos | 1 a cada 4 sorteados | Todos |
| Pontos por resíduo | 65, fixos | 15 vezes o combo |
| Transformação por coleta | 1,18 ponto percentual | 0,115, mais 0,013 com combo de 4 ou mais |
| Recursos por coleta | 4 | 1 |
| Combo | Não há | Sobe a cada 4 coletas seguidas, até 8 vezes |

O combo zera se a criança passar 2,2 segundos sem coletar ou ao colidir. Nos dois modos, a dificuldade cresce ao longo de 240 segundos: a frequência de obstáculos aumenta e a velocidade sobe até 30 unidades/s no Difícil (metade no Normal); a transformação acrescenta até mais 30.

Com a criança pegando 4 de cada 10 resíduos, uma fase dura cerca de 3,7 minutos no Normal e 3,8 no Difícil, e tudo da vila e do avião fica comprado em cerca de 11 voos no Normal e 5 no Difícil (simulação em `tools/balance.py`).

### Metas curtas

Durante o voo aparece uma meta por vez, de 20 a 60 segundos: coletar resíduos de um tipo, desviar de obstáculos na faixa do avião, passar por baixo de portais ou pegar power-ups. No Normal os alvos são menores (por exemplo, 2 resíduos ou 3 desvios; no Difícil, 6 e 6). Cada meta cumprida rende 0,5% de transformação, 6 recursos e 50 pontos.

### Vila-base

A vila tem oito melhorias, compradas com recursos. Cada uma aparece no seu lugar na cena, que é um diorama de papel: morros, um rio com ponte, caminhos e um largo central onde o avião pousa. As cinco casas do fundo passam de industriais a solarpunk, uma a uma, conforme a vila avança; o céu clareia, com sol e nuvens de papel, a fumaça diminui e surgem brilhos de papel. Há árvores e gente passeando. O percentual "sustentável" da tela é a proporção de melhorias construídas. ESC na vila pergunta se é para sair do jogo.

| Melhoria | Custo | Descrição |
|---|---|---|
| Ponto de troca | 72 papel, 72 plástico | Separa os resíduos e os transforma em recursos |
| Horta urbana | 96 papel, 72 vidro | Alimento fresco plantado no meio da vila |
| Painéis solares | 144 metal, 120 vidro | Microgeração de energia limpa nos telhados |
| Compostor | 96 plástico, 72 metal | Restos orgânicos viram adubo para a horta |
| Cisterna | 120 plástico, 96 metal | Guarda a água da chuva para regar e beber |
| Bicicletário | 120 metal, 72 plástico | Bicicletas no lugar dos carros a diesel |
| Telhado verde | 144 papel, 96 vidro | Plantas no telhado refrescam as casas |
| Turbina eólica | 192 metal, 120 vidro, 72 papel | O vento também gera energia para a vila |

### Peças do avião

As peças são reaproveitadas de resíduos. Cada uma tem dois níveis e altera o voo:

| Peça | Nível 1 | Nível 2 | Efeito por nível |
|---|---|---|---|
| Estabilizador | 120 papel, 72 plástico | 216 papel, 144 plástico, 72 metal | Caixa de colisão 7% menor e inclinação nas curvas 20% menor |
| Leme reaproveitado | 120 plástico, 72 metal | 192 plástico, 144 metal, 72 vidro | Resposta do avião 18% mais rápida |
| Quilha de lata | 120 metal, 72 vidro | 192 metal, 144 vidro, 72 papel | Velocidade máxima 8% maior e zona morta do controle corporal 25% menor |

### Hangar

O hangar oferece 11 dobraduras de voo distinto, entre elas uma miniatura do 14-Bis. A pintura pode ser a original do estúdio ou uma de 14 cores de papel. Há 26 padrões: dois são gratuitos (Liso e Jornal) e os outros 24 custam pontos, de 300 a 5 000. Os pontos se acumulam em todos os voos. A pintura padrão é a Liso, papel branco limpo. Escolher uma cor define o padrão do avião como liso.

### Piloto

A criança monta o piloto na tela Piloto, que abre antes da vila na primeira execução e depois fica no menu da vila. Um balão de fala acompanha as escolhas. O botão **Surpresa!** sorteia uma combinação, sem mexer no aparelho auditivo nem na cadeira de rodas, e na primeira vez o botão **Pronto!** confirma a escolha.

As opções são:

- **Pele:** 10 tons, seis realistas e quatro de fantasia (roxo, azul, verde e rosa).
- **Cabelo:** 12 estilos (curto, cacheado, black power, longo, tranças, coque, franja, maria-chiquinha, afro puffs, moicano, lenço e raspado), em 10 cores.
- **Roupa:** 8 cores de camiseta.
- **Óculos:** sem óculos, redondos, quadrados ou de sol.
- **Acessório:** nenhum, boné, lenço, abafador de ruído, capacete de aviador, flor, tiara ou coroa de papel.
- **Aparelho auditivo** e **cadeira de rodas:** sim ou não.

O piloto não tem marcação de gênero, e os dispositivos assistivos são itens comuns da lista.

## Controles

### Controle corporal pela webcam

O controle usa visão computacional (MediaPipe Pose). O jogo acompanha o segmento escolhido e converte seu deslocamento, em relação à postura calibrada, em dois eixos que movem o avião para cima, para baixo, para a esquerda e para a direita.

Em Opções, a opção **Controle do avião** escolhe o modo:

- **Posição (padrão):** a postura calibrada corresponde ao centro da pista, em altura média. O corpo indica o ponto em que o avião deve ficar, e o avião vai até lá suavemente. Ficar parado mantém o avião parado. Se a câmera perder o segmento, o avião mantém o rumo.
- **Velocidade:** o deslocamento do corpo define a velocidade do avião, como nas versões anteriores.

| Segmento | Pontos do MediaPipe Pose usados |
|---|---|
| Pés | Tornozelos e pés (índices 27 a 32) |
| Tronco (em pé) | Ombros e quadris (índices 11, 12, 23 e 24) |
| Tronco (sentado) | Ombros (índices 11 e 12) |
| Mão direita | Punho (índice 16) |
| Mão esquerda | Punho (índice 15) |
| Cabeça | Nariz e orelhas (índices 0, 7 e 8) |

- **Calibração:** a criança fica parada na postura confortável por cerca de 2 segundos, com pelo menos 15 leituras. O jogo usa a mediana como centro, e o repouso só é aceito se o segmento ficou parado; se ele se mexer, a calibração recomeça. A calibração pode ser refeita em Opções, na pausa ("Recalibrar") e ao trocar de segmento.
- **Centrar sozinho:** com a opção ligada (padrão), cabeça, mãos e tronco refazem a postura neutra sozinhos depois de 3 segundos sem o segmento. Os pés não se recalibram sozinhos.
- **Trocar lados:** inverte esquerda e direita, para câmeras que não espelham a imagem.
- No console T-TEA, os mesmos segmentos usam os pontos da câmera do console (veja [Console T-TEA (cartucho)](#console-t-tea-cartucho)).
- **Menus:** um cursor acompanha o segmento. O botão é acionado quando o cursor permanece sobre ele pelo tempo de permanência, que é de 2,0 segundos por padrão e pode ser ajustado de 1,0 a 3,5 segundos em Opções.
- **Sensibilidade:** de 0,5 a 2,0 vezes (padrão 1,0). Valores maiores exigem um movimento menor.
- **Pausa automática:** se o segmento sai da área de captura por 1 segundo durante o voo, o jogo pausa. Ao voltar, espera a presença estável por 1,2 segundo e faz uma contagem de 3 segundos antes de retomar.
- Sem webcam, sem as bibliotecas ou sem o modelo de pose, o jogo segue com teclado e mouse. Se a câmera falhar com um segmento selecionado, o motivo aparece em Opções e na calibração.

### Pés sobre a projeção

Com a superfície **Chão** e o segmento **Pés**, o avião e o cursor seguem onde a criança pisa na imagem projetada. Sem calibração, os pés usam a posição relativa à postura neutra, como os demais segmentos. Para a calibração, use **Opções > Projeção e chão** (só no executável):

1. Deixe a webcam vendo toda a projeção no chão e escolha "Calibrar os 4 cantos". Os alvos 1, 2, 3 e 4 aparecem a 15% das bordas da imagem.
2. A câmera tira uma foto. Clique no centro de cada alvo, na ordem 1 (superior esquerdo), 2 (superior direito), 3 (inferior direito) e 4 (inferior esquerdo).
3. Confira pisando sobre os alvos. "Cursor à frente" (0 a 35%, padrão 12%) desloca o cursor um pouco à frente dos dedos, para ficar visível.

A câmera estima a posição do pé; ela não detecta o contato com o chão. Passar a imagem de deitada para em pé (90° ou 270°), ou o contrário, apaga a calibração, e o jogo pede para calibrar de novo. Espelhar ou girar 180° não exige nova calibração, mas mover a câmera ou o projetor exige.

### Teclado e mouse (supervisor)

| Ação | Teclas |
|---|---|
| Voar | Setas ou W, A, S, D. Espaço também sobe |
| Navegar nos menus | Setas ou W, A, S, D |
| Confirmar nos menus | Enter, Espaço ou clique |
| Voltar nos menus | Esc ou Backspace |
| Pausar e retomar o voo | P ou Esc |
| Voltar à vila, na pausa | C |
| Tela cheia | F11 (em qualquer tela) |
| Caixas de colisão, no voo | F3 |
| Modo demonstração, no voo, sem colisões | F2 |

Com o controle corporal por posição, uma tecla de direção pressionada pelo supervisor tem prioridade sobre o corpo enquanto estiver apertada.

O mouse também seleciona botões por permanência quando não há controle corporal ativo.

### Superfícies de exibição

Em Opções, a superfície pode ser monitor, parede, mesa ou chão (T-TEA). Cada uma traz uma sugestão de segmento: qualquer segmento, tronco ou cabeça, uma das mãos, ou pés sobre a projeção. Se a câmera já estiver em uso, escolher a superfície aplica o segmento sugerido (chão: pés; mesa: mão direita; parede: tronco em pé), com um aviso. Para câmeras vistas de cima, a opção **Trocar cima/baixo** troca o sentido vertical.

Em **Opções > Projeção e chão** (só no executável), a imagem inteira pode ser girada no sentido horário em 0°, 90°, 180° ou 270° e espelhada. Espelhar serve à projeção por trás de uma parede. Girar serve ao projetor no teto ou à imagem no chão ou na mesa; girada 90° ou 270°, a imagem fica em pé, com faixas pretas dos lados. O mouse é convertido de volta para as coordenadas do jogo.

## Acessibilidade, segurança e privacidade

- **Alto contraste:** dessatura o fundo e destaca avião, resíduos, obstáculos e alertas com cores intensas e contornos espessos.
- **Efeitos fortes:** a opção "Efeitos fortes (clarão, tremor)", em Opções, quando desligada, tira o clarão vermelho da colisão, o clarão da estrela e o tremor da tela, e suaviza o tom do momento de foco. Para crianças com sensibilidade sensorial.
- **Som:** volumes geral, de música e de efeitos, e opção de silêncio, que reduz a carga sensorial em casos de hipersensibilidade auditiva. Cada estágio tem sua própria trilha, com troca suave.
- **Ritmo:** tempo de permanência e sensibilidade ajustáveis, pausa automática, pausa a qualquer momento com P ou Esc, e momento de foco desligável.
- **Vídeo:** processado localmente, quadro a quadro, e nunca gravado. O supervisor vê apenas uma miniatura ao vivo, mantida em memória.
- **Supervisão:** o uso requer a supervisão de um adulto (Pereira et al., 2023). Na primeira execução, o jogo mostra um aviso ao supervisor, que precisa confirmar a leitura antes de seguir.
- **Dados e LGPD:** o aviso cita os arts. 11 e 14 da Lei nº 13.709/2018 (LGPD) e informa que o uso depende do consentimento dos responsáveis. O perfil salvo guarda progresso, personalização, opções e o histórico dos últimos 60 voos. Cada voo guarda um resumo: fase, modo, tipo de controle, data, duração, transformação, estrelas, pontos, batidas, momentos de foco acertados e tempo e alcances em movimento. Não guarda imagens nem medidas do corpo: o movimento aparece só como tempo e alcances somados por voo, e a calibração da postura neutra fica só na memória e é refeita a cada sessão.

## Instalar e jogar

### Executável para Windows

Após a geração com `build_windows.bat` (ver [Gerar o executável](#gerar-o-executável)), o jogo fica na pasta `dist\Dobramundo\`. Abra `Dobramundo.exe` dentro dela e distribua a pasta inteira. Com a opção `onefile`, o arquivo gerado é `dist\Dobramundo.exe`. O executável não mostra janela de console, a menos que seja gerado com `DOBRA_CONSOLE=1`.

### Pelo código-fonte

Requisitos: Python 3.8 ou mais novo. A webcam é opcional e exige MediaPipe e OpenCV.

```
python -m pip install -r requirements-webcam.txt
python run_dobramundo.py
```

- `python -m dobramundo` é equivalente a `python run_dobramundo.py`.
- A opção `--sem-som` inicia o jogo sem som.
- Para jogar só com teclado e mouse, instale apenas `requirements.txt`.
- No Windows, `Jogar_Dobramundo.bat` instala as dependências na primeira vez e inicia o jogo.
- O controle corporal exige o modelo `assets/pose_model/pose_landmarker_lite.task`.

### Onde ficam o perfil, o log de erros e o relatório

| Arquivo | Executável | Código-fonte |
|---|---|---|
| `dobramundo_perfil.json`, com progresso, personalização e opções | `%APPDATA%\Dobramundo` (Windows) ou `~/.local/share/Dobramundo` (Linux) | Pasta `save/` na raiz do projeto, se for gravável |
| `dobramundo_erro.log`, com o rastreamento de uma falha | Mesma pasta | Mesma pasta |
| `dobramundo.log`, com avisos (imagem, som ou câmera que falhou, perfil que não gravou) | Mesma pasta | Mesma pasta |
| `self_test.json`, com o relatório do `--self-test` | Mesma pasta | Mesma pasta |

Se a pasta escolhida não for gravável, o jogo usa a próxima opção da lista (a pasta do sistema e, por fim, a pasta temporária). No macOS, a pasta do sistema é `~/Library/Application Support/Dobramundo`. A variável de ambiente `DOBRAMUNDO_DATA_DIR` substitui a pasta de dados. O perfil é gravado de forma atômica, com arquivo temporário e troca.

### Importar o save do protótipo Eco Runner

Se não houver perfil salvo, o jogo importa da pasta de dados do protótipo (`EcoRunner`, ou a pasta `save/` do código-fonte) os pontos acumulados, os padrões comprados, a pintura e o avião escolhidos e o modo de jogo. A importação acontece só na primeira execução.

## Console T-TEA (cartucho)

O Dobramundo também roda como cartucho do console T-TEA. O console cuida da janela, do relógio, da câmera, do modelo de pose e da pausa; o cartucho leva só o núcleo do jogo. Não há webcam, MediaPipe, self-test nem janela própria no cartucho.

- **Rastreamento:** perfil "body" (os 33 pontos do corpo), com resolução de 1100 x 650.
- **Pés:** o chão interativo do console define a posição do avião e do cursor, e pisar sobre um botão o escolhe.
- **Tronco, mãos e cabeça:** o movimento é medido nos pontos da câmera do console, espelhados. A opção **Trocar lados** desfaz o espelho se a câmera estiver atrás da criança.
- **Primeira vez:** o controle começa nos pés, com a superfície Chão.
- **Jogador registrado:** o perfil fica no armazenamento do jogador. As opções de controle (sensibilidade, permanência, controle por posição, momento de foco, efeitos fortes, alto contraste, silêncio, trocas de lado e de cima/baixo e centrar sozinho) acompanham a criança, e cada voo vira um evento da sessão.
- **Teclas:** ESC encerra o jogo, P pausa e F2 (demonstração) fica com o console.
- **Perda do rastreamento:** o console pausa o jogo, que mostra "Volte para a área do jogo". Ao voltar, o voo retoma depois de uma contagem.
- **Opções:** "Tela cheia" não aparece, e "Projeção e chão" fica desativada, porque a projeção é do próprio console.

Para gerar o cartucho, use a ferramenta oficial de cartuchos do T-TEA (comando `tsdk`, Python 3.14):

```
python tools/build_cartridge.py --tsdk CAMINHO_DO_TSDK
python tools/build_cartridge.py --so-montar
```

O primeiro comando monta `build/cartucho/`, roda `tsdk check` e `tsdk build` e gera `dist/dobramundo-<versão>.ttea`. Com `--so-montar`, ele só monta a pasta, sem validar nem gerar o arquivo. O cartucho leva o `LICENSE` (CC BY 4.0) e um `CREDITOS.md` gerado a partir dos créditos do jogo.

## Gerar o executável

### Windows

```
build_windows.bat [onefile] [nopause]
```

O script procura o Python 3, cria o ambiente `.venv`, instala `requirements-webcam.txt` e `pyinstaller>=6,<7` com as versões exatas de `constraints-build.txt`, limpa as pastas `build` e `dist` e roda `PyInstaller --noconfirm --clean Dobramundo.spec`. Depois copia o README para a pasta de saída e executa `Dobramundo.exe --self-test 90 --exigir-camera` sem abrir janela (`SDL_VIDEODRIVER=dummy`). A geração falha se o self-test retornar código diferente de zero ou não gravar o relatório: faltam sprites, um voo não chegou ao estágio 3 ou, com `--exigir-camera`, o detector de pose não carregou dentro do executável.

- `onefile` gera um único arquivo, `dist\Dobramundo.exe`. Sem essa opção, o padrão é `dist\Dobramundo\`.
- `nopause` não espera tecla ao final, útil em automações.
- `DOBRA_CONSOLE=1` mantém a janela de console, para depuração.
- O PyInstaller não faz compilação cruzada. O `.exe` precisa ser gerado no Windows.

### Linux

```
./build_linux.sh
```

O script segue a mesma sequência com `python3` e gera `dist/Dobramundo/Dobramundo` (modo de pasta). Ele confere se o relatório do self-test contém `"status": "ok"`. No Debian ou no Ubuntu, instale antes o pacote `python3-venv`.

### Especificação e assets

`Dobramundo.spec` empacota toda a pasta `assets/` com as extensões `.png`, `.json`, `.ogg`, `.wav`, `.task`, `.ico`, `.ttf` e `.txt` (as fontes e as licenças OFL vão junto). As variáveis `DOBRA_ONEFILE=1` (arquivo único) e `DOBRA_CONSOLE=1` (console) alteram a geração. Para trocar um sprite sem recompilar, coloque o PNG em `Dobramundo/assets/<pasta>/<nome>.png`, ao lado do executável. O jogo procura essa cópia antes da embutida.

## Desenvolvimento

### Estrutura do repositório

```
dobramundo/                          pacote do jogo
    __init__.py, __main__.py         nome, versão e entrada com "python -m dobramundo"
    main.py                          ponto de entrada do executável, self-test e mensagens de erro
    core.py                          núcleo sem plataforma: GameCore (serviços e quadro) e first_scene
    app.py                           executável: janela, laço principal, som, tela cheia e orientação
    cartridge.py                     cartucho do console T-TEA: ConsoleCore e Dobramundo
    config.py                        constantes do motor (tela, projeção, voo, neblina, paralaxe)
    paths.py                         pastas de assets e de dados (código-fonte e executável)
    persistence.py                   perfil versionado em JSON e importação do protótipo
    audio.py                         trilhas por estágio, efeitos e volumes
    selftest.py                      teste de fumaça (--self-test) e critérios de aprovação
    log.py                           avisos em dobramundo.log
    util.py                          funções numéricas, de cor e de neblina
    content/                         dados do jogo, sem pygame
        biomes.py                    fases, estágios, cenários e obstáculos
        planes.py                    aviões, pinturas, padrões e curvas de manobra
        pilot.py                     opções do piloto
        progress.py                  melhorias da vila, peças do avião e estrelas
        items.py                     resíduos, power-ups e tipos de obstáculo
        texts.py                     textos, créditos e referências
    game/                            regras do voo, sem pygame
        run.py                       um voo: vidas, pontos, combo, estrelas e eventos
        focus.py                     momento de foco: batida, seta e desvio guiado
        missions.py                  metas curtas dentro do voo
        world.py                     pista, trechos, transformação e abertura didática
        player.py                    física do avião, manobras e controle por posição
        entities.py                  objetos e caixas de colisão
    engine/                          desenho pseudo-3D
        world_view.py                ordem de pintura de uma fase
        sky.py, ground.py            céu de papel em paralaxe e chão texturizado
        paper.py                     formas de papel desenhadas por código (vila e abertura)
        sprites.py                   projeção, neblina e caches de sprite
        cache.py                     BoundedCache (descarte gradual) usado por todos os caches
        plane_skin.py, pilot.py      aparência do avião e piloto em camadas
        assets.py                    carregamento preguiçoso dos PNG
    input/                           entradas
        hub.py                       teclado, mouse e escolha da fonte e do controle
        pose.py                      segmentos, calibração e eixos (sem MediaPipe)
        camera.py                    webcam do executável: MediaPipe Pose numa thread
        console.py                   pontos do rastreamento do console T-TEA
        floor.py                     calibração dos 4 cantos: câmera para a projeção
    ui/                              tema (fontes e cartões de papel), botões e seleção por permanência
    scenes/                          telas: abertura, piloto, aviso, calibração, vila, mapa, voo etc.
        __init__.py                  registro das cenas: scene.goto("vila")
        projection.py                Projeção e chão: orientação e calibração (só no executável)
assets/                              sprites, sons, texturas, fontes, modelo de pose e curvas
tools/                               geração de assets e do cartucho (ver tools/README.md)
    build_cartridge.py               monta e valida o cartucho do console T-TEA
    stylize.py                       filtro de papel e aquarela aplicado aos sprites
tests/                               suíte pytest
docs/                                GDD e arte original da logo
docs/arquitetura.md                  arquitetura do código
run_dobramundo.py                    atalho para rodar pelo código e entrada do PyInstaller
Dobramundo.spec                      receita do PyInstaller
build_windows.bat, build_linux.sh    geração do executável
Jogar_Dobramundo.bat                 atalho para jogar pelo código no Windows
pyproject.toml                       metadados, dependências opcionais e configuração do ruff e do pytest
constraints-build.txt                versões exatas usadas para gerar o executável
.github/workflows/testes.yml         CI: lint, testes e self-test em Python 3.8 e 3.12
```

### Testes

```
python -m pytest
```

A suíte roda sem janela e sem áudio (drivers `dummy`), com o perfil isolado em pasta temporária. Ela cobre seis módulos: assets, cenas, controle corporal (sem webcam), regras do voo, progressão e perfil, e a pista.

### Lint e formato

```
ruff check .
ruff format --check .
```

A configuração está em `pyproject.toml`: 120 colunas, alvo Python 3.8 e as regras E, F, W, I, B e UP. Sem `--check`, `ruff format` reescreve os arquivos.

### Teste de fumaça

```
python -m dobramundo --self-test 240
```

O número após `--self-test` é a quantidade de quadros por voo, com padrão de 240. O teste percorre todas as telas e voa as duas fases com invencibilidade, forçando as três etapas de transformação. Grava `self_test.json` na pasta de dados, com os sprites carregados, os tempos de quadro (média e percentil 95) e o resultado de cada voo. O perfil real não é alterado. O relatório traz `status` (`ok` ou `falhou`) e a lista `falhas`; o código de saída é 1 quando há falha. Com `--exigir-camera`, o teste também carrega o detector de pose do MediaPipe (sem abrir a webcam) e reprova se ele não funcionar.

### Integração contínua

`.github/workflows/testes.yml` roda lint, testes e self-test a cada push e pull request, em Python 3.8 (mínimo declarado) e 3.12 (versão do build).

### Regenerar os assets

Os comandos abaixo estão detalhados, com dependências, em [tools/README.md](tools/README.md).

```
python tools/build_assets.py                   # sprites low-poly de fases e vila, já com o filtro de papel
python tools/stylize.py                        # refaz o filtro de papel nos sprites existentes
python tools/build_assets.py --pilot           # camadas do piloto e anchors.json
python tools/make_audio.py                     # trilhas e efeitos sonoros
python tools/make_logo.py ARTE.png             # logo, ícone da janela e ícone do executável
python tools/make_ground_textures.py           # texturas de solo da Caatinga
python tools/measure_obstacles.py              # confere as medidas de colisão contra os sprites
```

### Compatibilidade com Python 3.8

O projeto mantém compatibilidade com Python 3.8, que é o piso de `requires-python` e o alvo do ruff. Esse piso vale para o executável e para o código do pacote. O cartucho gerado para o console declara Python 3.14, exigido pela ferramenta oficial de cartuchos do T-TEA. Os módulos usam `from __future__ import annotations` e os tipos do `typing`.

## Créditos

- **Equipe:** Liga de Psiquiatria e Neurociências – CENSUPEG
- **Membros:** João Pedro Turnes (capitão), Isabella Cordeiro Sonza, Gerciane Larice da Silva Barros e Luiz Felipe Santana Tomio
- **Captura:** Adaptada do T-TEA 2.0 (LARVA/UDESC)
- **Modelos 3D:** kits 3D da equipe, aviões do estúdio 3D do protótipo e modelos low-poly gerados por código (`tools/lowpoly`)
- **Referências de design:** Star Fox 64, Subway Surfers, It Takes Two e Super Mario World
- **Programação:** IA generativa (Gemini e Claude) apoiou a programação
- **Tecnologia:** Python, pygame, OpenCV e MediaPipe Pose
- **Música e efeitos:** Sintetizados pelo projeto
- **Fontes:** Fredoka, Nunito e Patrick Hand (Google Fonts, licença OFL)
- **Evento:** 3ª ExerGame JAM LARVA/UDESC 2026

A música e os efeitos são gerados por síntese no script `tools/make_audio.py`. Os modelos low-poly das fases, da vila, dos resíduos e do piloto são gerados por código em `tools/lowpoly`.

## Referências

EPE. **Balanço Energético Nacional 2025: ano base 2024.** Rio de Janeiro: EPE, 2025.

LODI-RIBEIRO, G. (org.). **Solarpunk: histórias ecológicas e fantásticas em um mundo sustentável.** São Paulo: Draco, 2012.

PEREIRA, G. B. et al. Jogo sério para estímulo sensorial de crianças com transtorno do espectro autista. In: SBIE, 34., 2023, Passo Fundo. **Anais [...]**. Porto Alegre: SBC, 2023. DOI: 10.5753/sbie.2023.233744.

## Licenças

O regulamento da 3ª ExerGame JAM LARVA (item 4.6) determina que o executável e o código-fonte sejam disponibilizados como código aberto, sob licença Creative Commons, no Git da competição. Por isso:

- **Código, sprites, ícones, logo, textos, músicas e efeitos do Dobramundo:** [Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.pt-br), texto completo em [`LICENSE`](LICENSE). Qualquer pessoa pode copiar, adaptar e redistribuir, inclusive em outras edições da jam, desde que dê o crédito: *Dobramundo, Liga de Psiquiatria e Neurociências – CENSUPEG (3ª ExerGame JAM LARVA/UDESC, 2026)*, com link para a licença e indicação do que foi alterado.
- **Fora da CC BY 4.0, com as licenças de origem:**
  - **Modelo de pose** (`assets/pose_model/pose_landmarker_lite.task`): Google MediaPipe, licença Apache 2.0. Vai só no executável; o cartucho do T-TEA não o inclui.
  - **Captura corporal:** adaptada do T-TEA 2.0 (LARVA/UDESC), nas condições do grupo de origem.
  - **Fontes** (`assets/fonts`): Fredoka, Nunito e Patrick Hand, do Google Fonts, sob a SIL Open Font License 1.1. Os textos das licenças estão em `assets/fonts/OFL-*.txt`.
  - **Dependências** (pygame, numpy, OpenCV, MediaPipe e o runtime do T-TEA): cada uma com a sua licença. O executável inclui as bibliotecas do pygame (LGPL), do OpenCV e do MediaPipe (Apache 2.0) sem modificá-las.
