"""Constantes do motor: tela, projeção, voo, neblina, chão e paralaxe.

Unidades de mundo: x lateral (0 = centro da pista), y altura, z profundidade
(o avião fica em PLAYER_Z). Cerca de 28 unidades equivalem a 1 metro.
Conteúdo (biomas, aviões, resíduos, preços) fica em dobramundo/content/.
"""

from __future__ import annotations

import math

# ------------------------------------------------------------------ tela
WIDTH, HEIGHT = 1100, 650
FPS = 60
MAX_DT = 0.05
DT_SMOOTHING = 0.25  # suavização do passo de tempo (menos tremor no movimento)

# ------------------------------------------------------------- projeção
HORIZON_Y = 215
FOV = 360.0
CAMERA_HEIGHT = 155.0  # altura da câmera usada em project()
NEAR_CLIP_Z = 60.0  # sprites mais perto que isso não são desenhados
CAMERA_FOLLOW = 0.35  # fração do deslocamento lateral do avião que a câmera acompanha

# ---------------------------------------------------------------- pista
PLAYER_Z = 190.0
ROAD_WIDTH = 760.0
LANE_WIDTH = 220.0
SEGMENT_LENGTH = 100.0
TRACK_LENGTH = 2500.0  # profundidade da pista mantida à frente do avião

# ------------------------------------------------------------------ voo
BASE_SPEED = 340.0  # Difícil; o Normal voa à metade (antes 460: rápido demais para a criança)
RESTORATION_SPEED_GAIN = 0.3  # velocidade extra por ponto de transformação
DIFFICULTY_SPEED_GAIN = 30.0  # velocidade extra ao fim da rampa de dificuldade
DIFFICULTY_RAMP_S = 240.0  # segundos até a dificuldade máxima
MAX_LATERAL_SPEED = 620.0  # unidades/s para os lados
MAX_VERTICAL_SPEED = 420.0  # unidades/s para cima/baixo
FLIGHT_RESPONSE = 9.0  # quão rápido o avião responde aos comandos
MIN_ALTITUDE = 22.0
MAX_ALTITUDE = 155.0  # acima disso o avião ficaria sob o HUD
START_ALTITUDE = 60.0
MAX_PLAYER_X = LANE_WIDTH  # mantém o avião inteiro na tela
MAX_ROLL_DEG = 26.0
PLANE_WIDTH = 130.0  # envergadura visual/colisão (mundo)
PLANE_HEIGHT = 34.0
MAX_LIVES = 3
INVULNERABLE_S = 1.25
HIT_FLASH_S = 0.28

# ------------------------------------------------- transformação da cidade
ERA_SPAN = 100.0 / 3.0  # três estágios do mesmo tamanho (33,3% e 66,7%)
START_RESTORATION = 5.0
# Fase de ~3,5 min com a criança pegando 4 de cada 10 resíduos (ver tools/balance.py).
RESTORATION_PER_TRASH = 0.35  # Difícil
RESTORATION_COMBO_BONUS = 0.04  # com combo >= COMBO_BONUS_FROM
REPAIR_RESTORATION = 2.0  # reparo com vidas cheias
NORMAL_TRASH_EVERY = 4  # Normal: 1 resíduo a cada 4 do Difícil
NORMAL_TRASH_POINTS = 65  # pontos fixos por resíduo no Normal
NORMAL_SPEED_FACTOR = 0.5  # Normal: metade da velocidade-base
# Cada coleta do Normal é mais rara (1 em 4, à metade da velocidade) e rende bem mais:
# calibrado para a fase durar o mesmo que no Difícil (ver tools/balance.py).
NORMAL_RESTORATION_PER_TRASH = 2.24
HARD_TRASH_POINTS = 15  # Difícil: 15 x combo por resíduo
COMBO_WINDOW_S = 2.2
COMBO_STEP = 4  # a cada 4 coletas seguidas o combo sobe
MAX_COMBO = 8
COMBO_BONUS_FROM = 4  # combo a partir do qual cada coleta rende transformação extra
SHIELD_S = 6.0
MAGNET_S = 7.0
TRASH_HEIGHTS = (32.0, 88.0, 140.0)  # rasante, meia altura, alto

# Transição de cenário: o desenho segue a transformação aos poucos (constante de tempo).
VISUAL_RESTORATION_TIME = 2.8
GRASS_START_RESTORATION = ERA_SPAN  # início do estágio 2: chão verde e flora
GREEN_SWEEP_RESTORATION = 30.0  # parcela verde sobe de 0 a 100% ao longo disto
GREEN_CONVERT_Z = 1800.0  # trechos novos chegam transformados a partir daqui
GREEN_GROW_DISTANCE = 1000.0  # a peça antiga afunda e a nova cresce nesta distância
FINAL_START_RESTORATION = 2 * ERA_SPAN  # início do estágio 3 (cidade solarpunk)
FINAL_SWEEP_RESTORATION = 10.0
FINAL_GROW_DISTANCE = 900.0
ROAD_PURIFY_BAND = 300.0  # a pista passa de suja a limpa nesta profundidade

# -------------------------------------------------------------- neblina
FOG_START = 900.0
FOG_END = 2450.0
FOG_LEVELS = 10

# ----------------------------------------------------------- paralaxe
SKY_SHIFT_PX = 0.08
SKY_DRIFT_PX = 0.004
CLOUD_SHIFT_PX = 0.15
FAR_SHIFT_PX = 0.25
FAR_DRIFT_PX = 0.03
FAR_BACK_RATIO = 0.55
SKYLINE_HAZE = {"back": 0.72, "front": 0.5, "green": 0.45}
MID_PARALLAX = 0.5
MARGIN_PARALLAX = 0.8
MARGIN_X = 480.0  # fileira da borda (distância lateral do centro)
MID_ROW_X = 690.0  # fileira de fundo
MARGIN_MAX_Z = 1800.0  # a borda some na neblina além disso
RESTORED_EVERY = 6  # estágio 2: 1 trecho a cada 6 mostra um prédio restaurado
RESTORED_REMAINDER = 3
LANDMARK_EVERY = 9  # estágio 3: marco da cidade em 1 trecho a cada 9

# --------------------------------------------------------------- chão
GROUND_ROW_GROUP = 1.06  # linhas de escala parecida compartilham a mesma textura
GROUND_STRIP_MIN = 560  # largura mínima (px) das faixas de textura guardadas
GROUND_TILES = {
    "grass": (240.0, 120.0),
    "concrete": (400.0, 200.0),
    "meadow": (240.0, 120.0),
    "paver_road": (190.0, 190.0),
    "dry_soil": (260.0, 130.0),
    "agreste": (240.0, 120.0),
}
CONCRETE_JOINTS_X = (560.0, 860.0, 1200.0)  # juntas paralelas à pista
CONCRETE_JOINT_COLOR = (46, 42, 38)
GRASS_FALLBACK = ((74, 140, 52), (64, 128, 46))

# ----------------------------------------------------------------- céu
POLLUTION_CLEAR_START = 15.0
POLLUTION_CLEAR_END = 45.0
SKY_PANORAMA_SCALE = 1.4
SKYLINE_HEIGHT = 160
SKYLINE_CHUNK = 220
SKYLINE_BUDGET_MS = 1.5
SKYLINE_FADE_S = 0.6
CLOUD_TILE = 1900
FAR_TILE = 2 * 1100
FAR_STEP = 8
FAR_PROFILE = [
    26
    + 14 * abs(math.sin(2 * math.pi * 3 * (i * FAR_STEP) / FAR_TILE))
    + 10 * math.sin(2 * math.pi * 7 * (i * FAR_STEP) / FAR_TILE + 1.1)
    + 6 * math.sin(2 * math.pi * 13 * (i * FAR_STEP) / FAR_TILE + 0.4)
    for i in range(FAR_TILE // FAR_STEP)
]
DECOR_CYCLE = WIDTH + 700
BIRDS = 7

# ------------------------------------------------------------- caches
SPRITE_CACHE_LIMIT = 1400
PATTERN_TEXTURE_SIZE = 256
PATTERN_CACHE_LIMIT = 4

# ------------------------------------------------------------ efeitos
FINAL_HALO_SCALE = 2.1
FINAL_ALERT_DEPTH = (24.0, 96.0)
MANEUVER_MIN_THICKNESS = 0.28
MANEUVER_TOP_MARGIN = 70
