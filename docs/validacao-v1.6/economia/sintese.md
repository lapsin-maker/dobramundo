# Economia P1/P2 — reavaliação após expiração de metas e custos iniciais

**Modelo:** `dynamic-position-agent-v1`; cada execução usa 8 sementes por bioma e modo. Os JSONs foram regenerados após a expiração de missão não cumprida aos 60 s ativos e usam a implementação atual. O agente controla posição com a física real de `Player`, uma decisão simplificada de rota, erros deliberados e colisões reais. Não representa crianças nem constitui teste de usabilidade.

**Limites:** os resultados descrevem só esse modelo. As metas expiram sem recompensa/punição e aguardam 2,5 s para nova oferta; isso evita objetivo preso, mas não mede se 60 s é o ritmo ideal para crianças. Não alterei preços posteriores.

## Cenários e resultados

| Cenário / bioma | Modo | Ativo / parede médios | Conclusões | Game over | Limite/interrupção | Batidas médias | Recursos/voo (papel, plástico, metal, vidro) |
|---|---|---:|---:|---:|---:|---:|---|
| Padrão · Manaus | Normal | 51 / 51 s | 0/8 | 8/8 | 0/8 | 3.1 | 5.5 · 9.2 · 9.5 · 6.8 |
| Padrão · Manaus | Dificil | 25 / 25 s | 0/8 | 8/8 | 0/8 | 3.4 | 6.5 · 7.4 · 8.0 · 8.6 |
| Padrão · Petrolina | Normal | 50 / 50 s | 0/8 | 8/8 | 0/8 | 3.1 | 6.5 · 9.2 · 10.0 · 5.5 |
| Padrão · Petrolina | Dificil | 25 / 25 s | 0/8 | 8/8 | 0/8 | 3.4 | 6.5 · 7.4 · 8.0 · 8.6 |
| Erro + encerramento aos 20 s · Manaus | Normal | 20 / 20 s | 0/8 | 0/8 | 8/8 | 0.8 | 2.5 · 1.5 · 3.5 · 0.0 |
| Erro + encerramento aos 20 s · Manaus | Dificil | 16 / 16 s | 0/8 | 6/8 | 2/8 | 2.6 | 6.0 · 7.5 · 7.2 · 6.1 |
| Erro + encerramento aos 20 s · Petrolina | Normal | 20 / 20 s | 0/8 | 0/8 | 8/8 | 0.8 | 2.5 · 1.5 · 3.5 · 0.0 |
| Erro + encerramento aos 20 s · Petrolina | Dificil | 15 / 15 s | 0/8 | 6/8 | 2/8 | 2.6 | 5.6 · 7.2 · 7.0 · 6.1 |
| Explorar + assistência + limite 120 s · Manaus | Normal | 120 / 130 s | 0/8 | 0/8 | 8/8 | 12.2 | 25.2 · 28.8 · 27.8 · 21.2 |
| Explorar + assistência + limite 120 s · Manaus | Dificil | 120 / 130 s | 0/8 | 0/8 | 8/8 | 19.0 | 54.4 · 63.1 · 55.4 · 64.1 |
| Explorar + assistência + limite 120 s · Petrolina | Normal | 120 / 130 s | 0/8 | 0/8 | 8/8 | 11.6 | 24.0 · 26.0 · 28.8 · 21.2 |
| Explorar + assistência + limite 120 s · Petrolina | Dificil | 120 / 130 s | 0/8 | 0/8 | 8/8 | 18.9 | 53.2 · 60.5 · 54.0 · 60.6 |
| Erro + pausa + limite de 120 s · Manaus | Normal | 43 / 44 s | 0/8 | 8/8 | 0/8 | 3.1 | 5.0 · 6.8 · 6.0 · 3.8 |
| Erro + pausa + limite de 120 s · Manaus | Dificil | 17 / 17 s | 0/8 | 8/8 | 0/8 | 3.1 | 6.4 · 8.1 · 7.8 · 6.2 |
| Erro + pausa + limite de 120 s · Petrolina | Normal | 45 / 47 s | 0/8 | 8/8 | 0/8 | 3.1 | 5.5 · 8.2 · 6.0 · 3.8 |
| Erro + pausa + limite de 120 s · Petrolina | Dificil | 17 / 17 s | 0/8 | 8/8 | 0/8 | 3.1 | 6.0 · 7.9 · 7.5 · 6.2 |

## Primeiras compras

Custos: **Ponto de troca = 8 papel + 8 plástico**; **Horta = 24 papel + 16 vidro**. Para cada cenário, bioma e modo, usei os oito registros guardados em ordem de semente (1 a 8) como **uma única trajetória sintética de oito voos**. Somei os recursos mantidos pelo perfil, comprei o Ponto assim que possível e depois a Horta assim que possível. Prêmios de missão entram no saldo, como no jogo; `collected` permanece uma contagem separada de coletas físicas.

| Cenário / bioma | Modo | Voo do Ponto | Voo da Horta após o Ponto |
|---|---|---:|---:|
| Padrão · Manaus | Normal | 1 | 6 |
| Padrão · Manaus | Difícil | 2 | 7 |
| Padrão · Petrolina | Normal | 1 | 6 |
| Padrão · Petrolina | Difícil | 2 | 7 |
| Erro + encerramento aos 20 s · Manaus | Normal | 6 | >8 |
| Erro + encerramento aos 20 s · Manaus | Difícil | 2 | 6 |
| Erro + encerramento aos 20 s · Petrolina | Normal | 6 | >8 |
| Erro + encerramento aos 20 s · Petrolina | Difícil | 3 | 7 |
| Explorar + assistência + limite 120 s · Manaus | Normal | 1 | 1 |
| Explorar + assistência + limite 120 s · Manaus | Difícil | 1 | 1 |
| Explorar + assistência + limite 120 s · Petrolina | Normal | 1 | 1 |
| Explorar + assistência + limite 120 s · Petrolina | Difícil | 1 | 1 |
| Erro + pausa + limite de 120 s · Manaus | Normal | 5 | 7 |
| Erro + pausa + limite de 120 s · Manaus | Difícil | 2 | 6 |
| Erro + pausa + limite de 120 s · Petrolina | Normal | 3 | 6 |
| Erro + pausa + limite de 120 s · Petrolina | Difícil | 3 | 7 |

Cada linha é somente uma trajetória construída com oito sementes; não é oito trajetórias independentes, frequência de sucesso ou chance para jogadores. O voo indicado é o primeiro em que o saldo acumulado permite a compra nessa trajetória. Os resultados descrevem o agente sintético, não preveem a progressão de uma criança. Os preços de entrada seguem a decisão de produto: 2 coletas de cada material no Normal para o Ponto; os custos posteriores foram preservados.

## Rotas comunitárias

A auditoria delimitada das quatro sementes oficiais em Manaus e Petrolina, normal e difícil, com introdução ligada/desligada, obteve **32/32 casos aprovados** após 25 s simulados por mundo: rota inicial validada independentemente, frontier não vazia e zero falhas de tutorial. Isso valida o contrato do planner nesses casos, não alcance físico individual. Detalhes em `audit-community-routes.json`.

## Artefatos

- `baseline-amazonia-8.json`
- `baseline-caatinga-8.json`
- `errors-early-stop-amazonia-8.json`
- `errors-early-stop-caatinga-8.json`
- `exploration-assistance-amazonia-8.json`
- `exploration-assistance-caatinga-8.json`
- `errors-interruption-amazonia-8.json`
- `errors-interruption-caatinga-8.json`
- `audit-community-routes.json`
- `sintese.md` (este relatório)
