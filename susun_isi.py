"""
Mengolah teks isi subbab sebagai susunan blok, tanpa Streamlit.

Teks isi subbab tetap sumber utama: satu baris satu paragraf, dengan penanda [[GAMBAR]], [[TABEL]]...[[/TABEL]],
[[RUMUS]], dan "### Judul". Fungsi di sini hanya menulis, mengubah, dan memindah baris penanda itu, jadi
generator.py, preview.py, dan rujukan.py tidak perlu tahu bahwa teksnya disusun lewat tombol.

- pecah_blok(teks)            -> daftar blok (baris kosong bukan blok)
- pilihan_letak(teks)         -> [(indeks_sisip, label)] untuk dropdown Letak
- sisipkan_gambar / sisipkan_subjudul
- pindah_blok / ubah_gambar / ubah_subjudul / hapus_blok
- pindah_bagian(teks, indeks_blok, arah)  -> memindah sub-subbab beserta isinya (dipakai panel Kerangka)
- nomor_blok(data, i, j)      -> nomor yang akan tampil untuk gambar, tabel, rumus, dan sub-subbab
- pemakaian_gambar(data)      -> {nama file: ["1.1", "Lampiran 2"]}
- nama_bebas(nama, isi, simpanan) -> nama file yang tidak menimpa gambar lain
- tukar_subbab / sisip_subbab / hapus_subbab -> menggeser kunci bab{i}_s{j}_* di session_state (atau dict biasa)

indeks_sisip: 0 berarti sebelum blok pertama, k berarti sesudah blok ke-k (terhitung dari 1), dan
len(blok) berarti di akhir subbab.
"""

import re

from generator import RE_GAMBAR, RE_LIST1, RE_LIST2, RE_LIST3, RE_RUMUS, RE_TABEL_BUKA, RE_TABEL_TUTUP
from rujukan import RE_LABEL, pisah_label, pisah_label_rumus

LEBAR_BAWAAN_CM = 12.0
LEBAR_MIN_CM, LEBAR_MAX_CM = 5.0, 14.0
NAMA_JENIS = {"paragraf": "paragraf", "daftar": "perincian", "subjudul": "sub-subbab", "gambar": "Gambar",
              "tabel": "Tabel", "rumus": "Rumus"}


def _baris(teks):
    return (teks or "").replace("\r\n", "\n").split("\n")


def _lebar(teks):
    try:
        return float(teks.replace(",", ".")) if teks else LEBAR_BAWAAN_CM
    except ValueError:
        return LEBAR_BAWAAN_CM


def _urai_gambar(argumen):
    sisa, label = pisah_label(argumen)
    bagian = [x.strip() for x in sisa.split("|")]
    bagian += [""] * (4 - len(bagian))
    return {"file": bagian[0], "judul": bagian[1], "sumber": bagian[2], "lebar": _lebar(bagian[3]), "label": label}


def pecah_blok(teks):
    """Daftar blok {jenis, baris_awal, baris_akhir, teks, data}. Aturannya mengikuti generator._isi_subbab()."""
    baris = _baris(teks)
    blok = []
    i = 0
    while i < len(baris):
        b = baris[i].strip()
        awal = i
        i += 1
        if not b:
            continue
        jenis, data = "paragraf", {}
        if b.startswith("### "):
            jenis, data = "subjudul", {"judul": b[4:].strip()}
        elif RE_GAMBAR.match(b):
            jenis, data = "gambar", _urai_gambar(RE_GAMBAR.match(b).group(1))
        elif RE_TABEL_BUKA.match(b):
            sisa, label = pisah_label(RE_TABEL_BUKA.match(b).group(1))
            bagian = [x.strip() for x in sisa.split("|")] + [""]
            while i < len(baris) and not RE_TABEL_TUTUP.match(baris[i].strip()):
                i += 1
            tertutup = i < len(baris)
            i = min(i + 1, len(baris))
            jenis, data = "tabel", {"judul": bagian[0], "sumber": bagian[1], "label": label, "tertutup": tertutup}
        elif RE_RUMUS.match(b):
            rumus, label = pisah_label_rumus(RE_RUMUS.match(b).group(1))
            jenis, data = "rumus", {"rumus": rumus.strip(), "label": label}
        elif RE_LIST3.match(b) or RE_LIST1.match(b) or RE_LIST2.match(b):
            jenis = "daftar"
        blok.append({"jenis": jenis, "baris_awal": awal, "baris_akhir": i - 1,
                     "teks": "\n".join(baris[awal:i]), "data": data})
    return blok


def cuplikan(teks, panjang=40):
    teks = " ".join((teks or "").split())
    return teks if len(teks) <= panjang else teks[:panjang].rstrip() + "…"


def nama_blok(blok, no_paragraf=None):
    """Sebutan singkat satu blok: 'paragraf 2: Penelitian ini…', 'Gambar: Grafik Penjualan'."""
    jenis, data = blok["jenis"], blok["data"]
    if jenis == "paragraf":
        return f"paragraf {no_paragraf}: {cuplikan(blok['teks'])}" if no_paragraf else cuplikan(blok["teks"])
    if jenis == "daftar":
        return f"perincian: {cuplikan(blok['teks'])}"
    isi = {"subjudul": data.get("judul"), "gambar": data.get("judul") or data.get("file"),
           "tabel": data.get("judul"), "rumus": data.get("rumus")}[jenis]
    return f"{NAMA_JENIS[jenis]}: {cuplikan(isi) or '(tanpa judul)'}"


def pilihan_letak(teks):
    blok = pecah_blok(teks)
    pilihan = [(0, "Di awal subbab")] if blok else []
    no = 0
    for k, b in enumerate(blok, start=1):
        no += b["jenis"] == "paragraf"
        pilihan.append((k, "Setelah " + nama_blok(b, no)))
    pilihan.append((len(blok), "Di akhir subbab"))
    return pilihan


def bersihkan(teks):
    """Judul atau sumber yang aman ditaruh di dalam penanda: tanpa baris baru, tanpa | dan ]]."""
    teks = " ".join((teks or "").split()).replace("|", "/")
    while "]]" in teks:
        teks = teks.replace("]]", "]")
    return teks.lstrip("#").strip() if RE_LABEL.match(teks) else teks


def nama_aman(nama):
    """Nama file yang aman ditaruh di dalam penanda."""
    return re.sub(r"[|\[\]\n\r]", "_", nama or "").strip() or "gambar.png"


def penanda_gambar(file, judul, sumber="", lebar=LEBAR_BAWAAN_CM, label=None):
    bagian = [nama_aman(file), bersihkan(judul), bersihkan(sumber), f"{float(lebar):g}"]
    if label:
        bagian.append("#" + label.lstrip("#"))
    return "[[GAMBAR: " + " | ".join(bagian) + "]]"


def _sisipkan_baris(teks, indeks_sisip, baris_baru):
    baris, blok = _baris(teks), pecah_blok(teks)
    if not blok:
        return baris_baru
    indeks_sisip = max(0, min(indeks_sisip, len(blok)))
    posisi = blok[0]["baris_awal"] if indeks_sisip == 0 else blok[indeks_sisip - 1]["baris_akhir"] + 1
    return "\n".join(baris[:posisi] + [baris_baru] + baris[posisi:])


def sisipkan_gambar(teks, indeks_sisip, file, judul, sumber="", lebar=LEBAR_BAWAAN_CM):
    return _sisipkan_baris(teks, indeks_sisip, penanda_gambar(file, judul, sumber, lebar))


def bersihkan_subjudul(judul):
    return " ".join((judul or "").replace("#", " ").split())


def sisipkan_subjudul(teks, indeks_sisip, judul):
    return _sisipkan_baris(teks, indeks_sisip, "### " + bersihkan_subjudul(judul))


def _ganti_blok(teks, indeks_blok, baris_baru):
    baris, b = _baris(teks), pecah_blok(teks)[indeks_blok]
    return "\n".join(baris[: b["baris_awal"]] + baris_baru + baris[b["baris_akhir"] + 1:])


def ubah_subjudul(teks, indeks_blok, judul_baru):
    if pecah_blok(teks)[indeks_blok]["jenis"] != "subjudul":
        return teks
    return _ganti_blok(teks, indeks_blok, ["### " + bersihkan_subjudul(judul_baru)])


def ubah_gambar(teks, indeks_blok, judul=None, sumber=None, lebar=None, file=None):
    b = pecah_blok(teks)[indeks_blok]
    if b["jenis"] != "gambar":
        return teks
    d = b["data"]
    baru = penanda_gambar(d["file"] if file is None else file, d["judul"] if judul is None else judul,
                          d["sumber"] if sumber is None else sumber, d["lebar"] if lebar is None else lebar,
                          d["label"])
    return _ganti_blok(teks, indeks_blok, [baru])


def hapus_blok(teks, indeks_blok):
    return _ganti_blok(teks, indeks_blok, [])


def _tukar(baris, a, b):
    """Tukar dua rentang baris (awal, akhir) yang tidak tumpang tindih; baris di antaranya tetap di tempat."""
    (a1, a2), (b1, b2) = sorted([a, b])
    return baris[:a1] + baris[b1: b2 + 1] + baris[a2 + 1: b1] + baris[a1: a2 + 1] + baris[b2 + 1:]


def bisa_pindah(teks, indeks_blok, arah):
    return 0 <= indeks_blok + arah < len(pecah_blok(teks))


def pindah_blok(teks, indeks_blok, arah):
    """Tukar blok dengan tetangganya (arah -1 naik, +1 turun). Tabel pindah utuh. Di batas, teks tidak berubah."""
    blok = pecah_blok(teks)
    if not (0 <= indeks_blok < len(blok) and 0 <= indeks_blok + arah < len(blok)):
        return teks
    x, y = blok[indeks_blok], blok[indeks_blok + arah]
    return "\n".join(_tukar(_baris(teks), (x["baris_awal"], x["baris_akhir"]), (y["baris_awal"], y["baris_akhir"])))


def _bagian(teks):
    """Rentang baris tiap sub-subbab: dari baris judulnya sampai tepat sebelum sub-subbab berikutnya."""
    blok = pecah_blok(teks)
    judul = [k for k, b in enumerate(blok) if b["jenis"] == "subjudul"]
    rentang = {}
    for urut, k in enumerate(judul):
        akhir = blok[judul[urut + 1] - 1]["baris_akhir"] if urut + 1 < len(judul) else blok[-1]["baris_akhir"]
        rentang[k] = (blok[k]["baris_awal"], akhir)
    return judul, rentang


def bisa_pindah_bagian(teks, indeks_blok, arah):
    judul, _ = _bagian(teks)
    return indeks_blok in judul and 0 <= judul.index(indeks_blok) + arah < len(judul)


def pindah_bagian(teks, indeks_blok, arah):
    """Tukar satu sub-subbab, beserta semua baris di bawahnya, dengan sub-subbab di sebelahnya."""
    if not bisa_pindah_bagian(teks, indeks_blok, arah):
        return teks
    judul, rentang = _bagian(teks)
    tetangga = judul[judul.index(indeks_blok) + arah]
    return "\n".join(_tukar(_baris(teks), rentang[indeks_blok], rentang[tetangga]))


def ringkasan_isi(teks):
    """Jumlah paragraf, gambar, dan tabel, untuk konfirmasi sebelum menghapus subbab."""
    jenis = [b["jenis"] for b in pecah_blok(teks)]
    return {"paragraf": jenis.count("paragraf") + jenis.count("daftar"), "gambar": jenis.count("gambar"),
            "tabel": jenis.count("tabel")}


def nomor_blok(data, i, j):
    """{indeks_blok: 'Gambar 4.1' / 'Tabel 4.2' / 'Persamaan (3)' / '4.1.2'} untuk subbab j di bab i (dari 0).

    Aturannya sama dengan generator.bab() dan rujukan.peta_label(): gambar dan tabel per bab, rumus untuk
    seluruh dokumen, subbab tanpa judul dilewati.
    """
    hasil = {}
    no_rumus = 0
    for bi, bab in enumerate(data.get("bab", [])):
        n = {"gambar": 0, "tabel": 0}
        sj = 0
        for si, sub in enumerate(bab.get("subbab", [])):
            if not (sub.get("judul") or "").strip():
                continue
            sj += 1
            no_subsub = 0
            for k, b in enumerate(pecah_blok(sub.get("isi"))):
                teks = None
                if b["jenis"] == "rumus":
                    no_rumus += 1
                    teks = f"Persamaan ({no_rumus})"
                elif b["jenis"] in n:
                    n[b["jenis"]] += 1
                    teks = f"{b['jenis'].capitalize()} {bi + 1}.{n[b['jenis']]}"
                elif b["jenis"] == "subjudul":
                    no_subsub += 1
                    teks = f"{bi + 1}.{sj}.{no_subsub}"
                if teks and (bi, si) == (i, j):
                    hasil[k] = teks
    return hasil


def pemakaian_gambar(data):
    """{nama file: ['1.1', '4.2', 'Lampiran 1']} untuk setiap gambar yang dipakai di laporan."""
    pakai = {}
    for bi, bab in enumerate(data.get("bab", []), start=1):
        for si, sub in enumerate(bab.get("subbab", []), start=1):
            for b in pecah_blok(sub.get("isi")):
                if b["jenis"] == "gambar":
                    tempat = pakai.setdefault(b["data"]["file"], [])
                    if f"{bi}.{si}" not in tempat:
                        tempat.append(f"{bi}.{si}")
    for k, lamp in enumerate(data.get("lampiran", []), start=1):
        if lamp.get("gambar"):
            pakai.setdefault(lamp["gambar"], []).append(f"Lampiran {k}")
    return pakai


def nama_bebas(nama, isi, simpanan):
    """Nama untuk menyimpan gambar baru tanpa menimpa gambar lain.

    Nama yang belum dipakai, atau dipakai oleh gambar yang isinya sama, dikembalikan apa adanya. Bila isinya
    berbeda, dicari nama berikutnya: grafik.png -> grafik-2.png -> grafik-3.png.
    """
    nama = nama_aman(nama)
    batang, titik, akhiran = nama.rpartition(".")
    if not titik:
        batang, akhiran = nama, ""
    calon, n = nama, 1
    while calon in simpanan and simpanan[calon] != isi:
        n += 1
        calon = f"{batang}-{n}" + (f".{akhiran}" if titik else "")
    return calon


# ---------------------------------------------------------------------------
# Kunci subbab di session_state. `isian` boleh st.session_state atau dict biasa.
# ---------------------------------------------------------------------------
BAGIAN_SUBBAB = ("judul", "isi")   # semua kunci bab{i}_s{j}_<bagian>; tambah di sini bila subbab punya isian baru


def _salin_subbab(isian, i, dari, ke):
    for bagian in BAGIAN_SUBBAB:
        isian[f"bab{i}_s{ke}_{bagian}"] = isian.get(f"bab{i}_s{dari}_{bagian}", "")


def tukar_subbab(isian, i, j, k):
    """Tukar subbab j dan k di bab i, judul beserta seluruh isinya."""
    n = isian.get(f"bab{i}_n", 0)
    if not (0 <= j < n and 0 <= k < n) or j == k:
        return False
    for bagian in BAGIAN_SUBBAB:
        a, b = f"bab{i}_s{j}_{bagian}", f"bab{i}_s{k}_{bagian}"
        isian[a], isian[b] = isian.get(b, ""), isian.get(a, "")
    return True


def sisip_subbab(isian, i, j):
    """Sisipkan subbab kosong di posisi j (subbab j dan sesudahnya bergeser turun)."""
    n = isian.get(f"bab{i}_n", 0)
    j = max(0, min(j, n))
    for x in range(n, j, -1):
        _salin_subbab(isian, i, x - 1, x)
    for bagian in BAGIAN_SUBBAB:
        isian[f"bab{i}_s{j}_{bagian}"] = ""
    isian[f"bab{i}_n"] = n + 1
    return j


def hapus_subbab(isian, i, j):
    """Hapus subbab j di bab i; subbab sesudahnya bergeser naik."""
    n = isian.get(f"bab{i}_n", 0)
    if not 0 <= j < n:
        return False
    for x in range(j, n - 1):
        _salin_subbab(isian, i, x + 1, x)
    for bagian in BAGIAN_SUBBAB:
        isian[f"bab{i}_s{n - 1}_{bagian}"] = ""
    isian[f"bab{i}_n"] = n - 1
    return True
