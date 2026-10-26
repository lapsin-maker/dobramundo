# Progressão econômica — simulações registradas

## Escopo

Este resumo agrega os 18 relatórios JSON da subpasta `economia/`; não executa nem recalcula voos. Cada relatório contém três voos no modo Normal e três no Difícil. O conjunto cobre três configurações do mesmo agente sintético (`dynamic-position-agent-v1`), dois biomas (Amazônia e Caatinga) e três sementes iniciais (1, 101 e 201): 3 × 2 × 3 relatórios e 108 voos. As sementes seguintes e os resultados de cada voo estão nos JSONs.

As configurações são **base** (assistência padrão e decisões/percepção intermediárias), **explorar-lento** (exploração, menor tentativa de coleta, mais erros deliberados e reação mais lenta) e **preciso-sem-apoio** (apoio desligado, maior tentativa de coleta, menos erros e reação mais rápida). As latências simuladas são 0,25 s na base, 0,35 s em explorar-lento e 0,10 s em preciso-sem-apoio. Cada voo tem limite de 45 s ativos, mas pode terminar antes por perda de vidas ou interrupção. Cada arquivo registra os parâmetros usados.

Durante o voo ativo, a cidade recupera 1 ponto percentual por segundo, até 100%. Coletas aceleram essa transformação e trazem recursos e pontos; peças continuam exigindo sua compra no hangar. O progresso pelo tempo não gera esses itens nem acelera o avião. Pausas, menus e carregamento não contam como voo ativo. Ao chegar a 100%, a cidade permanece transformada, mas o voo seguinte continua normalmente.

## Transformação e conclusão

“Ganho por voo” é a diferença entre a transformação global final e inicial daquele voo. “Cidade ao fim” resume o valor final entre os 18 voos de cada configuração e modo; valores repetidos de 100% aparecem porque alcançar esse limite não encerra voos posteriores. Os números são pontos percentuais. “Concluiu” conta as seis sequências de três voos (uma por combinação de bioma e semente) que cruzaram 100% até o terceiro voo.

| Configuração | Modo | Ganho por voo, mín. / mediana / máx. | Cidade ao fim, mín. / mediana / máx. | Sequências que cruzaram 100% até 3 voos |
|---|---|---:|---:|---:|
| Base | Normal | 0 / 8,5 / 91 | 88 / 100 / 100 | 6 de 6 |
| Base | Difícil | 0 / 0 / 95 | 100 / 100 / 100 | 6 de 6 |
| Explorar-lento | Normal | 0 / 23 / 76,5 | 73,5 / 100 / 100 | 6 de 6 |
| Explorar-lento | Difícil | 0 / 0 / 95 | 100 / 100 / 100 | 6 de 6 |
| Preciso-sem-apoio | Normal | 0 / 27,5 / 70,1 | 55,9 / 100 / 100 | 6 de 6 |
| Preciso-sem-apoio | Difícil | 0 / 26,8 / 95 | 65,9 / 100 / 100 | 6 de 6 |

As 18 sequências Normal cruzaram 100% no segundo voo. No Difícil, 14 das 18 cruzaram no primeiro e quatro no segundo. O tempo ativo acumulado até 100% variou por configuração: Base, 0,87–0,93 min no Normal (mediana 0,87) e 0,52–0,64 min no Difícil (0,60); Explorar-lento, 1,02–1,03 min no Normal (1,02) e 0,58–0,70 min no Difícil (0,68); Preciso-sem-apoio, 0,89–1,06 min no Normal (0,95) e 0,56–0,77 min no Difícil (0,68). São tempos deste agente parametrizado, não uma previsão de duração para crianças.

## Primeiras obras

O **Ponto de troca** foi registrado nas seis sequências de cada configuração e modo até o terceiro voo. No Normal, surgiu entre o primeiro e o terceiro voo; no Difícil, entre o primeiro e o segundo. A **Horta** apareceu em 0/6 sequências Base Normal, 6/6 Base Difícil, 0/6 Explorar-lento Normal, 6/6 Explorar-lento Difícil, 0/6 Preciso-sem-apoio Normal e 1/6 Preciso-sem-apoio Difícil. Nessas trajetórias, chegar a 100% e reunir materiais para obras são resultados distintos: a recuperação contínua não fornece recursos.

## Limites de interpretação

Os 108 voos foram produzidos pelo mesmo modelo de controle sintético, com coleta, erro deliberado, reação, exploração e apoio configurados por cenário. O agente simplifica a aproximação a alvos de rota com um obstáculo; não é uma pessoa, não representa a variabilidade motora ou decisória infantil e não foi validado como modelo de usuário. Os relatórios também registram colisões, coletas e recursos, mas esses números não medem diversão, compreensão, alcance físico, acessibilidade ou esforço. A aceitação da economia requer ensaio com crianças e observação presencial; as simulações não substituem essa avaliação.

## Dados-fonte

- [Base — Amazônia](economia/base-amazonia-1.json), [Base — Caatinga](economia/base-caatinga-1.json); os sufixos `101` e `201` identificam as outras sementes iniciais.
- [Explorar-lento — Amazônia](economia/explorar-lento-amazonia-1.json), [Explorar-lento — Caatinga](economia/explorar-lento-caatinga-1.json).
- [Preciso-sem-apoio — Amazônia](economia/preciso-sem-apoio-amazonia-1.json), [Preciso-sem-apoio — Caatinga](economia/preciso-sem-apoio-caatinga-1.json).

Os seis links ilustram os cruzamentos; para os demais dados, consulte os arquivos irmãos com sufixo `101` e `201`.
