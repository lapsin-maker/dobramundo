# Arquitetura do Dobramundo

Este documento descreve o código do pacote `dobramundo/` como ele está no repositório. A visão de jogo está no GDD (`docs/GDD_Dobramundo_v10.pdf`), e o uso do projeto está no `README.md`.

## 1. Camadas

O pacote se divide em camadas com dependências em um sentido só: cada camada usa as de baixo, e nenhuma usa as de cima.

```
executável (app.py: App)       cartucho do T-TEA (cartridge.py: ConsoleCore, Dobramundo)
   plataformas: janela, relógio, eventos, tela cheia e, no console, o próprio console
          \                                /
           \                              /
   núcleo (core.py: GameCore, first_scene): jogo sem plataforma
                        |
scenes/ ........ telas do jogo (menus, calibração, voo, resultado)
   |
ui/ ............ tema (fontes e cartões de papel), botões e seleção por permanência
input/ ......... teclado, mouse e pontos do corpo (webcam em camera.py; console em console.py)
engine/ ........ desenho pseudo-3D: céu, chão, pista, objetos, avião, piloto, orientação, formas de papel
   |
game/ .......... regras do voo: mundo, avião, vidas, pontos, estrelas, momento de foco, eventos
   |
content/ ....... dados do jogo: fases, aviões, pinturas, resíduos, melhorias, textos
   |
config.py ...... constantes do motor (sem dependências)
```

Duas camadas não dependem do pygame: `content/` e `game/`. Isso permite testar as regras do voo e a progressão sem janela (os testes ainda usam drivers `dummy` para as cenas). `input/pose.py` também não importa o pygame nem o MediaPipe. Só `input/camera.py` importa o MediaPipe e o OpenCV, e apenas quando a câmera é ligada.

O `GameCore` (em `core.py`) reúne os serviços que as cenas usam: o perfil, a tela lógica, os sprites compartilhados (`assets`), o desenho (`view`), o som (`audio`), as entradas (`input`) e a cena atual. Ele não abre janela nem lê eventos do sistema: quem faz isso é a plataforma. O `App` (em `app.py`) é a plataforma do executável, e o `ConsoleCore` (em `cartridge.py`) é a do console. Os dois herdam do `GameCore`.

## 2. Um quadro

`App.run()` chama `App.step(dt)` a cada quadro, com o tempo suavizado (`DT_SMOOTHING`) e limitado a `MAX_DT`. No executável, `App.step` faz, nesta ordem:

1. `App.events()`: lê os eventos do pygame. Converte a posição do mouse para as coordenadas lógicas (desfazendo espelho e rotação), trata F11 e repassa os demais ao `InputHub`.
2. `GameCore.advance(dt, eventos)`, o mesmo núcleo em qualquer plataforma:
   1. `_switch()`: se houver uma cena pendente (`GameCore.go`), sai da atual (`leave`) e entra na nova (`enter`: toca a trilha e chama `build`).
   2. `input.update(dt)`: consome a leitura mais recente da câmera ou do console (`BodyControl.poll`).
   3. `view.update(dt)`: avança o tempo do desenho e as decorações do céu.
   4. `scene.handle_event` para cada evento, depois `scene.update(dt)` e `scene.draw(canvas)`.
   5. `view.step_warm_up(ms)`: prepara sprites em fatias de tempo. São 6 ms nas telas de menu e 1,5 ms no voo (`idle_warm_up`).
3. `present()`: copia a tela lógica (1100 x 650) para a janela, com espelho e rotação (`engine/orientation.py`). O SDL escala para a janela ou a tela cheia.

No console, o cartucho faz o papel de `events()` e de `present()` em `Dobramundo.update` e `Dobramundo.draw`: recebe os eventos e o rastreamento, passa-os ao núcleo e desenha o canvas na superfície do console.

Ao sair, `shutdown()` para o controle corporal e o som e grava o perfil.

### Quadro do voo

Dentro do passo 5, `FlightScene.update` chama `FlightRun.update` com o comando do quadro. A ordem é esta:

```
InputHub.flight_command()          (ix, iy, alvo): teclado e corpo; alvo só no controle por posição
  -> FlightRun.record_movement()   medida de movimento (só com controle corporal calibrado)
  -> FlightRun.update(dt, ix, iy, alvo)
       1. tempo real: real_dt = min(dt, MAX_DT); soma flight_time
       2. FocusMoment.update(real_dt, comando, aonde o avião vai)
            conta a janela da seta e o desvio guiado, detecta acerto ou erro
       3. escala de tempo: dt = real_dt * focus.time_scale
            1,0 normal; FOCUS_SLOW (0,12) com a seta; FOCUS_GUIDE_SLOW (0,45) no desvio guiado
       4. escudo, ímã, invulnerabilidade, flash e combo, com o dt do mundo
       5. avião: guide_point() com exact=True no desvio guiado;
          senão Player.update (posição: steer_to; velocidade: vx e vy)
       6. World.advance(dt, distância): trechos, objetos e abertura didática
       7. announce_lessons, check_collisions, count_passes, missions.update
  -> FlightScene.handle_run_events()   sons, banners, flash e tremor
```

Os relógios do momento de foco correm em tempo real (`real_dt`). Por isso a janela de 1,8 s ou 1,2 s dura o mesmo, por mais lento que o mundo esteja. Os demais sistemas do voo usam o `dt` do mundo, já escalado.

## 3. Máquina de cenas e fluxo de telas

Toda cena herda de `scenes/base.py:Scene`, que tem o menu com seleção por permanência e a barra de recursos. A troca de cena é sempre no fim do quadro, com `GameCore.go(scene)`.

Fluxo da execução (`core.first_scene`, usado pelo executável e pelo cartucho). A cadeia é montada de trás para frente, e cada tela de primeira vez só entra enquanto a condição do perfil não foi cumprida:

```
PilotScene (1ª vez: piloto_montado)  -> IntroScene (1ª vez: abertura_vista)
           -> ConsentScene (1ª vez: consentimento)
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
  Opções ............. OptionsScene -> IntroScene ("Ver a abertura"), CalibrationScene e
                       ProjectionScene ("Projeção e chão", só no executável)
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
| `lesson` | tipo da lição (`waste`, `low`, `gate`, `tower`) | Banner com a legenda de `texts.LESSONS` |
| `foco` | direção pedida (`up`, `down`, `left`, `right`) | Som `sfx_desvio_alerta`. A seta e a barra são desenhadas em `FlightScene.draw_focus` |
| `foco_ok` | direção | Som `sfx_desvio_ok`, legenda "Boa!" |
| `foco_quase` | direção | Som `sfx_desvio_quase`, legenda "Quase!" |

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

1. **Céu** (`SkyRenderer.draw`): degradê do céu; panorama do kit tingido pelo bioma (`tint_panorama`, com `polluted_haze`), com transparência conforme a poluição; sol de papel com halo (`draw_sun`); nuvens de fumaça e nuvens de papel recortado (`paper_cloud`) no céu limpo, com 12 níveis de transparência pré-calculados; silhuetas do horizonte em duas fileiras (fundo e frente), com a fileira de fundo misturando as silhuetas regionais (`industrial_skyline`), com paralaxe de 0,55 e 1,0 e transição de 0,6 segundo; decoração móvel (dirigível, balões e pássaros); e o barco (Amazônia) ou o bonde (Caatinga) na linha do horizonte. As silhuetas são montadas em faixas de 2 200 pixels, em pedaços que cabem em 1,5 ms por quadro.
2. **Neblina**: faixa de cor sólida abaixo da linha do horizonte.
3. **Chão** (`GroundRenderer.draw`): textura por faixas de linha. Linhas de escala parecida compartilham a mesma faixa reduzida. O chão é concreto no estágio industrial, solo do bioma no despertar e prado no solarpunk. Depois vêm as juntas das placas de concreto e a névoa final.
4. **Pista**: um polígono por trecho, do horizonte ao avião, com cor do estágio, neblina pela distância e variações: o rio da Amazônia (Rio Negro e encontro das águas), o piso drenante da Caatinga no estágio final e as faixas da pista.
5. **Margens** (`WorldView.margins`): a fileira de fundo fica em `MID_ROW_X` (paralaxe 0,5), e a borda, em `MARGIN_X` (paralaxe 0,8). O cenário é em quarteirões: a cada 6 trechos, 2 ficam vazios de cada lado, com o lado direito deslocado em 3 trechos. A borda alterna de lado a cada trecho, tem um vão a cada quatro pares de trechos e some depois de `MARGIN_MAX_Z`. No estágio industrial, `industrial_mid` intercala peças regionais às do kit. Em cada fileira, as peças cruzam o fade conforme a transformação do trecho, e a peça de um estágio afunda enquanto a do seguinte cresce.
6. **Objetos atrás do avião** (`z >= PLAYER_Z`), em ordem de profundidade.
7. **Avião** (`draw_player`): sombra, piscada depois de colisão, rotação pela inclinação, tremular de papel (`PAPER_FLUTTER_DEG`), nariz para cima ao subir (`PITCH_STRETCH`), manobras, escudo e ímã.
8. **Objetos à frente do avião**, com halos no solarpunk do Difícil e alertas de chão antes dos obstáculos que colidem.
9. **Feixes de coleta** e **textos flutuantes** ("+65", "ESCUDO").

`FlightScene.draw` desenha depois, por cima: o flash da colisão, a seta e a barra do momento de foco (`draw_focus`, com `focus_vignette` escurecendo as bordas), o HUD, os banners, a miniatura da câmera e a tela de pausa. O tremor da colisão (`HIT_SHAKE_S`) desloca só o cenário; o HUD fica parado. No alto contraste (`high_contrast`), tudo o que vem antes dos objetos é dessaturado (`desaturate`), e objetos e avião ganham contorno espesso.

**Papel e aquarela.** `engine/paper.py` desenha as formas de papel por código (`ink_polygon`, `blob`, `shadow`, `hill_points`, `ribbon`, `bezier`, `tree`, `person`, `wave_lines`, `smoke` e `sparkles`), usadas pela vila e pela abertura. Ao coletar, o `Beam` (em `game/entities.py`) leva a cor do resíduo, e `WorldView.splash` desenha o respingo de aquarela durante `SPLASH_S` (0,55 s, em `game/run.py`).

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
- `hair_<estilo>` e `hijab`: cinza. Recebem a cor do cabelo (no lenço, a cor do cabelo vira a cor do lenço). O estilo `raspado` não tem camada. Com o lenço, `skin_hijab` substitui `skin`, porque o lenço muda o recorte da pele.
- `glasses_<estilo>`, `acc_<estilo>`, `hearing`, `chair`: com cor fixa.

`PilotRenderer.compose` monta as camadas na ordem: pele, base, camisa, cabelo (ou lenço), aparelho auditivo, óculos, acessório e cadeira. Essa ordem resolve o que fica na frente. Depois, `ink_outline` põe um contorno de tinta na composição inteira, e o resultado fica em cache por aparência (`PilotRenderer.cache`). As opções, com as cores de pele, cabelo, roupa e os itens, ficam em `content/pilot.py`, e são validadas em `normalize_pilot`.

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
- **Versão 1.2:** `voos_fase` e `historico` entram no perfil sem mudar `SCHEMA_VERSION` (continua 1). Campos ausentes em perfis antigos recebem o valor padrão.
- **Versão 1.3:** a opção booleana `girar` vira `rotacao` (0, 90, 180 ou 270). Perfis com `girar` verdadeiro viram `rotacao = 180` (`persistence.py`). `SCHEMA_VERSION` continua 1, e campos novos, como `chao_pontos`, `alvo_frente` e `centralizar_sozinho`, recebem o valor padrão em perfis antigos.
- **Versão 1.4:** o campo `piloto_montado` entra no perfil. Perfis antigos recebem `False`, e a tela Piloto aparece na primeira execução. A permanência padrão passa a 2,0 s (faixa de 1,0 a 3,5 s, em `persistence.py`), mas perfis que já têm o campo mantêm o valor salvo. `SCHEMA_VERSION` continua 1.

## 10. Como adicionar um novo bioma

O exemplo abaixo usa um bioma chamado `cerrado`, com a sigla `CE_` para os sprites. Os passos seguem a ordem do código.

1. **Dados da fase** em `content/biomes.py`. Crie um `Biome(...)` com:
   - três `StageLook` (industrial, despertar e solarpunk), `polluted_haze` (cor da fumaça, que tinge o céu) e `river`;
   - `industrial_skyline` (silhuetas regionais do horizonte) e, no estágio industrial, `industrial_mid` e `industrial_margin`, sendo que `industrial_mid(regional)` intercala as peças regionais às do kit;
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

## 11. Controle por posição, momento de foco e abertura didática

**Controle por posição** (`input/hub.py`, `game/player.py`). `InputHub.flight_command` devolve o alvo do corpo (-1..1, 0 na postura calibrada) quando o controle corporal está calibrado (ou quando os pés estão sobre a projeção, com `FloorControl`), o modo é posição (`controle_posicao`, padrão) e nenhuma tecla de direção está apertada. Caso contrário, devolve a velocidade do teclado somada ao corpo. `Player.command_target` converte o alvo em um ponto da pista: o centro do eixo horizontal e, na vertical, `REST_ALTITUDE` como centro, com os limites `MIN_ALTITUDE` e `MAX_ALTITUDE`. `Player.steer_to` aproxima o avião desse ponto com `POSITION_RESPONSE` (5,0 por segundo, em `config.py`), limitado por `MAX_LATERAL_SPEED` e `MAX_VERTICAL_SPEED` vezes o fator do avião. `AxisMapper.hold_when_lost` (`input/pose.py`) mantém a última leitura quando a câmera perde o segmento, então o avião conserva o rumo. Esse flag é definido ao abrir a câmera e em `InputHub.configure`.

**Momento de foco** (`game/focus.py`). `FocusMoment` tem três estados: `None` (voo normal), `"pending"` (a seta espera o movimento) e `"success"` ou `"miss"` (legenda de 0,8 s). `find_threat` escolhe o obstáculo cujo contato com o avião acontece em `FOCUS_IMPACT_S` (0,3 a 0,75 s de mundo), que bateria no ponto atual e no ponto para onde o avião vai (`intended_point`). `choose_escape` escolhe a direção do desvio, com a tabela `PREFERRED` por tipo de obstáculo. `moved_towards` mede se o comando andou pelo menos `FOCUS_STEP` (0,3, na escala de -1 a 1) a partir do comando que havia quando a seta apareceu. Acertar cria um desvio guiado (`guide_point`, com `exact=True` no `Player.update`) até o ponto seguro, e o obstáculo recebe `dodged`. Errar só deixa o tempo voltar ao normal. Intervalo de `FOCUS_COOLDOWN_S` (9 s), com `FOCUS_FIRST_S` (5 s) no início. A abertura didática ignora o intervalo (`entity.lesson`). Não abre com `invincible`, invulnerabilidade ou escudo. A opção `momento_foco` desliga o recurso.

**Abertura didática** (`game/world.py`, `game/run.py`). `FlightRun` recebe `intro=True` quando o modo é Normal ou quando é o primeiro voo da fase (`Profile.voos_fase`). `World.plan_intro` converte os tempos de `INTRO_*` (em `config.py`) em posições da pista pela velocidade inicial. `intro_pattern` põe só resíduos até `INTRO_FIRST_WASTE_S`, e `spawn_lessons` põe cada obstáculo da lista `INTRO_LESSONS` na faixa do meio, com um resíduo na faixa certa. `in_intro` vale até `INTRO_END_S` (22 s). `announce_lessons` publica o evento `lesson` antes da chegada, e a cena mostra a legenda de `texts.LESSONS`.

## 12. Fontes de pontos, controles e orientação

**Fontes de pontos.** O `InputHub` usa uma fonte por vez, com a forma `snapshot()`, `error`, `start()` e `stop()`:

- Executável: `input/camera.py` (`PoseCameraSource`) lê a webcam numa thread e roda o MediaPipe Pose. A fonte é criada por `webcam_source()` em `input/hub.py`, e só esse módulo importa o MediaPipe e o OpenCV.
- Console: `input/console.py` (`TrackingSource`) recebe a cada quadro os 33 pontos do corpo, com o x espelhado (`body_points`), e a posição dos pés já projetada na imagem do jogo (`locate_floor`). O cartucho entrega esses dados em `Dobramundo.update`.

**BodyControl x FloorControl.** `InputHub.make_control` escolhe o controle de cada segmento:

- `BodyControl` (`input/pose.py`) é relativo. O `AxisMapper` calibra o repouso (2 segundos e pelo menos 15 leituras, em `CALIBRATION_SECONDS` e `MIN_SAMPLES`) e só aceita o repouso se o desvio mediano das leituras fica até metade do alcance do segmento (`settle`, `STILL_SHARE`). Com `recenter_after` (`RECENTER_S`, 3 s, em `input/hub.py`), uma ausência longa apaga o repouso, e ele se refaz quando o segmento volta e fica parado. Isso vale para cabeça, mãos e tronco, com "Centrar sozinho" ligado, e para os pés na câmera sem chão calibrado.
- `FloorControl` (subclasse de `BodyControl`, com `absolute = True`) é usado só com o segmento "pes" e um localizador de chão (`InputHub.set_floor`). O localizador converte os pontos na posição (0..1) da imagem do jogo, e o avião e o cursor vão até esse ponto. Não há repouso a calibrar, e, quando o pé some, o último ponto é mantido.

**Orientação da projeção.** `engine/orientation.py` espelha primeiro e gira depois, no sentido horário. `game_to_screen` e `screen_to_game` fazem a conversão de ida e de volta, com as faixas pretas da imagem em pé. `App.to_logical` usa `screen_to_game` para o mouse, e `App.present` aplica `orient` na janela. A calibração do chão (`input/floor.py`, `FloorMap`) é uma homografia entre a câmera e a imagem projetada, medida nos quatro alvos (`TARGETS`, a 15% das bordas). `FloorMap.locator` desfaz a orientação e sobe o ponto em `alvo_frente`. `App.floor_setup` devolve esse localizador com um token que muda com os pontos, a rotação, o espelho e o cursor à frente, para refazê-lo só quando preciso. No console, `ConsoleCore.floor_setup` usa o localizador do próprio console.

## Pontos de atenção

- Se o JSON do perfil estiver ilegível, `load_profile` guarda o arquivo como `dobramundo_perfil.corrompido.json` e recomeça com o perfil padrão (e a importação do protótipo).
- A abertura completa aparece só na primeira execução (`abertura_vista`); depois ela fica em Opções > "Ver a abertura".
- O mapa (`scenes/map.py`) tem posições fixas para duas fases; uma terceira fase pede reorganizar os botões.
- O `Dobramundo.spec` empacota as extensões `.png`, `.json`, `.ogg`, `.wav`, `.task`, `.ico`, `.ttf` e `.txt` de `assets/`; se uma fonte faltar, `theme.load_font` cai para `SysFont` e o visual do texto muda.
- `tools/stylize.py` sobrescreve os PNG de `assets/`; o git guarda os originais.

## Mudanças da versão 1.1

- **Registro de cenas** (`scenes/__init__.py`): as cenas trocam de tela pelo nome (`self.goto("vila")`, `self.fly(bioma)`), sem importar umas às outras; voltar para a vila é o `back()` padrão.
- **Metas curtas** (`game/missions.py`): `MissionTracker` sorteia uma meta por vez; o `FlightRun` conta coletas, power-ups e obstáculos que passam pelo avião sem acertá-lo (`Entity.hit` e `Entity.passed`) e publica o evento `mission`.
- **Câmera única** (`input/hub.py`): o `InputHub` mantém uma só fonte de câmera aberta; trocar de segmento só troca o `BodyControl`. A calibração conta tempo real (2 s), e `inverter_vertical` atende câmeras vistas de cima.
- **Caches**: todos usam `engine/cache.py:BoundedCache` (descarte gradual do mais antigo).
- **Desenho da pista**: `WorldView.track_palette`, `draw_road`, `draw_lanes` e `curbs`; o chão usa `GroundRenderer.row_texture` e `queue_rows`. O estágio solarpunk se chama `solar` em todo o código (`solar_since`, `segment_solar`).
- **FlightView** (Protocol em `engine/world_view.py`) documenta o que o desenho lê de um voo.
- **Robustez**: perfil inválido ganha cópia `.corrompido.json`; falha ao salvar aparece na vila; avisos vão para `dobramundo.log` (`log.py`); o self-test reprova com `status: falhou` e código 1.

## Mudanças da versão 1.2

- **Controle por posição**: `Player.steer_to` e `Player.command_target`; `InputHub.flight_command` e `position_control`; `AxisMapper.hold_when_lost` (`input/pose.py`); opção `controle_posicao` no perfil e em Opções.
- **Momento de foco**: `game/focus.py` (`FocusMoment`), constantes `FOCUS_*` em `config.py`, desenho em `FlightScene.draw_focus` e `focus_vignette`. Sons `sfx_desvio_alerta`, `sfx_desvio_ok` e `sfx_desvio_quase`, gerados por `tools/make_audio.py`. Eventos `foco`, `foco_ok` e `foco_quase`.
- **Abertura didática**: `World.plan_intro`, `spawn_lessons` e `intro_pattern`; `FlightRun.announce_lessons`; textos em `texts.LESSONS`; constantes `INTRO_*`; `Profile.voos_fase` decide a abertura no Difícil.
- **Sensação de voo**: `PAPER_FLUTTER_DEG` e `PITCH_STRETCH` em `WorldView.draw_player`; tremor da colisão com `HIT_SHAKE_S`.
- **Opção "Efeitos fortes (clarão, tremor)"** (`efeitos_fortes`): controla o clarão da colisão e da estrela, o tremor e o tom do momento de foco.
- **Medida de movimento e histórico**: `FlightRun.record_movement` e `FlightRun.summary`; `scenes/result.py` (`apply_run` e `movement_line`); `Profile.historico`, com até `HISTORY_LIMIT` (60) voos, gravado em `dobramundo_perfil.json`.
- **Equilíbrio**: `tools/balance.py` e `test_fase_dura_alguns_minutos` marcam a decisão de coleta no próprio objeto (antes usavam `id()`, que se repete quando objetos são liberados, e coletavam bem menos que 4 de cada 10). Recalibrados `RESTORATION_PER_TRASH` (0,115), `RESTORATION_COMBO_BONUS` (0,013), `NORMAL_RESTORATION_PER_TRASH` (1,18) e `COST_SCALE` (12).

## Mudanças da versão 1.3

- **Núcleo e plataformas:** `core.py` (`GameCore`, `first_scene`) é o jogo sem plataforma. `app.py` (`App`) é o executável, com `events()`, `present()`, `run()` e `to_logical()`. `cartridge.py` (`ConsoleCore`, `Dobramundo`) é o cartucho do console. `GameCore.advance` faz o quadro comum às duas plataformas. O registro de cenas (`scenes/__init__.py`) segue explícito, sem `importlib`.
- **Fontes de pontos:** a webcam com MediaPipe foi para `input/camera.py`. `input/console.py` traz os pontos do console. `input/pose.py` ficou com segmentos, calibração, eixos e `FloorControl`.
- **Chão e orientação:** `input/floor.py` (`FloorMap`), `engine/orientation.py` e `scenes/projection.py`. Opções `rotacao`, `espelhar`, `chao_pontos` e `alvo_frente`, com migração de `girar` em `persistence.py`.
- **Conforto:** `RECENTER_S` em `input/hub.py`, `AxisMapper.settle` (o repouso só vale com o segmento parado) e as opções `centralizar_sozinho` e `inverter_horizontal` ("Trocar lados").
- **Seleção:** `HOLD_MARGIN` (30 px) e `LEAVE_TOLERANCE` (0,5 s) em `ui/widgets.py`.
- **Cartucho:** `tools/build_cartridge.py` monta `build/cartucho/` sem `app.py`, `main.py`, `selftest.py`, `input/camera.py` e o modelo de pose, gera `CREDITOS.md` e roda `tsdk check` e `tsdk build`. `PLATFORM_KEYS` (ESC, P e F2) fica com o console, e `PLAYER_OPTIONS` define as opções que acompanham a criança registrada.

## Mudanças da versão 1.4

- **Fontes e cartões** (`ui/theme.py`): `FONT_FILES` carrega Fredoka (títulos e botões), Nunito (leitura) e Patrick Hand (legendas à mão, com `hand=True`) de `assets/fonts`, com `SysFont` como reserva. `panel` desenha cartões de papel com sombra (`SHADOW_OFFSET`), grão (`paper_grain`, de ruído fixo) e borda de tinta, em cache por tamanho e cor.
- **Filtro de papel** (`tools/stylize.py`): `stylize_image` aplica degraus de claridade, traço nas quebras internas, contorno de tinta azul-marinho e grão. `FOLDERS` lista as pastas de sprites, e `LIGHT_INK_FOLDERS` (aviões) recebe um traço mais fino e cinza-azulado. `tools/build_assets.py` aplica o filtro em cada sprite gerado, com `params_for`. As camadas do piloto não passam por ele.
- **Formas de papel** (`engine/paper.py`): desenho por código das formas de papel, usado pela vila e pela abertura (ver seção 6).
- **Vila em diorama** (`scenes/village.py`): `draw_ground` desenha morros (`HILLS`), rio, ponte, caminhos (`PATH_LEFT`, `PATH_RIGHT`) e o largo (`SQUARE`). `HOUSES` tem cinco casas que trocam de sprite industrial para solar em ordem, conforme o progresso. `SLOTS` posiciona as melhorias em três núcleos. `TREES` e `PEOPLE` dão a vida da cena, e `paper.smoke` e `paper.sparkles` variam com o progresso.
- **Céu** (`engine/sky.py`): `draw_sun`, `paper_cloud` e `tint_panorama`, que tinge o panorama com `polluted_haze` do bioma.
- **Fases** (`content/biomes.py`, `engine/world_view.py`): `industrial_mid` intercala peças regionais a cada duas do kit; `industrial_skyline` alimenta o horizonte (`skyline_base("back")`); `WorldView.margins` monta quarteirões com vãos; `Beam` tem cor, e `WorldView.splash` desenha o respingo.
- **Piloto** (`content/pilot.py`, `tools/lowpoly/pilot.py`, `engine/pilot.py`, `scenes/pilot.py`): proporções de criança, novas opções, contorno `ink_outline`, a tela com balão de fala, o botão "Surpresa!" e o campo `piloto_montado` no perfil.
- **Fluxo inicial** (`core.first_scene`): piloto, abertura, aviso, calibração e vila.
- **Abertura em páginas** (`scenes/intro.py`): `PAGES` define quatro páginas, com viradas de `TURN_S`; a dobradura usa `FOLD_STEPS` numa mesa de papel, e o rastro usa as cores de `TRAIL`, as da logo.
- **Voo, opções e padrões**: HUD mais fino em `scenes/flight.py`; `DEFAULT_PATTERN = "liso"` em `content/planes.py`; permanência padrão de 2,0 s, com faixa de 1,0 a 3,5 s em `persistence.py` e `scenes/options.py`.
