import json
import sys
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))


@pytest.fixture
def data_contoh():
    return json.loads((AKAR / "contoh_data.json").read_text(encoding="utf-8"))


@pytest.fixture
def gambar_contoh():
    return {"grafik_contoh.png": (AKAR / "grafik_contoh.png").read_bytes()}


@pytest.fixture
def aplikasi(monkeypatch):
    """Aplikasi mode web yang sudah dijalankan sekali, dari folder repo."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(AKAR)
    monkeypatch.setenv("GENERATOR_MODE", "web")
    return AppTest.from_file(str(AKAR / "app.py"), default_timeout=60).run()


def tombol(at, label):
    return next(b for b in at.button if b.label == label)


def ke_tahap(at, kunci):
    """Pindah tahap ("isi", "bahan", "periksa", "buat") seperti mengklik tombol tahapnya."""
    at.session_state["tahap"] = kunci
    return at.run()
