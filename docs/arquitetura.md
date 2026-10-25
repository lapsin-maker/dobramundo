# Arquitetura do Dobramundo

Este documento descreve o código do pacote `dobramundo/` como ele está no repositório. A visão de jogo está no GDD (`docs/GDD_Dobramundo_v10.pdf`), e o uso do projeto está no `README.md`.

## Estado atual — versão 1.7

O perfil e as migrações estão em `profile_model.py`; `persistence.py` cuida do armazenamento, rejeita revisões antigas e preserva arquivos de versões futuras. No desktop, `instance_lock.py` impede duas instâncias de usar o mesmo diretório de dados. O console conserva a persistência fornecida pelo SDK.

`game/settlement.py` concentra a liquidação idempotente. `FlightScene` só inicia a sessão depois do preparo e `ResultScene` aplica os efeitos ao entrar ou fechar, sem gravação no construtor. `transformacao_cidades` preserva o maior progresso de cada bioma. Uma nova decolagem restaura vidas e velocidade inicial; não restaura posição ou entidades do voo anterior. O fluxo inicial consulta `abertura_vista` e apresenta o jornal pulável após a montagem do piloto.

`scenes/flight_hud.py` contém a apresentação do voo. `RenderContext` explicita as entradas da composição de fundo. As superfícies derivadas compartilham um orçamento de 192 MiB em `engine/cache.py`; arte base, buffers ativos e RSS são medidos separadamente. O preparo inclui mipmaps do terreno e a aparência selecionada. A geometria invariável das linhas do chão é reutilizada, e cada linha de saída tem sua própria amostra de textura.

`InputFrame` acompanha a mesma sequência consumida até o canvas e a apresentação desktop. Essa telemetria não mede o atraso físico do sensor ou do projetor. `tools/runtime_assets.py` fornece o inventário comum dos pacotes, com uma variante por imagem utilizada. Os protocolos e resultados atuais estão em [validação 1.7](validacao-v1.7/README.md); as seções de versões anteriores abaixo registram a evolução e devem ser lidas junto destas mudanças.

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
ConsentScene (quando necessário) -> CalibrationScene (controle corporal)
           -> DwellPracticeScene -> PilotScene (se piloto_montado=False)
           -> VillageScene
```

Fluxo a partir da vila:

```
VillageScene
  Decolar ............ MapScene -> [CalibrationScene, se necessária] -> [TutorialScene, se tutorial_visto=False] -> FlightScene
  Melhorias .......... UpgradesScene (abas Vila e Avião)
  Hangar ............. HangarScene (abas Dobradura, Cor e Padrão)
  Piloto ............. PilotScene
  Opções ............. OptionsScene -> IntroScene, CalibrationScene, DwellPracticeScene,
                       PreparationScene e ProjectionScene (só no executável)
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

Ao fim do voo, `run.finished` vira verdadeiro (por game over, limite ou 3 segundos depois do primeiro cruzamento de 100%), e `FlightScene.update` abre o `ResultScene`. `game/settlement.py` leva recursos, transformação, pontos, estrelas e recorde ao perfil de modo idempotente. O construtor da tela não grava: seus efeitos ficam em `enter` e no hook de fechamento. O HUD fica em `scenes/flight_hud.py`; ele não decide recompensas.

## 5. Transformação: do horizonte ao avião

O estado da cidade está em `World` (`game/world.py`), em dois valores:

- `restoration`: o valor real da cidade, de 0 a 100. Coletas e reparos o aumentam; ele define o estágio e as estrelas. Ao liquidar o voo, o perfil guarda o máximo já atingido por cidade. A velocidade usa `FlightRun.local_restoration`, reiniciado em cada partida, para não penalizar a criança por ter transformado a cidade.
- `visual`: segue `restoration` com uma constante de tempo de 2,8 segundos (`ease_visual`). Ele define as cores, o céu, o chão e a pista.

O mundo é uma fila de trechos de 100 unidades (`segments`), que avançam em direção ao avião. Os trechos mais distantes ficam na neblina. Por isso a transformação começa lá:

- `_sweep` percorre os trechos com `z >= GREEN_CONVERT_Z` (1800 unidades) e marca, em `green_since` e `final_since`, a distância percorrida no momento em que cada trecho passa a se transformar. Só são marcados os trechos cuja posição na sequência (`green_rank` e `final_rank`, com sequências de Weyl) está abaixo da parcela da transformação. Isso espalha os trechos novos.
- `segment_green(seg)` e `segment_final(seg)` dão a parcela já crescida, com `smoothstep` ao longo de `GREEN_GROW_DISTANCE` (1000) e `FINAL_GROW_DISTANCE` (900) unidades percorridas. Assim a peça antiga afunda enquanto a nova cresce.
- `green_share()` e `final_share()` dão a parcela desejada pela transformação visual: a flora começa aos 33,3% e o estágio solarpunk, aos 66,7%.
- Objetos novos usam a tabela de obstáculos solarpunk quando o trecho deles já está transformado ou vai chegar lá (`spawn_is_final`).

Em `WorldView.draw_track`, a pista também se purifica em forma de onda (`wave_z`), que avança do horizonte para o avião conforme `visual` sobe. `set_restoration` aplica o estado final de uma vez e serve ao início da fase e aos testes.

## 6. Renderização em camadas

Na prévia aquarelada, `WorldView.background` usa `WatercolorWorld` para o horizonte e `PaintedRoute` para o percurso. `PaintedGround` projeta texturas de água/solo por faixas de três pixels, com buffers reutilizados e coordenada vertical derivada de `world.distance`. `PaintedRoute.placements` mantém margens ancoradas no mundo e usa a mesma função `project` das entidades. Reduzir movimento remove efeitos decorativos e diminui a densidade das margens, mas conserva o avanço. Se faltarem terrenos ou células válidas do atlas, o motor prepara e usa o cenário procedural completo.

Objetos interativos usam `PaperItems`, que separa resíduos circulares, benefícios hexagonais e obstáculos pintados. Depois entram avião/piloto, objetos em primeiro plano, efeitos e HUD. A cenografia não participa da colisão.

O caminho procedural de reserva de `WorldView` segue esta ordem:

1. **Céu** (`SkyRenderer.draw`): degradê do céu; panorama do kit tingido pelo bioma (`tint_panorama`, com `polluted_haze`), com transparência conforme a poluição; sol de papel com halo (`draw_sun`); nuvens de fumaça e nuvens de papel recortado (`paper_cloud`) no céu limpo, com 12 níveis de transparência pré-calculados; silhuetas do horizonte em duas fileiras (fundo e frente), com a fileira de fundo misturando as silhuetas regionais (`industrial_skyline`), com paralaxe de 0,55 e 1,0 e transição de 0,6 segundo; decoração móvel (dirigível, balões e pássaros); e o barco (Amazônia) ou o bonde (Caatinga) na linha do horizonte. As silhuetas são montadas em faixas de 2 200 pixels, em pedaços que cabem em 1,5 ms por quadro.
2. **Neblina**: faixa de cor sólida abaixo da linha do horizonte.
3. **Chão** (`GroundRenderer.draw`): textura por faixas de linha. Linhas de escala parecida compartilham a mesma faixa reduzida. O chão é concreto no estágio industrial, solo do bioma no despertar e prado no solarpunk. Depois vêm as juntas das placas de concreto e a névoa final.
4. **Pista**: um polígono por trecho, do horizonte ao avião, com cor do estágio, neblina pela distância e variações: o rio da Amazônia (Rio Negro e encontro das águas), o piso drenante da Caatinga no estágio final e as faixas da pista.
5. **Margens** (`WorldView.margins`): a fileira de fundo fica em `MID_ROW_X` (paralaxe 0,5), e a borda, em `MARGIN_X` (paralaxe 0,8). O cenário é em quarteirões: a cada 6 trechos, 2 ficam vazios de cada lado, com o lado direito deslocado em 3 trechos. A borda alterna de lado a cada trecho, tem um vão a cada quatro pares de trechos e some depois de `MARGIN_MAX_Z`. No estágio industrial, `industrial_mid` intercala peças regionais às do kit. Em cada fileira, as peças cruzam o fade conforme a transformação do trecho, e a peça de um estágio afunda enquanto a do seguinte cresce.
6. **Objetos atrás do avião** (`z >= PLAYER_Z`), em ordem de profundidade.
7. **Avião** (`draw_player`): sombra, piscada depois de colisão, rotação pela inclinação, tremular de papel (`PAPER_FLUTTER_DEG`), nariz para cima ao subir (`PITCH_STRETCH`), manobras, escudo e ímã.
8. **Objetos à frente do avião**, com halos no solarpunk do Difícil e alertas de chão antes dos obstáculos que colidem.
9. **Feixes de coleta** e **textos flutuantes** ("+65", "ESCUDO").

`FlightScene.draw` desenha depois, por cima: o flash da colisão, a seta e a barra do momento de foco (`draw_focus`, com `focus_vignette` escurecendo as bordas), o HUD, os banners, a miniatura da câmera e a tela de pausa. O tremor da colisão (`HIT_SHAKE_S`) desloca só o cenário; o HUD fica parado. No alto contraste (`high_contrast`), o fundo é dessaturado (`desaturate`), objetos/avião ganham contorno e o canvas do mundo recebe zoom uniforme de `contrast_scale` (1 a 1,6×). Setas externas usam `screen_point`; HUD conserva o tamanho nativo.

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

`WorldView.warm_tasks` cria uma fila de tarefas nomeadas sem executá-las. O caminho aquarelado prepara apenas seus fundos, terreno, células de margem e detalhes regionais; o caminho procedural prepara seus próprios sprites. O voo mostra a prontidão e aguarda a fila antes de atualizar regras. O orçamento é conferido entre tarefas, não interrompe uma tarefa individual; tempos e estouros ficam expostos para medição, sem prometer um limite rígido de 1,5 ms.

## 8. Piloto em camadas e anchors.json

`PilotRenderer.compose` prefere `PaintedPilot`: base RGBA com quatro poses, máscaras de pele/camisa/olhos, cabelo frontal/traseiro e dispositivos assistivos pintados. `pose='back_seated'` permite sentar no cockpit sem mudar a escolha de mobilidade do perfil. O resultado é cacheado por vista, pose e aparência. Se faltar a base pintada, usa `paper_pilot.draw_pilot`. As opções ficam em `content/pilot.py` e passam por `normalize_pilot`.

`PaintedPlanes` lê os 11 aviões em atlas de voo/hangar, recorta alfa, aplica cor e estampa sobre o papel claro e monta o piloto proporcionalmente. Em voo, só a parte superior do piloto aparece sobre a dobra. Os anchors antigos são usados no fallback de avião, não nos atlases novos.

O kit legado em `assets/pilot_layers/` permanece no pacote e é gerado por `tools/build_assets.py --pilot` (ver `tools/lowpoly/pilot.py`). Seus nomes seguem `<vista>__<camada>.png`:

- `skin`, `shirt`: tons de cinza. Recebem a cor escolhida por multiplicação (`tinted`).
- `base`: calça, tênis e olhos, com cor fixa.
- `hair_<estilo>` e `hijab`: cinza. Recebem a cor do cabelo (no lenço, a cor do cabelo vira a cor do lenço). O estilo `raspado` não tem camada. Com o lenço, `skin_hijab` substitui `skin`, porque o lenço muda o recorte da pele.
- `glasses_<estilo>`, `acc_<estilo>`, `hearing`, `chair`: com cor fixa.

Essas camadas documentam o formato anterior e continuam disponíveis para compatibilidade de conteúdo.

`assets/pilot_layers/anchors.json` tem a ancoragem do piloto:

- `flight` e `menu`: para cada modelo de avião, a caixa `[x0, y0, x1, y1]` em pixels do sprite `<modelo>__none`, onde o piloto senta. Um `y0` negativo indica que o piloto passa do topo do sprite.
- `body`: para cada vista, a caixa do corpo na camada de referência, usada para escalar o piloto.

No fallback, `PilotRenderer.mount` escala o corpo para a caixa do avião (com o mínimo `MIN_PILOT_SHARE`) e alinha pelo centro da base. Sem piloto ou ancoragem, devolve o avião sem composição adicional.

A pintura legada do avião usa a camada `paint` e seu mapa UV, em que o verde (G) é a linha e o vermelho (R) é a coluna da textura de 256 x 256 pixels. A rota preferida da sprint usa a máscara de papel de `PaintedPlanes`.

## 9. Perfis, persistência e migração

`Profile`, `Options`, validação e migração ficam em `profile_model.py`, reexportados por `persistence.py` para manter os imports existentes. O arquivo JSON legado (`dobramundo_perfil.json`) continua como slot `principal`. No desktop, um índice (`profiles.json`) registra até oito slots e os demais arquivos ficam em `profiles/`; cada slot contém progresso, personalização, opções e consentimento. Os cartões são anônimos (“Piloto 1” etc.) e a prévia não ativa nem regrava o slot. O console T-TEA continua usando o armazenamento por jogador do SDK, sem substituí-lo por perfis desktop.

O esquema 2 acrescenta `transformacao_cidades` e `apoio_escolhido`. Migrações são explícitas, repetíveis e nunca rebaixam versões futuras. A leitura desktop guarda a revisão esperada do arquivo; uma gravação de snapshot antigo falha em vez de apagar mudanças posteriores. `instance_lock.py` protege todo o diretório do desktop por lock do sistema operacional, inclusive índice e backups; encerramento inesperado libera o lock. Esse módulo não entra no cartucho.

- **Gravação:** arquivo temporário, flush/fsync e substituição atômica. Antes de substituir um perfil ou índice válido, rotaciona até duas cópias `.bak`/`.bak.1` validadas. O limite é recuperação de arquivo: não é journal nem checkpoint de execução.
- **Leitura e recuperação:** valida tipos e normaliza faixas; arquivo ausente ou inválido tenta cópias anteriores. Índices recuperáveis podem restaurar slots órfãos válidos sem ativá-los automaticamente. Arquivo corrompido é preservado com sufixo `.corrompido`; erro de leitura bloqueia gravação ao slot na sessão para evitar sobrescrever dados que não foram lidos.
- **Falha de recuperação:** se a cópia íntegra só puder ser aberta em memória, o jogo apresenta aviso e não afirma que a restauração em disco ocorreu. A interface permite reconhecer o aviso; falhas de gravação no perfil ativo precisam ser resolvidas antes de trocar de piloto.
- **Compatibilidade:** `SCHEMA_VERSION` permanece 1; campos opcionais novos recebem padrões e perfis antigos seguem legíveis. Para uma mudança incompatível, aumentar versão, adicionar migração explícita e cobrir o legado em testes. A opção antiga `girar` continua migrada para `rotacao`.
- **Opções de sessão:** limites 0/120/180/240 segundos, exploração, assistência previsível e semente comunitária são validados antes do uso. A semente `0` escolhe uma rota aleatória por voo; o resultado registra a semente efetiva para replay.
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

**Controle por posição** (`input/hub.py`, `game/player.py`). `InputHub.flight_command` devolve o alvo do corpo (-1..1, 0 na postura calibrada) quando o controle corporal está calibrado (ou quando os pés estão sobre a projeção, com `FloorControl`), o modo é posição (`controle_posicao`, padrão) e nenhuma tecla de direção está apertada. Caso contrário, devolve a velocidade do teclado somada ao corpo. `Player.command_target` converte o alvo em um ponto da pista: o centro do eixo horizontal e, na vertical, `REST_ALTITUDE` como centro, com os limites `MIN_ALTITUDE` e `MAX_ALTITUDE`. `Player.steer_to` aproxima o avião desse ponto com `POSITION_RESPONSE` (5,0 por segundo, em `config.py`), limitado por `MAX_LATERAL_SPEED` e `MAX_VERTICAL_SPEED` vezes o fator do avião. `AxisMapper.hold_when_lost` pode conservar internamente a última leitura em modo de posição, mas `InputHub.flight_command` só entrega alvos de leituras válidas. Na perda do segmento, retorna velocidade zero e nenhum alvo novo; a leitura antiga não vira velocidade contínua. O cursor corporal retorna `None`, suspendendo escolhas.

**Momento de foco** (`game/focus.py`). `FocusMoment` tem três estados: `None` (voo normal), `"pending"` (a seta espera o movimento) e `"success"` ou `"miss"` (legenda de 0,8 s). `find_threat` escolhe o obstáculo cujo contato com o avião acontece em `FOCUS_IMPACT_S` (0,3 a 0,75 s de mundo), que bateria no ponto atual e no ponto para onde o avião vai (`intended_point`). `choose_escape` escolhe a direção do desvio, com a tabela `PREFERRED` por tipo de obstáculo. `moved_towards` mede se o comando andou pelo menos `FOCUS_STEP` (0,3, na escala de -1 a 1) a partir do comando que havia quando a seta apareceu. Acertar cria um desvio guiado (`guide_point`, com `exact=True` no `Player.update`) até o ponto seguro, e o obstáculo recebe `dodged`. Errar só deixa o tempo voltar ao normal. Intervalo de `FOCUS_COOLDOWN_S` (9 s), com `FOCUS_FIRST_S` (5 s) no início. A abertura didática ignora o intervalo (`entity.lesson`). Não abre com `invincible`, invulnerabilidade ou escudo. A opção `momento_foco` desliga o recurso.

**Abertura didática** (`game/world.py`, `game/run.py`). `FlightRun` recebe `intro=True` quando o modo é Normal ou quando é o primeiro voo da fase (`Profile.voos_fase`). `World.plan_intro` converte os tempos de `INTRO_*` (em `config.py`) em posições da pista pela velocidade inicial. `intro_pattern` põe só resíduos até `INTRO_FIRST_WASTE_S`, e `spawn_lessons` põe cada obstáculo da lista `INTRO_LESSONS` na faixa do meio, com um resíduo na faixa certa. `in_intro` vale até `INTRO_END_S` (22 s). `announce_lessons` publica o evento `lesson` antes da chegada, e a cena mostra a legenda de `texts.LESSONS`.

## 12. Fontes de pontos, controles e orientação

**Fontes de pontos.** O `InputHub` usa uma fonte por vez, com a forma `snapshot()`, `error`, `start()` e `stop()`:

- Executável: `input/camera.py` (`PoseCameraSource`) lê a webcam numa thread e roda o MediaPipe Pose. A fonte é criada por `webcam_source()` em `input/hub.py`, e só esse módulo importa o MediaPipe e o OpenCV.
- Console: `input/console.py` (`TrackingSource`) recebe a cada quadro os 33 pontos do corpo, com o x espelhado (`body_points`), e a posição dos pés já projetada na imagem do jogo (`locate_floor`). O cartucho entrega esses dados em `Dobramundo.update`.

**BodyControl x FloorControl.** `InputHub.make_control` escolhe o controle de cada segmento:

- `BodyControl` (`input/pose.py`) é relativo. O `AxisMapper` calibra o repouso (2 segundos e pelo menos 15 leituras, em `CALIBRATION_SECONDS` e `MIN_SAMPLES`) e só aceita o repouso se o desvio mediano das leituras fica até metade do alcance do segmento (`settle`, `STILL_SHARE`). Com `recenter_after` (`RECENTER_S`, 3 s, em `input/hub.py`), uma ausência longa apaga o repouso, e ele se refaz quando o segmento volta e fica parado. Isso vale para cabeça, mãos e tronco, com "Centrar sozinho" ligado, e para os pés na câmera sem chão calibrado.
- `FloorControl` (subclasse de `BodyControl`, com `absolute = True`) é usado só com o segmento "pes" e um localizador de chão (`InputHub.set_floor`). O localizador converte os pontos na posição (0..1) da imagem do jogo, e o avião e o cursor vão até esse ponto. Não há repouso a calibrar. O último ponto pode permanecer no localizador, mas, quando o pé some, a camada de entrada invalida o cursor e deixa de enviar alvos ao voo.

**Orientação da projeção.** `engine/orientation.py` espelha primeiro e gira depois, no sentido horário. `game_to_screen` e `screen_to_game` fazem a conversão de ida e de volta, com as faixas pretas da imagem em pé. `App.to_logical` usa `screen_to_game` para o mouse, e `App.present` aplica `orient` na janela. A calibração do chão (`input/floor.py`, `FloorMap`) é uma homografia entre a câmera e a imagem projetada, medida nos quatro alvos (`TARGETS`, a 15% das bordas). `FloorMap.locator` desfaz a orientação e sobe o ponto em `alvo_frente`. `App.floor_setup` devolve esse localizador com um token que muda com os pontos, a rotação, o espelho e o cursor à frente, para refazê-lo só quando preciso. No console, `ConsoleCore.floor_setup` usa o localizador do próprio console.

## Pontos de atenção

- Se o JSON do perfil estiver ilegível, `load_profile` guarda o arquivo como `dobramundo_perfil.corrompido.json` e recomeça com o perfil padrão (e a importação do protótipo).
- A história aparece após o piloto enquanto `abertura_vista` for falso, com Pular, e pode ser revista em Opções. O treino de primeiro voo usa `tutorial_visto`, que só é marcado ao concluir/pular; voltar ao mapa mantém o treino pendente.
- O mapa (`scenes/map.py`) tem posições fixas para duas fases; uma terceira fase pede reorganizar os botões.
- `Dobramundo.spec` e `build_cartridge.py` compartilham `tools/runtime_assets.py`: inventário de execução que verifica hashes e escolhe a variante preparada ou o original, sem duplicá-los. Fontes/licenças são preservadas; se uma fonte faltar, `theme.load_font` cai para `SysFont` e o visual muda.
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

## Mudanças da sprint aquarelada

`engine/painted_route.py` projeta terreno e margens usando a distância do mundo; `engine/watercolor.py` compõe o horizonte e escolhe o cenário procedural de reserva quando o pacote está incompleto. O piloto usa `engine/painted_pilot.py`, os aviões usam `engine/painted_planes.py`, e `engine/pilot.py` integra o personagem às vistas. As camadas low-poly e `engine/paper_pilot.py` permanecem para compatibilidade e fallback.

`engine/village_art.py`, `scenes/village.py` e `scenes/upgrades.py` compõem a vila em três estágios e mostram a instalação das obras. `scenes/tutorial.py` oferece treino opcional no primeiro voo e pode ser reaberto por Opções. A abertura narrativa é opcional. Implementação, capturas e validação anteriores: [DIRECAO_AQUARELA.md](historico/DIRECAO_AQUARELA.md) e [ENTREGA_SPRINT2.md](historico/ENTREGA_SPRINT2.md).

## Sprint 3: controle, legibilidade e vida

O fluxo de primeira execução prepara aviso/calibração, oferece treino opcional de permanência, abre o piloto neutro e segue para a vila. `ui/widgets.py` conserva a trava do alvo ativado por chave/região após reconstruções do editor. Tempo de personalização e ampliação de contraste são campos próprios do perfil e acompanham o jogador registrado no console.

`input/pose.py` usa nariz e orelhas compensadas para cabeça, rejeita leituras envelhecidas e permite alcances direcionais calibrados em sessão. O cursor sem leitura retorna `None`; eixos antigos não alimentam a velocidade do voo. `engine/accessible_view.py` aplica zoom uniforme do mundo; `screen_point` mantém setas e tutorial alinhados com a imagem ampliada, sem alterar a física. O fundo de alto contraste é atenuado em baixa resolução antes dos objetos interativos.

`engine/painted_route.py` dissolve as formas das margens entre estágios, mantendo posição/distância. `engine/regional_life.py` desenha fauna decorativa atenuada perto de desafios, sem criar entidades. `engine/pilot.py` cacheia expressões. `scenes/village.py` mantém pedidos por obra e encena usos cotidianos. `audio.py` reserva dois canais de efeitos e prioriza uma fanfarra por vez. Os detalhes da implementação e o aceite presencial restante estão em [SPRINT3.md](historico/SPRINT3.md).

## Histórico — versão 1.4

Os itens abaixo registram a implementação anterior à sprint aquarelada. Os fluxos e renderizadores atuais estão descritos nas seções anteriores.

- **Fontes e cartões** (`ui/theme.py`): `FONT_FILES` carrega Fredoka (títulos e botões), Nunito (leitura) e Patrick Hand (legendas à mão, com `hand=True`) de `assets/fonts`, com `SysFont` como reserva. `panel` desenha cartões de papel com sombra (`SHADOW_OFFSET`), grão (`paper_grain`, de ruído fixo) e borda de tinta, em cache por tamanho e cor.
- **Filtro de papel** (`tools/stylize.py`): `stylize_image` aplica degraus de claridade, traço nas quebras internas, contorno de tinta azul-marinho e grão. `FOLDERS` lista as pastas de sprites, e `LIGHT_INK_FOLDERS` (aviões) recebe um traço mais fino e cinza-azulado. `tools/build_assets.py` aplica o filtro em cada sprite gerado, com `params_for`. As camadas do piloto não passam por ele.
- **Formas de papel** (`engine/paper.py`): desenho por código das formas de papel, usado pela vila e pela abertura (ver seção 6).
- **Vila em diorama** (`scenes/village.py`): `draw_ground` desenha morros (`HILLS`), rio, ponte, caminhos (`PATH_LEFT`, `PATH_RIGHT`) e o largo (`SQUARE`). `HOUSES` tem cinco casas que trocam de sprite industrial para solar em ordem, conforme o progresso. `SLOTS` posiciona as melhorias em três núcleos. `TREES` e `PEOPLE` dão a vida da cena, e `paper.smoke` e `paper.sparkles` variam com o progresso.
- **Céu** (`engine/sky.py`): `draw_sun`, `paper_cloud` e `tint_panorama`, que tinge o panorama com `polluted_haze` do bioma.
- **Fases** (`content/biomes.py`, `engine/world_view.py`): `industrial_mid` intercala peças regionais a cada duas do kit; `industrial_skyline` alimenta o horizonte (`skyline_base("back")`); `WorldView.margins` monta quarteirões com vãos; `Beam` tem cor, e `WorldView.splash` desenha o respingo.
- **Piloto** (`content/pilot.py`, `tools/lowpoly/pilot.py`, `engine/pilot.py`, `scenes/pilot.py`): proporções de criança, novas opções, contorno `ink_outline`, a tela com balão de fala, o botão "Surpresa!" e o campo `piloto_montado` no perfil.
- **Fluxo inicial** (`core.first_scene`): aviso, calibração quando necessária, piloto, abertura pulável e vila; etapas já concluídas são omitidas.
- **Abertura em páginas** (`scenes/intro.py`): `PAGES` define quatro páginas, com viradas de `TURN_S`; a dobradura usa `FOLD_STEPS` numa mesa de papel, e o rastro usa as cores de `TRAIL`, as da logo.
- **Voo, opções e padrões**: HUD mais fino em `scenes/flight.py`; `DEFAULT_PATTERN = "liso"` em `content/planes.py`; permanência padrão de 2,0 s, com faixa de 1,0 a 3,5 s em `persistence.py` e `scenes/options.py`.


## Entrega 1.6 — sessão e recuperação

`GameCore.create_scene` fornece a fachada da fábrica de cenas, com implementação padrão e injeção opcional usada em testes. `App` e `ConsoleCore` preservam argumentos existentes e aceitam fábrica ao final da assinatura.

`FlightRun` encerra por conclusão, colisão final, limite escolhido ou pedido de encerramento. `scenes/result.py` liquida recursos, pontos e histórico de modo idempotente por instância; encerramentos parciais não criam conclusão ou estrela. Sementes efetivas e opções selecionadas permitem abrir novamente o mesmo desafio. Isso não recupera processo encerrado à força antes de uma gravação.

`MissionTracker` consulta alvos existentes antes de oferecer meta e espera uma nova oferta quando não há suprimento; desafios comunitários têm sementes publicadas e temas associados. Exploração evita eliminação, mas colisões continuam contando. Assistência previsível altera ajuda de forma fixa durante o voo; não é uma garantia de adequação individual.

`WorldView` delega chão, entidades e avião a `track_layer.py`, `entity_layer.py` e `plane_layer.py`, ligados por Protocols somente de leitura em `contracts.py`; a camada de render não importa os módulos de simulação. `set_biome` descarta o cache específico do bioma anterior. O código gerado/preparado mantém fallback procedural quando o asset preparado não está disponível.

## Entrega 1.5 — confiabilidade e orçamento de recursos (histórico)

`PaintedPilot` solicita apenas suas camadas, sem decodificar cenários. O loader detecta fundos completamente opacos uma vez e conserva alfa em sprites com transparência. `WatercolorWorld` compõe apenas o horizonte visível quando o terreno cobre o restante; o fallback segue integral. `PaintedGround` usa faixas de 3 pixels e uma passagem de solo na Caatinga. Alto contraste reutiliza seus buffers; o conteúdo continua atualizado a cada desenho.

`GameCore.advance` desconta o tempo já gasto antes de iniciar aquecimento e reserva 2 ms para apresentação. O orçamento é cooperativo: uma tarefa indivisível ainda pode exceder a folga, portanto o benchmark deve registrar picos.

`Scene.settle_on_close` permite finalizar efeitos no fechamento normal. O voo só liquida após ter iniciado; `FlightRun.settlement` impede crédito duplicado na mesma execução, e o resultado usa o mesmo caminho para voos completos e parciais. Não é um checkpoint de recuperação de processo interrompido à força. Falha de save oferece retry no resultado.

A câmera desktop mantém a fonte enquanto ela encerra, permite reabertura posterior e expõe métricas sem imagens. Metadados de idade usam relógio monotônico desde o retorno da captura; o console conserva sua fonte própria. A entrada rejeita leituras antigas; perda breve impede colisões antes da pausa automática.

`BodyControl.reading_captured_at` pertence à sequência efetivamente consumida. Após `Scene.draw`, o núcleo chama `InputHub.note_rendered` para registrar captura→canvas pronto; a calibração mostra a última amostra concluída. Isso não mede exposição do sensor, apresentação física ou envio ao monitor. Fontes legadas/console sem timestamp exibem valor indisponível. Erro da webcam pausa imediatamente; retomada exige dados visíveis, calibração e tempo de presença, ou seleção explícita do teclado.

`RoutePlanner` conserva a fronteira de posições seguras em coordenadas absolutas. A origem nasce no reset e inclui as lições; não é reiniciada a cada novo obstáculo. Grupos que se sobrepõem no eixo de profundidade exigem manter uma mesma posição durante toda a janela de colisão. O deslocamento permitido usa o menor limite entre posição exponencial saturada e aceleração por velocidade, 75% da velocidade comum, velocidade máxima da pista e margens de 0,35 s de reação e 0,15 s de reversão. O passo de posição é calibrado para `MAX_DT`. É um modelo conservador discreto, não prova de conforto individual. A auditoria completa fica em `tools/check_routes.py`, fora do laço de desenho. O respawn desloca entidades existentes antes de inserir as novas, mantendo `distance + z` coerente com o planejador.

`plane_stats` entrega o mesmo conforto independentemente das peças. Os campos/níveis existentes são preservados para progressão e terceira estrela. A calibração e a zona morta não são modificadas por compras.

[Análise consolidada](historico/ANALISE_CONSOLIDADA.md), [notas da entrega 1.6](historico/ENTREGA_1_6.md) e [roteiro presencial](VALIDACAO_PRESENCIAL.md) detalham o escopo e os limites. A [entrega 1.5](historico/ENTREGA_1_5.md) é histórica.
