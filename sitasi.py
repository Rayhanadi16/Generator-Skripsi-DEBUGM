"""
Cek sitasi: mencocokkan kutipan di isi bab dengan entri daftar pustaka (gaya APA 7).

- cari_kutipan(teks)   -> daftar {"nama", "tahun", "teks"}; nama = penulis pertama atau nama lembaga
- kunci_pustaka(entri) -> (nama belakang penulis pertama atau nama lembaga, tahun) dari satu baris APA
- periksa(data)        -> {"tanpa_pustaka": [...], "tidak_dikutip": [...], "cocok": n, "jumlah": n, "ada_isi": bool}

Fitur ini hanya melapor. Isi bab dan daftar pustaka tidak pernah diubah.
"""

import re
import unicodedata

TAHUN = r"(?:19|20)\d{2}[a-z]?|t\.t\.|n\.d\."
KATA = r"[A-ZÀ-Ý][\w'’\-]*"   # satu kata berawalan huruf besar: Santoso, Al-Farisi, BPS

# (Santoso, 2021) (Santoso & Putri, 2021) (Santoso et al., 2021, hlm. 5) (Bank Indonesia, 2023)
RE_KURUNG = re.compile(r"\(([^()]*)\)")
RE_BAGIAN = re.compile(
    rf"^(?:(?:lihat|dalam|misalnya|mis\.|e\.g\.,?)\s+)?(?P<nama>[A-ZÀ-Ý][^()\d]*?),?\s+(?P<tahun>{TAHUN})(?:\s*[,:].*)?$")
# Santoso (2021), Santoso dan Putri (2021), Santoso dkk. (2021), Bank Indonesia (2023)
RE_NARATIF = re.compile(
    rf"(?P<nama>(?:{KATA}\s+){{0,3}}{KATA}(?:\s+(?:dan|and|&)\s+(?:{KATA}\s+){{0,2}}{KATA}|\s+et\s+al\.?|\s+dkk\.?)?)"
    rf"\s*\((?P<tahun>{TAHUN})(?:\s*[,:][^()]*)?\)")
RE_PEMISAH_PENULIS = re.compile(r"\s*(?:,|&|\bdan\b|\band\b|\bet\s+al\b|\bdkk\b)")
RE_TAHUN_ENTRI = re.compile(rf"\(\s*({TAHUN})[^)]*\)")
RE_GAMBAR = re.compile(r"^\[\[\s*GAMBAR\s*:(.*)\]\]$", re.I)
RE_TABEL_BUKA = re.compile(r"^\[\[\s*TABEL\s*:(.*)\]\]$", re.I)
RE_TABEL_TUTUP = re.compile(r"^\[\[\s*/\s*TABEL\s*\]\]$", re.I)
RE_PENANDA = re.compile(r"^\[\[.*\]\]$")

# kata sebelum "(2021)" yang bukan nama penulis, dan awalan sumber yang berarti data sendiri
BUKAN_NAMA = {"tahun", "periode", "bulan", "tabel", "gambar", "lampiran", "bab", "data", "sumber", "semester",
              "triwulan", "kuartal", "januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus",
              "september", "oktober", "november", "desember", "persamaan", "rumus"}
DATA_SENDIRI = ("data primer", "data sekunder", "data diolah", "diolah", "olahan", "hasil olah", "hasil pengolahan",
                "dokumentasi", "dokumen pribadi", "penulis", "peneliti")
ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _polos(teks):
    """Huruf kecil, tanpa diakritik dan tanda baca, untuk pencocokan."""
    teks = unicodedata.normalize("NFKD", teks or "")
    teks = "".join(c for c in teks if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", teks)).strip()


def _tahun_polos(tahun):
    tahun = tahun.lower().replace(" ", "")
    return "n.d." if tahun in ("t.t.", "n.d.") else tahun


def _penulis_pertama(nama):
    return RE_PEMISAH_PENULIS.split(nama.strip(), maxsplit=1)[0].strip(" .,")


def _layak(nama):
    kata = _polos(nama).split()
    return bool(kata) and kata[-1] not in BUKAN_NAMA and kata[0] not in ("data", "sumber", "hasil")


def cari_kutipan(teks):
    """Semua kutipan di satu potong teks, urut kemunculan."""
    hasil = []
    for m in RE_KURUNG.finditer(teks or ""):
        for bagian in m.group(1).split(";"):
            b = RE_BAGIAN.match(bagian.strip())
            if b and _layak(_penulis_pertama(b.group("nama"))):
                hasil.append({"nama": _penulis_pertama(b.group("nama")), "tahun": b.group("tahun"),
                              "teks": f"({bagian.strip()})", "posisi": m.start()})
    for m in RE_NARATIF.finditer(teks or ""):
        nama = _penulis_pertama(m.group("nama"))
        if _layak(nama):
            hasil.append({"nama": nama, "tahun": m.group("tahun"), "teks": m.group(0).strip(), "posisi": m.start()})
    hasil.sort(key=lambda k: k.pop("posisi"))
    return hasil


def _kutipan_sumber(sumber):
    """Kolom Sumber pada penanda GAMBAR/TABEL: 'KSEI, 2025' atau 'Santoso (2021)'. Data sendiri bukan kutipan."""
    hasil = []
    for bagian in (sumber or "").split(";"):
        bagian = bagian.strip()
        if not bagian or _polos(bagian).startswith(DATA_SENDIRI) or any(k in _polos(bagian) for k in ("diolah", "olahan")):
            continue
        ketemu = cari_kutipan(bagian)
        if not ketemu:
            b = RE_BAGIAN.match(bagian)
            if b and _layak(_penulis_pertama(b.group("nama"))):
                ketemu = [{"nama": _penulis_pertama(b.group("nama")), "tahun": b.group("tahun"), "teks": bagian}]
        hasil += ketemu
    return hasil


def _bagian_penulis(entri):
    """Potongan entri sebelum tahun, tanpa penanda miring."""
    entri = (entri or "").replace("*", "").strip()
    m = RE_TAHUN_ENTRI.search(entri)
    return (entri[: m.start()] if m else entri).strip(), (m.group(1) if m else "")


def kunci_pustaka(entri):
    """'Santoso, B., & Putri, A. (2021). Judul' -> ('Santoso', '2021'); 'Bank Indonesia. (2023).' -> ('Bank Indonesia', '2023')."""
    penulis, tahun = _bagian_penulis(entri)
    m = re.match(r"^([^,]+),\s*[A-ZÀ-Ý]\.", penulis)   # "Belakang, D." berarti orang
    if m:
        return m.group(1).strip(), tahun
    nama = re.sub(r"\s*\([^)]*\)\s*", " ", penulis).strip(" .,")   # buang singkatan dalam kurung
    return nama, tahun


def _alias(entri):
    """Nama lain yang sah untuk mengutip entri ini: singkatan dalam kurung dan huruf awal nama lembaga."""
    penulis, _ = _bagian_penulis(entri)
    nama, _ = kunci_pustaka(entri)
    alias = {_polos(nama)}
    if not re.match(r"^([^,]+),\s*[A-ZÀ-Ý]\.", penulis):
        alias |= {_polos(s) for s in re.findall(r"\(([^)]+)\)", penulis)}
        awal = "".join(k[0] for k in nama.split() if k[:1].isupper())
        if len(awal) >= 2:
            alias.add(awal.lower())
    return {a for a in alias if a}


def _cocok(kutipan, entri):
    _, tahun = kunci_pustaka(entri)
    tk, te = _tahun_polos(kutipan["tahun"]), _tahun_polos(tahun or "")
    if tk != te and tk.rstrip("abcdefghijklmnopqrstuvwxyz") != te.rstrip("abcdefghijklmnopqrstuvwxyz"):
        return False
    kata = _polos(kutipan["nama"]).split()
    # kutipan naratif bisa terbawa kata di depannya ("Menurut Santoso"), jadi yang dicocokkan ekornya
    return any(kata[-len(a.split()):] == a.split() for a in _alias(entri))


def periksa(data):
    entri = [b.strip() for b in (data.get("daftar_pustaka") or "").splitlines() if b.strip()]
    kutipan, ada_isi = [], False
    for bi, bab in enumerate(data.get("bab", []), start=1):
        for sj, sub in enumerate(bab.get("subbab", []), start=1):
            lokasi = f"Bab {ROMAWI[bi] if bi < len(ROMAWI) else bi}, subbab {bi}.{sj}"
            dalam_tabel = False
            for baris in (sub.get("isi") or "").splitlines():
                b = baris.strip()
                if not b:
                    continue
                ada_isi = True
                ketemu = []
                if RE_TABEL_TUTUP.match(b):
                    dalam_tabel = False
                elif RE_TABEL_BUKA.match(b):
                    dalam_tabel = True
                    bagian = [x.strip() for x in RE_TABEL_BUKA.match(b).group(1).split("|")]
                    ketemu = _kutipan_sumber(bagian[1] if len(bagian) > 1 else "")
                elif RE_GAMBAR.match(b):
                    bagian = [x.strip() for x in RE_GAMBAR.match(b).group(1).split("|")]
                    ketemu = _kutipan_sumber(bagian[2] if len(bagian) > 2 else "")
                elif not dalam_tabel and not RE_PENANDA.match(b):
                    ketemu = cari_kutipan(b)
                kutipan += [{**k, "lokasi": lokasi} for k in ketemu]

    dikutip = set()
    tanpa, sudah = [], set()
    for k in kutipan:
        cocok = [i for i, e in enumerate(entri) if _cocok(k, e)]
        dikutip.update(cocok)
        kunci = (_polos(k["nama"]), _tahun_polos(k["tahun"]), k["lokasi"])
        if not cocok and kunci not in sudah:
            sudah.add(kunci)
            tanpa.append({"kutipan": k["teks"], "lokasi": k["lokasi"]})
    tidak = []
    for i, e in enumerate(entri):
        if i not in dikutip:
            nama, tahun = kunci_pustaka(e)
            tidak.append({"entri": f"{nama} ({tahun or 'tanpa tahun'})", "baris": e})
    n_tanpa = sum(1 for k in kutipan if not any(_cocok(k, e) for e in entri))
    return {"tanpa_pustaka": tanpa, "tidak_dikutip": tidak if ada_isi else [],
            "cocok": len(kutipan) - n_tanpa, "jumlah": len(kutipan), "ada_isi": ada_isi}


def kalimat_cek(hasil, batas=5):
    """Kalimat untuk daftar 'hal perlu diperhatikan'. Entri tak dikutip diringkas bila banyak."""
    kalimat = [f"Kutipan {k['kutipan']} di {k['lokasi']} tidak ada di daftar pustaka." for k in hasil["tanpa_pustaka"]]
    tidak = hasil["tidak_dikutip"]
    if len(tidak) > batas:
        kalimat.append(f"{len(tidak)} entri daftar pustaka tidak pernah dikutip di isi bab. "
                       "Rinciannya ada di tab Pustaka & lampiran.")
    else:
        kalimat += [f"Daftar pustaka berisi {t['entri']}, tetapi tidak pernah dikutip di isi bab." for t in tidak]
    return kalimat
