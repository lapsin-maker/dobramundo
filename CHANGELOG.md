# Histórico do Dobramundo

## 1.7.0 — 2026-10-25

- A transformação de cada cidade continua entre voos. A primeira execução apresenta o piloto, a história com botão Pular e a vila; os primeiros voos oferecem apoio, respeitando uma escolha explícita.
- Manaus e Petrolina abertas desde o início; recuperação pelo voo ativo, acelerada pelas coletas, e transição visual desde o começo do percurso. Margens industriais reforçadas com infraestrutura e menos vegetação dominante.
- Cursor dos pés alcança os quatro cantos a partir de uma zona confortável. A mira à frente atenua perto das bordas; o indicador do TSDK atual acompanha a seleção efetiva, com proteção contra leitura ausente.
- Opções divididas em quatro grupos, textos com mais contraste, piloto mais visível no avião e mapa com pigmento de aquarela. Avisos de recompensa saem do horizonte do voo.
- Preparo do cenário antes de iniciar a partida, solo com amostragem suave, avisos de ameaças nas bordas da ampliação e orçamento compartilhado de superfícies temporárias.
- Proteção contra duas instâncias usando os mesmos dados, migração explícita de perfis e preservação de arquivos de versões futuras. Concluir, fechar e repetir uma tela de resultado não duplica recompensas.
- Pacotes levam as imagens necessárias ao jogo, sem duplicar originais de edição e variantes preparadas. Montagem da release, inventário, comparações visuais, medição da leitura efetivamente usada e verificação do cartucho ficam versionados.
- Documentação de uso simplificada; notas das sprints anteriores reunidas no histórico. Detalhes e evidências em [Entrega 1.7](docs/ENTREGA_1_7.md).

## 1.6.0 — 2026-10-25

- Perfis locais independentes com cartões anônimos, preservação do save legado e recuperação a partir de cópias anteriores; falhas de leitura bloqueiam gravação destrutiva.
- Preparação de sessão: exploração sem eliminação, limite opcional de 120/180/240 s, assistência previsível e sementes comunitárias repetíveis. Resultados parciais preservam ganhos sem registrar conclusão não alcançada.
- Missões oferecidas conforme alvos disponíveis, com expiração após 60 s sem penalidade e nova oferta após um intervalo; repetição mantém parâmetros e preferência de material. Ponto de troca custa 8 papel/8 plástico e Horta custa 24 papel/16 vidro, antecipando a transformação inicial.
- Oito variações regionais com sementes publicadas; relatório de economia usa movimento, colisões, reação, erros e pausas.
- Treze imagens preparadas para o tamanho de uso, manifesto de procedência, caches limitados por bytes e descarte por bioma. Render de pista, objetos, avião e piloto dividido por responsabilidade; fallback preservado.
- Fábrica de cenas injetável, contratos de leitura do desenho, fontes e ajuste de texto comuns; testes organizados por comportamento. Formatação global em commit separado, sem alteração das árvores sintáticas.
- CI com versões fixadas por Python, cobertura, formatação e builds Windows/Linux com self-test. Exceções do cartucho passam a ser registradas sem conteúdo dos perfis.

## 1.5.0 — 2026-10-25

- Câmera com encerramento seguro e métricas locais de latência.
- Encerramento parcial com recompensa idempotente e aviso de falha ao salvar.
- Geração com rota segura verificável e conforto independente das compras.
- Carregamento seletivo do piloto, fundos opacos, renderização e pré-carga otimizadas.
- README, ferramentas e versão da entrega alinhados.

## Entrega anterior — sprint 3: controle confortável e mundo vivo

O editor confirma escolhas mais devagar e exige sair do alvo antes de repetir. O controle de cabeça tolera melhor a perda de um marco facial, oferece calibração dos quatro alcances confortáveis e interrompe o cursor quando a leitura envelhece. Alto contraste também amplia avião, objetos e passagens, com escala ajustável. A vila começa industrial e colorida, tem moradores e pedidos persistentes e evolui para jardins, energia e alimentos integrados às construções.

As margens do voo mudam gradualmente, o mapa tem rota e arte própria, o hangar mostra três modelos por página e a história usa quatro cenários ilustrados. Veja [escopo, operação e limites da sprint 3](docs/historico/SPRINT3.md). Os testes de renderização e controle não substituem ensaios presenciais com webcam, projeção e crianças.

Os artefatos dessa sprint pertencem à publicação histórica correspondente. Consulte a release mais recente para os downloads atuais.

## Entrega anterior — sprint 2: aquarela em movimento

Água e terreno avançam em perspectiva, e árvores e construções das margens passam pelo avião: o voo não fica sobre uma pintura parada. Manaus e Petrolina têm três estágios, com arte regional em aquarela, 11 aviões pintados, piloto personalizável, resíduos circulares e benefícios hexagonais. A vila começa colorida e poluída e ganha energia limpa, hortas e natureza integrada às construções. O primeiro voo oferece treino visual opcional; as compras mostram o terreno antes e a obra depois. Veja [implementação, capturas e validação](docs/historico/DIRECAO_AQUARELA.md) e os [prompts da sprint](assets/watercolor/generation-sprint2.json).

Baixe o executável e a galeria com gravações reais na [prévia da sprint 2](https://github.com/lapsin-maker/dobramundo/releases/tag/sprint2-aquarela-2026-10-25). A [documentação da entrega](docs/historico/ENTREGA_SPRINT2.md) explica a instalação, o perfil separado e a verificação dos arquivos. Esta prévia mantém a versão interna 1.4.0 e é identificada pela tag da sprint.

## Histórico — versão 1.4

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

