# Dobramundo

![Logo do Dobramundo](assets/ui/logo.png)

**Dobre o papel, voe e transforme a cidade.** Exergame sério de voo em que a criança pilota, com o próprio corpo, um avião de papel reciclado.

## O jogo

O Dobramundo é um exergame sério de voo, com proposta terapêutica. A criança pilota um avião de papel reciclado sobre cidades brasileiras poluídas e, a cada voo, as transforma em cidades solarpunk integradas à natureza do seu bioma. O nome une a dobradura de papel à transformação do mundo, como na canção *Aquarela*, popularizada por Toquinho.

O jogo atende ao console T-TEA, com projeção no chão e controle pelos pés, mas não se restringe a ele: pode ser projetado em mesas e paredes ou exibido em monitores, e o controle pode ser feito pelos pés, pelo tronco, por uma das mãos ou pela cabeça. Destina-se a crianças neurodiversas e com deficiências motoras, visuais, sensoriais ou do neurodesenvolvimento, oferecendo a cada uma um modo de interação compatível.

Projeto da Liga de Psiquiatria e Neurociências – CENSUPEG, desenvolvido para a 3ª ExerGame JAM LARVA/UDESC 2026. Versão 1.1.0.

### Tema e objetivo

O jogo trata a sustentabilidade em duas escalas:

- **Ambiental:** adota o paradigma solarpunk, vertente que imagina sociedades tecnológicas, movidas a energia renovável e integradas à natureza. O percurso segue a trilogia vaporpunk, dieselpunk e solarpunk, da cidade dieselpunk à solarpunk (Lodi-Ribeiro, 2012).
- **Pessoal:** atividade corporal regular, prazerosa e acessível.

O objetivo não é restaurar uma natureza intocada, mas construir uma cidade em que a natureza integra a vida urbana. Na abertura, uma criança dobra um jornal em avião numa metrópole poluída. A cada voo, os resíduos recolhidos viram recursos que desenvolvem a vila-base e o avião.

### Objetivos de Desenvolvimento Sustentável

| ODS | Nome | Relação com o jogo |
|---|---|---|
| 3 | Saúde e Bem-Estar | Atividade física e estímulo sensório-motor |
| 7 | Energia Limpa e Acessível | Microgeração solar |
| 10 | Redução das Desigualdades | Acessibilidade |
| 11 | Cidades e Comunidades Sustentáveis | Cidade integrada à natureza |
| 12 | Consumo e Produção Responsáveis | Resíduos como recursos |
| 15 | Vida Terrestre | Biomas brasileiros |

## Fases

A versão atual tem duas fases, cada uma numa cidade brasileira do seu bioma:

| Fase | Cidade | Peças exigidas para a 3ª estrela |
|---|---|---|
| Amazônia | Manaus (AM) | Estabilizador, nível 1 |
| Caatinga | Petrolina (PE) | Leme, nível 1, e Quilha, nível 1 |

- Petrolina abre quando a criança conquista pelo menos 1 estrela em Manaus.
- Cerrado, Mata Atlântica, Pantanal e Pampa aparecem no mapa como "Em breve".
- A paisagem de cada fase tem três estágios: cidade industrial (dieselpunk), despertar ecológico e cidade solarpunk. Eles se sucedem aos 33,3% e aos 66,7% de transformação.

## Como se joga

Cada partida segue o ciclo **vila-base, mapa, voo e resultado**. Na vila, a criança escolhe a fase e o modo no mapa. No voo, o avião decola da vila, coleta resíduos e power-ups, desvia de obstáculos e acumula transformação. No resultado, estrelas e recursos vão para o perfil, e a criança volta à vila para construir melhorias e peças.

### Resíduos e recursos

Há quatro tipos de resíduo, com as cores da coleta seletiva da Resolução CONAMA nº 275/2001: papel (azul), plástico (vermelho), metal (amarelo) e vidro (verde). Eles aparecem em três alturas da pista. Cada coleta gera recursos para a vila e para as peças do avião: 4 recursos por coleta no modo Normal e 1 no modo Difícil. Um halo pulsante marca tudo o que se pode pegar, e chevrons âmbar no chão marcam o que colide, em todos os estágios.

### Obstáculos

Cada tipo de obstáculo pede uma manobra:

- **Obstáculo baixo:** passar por cima.
- **Portal:** passar por baixo.
- **Torre:** desviar para o lado.

### Power-ups

- **Escudo:** 6 segundos sem colisões.
- **Ímã:** 7 segundos atraindo resíduos das faixas vizinhas.
- **Reparo:** devolve uma vida perdida. Com as vidas cheias, adiciona 2% à transformação da cidade.

### Vidas

A criança tem três vidas. Cada colisão consome uma delas, seguida de 1,25 segundo de invulnerabilidade, e zera o combo. Sem vidas, o voo termina.

### Transformação e estrelas

A transformação da cidade vai de 0% a 100%, começando em 5%. Ao atingir os limiares, a criança ganha estrelas:

- 1 estrela aos 33,3%, no despertar ecológico;
- 2 estrelas aos 66,7%, na cidade solarpunk;
- 3 estrelas com a cidade completa (100%), desde que as peças exigidas pela fase estejam instaladas no avião. Sem elas, a conclusão rende 2 estrelas, e a tela de resultado indica quais peças faltam.

Ao chegar a 100%, o avião segue planando por 3 segundos para a criança ver a cidade.

### Modos de jogo

A dificuldade é a primeira escolha do mapa, em dois cartões grandes: **Normal** (mais calmo) e **Difícil** (mais rápido, com combo). O modo atual também aparece na vila e no painel do voo.

| | Normal | Difícil |
|---|---|---|
| Velocidade | Metade da velocidade-base (170 unidades/s) | Velocidade plena (340 unidades/s) |
| Resíduos | 1 a cada 4 sorteados | Todos |
| Pontos por resíduo | 65, fixos | 15 vezes o combo |
| Transformação por coleta | 2,24 pontos percentuais | 0,35, mais 0,04 com combo de 4 ou mais |
| Recursos por coleta | 4 | 1 |
| Combo | Não há | Sobe a cada 4 coletas seguidas, até 8 vezes |

O combo zera se a criança passar 2,2 segundos sem coletar ou ao colidir. Nos dois modos, a dificuldade cresce ao longo de 240 segundos: a frequência de obstáculos aumenta e a velocidade sobe até 30 unidades/s no Difícil (metade no Normal); a transformação acrescenta até mais 30.

Com a criança pegando 4 de cada 10 resíduos, uma fase dura cerca de 4 minutos no Normal e 3,8 no Difícil, e tudo da vila e do avião fica comprado em cerca de 8 voos no Normal e 6 no Difícil (simulação em `tools/balance.py`).

### Metas curtas

Durante o voo aparece uma meta por vez, de 20 a 60 segundos: coletar resíduos de um tipo, desviar de obstáculos na faixa do avião, passar por baixo de portais ou pegar power-ups. No Normal os alvos são menores (por exemplo, 2 resíduos ou 3 desvios; no Difícil, 6 e 6). Cada meta cumprida rende 0,5% de transformação, 6 recursos e 50 pontos.

### Vila-base

A vila tem oito melhorias, compradas com recursos. Cada uma aparece no seu lugar na cena. Conforme a vila avança, o céu clareia e os prédios de fundo dão lugar à arquitetura solarpunk. O percentual "sustentável" da tela é a proporção de melhorias construídas. ESC na vila pergunta se é para sair do jogo.

| Melhoria | Custo | Descrição |
|---|---|---|
| Ponto de troca | 30 papel, 30 plástico | Separa os resíduos e os transforma em recursos |
| Horta urbana | 40 papel, 30 vidro | Alimento fresco plantado no meio da vila |
| Painéis solares | 60 metal, 50 vidro | Microgeração de energia limpa nos telhados |
| Compostor | 40 plástico, 30 metal | Restos orgânicos viram adubo para a horta |
| Cisterna | 50 plástico, 40 metal | Guarda a água da chuva para regar e beber |
| Bicicletário | 50 metal, 30 plástico | Bicicletas no lugar dos carros a diesel |
| Telhado verde | 60 papel, 40 vidro | Plantas no telhado refrescam as casas |
| Turbina eólica | 80 metal, 50 vidro, 30 papel | O vento também gera energia para a vila |

### Peças do avião

As peças são reaproveitadas de resíduos. Cada uma tem dois níveis e altera o voo:

| Peça | Nível 1 | Nível 2 | Efeito por nível |
|---|---|---|---|
| Estabilizador | 50 papel, 30 plástico | 90 papel, 60 plástico, 30 metal | Caixa de colisão 7% menor e inclinação nas curvas 20% menor |
| Leme reaproveitado | 50 plástico, 30 metal | 80 plástico, 60 metal, 30 vidro | Resposta do avião 18% mais rápida |
| Quilha de lata | 50 metal, 30 vidro | 80 metal, 60 vidro, 30 papel | Velocidade máxima 8% maior e zona morta do controle corporal 25% menor |

### Hangar

O hangar oferece 11 dobraduras de voo distinto, entre elas uma miniatura do 14-Bis. A pintura pode ser a original do estúdio ou uma de 14 cores de papel. Há 26 padrões: dois são gratuitos (Liso e Jornal) e os outros 24 custam pontos, de 300 a 5 000. Os pontos se acumulam em todos os voos. Escolher uma cor define o padrão do avião como liso.

### Piloto

A criança monta o piloto com tom de pele, estilo e cor do cabelo, roupa, óculos, acessório (boné, lenço, abafador de ruído, capacete de aviador ou nenhum), aparelho auditivo e cadeira de rodas. O piloto não tem marcação de gênero, e os dispositivos assistivos são itens comuns da lista.

## Controles

### Controle corporal pela webcam

O controle usa visão computacional (MediaPipe Pose). O jogo acompanha o segmento escolhido e converte seu deslocamento, em relação à postura neutra, em dois eixos que movem o avião para cima, para baixo, para a esquerda e para a direita.

| Segmento | Pontos do MediaPipe Pose usados |
|---|---|
| Pés | Tornozelos e pés (índices 27 a 32) |
| Tronco (em pé) | Ombros e quadris (índices 11, 12, 23 e 24) |
| Tronco (sentado) | Ombros (índices 11 e 12) |
| Mão direita | Punho (índice 16) |
| Mão esquerda | Punho (índice 15) |
| Cabeça | Nariz e orelhas (índices 0, 7 e 8) |

- **Calibração:** a criança fica parada na postura confortável por cerca de 2 segundos (40 leituras). O jogo usa a mediana como centro. A calibração pode ser refeita em Opções, na pausa ("Recalibrar") e ao trocar de segmento.
- **Menus:** um cursor acompanha o segmento. O botão é acionado quando o cursor permanece sobre ele pelo tempo de permanência, que é de 1,2 segundo por padrão e pode ser ajustado de 0,6 a 3,0 segundos em Opções.
- **Sensibilidade:** de 0,5 a 2,0 vezes (padrão 1,0). Valores maiores exigem um movimento menor.
- **Pausa automática:** se o segmento sai da área de captura por 1 segundo durante o voo, o jogo pausa. Ao voltar, espera a presença estável por 1,2 segundo e faz uma contagem de 3 segundos antes de retomar.
- Sem webcam, sem as bibliotecas ou sem o modelo de pose, o jogo segue com teclado e mouse. Se a câmera falhar com um segmento selecionado, o motivo aparece em Opções e na calibração.

### Teclado e mouse (supervisor)

| Ação | Teclas |
|---|---|
| Voar | Setas ou W, A, S, D. Espaço também sobe |
| Navegar nos menus | Setas ou W, A, S, D |
| Confirmar nos menus | Enter, Espaço ou clique |
| Voltar nos menus | Esc ou Backspace |
| Pausar e retomar o voo | P ou Esc |
| Voltar à vila, na pausa | C |
| Tela cheia | F11 (em qualquer tela) |
| Caixas de colisão, no voo | F3 |
| Modo demonstração, no voo, sem colisões | F2 |

O mouse também seleciona botões por permanência quando não há controle corporal ativo.

### Superfícies de exibição

Em Opções, a superfície pode ser monitor, parede, mesa ou chão (T-TEA). Cada uma traz uma sugestão de segmento: qualquer segmento, tronco ou cabeça, uma das mãos, ou pés sobre a projeção. Se a câmera já estiver em uso, escolher a superfície aplica o segmento sugerido (chão: pés; mesa: mão direita; parede: tronco em pé), com um aviso. Para câmeras vistas de cima, a opção **Inverter subir e descer** troca o sentido vertical.

As opções **Espelhar** e **Girar 180°** atingem a imagem inteira. Espelhar serve à projeção por trás de uma parede. Girar serve ao projetor no teto ou à imagem no chão ou na mesa. O mouse é convertido de volta para as coordenadas do jogo.

## Acessibilidade, segurança e privacidade

- **Alto contraste:** dessatura o fundo e destaca avião, resíduos, obstáculos e alertas com cores intensas e contornos espessos.
- **Som:** volumes geral, de música e de efeitos, e opção de silêncio, que reduz a carga sensorial em casos de hipersensibilidade auditiva. Cada estágio tem sua própria trilha, com troca suave.
- **Ritmo:** tempo de permanência e sensibilidade ajustáveis, pausa automática e pausa a qualquer momento com P ou Esc.
- **Vídeo:** processado localmente, quadro a quadro, e nunca gravado. O supervisor vê apenas uma miniatura ao vivo, mantida em memória.
- **Supervisão:** o uso requer a supervisão de um adulto (Pereira et al., 2023). Na primeira execução, o jogo mostra um aviso ao supervisor, que precisa confirmar a leitura antes de seguir.
- **Dados e LGPD:** o aviso cita os arts. 11 e 14 da Lei nº 13.709/2018 (LGPD) e informa que o uso depende do consentimento dos responsáveis. O perfil salvo guarda progresso, personalização e opções. Não guarda imagens nem medidas do corpo: a calibração da postura neutra fica só na memória e é refeita a cada sessão.

## Instalar e jogar

### Executável para Windows

Após a geração com `build_windows.bat` (ver [Gerar o executável](#gerar-o-executável)), o jogo fica na pasta `dist\Dobramundo\`. Abra `Dobramundo.exe` dentro dela e distribua a pasta inteira. Com a opção `onefile`, o arquivo gerado é `dist\Dobramundo.exe`. O executável não mostra janela de console, a menos que seja gerado com `DOBRA_CONSOLE=1`.

### Pelo código-fonte

Requisitos: Python 3.8 ou mais novo. A webcam é opcional e exige MediaPipe e OpenCV.

```
python -m pip install -r requirements-webcam.txt
python run_dobramundo.py
```

- `python -m dobramundo` é equivalente a `python run_dobramundo.py`.
- A opção `--sem-som` inicia o jogo sem som.
- Para jogar só com teclado e mouse, instale apenas `requirements.txt`.
- No Windows, `Jogar_Dobramundo.bat` instala as dependências na primeira vez e inicia o jogo.
- O controle corporal exige o modelo `assets/pose_model/pose_landmarker_lite.task`.

### Onde ficam o perfil, o log de erros e o relatório

| Arquivo | Executável | Código-fonte |
|---|---|---|
| `dobramundo_perfil.json`, com progresso, personalização e opções | `%APPDATA%\Dobramundo` (Windows) ou `~/.local/share/Dobramundo` (Linux) | Pasta `save/` na raiz do projeto, se for gravável |
| `dobramundo_erro.log`, com o rastreamento de uma falha | Mesma pasta | Mesma pasta |
| `dobramundo.log`, com avisos (imagem, som ou câmera que falhou, perfil que não gravou) | Mesma pasta | Mesma pasta |
| `self_test.json`, com o relatório do `--self-test` | Mesma pasta | Mesma pasta |

Se a pasta escolhida não for gravável, o jogo usa a próxima opção da lista (a pasta do sistema e, por fim, a pasta temporária). No macOS, a pasta do sistema é `~/Library/Application Support/Dobramundo`. A variável de ambiente `DOBRAMUNDO_DATA_DIR` substitui a pasta de dados. O perfil é gravado de forma atômica, com arquivo temporário e troca.

### Importar o save do protótipo Eco Runner

Se não houver perfil salvo, o jogo importa da pasta de dados do protótipo (`EcoRunner`, ou a pasta `save/` do código-fonte) os pontos acumulados, os padrões comprados, a pintura e o avião escolhidos e o modo de jogo. A importação acontece só na primeira execução.

## Gerar o executável

### Windows

```
build_windows.bat [onefile] [nopause]
```

O script procura o Python 3, cria o ambiente `.venv`, instala `requirements-webcam.txt` e `pyinstaller>=6,<7` com as versões exatas de `constraints-build.txt`, limpa as pastas `build` e `dist` e roda `PyInstaller --noconfirm --clean Dobramundo.spec`. Depois copia o README para a pasta de saída e executa `Dobramundo.exe --self-test 90 --exigir-camera` sem abrir janela (`SDL_VIDEODRIVER=dummy`). A geração falha se o self-test retornar código diferente de zero ou não gravar o relatório: faltam sprites, um voo não chegou ao estágio 3 ou, com `--exigir-camera`, o detector de pose não carregou dentro do executável.

- `onefile` gera um único arquivo, `dist\Dobramundo.exe`. Sem essa opção, o padrão é `dist\Dobramundo\`.
- `nopause` não espera tecla ao final, útil em automações.
- `DOBRA_CONSOLE=1` mantém a janela de console, para depuração.
- O PyInstaller não faz compilação cruzada. O `.exe` precisa ser gerado no Windows.

### Linux

```
./build_linux.sh
```

O script segue a mesma sequência com `python3` e gera `dist/Dobramundo/Dobramundo` (modo de pasta). Ele confere se o relatório do self-test contém `"status": "ok"`. No Debian ou no Ubuntu, instale antes o pacote `python3-venv`.

### Especificação e assets

`Dobramundo.spec` empacota toda a pasta `assets/` com as extensões `.png`, `.json`, `.ogg`, `.wav`, `.task` e `.ico`. As variáveis `DOBRA_ONEFILE=1` (arquivo único) e `DOBRA_CONSOLE=1` (console) alteram a geração. Para trocar um sprite sem recompilar, coloque o PNG em `Dobramundo/assets/<pasta>/<nome>.png`, ao lado do executável. O jogo procura essa cópia antes da embutida.

## Desenvolvimento

### Estrutura do repositório

```
dobramundo/                          pacote do jogo
    __init__.py, __main__.py         nome, versão e entrada com "python -m dobramundo"
    main.py                          ponto de entrada, primeira cena e mensagens de erro
    app.py                           janela, laço principal e serviços compartilhados
    config.py                        constantes do motor (tela, projeção, voo, neblina, paralaxe)
    paths.py                         pastas de assets e de dados (código-fonte e executável)
    persistence.py                   perfil versionado em JSON e importação do protótipo
    audio.py                         trilhas por estágio, efeitos e volumes
    selftest.py                      teste de fumaça (--self-test) e critérios de aprovação
    log.py                           avisos em dobramundo.log
    util.py                          funções numéricas, de cor e de neblina
    content/                         dados do jogo, sem pygame
        biomes.py                    fases, estágios, cenários e obstáculos
        planes.py                    aviões, pinturas, padrões e curvas de manobra
        pilot.py                     opções do piloto
        progress.py                  melhorias da vila, peças do avião e estrelas
        items.py                     resíduos, power-ups e tipos de obstáculo
        texts.py                     textos, créditos e referências
    game/                            regras do voo, sem pygame
        run.py                       um voo: vidas, pontos, combo, estrelas e eventos
        missions.py                  metas curtas dentro do voo
        world.py                     pista, trechos e transformação
        player.py                    física do avião e manobras
        entities.py                  objetos e caixas de colisão
    engine/                          desenho pseudo-3D
        world_view.py                ordem de pintura de uma fase
        sky.py, ground.py            céu em paralaxe e chão texturizado
        sprites.py                   projeção, neblina e caches de sprite
        cache.py                     BoundedCache (descarte gradual) usado por todos os caches
        plane_skin.py, pilot.py      aparência do avião e piloto em camadas
        assets.py                    carregamento preguiçoso dos PNG
    input/                           entradas
        hub.py                       teclado, mouse e controle corporal
        pose.py                      MediaPipe Pose, segmentos e calibração
    ui/                              tema, botões e seleção por permanência
    scenes/                          telas: abertura, aviso, calibração, vila, mapa, voo etc.
        __init__.py                  registro das cenas: scene.goto("vila")
assets/                              sprites, sons, texturas, modelo de pose e curvas
tools/                               geração de assets (ver tools/README.md)
tests/                               suíte pytest
docs/                                GDD e arte original da logo
docs/arquitetura.md                  arquitetura do código
run_dobramundo.py                    atalho para rodar pelo código e entrada do PyInstaller
Dobramundo.spec                      receita do PyInstaller
build_windows.bat, build_linux.sh    geração do executável
Jogar_Dobramundo.bat                 atalho para jogar pelo código no Windows
pyproject.toml                       metadados, dependências opcionais e configuração do ruff e do pytest
constraints-build.txt                versões exatas usadas para gerar o executável
.github/workflows/testes.yml         CI: lint, testes e self-test em Python 3.8 e 3.12
```

### Testes

```
python -m pytest
```

A suíte roda sem janela e sem áudio (drivers `dummy`), com o perfil isolado em pasta temporária. Ela cobre seis módulos: assets, cenas, controle corporal (sem webcam), regras do voo, progressão e perfil, e a pista.

### Lint e formato

```
ruff check .
ruff format --check .
```

A configuração está em `pyproject.toml`: 120 colunas, alvo Python 3.8 e as regras E, F, W, I, B e UP. Sem `--check`, `ruff format` reescreve os arquivos.

### Teste de fumaça

```
python -m dobramundo --self-test 240
```

O número após `--self-test` é a quantidade de quadros por voo, com padrão de 240. O teste percorre todas as telas e voa as duas fases com invencibilidade, forçando as três etapas de transformação. Grava `self_test.json` na pasta de dados, com os sprites carregados, os tempos de quadro (média e percentil 95) e o resultado de cada voo. O perfil real não é alterado. O relatório traz `status` (`ok` ou `falhou`) e a lista `falhas`; o código de saída é 1 quando há falha. Com `--exigir-camera`, o teste também carrega o detector de pose do MediaPipe (sem abrir a webcam) e reprova se ele não funcionar.

### Integração contínua

`.github/workflows/testes.yml` roda lint, testes e self-test a cada push e pull request, em Python 3.8 (mínimo declarado) e 3.12 (versão do build).

### Regenerar os assets

Os comandos abaixo estão detalhados, com dependências, em [tools/README.md](tools/README.md).

```
python tools/build_assets.py                   # sprites low-poly de fases e vila
python tools/build_assets.py --pilot           # camadas do piloto e anchors.json
python tools/make_audio.py                     # trilhas e efeitos sonoros
python tools/make_logo.py ARTE.png             # logo, ícone da janela e ícone do executável
python tools/make_ground_textures.py           # texturas de solo da Caatinga
python tools/measure_obstacles.py              # confere as medidas de colisão contra os sprites
```

### Compatibilidade com Python 3.8

O projeto mantém compatibilidade com Python 3.8, que é o piso de `requires-python` e o alvo do ruff. Conforme o escopo do projeto, esse piso atende ao console T-TEA. Os módulos usam `from __future__ import annotations` e os tipos do `typing`.

## Créditos

- **Equipe:** Liga de Psiquiatria e Neurociências – CENSUPEG
- **Membros:** João Pedro Turnes (capitão), Isabella Cordeiro Sonza, Gerciane Larice da Silva Barros e Luiz Felipe Santana Tomio
- **Captura:** Adaptada do T-TEA 2.0 (LARVA/UDESC)
- **Modelos 3D:** kits 3D da equipe, aviões do estúdio 3D do protótipo e modelos low-poly gerados por código (`tools/lowpoly`)
- **Referências de design:** Star Fox 64, Subway Surfers, It Takes Two e Super Mario World
- **Programação:** IA generativa (Gemini e Claude) apoiou a programação
- **Tecnologia:** Python, pygame, OpenCV e MediaPipe Pose
- **Música e efeitos:** Sintetizados pelo projeto
- **Evento:** 3ª ExerGame JAM LARVA/UDESC 2026

A música e os efeitos são gerados por síntese no script `tools/make_audio.py`. Os modelos low-poly das fases, da vila, dos resíduos e do piloto são gerados por código em `tools/lowpoly`.

## Referências

EPE. **Balanço Energético Nacional 2025: ano base 2024.** Rio de Janeiro: EPE, 2025.

LODI-RIBEIRO, G. (org.). **Solarpunk: histórias ecológicas e fantásticas em um mundo sustentável.** São Paulo: Draco, 2012.

PEREIRA, G. B. et al. Jogo sério para estímulo sensorial de crianças com transtorno do espectro autista. In: SBIE, 34., 2023, Passo Fundo. **Anais [...]**. Porto Alegre: SBC, 2023. DOI: 10.5753/sbie.2023.233744.

## Licenças

- **Código e assets da equipe:** o repositório ainda não define a licença do código, dos sprites, dos ícones, dos textos e das trilhas gerados pelo projeto. Sem um arquivo de licença, o repositório não concede, por si só, permissão de uso ou de redistribuição.
- **Modelo de pose** (`assets/pose_model/pose_landmarker_lite.task`): do Google MediaPipe, sob licença Apache 2.0.
- **Captura corporal:** adaptada do T-TEA 2.0 (LARVA/UDESC). A condição de uso desse código deve ser confirmada com o grupo de origem.
- **Dependências:** pygame, OpenCV e MediaPipe mantêm suas próprias licenças.
