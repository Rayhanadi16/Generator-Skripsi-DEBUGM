"""
Autosave: menyimpan isian secara otomatis ke folder `autosave/` di sebelah app.py.

autosave/
  progres_terakhir.json      <- isian terbaru (ditulis setiap ada perubahan)
  gambar/                    <- gambar yang diupload / berasal dari draft
  logo.bin                   <- logo sampul
  riwayat/progres_YYYYMMDD_HHMMSS.json   <- cadangan berkala (maks. 30 versi)

Semua file hanya ada di komputer pengguna; tidak ada yang dikirim ke internet.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

FOLDER = Path(__file__).resolve().parent / "autosave"
FILE_UTAMA = FOLDER / "progres_terakhir.json"
FOLDER_GAMBAR = FOLDER / "gambar"
FILE_LOGO = FOLDER / "logo.bin"
FOLDER_RIWAYAT = FOLDER / "riwayat"
JEDA_RIWAYAT_DETIK = 5 * 60
MAKS_RIWAYAT = 30


def _tulis_atomik(path: Path, isi: bytes):
    """Tulis ke file sementara lalu ganti nama, supaya file tidak rusak bila laptop mati di tengah penulisan."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(isi)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _nama_aman(nama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._\-]", "_", Path(nama).name) or "gambar"


def sidik(data) -> str:
    return hashlib.sha1(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def info():
    """Return dict info autosave terakhir, atau None bila belum ada."""
    if not FILE_UTAMA.exists():
        return None
    try:
        data = json.loads(FILE_UTAMA.read_text(encoding="utf-8"))
    except Exception:
        return None
    waktu = datetime.fromtimestamp(FILE_UTAMA.stat().st_mtime)
    judul = (data.get("identitas", {}) or {}).get("judul_id") or ""
    n_kata = sum(len((s.get("isi") or "").split()) for b in data.get("bab", []) for s in b.get("subbab", []))
    return {"waktu": waktu, "judul": judul, "kata_bab": n_kata, "kosong": _kosong(data)}


def _kosong(data) -> bool:
    """True bila isian praktis belum diisi (hanya nilai bawaan)."""
    ada_bab = any((sub.get("isi") or "").strip() for b in data.get("bab", []) for sub in b.get("subbab", []))
    ada_teks = any((data.get(k) or "").strip() for k in ("kata_pengantar", "intisari", "abstract", "daftar_pustaka"))
    bawaan = ("tahun", "fakultas", "tempat_ttd")
    ada_identitas = any((v or "").strip() for k, v in (data.get("identitas") or {}).items() if k not in bawaan)
    return not (ada_bab or ada_teks or ada_identitas)


def simpan(data, gambar=None, logo=None):
    """Simpan isian + gambar + logo. Return waktu simpan."""
    isi = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    _tulis_atomik(FILE_UTAMA, isi)
    indeks = _baca_indeks()
    berubah = False
    for nama, blob in (gambar or {}).items():
        file = indeks.get(nama) or _nama_aman(nama)
        while file in indeks.values() and indeks.get(nama) != file:   # nama bentrok setelah dibersihkan
            file = "_" + file
        p = FOLDER_GAMBAR / file
        if not p.exists() or p.stat().st_size != len(blob):
            _tulis_atomik(p, blob)
        if indeks.get(nama) != file:
            indeks[nama] = file
            berubah = True
    if berubah:
        _tulis_atomik(FOLDER_GAMBAR / "_indeks.json", json.dumps(indeks, ensure_ascii=False).encode("utf-8"))
    if logo:
        if not FILE_LOGO.exists() or FILE_LOGO.stat().st_size != len(logo):
            _tulis_atomik(FILE_LOGO, logo)
    _riwayat_berkala(isi)
    return datetime.now()


def _riwayat_berkala(isi: bytes, paksa=False):
    FOLDER_RIWAYAT.mkdir(parents=True, exist_ok=True)
    semua = sorted(FOLDER_RIWAYAT.glob("progres_*.json"))
    if not paksa and semua and time.time() - semua[-1].stat().st_mtime < JEDA_RIWAYAT_DETIK:
        return
    nama = FOLDER_RIWAYAT / f"progres_{datetime.now():%Y%m%d_%H%M%S}.json"
    _tulis_atomik(nama, isi)
    for lama in sorted(FOLDER_RIWAYAT.glob("progres_*.json"))[:-MAKS_RIWAYAT]:
        lama.unlink(missing_ok=True)


def cadangkan_sekarang():
    """Salin isian terakhir ke riwayat (dipakai sebelum isian ditimpa: mulai baru, muat contoh, dll.)."""
    if FILE_UTAMA.exists():
        _riwayat_berkala(FILE_UTAMA.read_bytes(), paksa=True)


def muat():
    """Return (data, gambar, logo) dari autosave terakhir."""
    data = json.loads(FILE_UTAMA.read_text(encoding="utf-8"))
    return data, muat_gambar(), (FILE_LOGO.read_bytes() if FILE_LOGO.exists() else None)


def _baca_indeks():
    try:
        return json.loads((FOLDER_GAMBAR / "_indeks.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def muat_gambar():
    """{nama_asli: bytes} — nama asli dipertahankan agar penanda [[GAMBAR: ...]] tetap cocok."""
    hasil = {}
    for nama, file in _baca_indeks().items():
        p = FOLDER_GAMBAR / file
        if p.is_file():
            hasil[nama] = p.read_bytes()
    return hasil


def daftar_riwayat():
    """[(nama_file, label)] terbaru dulu."""
    hasil = []
    for p in sorted(FOLDER_RIWAYAT.glob("progres_*.json"), reverse=True) if FOLDER_RIWAYAT.exists() else []:
        try:
            w = datetime.strptime(p.stem.replace("progres_", ""), "%Y%m%d_%H%M%S")
            hasil.append((p.name, w.strftime("%d %b %Y, %H:%M")))
        except ValueError:
            continue
    return hasil


def muat_riwayat(nama_file):
    p = FOLDER_RIWAYAT / Path(nama_file).name
    return json.loads(p.read_text(encoding="utf-8"))
