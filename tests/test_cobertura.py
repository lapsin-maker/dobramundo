"""Cobertura complementar: calibração, áudio, texto, cache, opções de projeção, self-test e fontes da câmera."""

from __future__ import annotations

import pygame
import pytest
from helpers import CAL_READINGS, FakeSource, landmarks

from dobramundo import config as C
from dobramundo.audio import Audio
from dobramundo.engine.cache import BoundedCache
from dobramundo.input.hub import InputHub
from dobramundo.input.pose import SEGMENTS
from dobramundo.persistence import Options
from dobramundo.scenes.calibration import CalibrationScene
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.village import VillageScene
from dobramundo.selftest import REQUIRED_SPRITES, check_report
from dobramundo.ui import theme as T

PASSO = 1 / 30  # quadros de 30 por segundo nos testes de calibração


# ------------------------------------------------------------ calibração
class PreviewSource(FakeSource):
    """Fonte falsa com miniatura 160x120 RGB (sempre o mesmo objeto, como a câmera real)."""

    def __init__(self) -> None:
        super().__init__()
        self.preview_data = bytes(160 * 120 * 3)

    def snapshot(self):
        return self.seq, self.points, self.preview_data


def usa_camera_falsa(app, source, controle: str = "mao_direita") -> None:
    app.input.source_factory = lambda: source
    app.profile.controle = controle
    app.apply_options()


def test_calibracao_aguarda_continuar_e_nao_sai_durante_alcances(app):
    source = FakeSource()
    usa_camera_falsa(app, source)
    voo = FlightScene(app, "amazonia")
    scene = CalibrationScene(app, return_to=voo)
    app.go(scene)
    app.step(PASSO, [])
    for _ in range(30):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.step(PASSO, [])
    assert app.input.body.progress == pytest.approx(0.5, abs=0.02)
    assert not app.input.body.calibrated
    for _ in range(CAL_READINGS):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.step(PASSO, [])
        if app.input.body.calibrated:
            break
    assert app.input.body.calibrated and app.input.body.progress == 1.0
    for _ in range(100):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.step(PASSO, [])
    assert app.scene is scene  # calibração concluída aguarda confirmação explícita
    scene.begin_guided()
    for _ in range(40):
        source.show(landmarks({16: (0.65, 0.5)}))
        app.step(PASSO, [])
    assert scene.guided_index == 0 and app.scene is scene
    button = next(b for b in scene.menu.buttons if b.key == "continuar")
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center))
    app.step(PASSO, [])
    assert app.scene is voo


def test_recalibrar_zera_o_progresso(app):
    source = FakeSource()
    usa_camera_falsa(app, source)
    scene = CalibrationScene(app)
    app.go(scene)
    app.step(PASSO, [])
    for _ in range(CAL_READINGS):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.step(PASSO, [])
    assert app.input.body.calibrated
    scene.restart()
    assert not app.input.body.calibrated and app.input.body.progress < 1.0
    assert scene.done_time == 0.0


def test_usar_teclado_troca_o_perfil_e_fecha_a_camera(app):
    source = FakeSource()
    usa_camera_falsa(app, source)
    scene = CalibrationScene(app)
    app.go(scene)
    app.step(PASSO, [])
    scene.keyboard()
    assert app.profile.controle == "teclado"
    assert app.input.body is None and app.input.source is None
    assert isinstance(app.next_scene, VillageScene)


def test_sem_camera_volta_para_a_cena_de_retorno(app):
    voo = FlightScene(app, "amazonia")
    scene = CalibrationScene(app, return_to=voo)
    app.go(scene)
    app.step(PASSO, [])  # sem corpo (teclado): a calibração devolve a cena de retorno
    app.step(PASSO, [])
    assert app.scene is voo


def test_desenha_o_erro_da_camera_sem_quebrar(app):
    source = FakeSource()
    source.error = "câmera ocupada"
    usa_camera_falsa(app, source)
    scene = CalibrationScene(app)
    app.go(scene)
    app.step(PASSO, [])
    assert app.scene is scene and app.input.body.error == "câmera ocupada"


def test_desenha_a_miniatura_uma_vez_por_imagem(app):
    source = PreviewSource()
    usa_camera_falsa(app, source)
    source.show(landmarks({16: (0.5, 0.5)}))
    scene = CalibrationScene(app)
    app.go(scene)
    app.step(PASSO, [])
    assert scene.preview is not None and scene.preview.get_size() == (320, 240)
    primeira = scene.preview
    app.step(PASSO, [])
    assert scene.preview is primeira  # mesma imagem: não redimensiona de novo


# ------------------------------------------------------------------ áudio
def test_silencio_zera_o_volume_efetivo():
    audio = Audio(enabled=True)
    assert audio.enabled
    audio.apply(Options(silencio=True))
    assert audio.effective_music() == 0.0
    assert all(channel.get_volume() == pytest.approx(0.0) for channel in audio.channels)


def test_volume_da_musica_segue_as_opcoes():
    audio = Audio(enabled=True)
    audio.apply(Options())  # 0,8 geral x 0,6 música
    assert audio.effective_music() == pytest.approx(0.48)
    assert audio.channels[0].get_volume() == pytest.approx(0.48, abs=0.01)


def test_music_alterna_o_canal_ativo():
    audio = Audio(enabled=True)
    inicial = audio.active
    audio.music("musica_vila")
    assert audio.active != inicial
    assert audio.channels[audio.active].get_sound() is audio.sound("musica_vila")


def test_music_nao_repete_a_mesma_trilha():
    audio = Audio(enabled=True)
    audio.music("musica_vila")
    ativo = audio.active
    audio.music("musica_vila")
    assert audio.active == ativo


def test_music_none_so_faz_fade_no_canal_atual():
    audio = Audio(enabled=True)
    audio.music("musica_vila")
    ativo = audio.active
    audio.music(None)
    assert audio.current is None and audio.active == ativo


def test_trilha_depois_do_silencio_nao_usa_o_canal_em_fade():
    audio = Audio(enabled=True)
    audio.music("musica_vila")
    sumindo = audio.active
    audio.music(None)
    audio.music("musica_amazonia_1")
    assert audio.active != sumindo


def test_som_inexistente_nao_quebra():
    audio = Audio(enabled=True)
    audio.play("sfx_nao_existe")
    assert audio.sounds["sfx_nao_existe"] is None


def test_coleta_de_tipo_desconhecido_toca_papel():
    audio = Audio(enabled=True)
    audio.collect("madeira")
    assert "sfx_coleta_papel" in audio.sounds


# ------------------------------------------------------------ texto (theme)
FRASE = "a quebra de linha precisa respeitar a largura do cartão de texto " * 4


def test_wrap_quebra_dentro_da_largura():
    text = T.Text()
    linhas = text.wrap(FRASE, 220)
    font = text.font(T.SIZES["body"])
    assert len(linhas) > 1
    assert all(font.size(linha)[0] <= 220 for linha in linhas)
    assert " ".join(linhas).split() == FRASE.split()


def test_wrap_usa_cache():
    text = T.Text()
    primeira = text.wrap("um dois três quatro", 80)
    assert text.wrap("um dois três quatro", 80) is primeira
    assert len(text.wrapped) == 1


def test_paragraph_devolve_o_y_logo_abaixo_do_texto():
    text = T.Text()
    tela = pygame.Surface((400, 400))
    rect = pygame.Rect(10, 20, 200, 300)
    linhas = text.wrap(FRASE, rect.width)
    fim = text.paragraph(tela, FRASE, rect)
    passo = int(text.font(T.SIZES["body"]).get_linesize() * 1.3)
    assert len(linhas) > 1
    assert fim == rect.top + len(linhas) * passo


def test_painel_e_veu_nao_quebram():
    tela = pygame.Surface((300, 200))
    T.panel(tela, pygame.Rect(10, 10, 100, 80))
    T.panel(tela, pygame.Rect(10, 10, 100, 80), width=0, radius=0)
    T.veil(tela)
    T.veil(tela, (0, 0, 0), 0)


# -------------------------------------------------------------------- cache
def test_cache_descarta_o_item_mais_antigo():
    cache = BoundedCache(3)
    for chave in "abcd":
        cache[chave] = chave.upper()
    assert list(cache) == ["b", "c", "d"]


def test_put_devolve_o_valor_guardado():
    cache = BoundedCache(2)
    assert cache.put("x", 42) == 42
    assert cache["x"] == 42


def test_regravar_chave_existente_nao_descarta_ninguem():
    cache = BoundedCache(2)
    cache["a"] = 1
    cache["b"] = 2
    cache["a"] = 10
    assert dict(cache) == {"a": 10, "b": 2}


def test_limite_minimo_e_um():
    assert BoundedCache(0).limit == 1


# ------------------------------------------------------- espelho e giro (app)
@pytest.mark.parametrize(
    "espelhar, rotacao, esperado",
    [
        (False, 0, (100, 50)),
        (True, 0, (C.WIDTH - 1 - 100, 50)),
        (False, 180, (C.WIDTH - 1 - 100, C.HEIGHT - 1 - 50)),
        (True, 180, (100, C.HEIGHT - 1 - 50)),
    ],
)
def test_to_logical_combina_espelhar_e_girar(app, espelhar, rotacao, esperado):
    app.options.espelhar = espelhar
    app.options.rotacao = rotacao
    assert app.to_logical((100, 50)) == esperado


def test_save_marca_falha_e_depois_limpa(app, monkeypatch):
    monkeypatch.setattr(app, "writer", lambda profile: False)
    app.save()
    assert app.save_failed is True
    monkeypatch.setattr(app, "writer", lambda profile: True)
    app.save()
    assert app.save_failed is False


# ------------------------------------------------------------- self-test
def relatorio(sprites=None, estagio: int = 2, detector: str = "ok") -> dict:
    if sprites is None:
        sprites = {nome: 3 for nome in REQUIRED_SPRITES}
    return {
        "sprites": sprites,
        "voos": {"amazonia": {"estagio": estagio, "segundos_ativos": 20, "distancia": 3400}},
        "camera": {"detector": detector},
    }


def test_relatorio_completo_passa():
    assert check_report(relatorio(), require_camera=True) == []


def test_pasta_de_sprites_vazia_falha():
    sprites = {nome: 3 for nome in REQUIRED_SPRITES}
    sprites["ui"] = 0
    assert check_report(relatorio(sprites), require_camera=False) == ["pasta de sprites vazia: ui"]


def test_sprites_ausentes_falham_todos():
    falhas = check_report(relatorio(sprites={}), require_camera=False)
    assert len(falhas) == len(REQUIRED_SPRITES)
    assert all(falha.startswith("pasta de sprites vazia") for falha in falhas)


def test_voo_que_nao_chegou_ao_terceiro_estagio_falha():
    assert check_report(relatorio(estagio=1), require_camera=False) == ["o voo em amazonia não chegou ao estágio 3"]


def test_detector_so_falha_quando_a_camera_e_exigida():
    ruim = relatorio(detector="bibliotecas ausentes (mediapipe)")
    assert check_report(ruim, require_camera=False) == []
    assert check_report(ruim, require_camera=True) == ["detector de pose: bibliotecas ausentes (mediapipe)"]


# ------------------------------------------------------- fontes da câmera
class GravadorDeCamera(FakeSource):
    def __init__(self) -> None:
        super().__init__()
        self.iniciadas = 0
        self.paradas = 0

    def start(self):
        self.iniciadas += 1

    def stop(self):
        self.paradas += 1


def test_stop_camera_desliga_a_fonte():
    hub = InputHub()
    fonte = GravadorDeCamera()
    hub.source_factory = lambda: fonte
    hub.set_segment("cabeca")
    assert hub.source is fonte and fonte.iniciadas == 1
    hub.stop_camera()
    assert fonte.paradas == 1
    assert hub.source is None and hub.body is None


def test_trocar_de_segmento_reaproveita_a_mesma_camera():
    hub = InputHub()
    fonte = GravadorDeCamera()
    chamadas = []

    def fabrica():
        chamadas.append(1)
        return fonte

    hub.source_factory = fabrica
    hub.set_segment("cabeca")
    hub.set_segment("mao_direita")
    assert len(chamadas) == 1 and fonte.iniciadas == 1 and fonte.paradas == 0
    assert hub.body.segment is SEGMENTS["mao_direita"] and hub.body.source is fonte


def test_voltar_para_teclado_desliga_a_camera():
    hub = InputHub()
    fonte = GravadorDeCamera()
    hub.source_factory = lambda: fonte
    hub.set_segment("cabeca")
    hub.set_segment("teclado")
    assert fonte.paradas == 1
    assert hub.source is None and not hub.uses_body
