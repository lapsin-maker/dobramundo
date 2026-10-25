# Entrega 1.6.0 — perfis, sessões e recuperação

**Estado deste registro:** implementação documentada; evidências finais de CI, builds e aceite presencial ainda não foram preenchidas. Versão fonte declarada em `dobramundo/__init__.py`: `1.6.0`.

## Resultado implementado

- Perfis desktop locais anônimos, com slots independentes para progresso, piloto, opções e consentimento. O save legado permanece no slot `principal`; a tela de perfis não pede nome real. O console T-TEA continua usando o armazenamento por jogador do SDK.
- Gravação atômica com cópias anteriores validadas, tentativa de recuperação de perfis/índice e preservação de arquivos inválidos. Erros de leitura bloqueiam gravação que poderia apagar progresso; a interface informa quando recuperou apenas em memória.
- Preparação para sessões livres ou de 120, 180 e 240 segundos, modo exploração, assistência previsível e sementes de desafios publicadas. O resultado registra a semente efetiva e as opções necessárias ao replay.
- Encerramento parcial e completo idempotentes no fluxo normal: credita ganhos já obtidos, mantém histórico e permite nova tentativa de salvar. Encerrar pelo limite, pela pausa ou por colisão final não concede conclusão de fase que não ocorreu.
- Metas curtas são escolhidas conforme alvos presentes. Fábrica de cenas pode ser injetada sem alterar o caminho padrão do jogo.

## Resultado de validação — preencher após execução final

- Commit validado: **PENDENTE**
- Suíte automatizada final (comando, resultado e saída): **PENDENTE**
- CI Python 3.8/3.12 (link e revisão): **PENDENTE**
- Build Windows/Linux e hashes dos pacotes: **PENDENTE**
- Cartucho T-TEA e console físico: **PENDENTE**
- Benchmark/soak da versão 1.6 (equipamento e condições): **PENDENTE**

Não reutilizar contagens ou medições de versões anteriores como resultado desta entrega. O campo de versão não comprova que os artefatos foram construídos ou publicados.

## Aceite presencial — pendente

Usar o [roteiro de validação presencial](VALIDACAO_PRESENCIAL.md) em equipamento e com participantes. Ainda precisam ser observados controle por webcam, seis segmentos, projeção no chão a 2–3 m, legibilidade sem leitura, compreensão de sessão curta, exploração/assistência, transformação da vila, reconexão e troca de perfil. Capturas e testes automatizados não equivalem a esse aceite.

## Limites e recuperação

- Perfis são arquivos locais, não contas sincronizadas. Não se solicitam nomes reais; os slots não constituem controle de acesso ou proteção contra leitura por outros usuários do mesmo sistema operacional.
- Cópias rotativas protegem contra corrupção e interrupções durante gravações cobertas pelo mecanismo. Não recuperam alteração perdida antes da rotação, falha do disco, exclusão de todos os arquivos, encerramento forçado antes de salvar nem corrupção simultânea de todas as cópias.
- Liquidação idempotente vale durante a vida da instância do voo e para seu fechamento normal. Não é diário transacional/checkpoint que reconstrua uma execução depois de queda abrupta do processo.
- Os limites de sessão são limites do tempo contabilizado pelo voo, não prescrição clínica. Exploração mantém o jogo após perda de vidas; colisões continuam registradas. A assistência previsível tem parâmetros fixos no voo e não demonstra que o desafio está confortável para uma pessoa específica.
- A semente permite repetir a geração do desafio com as mesmas configurações e versão do código. Não garante identidade entre versões, plataformas ou alterações futuras no algoritmo.
- Simulação de equilíbrio não prova duração real, eficácia terapêutica, segurança clínica ou adequação motora. Nenhuma dessas conclusões é afirmada nesta entrega.

## Documentação relacionada

[Guia do jogo](GUIA_DO_JOGO.md) · [Arquitetura](arquitetura.md) · [Análise consolidada](ANALISE_CONSOLIDADA.md) · [Histórico](../CHANGELOG.md)
