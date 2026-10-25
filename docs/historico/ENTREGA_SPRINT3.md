# Entrega da sprint 3 — controle confortável e mundo vivo

Prévia de 25/10/2026. [Baixar os pacotes](https://github.com/lapsin-maker/dobramundo/releases/tag/sprint3-controle-e-vida-2026-10-25) · [PR #10](https://github.com/lapsin-maker/dobramundo/pull/10) · [escopo e operação](SPRINT3.md).

## Instalar e conferir

1. Extraia **Dobramundo-Sprint3-Windows.zip** por inteiro e abra **Jogar-Sprint3.bat**. Não é necessário instalar Python. Mantenha o executável junto da pasta `_internal`.
2. O lançador usa `%LOCALAPPDATA%\Dobramundo-Aquarela-Sprint3`, separado do perfil anterior. Assim é possível testar o piloto neutro e a vila inicial sem apagar progresso. Abrir o executável diretamente usa o perfil padrão.
3. Extraia **Dobramundo-Sprint3-Galeria.zip** e abra **galeria.html** junto da pasta `galeria-media`. As gravações começam apenas quando acionadas. Há dois percursos de 96 segundos e dois trechos de voo de 10 segundos.
4. **Dobramundo-Sprint3.ttea** é o cartucho validado pelo TSDK. A execução no console físico ainda precisa ser ensaiada.
5. **SHA256SUMS.txt** acompanha os três pacotes. Tamanhos, hashes e condições estão também em [validacao-sprint3.json](../validacao-sprint3.json).

Os pacotes executáveis foram produzidos do código `87813ed8001195796c1a19a2d02239d26b7bfb45`. Os commits posteriores de entrega apenas acrescentam documentação e evidências. A versão interna continua 1.4.0; a identificação desta prévia é a tag `sprint3-controle-e-vida-2026-10-25` e o `BUILD-INFO.json` do pacote Windows.

## Resultado frente ao diagnóstico

| Frente | Entrega |
|---|---|
| Legibilidade do voo | Categorias visuais de coleta/benefício/obstáculo preservadas; alto contraste amplia o mundo uniformemente, contorna o avião e mantém HUD e apontadores alinhados. Escudo e ímã têm arcos separados; missões contam ações por marcas visuais. |
| Unidade visual | Vila industrial e intermediária novas, quatro fundos da história, arte do mapa, moradores e fauna em aquarela. Piloto com expressões, hangar com modelos grandes e prévia de voo. Os 11 novos PNGs têm prompts e origens no manifesto. |
| Experiência infantil | Treino de mirar/esperar/retirar, permanência mais lenta e trava após escolha; pedidos de moradores, usos das obras e reação do piloto ligam a recompensa à transformação da vila. Textos de apoio continuam disponíveis. |
| Controle corporal | Âncora da cabeça e fallback compensado, descarte de leitura envelhecida, alcance total do cursor, calibração assimétrica de quatro direções e diagnóstico ao supervisor. |
| Avanço pelo cenário | Água/solo e margens seguem distância contínua; troca de estágio e saída das peças próximas têm dissolução gradual. Marcos de horizonte não viram cópias sucessivas na margem. |
| Conforto e preparação | Atalhos de conforto, contraste, calibração, projeção e treino de seleção; movimento reduzido mantém informação estática e sons concorrentes são limitados. |

## Verificação executada

- **404 testes** na suíte completa local. Após a otimização final de ampliação, **14 testes direcionados** passaram novamente. A CI do código final passou em Python 3.8 e 3.12. Ruff e auditoria AST passaram.
- Self-test do **código e do executável Windows**, 1.200 quadros por cidade, com `--exigir-camera`: duas cidades chegam ao terceiro estágio, cenas carregam e detector de pose é criado; sem falhas. O self-test **não abre a webcam**.
- Os **39 PNGs aquarelados** do Windows e do staging do cartucho foram comparados por SHA-256 com os arquivos fonte.
- TSDK: **505 arquivos portáveis**, check aprovado e cartucho construído. O SDK local tinha um lançador apontando para Python ausente; foi executado com o Python 3.14 instalado e as dependências já presentes, sem alterar o ambiente compartilhado.
- Capturas reais de menus, vila e voo, incluindo avião nos extremos com ampliação de 1,6×. Os percursos gravados atravessam **6,17 ciclos de margens** e ambas as transições. A transformação é forçada no ensaio de renderização; não representa progresso obtido por uma criança. As gravações normais precedem apenas a última otimização, que afeta exclusivamente o alto contraste.
- Referências de mídia da galeria verificadas. As capturas foram inspecionadas diretamente; a prévia automatizada do HTML no navegador foi bloqueada pela política da ferramenta para `file://`.

## Desempenho e aceite ainda necessário

Medição CPU sem webcam, SDL dummy, resolução lógica de 1100×650, 60 quadros de aquecimento e 600 medidos por caso. São tempos de atualização/desenho, sem limitador de FPS, e não uma garantia no projetor.

| Caso | Mediana | p95 |
|---|---:|---:|
| Manaus normal | 6,82 ms | 8,83 ms |
| Manaus alto contraste | 9,89 ms | 18,90 ms |
| Petrolina normal | 5,39 ms | 9,57 ms |
| Petrolina alto contraste | 9,27 ms | 15,80 ms |

O orçamento para 60 fps é 16,7 ms. O p95 de Manaus em alto contraste e picos dos demais casos ultrapassam esse valor; **60 fps constantes com captura real não estão comprovados**. A ampliação usa escala rápida e o fundo cinza é processado em resolução reduzida para conter esse custo.

Os recursos solicitados desta sprint estão implementados. O que permanece aberto é:

1. Testar com a pessoa real se a cabeça mantém leitura nas laterais e alcança os extremos após calibração; ajustar o detector ou o mapeamento se o ensaio revelar perdas.
2. Medir captura + jogo + saída no equipamento de destino, sobretudo alto contraste, e otimizar os gargalos observados até o orçamento de quadro necessário.
3. Validar tamanho, contraste, oclusão pelo pé e orientação na projeção a 2–3 m, além dos demais segmentos de controle.
4. Avaliar com crianças, mediante supervisão, entendimento dos símbolos, tempo de seleção, conforto e percepção das mudanças na vila; reduzir a dependência de explicação onde o teste indicar.
5. Executar o cartucho no T-TEA físico. Check/build e testes de Python não demonstram esse funcionamento presencial.

Nenhuma imagem da webcam foi gravada para esta entrega. Os cenários e sprites gerados por IA são arquivos locais; o jogo não precisa de serviço de IA em execução.
