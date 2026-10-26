# Ferramentas de desenvolvimento e geração de assets

## Diagnóstico, estabilidade e capturas

Execute a partir da raiz do repositório, sem builds/testes concorrentes para comparar tempos:

```powershell
python tools/benchmark_runtime.py --out build/benchmark --frames 600 --screenshots
python tools/benchmark_runtime.py --out build/benchmark-camera --camera --paced
python tools/benchmark_camera.py --seconds 8 --output build/camera.json
python tools/check_routes.py --seeds 1000 --out build/rotas.json
python tools/soak_runtime.py --out build/soak --cycles 30 --frames 1200
python tools/capture_release.py --out build/capturas
```

`benchmark_runtime` mede abertura, memória residente no Windows/Linux, primeiro quadro, aquecimento e custo por quadro em dois biomas com/sem alto contraste. Usa CPU/SDL dummy; `--camera` abre a webcam para medir concorrência de inferência, com comandos de voo sintéticos. A idade do snapshot mais recente após a apresentação é distinta da métrica **captura→quadro consumido** da calibração integrada. Ambas começam no retorno da leitura e excluem exposição/buffering do sensor e latência física do monitor. Componentes estão aninhados e não devem ser somados.

`benchmark_camera` separa até 15 segundos de preparação da janela de amostragem; exige pelo menos cinco resultados publicados e encerramento confirmado. Falta de amostras ou erro retorna código 2. Essas ferramentas salvam métricas; apenas `--screenshots` grava imagens sintéticas do jogo, nunca da webcam ou dos pontos do corpo.

`check_routes` verifica sementes reproduzíveis, diversidade, auditoria completa de uma amostra, continuidade após avanço e tempos de inserção/geração. O contrato geométrico não substitui testes de controle corporal e conforto com a pessoa. Veja [condições e validação](../docs/historico/ENTREGA_1_5.md).

No benchmark, `--paced` cede CPU entre quadros para mirar 60 fps, excluindo esse sono dos tempos de processamento. Sem a opção, a execução é um teste de estresse sem limite de quadros. Registre a modalidade ao comparar resultados.

`soak_runtime` alterna cenas, biomas e contraste durante um percurso sintético
prolongado. Registra RSS, superfícies retidas, entidades e tempos por ciclo.
Tempo simulado e tempo de parede ficam separados; invencibilidade serve somente
ao estresse de renderização. Economia é medida separadamente por `balance.py`.

`capture_release` captura menus, perfis, estados de erro e voos com semente fixa.
Verifica os limites dos botões, mas a revisão das imagens continua necessária
para detectar cortes de texto, glifos ausentes e contraste insuficiente.

## Build nativo automatizado

Instale o conjunto desktop com Python 3.12 e execute `python tools/build_desktop.py`.
Os wrappers `build_windows.bat` e `build_linux.sh` preparam esse ambiente. O comando
gera `dist/Dobramundo`, testa 1.200 quadros por bioma e exige o detector de pose;
`--sem-camera` é uma variante explícita para teclado. Usa perfil temporário,
não apaga a pasta `dist/` inteira e não lê saves reais. O relatório sanitizado
fica em `build/desktop-selftest/self_test.json`.

A CI testa Python 3.8/3.12 com arquivos de dependências específicos, publica
cobertura e gera executáveis nativos em Windows/Linux. Segue a estrutura de
[build/test de Python do GitHub](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## Geração de assets

Os scripts desta pasta criam parte dos arquivos de `assets/` que o jogo carrega. O jogo não precisa das ferramentas para rodar: ele usa os PNG, OGG e JSON já gerados. Use-as para regenerar ou ajustar os assets indicados na tabela abaixo.

## Arte aquarelada da sprint 2

A direção visual principal está em `assets/watercolor/`: fundos, terreno, margens, vila, piloto, aviões e objetos pintados. Esses PNGs foram gerados por IA e estão versionados; `build_assets.py` e `stylize.py` não recriam esse conjunto. Prompts e identificadores das saídas estão em `generation.json`, `generation-sprint2.json` e `generation-pilot-sprint2.json`, na mesma pasta, junto de `CREDITOS.txt`.

O jogo recorta os atlases, aplica cores e estampas e projeta as peças em Pygame. Não gera imagens nem acessa serviços de IA durante a execução. Os geradores low-poly abaixo mantêm os sprites procedurais de reserva. Para revisar os novos PNGs, preserve a disposição dos atlases e confira os recortes em `painted_route.py`, `painted_pilot.py`, `painted_planes.py`, `paper_items.py` e `village_art.py`. Os testes correspondentes e o self-test estão descritos em [DIRECAO_AQUARELA.md](../docs/historico/DIRECAO_AQUARELA.md).

A pasta tem duas partes:

- **Geradores ativos** (`build_assets.py`, `stylize.py`, `make_audio.py`, `make_logo.py`, `make_ground_textures.py`, `make_grass_texture.py`, `measure_obstacles.py`, `balance.py`, `build_cartridge.py` e o pacote `lowpoly/`). Rodam a partir do repositório.
- **Legado** (`legado/`). Scripts do protótipo Eco Runner. Dependem de materiais externos que não estão no repositório (ver a seção própria).

## Ambiente

Para todos os geradores ativos, instale as dependências de desenvolvimento a partir da raiz do projeto:

```
python -m pip install -r requirements-dev.txt
```

Esse arquivo traz numpy, Pillow e soundfile (opcional, para OGG). O `measure_obstacles.py` também importa o pygame, que já vem com `requirements.txt`. O `build_cartridge.py` não usa essas dependências: ele precisa da ferramenta oficial de cartuchos do T-TEA (comando `tsdk`, Python 3.14).

## Fluxo de geração

```
tools/lowpoly/  (modelos por código: kit, mesh, raster, models_*)
    |
    +--> build_assets.py ----------> assets/biome_sprites/ (AM_, CA_, VL_)
    |                                assets/waste_sprites/ (papel, plastico, metal, vidro)
    |
    +--> build_assets.py --pilot --> assets/pilot_layers/ (camadas e anchors.json)
                                     (depende de assets/plane_sprites e plane_menu, do legado)

stylize.py ----------------------> filtro de papel e aquarela sobre os PNG de assets/ (sobrescreve;
                                   o git guarda os originais). build_assets.py aplica o mesmo filtro
                                   em cada sprite que gera

make_audio.py -------------------> assets/audio/ (musica_*.ogg, sfx_*.ogg)
make_logo.py  -------------------> assets/ui/logo.png, icone.png, assets/icon.ico, docs/logo.jpg
make_grass_texture.py -----------> assets/ground/grass.png
make_ground_textures.py ---------> assets/ground/dry_soil.png, agreste.png
                                   (importa make_grass_texture.py)
measure_obstacles.py ------------> nada gravado: confere as colisões contra os sprites
balance.py ----------------------> relatório opcional em JSON: voo, erros, pausas e recursos

build_cartridge.py --------------> build/cartucho/ e dist/dobramundo-<versão>.ttea
                                   (monta o pacote do jogo; valida e gera com o tsdk)
```

## Geradores ativos

| Ferramenta | O que gera | Comando | Dependências | Observações |
|---|---|---|---|---|
| `build_assets.py` | 48 sprites de fase e vila em `assets/biome_sprites/` (prefixos AM_, CA_ e VL_) e os 4 resíduos em `assets/waste_sprites/` | `python tools/build_assets.py [--only NOME ...] [--prefix AM_] [--sheet folha.png]` | numpy, Pillow | Renderiza os modelos registrados em `lowpoly/` e aplica o filtro de `stylize.py` (`stylize_image`, com `params_for` por pasta) em cada sprite. `--sheet` grava também uma folha de contato para conferência |
| `stylize.py` | Sobrescreve os PNG das pastas de `FOLDERS` em `assets/` (sprites de fases, vila, resíduos, power-ups e aviões) com o filtro de papel e aquarela | `python tools/stylize.py [--folders PASTA ...] [--only NOME ...] [--preview saida.png]` | numpy, Pillow | Degraus de claridade, contorno de tinta azul-marinho (`INK`), traço nas quebras internas e grão de papel. Os aviões (`LIGHT_INK_FOLDERS`: `plane_sprites` e `plane_menu`) têm traço mais fino e cinza-azulado. `--preview` grava antes e depois numa imagem, sem sobrescrever. O git guarda os originais |
| `build_assets.py --pilot` | Camadas do piloto em `assets/pilot_layers/` (`<vista>__<camada>.png`) e `anchors.json` | `python tools/build_assets.py --pilot` | numpy, Pillow | O `anchors.json` é medido a partir de `assets/plane_sprites` e `assets/plane_menu` (sprites `__riding` e `__none`), que vêm do estúdio legado |
| `make_audio.py` | 7 trilhas (`musica_vila`, `musica_amazonia_1` a `_3`, `musica_caatinga_1` a `_3`) e 15 efeitos (`sfx_*`) em `assets/audio/` | `python tools/make_audio.py [--out PASTA] [--only musica\|sfx]` | numpy; soundfile para gravar OGG | Síntese determinística (semente fixa). Sem soundfile, grava WAV de 16 bits com o mesmo nome |
| `make_logo.py` | `assets/ui/logo.png` (900 px de largura, fundo transparente), `assets/ui/icone.png`, `assets/icon.ico` e `docs/logo.jpg` (logo sobre fundo branco para o README) | `python tools/make_logo.py ARTE.png [--out assets]` | numpy, Pillow | Recebe a arte original (o repositório traz `docs/logo_original.webp`). Remove o branco do papel por desmistura da cor |
| `make_grass_texture.py` | `assets/ground/grass.png` | `python tools/make_grass_texture.py [--out assets/ground/grass.png] [--seed 7]` | numpy, Pillow | Textura de grama contínua nas bordas, para repetição sem emenda |
| `make_ground_textures.py` | `assets/ground/dry_soil.png` (despertar do sertão) e `agreste.png` (Petrolina solarpunk) | `python tools/make_ground_textures.py [--out assets/ground]` | numpy, Pillow | Importa `make_grass_texture.py`, que deve estar na mesma pasta |
| `measure_obstacles.py` | Nada gravado. Imprime, para cada obstáculo de cada fase, a medida usada no jogo ao lado da medida medida no sprite | `python tools/measure_obstacles.py` | numpy, Pillow, pygame | Usa a altura visual e o alfa dos sprites. Ajuda a calibrar `low`, `gate` e `tower` em `content/items.py` e `content/biomes.py` |
| `build_cartridge.py` | `build/cartucho/` (pasta montada do pacote) e `dist/dobramundo-<versão>.ttea` (cartucho do console T-TEA) | `python tools/build_cartridge.py [--tsdk CAMINHO_DO_TSDK] [--so-montar]` | ferramenta oficial de cartuchos do T-TEA (comando `tsdk`, Python 3.14) | Monta `dobramundo/` e `assets/` sem o que só o executável usa (`app.py`, `main.py`, `selftest.py`, `input/camera.py`) e sem o modelo de pose. Escreve `ttea.toml`, `pyproject.toml`, `CREDITOS.md` (a partir dos créditos do jogo) e copia o `LICENSE`, depois roda `tsdk check` e `tsdk build`. `--so-montar` só monta a pasta |

### Pacote `lowpoly/`

Não é um script, e sim a biblioteca usada por `build_assets.py`:

- `mesh.py`: malha de triângulos coloridos e primitivas (caixa, cilindro, esfera e outras), com a parte de cada triângulo.
- `raster.py`: rasterizador em numpy, em vista 3/4 com luz difusa, supersampling 3x e saída RGBA.
- `kit.py`: peças reutilizáveis (copas, folhas de palmeira, casas, painéis solares, janelas) e o registro `@model(nome, pasta, **render)`.
- `models_amazonia.py` e `models_caatinga.py`: modelos das fases, nas pastas `biome_sprites`.
- `models_common.py`: resíduos (`waste_sprites`) e melhorias da vila (`VL_`).
- `pilot.py`: corpo com proporções de criança e itens do piloto, nas vistas `flight` e `menu`: cabelos (incluindo o lenço e o raspado), roupas, óculos, acessórios (boné, lenço, abafador, capacete, flor, tiara e coroa), aparelho auditivo e cadeira de rodas. Gera também `skin_hijab`, que substitui a pele quando o cabelo é o lenço. As cores de pele, cabelo e roupa não são gravadas aqui: o jogo as aplica em `content/pilot.py`. As camadas do piloto não passam pelo `stylize.py`.
- `anchors.py`: mede, nos sprites com e sem piloto, onde o piloto senta em cada avião.

Para incluir um novo modelo, registre-o com `@model` em um dos `models_*.py`. Para um novo módulo de modelos, importe-o em `build_assets.py`.

## Legado: scripts do protótipo Eco Runner

Estes scripts geraram assets do protótipo. Ficam aqui para registro da proveniência, e a documentação completa está em `tools/legado/LEIAME.md`. Eles precisam de entradas que não estão no repositório.

| Ferramenta | O que gera | Entradas externas | Dependências |
|---|---|---|---|
| `legado/render_models.py` | Sprites dos kits Dieselpunk e EcoUrbe: `dieselpunk_sprites`, `scenario_sprites`, `skyline_sprites` e `atmosphere` (`sky_panorama`, `smog_cloud`) | Pasta `modelos_3d` com OBJ, MTL e texturas, informada com `--models` | numpy, Pillow |
| `legado/extract_planes.py` | Aviões e pilotos: `plane_sprites`, `plane_menu`, `plane_paint`, `plane_menu_paint`, `plane_uv`, `plane_menu_uv`, `plane_patterns` e `catalog.json` | HTML do estúdio 3D de aviões, com three.js e JSZip (`--html`, `--three`, `--jszip`) | Playwright e Chromium |
| `legado/extract_maneuvers.py` | `assets/maneuvers/maneuvers.json`, com as curvas das manobras | Pasta com as animações glTF (`--gltf-dir`) | Biblioteca padrão |
| `legado/make_concrete_texture.py` | `assets/ground/concrete.png` (concreto sujo do estágio industrial) | Nenhuma | numpy, Pillow |

Atenção: o `render_models.py` sobrescreve sprites que foram substituídos por versões revisadas da equipe (`fabrica`, `chamine`, `tambores` e `cacamba`). Use `--out` para gravar em outra pasta.

O `--out` padrão desses scripts é a pasta `assets/` da raiz do projeto.

## Assets sem gerador no repositório

Os arquivos abaixo estão em `assets/`, mas nenhum script do repositório os gera. Para regenerá-los é preciso a origem original, que não está versionada aqui:

- `assets/era_final_sprites/` (24 sprites `EF_*`, usados nas cidades solarpunk de Manaus e Petrolina).
- `assets/powerup_sprites/` (`shield`, `magnet` e `repair`).
- `assets/era_final_fx/` (`halo_coletavel` e `alerta_chao`).
- `assets/ground/meadow.png` e `assets/ground/paver_road.png`.
- `assets/fonts/`: Fredoka, Nunito e Patrick Hand, do Google Fonts, sob a SIL Open Font License 1.1. Os textos das licenças estão em `OFL-*.txt`.
- `assets/pose_model/pose_landmarker_lite.task`: modelo do MediaPipe Pose, de origem externa (Google).

Os PNG de `assets/dieselpunk_sprites`, `scenario_sprites`, `skyline_sprites` e `atmosphere` dependem do `render_models.py` do legado e da pasta `modelos_3d`, que não está no repositório.

## Equilíbrio (`balance.py`)

Simula comandos de um piloto automático com movimento limitado pela física real, colisões, atraso de reação e erros. `--coleta 0.4` é a probabilidade de **tentar** uma coleta; não garante alcançar o item. O relógio ativo para durante a pausa; o relatório registra separadamente tempo ativo, tempo total, coletas físicas, recursos com bônus, batidas, vidas e motivo do término. Rode depois de mexer em `dobramundo/config.py`, `dobramundo/content/progress.py` ou `dobramundo/game/missions.py`:

```
python tools/balance.py --coleta 0.4 --erro 0.15 --pausa 10 --voos 10 --out build/balance.json
python tools/balance.py --exploracao --assistencia --limite 120 --voos 10 --out build/exploracao.json
```

A ferramenta acumula a transformação entre voos, como o perfil do jogo, e informa em qual voo a cidade chega a 100%. Use sementes iniciais diferentes para trajetórias independentes. `--apoio-escolhido` representa um perfil que já decidiu manualmente sobre apoio; sem essa opção, os três primeiros voos recebem o apoio inicial. Recursos e preços continuam medidos separadamente do percentual visual.

O agente sintético não representa uma criança nem mede conforto motor. Interprete os resultados como regressão de economia e interrupções, junto ao aceite presencial.

## Preparação de imagens

`python tools/prepare_assets.py` produz fundos de voo, história e vila, atlas de aviões e pigmento do mapa na resolução de uso em `assets/watercolor_prepared/`. Mantém os originais no repositório e registra tamanho, SHA-256, vista, grade e pivô no manifesto. `python tools/audit_assets.py` confere o inventário. `runtime_assets.py` é compartilhado por desktop e cartucho: escolhe a variante verificada, sem duplicar o original, ou inclui o original quando a variante está ausente. Imagens de menus preparadas conservam o caminho lógico usado pelas cenas. Não há conversão de codec presumida compatível com o console.

## Medições e entrega

Execute benchmarks em processos novos e sem builds ou testes concorrentes. O padrão usa um piloto sintético personalizado; `--empty-pilot` reproduz a carga sem avatar da ferramenta 1.5. Os relatórios separam abertura, primeiros quadros, aquecimento, tempos de quadro e memória. Componentes aninhados não devem ser somados.

```powershell
python tools/benchmark_runtime.py --out build/benchmark --frames 600
python tools/benchmark_runtime.py --out build/benchmark-camera --frames 600 --camera --paced
python tools/benchmark_runtime.py --out build/controle-real --frames 600 --camera-control --window
python tools/benchmark_runtime.py --out build/entrada-fria --frames 30 --biome amazonia --contrast no
python tools/soak_runtime.py --out build/soak --cycles 30 --frames 2400
python tools/capture_release.py --out build/capturas
```

`--camera` mede processamento concorrente; `--camera-control` liga efetivamente a leitura da cabeça e registra a sequência consumida até canvas/apresentação, incluindo quantos quadros eram utilizáveis. Nenhum desses modos demonstra precisão física dos gestos ou atraso do sensor/projetor. Tempos exclusivos descontam componentes instrumentados filhos; os inclusivos não devem ser somados. A preparação é separada dos quadros interativos e suas tarefas têm tempos próprios.

O soak alterna biomas, contraste, aparências e menus usando perfis sintéticos. O preparo não conta como tempo ativo; invencibilidade e supressão do encerramento por conclusão mantêm a carga de desenho pelo ciclo inteiro. A economia é medida separadamente por `balance.py`, com colisões e término normal.

Para validar os arquivos isolados do cartucho: `python tools/build_cartridge.py --so-montar` seguido de `python tools/verify_cartridge.py --stage build/cartucho --out build/cartucho-render.json`. O CI executa esse percurso e compara menus capturados com referências revisadas. Isso complementa, sem substituir, `tsdk check`, `tsdk build` e o teste no console físico.

Para fechar uma release, use `python tools/package_release.py --help`. A rotina exige os dois artefatos nativos, relatório JSON da CI completa, commits de build/release com árvores iguais, checkout limpo na revisão da release, cartucho válido e diretório de saída. Confere versão, commit, execução/tentativa da CI, detector e identificador novo de cada self-test; compara fontes e assets do cartucho byte a byte com o inventário rastreado pelo Git. Ela gera downloads, `release-manifest.json` e `SHA256SUMS.txt`; não publica automaticamente. Nunca inclua perfis reais na galeria ou nos pacotes.

`build_desktop.py` constrói o pacote nativo, invalida resultados antigos e roda o executável com `--self-test 1200 --exigir-camera` em diretório temporário. A CI gera Windows e Linux, publica cobertura e preserva a permissão de execução do Linux em `.tar.gz`. Linux requer `libegl1 libgles2` (Debian/Ubuntu); a CI verifica as dependências de `libmediapipe.so` com `ldd` antes de empacotar. O diagnóstico manual só de Linux não substitui a matriz completa de testes e builds.
