"""
Rujukan silang: [[REF: #label]] di tengah kalimat diganti "Tabel 4.2", "Gambar 4.1", atau "Persamaan (3)".

- peta_label(data)                 -> ({label: "Tabel 4.2"}, [label yang dipakai lebih dari sekali])
- siapkan(isi, peta, tak_dikenal)  -> isi subbab dengan REF sudah diganti dan label sudah dilepas dari penanda

Label:
- gambar  : otomatis dari nama file tanpa ekstensi, atau argumen berawalan # ([[GAMBAR: a.png | Judul | Sumber | #peta]])
- tabel   : argumen berawalan # ([[TABEL: Judul | Sumber | #statistik]])
- rumus   : argumen berawalan # di ujung ([[RUMUS: Y = a + bX | #regresi]])

Nomor dihitung di sini dengan aturan yang sama persis dengan generator.bab() dan preview.kerangka(): gambar dan
tabel per bab, rumus berurutan untuk seluruh dokumen, subbab tanpa judul dilewati. generator.py dan preview.py
memanggil siapkan() sebelum mengurai isi, jadi penanda tanpa label dan tanpa REF diproses persis seperti dulu.
"""

import re

RE_GAMBAR = re.compile(r"^\[\[\s*GAMBAR\s*:(.*)\]\]$", re.I)
RE_TABEL_BUKA = re.compile(r"^\[\[\s*TABEL\s*:(.*)\]\]$", re.I)
RE_TABEL_TUTUP = re.compile(r"^\[\[\s*/\s*TABEL\s*\]\]$", re.I)
RE_RUMUS = re.compile(r"^\[\[\s*RUMUS\s*:(.*)\]\]$", re.I)
RE_REF = re.compile(r"\[\[\s*REF\s*:\s*#?([^\]\s]+)\s*\]\]", re.I)
RE_LABEL = re.compile(r"^#([\w\-.]+)$")
RE_LABEL_RUMUS = re.compile(r"\s*\|\s*#([\w\-.]+)\s*$")   # hanya di ujung, karena rumus boleh memuat | (nilai mutlak)

# Rujukan yang labelnya tidak dikenal dibungkus dua karakter ini, lalu ditulis merah miring
# oleh generator._tulis_inline() dan preview._inline().
BUKA, TUTUP = "", ""


def _kunci(label):
    return label.strip().lstrip("#").lower()


def pisah_label(argumen):
    """'Judul | Sumber | #statistik' -> ('Judul | Sumber', 'statistik'). Tanpa label, argumen kembali apa adanya."""
    bagian = [x.strip() for x in argumen.split("|")]
    label = [RE_LABEL.match(x).group(1) for x in bagian if RE_LABEL.match(x)]
    if not label:
        return argumen, None
    return " | ".join(x for x in bagian if not RE_LABEL.match(x)), _kunci(label[0])


def pisah_label_rumus(rumus):
    m = RE_LABEL_RUMUS.search(rumus)
    return (rumus[: m.start()], _kunci(m.group(1))) if m else (rumus, None)


def _telusuri(isi):
    """Hasilkan (jenis, argumen) untuk setiap penanda bernomor di satu isi subbab, urut kemunculan."""
    dalam_tabel = False
    for baris in (isi or "").splitlines():
        b = baris.strip()
        if dalam_tabel:
            dalam_tabel = not RE_TABEL_TUTUP.match(b)
            continue
        for jenis, pola in (("gambar", RE_GAMBAR), ("tabel", RE_TABEL_BUKA), ("rumus", RE_RUMUS)):
            m = pola.match(b)
            if m:
                dalam_tabel = jenis == "tabel"
                yield jenis, m.group(1)
                break


def peta_label(data):
    peta, ganda, eksplisit = {}, [], set()
    no_rumus = 0
    for bi, bab in enumerate(data.get("bab", []), start=1):
        n = {"tabel": 0, "gambar": 0}
        for sub in bab.get("subbab", []):
            if not (sub.get("judul") or "").strip():
                continue
            for jenis, argumen in _telusuri(sub.get("isi")):
                if jenis == "rumus":
                    no_rumus += 1
                    teks, (_, label) = f"Persamaan ({no_rumus})", pisah_label_rumus(argumen)
                    bawaan = None
                else:
                    n[jenis] += 1
                    teks, (sisa, label) = f"{jenis.capitalize()} {bi}.{n[jenis]}", pisah_label(argumen)
                    berkas = sisa.split("|")[0].strip() if jenis == "gambar" else ""
                    bawaan = _kunci(berkas.rsplit(".", 1)[0]) if berkas else None
                if label:
                    if label in eksplisit and label not in ganda:
                        ganda.append(label)
                    if label not in eksplisit:
                        eksplisit.add(label)
                        peta[label] = teks      # label yang ditulis sendiri menang atas label dari nama file
                if bawaan and bawaan not in eksplisit:
                    peta.setdefault(bawaan, teks)
    return peta, ganda


def siapkan(isi, peta, tak_dikenal=None):
    """Ganti [[REF: #label]] dan lepaskan label dari penanda. tak_dikenal (list) diisi label yang tidak ditemukan."""
    isi = isi or ""
    if "#" not in isi and "[[REF" not in isi.upper():
        return isi      # jalur cepat: isi lama tanpa fitur ini tidak disentuh sama sekali

    def ganti(m):
        label = _kunci(m.group(1))
        if label in peta:
            return peta[label]
        if tak_dikenal is not None and label not in tak_dikenal:
            tak_dikenal.append(label)
        return f"{BUKA}[rujukan #{label} tidak ditemukan]{TUTUP}"

    hasil = []
    for baris in isi.splitlines():
        baris = RE_REF.sub(ganti, baris)
        b = baris.strip()
        m = RE_GAMBAR.match(b) or RE_TABEL_BUKA.match(b)
        if m:
            sisa, label = pisah_label(m.group(1))
            if label:
                baris = b[: m.start(1)] + " " + sisa + "]]"
        else:
            m = RE_RUMUS.match(b)
            if m:
                sisa, label = pisah_label_rumus(m.group(1))
                if label:
                    baris = b[: m.start(1)] + sisa + "]]"
        hasil.append(baris)
    return "\n".join(hasil)
