# P1 e P2 — meta e critérios de entrega

Base: `f80294b` (1.5.0). Branch `codex/p1-p2-experiencia-e-manutencao`.
Solicitação: implementar os itens P1/P2 da análise consolidada, preservando os P0.

## Frentes de implementação

| Frente | Critério verificável |
|---|---|
| Sessões, exploração e assistência | Escolhas explícitas antes do voo; término curto preserva conquistas; exploração permite erros sem eliminação; assistência não muda sem aviso. |
| Missões e economia | Primeiro objetivo compatível com o tutorial; oportunidades correspondentes presentes; simulação com erros, pausas e interrupções. |
| Percursos regionais | Semente registrada e repetível, variações coerentes com o bioma e desafios comunitários sem ranking obrigatório. |
| Saves e pilotos | Recuperação de backup válido, escrita atômica, perfis independentes, legado preservado e falhas visíveis. |
| Assets e memória | Preparação na resolução de uso, orçamento e descarte seletivo medidos; originais e fallback preservados. |
| Manutenção | Funções divididas por responsabilidade, remoção só de referências comprovadamente mortas, fachada de entrada e texto compartilhado. |
| Testes e builds | Nomes por comportamento, helpers comuns, cobertura medida, versões fixadas por Python, builds nativos Windows/Linux e self-test do executável. |
| Entrega | Documentação, fontes e pacotes rastreáveis, validação local e CI, merge na main. |

## Aceite presencial distinto

Compreensão a 2–3 m, conforto nos seis controles, uso com crianças, desconexão física
e instalação no console não são demonstrados por screenshots ou testes sintéticos.
O roteiro em `VALIDACAO_PRESENCIAL.md` terá resultados explicitamente pendentes
quando o equipamento ou participantes não estiverem disponíveis.

O console mantém PNG como formato de distribuição. A compatibilidade de um codec
no desktop não autoriza substituir os formatos no dispositivo de destino.

## Histórico e escopo

Não apagar branches, releases anteriores ou histórico Git. A limpeza do código
preserva os renderizadores de reserva. A formatação global será um commit próprio,
executado após as frentes paralelas terminarem. Descrição/tópicos do repositório
podem ser atualizados; prévia social será preparada como artefato se a API não
permitir aplicá-la. Não gravar imagens de câmera nem landmarks nos relatórios.
