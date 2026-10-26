"""Tempos da leitura consumida; nunca guarda imagem, posição ou identificação."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class InputFrame:
    sequence: int
    captured_at: float
    consumed_at: float
    rendered_at: float
    presented_at: float
    usable: bool

    def milliseconds(self) -> Dict[str, float]:
        return {
            "capture_to_consume": max(0.0, self.consumed_at - self.captured_at) * 1000,
            "consume_to_canvas": max(0.0, self.rendered_at - self.consumed_at) * 1000,
            "canvas_to_present": max(0.0, self.presented_at - self.rendered_at) * 1000,
            "capture_to_present": max(0.0, self.presented_at - self.captured_at) * 1000,
        }


def input_frame(
    sequence: int,
    captured: Optional[float],
    consumed: Optional[float],
    rendered: Optional[float],
    presented: float,
    usable: bool,
) -> Optional[InputFrame]:
    if captured is None or consumed is None or rendered is None or sequence < 1:
        return None
    return InputFrame(sequence, captured, consumed, rendered, presented, usable)
