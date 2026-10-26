# Desempenho e estabilidade — 1.7

Windows 11, Core i7-10750H, 32 GB, Python 3.12.10, pygame 2.6.1, CPU, 1100 × 650. Três processos novos por condição, avatar personalizado idêntico, semente 7, 60 quadros interativos de aquecimento e 600 medidos por caso. Execução serial, sem builds ou suítes pesadas concorrentes. Dois checks rápidos da ferramenta de empacotamento foram executados durante a terceira repetição com câmera; ela deve ser lida como medição sob carga, sem atribuir todos os picos ao jogo. O computador manteve seus aplicativos habituais; uma amostra de uso total durante o ensaio registrou 73% de CPU, incluindo outros processos. Não é uma máquina de laboratório isolada, e a variação entre processos faz parte do resultado.

A preparação não entra no tempo do quadro interativo. Sem câmera, a execução é sem limite de frequência; com câmera, mira 60 FPS e exclui a espera do tempo medido. Não some percentis dos componentes inclusivos: cada JSON também contém custos exclusivos.

| Execução | Cena | Mediana ms | p95 ms | p99 ms | Máximo ms | Até 16,67 ms |
|---|---|---:|---:|---:|---:|---:|
| runtime-1 | amazonia_normal | 10.617 | 15.14 | 18.258 | 22.545 | 98.50% |
| runtime-1 | amazonia_contrast | 14.906 | 21.068 | 25.056 | 28.569 | 73.50% |
| runtime-1 | caatinga_normal | 7.033 | 9.956 | 11.439 | 12.461 | 100.00% |
| runtime-1 | caatinga_contrast | 11.244 | 16.431 | 22.89 | 31.113 | 95.50% |
| runtime-2 | amazonia_normal | 10.721 | 15.925 | 20.752 | 24.782 | 96.67% |
| runtime-2 | amazonia_contrast | 14.243 | 21.36 | 27.808 | 37.129 | 79.50% |
| runtime-2 | caatinga_normal | 7.51 | 11.882 | 14.226 | 15.348 | 100.00% |
| runtime-2 | caatinga_contrast | 12.26 | 20.117 | 25.107 | 32.584 | 89.67% |
| runtime-3 | amazonia_normal | 10.931 | 15.075 | 17.034 | 19.73 | 98.83% |
| runtime-3 | amazonia_contrast | 14.796 | 20.107 | 22.665 | 26.702 | 77.83% |
| runtime-3 | caatinga_normal | 7.147 | 9.886 | 12.171 | 16.557 | 100.00% |
| runtime-3 | caatinga_contrast | 10.798 | 15.068 | 18.701 | 21.234 | 98.00% |
| camera-1 | amazonia_normal | 12.922 | 19.328 | 25.076 | 31.024 | 85.00% |
| camera-1 | amazonia_contrast | 18.203 | 25.361 | 28.527 | 53.239 | 29.50% |
| camera-1 | caatinga_normal | 7.836 | 11.613 | 13.351 | 15.436 | 100.00% |
| camera-1 | caatinga_contrast | 12.594 | 17.409 | 20.617 | 22.299 | 93.67% |
| camera-2 | amazonia_normal | 12.297 | 17.519 | 23.404 | 35.79 | 92.50% |
| camera-2 | amazonia_contrast | 32.368 | 81.591 | 182.415 | 343.482 | 0.17% |
| camera-2 | caatinga_normal | 21.992 | 92.955 | 217.297 | 387.667 | 19.67% |
| camera-2 | caatinga_contrast | 24.638 | 41.919 | 66.551 | 114.308 | 0.00% |
| camera-3 | amazonia_normal | 19.773 | 25.892 | 32.579 | 96.18 | 20.33% |
| camera-3 | amazonia_contrast | 23.579 | 31.663 | 36.465 | 72.838 | 2.83% |
| camera-3 | caatinga_normal | 9.671 | 15.336 | 23.289 | 74.521 | 96.00% |
| camera-3 | caatinga_contrast | 12.302 | 17.321 | 20.494 | 26.09 | 93.17% |

**A meta de p95 até 16,67 ms não foi atingida em todas as condições.** Os resultados não sustentam promessa de 60 FPS constantes neste computador sob esta carga. A otimização de geometria do chão preserva pixels; a suavização introduzida nesta versão tem custo próprio e não deve ser confundida com uma redução universal do custo frente à versão 1.6.

## Entradas frias

| Bioma | Mediana do primeiro quadro ms | p95 ms | Máximo ms | Mediana do preparo ms | Maior tarefa indivisível ms |
|---|---:|---:|---:|---:|---:|
| amazonia | 40.144 | 72.792 | 72.792 | 582.679 | 136.571 |
| caatinga | 34.947 | 45.12 | 45.12 | 533.367 | 92.539 |

O orçamento cooperativo é conferido entre tarefas. A decodificação de uma imagem é indivisível e pode ultrapassá-lo; por isso sua duração é publicada. O voo não consome vidas nem a contagem de primeiras sessões enquanto prepara o cenário.

## Uso prolongado

30 ciclos × 2.400 quadros, 1200.0 s de voo simulado ativo; 801.453 s de parede. Preparação e menus são separados. Trocas de bioma, aparência e contraste, sem webcam. Sem falhas de ciclo ou crescimento descontrolado de entidades.

RSS final 570.3 MiB; máximo 617.1 MiB; últimos dez ciclos entre 563.8 e 617.1 MiB. Cache derivado máximo 192.0 MiB, sob orçamento de 192 MiB. Teto experimental de RSS: 768 MiB. Um ensaio sem crescimento contínuo não prova ausência de todo vazamento.

## Sequência realmente consumida

Ensaio adicional em janela nativa com controle de cabeça, 300 quadros por caso. Estado da fonte: `ok`. Resolução do relógio monotônico deste host: 15.625 ms. Cada JSON informa sequências distintas, fração utilizável e tempos da mesma amostra até canvas/apresentação. Ausência de pose/calibração utilizável não equivale a controle corporal aprovado. Não foram salvos vídeo ou landmarks.

A medição começa no retorno da captura, não na exposição do sensor, e termina na chamada de apresentação, não na luz emitida pelo projetor. Extremos confortáveis, perda/retorno, seis segmentos e projeção exigem o roteiro presencial.

| Cena | Sequências distintas | Quadros utilizáveis | Captura→apresentação p95 ms |
|---|---:|---:|---:|
| amazonia_normal | 155 | 0/300 | 78.0 |
| amazonia_contrast | 168 | 0/300 | 79.0 |
| caatinga_normal | 154 | 0/300 | 78.0 |
| caatinga_contrast | 160 | 0/300 | 93.0 |

**Não houve controle corporal utilizável neste ensaio sem calibração de participante.** Os dados confirmam a leitura da fonte e o encadeamento de timestamps, não o alcance de gestos ou uma partida controlada com a cabeça.

## Chão isolado

Comparações locais de 80 quadros por bioma/renderizador, sem webcam. O primeiro comparador inclui a mudança de amostragem visual; o segundo compara apenas a otimização que preserva pixels. A igualdade RGB também é exercitada em 60 estados pelo teste de regressão.

Comparação com `d442c6c`: [dados do terreno](desempenho/terreno-versao-1.6.json).

| Bioma | Mediana anterior ms | Mediana atual ms | p95 anterior ms | p95 atual ms |
|---|---:|---:|---:|---:|
| amazonia | 3.583 | 5.632 | 5.065 | 9.79 |
| caatinga | 1.249 | 1.936 | 1.469 | 2.498 |

Comparação com `12dda71`: [dados do terreno](desempenho/terreno-antes-da-otimizacao.json).

| Bioma | Mediana anterior ms | Mediana atual ms | p95 anterior ms | p95 atual ms |
|---|---:|---:|---:|---:|
| amazonia | 5.742 | 5.503 | 9.023 | 10.792 |
| caatinga | 2.316 | 1.852 | 3.991 | 2.99 |

## Janela nativa com câmera concorrente

Três processos adicionais, janela visível, câmera inferindo em paralelo e entrada sintética, mesmos 600 quadros por caso e ritmo alvo de 60 FPS. Incluem apresentação da janela. Executados em série, sem testes ou builds locais concorrentes; aplicativos habituais continuam ativos. Não substituem o ensaio de gesto real e não apagam os picos observados anteriormente.

| Execução | Cena | Mediana ms | p95 ms | p99 ms | Máximo ms | Até 16,67 ms |
|---|---|---:|---:|---:|---:|---:|
| native-camera-1 | amazonia_normal | 14.835 | 22.753 | 24.88 | 30.792 | 64.00% |
| native-camera-1 | amazonia_contrast | 19.921 | 36.053 | 46.397 | 50.408 | 12.83% |
| native-camera-1 | caatinga_normal | 13.349 | 18.84 | 23.961 | 30.786 | 85.33% |
| native-camera-1 | caatinga_contrast | 18.808 | 33.272 | 56.509 | 96.352 | 26.83% |
| native-camera-2 | amazonia_normal | 13.526 | 20.629 | 29.174 | 86.252 | 84.00% |
| native-camera-2 | amazonia_contrast | 19.449 | 30.806 | 43.736 | 77.299 | 13.67% |
| native-camera-2 | caatinga_normal | 10.273 | 18.192 | 29.323 | 60.224 | 91.67% |
| native-camera-2 | caatinga_contrast | 16.176 | 28.079 | 43.613 | 177.291 | 55.17% |
| native-camera-3 | amazonia_normal | 15.422 | 24.787 | 26.527 | 29.225 | 59.67% |
| native-camera-3 | amazonia_contrast | 20.544 | 30.008 | 35.225 | 44.645 | 9.83% |
| native-camera-3 | caatinga_normal | 10.725 | 16.816 | 19.002 | 20.653 | 94.67% |
| native-camera-3 | caatinga_contrast | 15.373 | 23.821 | 26.196 | 27.937 | 61.17% |
