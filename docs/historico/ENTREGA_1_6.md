# Entrega 1.6.0 — sessões, progressão, perfis e manutenção

**Escopo:** itens técnicos P1/P2 implementados na versão `1.6.0`, preservando os P0. O aceite com participantes, projetor e console físico continua pendente. [PR #12](https://github.com/lapsin-maker/dobramundo/pull/12) · [Release, pacotes e hashes](https://github.com/lapsin-maker/dobramundo/releases/tag/v1.6.0).

## Resultado implementado

- Perfis desktop locais anônimos, com slots independentes para progresso, piloto, opções e consentimento. O save legado permanece no slot `principal`; a tela de perfis não pede nome real. O console T-TEA continua usando o armazenamento por jogador do SDK.
- Gravação atômica com cópias anteriores validadas, tentativa de recuperação de perfis/índice e preservação de arquivos inválidos. Erros de leitura bloqueiam gravação que poderia apagar progresso; a interface informa quando recuperou apenas em memória.
- Preparação para sessões livres ou de 120, 180 e 240 segundos, modo exploração, assistência previsível e sementes de desafios publicadas. O resultado registra a semente efetiva e as opções necessárias ao replay.
- Encerramento parcial e completo idempotentes no fluxo normal: credita ganhos já obtidos, mantém histórico e permite nova tentativa de salvar. Encerrar pelo limite, pela pausa ou por colisão final não concede conclusão de fase que não ocorreu.
- Metas curtas são escolhidas conforme alvos presentes, após as lições iniciais, e dão lugar a outra oferta após 60 segundos ativos do mundo sem penalidade. Repetir o voo conserva a preferência de material, além da semente e dos modos.
- Ponto de troca custa 8 papel/8 plástico; Horta, 24 papel/16 vidro. As duas primeiras obras ficaram acessíveis mais cedo por decisão de produto; os demais preços foram preservados. A [simulação econômica](../validacao-v1.6/economia/sintese.md) inclui colisões, reação, erros, pausas e interrupções, sem representar jogadores humanos.
- Oito temas regionais usam sementes publicadas. A auditoria de 32 combinações de bioma, modo, introdução e semente encontrou rotas iniciais e manteve a geração por 25 segundos simulados em cada caso.
- Treze variantes PNG preparadas para a resolução de uso: seis fundos e sete atlas de aviões. O catálogo registra hashes, dimensões, vistas e pivôs; os 39 originais permanecem disponíveis. PNG e os renderizadores de reserva foram preservados.
- Caches têm limites de quantidade e bytes; a troca de bioma libera fundos, margens e sprites de céu. As métricas discriminam donos de superfícies e RSS, que também inclui bibliotecas e memória do processo.
- Desenho de pista, entidades, avião e piloto separado por camada; o motor recebe contratos de leitura sem importar regras de voo. Fontes e ajuste de texto são comuns, e todas as cenas usam a fábrica injetável.
- Testes agrupados por comportamento, helpers compartilhados, dependências fixadas por versão de Python, cobertura, builds nativos Windows/Linux e self-test dos executáveis. A formatação foi isolada no commit `b9b3c4e`: 152 árvores sintáticas comparadas sem mudança semântica.

## Resultados de validação

- A revisão técnica `d47035c` passou na [matriz de testes e builds](https://github.com/lapsin-maker/dobramundo/actions/runs/40236396562). A revisão final da PR e o manifesto anexado à release identificam os commits de fonte e build dos downloads.
- Suíte local principal: **515 testes passaram**, 197,48 s, Python 3.12, antes de acrescentar os três casos finais de diagnóstico/empacotamento. Os quatro testes finais de diagnóstico/empacotamento também passaram. Testes usam perfil sintético isolado.
- CI Python 3.8/3.12: a execução acima passou com 516 testes e dois filtros gráficos opcionais pulados. NumPy foi então fixado separadamente por versão de Python para incluir esses filtros na verificação final da PR, totalizando 518 casos. Lint e formatação fazem parte da matriz.
- Cobertura da execução identificada: **78,95% de linhas e 66,26% de ramos** no pacote `dobramundo`; [contagens e escopo](../validacao-v1.6/cobertura.json). Percentual não comprova qualidade ou comportamento em equipamento físico.
- Builds Windows e Ubuntu 24.04: executáveis testados com `--self-test 1200 --exigir-camera`. O detector foi carregado sem abrir a webcam. No Linux, `libegl1 libgles2` são dependências do sistema, e a CI verifica `libmediapipe.so` com `ldd`.
- Self-test local do fonte: **14 telas e 1.200 quadros por bioma**, detector carregado, sem falhas. [Relatório sem caminhos locais](../validacao-v1.6/selftest-fonte.json). A auditoria verificou os hashes dos **39 originais e 13 variantes preparadas**.
- T-TEA: `tsdk check` validou **527 arquivos portáveis** com o SDK em Python 3.14.8. O cartucho e seus hashes acompanham a release; console físico continua pendente.
- Capturas sintéticas: **15 telas**, sem botões fora da área ou sobrepostos. As quatro imagens de voo removem somente as partículas transitórias no quadro final, para mostrar o piloto; não constituem teste de usabilidade.
- Benchmark e webcam: [relatório com dados completos](../validacao-v1.6/desempenho.md). Comparação sem avatar: incremento de RSS na abertura de **160,7 para 87,2 MiB**; maior amostra ao fim dos cenários de **532,1 para 258,9 MiB**. Com avatar e webcam houve pico de **67,459 ms** por quadro. Não se afirma ganho geral de CPU ou 60 fps constantes.
- Ensaio prolongado: **30 ciclos, 1.215,5 segundos simulados e nenhuma falha**; 72 mil quadros de voo com trocas de cenas, biomas e aparências. RSS final de 542,5 MiB, máximo amostrado de 559,6 MiB; últimos dez ciclos entre 537,3 e 555,0 MiB. [Dados completos](../validacao-v1.6/soak.json).

A galeria, os dois pacotes desktop, o cartucho, `SHA256SUMS.txt` e `release-manifest.json` ficam na release. As duas revisões listadas no manifesto devem ter a mesma árvore de arquivos; o executável e seu diretório de bibliotecas são distribuídos juntos. Os relatórios históricos das versões anteriores permanecem preservados.

## Aceite presencial — pendente

Usar o [roteiro de validação presencial](../VALIDACAO_PRESENCIAL.md) em equipamento e com participantes. Ainda precisam ser observados controle por webcam, seis segmentos, projeção no chão a 2–3 m, legibilidade sem leitura, compreensão de sessão curta, exploração/assistência, transformação da vila, reconexão e troca de perfil. Capturas e testes automatizados não equivalem a esse aceite.

## Limites e recuperação

- Perfis são arquivos locais, não contas sincronizadas. Não se solicitam nomes reais; os slots não constituem controle de acesso ou proteção contra leitura por outros usuários do mesmo sistema operacional.
- Cópias rotativas protegem contra corrupção e interrupções durante gravações cobertas pelo mecanismo. Não recuperam alteração perdida antes da rotação, falha do disco, exclusão de todos os arquivos, encerramento forçado antes de salvar nem corrupção simultânea de todas as cópias.
- Liquidação idempotente vale durante a vida da instância do voo e para seu fechamento normal. Não é diário transacional/checkpoint que reconstrua uma execução depois de queda abrupta do processo.
- Os limites de sessão são limites do tempo contabilizado pelo voo, não prescrição clínica. Exploração mantém o jogo após perda de vidas; colisões continuam registradas. A assistência previsível tem parâmetros fixos no voo e não demonstra que o desafio está confortável para uma pessoa específica.
- A semente permite repetir a geração do desafio com as mesmas configurações e versão do código. Não garante identidade entre versões, plataformas ou alterações futuras no algoritmo.
- Simulação de equilíbrio não prova duração real, eficácia terapêutica, segurança clínica ou adequação motora. Nenhuma dessas conclusões é afirmada nesta entrega.

## Documentação relacionada

[Guia do jogo](../GUIA_DO_JOGO.md) · [Arquitetura](../arquitetura.md) · [Análise consolidada](ANALISE_CONSOLIDADA.md) · [Histórico](../../CHANGELOG.md)
