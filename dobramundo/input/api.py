"""Interface pública e estática de entrada para cenas e plataformas.

Não abre câmera nem carrega MediaPipe. Sem importação dinâmica: compatível com
o contrato de módulos portáveis do console T-TEA.
"""

from .floor import TARGETS, FloorMap
from .hub import FLIGHT_KEYS, InputHub
from .pose import SEGMENTS, BodyControl, FloorControl

__all__ = ["FLIGHT_KEYS", "SEGMENTS", "TARGETS", "BodyControl", "FloorControl", "FloorMap", "InputHub"]
