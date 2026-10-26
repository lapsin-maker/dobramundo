"""Aplica um voo ao perfil uma única vez, fora da apresentação de resultado."""

from __future__ import annotations

from datetime import datetime

from .. import config as C
from .run import FlightRun


def apply_run(profile, run: FlightRun) -> dict:
    """Credita recompensas e registra a transformação persistente da cidade."""
    if run.settlement is not None:
        return dict(run.settlement)
    key = run.biome.key
    best_before = profile.estrelas.get(key, 0)
    for waste, amount in run.resources.items():
        profile.recursos[waste] = profile.recursos.get(waste, 0) + amount
    profile.pontos += run.score
    profile.voos += 1
    profile.voos_fase[key] = profile.voos_fase.get(key, 0) + 1
    profile.transformacao_cidades[key] = max(
        profile.transformacao_cidades.get(key, C.START_RESTORATION), run.restoration
    )
    entry = run.summary()
    entry["data"] = datetime.now().isoformat(timespec="seconds")
    entry["controle"] = profile.controle
    profile.historico = (profile.historico + [entry])[-C.HISTORY_LIMIT :]
    if run.stars > best_before:
        profile.estrelas[key] = run.stars
    record_key = f"{key}:{run.mode}"
    new_record = run.score > profile.recordes.get(record_key, 0)
    if new_record:
        profile.recordes[record_key] = run.score
    run.settlement = {"new_stars": max(0, run.stars - best_before), "new_record": new_record}
    return dict(run.settlement)


def notify_settlement(app, run: FlightRun) -> None:
    """Notifica o cartucho uma vez após o assentamento das recompensas."""
    if run.settlement_callback_sent or not run.settlement:
        return
    app.on_flight(app.profile.historico[-1])
    run.settlement_callback_sent = True
