"""Dobramundo: exergame sério de voo com um avião de papel reciclado.

A criança pilota com o próprio corpo (pés, tronco, uma das mãos ou cabeça, pela
webcam) e, a cada voo, transforma uma cidade brasileira poluída em uma cidade
solarpunk integrada ao seu bioma.

Estrutura do pacote:
    content/  dados do jogo (biomas, aviões, resíduos, melhorias, textos)
    engine/   desenho pseudo-3D (projeção, sprites, céu, chão, cenário)
    game/     simulação do voo (mundo, avião, regras, estrelas)
    input/    teclado, mouse e controle corporal (MediaPipe Pose)
    ui/       tema, widgets e seleção por permanência
    scenes/   telas do jogo (abertura, vila, mapa, voo, resultado...)
"""

APP_NAME = "Dobramundo"
__version__ = "1.5.0"
