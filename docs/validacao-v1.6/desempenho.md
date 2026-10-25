# Desempenho e câmera — versão 1.6

## Equipamento e condições

Intel Core i7-10750H (6 núcleos/12 threads), 32 GB RAM, Windows 11 build 26200, Python 3.12.10, pygame 2.6.1; render 1100×650 em CPU. Os relatórios foram coletados sem outros testes ou builds locais concorrentes. Aplicativos de uso normal não foram controlados. São observações deste equipamento e desta sessão, sem garantia de repetição ou de desempenho noutro computador.

Os cenários sem câmera usam SDL dummy, processo novo e 60 quadros de aquecimento por caso; alguns relatórios estão em estresse sem limite de quadros. As medições com câmera indicam alvo de 60 FPS e excluem o tempo de sleep das durações de quadro. Quantidade de quadros: 600 por cenário, exceto `runtime-camera-paced`, com 480.

## Inicialização e memória — comparação sem avatar

O baseline 1.5 foi extraído do commit `f80294b` para uma pasta isolada e executado com o mesmo Python da medição 1.6. O par (`baseline-current` e `runtime-seed7`) usa a semente 7, sem avatar. Inicialização fria, delta de RSS e maior RSS amostrado ao fim dos cenários (não o pico instantâneo do processo):

| Relatório | Startup frio | Delta RSS após inicialização | Pico RSS observado nos voos |
|---|---:|---:|---:|
| 1.5 baseline, `baseline-current` | 2.772 ms | 160,7 MiB | 532,1 MiB |
| 1.6, `runtime-seed7` | 1.084 ms | 87,2 MiB | 258,9 MiB |

Neste par, o RSS máximo observado caiu cerca de 51% e o delta inicial cerca de 46%. A inicialização reportada também foi menor. São resultados de duas execuções, não uma distribuição de repetições: não atribuir toda a diferença ao código nem generalizar para outros equipamentos. O primeiro quadro dos quatro casos variou de 10 a 671 ms no baseline e de 20 a 352 ms em `runtime-seed7`; o pico de primeiro quadro não é o startup frio.

## Duração dos quadros sem câmera

P95 e máximo em milissegundos. Valores maiores são quadros mais demorados.

| Caso | 1.5 baseline p95/máx | 1.6 sem avatar p95/máx |
|---|---:|---:|
| Amazônia, normal | 11,580 / 15,116 | 13,974 / 20,393 |
| Amazônia, alto contraste | 13,933 / 19,912 | 15,741 / 28,772 |
| Caatinga, normal | 7,705 / 10,476 | 9,917 / 12,688 |
| Caatinga, alto contraste | 12,515 / 16,512 | 12,570 / 16,275 |

O conjunto não mostra melhora geral do tempo de CPU por quadro; os dois casos da Amazônia e Caatinga normal tiveram p95 maior em 1.6. Em nova execução da semente 7 com avatar sintético e sem câmera, o p95/máximo foi 11,966/18,544 ms (Amazônia normal), 19,169/40,274 ms (Amazônia contraste), 10,351/14,958 ms (Caatinga normal) e 13,491/18,831 ms (Caatinga contraste). O avatar é uma carga específica, não um agregado de aparências.

## Câmera local e picos

No relatório final com avatar sintético e inferência de câmera em paralelo, p95/máximo por caso foi: Amazônia normal 18,050/41,875 ms; Amazônia contraste 17,541/22,050 ms; Caatinga normal 38,394/67,459 ms; Caatinga contraste 16,098/21,147 ms. Outros dois ensaios sem avatar, paced e recheck, registraram máximos de 55,321 ms e 18,071 ms, respectivamente, em Caatinga normal; o recheck chegou a 29,231 ms em Amazônia/contraste. Esses picos são preservados aqui e mostram que não há garantia de 60 FPS.

Os ensaios de câmera em paralelo reportaram 28,05–29,55 leituras e inferências por segundo, sem erros, falhas de leitura ou amostras descartadas por idade nesses arquivos. Isso descreve a captura/inferência observadas, não a resposta física do jogo. `camera-local.json` contém uma janela medida de 8,032 s após aquecimento de 5,781 s: 26,39 FPS de captura e 26,27 inferências/s; a última inferência durou 94 ms na resolução de relógio informada (15,625 ms). A idade de 1.172 ms do último resultado ocorreu após o encerramento da câmera; não é latência humana nem medida de reação do controle.

O benchmark consulta a idade do último resultado disponível logo após a chamada de apresentação. O render continua com entrada sintética enquanto o detector processa a webcam em paralelo; essa amostra não é necessariamente a leitura consumida pelo controle do jogo. A origem temporal é o retorno de `VideoCapture.read`, que **não** inclui buffering/exposição do sensor, emissão do projetor nem o instante em que a imagem é vista no chão. Não equivale a latência ponta a ponta. A métrica da calibração do jogo acompanha separadamente a leitura efetivamente consumida até o canvas pronto; os contratos de sequência/relógio são testados. `last_result_age` após `stop` também não é latência de movimento.

## Soak prolongado

O [soak de 30 ciclos](soak.json) concluiu sem falhas: 1.215,5 s simulados (20 min 15,5 s), em 758,138 s de parede. Foram 72.000 quadros de voo, além das visitas repetidas à vila, mapa, piloto, hangar e preparação. Alternou os dois biomas, contraste, cabelos, tons de pele, cadeira e andador; sem câmera e com invencibilidade apenas para manter a carga de render. O máximo foi 27 entidades vivas, abaixo do limite de diagnóstico de 300.

RSS amostrado ao final de cada ciclo: 419,5 MiB no primeiro, máximo 559,6 MiB, e 542,5 MiB no último. Houve aquecimento/acúmulo inicial de variantes; nos dez ciclos finais o intervalo foi 537,3–555,0 MiB, sem crescimento monotônico. O último inventário reteve aproximadamente 309 MiB estimados de superfícies (o cálculo conservador pode contar subsurfaces compartilhadas). Isso não prova ausência de todo vazamento nem limite de RAM no console. A carga prolongada com múltiplas aparências é diferente dos quatro voos curtos usados na comparação anterior.

## Relatórios JSON preservados

Os arquivos abaixo são cópias dos relatórios indicados; não incluem dados de perfil. Foi feita inspeção de strings para caminhos absolutos e não havia nenhum a remover.

- [baseline-current-runtime.json](baseline-current-runtime.json)
- [runtime-seed7-runtime.json](runtime-seed7-runtime.json)
- [runtime-avatar-runtime.json](runtime-avatar-runtime.json)
- [runtime-avatar-camera-runtime.json](runtime-avatar-camera-runtime.json)
- [runtime-camera-paced-runtime.json](runtime-camera-paced-runtime.json)
- [runtime-camera-recheck-runtime.json](runtime-camera-recheck-runtime.json)
- [camera-local.json](camera-local.json)
