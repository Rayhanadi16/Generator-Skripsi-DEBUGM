"""
Impor tabel dari Excel (.xlsx) atau CSV menjadi penanda [[TABEL]] di isi subbab.

- baca_xlsx(isi_bytes)  -> {nama_sheet: daftar baris}; nilai hasil rumus, sel gabungan diisi nilai kiri atasnya
- baca_csv(isi_bytes)   -> daftar baris; pemisah koma, titik koma, atau tab dikenali sendiri
- rapikan(baris)        -> tanpa baris dan kolom kosong di tepi, semua baris sama panjang
- format_angka(nilai)   -> teks: 1.250.000, 3,14, 12 Januari 2026
- format_tabel(baris)   -> semua sel menjadi teks, angka desimal seragam per kolom
- ke_penanda(baris, judul, sumber) -> teks penanda siap ditempel ke isi subbab

Hasilnya penanda biasa, jadi mesin pembuat Word tidak tahu dan tidak perlu tahu tabelnya berasal dari Excel.
"""

import csv
import io
import re
from datetime import date, datetime

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
         "Oktober", "November", "Desember"]
MAKS_KOLOM, MAKS_BARIS = 8, 40   # di atas ini tabel kemungkinan tidak muat di A4 tegak
MAKS_DESIMAL = 4


class GagalTabel(Exception):
    """Pesannya sudah siap ditampilkan ke pengguna."""


# ---------------------------------------------------------------------------
# Membaca file
# ---------------------------------------------------------------------------
def baca_xlsx(isi_bytes):
    try:
        from openpyxl import load_workbook
    except ImportError as e:  # pragma: no cover
        raise GagalTabel("Pembaca Excel belum terpasang. Jalankan: pip install openpyxl") from e
    try:
        buku = load_workbook(io.BytesIO(isi_bytes), data_only=True)   # data_only: nilai hasil rumus, bukan rumusnya
    except Exception as e:
        raise GagalTabel("File Excel ini tidak bisa dibaca. Simpan ulang sebagai .xlsx lalu coba lagi.") from e
    hasil = {}
    for lembar in buku.worksheets:
        baris = [list(b) for b in lembar.iter_rows(values_only=True)]
        for rentang in lembar.merged_cells.ranges:
            nilai = lembar.cell(rentang.min_row, rentang.min_col).value
            for r in range(rentang.min_row, rentang.max_row + 1):
                for c in range(rentang.min_col, rentang.max_col + 1):
                    if r - 1 < len(baris) and c - 1 < len(baris[r - 1]):
                        baris[r - 1][c - 1] = nilai
        hasil[lembar.title] = baris
    return hasil


def _angka_csv(teks, koma_desimal):
    """Teks sel CSV menjadi angka bila bentuknya jelas angka; selain itu dibiarkan (mis. NIM berawalan nol)."""
    t = teks.strip()
    if re.fullmatch(r"-?(0|[1-9]\d*)", t):
        return int(t)
    pola = r"-?(0|[1-9]\d*),\d+" if koma_desimal else r"-?(0|[1-9]\d*)\.\d+"
    if re.fullmatch(pola, t):
        return float(t.replace(",", "."))
    return teks


def baca_csv(isi_bytes):
    for enkode in ("utf-8-sig", "cp1252"):
        try:
            teks = isi_bytes.decode(enkode)
            break
        except UnicodeDecodeError:
            continue
    contoh = "\n".join(teks.splitlines()[:10])
    tanpa_kutip = re.sub(r'"[^"]*"', "", contoh)
    pemisah = max(";,\t", key=tanpa_kutip.count)   # Excel berbahasa Indonesia menyimpan CSV dengan titik koma
    koma_desimal = pemisah == ";"
    return [[_angka_csv(sel, koma_desimal) for sel in baris] for baris in csv.reader(io.StringIO(teks), delimiter=pemisah)]


def _kosong(nilai):
    return nilai is None or (isinstance(nilai, str) and not nilai.strip())


def rapikan(baris):
    baris = [list(b) for b in baris]
    while baris and all(_kosong(s) for s in baris[0]):
        baris.pop(0)
    while baris and all(_kosong(s) for s in baris[-1]):
        baris.pop()
    if not baris:
        return []
    lebar = max(len(b) for b in baris)
    baris = [b + [None] * (lebar - len(b)) for b in baris]
    kiri = next(c for c in range(lebar) if any(not _kosong(b[c]) for b in baris))
    kanan = next(c for c in range(lebar - 1, -1, -1) if any(not _kosong(b[c]) for b in baris))
    return [b[kiri: kanan + 1] for b in baris]


# ---------------------------------------------------------------------------
# Format angka
# ---------------------------------------------------------------------------
def _ribuan(n, pemisah):
    return f"{n:,}".replace(",", pemisah)


def format_angka(nilai, koma_desimal=True, desimal=None, tahun=False):
    """desimal=None: bilangan bulat tanpa desimal, pecahan apa adanya (maksimal 4 angka di belakang koma)."""
    ribu, des = (".", ",") if koma_desimal else (",", ".")
    if nilai is None:
        return ""
    if isinstance(nilai, bool):
        return "Ya" if nilai else "Tidak"
    if isinstance(nilai, (datetime, date)):
        return f"{nilai.day} {BULAN[nilai.month - 1]} {nilai.year}"
    if isinstance(nilai, float) and nilai.is_integer() and desimal is None:
        nilai = int(nilai)
    if isinstance(nilai, int):
        if tahun:
            return str(nilai)
        teks = _ribuan(abs(nilai), ribu) + (des + "0" * desimal if desimal else "")
        return ("-" if nilai < 0 else "") + teks
    if isinstance(nilai, float):
        n = desimal if desimal is not None else _n_desimal(nilai)
        bulat, _, pecahan = f"{abs(nilai):.{n}f}".partition(".")
        teks = _ribuan(int(bulat), ribu) + (des + pecahan if pecahan else "")
        return ("-" if nilai < 0 and float(f"{nilai:.{n}f}") != 0 else "") + teks
    return str(nilai).strip()


def _n_desimal(nilai):
    return len(f"{abs(nilai):.{MAKS_DESIMAL}f}".rstrip("0").partition(".")[2])


def format_tabel(baris, koma_desimal=True):
    """Semua sel menjadi teks. Dalam satu kolom, jumlah angka di belakang koma dibuat sama."""
    baris = rapikan(baris)
    if not baris:
        return []
    hasil = [[None] * len(baris[0]) for _ in baris]
    for c in range(len(baris[0])):
        kolom = [b[c] for b in baris]
        angka = [v for v in kolom if isinstance(v, (int, float)) and not isinstance(v, bool)]
        pecahan = [v for v in angka if isinstance(v, float) and not v.is_integer()]
        desimal = max((_n_desimal(v) for v in pecahan), default=None)
        tahun = bool(angka) and not pecahan and all(1900 <= v <= 2100 for v in angka)
        for r, v in enumerate(kolom):
            hasil[r][c] = format_angka(v, koma_desimal, desimal=desimal if isinstance(v, (int, float)) else None,
                                       tahun=tahun)
    return hasil


# ---------------------------------------------------------------------------
# Penanda
# ---------------------------------------------------------------------------
def _sel(teks):
    """Karakter | memisahkan kolom di penanda, jadi tidak boleh ada di dalam sel."""
    return re.sub(r"\s+", " ", str(teks).replace("|", "/")).strip()


def ke_penanda(baris, judul, sumber="", koma_desimal=True):
    teks = format_tabel(baris, koma_desimal)
    if not teks:
        raise GagalTabel("Rentang yang dipilih kosong.")
    kepala = f"[[TABEL: {_sel(judul)}" + (f" | {_sel(sumber)}" if _sel(sumber) else "") + "]]"
    return "\n".join([kepala] + [" | ".join(_sel(s) for s in b) for b in teks] + ["[[/TABEL]]"])


def peringatan_ukuran(baris):
    baris = rapikan(baris)
    pesan = []
    if baris and len(baris[0]) > MAKS_KOLOM:
        pesan.append(f"Tabel ini {len(baris[0])} kolom. Lebih dari {MAKS_KOLOM} kolom biasanya tidak muat di A4 tegak.")
    if len(baris) > MAKS_BARIS:
        pesan.append(f"Tabel ini {len(baris)} baris. Lebih dari {MAKS_BARIS} baris akan memanjang ke beberapa halaman.")
    return pesan
