# Audio do Dobramundo

Todos os arquivos desta pasta sao gerados por `tools/make_audio.py`, por sintese com numpy (sem samples externos). Mono, 22050 Hz.

## Regenerar

Na raiz do projeto:

    .venv\Scripts\python.exe tools\make_audio.py
    .venv\Scripts\python.exe tools\make_audio.py --only sfx
    .venv\Scripts\python.exe tools\make_audio.py --out assets\audio --only musica

Requer numpy. Para gravar OGG Vorbis, precisa de `soundfile`; sem ele o script grava WAV 16-bit.

## Conteudo

- `musica_*.ogg`: loops de 16 compassos (vila, Amazonia e Caatinga, com 3 estagios cada). Cada bioma usa a mesma tonalidade e o mesmo andamento, para crossfade.
- `sfx_*.ogg`: efeitos curtos de coleta, interface e fases.

## Licenca

Gerado pelo projeto; mesma licenca do codigo do Dobramundo.
