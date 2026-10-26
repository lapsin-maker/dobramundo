# Desempenho e estabilidade — 1.7

Windows 11, Core i7-10750H, 32 GB, Python 3.12.10, pygame 2.6.1, CPU, 1100 × 650. Três processos novos por condição, avatar personalizado idêntico, semente 7, 60 quadros interativos de aquecimento e 600 medidos por caso. Medições refeitas após os ajustes de alcance, recuperação ativa e margens industriais. Execução serial, sem builds ou suítes locais concorrentes. O computador manteve seus aplicativos habituais; portanto a medição inclui a competição por CPU no desktop. Não é uma máquina de laboratório isolada, e a variação entre processos faz parte do resultado.

A preparação não entra no tempo do quadro interativo. Sem câmera, a execução é sem limite de frequência; com câmera, mira 60 FPS e exclui a espera do tempo medido. Não some percentis dos componentes inclusivos: cada JSON também contém custos exclusivos.

| Execução | Cena | Mediana ms | p95 ms | p99 ms | Máximo ms | Até 16,67 ms |
|---|---|---:|---:|---:|---:|---:|
| runtime-1 | amazonia_normal | 11.15 | 15.089 | 17.465 | 19.599 | 98.33% |
| runtime-1 | amazonia_contrast | 15.189 | 20.917 | 25.132 | 29.055 | 69.67% |
| runtime-1 | caatinga_normal | 7.849 | 14.579 | 24.948 | 39.558 | 96.50% |
| runtime-1 | caatinga_contrast | 11.53 | 17.481 | 25.002 | 32.637 | 94.00% |
| runtime-2 | amazonia_normal | 14.465 | 21.691 | 26.103 | 36.097 | 72.83% |
| runtime-2 | amazonia_contrast | 15.63 | 21.795 | 27.26 | 32.726 | 64.83% |
| runtime-2 | caatinga_normal | 8.078 | 11.243 | 13.332 | 15.364 | 100.00% |
| runtime-2 | caatinga_contrast | 11.76 | 17.078 | 21.837 | 23.648 | 94.00% |
| runtime-3 | amazonia_normal | 10.715 | 14.484 | 17.585 | 19.843 | 98.33% |
| runtime-3 | amazonia_contrast | 15.077 | 21.42 | 27.148 | 29.448 | 74.17% |
| runtime-3 | caatinga_normal | 8.319 | 13.518 | 18.252 | 22.565 | 97.83% |
| runtime-3 | caatinga_contrast | 11.887 | 16.821 | 20.296 | 23.143 | 94.50% |
| camera-1 | amazonia_normal | 12.388 | 66.005 | 76.503 | 95.86 | 86.83% |
| camera-1 | amazonia_contrast | 16.648 | 23.478 | 27.972 | 34.959 | 50.67% |
| camera-1 | caatinga_normal | 8.489 | 12.108 | 14.718 | 16.975 | 99.67% |
| camera-1 | caatinga_contrast | 13.368 | 21.393 | 28.951 | 37.464 | 82.50% |
| camera-2 | amazonia_normal | 11.873 | 16.942 | 20.409 | 28.37 | 94.50% |
| camera-2 | amazonia_contrast | 17.257 | 24.374 | 28.807 | 32.675 | 41.17% |
| camera-2 | caatinga_normal | 8.472 | 12.334 | 14.844 | 19.343 | 99.83% |
| camera-2 | caatinga_contrast | 12.837 | 19.288 | 22.663 | 30.026 | 87.50% |
| camera-3 | amazonia_normal | 13.657 | 22.142 | 28.967 | 54.418 | 75.17% |
| camera-3 | amazonia_contrast | 20.289 | 35.619 | 43.943 | 67.191 | 21.67% |
| camera-3 | caatinga_normal | 9.255 | 13.561 | 16.48 | 20.091 | 99.17% |
| camera-3 | caatinga_contrast | 14.22 | 19.863 | 23.287 | 38.689 | 79.67% |

**A meta de p95 até 16,67 ms não foi atingida em todas as condições.** Os resultados não sustentam promessa de 60 FPS constantes neste computador sob esta carga. A otimização de geometria do chão preserva pixels; a suavização introduzida nesta versão tem custo próprio e não deve ser confundida com uma redução universal do custo frente à versão 1.6.

## Entradas frias

| Bioma | Mediana do primeiro quadro ms | p95 ms | Máximo ms | Mediana do preparo ms | Maior tarefa indivisível ms |
|---|---:|---:|---:|---:|---:|
| amazonia | 36.825 | 48.601 | 48.601 | 548.177 | 87.643 |
| caatinga | 31.868 | 38.382 | 38.382 | 505.510 | 83.134 |

O orçamento cooperativo é conferido entre tarefas. A decodificação de uma imagem é indivisível e pode ultrapassá-lo; por isso sua duração é publicada. O voo não consome vidas nem a contagem de primeiras sessões enquanto prepara o cenário.

## Uso prolongado

30 ciclos × 2.400 quadros, 1200.0 s de voo simulado ativo; 832.694 s de parede. Preparação e menus são separados. Trocas de bioma, aparência e contraste, sem webcam. Sem falhas de ciclo ou crescimento descontrolado de entidades.

RSS final 571.7 MiB; máximo 607.0 MiB; últimos dez ciclos entre 558.3 e 607.0 MiB. Cache derivado máximo 191.9 MiB, sob orçamento de 192 MiB. Teto experimental de RSS: 768 MiB. Um ensaio sem crescimento contínuo não prova ausência de todo vazamento.

## Sequência realmente consumida

Ensaio adicional em janela nativa com controle de cabeça, 300 quadros por caso. Estado da fonte: `ok`. Resolução do relógio monotônico deste host: 15.625 ms. Cada JSON informa sequências distintas, fração utilizável e tempos da mesma amostra até canvas/apresentação. Ausência de pose/calibração utilizável não equivale a controle corporal aprovado. Não foram salvos vídeo ou landmarks.

A medição começa no retorno da captura, não na exposição do sensor, e termina na chamada de apresentação, não na luz emitida pelo projetor. Extremos confortáveis, perda/retorno, seis segmentos e projeção exigem o roteiro presencial.

| Cena | Sequências distintas | Quadros utilizáveis | Captura→apresentação p95 ms |
|---|---:|---:|---:|
| amazonia_normal | 156 | 0/300 | 79.0 |
| amazonia_contrast | 177 | 0/300 | 79.0 |
| caatinga_normal | 153 | 0/300 | 78.0 |
| caatinga_contrast | 160 | 0/300 | 93.0 |

**Não houve controle corporal utilizável neste ensaio sem calibração de participante.** Os dados confirmam a leitura da fonte e o encadeamento de timestamps, não o alcance de gestos ou uma partida controlada com a cabeça.

## Chão isolado

Comparações locais de 80 quadros por bioma/renderizador, sem webcam. O primeiro comparador inclui a mudança de amostragem visual; o segundo compara a implementação anterior à otimização de geometria. Este microbenchmark isola o chão: não mede as novas estruturas das margens nem o voo completo.

Comparação com `d442c6c`: [dados do terreno](desempenho/terreno-versao-1.6.json).

| Bioma | Mediana anterior ms | Mediana atual ms | p95 anterior ms | p95 atual ms |
|---|---:|---:|---:|---:|
| amazonia | 4.085 | 5.659 | 6.067 | 8.754 |
| caatinga | 1.407 | 2.296 | 1.974 | 3.362 |

Comparação com `12dda71`: [dados do terreno](desempenho/terreno-antes-da-otimizacao.json).

| Bioma | Mediana anterior ms | Mediana atual ms | p95 anterior ms | p95 atual ms |
|---|---:|---:|---:|---:|
| amazonia | 7.915 | 7.223 | 12.153 | 11.175 |
| caatinga | 2.587 | 2.367 | 4.161 | 3.56 |

## Janela nativa com câmera concorrente

Três processos adicionais, janela visível, câmera inferindo em paralelo e entrada sintética, mesmos 600 quadros por caso e ritmo alvo de 60 FPS. Incluem apresentação da janela. Executados em série, sem testes ou builds locais concorrentes; aplicativos habituais continuam ativos. Não substituem o ensaio de gesto real e não apagam os picos observados anteriormente.

| Execução | Cena | Mediana ms | p95 ms | p99 ms | Máximo ms | Até 16,67 ms |
|---|---|---:|---:|---:|---:|---:|
| native-camera-1 | amazonia_normal | 14.124 | 19.117 | 22.017 | 27.875 | 83.00% |
| native-camera-1 | amazonia_contrast | 18.884 | 25.081 | 27.624 | 28.824 | 17.17% |
| native-camera-1 | caatinga_normal | 11.643 | 18.675 | 20.647 | 24.894 | 88.83% |
| native-camera-1 | caatinga_contrast | 16.643 | 23.418 | 26.614 | 29.424 | 50.50% |
| native-camera-2 | amazonia_normal | 16.97 | 22.677 | 25.766 | 47.737 | 45.17% |
| native-camera-2 | amazonia_contrast | 19.855 | 26.386 | 30.126 | 32.295 | 10.33% |
| native-camera-2 | caatinga_normal | 11.136 | 15.872 | 18.709 | 20.261 | 97.00% |
| native-camera-2 | caatinga_contrast | 16.856 | 24.531 | 27.326 | 29.288 | 47.83% |
| native-camera-3 | amazonia_normal | 14.167 | 19.399 | 22.415 | 25.55 | 80.33% |
| native-camera-3 | amazonia_contrast | 19.268 | 28.387 | 34.409 | 47.571 | 17.50% |
| native-camera-3 | caatinga_normal | 10.342 | 39.92 | 52.708 | 64.441 | 83.67% |
| native-camera-3 | caatinga_contrast | 12.928 | 18.256 | 21.271 | 27.267 | 90.83% |
