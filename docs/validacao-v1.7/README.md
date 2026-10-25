# Validação 1.7

Os ensaios usam perfis sintéticos separados dos dados do jogador. Referência local: Windows 11, Core i7-10750H, 32 GB, Python 3.12.10, pygame 2.6.1, desenho por CPU em 1100 × 650.

## Cobertura automatizada

- Testes de regras, cenas, persistência, câmera simulada e contratos portáteis em Python 3.8 e 3.12 no CI.
- Self-test de fonte e executáveis: 14 telas, dois voos de 1.200 quadros interativos e carregamento real do detector, sem abrir a webcam.
- Cartucho: check/build do TSDK local e renderização do estágio isolado, sem procurar imagens no checkout.
- Quatro referências de menus comparadas no CI; galeria com abertura, resultados, estágios e obras. Sequências de emenda e de mistura de estágios têm distâncias registradas.

## Protocolo de desempenho

Processos novos, execução serial, avatar sintético idêntico, semente 7. Preparação e primeiro quadro interativo são separados. Tempos inclusivos e exclusivos são identificados; não some percentis de componentes aninhados.

O orçamento de superfícies derivadas é 192 MiB; ele não limita arte base, buffers ativos, bibliotecas nem RSS. Para esta configuração de referência, o teto experimental de acompanhamento é 768 MiB de RSS no ensaio de 30 ciclos. Isso não certifica um hardware mínimo nem garante desempenho em outro equipamento.

As comparações usam três execuções com e sem câmera, os dois biomas e alto contraste. Entradas frias têm processos independentes. O ensaio prolongado alterna aparências, cenas, biomas e contraste. A câmera em modo concorrente mede carga; o modo `--camera-control` registra a sequência realmente consumida e informa se ela era utilizável.

## Limites

Nenhum relatório automatizado comprova conforto infantil ou resposta física gesto→projetor. Câmera física, quatro superfícies, seis segmentos, compreensão das recompensas e console instalado precisam do [roteiro presencial](../VALIDACAO_PRESENCIAL.md). Os arquivos de números e a síntese da release são acrescentados ao fechar as medições.
