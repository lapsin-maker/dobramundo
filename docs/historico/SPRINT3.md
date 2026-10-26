# Sprint 3 — controle confortável e mundo vivo

Implementação do backlog pós-sprint 2, a partir do teste do jogador em 25/10/2026. A referência visual continua sendo o conceito de papel e aquarela aprovado; as novas imagens são geradas por IA e compostas localmente no Pygame. Não há chamadas de geração durante o jogo.

## O que mudou

| Pedido / diagnóstico | Implementação |
|---|---|
| Cabeça perde leitura lateral | Nariz como âncora, orelhas compensadas individualmente quando o nariz não está disponível, diagnóstico de pontos/confiança/resolução/eixos. Leituras sem atualização por 0,35 s deixam de alimentar o cursor. |
| Não alcançar as bordas | Cursor corporal usa toda a área útil. Calibração guiada mede separadamente direita, esquerda, cima e baixo com o alcance confortável da pessoa; mantém assimetrias. O limite do voo continua sendo a pista jogável. |
| Confirmações precipitadas | Personalização usa 3 s por padrão, ajustável de 1 a 5 s; trava por chave e região do botão persiste após reconstruir o menu. Perda breve pausa a contagem; perda prolongada a cancela. |
| Alto contraste com objetos maiores | Ampliação de 1 a 1,6×, padrão 1,3×, do mundo completo; avião, itens, sinais e passagens recebem a mesma transformação. HUD fica nativo. Enquadramento acompanha o avião e setas usam a mesma conversão. |
| Vila inicial pouco industrial | Novos fundos inicial e intermediário com dutos, geradores, chaminés, ferrugem e resíduos localizados; fachadas vivas e aquarela preservadas. Os locais continuam reconhecíveis no estado solarpunk. |
| Repetição brusca do cenário | Distância contínua; margens mantêm posição e dissolvem entre estágios, primeiro ao longe. Saída no plano próximo também é gradual. Texturas mais suaves; Teatro Amazonas permanece como marco único no horizonte. |
| Menos leitura obrigatória | Missões com contas visuais por ação, relógios em arco para escudo e ímã, sinal gráfico de resposta no foco, peças da terceira estrela no mapa e treino específico de permanência. |
| Recompensa vivida na vila | Pedidos pictográficos persistidos para as oito obras; moradores em pé e em cadeira de rodas visitam os locais, usam melhorias e celebram. Construir continua consumindo os mesmos recursos. |
| Expressividade | Piloto curioso, concentrado, feliz e em recuperação no livro/resultado; selo de conquista e pequeno gesto das asas durante o voo. Movimento reduzido mantém o sinal estático. Efeitos sonoros limitados a dois canais, com prioridade de conquistas. |
| Vida regional | Garça e boto na Amazônia, ave da Caatinga; aparições breves nas margens, atenuadas perto de obstáculos. São cenografia, sem coleta ou colisão. |
| Livro, mapa e hangar | Quatro fundos próprios para a história; mapa com rota e cartões ilustrados; hangar com três modelos grandes por página, amostras de cor/estampa e prévia da orientação de voo. |
| Preparação e superfícies | Opções reúnem calibração, projeção, treino de seleção e conforto. Cursor e progresso fora do centro do alvo ajudam quando o pé encobre a imagem; rotação, espelho e mapeamento do chão continuam na camada de saída. |

## Controle e preparação

Na primeira execução, o aviso ao supervisor e a calibração corporal (se necessária) antecedem o treino opcional de seleção. A primeira escolha da criança continua sendo o piloto neutro; depois ela chega à vila e pode ir ao hangar, mudar o piloto ou decolar. A história é acessível em Opções. O treino de voo continua disponível antes da primeira decolagem.

Em **Calibrar**, espere a posição neutra ficar pronta. **Alcances** inicia quatro movimentos confortáveis, confirmados pelo supervisor com Enter; **Continuar** encerra a preparação. Esses alcances pertencem à sessão de captura. Não é preciso forçar amplitude máxima. A confiança exibida é um diagnóstico do detector, não uma medida clínica. A recentralização automática passa a ser opt-in; preferências explicitamente salvas em perfis existentes são preservadas.

Em **Opções**, ajuste a permanência da personalização separadamente da navegação geral. O atalho de conforto reduz efeitos decorativos e sons. O mouse mantém prioridade temporária depois de ser movido; ao cessar essa intervenção, o corpo reassume. Sem leitura corporal válida, um cursor antigo não confirma escolhas.

## Engenharia e arte

- `engine/accessible_view.py` define uma transformação única de câmera. Nenhuma hitbox ou regra de dificuldade é aumentada individualmente.
- `engine/painted_route.py` ancora as margens por distância absoluta e interpola sua aparência. Água/solo avançam mesmo em movimento reduzido; pausa congela a navegação.
- `engine/regional_life.py` mantém os encontros decorativos fora das entidades de jogo. O retorno após um obstáculo usa distância percorrida, inclusive para permanecer parado na pausa.
- `input/pose.py` mantém mapeamento independente de OpenCV/MediaPipe e aceita testes com pontos simulados. `input/camera.py` expõe resolução negociada, sem persistir quadros.
- `pedidos_vila`, `permanencia_editor` e `escala_contraste` são normalizados no perfil. Perfis antigos recebem padrões sem perder progresso.
- [Manifesto da arte](../../assets/watercolor/generation-sprint3.json) registra os 11 arquivos, prompts e origens. Os PNGs anteriores são conservados como referência/fallback; nenhuma dependência de IA é necessária em execução.

## Validação e limites

O roteiro reproduzível `tools/qa_sprint3.py --out <pasta> --record` captura telas e duas sequências de 96 segundos, com distância contínua, mais de seis ciclos de margens (período de 24 × 220 unidades) e ambas as mudanças de estágio. A progressão dessas sequências é forçada para inspecionar a renderização; elas não representam uma criança completando a fase. O relatório separa renderização normal e alto contraste. A [entrega e suas medições](ENTREGA_SPRINT3.md) registram os pacotes, os resultados e os limites de desempenho.

A suíte verifica perda/retorno de rastreamento, calibração assimétrica, travas de permanência, persistência, continuidade das margens, ampliação, fauna, sons e fluxo das cenas. O self-test verifica a carga do detector de pose, sem provar rastreamento físico.

Continuam necessários ensaios presenciais: movimentos laterais reais da cabeça, conforto de todos os seis segmentos, projeção a 2–3 m, entendimento dos símbolos e da transformação por crianças e funcionamento do cartucho no console físico. Esse aceite não pode ser inferido de screenshots ou testes sintéticos. Os recursos pedidos estão implementados; a adequação ao público e ao equipamento depende dessa avaliação mediada.
