# Validação 1.7

Os ensaios usam perfis sintéticos separados dos dados do jogador. Referência local: Windows 11, Core i7-10750H, 32 GB, Python 3.12.10, pygame 2.6.1, desenho por CPU em 1100 × 650.

## Cobertura automatizada

- 578 testes de regras, cenas, persistência, câmera simulada e contratos portáteis em Python 3.8 e 3.12. [Execução de integração aprovada](https://github.com/lapsin-maker/dobramundo/actions/runs/40247641383); o manifesto da release identifica também a execução usada para os downloads.
- Self-test: 14 telas, dois voos de 1.200 quadros interativos (20 segundos simulados cada) e carregamento real do detector, sem abrir a webcam. [Resultado da fonte](self-test.json). Os executáveis têm relatórios próprios no manifesto da release.
- Cartucho: check/build do TSDK local e renderização do estágio isolado, sem procurar imagens no checkout: nove menus e dois voos com 900 passos, incluindo preparação. [Resultado](cartucho.json).
- 35 capturas finais sem falha de geometria dos botões; quatro referências de menus com diferença de pixels igual a zero. A checagem de botões não substitui a revisão humana dos textos. [Capturas](capturas.json), [comparação](regressao-visual.json).
- 12 sequências de emendas/mudanças de estágio e oito pares de obras antes/depois. Distâncias e mistura do horizonte e das margens são registradas no [manifesto visual](jornadas.json). O retorno do último ao primeiro quadro de um GIF é uma repetição do arquivo, não uma emenda do jogo.
- 108 voos sintéticos em três cenários parametrizados, dois modos e dois biomas. [Economia e transformação](economia.md).
- Alcance dos quatro extremos e alinhamento do marcador com as classes reais do TSDK instalado, em Python 3.14.8/pygame-ce 2.5.8. [Relatório do cursor](cursor-sdk.json). Usa coordenadas sintéticas, sem comprovar alcance físico de uma pessoa.

## Protocolo de desempenho

Processos novos, execução serial, avatar sintético idêntico, semente 7. Preparação e primeiro quadro interativo são separados. Tempos inclusivos e exclusivos são identificados; não some percentis de componentes aninhados.

O orçamento de superfícies derivadas é 192 MiB; ele não limita arte base, buffers ativos, bibliotecas nem RSS. Para esta configuração de referência, o teto experimental de acompanhamento é 768 MiB de RSS no ensaio de 30 ciclos. Isso não certifica um hardware mínimo nem garante desempenho em outro equipamento.

As comparações usam três execuções com e sem câmera, os dois biomas e alto contraste. Entradas frias têm processos independentes. O ensaio prolongado alterna aparências, cenas, biomas e contraste. A câmera em modo concorrente mede carga; o modo `--camera-control` registra a sequência realmente consumida e informa se ela era utilizável.

## Resultados e limites

[Desempenho completo, com dados brutos](desempenho.md): 30 ciclos de 2.400 quadros, 72 mil quadros ativos, sem falhas; RSS máximo de 617,1 MiB e final de 570,3 MiB, com cache derivado dentro de 192 MiB. A memória total não diminuiu em relação à medição histórica da 1.6; o resultado aqui é o limite explícito dos caches e a estabilidade no ensaio.

**O alvo de 60 FPS não passou em todas as condições.** Alto contraste e webcam ainda têm picos. Nas entradas frias, o p95 do primeiro quadro foi 72,8 ms na Amazônia e 45,1 ms na Caatinga; a meta proposta de 50 ms passou apenas na Caatinga. O preparo visível separa o trabalho pesado da fase interativa, mas não torna todas as operações indivisíveis menores que 1,5 ms.

A webcam foi aberta nos ensaios concorrentes e no ensaio de sequência consumida. Neste último não houve pose calibrada utilizável: isso valida o encadeamento dos timestamps, não uma partida comandada por uma criança. Nenhum relatório automatizado comprova conforto infantil ou resposta física gesto→projetor. Quatro superfícies, seis segmentos, leitura a 2–3 m, compreensão das recompensas e console instalado precisam do [roteiro presencial](../VALIDACAO_PRESENCIAL.md).
