"""Contratos de legibilidade dos textos compartilhados pelas cenas."""

import pytest

from dobramundo.ui import theme as T


@pytest.mark.parametrize("width", [0, 4, 30, 80, 180, 600])
def test_long_labels_stay_inside_their_card(display, width):
    text = T.Text()
    label, size = T.fit_text(text, "Recuperamos o progresso do último arquivo válido", width, bold=True)
    assert 16 <= size <= 20
    assert text.font(size, True).size(label)[0] <= max(0, width)


def test_short_label_is_not_altered(display):
    text = T.Text()
    assert T.fit_text(text, "Voar", 200, size=24) == ("Voar", 24)


def test_public_input_import_does_not_load_camera():
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import dobramundo.input; "
            "assert 'pygame' not in sys.modules; assert 'mediapipe' not in sys.modules; "
            "assert 'dobramundo.input.camera' not in sys.modules",
        ],
        check=True,
    )
