"""Modelagem low-poly por código e renderização em sprites (sem Blender).

    mesh.py     malha de triângulos coloridos + primitivas (caixa, cilindro, esfera...)
    raster.py   rasterizador numpy (vista 3/4, luz difusa) -> PNG RGBA e mapa de partes
    models_*.py catálogos de modelos (Amazônia, Caatinga, comuns, piloto)

Os sprites gerados seguem a mesma câmera e a mesma luz dos sprites já existentes
do jogo (tools/legado/render_models.py), para que tudo pareça do mesmo mundo.
"""
