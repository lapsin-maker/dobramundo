# Progressão econômica — simulações registradas

## Escopo

Este resumo sintetiza os 18 relatórios JSON da subpasta `economia/`; não executa nem recalcula voos. Cada relatório contém três voos no modo Normal e três no Difícil. O desenho cobre três configurações do mesmo agente sintético (`dynamic-position-agent-v1`), dois biomas (Amazônia e Caatinga) e três sementes iniciais (1, 101 e 201): 3 × 2 × 3 relatórios, 108 voos no total. As sementes seguintes e os resultados de cada voo estão registrados nos JSONs.

As configurações são: **base**, com assistência padrão e decisões/percepção intermediárias; **explorar-lento**, com exploração, tentativa de coleta menor, erros deliberados mais frequentes e reação mais lenta; e **preciso-sem-apoio**, com apoio explicitamente desligado, tentativa de coleta maior, menos erros e reação mais rápida. A latência de entrada simulada é 0,25 s na base, 0,35 s em explorar-lento e 0,10 s em preciso-sem-apoio. Cada voo tem uma janela máxima de até 45 s ativos, mas conclusão da cidade, perda de todas as vidas ou interrupção parametrizada podem encerrá-lo antes disso. Cada arquivo detalha os parâmetros exatos.

## Transformação e conclusão

Na tabela, “ganho por voo” é a diferença entre a transformação global da cidade no fim e no início daquele voo. “Cidade ao fim” é o valor global final registrado (mínimo, mediana, máximo entre os 18 voos de cada configuração e modo). Os valores são pontos percentuais; cidades que já chegaram ao limite podem ter ganho zero. “Concluiu” conta sequências de três voos que cruzaram 100% até o voo indicado, entre seis combinações de bioma e semente por configuração.

| Configuração | Modo | Ganho por voo, min / mediana / máx. | Cidade ao fim, min / mediana / máx. | Sequências concluídas até 3 voos |
|---|---|---:|---:|---:|
| Base | Normal | 12 / 32 / 46 | 43 / 74 / 100 | 4 de 6 |
| Base | Difícil | 0 / 13,1 / 95 | 76,2 / 100 / 100 | 6 de 6 |
| Explorar-lento | Normal | 13,5 / 23,5 / 36 | 28,5 / 51 / 100 | 1 de 6 |
| Explorar-lento | Difícil | 0 / 2,7 / 95 | 88,3 / 100 / 100 | 6 de 6 |
| Preciso-sem-apoio | Normal | 13,5 / 22,5 / 45,5 | 27,5 / 59 / 100 | 2 de 6 |
| Preciso-sem-apoio | Difícil | 0 / 33,3 / 64,1 | 40 / 78,1 / 100 | 6 de 6 |

No conjunto, 7 das 18 sequências Normal chegaram a 100% no terceiro voo; nenhuma concluiu antes do terceiro. No Difícil, 18 de 18 chegaram ao limite em até três voos: 3 no primeiro, 11 no segundo e 4 no terceiro. Isso descreve somente estas trajetórias parametrizadas. Não é uma taxa de sucesso de crianças, nem demonstra equilíbrio, conforto ou justiça entre modos.

## Primeiras obras

O **Ponto de troca** foi registrado em todas as seis sequências de cada configuração e modo até o fim do terceiro voo. O momento variou: nas sequências Normais, surgiu entre o primeiro e o terceiro voo; no Difícil, entre o primeiro e o segundo, exceto na configuração explorar-lento, em que apareceu já no primeiro.

A **Horta** apareceu com menor regularidade: em 2/6 sequências Base Normal e 5/6 Base Difícil; em 0/6 Explorar-lento Normal e 6/6 Explorar-lento Difícil; e em nenhuma sequência Preciso-sem-apoio, em ambos os modos. Assim, chegar a 100% e conseguir materiais para obras são resultados distintos; as simulações não sustentam que toda primeira obra esteja disponível rapidamente em qualquer trajetória.

## Limites de interpretação

Os 108 voos são produzidos pelo mesmo modelo de controle sintético, com parâmetros de coleta, erro deliberado, reação, exploração e apoio configurados por cenário. O agente simplifica a escolha de aproximação a alvos de rota com um obstáculo; não é uma pessoa, não representa a variabilidade motora ou decisória infantil e não foi validado como modelo de usuário. Os relatórios registram também colisões, coletas e recursos, mas esses números não medem diversão, compreensão, alcance físico, acessibilidade ou esforço. A aceitação da economia requer ensaio com crianças e observação presencial, sem substituir a decisão delas por estas simulações.

## Dados-fonte

- [Base — Amazônia](economia/base-amazonia-1.json), [Base — Caatinga](economia/base-caatinga-1.json); os sufixos `101` e `201` identificam as outras sementes iniciais.
- [Explorar-lento — Amazônia](economia/explorar-lento-amazonia-1.json), [Explorar-lento — Caatinga](economia/explorar-lento-caatinga-1.json).
- [Preciso-sem-apoio — Amazônia](economia/preciso-sem-apoio-amazonia-1.json), [Preciso-sem-apoio — Caatinga](economia/preciso-sem-apoio-caatinga-1.json).

Os seis links ilustram cada cruzamento; para os demais dados, consulte os arquivos irmãos com sufixo `101` e `201`.
