#!/usr/bin/env python3
"""Sintetiza a trilha e os efeitos sonoros do jogo Dobramundo.

Tudo e gerado por sintese com numpy (osciladores, envelopes ADSR, filtros no
dominio da FFT, reverb por linhas de atraso), sem samples externos. A semente
e fixa, entao a saida e deterministica.

Uso:
    python tools/make_audio.py [--out assets/audio] [--only musica|sfx]

Cada musica e um loop de 16 compassos renderizado como buffer periodico: notas
que passam do fim voltam ao inicio, e filtros e reverb sao circulares. Assim a
emenda do loop nao tem salto nem clique.
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

SR = 22050
SEMENTE = 20261024
COMPASSOS = 16
TEMPOS = 4  # tempos por compasso (4/4)
PICO_MUSICA_DB = -3.0
RMS_MUSICA_DB = -18.0
PICO_SFX_DB = -8.0

Onda = np.ndarray

# Escalas (graus em semitons a partir da tonica)
ESC_MENOR_PENT = [0, 3, 5, 7, 10]
ESC_MAIOR_PENT = [0, 2, 4, 7, 9]
ESC_DORICO = [0, 2, 3, 5, 7, 9, 10]
ESC_MIXOLIDIO = [0, 2, 4, 5, 7, 9, 10]

# Progressoes (um acorde por compasso, MIDI); 4 acordes ciclam nos 16 compassos
PROG_VILA = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]  # C Am F G
PROG_AMAZ_MENOR = [[50, 53, 57], [46, 50, 53], [48, 52, 55], [50, 53, 57]]  # Dm Bb C Dm
PROG_AMAZ_MAIOR = [[50, 54, 57], [55, 59, 62], [57, 61, 64], [50, 54, 57]]  # D G A D
PROG_CAA_MENOR = [[57, 60, 64], [50, 53, 57], [55, 59, 62], [52, 56, 59]]  # Am Dm G E
PROG_CAA_MAIOR = [[57, 61, 64], [50, 54, 57], [55, 59, 62], [52, 56, 59]]  # A D G E

# Frases melodicas de 4 compassos (tempo dentro da frase, duracao, grau)
FRASE_VILA = [
    (0, 1.5, 2),
    (1.5, 0.5, 1),
    (2, 2, 0),
    (4, 1, 1),
    (5, 1, 2),
    (6, 2, 3),
    (8, 1, 4),
    (9, 1, 3),
    (10, 2, 2),
    (12, 1, 1),
    (13, 1, 0),
    (14, 2, -1),
]
FRASE_TOADA = [
    (0, 1, 0),
    (1, 1, 2),
    (2, 2, 3),
    (4, 1, 2),
    (5, 1, 1),
    (6, 2, 0),
    (8, 1, 4),
    (9, 1, 3),
    (10, 1, 2),
    (11, 1, 1),
    (12, 2, 0),
    (14, 2, -1),
]
FRASE_BAIAO = [
    (0, 0.5, 4),
    (0.5, 0.5, 5),
    (1, 1, 4),
    (2, 1, 2),
    (3, 1, 0),
    (4, 1.5, 0),
    (5.5, 0.5, 1),
    (6, 2, 2),
    (8, 0.5, 4),
    (8.5, 0.5, 5),
    (9, 1, 6),
    (10, 1, 5),
    (11, 1, 4),
    (12, 1, 2),
    (13, 1, 0),
    (14, 2, -1),
]


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def hz(midi: float) -> float:
    """Converte nota MIDI em frequencia (Hz); 69 = 440 Hz."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def eixo(n: int) -> Onda:
    """Eixo de tempo em segundos com n amostras."""
    return np.arange(n) / SR


def secs(segundos: float) -> int:
    """Converte segundos em numero de amostras."""
    return int(round(segundos * SR))


def rng_para(desloc: int) -> np.random.Generator:
    """Gerador pseudoaleatorio determinstico derivado da semente fixa."""
    return np.random.default_rng(SEMENTE + desloc)


def db(valor: float) -> float:
    """Converte amplitude linear em dBFS."""
    return 20.0 * np.log10(max(float(valor), 1e-12))


def medidas(x: Onda) -> Tuple[float, float, float]:
    """Retorna (duracao em s, pico em dBFS, RMS em dBFS)."""
    pico = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x * x)))
    return len(x) / SR, db(pico), db(rms)


def adsr(n: int, ataque: float, decaimento: float, sustentacao: float, liberacao: float) -> Onda:
    """Envelope ADSR com n amostras; tempos em segundos.

    A liberacao ocupa o final do array e termina em zero.
    """
    a = min(n, max(1, secs(ataque)))
    d = min(n - a, secs(decaimento))
    r = min(n - a - d, secs(liberacao))
    s = n - a - d - r
    return np.concatenate(
        [
            np.linspace(0.0, 1.0, a, endpoint=False),
            np.linspace(1.0, sustentacao, d, endpoint=False),
            np.full(s, sustentacao),
            np.linspace(sustentacao, 0.0, r),
        ]
    )


def bordas(x: Onda, ataque: float = 0.006, cauda: float = 0.05) -> Onda:
    """Fade-in de ~6 ms e fade-out de ~50 ms (cos^2): evita cliques."""
    y = np.asarray(x, dtype=np.float64).copy()
    a = min(len(y) // 2, secs(ataque))
    c = min(len(y) // 2, secs(cauda))
    if a > 0:
        y[:a] *= np.sin(np.linspace(0.0, np.pi / 2, a)) ** 2
    if c > 0:
        y[-c:] *= np.cos(np.linspace(0.0, np.pi / 2, c)) ** 2
    return y


def passa_baixa(x: Onda, corte: float, ordem: int = 2) -> Onda:
    """Filtro passa-baixa de fase zero (magnitude Butterworth) no dominio da FFT.

    Para buffers periodicos o resultado e circular, portanto sem bordas.
    """
    n = len(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    mascara = 1.0 / np.sqrt(1.0 + (freqs / corte) ** (2 * ordem))
    return np.fft.irfft(np.fft.rfft(x) * mascara, n)


def ruido_banda(rng: np.random.Generator, n: int, lo: float, hi: float) -> Onda:
    """Ruido branco filtrado entre lo e hi (Hz), normalizado para RMS 1."""
    espectro = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    y = np.fft.irfft(espectro * ((freqs >= lo) & (freqs <= hi)), n)
    return y / (np.sqrt(np.mean(y * y)) + 1e-12)


def limita(x: Onda, teto: float, joelho: float = 0.7) -> Onda:
    """Limitador suave: linear ate o joelho e tanh acima, sem passar do teto."""
    k = teto * joelho
    a = np.abs(x)
    comp = k + (teto - k) * np.tanh((a - k) / (teto - k))
    return np.sign(x) * np.where(a > k, comp, a)


def ajusta_musica(x: Onda) -> Onda:
    """Normaliza o RMS para -18 dBFS e garante pico abaixo de -3 dBFS."""
    y = x - np.mean(x)
    teto = 10.0 ** ((PICO_MUSICA_DB - 0.25) / 20.0)
    for _ in range(4):
        rms = np.sqrt(np.mean(y * y))
        y = y * (10.0 ** (RMS_MUSICA_DB / 20.0) / rms)
        y = limita(y, teto)
    return y


def polir(x: Onda, nivel_db: float = PICO_SFX_DB) -> Onda:
    """Aplica bordas (ataque >= 5 ms, cauda suave) e normaliza o pico do efeito."""
    y = bordas(x, 0.006, 0.03)
    return y * (10.0 ** (nivel_db / 20.0) / np.max(np.abs(y)))


def junta(partes: Sequence[Tuple[float, Onda]]) -> Onda:
    """Soma sinais em instantes (segundos) dentro de um unico buffer."""
    fim = max(secs(off) + len(s) for off, s in partes)
    y = np.zeros(fim)
    for off, s in partes:
        i = secs(off)
        y[i : i + len(s)] += s
    return y


# ---------------------------------------------------------------------------
# Reverb por linhas de atraso (IR) e convolucao circular
# ---------------------------------------------------------------------------


def ir_reverb(
    rng: np.random.Generator,
    dur: float = 1.5,
    atrasos: Sequence[float] = (0.0297, 0.0371, 0.0411, 0.0437, 0.0533, 0.0619),
    realimentacao: float = 0.8,
) -> Onda:
    """Resposta ao impulso gerada por linhas de atraso com realimentacao.

    Cada linha produz ecos em k*atraso com ganho realimentacao^k e sinal
    aleatorio; a soma e suavizada por passa-baixa e normalizada em energia.
    """
    tam = secs(dur)
    ir = np.zeros(tam)
    for atraso in atrasos:
        d = secs(atraso)
        k = 0
        while k * d < tam and realimentacao**k > 1e-3:
            sinal = 1.0 if rng.random() < 0.5 else -1.0
            ir[k * d] += sinal * realimentacao**k
            k += 1
    ir = passa_baixa(ir, 3500.0)
    return ir / np.sqrt(np.sum(ir * ir))


def reverbera(x: Onda, ir: Onda, mix: float) -> Onda:
    """Mistura seco/umido com convolucao circular (preserva o loop)."""
    n = len(x)
    h = np.zeros(n)
    h[: len(ir)] = ir
    wet = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h), n)
    return (1.0 - mix) * x + mix * wet


# ---------------------------------------------------------------------------
# Osciladores e instrumentos (todos recebem frequencia e numero de amostras)
# ---------------------------------------------------------------------------


def fase_vibrato(freq: float, n: int, taxa: float = 0.0, profundidade: float = 0.0) -> Onda:
    """Fase acumulada de uma senoide com vibrato leve."""
    t = eixo(n)
    f = freq * (1.0 + profundidade * np.sin(2.0 * np.pi * taxa * t))
    return 2.0 * np.pi * np.cumsum(f) / SR


def modos(freq: float, n: int, razoes: Sequence[float], amps: Sequence[float], taus: Sequence[float]) -> Onda:
    """Soma de parciais com decaimento exponencial (cordas, lamina, sinos)."""
    t = eixo(n)
    y = np.zeros(n)
    for r, a, tau in zip(razoes, amps, taus):
        y += a * np.sin(2.0 * np.pi * freq * r * t) * np.exp(-t / tau)
    return y


def sino_suave(freq: float, n: int) -> Onda:
    """Senoide com leve segundo parcial e ataque macio."""
    fa = 2.0 * np.pi * freq * eixo(n)
    return (np.sin(fa) + 0.15 * np.sin(2 * fa)) * adsr(n, 0.006, 0.0, 1.0, 0.12)


def kalimba(freq: float, n: int) -> Onda:
    """Lamela pinçada: parcial fundamental longo e parciais curtos."""
    return modos(freq, n, [1, 2.8, 5.4], [1, 0.12, 0.03], [0.8, 0.12, 0.03]) * 0.7


def violao(freq: float, n: int) -> Onda:
    """Corda pinçada sintetica (serie harmonica com decaimento por parcial)."""
    return modos(freq, n, [1, 2, 3, 4], [1, 0.45, 0.2, 0.08], [0.5, 0.25, 0.12, 0.06]) * 0.6


def flauta(freq: float, n: int) -> Onda:
    """Flauta suave: senoide com vibrato lento e ataque de 80 ms."""
    fase = fase_vibrato(freq, n, 5.2, 0.004)
    return (np.sin(fase) + 0.12 * np.sin(2 * fase)) * adsr(n, 0.08, 0.0, 1.0, 0.2)


def sanfona(freq: float, n: int, corte: float = 2200.0) -> Onda:
    """Sanfona: dente-de-serra por serie de Fourier, filtrada e com vibrato."""
    fase = fase_vibrato(freq, n, 5.5, 0.005)
    y = np.zeros(n)
    k = 1
    while k * freq < 3.0 * corte:
        y += ((1.0 / k) / (1.0 + (k * freq / corte) ** 4)) * np.sin(k * fase)
        k += 1
    return y * 0.45 * adsr(n, 0.05, 0.1, 0.85, 0.12)


def metal(freq: float, n: int) -> Onda:
    """Timbre metalico e mecanico: harmonicos impares com par desafinado."""
    t = eixo(n)
    fa = 2.0 * np.pi * freq * t
    fb = fa * 1.006
    y = np.zeros(n)
    for k in (1, 3, 5, 7):
        y += (np.sin(k * fa) + 0.8 * np.sin(k * fb)) / k
    return y * 0.25 * adsr(n, 0.008, 0.15, 0.55, 0.15)


def pad(freq: float, n: int) -> Onda:
    """Nota de acompanhamento macia, com ataque lento."""
    fa = 2.0 * np.pi * freq * eixo(n)
    y = np.sin(fa) + 0.3 * np.sin(2 * fa) + 0.1 * np.sin(3 * fa)
    return y * adsr(n, 0.28, 0.1, 0.9, 0.5) * 0.4


def baixo_nota(freq: float, n: int) -> Onda:
    """Baixo suave com senoide e segundo parcial."""
    fa = 2.0 * np.pi * freq * eixo(n)
    return (np.sin(fa) + 0.2 * np.sin(2 * fa)) * adsr(n, 0.012, 0.25, 0.55, 0.2) * 0.6


def tri(freq: float, n: int) -> Onda:
    """Tom de triangulo (harmonicos impares 1/k^2), usado em fanfarra e game over."""
    fa = 2.0 * np.pi * freq * eixo(n)
    y = np.sin(fa) + np.sin(3 * fa) / 9.0 + np.sin(5 * fa) / 25.0
    return y * adsr(n, 0.01, 0.0, 1.0, 0.3) * 0.7


def acorde_puro(midis: Sequence[int], n: int, ataque: float, liberacao: float) -> Onda:
    """Acorde de senoides com envelope ADSR simples."""
    t = eixo(n)
    y = sum(np.sin(2.0 * np.pi * hz(m) * t) for m in midis) / len(midis)
    return y * adsr(n, ataque, 0.0, 1.0, liberacao)


def zabumba(n: int, f0: float = 95.0, f1: float = 52.0, tau_f: float = 0.03, tau_a: float = 0.12) -> Onda:
    """Bumbo/tambor grave: senoide com queda de altura e decaimento."""
    t = eixo(n)
    fase = 2.0 * np.pi * (f1 * t + (f0 - f1) * tau_f * (1.0 - np.exp(-t / tau_f)))
    return np.sin(fase) * np.exp(-t / tau_a)


def tambor_grave(n: int) -> Onda:
    """Tambor grave suave (carimbo/toada)."""
    return zabumba(n, 78.0, 46.0, 0.02, 0.18) * 0.8


def zabumba_baiao(n: int) -> Onda:
    """Zabumba suave do baiao."""
    return zabumba(n, 98.0, 55.0, 0.03, 0.14) * 0.9


def triangulo(n: int) -> Onda:
    """Triangulo de percussao: parciais inarmonicos curtos."""
    return modos(1480.0, n, [1, 2.76, 5.4], [1, 0.25, 0.07], [0.45, 0.12, 0.05]) * 0.8


def maraca(n: int, rng: np.random.Generator) -> Onda:
    """Maraca: ruido de faixa alta com decaimento curto."""
    return ruido_banda(rng, n, 5200.0, 8800.0) * np.exp(-eixo(n) / 0.028)


def pulso_maquina(n: int, rng: np.random.Generator) -> Onda:
    """Pulso de maquina abafado (estagio industrial)."""
    t = eixo(n)
    fase = 2.0 * np.pi * (58.0 * t + 32.0 * 0.02 * (1.0 - np.exp(-t / 0.02)))
    return np.sin(fase) * np.exp(-t / 0.05) + 0.4 * ruido_banda(rng, n, 160.0, 650.0) * np.exp(-t / 0.02)


def passaro(n: int, rng: np.random.Generator) -> Onda:
    """Gorjeio: glissando curto e agudo com envelope."""
    f0 = rng.uniform(2300.0, 2900.0)
    f1 = f0 * rng.uniform(1.25, 1.5)
    t = eixo(n)
    f = f0 + (f1 - f0) * np.clip(t / max(n / SR, 1e-6), 0.0, 1.0)
    fase = 2.0 * np.pi * np.cumsum(f) / SR
    return np.sin(fase) * adsr(n, 0.01, 0.0, 1.0, 0.05) * 0.8


# ---------------------------------------------------------------------------
# Faixa: barramento periodico de 16 compassos (um ciclo exato do loop)
# ---------------------------------------------------------------------------


class Faixa:
    """Buffer periodico: cada nota que passa do fim volta ao inicio."""

    def __init__(self, bpm: float) -> None:
        self.bpm = float(bpm)
        self.n = int(round(COMPASSOS * TEMPOS * 60.0 / self.bpm * SR))
        self.buf = np.zeros(self.n)

    def amostras(self, dur_tempos: float, cauda: float = 0.3) -> int:
        """Numero de amostras de uma nota de dur_tempos mais a cauda (s)."""
        n = secs(dur_tempos * 60.0 / self.bpm + cauda)
        return min(n, self.n)

    def soma(self, beat: float, sinal: Onda, vel: float = 1.0) -> None:
        """Soma um sinal (com bordas) a partir do tempo beat, em modo circular."""
        sinal = bordas(sinal) * vel
        inicio = int(round(beat * 60.0 / self.bpm * SR))
        idx = (np.arange(len(sinal)) + inicio) % self.n
        self.buf[idx] += sinal

    def nota(
        self,
        beat: float,
        dur: float,
        instr: Callable[[float, int], Onda],
        freq: float,
        vel: float = 1.0,
        cauda: float = 0.3,
    ) -> None:
        """Toca uma nota de instrumento com frequencia fixa."""
        self.soma(beat, instr(freq, self.amostras(dur, cauda)), vel)

    def golpe(
        self, beat: float, func: Callable[[int], Onda], vel: float = 1.0, dur: float = 0.5, cauda: float = 0.3
    ) -> None:
        """Dispara um golpe de percussao (func recebe apenas n)."""
        self.soma(beat, func(self.amostras(dur, cauda)), vel)


def misturar(barras: Sequence[Tuple[Faixa, float, Optional[float], float]], rng: np.random.Generator) -> Onda:
    """Mixa barramentos: (faixa, ganho, corte Hz ou None, mix de reverb)."""
    ir = ir_reverb(rng)
    saida: Optional[Onda] = None
    for faixa, ganho, corte, wet in barras:
        x = faixa.buf
        if corte:
            x = passa_baixa(x, corte)
        if wet > 0.0:
            x = reverbera(x, ir, wet)
        saida = ganho * x if saida is None else saida + ganho * x
    assert saida is not None
    return saida


def toca_frase(
    faixa: Faixa,
    frase: Sequence[Tuple[float, float, int]],
    escala: Sequence[int],
    raiz: int,
    instr: Callable[[float, int], Onda],
    vel: float,
    cauda: float,
    desloc: Sequence[int] = (0, 1, 2, 0),
    soma_grau: int = 0,
    filtro: Optional[Callable[[float, float], bool]] = None,
) -> None:
    """Toca a frase de 4 compassos nos 16 compassos, com transposicao por bloco."""
    for bloco, deslo in enumerate(desloc):
        inicio = bloco * 4 * TEMPOS
        for beat, dur, grau in frase:
            if filtro is not None and not filtro(beat, dur):
                continue
            g = grau + deslo + soma_grau
            midi = raiz + escala[g % len(escala)] + 12 * (g // len(escala))
            faixa.nota(inicio + beat, dur, instr, hz(midi), vel, cauda)


def acordes(
    faixa: Faixa,
    progressao: Sequence[Sequence[int]],
    instr: Callable[[float, int], Onda],
    vel: float,
    cauda: float = 0.5,
) -> None:
    """Um acorde por compasso (4 tempos), distribuindo o volume entre as notas."""
    for c in range(COMPASSOS):
        acorde = progressao[c % len(progressao)]
        for m in acorde:
            faixa.nota(c * TEMPOS, TEMPOS, instr, hz(m), vel / len(acorde), cauda)


def baixo_raiz(
    faixa: Faixa,
    progressao: Sequence[Sequence[int]],
    batidas: Sequence[float],
    vel: float,
    instr: Callable[[float, int], Onda] = baixo_nota,
) -> None:
    """Nota da fundamental (uma oitava abaixo do acorde) nas batidas indicadas."""
    for c in range(COMPASSOS):
        raiz = progressao[c % len(progressao)][0] - 12
        for b in batidas:
            faixa.nota(c * TEMPOS + b, 0.9, instr, hz(raiz), vel, 0.3)


def bateria(faixa: Faixa, padrao: Sequence[Tuple[float, float, Callable[[int], Onda]]]) -> None:
    """Repete um padrao de golpes (tempo no compasso, volume, funcao) em cada compasso."""
    for c in range(COMPASSOS):
        for beat, vel, func in padrao:
            faixa.golpe(c * TEMPOS + beat, func, vel)


# ---------------------------------------------------------------------------
# Musicas (loops de 16 compassos)
# ---------------------------------------------------------------------------


def compor_vila() -> Onda:
    """Tema calmo e acolhedor da vila: kalimba, violao e pad, em do maior."""
    bpm = 92
    melo, harm, viol, baixo = Faixa(bpm), Faixa(bpm), Faixa(bpm), Faixa(bpm)
    toca_frase(melo, FRASE_VILA, ESC_MAIOR_PENT, 72, kalimba, 0.5, 0.9)
    acordes(harm, PROG_VILA, pad, 0.5)
    for c in range(COMPASSOS):
        acorde = PROG_VILA[c % 4]
        for k in range(8):  # arpejo de colcheias no violao
            nota = acorde[[0, 1, 2, 1][k % 4]] + 12
            viol.nota(c * TEMPOS + k * 0.5, 0.5, violao, hz(nota), 0.6, 0.8)
    baixo_raiz(baixo, PROG_VILA, [0, 2], 0.5)
    return misturar(
        [(melo, 1.0, None, 0.25), (harm, 0.6, None, 0.3), (viol, 0.5, 3500.0, 0.15), (baixo, 0.5, 700.0, 0.0)],
        rng_para(1),
    )


def compor_amazonia(estagio: int) -> Onda:
    """Toada/carimbo de Manaus em re. Estagio 1 menor e mecanico; 3 maior e brilhante."""
    bpm = 96
    rng = rng_para(100 + estagio)
    ritmo, harm, baixo, melo, ambi = (Faixa(bpm) for _ in range(5))
    if estagio == 1:
        prog, escala, raiz = PROG_AMAZ_MENOR, ESC_MENOR_PENT, 62
    else:
        prog, escala, raiz = PROG_AMAZ_MAIOR, ESC_MAIOR_PENT, 74
    tambor = tambor_grave
    if estagio == 1:
        bateria(
            ritmo,
            [(0, 0.22, tambor), (2, 0.16, tambor)]
            + [(b, 0.09, lambda n: pulso_maquina(n, rng)) for b in (0.5, 1.5, 2.5, 3.5)],
        )
        acordes(harm, prog, pad, 0.4)
        baixo_raiz(baixo, prog, [0, 2], 0.22)
        toca_frase(melo, FRASE_TOADA, escala, raiz, metal, 0.22, 0.2, filtro=lambda b, d: d >= 1.0)
        barras = [
            (ritmo, 0.9, 1800.0, 0.05),
            (harm, 0.5, 900.0, 0.25),
            (baixo, 0.7, 500.0, 0.0),
            (melo, 0.9, 1500.0, 0.18),
        ]
    elif estagio == 2:
        bateria(
            ritmo,
            [(0, 0.42, tambor), (1.5, 0.22, tambor), (2, 0.36, tambor), (3.5, 0.22, tambor)]
            + [(k * 0.5, 0.10 if k % 2 == 0 else 0.16, lambda n: maraca(n, rng)) for k in range(8)],
        )
        acordes(harm, prog, pad, 0.36)
        baixo_raiz(baixo, prog, [0, 2], 0.26)
        toca_frase(melo, FRASE_TOADA, escala, raiz, flauta, 0.3, 0.3)
        for c in range(COMPASSOS):  # passaros esparsos
            if rng.random() < 0.5:
                for _ in range(int(rng.integers(1, 3))):
                    ambi.golpe(c * TEMPOS + rng.uniform(0.0, 3.2), lambda n: passaro(n, rng), 0.06, 0.2, 0.06)
        barras = [
            (ritmo, 0.9, None, 0.05),
            (harm, 0.45, None, 0.25),
            (baixo, 0.7, None, 0.0),
            (melo, 0.9, None, 0.22),
            (ambi, 0.6, None, 0.35),
        ]
    else:
        bateria(
            ritmo,
            [
                (0, 0.45, tambor),
                (0.75, 0.25, tambor),
                (1.5, 0.22, tambor),
                (2, 0.40, tambor),
                (2.75, 0.25, tambor),
                (3.5, 0.22, tambor),
            ]
            + [(k * 0.25, 0.07 if k % 2 else 0.11, lambda n: maraca(n, rng)) for k in range(16)],
        )
        acordes(harm, prog, pad, 0.4)
        baixo_raiz(baixo, prog, [0, 1, 2, 3], 0.2)
        toca_frase(melo, FRASE_TOADA, escala, raiz, kalimba, 0.42, 0.9)
        toca_frase(melo, FRASE_TOADA, escala, raiz, flauta, 0.12, 0.3)
        for c in range(COMPASSOS):
            if rng.random() < 0.35:
                ambi.golpe(c * TEMPOS + rng.uniform(0.0, 3.2), lambda n: passaro(n, rng), 0.05, 0.2, 0.06)
        barras = [
            (ritmo, 1.0, None, 0.05),
            (harm, 0.5, None, 0.3),
            (baixo, 0.8, None, 0.0),
            (melo, 1.0, None, 0.24),
            (ambi, 0.5, None, 0.35),
        ]
    return misturar(barras, rng)


def compor_caatinga(estagio: int) -> Onda:
    """Baiao/xote do Sertao (la). Estagio 1 dorico e esparso; 3 mixolidio e brilhante."""
    bpm = 100
    rng = rng_para(200 + estagio)
    ritmo, harm, baixo, melo = (Faixa(bpm) for _ in range(4))
    if estagio == 1:
        prog, escala, raiz = PROG_CAA_MENOR, ESC_DORICO, 57
        corte = 1400.0
    else:
        prog, escala, raiz = PROG_CAA_MAIOR, ESC_MIXOLIDIO, 69
        corte = 1800.0 if estagio == 2 else 2600.0
    sanf = lambda f, n: sanfona(f, n, corte)  # noqa: E731 - closure curta
    if estagio == 1:
        bateria(ritmo, [(0, 0.30, zabumba_baiao), (2, 0.20, zabumba_baiao), (1, 0.07, triangulo), (3, 0.07, triangulo)])
        acordes(harm, prog, sanf, 0.10)
        baixo_raiz(baixo, prog, [0, 2], 0.22)
        toca_frase(melo, FRASE_BAIAO, escala, raiz, sanf, 0.28, 0.25, filtro=lambda b, d: d >= 1.0)
        barras = [(ritmo, 0.9, 1800.0, 0.08), (harm, 0.5, None, 0.25), (baixo, 0.7, 600.0, 0.0), (melo, 0.9, None, 0.2)]
    else:
        gz = 1.1 if estagio == 3 else 1.0
        bateria(
            ritmo,
            [
                (0, 0.5 * gz, zabumba_baiao),
                (1.5, 0.28 * gz, zabumba_baiao),
                (2, 0.4 * gz, zabumba_baiao),
                (3.5, 0.25 * gz, zabumba_baiao),
            ]
            + [(k * 0.5, 0.09 if k % 2 == 0 else 0.13, triangulo) for k in range(8)],
        )
        for c in range(COMPASSOS):  # stabs de sanfona nos tempos
            acorde = prog[c % len(prog)]
            for b in (0.5, 1.5, 2.5, 3.5):
                for m in acorde:
                    harm.nota(c * TEMPOS + b, 0.45, sanf, hz(m), 0.08 / len(acorde), 0.2)
        baixo_raiz(baixo, prog, [0, 2], 0.24)
        toca_frase(melo, FRASE_BAIAO, escala, raiz, sanf, 0.32, 0.3)
        barras = [(ritmo, 0.9, None, 0.08), (harm, 0.45, None, 0.22), (baixo, 0.7, None, 0.0), (melo, 0.9, None, 0.2)]
        if estagio == 3:  # segunda voz de sanfona (terça acima)
            toca_frase(melo, FRASE_BAIAO, escala, raiz, sanf, 0.16, 0.3, soma_grau=2)
            barras[-1] = (melo, 1.0, None, 0.25)
    return misturar(barras, rng)


# ---------------------------------------------------------------------------
# Efeitos sonoros
# ---------------------------------------------------------------------------


def sfx_coleta_papel() -> Onda:
    """Farfalhar de papel seguido de nota suave."""
    rng = rng_para(301)
    n = secs(0.5)
    farfalho = ruido_banda(rng, n, 2000.0, 7000.0) * np.exp(-eixo(n) / 0.07)
    nota = modos(hz(84), secs(0.45), [1, 2], [1, 0.2], [0.25, 0.1])
    return junta([(0.0, 0.15 * farfalho), (0.05, 0.6 * nota)])


def sfx_coleta_plastico() -> Onda:
    """Pop macio: senoide com queda rapida de altura."""
    n = secs(0.22)
    t = eixo(n)
    fase = 2.0 * np.pi * np.cumsum(300.0 + 220.0 * np.exp(-t / 0.02)) / SR
    return passa_baixa(np.sin(fase) * np.exp(-t / 0.05), 1500.0)


def sfx_coleta_metal() -> Onda:
    """Sininho de metal."""
    return modos(hz(93), secs(0.9), [1, 2.76, 5.4, 8.9], [1, 0.2, 0.06, 0.02], [0.6, 0.25, 0.1, 0.05])


def sfx_coleta_vidro() -> Onda:
    """Tilintar cristalino: dois sinos com parciais inarmonicos."""
    return junta(
        [
            (0.0, modos(hz(96), secs(0.8), [1, 2.32, 4.25], [1, 0.25, 0.08], [0.5, 0.2, 0.08])),
            (0.12, modos(hz(100), secs(0.68), [1, 2.32], [0.8, 0.2], [0.45, 0.15])),
        ]
    )


def sfx_colisao() -> Onda:
    """Batida abafada: queda grave suave e ruido filtrado."""
    rng = rng_para(305)
    n = secs(0.35)
    t = eixo(n)
    fase = 2.0 * np.pi * np.cumsum(70.0 + 60.0 * np.exp(-t / 0.03)) / SR
    y = np.sin(fase) * np.exp(-t / 0.09)
    y = y + 0.15 * ruido_banda(rng, n, 200.0, 900.0) * np.exp(-t / 0.02)
    return passa_baixa(y, 500.0)


def sfx_powerup() -> Onda:
    """Arpejo ascendente de Do maior."""
    return junta([(i * 0.12, sino_suave(hz(m), secs(0.3))) for i, m in enumerate((72, 76, 79, 84))])


def sfx_escudo_fim() -> Onda:
    """Descida suave curta (de E6 para A5)."""
    n = secs(0.45)
    t = eixo(n)
    f = hz(88) + (hz(81) - hz(88)) * np.clip(t / 0.35, 0.0, 1.0)
    fase = 2.0 * np.pi * np.cumsum(f) / SR
    return np.sin(fase) * adsr(n, 0.01, 0.0, 1.0, 0.15)


def sfx_estrela() -> Onda:
    """Brilho de conquista: arpejo agudo seguido de acorde tremulo."""
    n = secs(0.55)
    t = eixo(n)
    acorde = acorde_puro([84, 88, 91], n, 0.02, 0.3) * (1.0 + 0.2 * np.sin(2 * np.pi * 7.5 * t)) / 1.2
    partes = [(i * 0.1, sino_suave(hz(m), secs(0.5))) for i, m in enumerate((84, 88, 91, 96))]
    partes.append((0.45, acorde))
    return junta(partes)


def sfx_estagio() -> Onda:
    """Acorde que se abre: comeca abafado e clareia (filtro simulado por mistura)."""
    n = secs(1.2)
    t = eixo(n)
    brilhante = acorde_puro([60, 64, 67, 69], n, 0.18, 0.35)
    grave = passa_baixa(brilhante, 700.0)
    abertura = np.clip(t / 0.9, 0.0, 1.0)
    return grave * (1.0 - abertura) + brilhante * abertura


def sfx_selecao() -> Onda:
    """Confirmacao de menu: duas notas ascendentes (G5 para C6)."""
    return junta([(0.0, sino_suave(hz(79), secs(0.2))), (0.09, sino_suave(hz(84), secs(0.22)))])


def sfx_foco() -> Onda:
    """Tique muito suave ao entrar num botao."""
    n = secs(0.1)
    t = eixo(n)
    return passa_baixa(np.sin(2 * np.pi * 1800.0 * t) * np.exp(-t / 0.012), 3000.0)


def sfx_compra() -> Onda:
    """Melhoria comprada: dois toques de sino (E6 e B6)."""
    return junta(
        [
            (0.0, modos(hz(88), secs(0.6), [1, 2.0], [1, 0.15], [0.25, 0.08])),
            (0.1, modos(hz(95), secs(0.5), [1, 2.0], [0.9, 0.12], [0.25, 0.08])),
        ]
    )


def sfx_fim_fase() -> Onda:
    """Fanfarra curta: C5-E5-G5 e acorde final (2,3 s)."""
    return junta(
        [
            (0.0, tri(hz(72), secs(0.45))),
            (0.35, tri(hz(76), secs(0.45))),
            (0.7, tri(hz(79), secs(0.45))),
            (1.05, (tri(hz(84), secs(1.25)) + tri(hz(79), secs(1.25)) + tri(hz(76), secs(1.25))) / 3.0),
        ]
    )


def sfx_game_over() -> Onda:
    """Frase descendente gentil (E5, D5, C5), com final mais longo (1,8 s)."""
    return junta(
        [
            (0.0, tri(hz(76), secs(0.5))),
            (0.45, tri(hz(74), secs(0.5))),
            (0.9, tri(hz(72), secs(0.9))),
        ]
    )


def sopro_papel(n: int, rng: np.random.Generator) -> Onda:
    """Sopro de papel: ruido com banda central que sobe no tempo (STFT simples)."""
    tam, passo = 1024, 256
    janela = np.hanning(tam)
    ruido = rng.standard_normal(n + tam)
    freqs = np.fft.rfftfreq(tam, 1.0 / SR)
    saida = np.zeros(n + tam)
    for ini in range(0, n, passo):
        fc = 800.0 * (4000.0 / 800.0) ** (ini / n)
        mascara = np.exp(-0.5 * ((freqs - fc) / (0.5 * fc)) ** 2)
        quadro = ruido[ini : ini + tam] * janela
        saida[ini : ini + tam] += np.fft.irfft(np.fft.rfft(quadro) * mascara, tam)
    envelope = np.sin(np.pi * np.linspace(0.0, 1.0, n)) ** 1.5
    return saida[:n] * envelope


def sfx_decolagem() -> Onda:
    """Whoosh de aviao de papel (1,1 s)."""
    return sopro_papel(secs(1.1), rng_para(330))


def sopro_suave(n: int, rng: np.random.Generator, fc_ini: float, fc_fim: float) -> Onda:
    """Sopro de ar sem envelope: banda central vai de fc_ini a fc_fim (Hz), em quadros curtos."""
    tam, passo = 1024, 256
    janela = np.hanning(tam)
    ruido = rng.standard_normal(n + tam)
    freqs = np.fft.rfftfreq(tam, 1.0 / SR)
    saida = np.zeros(n + tam)
    for ini in range(0, n, passo):
        fc = fc_ini * (fc_fim / fc_ini) ** (ini / n)
        mascara = np.exp(-0.5 * ((freqs - fc) / (0.5 * fc)) ** 2)
        quadro = ruido[ini : ini + tam] * janela
        saida[ini : ini + tam] += np.fft.irfft(np.fft.rfft(quadro) * mascara, tam)
    return saida[:n] / (np.sqrt(np.mean(saida[:n] ** 2)) + 1e-12)


def sfx_desvio_alerta() -> Onda:
    """Chamada de atencao do momento de foco (0,5 s): duas notas descendentes (A5 e E5)
    com sopro de ar cuja banda desce, sugerindo o mundo desacelerando."""
    n = secs(0.5)
    envelope = np.sin(np.pi * np.linspace(0.0, 1.0, n)) ** 2
    sopro = 0.12 * sopro_suave(n, rng_para(341), 2600.0, 700.0) * envelope
    return junta(
        [
            (0.0, sino_suave(hz(81), secs(0.42))),
            (0.16, sino_suave(hz(76), secs(0.34))),
            (0.0, sopro),
        ]
    )


def sfx_desvio_ok() -> Onda:
    """Conquista do desvio (0,4 s): arpejo ascendente de kalimba (C6, E6, G6, C7)
    com sopro de ar cuja banda sobe."""
    n = secs(0.4)
    envelope = np.sin(np.pi * np.linspace(0.0, 1.0, n)) ** 2
    sopro = 0.1 * sopro_suave(n, rng_para(342), 900.0, 3500.0) * envelope
    partes = [(i * 0.055, kalimba(hz(m), secs(0.26))) for i, m in enumerate((84, 88, 91, 96))]
    partes.append((0.0, sopro))
    return junta(partes)


def sfx_desvio_quase() -> Onda:
    """Quase-la gentil (0,3 s): duas notas graves e suaves (G3 e E3), sem ruido."""
    return junta([(0.0, sino_suave(hz(55), secs(0.18))), (0.12, sino_suave(hz(52), secs(0.16)))])


# ---------------------------------------------------------------------------
# Salvamento e linha de comando
# ---------------------------------------------------------------------------


def salvar(caminho: Path, x: Onda) -> Path:
    """Grava OGG Vorbis via soundfile; se falhar, grava WAV 16-bit de mesmo nome."""
    x = np.asarray(x, dtype=np.float64)
    try:
        import soundfile as sf  # importado aqui para o erro ser tratado

        dados = x.astype(np.float32)
        # Escrita em blocos: a chamada unica com arrays grandes estourava a pilha no Windows.
        with sf.SoundFile(str(caminho), "w", SR, 1, format="OGG", subtype="VORBIS") as arq:
            for i in range(0, len(dados), 65536):
                arq.write(dados[i : i + 65536])
        return caminho
    except Exception as erro:  # pragma: no cover - depende do ambiente
        alt = caminho.with_suffix(".wav")
        print(f"AVISO: OGG indisponivel ({erro}); gravando WAV 16-bit: {alt.name}")
        pcm = (np.clip(x, -1.0, 1.0) * 32767).astype("<i2")
        with wave.open(str(alt), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return alt


def escrever_leiame(pasta: Path) -> None:
    """Grava o LEIAME.md com instrucoes de regeneracao e licenca."""
    texto = (
        "# Audio do Dobramundo\n\n"
        "Todos os arquivos desta pasta sao gerados por `tools/make_audio.py`, por sintese "
        "com numpy (sem samples externos). Mono, 22050 Hz.\n\n"
        "## Regenerar\n\n"
        "Na raiz do projeto:\n\n"
        "    .venv\\Scripts\\python.exe tools\\make_audio.py\n"
        "    .venv\\Scripts\\python.exe tools\\make_audio.py --only sfx\n"
        "    .venv\\Scripts\\python.exe tools\\make_audio.py --out assets\\audio --only musica\n\n"
        "Requer numpy. Para gravar OGG Vorbis, precisa de `soundfile`; sem ele o script "
        "grava WAV 16-bit.\n\n"
        "## Conteudo\n\n"
        "- `musica_*.ogg`: loops de 16 compassos (vila, Amazonia e Caatinga, com 3 estagios "
        "cada). Cada bioma usa a mesma tonalidade e o mesmo andamento, para crossfade.\n"
        "- `sfx_*.ogg`: efeitos curtos de coleta, interface, fases e avisos do momento de foco (`sfx_desvio_*`).\n\n"
        "## Licenca\n\n"
        "Gerado pelo projeto; mesma licenca do codigo do Dobramundo.\n"
    )
    (pasta / "LEIAME.md").write_text(texto, encoding="utf-8")


MUSICAS: List[Tuple[str, Callable[[], Onda]]] = [
    ("musica_vila.ogg", compor_vila),
    ("musica_amazonia_1.ogg", lambda: compor_amazonia(1)),
    ("musica_amazonia_2.ogg", lambda: compor_amazonia(2)),
    ("musica_amazonia_3.ogg", lambda: compor_amazonia(3)),
    ("musica_caatinga_1.ogg", lambda: compor_caatinga(1)),
    ("musica_caatinga_2.ogg", lambda: compor_caatinga(2)),
    ("musica_caatinga_3.ogg", lambda: compor_caatinga(3)),
]

SFX: List[Tuple[str, Callable[[], Onda], float]] = [
    ("sfx_coleta_papel.ogg", sfx_coleta_papel, PICO_SFX_DB),
    ("sfx_coleta_plastico.ogg", sfx_coleta_plastico, PICO_SFX_DB),
    ("sfx_coleta_metal.ogg", sfx_coleta_metal, PICO_SFX_DB),
    ("sfx_coleta_vidro.ogg", sfx_coleta_vidro, PICO_SFX_DB),
    ("sfx_colisao.ogg", sfx_colisao, -9.0),
    ("sfx_powerup.ogg", sfx_powerup, PICO_SFX_DB),
    ("sfx_escudo_fim.ogg", sfx_escudo_fim, -11.0),
    ("sfx_estrela.ogg", sfx_estrela, PICO_SFX_DB),
    ("sfx_estagio.ogg", sfx_estagio, PICO_SFX_DB),
    ("sfx_selecao.ogg", sfx_selecao, PICO_SFX_DB),
    ("sfx_foco.ogg", sfx_foco, -16.0),
    ("sfx_compra.ogg", sfx_compra, PICO_SFX_DB),
    ("sfx_fim_fase.ogg", sfx_fim_fase, PICO_SFX_DB),
    ("sfx_game_over.ogg", sfx_game_over, -12.0),
    ("sfx_decolagem.ogg", sfx_decolagem, -10.0),
    ("sfx_desvio_alerta.ogg", sfx_desvio_alerta, -12.0),
    ("sfx_desvio_ok.ogg", sfx_desvio_ok, PICO_SFX_DB),
    ("sfx_desvio_quase.ogg", sfx_desvio_quase, -12.0),
]


def relatar(nome: str, x: Onda, musica: bool) -> None:
    """Imprime duracao, pico e RMS e avisa se algum limite nao for atendido."""
    dur, pico, rms = medidas(x)
    linha = f"{nome:<26} {dur:6.2f} s  pico {pico:7.2f} dBFS  RMS {rms:7.2f} dBFS"
    if musica:
        salto = abs(float(x[0]) - float(x[-1]))
        tipica = float(np.median(np.abs(np.diff(x))))
        linha += f"  emenda {salto:.5f} (dif. tipica {tipica:.5f})"
        ok = pico <= PICO_MUSICA_DB and -20.0 <= rms <= -16.0 and 32.0 <= dur <= 48.0
    else:
        ok = dur <= 2.5 and pico <= -6.0
    print(linha + ("" if ok else "   <-- FORA DOS LIMITES"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ponto de entrada: gera musicas e/ou efeitos."""
    parser = argparse.ArgumentParser(description="Sintetiza a trilha e os SFX do Dobramundo.")
    parser.add_argument("--out", default=None, help="pasta de saida (padrao: assets/audio na raiz do projeto)")
    parser.add_argument("--only", choices=["musica", "sfx"], default=None, help="gera apenas musicas ou apenas efeitos")
    args = parser.parse_args(argv)

    raiz = Path(__file__).resolve().parent.parent
    pasta = Path(args.out) if args.out else raiz / "assets" / "audio"
    pasta.mkdir(parents=True, exist_ok=True)

    if args.only in (None, "musica"):
        print("== Musicas ==")
        for nome, funcao in MUSICAS:
            x = ajusta_musica(funcao())
            salvar(pasta / nome, x)
            relatar(nome, x, musica=True)
    if args.only in (None, "sfx"):
        print("== Efeitos ==")
        for nome, funcao, nivel in SFX:
            x = polir(funcao(), nivel)
            salvar(pasta / nome, x)
            relatar(nome, x, musica=False)

    escrever_leiame(pasta)
    total = sum(p.stat().st_size for p in pasta.iterdir() if p.is_file())
    print(f"Pasta: {pasta}")
    print(f"Tamanho total: {total / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
