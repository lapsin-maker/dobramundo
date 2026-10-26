# Dobramundo 1.7 — a cidade continua mudando

A transformação conquistada fica guardada em cada cidade. Um voo curto deixa de apagar o avanço anterior: na próxima decolagem, a paisagem continua de onde estava, com vidas e velocidade inicial renovadas. Ao terminar o tempo combinado, a tela informa que o voo terminou e mostra o que foi conquistado.

Perfis anteriores recuperam o maior avanço registrado no histórico. Quando só há estrelas, a migração conserva o estágio mínimo que elas comprovam; duas estrelas, por exemplo, não são tratadas automaticamente como 100% de transformação.

Na primeira execução, a criança monta seu piloto, acompanha a história do jornal e chega à vila. A história tem **Pular** e pode ser revista. Os primeiros três voos oferecem apoio, respeitando uma escolha feita no menu. Fechar durante a preparação do cenário não consome um desses voos.

## O que mudou na experiência

- **Escolhas mais claras:** Opções tem quatro grupos — Controle, Superfície, Som e Acessibilidade. O editor conserva o tempo de permanência mais lento e a exigência de sair do alvo antes de repetir.
- **Leitura:** textos auxiliares maiores e mais escuros, números de vidas derivados das regras, avisos de recompensa fora do horizonte e sinal discreto de troca das pequenas missões.
- **Identidade:** piloto neutro em papel quente, criança maior e sentada no avião, textura de pigmento no mapa e detalhes regionais dos obstáculos, preservando as três manobras aprendidas.
- **Preparação:** o cenário é preparado antes do primeiro quadro interativo. A barra representa tarefas concluídas; não é um temporizador fictício.
- **Movimento:** amostragem suave do chão, margens contínuas e avisos de ameaças que ficam fora da imagem ampliada no alto contraste.
- **Progresso protegido:** duas janelas não abrem simultaneamente o mesmo diretório de dados. Perfis antigos são migrados; um arquivo de uma versão futura é preservado e não é sobrescrito.
- **Downloads menores:** os pacotes levam uma variante de cada imagem usada no jogo. Originais e instruções de geração continuam no repositório para edição.

## Revisão dos 18 itens anteriores

| Item | Implementação e verificação |
|---|---|
| R01 — custo dos quadros | Medição de tempos inclusivos e exclusivos; solo com amostragem suave; comparação por bioma, contraste e câmera no relatório de desempenho. |
| R02 — entrada do voo | Fila de preparo com tarefas nomeadas e medidas; voo aguarda a prontidão real. Preparação e primeiro quadro interativo são medidos separadamente. |
| R03 — memória | Orçamento compartilhado de 192 MiB para caches de superfícies derivadas, contagem de armazenamento compartilhado e remoção da conversão duplicada. Arte base e buffers ativos não fazem parte desse teto; RSS é medido separadamente. |
| R04 — latência usada | Sequência da amostra consumida acompanha o quadro até a apresentação; ferramenta tem modo de controle real pela câmera, sem salvar imagens ou posições corporais. |
| R05 — duas instâncias | Bloqueio por diretório e revisão esperada do arquivo; testes com processos, encerramento inesperado e escrita antiga. |
| R06 — versão do perfil | Esquema 2, migração explícita da versão 1, testes de repetição e preservação byte a byte de versão futura. |
| R07 — mensagens e vidas | Mensagem de encerramento honesta; preparação mostra as mesmas vidas e proteção utilizadas pelo motor. |
| R08 — avisos na pista | HUD extraído; aviso de conquista posicionado na periferia, com tratamento de oclusão e redução de movimento. |
| R09 — ampliação | Indicadores de ameaça fora da imagem ampliada; testes de bordas e escalas 1,0/1,3/1,6. |
| R10 — piloto | Proporção maior, pose sentada, separação de cabelo/roupa/papel e ajuste por modelo de avião. |
| R11 — escolhas | Piso de texto auxiliar e contraste maiores; pictogramas e benefícios de apoio consistentes com as regras. |
| R12 — ritmo | Transformação persistente, ganho por coleta revisto e assistência inicial; simulações com erros/tempos de reação e trajetórias independentes, sem alterar os preços. |
| R13 — pequenas missões | Barra discreta de prazo no cartão da missão, sem piscar; usa tempo ativo do mundo e não retira recursos. |
| R14 — continuidade | Capturas de todos os estágios, abertura, resultados e obras; sequências das emendas e mudanças de estágio. |
| R15 — contratos | Dependências explícitas do desenho e verificação estática incremental no CI, com testes das camadas. |
| R16 — responsabilidades | Modelo/migração separados do armazenamento, liquidação em serviço próprio, HUD separado e geração desativada por política explícita. Construtor de resultado não grava nem notifica. |
| R17 — regressões | Novos casos de persistência, abertura, progresso, zoom, preparo, recursos, telemetria e comparação de imagens revisadas em ambiente fixo. |
| R18 — distribuição | Inventário compartilhado pelos builds, montagem versionada da release, manifestos/hashes, self-tests nativos e verificação do cartucho isolado. |

As funções auxiliares sem uso foram removidas. A busca de rota separa agrupamento de ameaças e cálculo de células seguras; seus testes preservam os intervalos e predicados de segurança. O modelo de perfil saiu de `persistence.py`. Fontes e ajuste de texto usam os helpers compartilhados nos caminhos alterados.

As notas das entregas anteriores estão em [histórico](historico/README.md). O README e a descrição do repositório explicam o jogo em linguagem direta. Onze branches já mescladas foram removidas após conferência dos commits; suas alterações continuam na história da main e dos pull requests.

## Evidências e limites

Os resultados medidos ficam em [validação 1.7](validacao-v1.7/README.md). Os testes sintéticos não demonstram conforto infantil, reconhecimento dos seis segmentos em todas as pessoas, leitura a 2–3 m ou desempenho do console físico. Esses critérios têm roteiro próprio em [validação presencial](VALIDACAO_PRESENCIAL.md).

O limite de cache não é um limite de memória total do processo. A medição da câmera começa no retorno da captura e termina na chamada de apresentação; não inclui atraso do sensor nem do projetor. Repetir usa a mesma semente e as mesmas escolhas, com a transformação já conquistada; não reconstrói uma partida interrompida.

Os 72 mil quadros do ensaio prolongado terminaram sem falha e com cache dentro do orçamento. **As metas de desempenho ainda não passaram integralmente:** o p95 excede 16,67 ms em parte das condições com câmera/alto contraste, e a entrada fria da Amazônia excedeu a meta de 50 ms. A implementação e a medição dos itens R01/R02 estão entregues; esses dois alvos de aceite permanecem em aberto. Consulte os [números e limites](validacao-v1.7/desempenho.md) antes de escolher o equipamento da sessão.

## Arte e procedência

A textura nova do mapa foi gerada pela ferramenta integrada `image_gen` e aplicada às máscaras geográficas existentes. O arquivo de edição é [map_pigment_v17.png](../assets/watercolor/map_pigment_v17.png); o [prompt completo e a procedência](../assets/watercolor/generation_v17_map.json) acompanham a imagem. A versão preparada do pacote tem 768 × 768 px. As demais alterações desta entrega usam composição e os assets já disponíveis.

Código, arte e textos próprios seguem CC BY 4.0; fontes e dependências mantêm seus créditos e licenças.
