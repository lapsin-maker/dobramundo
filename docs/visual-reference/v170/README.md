# Referências visuais 1.7

Quatro páginas de Opções, revisadas em 25/10/2026. Captura em 1100 × 650, pygame 2.6.1, fontes embutidas, `SDL_VIDEODRIVER=dummy` e perfil sintético, com `tools/capture_release.py --reference`. Redução de movimento elimina variação de câmera decorativa.

`tools/visual_regression.py` exige dimensões iguais, erro médio absoluto por canal até 1 e no máximo 1% dos pixels com diferença acima de 32. Isso detecta perda de botões/layout e tolera pequenas diferenças de rasterização. Atualizar estes PNGs exige inspeção visual; não regenere a referência apenas para silenciar uma falha do CI.

Voos e transições são conferidos separadamente pela galeria temporal, testes geométricos e métricas. Estes quatro menus não validam conforto de controle ou leitura no projetor.
