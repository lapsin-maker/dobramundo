# Ferramentas herdadas do protótipo (Eco Runner)

Estes scripts geraram os assets do protótipo e ficam aqui para registro da
proveniência. Eles dependem de arquivos que **não estão neste repositório**:

| Script | O que gerou | Precisa de |
|---|---|---|
| `render_models.py` | sprites dos kits Dieselpunk e EcoUrbe (`dieselpunk_sprites`, `scenario_sprites`, `skyline_sprites`, `atmosphere`) | pasta `modelos_3d` com os OBJ/MTL da equipe |
| `extract_planes.py` | os 11 aviões em 6 camadas (`plane_*`), padrões e `catalog.json` | HTML do "Estúdio 3D Aviões, 14-Bis & Piloto", Playwright e Chromium |
| `extract_maneuvers.py` | `assets/maneuvers/maneuvers.json` | animações glTF do estúdio |
| `make_concrete_texture.py` | `assets/ground/concrete.png` | só numpy e Pillow |

Atenção: rodar `render_models.py` sobrescreve sprites que depois foram
substituídos por versões revisadas da equipe (`fabrica`, `chamine`, `tambores`,
`cacamba`). Use `--out` para gravar numa pasta separada.

Os assets novos do Dobramundo (biomas, resíduos, vila, piloto) são gerados por
`tools/build_assets.py`, que não depende de nada externo.
