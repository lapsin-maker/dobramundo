# Arquitetura do Dobramundo

Este documento descreve o código do pacote `dobramundo/` como ele está no repositório. A visão de jogo está no GDD (`docs/GDD_Dobramundo_v10.pdf`), e o uso do projeto está no `README.md`.

## 1. Camadas

O pacote se divide em camadas com dependências em um sentido só: cada camada usa as de baixo, e nenhuma usa as de cima.

```
scenes/ ........ telas do jogo (menus, calibração, voo, resultado)
   |
ui/ ............ tema, botões e seleção por permanência
input/ ......... teclado, mouse e controle corporal (MediaPipe Pose)
engine/ ........ desenho pseudo-3D: céu, chão, pista, objetos, avião, piloto
   |
game/ .......... regras do voo: mundo, avião, vidas, pontos, estrelas, eventos
   |
content/ ....... dados do jogo: fases, aviões, pinturas, resíduos, melhorias, textos
   |
config.py ...... constantes do motor (sem dependências)
```

Duas camadas não dependem do pygame: `content/` e `game/`. Isso permite testar as regras do voo e a progressão sem janela (os testes ainda usam drivers `dummy` para as cenas). `input/pose.py` também não importa o pygame, e o MediaPipe e o OpenCV são importados só quando a câmera é ligada.

O `App` (em `app.py`) reúne os serviços que as cenas usam: o perfil, a tela lógica, os sprites compartilhados (`assets`), o desenho (`view`), o som (`audio`), as entradas (`input`) e a cena atual.

## 2. Um quadro

`App.run()` chama `App.step(dt)` a cada quadro, com o tempo suavizado (`DT_SMOOTHING`) e limitado a `MAX_DT`. Cada `step` faz, nesta ordem:

1. `_switch()`: se houver uma cena pendente (`App.go`), sai da atual (`leave`) e entra na nova (`enter`: toca a trilha e chama `build`).
2. `events()`: lê os eventos do pygame. Converte a posição do mouse para as coordenadas lógicas (espelhar e girar), trata F11 e repassa os demais ao `InputHub`.
3. `input.update(dt)`: consome a leitura mais recente da câmera (`BodyControl.poll`).
4. `view.update(dt)`: avança o tempo do desenho e as decorações do céu.
5. `scene.handle_event` para cada evento, depois `scene.update(dt)` e `scene.draw(canvas)`.
6. `present()`: copia a tela lógica (1100 x 650) para a janela. O SDL escala para a janela ou a tela cheia, e espelhar e girar são aplicados aqui.
7. `view.step_warm_up(ms)`: prepara sprites em fatias de tempo. São 6 ms nas telas de menu e 1,5 ms no voo (`idle_warm_up`).

Ao sair, `shutdown()` para o controle corporal e o som e grava o perfil.

## 3. Máquina de cenas e fluxo de telas

Toda cena herda de `scenes/base.py:Scene`, que tem o menu com seleção por permanência e a barra de recursos. A troca de cena é sempre no fim do quadro, com `App.go(scene)`.

Fluxo da execução (`main.first_scene`). A cadeia é montada de trás para frente; a abertura só aparece na primeira vez:

```
IntroScene (1ª execução) -> ConsentScene (se o aviso ainda não foi aceito)
           -> CalibrationScene (se houver controle corporal)
           -> VillageScene
```

Fluxo a partir da vila:

```
VillageScene
  Decolar ............ MapScene -> [CalibrationScene, se o corpo não estiver calibrado] -> FlightScene
  Melhorias .......... UpgradesScene (abas Vila e Avião)
  Hangar ............. HangarScene (abas Dobradura, Cor e Padrão)
  Piloto ............. PilotScene
  Opções ............. OptionsScene -> IntroScene ("Ver a abertura") e CalibrationScene
  Sobre .............. AboutScene (O jogo, ODS, Créditos, Referências)
  Esc ................ OptionsScene

FlightScene
  Pausa (P, Esc ou automática) -> Continuar | Recalibrar -> CalibrationScene(return_to=FlightScene) | Voltar à vila
  Fim do voo ........ ResultScene

ResultScene
  Voar de novo / Tentar de novo -> flight_or_calibration -> FlightScene
  Voltar à vila ..... VillageScene
```

`flight_or_calibration` desvia para a calibração quando o controle corporal está ativo e ainda não foi calibrado. `CalibrationScene.enter` refaz a calibração ao entrar.

## 4. Eventos do voo

`FlightRun` (em `game/run.py`) não desenha nem lê o teclado. Ele recebe os eixos de controle a cada quadro, avança o mundo e publica eventos com `emit(nome, dado)`. A cena consome esses eventos com `take_events()` dentro de `FlightScene.handle_run_events`, e cada um vira som, trilha, banner ou efeito.

| Evento | Dado | Quem consome e faz o quê |
|---|---|---|
| `collect` | tipo do resíduo | Som de coleta do tipo (`Audio.collect`) |
| `powerup` | tipo do power-up | Som `sfx_powerup`. O avião faz a manobra do power-up |
| `shield_end` | nenhum | Som `sfx_escudo_fim` |
| `hit` | vidas restantes | Som `sfx_colisao` e flash vermelho na tela |
| `stage` | estágio (0, 1 ou 2) | Som `sfx_estagio`, troca de trilha e banner com o nome do estágio |
| `star` | número da estrela | Som `sfx_estrela`, flash e banner. Com 2 estrelas e sem as peças, avisa as peças que faltam |
| `complete` | estrelas | Som `sfx_fim_fase` e banner "cidade solarpunk" |
| `game_over` | estrelas | Som `sfx_game_over`. O voo termina e a cena vai para o resultado |

Ao fim do voo, `run.finished` vira verdadeiro (por game over ou por 3 segundos depois de 100%), e `FlightScene.update` abre o `ResultScene`. No resultado, `apply_run` leva recursos, pontos, estrelas e recorde ao perfil.

## 5. Transformação: do horizonte ao avião

O estado da cidade está em `World` (`game/world.py`), em dois valores:

- `restoration`: o valor real, de 0 a 100. Coletas e reparos o aumentam. Ele define a velocidade, o estágio da jogabilidade e as estrelas.
- `visual`: segue `restoration` com uma constante de tempo de 2,8 segundos (`ease_visual`). Ele define as cores, o céu, o chão e a pista.

O mundo é uma fila de trechos de 100 unidades (`segments`), que avançam em direção ao avião. Os trechos mais distantes ficam na neblina. Por isso a transformação começa lá:

- `_sweep` percorre os trechos com `z >= GREEN_CONVERT_Z` (1800 unidades) e marca, em `green_since` e `final_since`, a distância percorrida no momento em que cada trecho passa a se transformar. Só são marcados os trechos cuja posição na sequência (`green_rank` e `final_rank`, com sequências de Weyl) está abaixo da parcela da transformação. Isso espalha os trechos novos.
- `segment_green(seg)` e `segment_final(seg)` dão a parcela já crescida, com `smoothstep` ao longo de `GREEN_GROW_DISTANCE` (1000) e `FINAL_GROW_DISTANCE` (900) unidades percorridas. Assim a peça antiga afunda enquanto a nova cresce.
- `green_share()` e `final_share()` dão a parcela desejada pela transformação visual: a flora começa aos 33,3% e o estágio solarpunk, aos 66,7%.
- Objetos novos usam a tabela de obstáculos solarpunk quando o trecho deles já está transformado ou vai chegar lá (`spawn_is_final`).

Em `WorldView.draw_track`, a pista também se purifica em forma de onda (`wave_z`), que avança do horizonte para o avião conforme `visual` sobe. `set_restoration` aplica o estado final de uma vez e serve ao início da fase e aos testes.

## 6. Renderização em camadas

`WorldView` (em `engine/world_view.py`) desenha uma fase na ordem do fundo para a frente:

1. **Céu** (`SkyRenderer.draw`): degradê do céu; panorama do kit, com transparência conforme a poluição; nuvens de fumaça e nuvens limpas (12 níveis de transparência pré-calculados); silhuetas do horizonte em duas fileiras (fundo e frente), com paralaxe de 0,55 e 1,0 e transição de 0,6 segundo; decoração móvel (dirigível, balões e pássaros); e o barco (Amazônia) ou o bonde (Caatinga) na linha do horizonte. As silhuetas são montadas em faixas de 2 200 pixels, em pedaços que cabem em 1,5 ms por quadro.
2. **Neblina**: faixa de cor sólida abaixo da linha do horizonte.
3. **Chão** (`GroundRenderer.draw`): textura por faixas de linha. Linhas de escala parecida compartilham a mesma faixa reduzida. O chão é concreto no estágio industrial, solo do bioma no despertar e prado no solarpunk. Depois vêm as juntas das placas de concreto e a névoa final.
4. **Pista**: um polígono por trecho, do horizonte ao avião, com cor do estágio, neblina pela distância e variações: o rio da Amazônia (Rio Negro e encontro das águas), o piso drenante da Caatinga no estágio final e as faixas da pista.
5. **Margens** (`WorldView.margins`): duas fileiras por lado em cada trecho. A fileira de fundo fica em `MID_ROW_X` (paralaxe 0,5), e a borda, em `MARGIN_X` (paralaxe 0,8, alternando de lado a cada trecho). A cada fileira, as peças cruzam o fade conforme a transformação do trecho.
6. **Objetos atrás do avião** (`z >= PLAYER_Z`), em ordem de profundidade.
7. **Avião** (`draw_player`): sombra, piscada depois de colisão, rotação pela inclinação, manobras, escudo e ímã.
8. **Objetos à frente do avião**, com halos no solarpunk do Difícil e alertas de chão antes dos obstáculos que colidem.
9. **Feixes de coleta** e **textos flutuantes** ("+65", "ESCUDO").

`FlightScene.draw` desenha depois, por cima: o flash da colisão, o HUD, os banners, a miniatura da câmera e a tela de pausa. No alto contraste (`high_contrast`), tudo o que vem antes dos objetos é dessaturado (`desaturate`), e objetos e avião ganham contorno espesso.

A paralaxe usa `player.cam_x`, que segue `CAMERA_FOLLOW` (35%) do deslocamento lateral do avião. Cada camada anda uma fração diferente desse deslocamento (`SKY_SHIFT_PX`, `CLOUD_SHIFT_PX`, `FAR_SHIFT_PX`, `MID_PARALLAX`, `MARGIN_PARALLAX`).

## 7. Caches

O desenho é pesado, então cada tipo de dado tem um cache com limite.

| Cache | Onde | O que guarda e limite |
|---|---|---|
| `SpriteCache.scaled` | `engine/sprites.py` | Sprites reescalados, com neblina e contorno. Limite `SPRITE_CACHE_LIMIT` (1 400). Descarta o item inserido há mais tempo |
| `SpriteCache.mips` | `engine/sprites.py` | Versões reduzidas de cada sprite, a cada 1/1,5 do tamanho, até o menor lado chegar perto de 20 px |
| `WorldView.rotations`, `shadows` | `engine/world_view.py` | Avião girado e sombras. Limpa tudo ao passar de 400 |
| `WorldView.text_cache` | `engine/world_view.py` | Textos do HUD. Limpa tudo ao passar de 64 |
| `PlaneSkin.cache` | `engine/plane_skin.py` | Avião pintado e com piloto. 48 entradas |
| `PlaneSkin.palettes` | `engine/plane_skin.py` | Texturas de padrão como listas de pixels. `PATTERN_CACHE_LIMIT` (4) |
| `PlaneSkin.uv_indices` | `engine/plane_skin.py` | Índices do mapa UV por avião. 8 entradas |
| `PilotRenderer.cache` | `engine/pilot.py` | Piloto composto por aparência. 32 entradas |
| `SkyRenderer` | `engine/sky.py` | Degradês (24), decorações (64) e nuvens nos 12 níveis de transparência |
| `GroundRenderer.groups`, `fog_cache` | `engine/ground.py` | Faixas de textura por grupo de escala e a névoa do chão |
| `Text` | `ui/theme.py` | Superfícies de texto. Acima de 600, remove as 200 mais antigas |
| `panel` | `ui/theme.py` | Cartões, por tamanho e cor. Limpa tudo ao passar de 200 |
| `veil` | `ui/theme.py` | Véus de tela cheia, por tamanho e cor |
| `Scene.scaled` | `scenes/base.py` | Miniaturas dos menus, guardadas no `SpriteCache.scaled` |
| `brazil_map` | `scenes/map.py` | Mapa do Brasil, pintado uma vez |

`WorldView.warm_tasks` monta, em segundo plano e em fatias, os mips de cenário, obstáculos, resíduos e power-ups, além das silhuetas. Assim o voo não engasga na primeira vez que um sprite aparece.

## 8. Piloto em camadas e anchors.json

O piloto é composto por camadas PNG em `assets/pilot_layers/`, geradas por `tools/build_assets.py --pilot` (ver `tools/lowpoly/pilot.py`). Há duas vistas: `flight` (de trás, como no voo) e `menu` (3/4, como no hangar). Os nomes seguem `<vista>__<camada>.png`:

- `skin`, `shirt`: tons de cinza. Recebem a cor escolhida por multiplicação (`tinted`).
- `base`: calça, tênis e olhos, com cor fixa.
- `hair_<estilo>`: cinza. Recebe a cor do cabelo. O estilo `raspado` não tem camada.
- `glasses_<estilo>`, `acc_<estilo>`, `hearing`, `chair`: com cor fixa.

`PilotRenderer.compose` monta as camadas na ordem: pele, base, camisa, cabelo, aparelho auditivo, óculos, acessório e cadeira. Essa ordem resolve o que fica na frente.

`assets/pilot_layers/anchors.json` tem a ancoragem do piloto:

- `flight` e `menu`: para cada modelo de avião, a caixa `[x0, y0, x1, y1]` em pixels do sprite `<modelo>__none`, onde o piloto senta. Um `y0` negativo indica que o piloto passa do topo do sprite.
- `body`: para cada vista, a caixa do corpo na camada de referência, usada para escalar o piloto.

`PilotRenderer.mount` escala o corpo para a altura da caixa do avião (nunca menos de 27% da altura do avião, `MIN_PILOT_SHARE`) e alinha pelo centro da base. Sem as camadas ou sem a ancoragem, o avião aparece sem piloto.

A pintura do avião (`PlaneSkin.painted`) usa a camada `paint` de cada sprite. Ela é multiplicada pela cor escolhida ou pelo padrão vestido pelo mapa UV, em que o verde (G) é a linha e o vermelho (R) é a coluna da textura de 256 x 256 pixels.

## 9. Perfil versionado e migração

O perfil fica num único JSON (`dobramundo_perfil.json`) e é modelado pela dataclass `Profile` em `persistence.py`. Ele tem o campo `versao`, com `SCHEMA_VERSION = 1`.

- **Gravação:** `save_profile` escreve um arquivo temporário (`.tmp`) e troca pelo arquivo final, de forma atômica.
- **Leitura:** `Profile.from_dict` lê campo a campo, só aceita valores do tipo esperado e ignora campos desconhecidos. Depois `normalize()` limita valores (volumes, permanência, sensibilidade, estrelas, recursos) e descarta opções que não existem mais (aviões, padrões, segmentos, melhorias). Se algo falhar, o resultado é o perfil padrão.
- **Migração:** não há migração por versão. O campo `versao` é gravado, mas não é lido. Para uma mudança incompatível, é preciso aumentar `SCHEMA_VERSION`, criar o tratamento em `from_dict` e cobrir o caso em `tests/test_progress.py`.
- **Importação do protótipo:** se não houver perfil, `import_legacy` lê `eco_runner_recorde.json` e `eco_runner_config.json` das pastas do protótipo (ver `legacy_data_dirs` em `paths.py`).

## 10. Como adicionar um novo bioma

O exemplo abaixo usa um bioma chamado `cerrado`, com a sigla `CE_` para os sprites. Os passos seguem a ordem do código.

1. **Dados da fase** em `content/biomes.py`. Crie um `Biome(...)` com:
   - três `StageLook` (industrial, despertar e solarpunk), `polluted_haze` e `river`;
   - as listas de cenário (`industrial_mid`, `industrial_margin`, `green_mid`, `green_margin`, `restored`, `green_skyline`, `solar_mid`, `solar_margin`, `landmark`, `solar_skyline`), em pares (nome do sprite, altura no mundo);
   - as tabelas de obstáculos (`industrial_obstacles` e `solar_obstacles`), com `obstacle_table(...)` e as funções `low`, `gate` e `tower`;
   - `green_ground`, `solar_ground`, `solar_road`, `horizon_vehicle`, `sky_decor`, `map_point` (longitude e latitude), `required_parts` e `music` (prefixo das trilhas).
   Depois, acrescente o bioma em `BIOMES` e em `BIOME_ORDER`. A ordem define a cadeia de desbloqueio (`Profile.unlocked`).
2. **Mapa.** Em `content/biomes.py`, remova o bioma de `LOCKED_BIOMES` e acrescente a cor em `BIOME_MAP_COLORS`. Em `scenes/map.py`, acrescente um polígono em `REGIONS`, se quiser a região pintada. Atenção: `MapScene.build` tem posições fixas para duas fases (a segunda ocupa y de 204 a 296, e o botão de modo começa em y = 330). Uma terceira fase exige reorganizar essas posições.
3. **Textos.** Em `content/texts.py`, acrescente uma tupla em `BIOME_FACTS[key]`, usada na tela de resultado.
4. **Sprites.** Crie os PNG em `assets/biome_sprites/` (ou em outra pasta listada em `SCENERY_FOLDERS`, em `engine/assets.py`). Os nomes são únicos, porque todas as pastas de cenário formam um só espaço de nomes.
5. **Gerador dos sprites.** Crie `tools/lowpoly/models_cerrado.py` com os modelos registrados por `@model("CE_Nome", "biome_sprites", ...)`. Importe o módulo em `tools/build_assets.py`, que hoje importa só `models_amazonia`, `models_caatinga` e `models_common`. Depois rode `python tools/build_assets.py --prefix CE_`.
6. **Texturas de chão.** Coloque os PNG em `assets/ground/`. Se o tamanho do ladrilho for diferente do padrão, registre-o em `GROUND_TILES` (`config.py`).
7. **Trilhas.** Em `tools/make_audio.py`, crie a composição (hoje há `compor_amazonia` e `compor_caatinga`) e as entradas `musica_cerrado_1.ogg` a `musica_cerrado_3.ogg`. Rode `python tools/make_audio.py --only musica`. A troca de estágio em voo usa `musica_<music>_<estágio+1>`.
8. **Colisões.** Rode `python tools/measure_obstacles.py`, que percorre `BIOMES` automaticamente, e ajuste `low`, `gate` e `tower` conforme a saída.
9. **Testes.** `tests/test_assets.py` já testa todas as fases pelo nome (`parametrize` sobre `BIOMES`). Rode `python -m pytest` e `python -m dobramundo --self-test 240`. O self-test também percorre `BIOME_ORDER` automaticamente.

## Pontos de atenção

- Se o JSON do perfil estiver ilegível, `load_profile` guarda o arquivo como `dobramundo_perfil.corrompido.json` e recomeça com o perfil padrão (e a importação do protótipo).
- A abertura completa aparece só na primeira execução (`abertura_vista`); depois ela fica em Opções > "Ver a abertura".
- O mapa (`scenes/map.py`) tem posições fixas para duas fases; uma terceira fase pede reorganizar os botões.

## Mudanças da versão 1.1

- **Registro de cenas** (`scenes/__init__.py`): as cenas trocam de tela pelo nome (`self.goto("vila")`, `self.fly(bioma)`), sem importar umas às outras; voltar para a vila é o `back()` padrão.
- **Metas curtas** (`game/missions.py`): `MissionTracker` sorteia uma meta por vez; o `FlightRun` conta coletas, power-ups e obstáculos que passam pelo avião sem acertá-lo (`Entity.hit` e `Entity.passed`) e publica o evento `mission`.
- **Câmera única** (`input/hub.py`): o `InputHub` mantém uma só fonte de câmera aberta; trocar de segmento só troca o `BodyControl`. A calibração conta tempo real (2 s), e `inverter_vertical` atende câmeras vistas de cima.
- **Caches**: todos usam `engine/cache.py:BoundedCache` (descarte gradual do mais antigo).
- **Desenho da pista**: `WorldView.track_palette`, `draw_road`, `draw_lanes` e `curbs`; o chão usa `GroundRenderer.row_texture` e `queue_rows`. O estágio solarpunk se chama `solar` em todo o código (`solar_since`, `segment_solar`).
- **FlightView** (Protocol em `engine/world_view.py`) documenta o que o desenho lê de um voo.
- **Robustez**: perfil inválido ganha cópia `.corrompido.json`; falha ao salvar aparece na vila; avisos vão para `dobramundo.log` (`log.py`); o self-test reprova com `status: falhou` e código 1.
