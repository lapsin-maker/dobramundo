# Roteiro de aceite no equipamento de destino

Este documento não registra um ensaio já realizado. Os testes automatizados
exercitam coordenadas, projeção, estado, renderização e falhas sintéticas. As
linhas abaixo exigem observação no equipamento e com participantes disponíveis.
Não preencher como aprovado a partir do self-test ou de captura estática.

## Preparar uma sessão

Escolher um slot de piloto de teste, o segmento de controle e uma duração curta.
Calibrar a postura neutra e os quatro extremos confortáveis. Registrar apenas
modelo do computador/projetor, resolução, superfície, iluminação, versão,
modo de contraste, duração e resultado agregado. Não gravar vídeo, landmarks,
nome ou diagnóstico da criança nesta ficha.

| Ensaio | Observar | Critério de aceite | Estado |
|---|---|---|---|
| Chão, mesa, parede e monitor | Avião, resíduos, obstáculos e cenário a 2–3 m | Participante distingue o que coletar, evitar e usar como passagem sem ler legenda | Pendente presencial |
| Profundidade e altura | Resíduo perto/longe, obstáculo baixo e passagem sob portal | Gesto e efeito correspondem; nenhuma colisão parece ocorrer fora do objeto | Pendente presencial |
| Seis controles | Pés, tronco em pé/sentado, mão direita/esquerda, cabeça | Alcance confortável chega aos quatro extremos e a todos os botões; perda de rastreamento pausa | Pendente presencial |
| Projeção | Quatro rotações, espelho e calibração dos cantos | Posição projetada coincide com área de interação; bordas não cortam avião | Pendente presencial |
| Webcam | Virar cabeça e sair/voltar ao enquadramento; retirar/reconectar cabo pelo operador | Sem movimento fantasma, interface responsiva, reabertura única, recalibração clara | Pendente físico |
| Exploração e assistência | Erros, pausas e término curto | Ajuda permanece previsível; sem eliminação no modo exploração; conquistas preservadas | Pendente com participante |
| Menus | Escolher aparência, trocar opções e retirar o cursor | Nenhuma confirmação involuntária em sequência; alvo e progresso de permanência compreensíveis | Pendente com participante |
| Cantos no chão | Aproximar um pé de cada borda com o outro mais para dentro; apontar aos quatro cantos e voltar ao centro | Cursor chega aos botões extremos sem exigir ambos os pés fora da projeção; indicador coincide com seleção; perda de leitura suspende permanência | Pendente console/webcam |
| Primeira visita às cidades | Abrir mapa com piloto novo e zero estrelas | Manaus e Petrolina podem ser escolhidas em qualquer ordem | Pendente com participante |
| Transformação | Estado industrial colorido, etapa intermediária, solarpunk | Participante reconhece a relação entre coleta/obra e a mudança na vila | Pendente com participante |
| Ritmo da paisagem | Observar 15, 30 e 60 segundos ativos, com poucas coletas e com pausas | Mudança de poluição/natureza já perceptível durante o primeiro minuto; pausa e preparação não avançam a transformação | Pendente com participante |
| Continuidade entre voos | Encerrar aos 30–60 s e decolar de novo | A paisagem mantém o progresso, vidas recomeçam e a criança entende que iniciou outro voo | Pendente com participante |
| História inicial | Criar piloto, acompanhar/pular jornal, reabrir o jogo | Ordem compreensível, Pular acessível e história não se repete sem pedido | Pendente com participante |
| Alto contraste ampliado | Escalas 1,0, 1,3 e 1,6, avião nos quatro extremos | Indicadores de borda antecipam ameaças sem distrair ou esconder o caminho | Pendente com participante |
| Pequenas missões | Observar a barra discreta e a troca após o prazo | Troca percebida sem sensação de perda de recursos ou pressão de tempo | Pendente com participante |
| Uso prolongado | 20–30 min no equipamento de destino, alternando biomas e alto contraste | Sem aumento contínuo de memória, congelamentos ou perda de salvamento | Pendente físico |
| Console T-TEA | Instalar cartucho, abrir, trocar cena, concluir e reabrir sessão | Assets PNG decodificados, perfil do SDK preservado, resumo registrado uma vez | Pendente console |

Se uma etapa falhar, registrar o gesto/situação, sem dados pessoais. A semente
fica no histórico técnico; o resultado só a mostra em desafios. Voar de novo
mantém a semente e as opções, mas parte da cidade já transformada. Isso ajuda
a investigar o percurso, sem prometer a reprodução exata da partida anterior.

## Evidência técnica disponível

Os comandos de `tools/README.md` geram relatório de desempenho, estabilidade,
rotas e economia em pasta isolada. `benchmark_camera.py` mede captura e inferência
reais sem armazenar pixels; a medição começa após aquecimento. O timestamp de
retorno da leitura não mede a exposição do sensor, e canvas pronto não mede o
instante de luz emitida pelo projetor. Portanto, esses números não comprovam
latência física ponta a ponta nem o conforto de uma criança.

Codecs opcionais: o suporte depende da compilação do SDL_image, conforme a
[documentação do pygame](https://www.pygame.org/docs/ref/image.html). A entrega
continua em PNG; converter no desktop não comprova suporte no console.
