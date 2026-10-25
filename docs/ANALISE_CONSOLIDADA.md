# Análise consolidada — estado de implementação

Esta lista atualiza as prioridades após as entregas P0/P1/P2 no código da versão 1.6.0. “Implementado” descreve código e validação técnica, não aceite de participantes. As evidências, condições e limites estão na [entrega 1.6](ENTREGA_1_6.md), no [relatório de desempenho](validacao-v1.6/desempenho.md) e na [simulação econômica](validacao-v1.6/economia/sintese.md).

A análise e o inventário completos que precederam a sprint estão preservados em [ANALISE_BASE_1_5.md](ANALISE_BASE_1_5.md); esta atualização resume estado e pendências sem apagar proveniência nem o backlog histórico.

## Checklist

| Frente | Estado no código | Validação ainda necessária |
|---|---|---|
| Liquidação e encerramento | Resultado completo/parcial idempotente por voo; fechamento normal liquida apenas voo iniciado; retry de save e histórico, cobertos por testes. | Confirmação de comportamento no equipamento de destino. Encerramento forçado do processo não é recuperável. |
| Câmera e controle | Pausa por leitura inválida/envelhecida, recuperação supervisionada, controles configuráveis e captura/inferência reais medidas localmente. | Reconexão física, latência ponta a ponta e conforto por segmento. |
| Acessibilidade de sessão | Permanência, contraste, exploração, duração, assistência previsível e treino estão implementados. | Compreensão sem leitura e alcance confortável com crianças e configurações distintas. |
| Missões e desafios | Metas selecionadas a partir dos alvos disponíveis; seeds efetivas registradas; desafios comunitários repetíveis; economia simulada com erros, pausas e interrupções. | Balanceamento percebido por participantes; a simulação não representa crianças. |
| Perfis e saves | Slots locais anônimos, save legado preservado, gravação atômica, cópias rotativas, recuperação e bloqueio em falha de leitura. | Testes de interrupção no sistema operacional e recuperação em máquina/disco de destino. |
| Fábrica de cenas e separação de plataforma | Criação injetável preserva fábrica padrão; armazenamento por jogador do T-TEA continua separado; contratos de integração testados. | Execução no console físico. |
| Render e desempenho | Loader seletivo, composição aquarelada, camadas separadas, cache com descarte e orçamento cooperativo. Benchmarks e ensaio prolongado publicados junto à entrega. | Picos de quadro ainda observados, sobretudo com webcam; medir no hardware de destino. Nenhum FPS ou latência física é garantido aqui. |
| Artefatos de release | CI com testes e builds nativos Windows/Linux, detector obrigatório e dependências Linux verificadas. Artefatos e hashes vinculados à entrega. | Instalação e uso nas máquinas de destino, além do console físico. |

## P0 — segurança de fluxo e confiabilidade

As prioridades foram liquidação de recompensa, fechamento normal, falhas de câmera, medição de latência, caminho seguro e independência do conforto em relação a compras. Campos de peças e requisitos de estrelas foram preservados. A liquidação é idempotente dentro da instância do voo; não equivale a checkpoint após encerramento abrupto ou perda física do disco.

## P1 — experiência e manutenção

- Implementados: exploração sem eliminação, limites curtos, assistência previsível, sementes para replay, recuperação de perfil e perfis desktop compartilhados com dados anônimos.
- Implementados: seleção de missões conforme entidades no percurso, registro explícito do resíduo coletado para o balanço e fábrica de cenas injetável.
- Validação pendente: duração confortável, compreensão da assistência, economia percebida e fluxo sem dependência de leitura.
- Aceite presencial: webcam, seis controles, projeção no chão a 2–3 m, movimento reduzido, alto contraste, sessões curtas e troca de piloto. Ver [roteiro presencial](VALIDACAO_PRESENCIAL.md).

## P2 — arquitetura e processo

- Implementados no código: APIs explícitas para entrada e cenas, separação progressiva das camadas do mundo, ferramentas de preparação/auditoria de assets e contrato entre render e simulação.
- Cobertura medida sem meta artificial; lint e formatação globais, CI por versão de Python e builds nativos com self-test. A entrega registra a execução conferida e o manifesto da release identifica as revisões.
- Revisões de desempenho devem registrar equipamento e condições; testes sintéticos não demonstram ergonomia individual, eficácia terapêutica ou latência física da projeção.
- Preservar geradores/fallbacks e compatibilidade do cartucho até validação no console real. A distribuição PNG não prova orçamento de memória no hardware T-TEA.

## Critério para fechar a entrega

Manter as evidências de CI/build e medições vinculadas à versão correspondente em [ENTREGA_1_6.md](ENTREGA_1_6.md). O aceite presencial continua distinto; não converter capturas estáticas ou simulações em resultado de usuário.
