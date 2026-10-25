# Dobramundo 1.5.0 — confiabilidade, conforto e desempenho

Esta entrega incorpora a análise externa do repositório e implementa os seis P0 da revisão de jogabilidade e engenharia. O [diagnóstico consolidado](ANALISE_CONSOLIDADA.md) registra o que foi confirmado e separa os próximos P1/P2.

## O que mudou

- A webcam encerra em segundo plano e só reabre depois de liberar a fonte anterior. Falhas podem ser recuperadas na calibração; leituras antigas deixam de mover o cursor ou expor o avião a colisões.
- Diagnóstico e ferramentas registram cadência, inferência e idade do resultado sem gravar imagens nem pontos do corpo. A idade começa no retorno de `VideoCapture.read`, não na exposição do sensor.
- **Encerrar voo** preserva os recursos e pontos obtidos e as estrelas já conquistadas. Fechamento normal, saída da recalibração e resultado compartilham a mesma liquidação. Reentrada e retry não duplicam crédito; o histórico distingue interrupção de conclusão.
- Piloto carrega apenas suas camadas. Fundos opacos usam superfícies apropriadas; terreno, horizonte e alto contraste gastam menos trabalho por quadro. A pré-carga respeita a folga estimada do quadro.
- Obstáculos passam por um planejador incremental com uma rota de referência, caixas de colisão reais e margens de manobra. O percurso avança sem recomeçar o planejamento do centro a cada geração.
- Resposta, velocidade, tolerância de colisão e zona morta são iguais antes e depois de comprar peças. Peças, níveis, saves e requisitos da terceira estrela continuam na progressão.

## Instalar

Baixe a [release 1.5.0](https://github.com/lapsin-maker/dobramundo/releases/tag/v1.5.0), extraia todo o ZIP Windows e abra `Jogar-Dobramundo.bat`. O lançador cria um perfil separado em `%LOCALAPPDATA%\Dobramundo-1.5.0`; não apaga os anteriores. Para o console, utilize o arquivo `.ttea`.

O código-fonte completo está nos arquivos automáticos da tag. A galeria contém capturas sintéticas do jogo e a entrega inclui hashes SHA-256. `BUILD-INFO.json` identifica o commit usado no executável. O [guia](GUIA_DO_JOGO.md) conserva as regras, os créditos e os detalhes antes concentrados no README.

## Validação

**446 testes locais passaram**, assim como lint e CI em Python 3.8/3.12. O self-test passou no código-fonte e no executável 1.5.0, carregando o detector de pose, desenhando 14 telas e percorrendo 1.200 quadros por bioma. O SDK validou 505 arquivos portáveis; o cartucho teve CRC e correspondência das fontes conferidos. Os pacotes incluem hashes SHA-256.

Os resultados e hashes estão em [validacao-1.5.0.json](validacao-1.5.0.json). Componentes do benchmark estão aninhados: seus tempos não devem ser somados. Foram usados Windows 11, Python 3.12.10, canvas 1100×650, áudio desabilitado e 600 quadros medidos por cenário após 60 quadros de preparação.

| Cenário | P95 sem câmera, sem limite de quadros | P95 com webcam e cadência de 60 fps | Máximo com webcam e cadência |
|---|---:|---:|---:|
| Manaus | 11,36 ms | 12,66 ms | 16,86 ms |
| Manaus, alto contraste | 12,37 ms | 16,07 ms | 22,48 ms |
| Petrolina | 7,57 ms | 8,58 ms | 11,99 ms |
| Petrolina, alto contraste | 10,84 ms | 14,12 ms | 19,18 ms |

O sono usado para mirar 60 fps fica fora do tempo de processamento medido. O teste com webcam **sem limite de quadros** também está preservado: apresentou P95 de 51,27 ms em Manaus/alto contraste, sob concorrência contínua por CPU. Portanto, o resultado não é garantia de 60 fps constantes. Na execução com cadência, 96% dos quadros de Manaus/alto contraste couberam em 16,67 ms.

- **Memória na abertura:** incremento de RSS de 377,9 MB no baseline para aproximadamente 170,4 MB; imagens aquareladas decodificadas na abertura caíram de 39 para 6. Isso não é o pico da sessão: ao visitar os dois biomas o processo chegou a cerca de 562 MB sem webcam e 767 MB com webcam. Descarte de caches e resolução dos assets continuam no P1.
- **Abertura e primeiro uso:** o tempo de criação do App variou de 1,21 a 3,51 s nas execuções desta máquina; não se afirma um ganho fixo de carregamento. Primeiro quadro sem cache chegou a 425 ms em Manaus e 270 ms em Petrolina. São medidos separadamente dos quadros após preparação.
- **Rotas:** 4.000 mundos, 100 auditorias completas independentes e 80 percursos de 500 avanços passaram. A otimização por máscaras preservou exatamente as contagens/resultados das mesmas sementes. P95 de geração caiu de 19,19 para 1,30 ms; P99 foi 2,25 ms e máximo 16,50 ms. As três faixas e os três tipos de obstáculo continuam presentes na amostra.
- **Webcam real:** captura 640×480; 237 publicações em 8 s de amostragem, aproximadamente 29,6 inferências/s, sem erros e com encerramento confirmado. A primeira publicação demorou 8,1 s nesse teste. A execução com cadência e renderização publicou 1.373 resultados, também sem erros.
- **Idade do resultado:** no teste com cadência, o último snapshot disponível ao terminar o quadro teve P95 de 78–79 ms. Isso é distinto da leitura efetivamente consumida, cuja métrica foi integrada à calibração e verificada por testes de sequência/relógio. O relógio monotônico deste Python/Windows tem resolução declarada de 15,625 ms; não há precisão física submilissegundo.

Os testes automatizados cobrem reabertura sem capturas concorrentes, desconexão/retomada, leituras antigas, saída normal e via recalibração, crédito único, retry de save, geometria, recursos gráficos e compatibilidade do cartucho. O self-test carrega o detector de pose, sem abrir a webcam; captura real é validada pelas ferramentas separadas.

## Limites do aceite

- Benchmark usa renderização CPU com SDL dummy, sem sincronização do monitor. Mede custo de processamento, não latência física movimento–imagem ou fps garantidos em outro computador.
- O teste com câmera confirma leitura/inferência e encerramento; não avalia a qualidade de reconhecer cada segmento de uma pessoa. Não grava imagens nem landmarks.
- A rota de referência valida um modelo conservador de movimento e colisão, não conforto individual nem todos os comandos possíveis. A pessoa ainda pode escolher um caminho que colide.
- A pré-carga é cooperativa: uma tarefa indivisível pode ultrapassar a folga. Os picos permanecem expostos no relatório.
- A liquidação protege a saída normal e a tentativa de salvar novamente. Encerrar o processo à força, perder energia ou continuar com falha de armazenamento não equivale a um checkpoint recuperável.
- O check do SDK e a construção do cartucho não substituem rodá-lo no T-TEA físico. Permanecem necessários ensaios de projeção, movimentos reais dos seis segmentos e uso mediado com crianças.

## Próximos trabalhos

Os P1 incluem sessões curtas e exploração sem eliminação, compatibilizar objetivos e lições iniciais, balanceamento com partidas reais, recuperação de save e ensaios longos. Refatoração ampla, formatação global, cobertura, empacotamento de imagens e CI de builds estão no P2. Não houve exclusão de branches/releases históricas nem reescrita do histórico Git.
