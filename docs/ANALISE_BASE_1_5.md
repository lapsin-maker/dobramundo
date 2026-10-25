# Análise consolidada — experiência, desempenho e entrega

Base: revisão da main `4a650b2`, análise externa `analise-repositorio-dobramundo.md` fornecida pelo usuário em 25/10/2026 e teste relatado com webcam. A análise externa foi usada como evidência a conferir; suas estimativas não são resultados desta implementação.

## P0 autorizados nesta entrega

| Item | Escopo de implementação e aceite |
|---|---|
| Câmera robusta | Encerrar sem bloquear a interface, manter fonte até liberação, reabrir sem duas capturas concorrentes; testar falha/desconexão. |
| Latência mensurável | Tempos de leitura, inferência, publicação, idade/cadência; relatório local sem imagens nem landmarks. Timestamp de retorno da leitura não equivale ao instante físico do sensor. |
| Recompensa ao interromper | Resultado parcial, crédito uma única vez, histórico, fechamento normal e tentativa de salvar novamente; sem conceder conclusão/estrela que não foi conquistada. |
| Orçamento de quadro | Medir componentes e memória; corrigir carregamento do piloto, custo do terreno, composição de horizonte, buffers e aquecimento. Comparar CPU sem câmera e com câmera disponível. |
| Sequências alcançáveis | Geração e auditoria determinística sob limites explícitos de manobra/reação; preservar variedade. Alcance matemático não prova conforto motor de cada pessoa. |
| Conforto sem compras | Sensibilidade, zona morta, resposta e tolerância disponíveis independentemente dos recursos. Peças preservam coleções, saves e requisitos de progressão, com textos coerentes. |

## Achados do anexo incorporados

Os seis P0 acima foram implementados. A entrega passou por 446 testes, CI em Python 3.8/3.12, auditoria de 4.000 sementes e medição com webcam local. As [notas e métricas da versão 1.5](ENTREGA_1_5.md) registram picos, carregamento inicial, memória acumulada e o aceite presencial ainda necessário.

| Achado | Conferência / encaminhamento |
|---|---|
| Piloto decodifica toda a pasta aquarela | Confirmado: 39 imagens, 245.378.820 bytes de superfícies dessa pasta na abertura. Baseline local: 2.793,9 ms para criar App e incremento de RSS de 377.925.632 bytes. Corrigido com seleção explícita das camadas do piloto. |
| Chão é o maior custo recorrente | Baseline instrumentado: mediana de 4,697 ms no chão de Manaus normal. Otimizar sem interromper avanço nem congelar faixas entre quadros. |
| Fundos opacos tratados como RGBA | Confirmado no loader. Detectar opacidade real uma vez e conservar alfa em sprites com transparência, inclusive furos interiores. |
| Composição da transição | Recalcular apenas região visível acima do terreno quando há percurso pintado; ignorar alfa zero e copiar diretamente alfa cheio. O fallback mantém composição integral. |
| Alto contraste | A escala rápida da sprint3 já está na main. Reutilizar buffers cinza; não cachear indefinidamente um fundo que está se movendo. |
| README e release difíceis de encontrar | Reorganizar a entrada do projeto, preservar manual/histórico em documentos próprios e identificar a entrega como 1.5.0. |
| Lint divergente | Excluir ferramentas legadas do escopo ativo e alinhar comando da CI ao README. A formatação global permanece separada das correções funcionais. |
| Python do console | SDK instalado confirma `requires-python >=3.14`; código portável continua testado em 3.8/3.12. São contratos distintos, agora descritos explicitamente. |
| Repositório público | Confirmado com GitHub CLI nesta revisão; nenhum ajuste de visibilidade foi feito. |

As medições do anexo (inclusive ganhos previstos de 30–50%, 240 MB e imagens de 20–25 MB) permanecem atribuídas à análise externa. Só o relatório desta entrega pode confirmar ganhos obtidos aqui.

## P1 — experiência e engenharia a seguir

- Sessões curtas, exploração sem eliminação e assistência opcional com mudanças previsíveis.
- Coordenar a primeira missão com as lições iniciais e garantir oferta dos objetivos sorteados.
- Balancear economia por tempo real, erros e interrupções; a simulação invencível não basta.
- Validar profundidade/vãos/altura e compreensão sem leitura na projeção e nos seis controles.
- Preparação de assets por tamanho de uso; memória por cena e descarte seletivo medido.
- Recuperação de último save válido e perfis de desktop compartilhado.
- Testes longos, latência no equipamento de destino, desconexão física e uso mediado com crianças.

## P2 — manutenção e evolução incorporadas do anexo

- Refatorar funções longas por camada e seção; manter a cadeia pintado → papel → lógico como fallback documentado. Imports locais nem sempre são ciclos: alguns evitam dependências opcionais no console.
- Auditar referências antes de remover funções apontadas como mortas. Não apagar renderizadores de reserva.
- Consolidar fontes, ajuste de texto, constantes e interface pública de entrada; documentar contratos do motor.
- Organizar testes por comportamento, reduzir helpers duplicados e medir cobertura sem usar percentual como prova de qualidade.
- Fixar dependências de CI por versão de Python. **Não aplicar cegamente `constraints-build.txt` a Python 3.8:** o conjunto do build 3.12 contém pacotes incompatíveis com o piso antigo.
- Formatação global em mudança própria, seguida de verificação na CI; build automatizado em Windows/Linux e cache de dependências.
- Testar suporte real do console antes de converter para WebP/JPEG. Menor tamanho comprimido não significa menor superfície decodificada em RAM.
- Atlas, pivôs e resolução de uso padronizados; preservar originais e manifestos de procedência. Não reescrever o histórico Git para recuperar espaço.
- Ajustar descrição, tópicos e prévia social se desejado. Exclusão de branches/releases históricas e configuração de exclusão automática ficam fora desta correção P0.
- Variações regionais de percurso, usos comunitários e desafios com sementes reproduzíveis.

## Critério de conclusão

Código testado, documentação coerente, pacotes identificados e rastreáveis. Testes automatizados, captura instrumentada e benchmark de CPU serão distinguidos do aceite presencial. Não será declarada latência física de movimento, eficácia terapêutica ou 60 fps garantidos em outro equipamento a partir de testes sintéticos.
