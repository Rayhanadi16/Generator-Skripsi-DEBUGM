"""
Impor daftar pustaka dari file ekspor Zotero atau Mendeley.

- baca_bib(teks)                   -> (daftar isian, daftar peringatan) dari BibTeX (.bib)
- baca_ris(teks)                   -> (daftar isian, daftar peringatan) dari RIS (.ris)
- baca_berkas(nama_file, isi_bytes) -> memilih pembaca dari ekstensi file

isian memakai kunci yang sama dengan pustaka.KOSONG, jadi bisa langsung diberikan ke pustaka.format_apa().
Entri yang rusak dilewati dan dicatat di daftar peringatan; impor tidak pernah gagal karena satu entri.
"""

import re
import unicodedata

from pustaka import JENIS, KOSONG, rapikan_doi

ARTIKEL, BUKU, LAIN = JENIS


class GagalImpor(Exception):
    """Pesannya sudah siap ditampilkan ke pengguna."""


# ---------------------------------------------------------------------------
# Pembersih LaTeX
# ---------------------------------------------------------------------------
AKSEN = {"'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302", "~": "\u0303", "c": "\u0327",
         "v": "\u030c", "u": "\u0306", "=": "\u0304", ".": "\u0307", "r": "\u030a", "H": "\u030b", "k": "\u0328"}
HURUF_KHUSUS = {"ss": "ß", "o": "ø", "O": "Ø", "ae": "æ", "AE": "Æ", "aa": "å", "AA": "Å", "l": "ł", "L": "Ł",
                "i": "ı", "j": "ȷ"}
RE_AKSEN = re.compile(r"""\\(['`"^~=.]|[cvurHk](?![A-Za-z]))\s*\{?\\?([A-Za-z])\}?""")
RE_HURUF_KHUSUS = re.compile(r"\\(ss|ae|AE|aa|AA|o|O|l|L|i|j)(?![A-Za-z])\s*(?:\{\})?")


def bersihkan_latex(teks):
    teks = teks or ""
    teks = RE_AKSEN.sub(lambda m: unicodedata.normalize("NFC", m.group(2) + AKSEN[m.group(1)]), teks)
    teks = RE_HURUF_KHUSUS.sub(lambda m: HURUF_KHUSUS[m.group(1)], teks)
    for dari, ke in (("\\&", "&"), ("\\%", "%"), ("\\_", "_"), ("\\$", "$"), ("\\#", "#"), ("---", "–"), ("--", "–"),
                     ("~", " "), ("``", "“"), ("''", "”")):
        teks = teks.replace(dari, ke)
    teks = re.sub(r"\\(?:textit|emph|textbf|textsc|mathrm|text)\s*\{([^{}]*)\}", r"\1", teks)
    teks = re.sub(r"\\[A-Za-z]+\s*", "", teks)   # perintah lain yang tidak dikenal dibuang
    teks = teks.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", teks).strip()


def _tahun(teks):
    m = re.search(r"(1[5-9]|20)\d{2}", teks or "")
    return m.group(0) if m else ""


def _tautan(doi, url):
    doi = rapikan_doi(doi or "")
    return f"https://doi.org/{doi}" if doi else (url or "").strip()


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------
def _sampai_tutup(teks, awal, buka="{", tutup="}"):
    """Indeks tepat setelah kurung penutup yang berpasangan dengan kurung di teks[awal], atau -1."""
    dalam = 0
    i = awal
    while i < len(teks):
        c = teks[i]
        if c == "\\":
            i += 2
            continue
        if c == buka:
            dalam += 1
        elif c == tutup:
            dalam -= 1
            if dalam == 0:
                return i + 1
        i += 1
    return -1


def _field_bib(badan):
    """Urai 'nama = {nilai}, nama = "nilai", nama = 2021' menjadi dict (nama huruf kecil)."""
    hasil, i = {}, 0
    while i < len(badan):
        m = re.compile(r"\s*,?\s*([A-Za-z][\w\-]*)\s*=\s*").match(badan, i)
        if not m:
            break
        nama, i = m.group(1).lower(), m.end()
        if i >= len(badan):
            break
        if badan[i] == "{":
            akhir = _sampai_tutup(badan, i)
            if akhir < 0:
                raise ValueError("kurung kurawal tidak berpasangan")
            nilai, i = badan[i + 1: akhir - 1], akhir
        elif badan[i] == '"':
            j = i + 1
            dalam = 0
            while j < len(badan) and not (badan[j] == '"' and dalam == 0):
                dalam += {"{": 1, "}": -1}.get(badan[j], 0)
                j += 2 if badan[j] == "\\" else 1
            if j >= len(badan):
                raise ValueError("tanda kutip tidak ditutup")
            nilai, i = badan[i + 1: j], j + 1
        else:
            m2 = re.compile(r"[^,]*").match(badan, i)
            nilai, i = m2.group(0).strip(), m2.end()
        hasil.setdefault(nama, nilai)
    return hasil


def _pisah_penulis_bib(teks):
    """Pisahkan pada ' and ' yang tidak berada di dalam kurung kurawal."""
    bagian, dalam, awal = [], 0, 0
    for m in re.finditer(r"[{}]|\s+and\s+", teks):
        if m.group(0) == "{":
            dalam += 1
        elif m.group(0) == "}":
            dalam -= 1
        elif dalam == 0:
            bagian.append(teks[awal: m.start()])
            awal = m.end()
    bagian.append(teks[awal:])
    return [b.strip() for b in bagian if b.strip()]


def _penulis_bib(teks):
    """-> (baris penulis 'Belakang, Depan', lembaga?)"""
    nama, lembaga = [], []
    for p in _pisah_penulis_bib(teks or ""):
        if p.lower() == "others":
            continue
        if p.startswith("{") and _sampai_tutup(p, 0) == len(p):   # {Bank Indonesia}: nama lembaga, jangan dibalik
            nama.append(bersihkan_latex(p))
            lembaga.append(True)
            continue
        lembaga.append(False)
        p = bersihkan_latex(p)
        if "," in p:
            nama.append(re.sub(r"\s*,\s*", ", ", p))
            continue
        kata = p.split()
        if len(kata) == 1:
            nama.append(p)
            continue
        awal_belakang = next((i for i, k in enumerate(kata[:-1]) if k[:1].islower()), len(kata) - 1)   # van, de, bin
        nama.append(f"{' '.join(kata[awal_belakang:])}, {' '.join(kata[:awal_belakang])}")
    return "\n".join(nama), bool(nama) and all(lembaga)


def _isian_bib(jenis_bib, f):
    b = lambda k: bersihkan_latex(f.get(k, ""))   # noqa: E731
    isian = dict(KOSONG)
    isian["penulis"], isian["lembaga"] = _penulis_bib(f.get("author") or f.get("editor") or "")
    isian["judul"] = b("title")
    isian["tahun"] = _tahun(f.get("year") or f.get("date") or "")
    if jenis_bib == "article":
        isian["jenis"] = ARTIKEL
        isian["wadah"] = b("journal") or b("journaltitle")
    elif jenis_bib in ("book", "inbook"):
        isian["jenis"] = BUKU
        isian["wadah"] = b("publisher")
    else:
        isian["jenis"] = LAIN
        isian["wadah"] = b("publisher") or b("institution") or b("organization") or b("school") or b("howpublished")
    isian["volume"], isian["nomor"] = b("volume"), b("number") or b("issue")
    isian["halaman"] = b("pages").replace("–", "-")
    isian["tautan"] = _tautan(f.get("doi"), bersihkan_latex(f.get("url", "")))
    return isian


def baca_bib(teks):
    daftar, peringatan = [], []
    i = 0
    for no, m in enumerate(re.finditer(r"@\s*([A-Za-z]+)\s*\{", teks or ""), start=1):
        if m.start() < i:      # '@' di dalam entri sebelumnya (mis. alamat email)
            continue
        jenis = m.group(1).lower()
        akhir = _sampai_tutup(teks, m.end() - 1)
        if jenis in ("comment", "string", "preamble"):
            i = akhir if akhir > 0 else m.end()
            continue
        if akhir < 0:
            peringatan.append(f"Entri @{jenis} di sekitar baris {teks.count(chr(10), 0, m.start()) + 1} dilewati: "
                              "kurung kurawalnya tidak ditutup.")
            continue
        i = akhir
        badan = teks[m.end(): akhir - 1]
        kunci, _, sisa = badan.partition(",")
        try:
            isian = _isian_bib(jenis, _field_bib(sisa))
        except ValueError as e:
            peringatan.append(f"Entri '{kunci.strip()}' dilewati: {e}.")
            continue
        if not isian["judul"]:
            peringatan.append(f"Entri '{kunci.strip()}' dilewati: tidak ada judul.")
            continue
        daftar.append(isian)
    return daftar, peringatan


# ---------------------------------------------------------------------------
# RIS
# ---------------------------------------------------------------------------
RE_RIS = re.compile(r"^([A-Z][A-Z0-9])\s\s?-\s?(.*)$")
RIS_ARTIKEL = {"JOUR", "EJOUR", "JFULL", "MGZN", "NEWS", "ABST", "INPR"}
RIS_BUKU = {"BOOK", "CHAP", "EBOOK", "ECHAP", "EDBOOK"}


def _isian_ris(tag):
    satu = lambda *kunci: next((tag[k][0].strip() for k in kunci if tag.get(k)), "")   # noqa: E731
    isian = dict(KOSONG)
    penulis = [p.strip().rstrip(",") for k in ("AU", "A1") for p in tag.get(k, []) if p.strip()]
    isian["penulis"] = "\n".join(re.sub(r"\s*,\s*", ", ", p) for p in penulis)
    isian["lembaga"] = bool(penulis) and all("," not in p for p in penulis)
    isian["judul"] = satu("TI", "T1", "CT")
    isian["tahun"] = _tahun(satu("PY", "Y1", "DA"))
    jenis = satu("TY").upper()
    if jenis in RIS_ARTIKEL:
        isian["jenis"], isian["wadah"] = ARTIKEL, satu("JO", "JF", "T2", "JA")
    elif jenis in RIS_BUKU:
        isian["jenis"], isian["wadah"] = BUKU, satu("PB")
    else:
        isian["jenis"], isian["wadah"] = LAIN, satu("PB", "T2")
    isian["volume"], isian["nomor"] = satu("VL"), satu("IS")
    awal, akhir = satu("SP"), satu("EP")
    isian["halaman"] = f"{awal}-{akhir}" if awal and akhir and akhir != awal else awal
    isian["tautan"] = _tautan(satu("DO"), satu("UR"))
    return isian


def baca_ris(teks):
    daftar, peringatan = [], []
    tag, no = None, 0

    def tutup():
        nonlocal tag
        if tag is None:
            return
        isian = _isian_ris(tag)
        if isian["judul"]:
            daftar.append(isian)
        else:
            peringatan.append(f"Entri ke-{no} dilewati: tidak ada judul.")
        tag = None

    for baris in (teks or "").splitlines():
        m = RE_RIS.match(baris.strip("\ufeff").rstrip())
        if not m:
            continue   # baris lanjutan dan baris kosong diabaikan
        kunci, nilai = m.group(1), m.group(2)
        if kunci == "TY":
            if tag is not None:
                peringatan.append(f"Entri ke-{no} tidak ditutup dengan ER, tetap dibaca.")
            tutup()
            no += 1
            tag = {"TY": [nilai]}
        elif kunci == "ER":
            tutup()
        elif tag is not None:
            tag.setdefault(kunci, []).append(nilai)
    tutup()
    return daftar, peringatan


# ---------------------------------------------------------------------------
def baca_berkas(nama_file, isi_bytes):
    ekstensi = (nama_file or "").lower().rsplit(".", 1)[-1]
    if ekstensi not in ("bib", "ris"):
        raise GagalImpor("Jenis file tidak dikenali. Pakai file .bib (BibTeX) atau .ris.")
    try:
        teks = isi_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        teks = isi_bytes.decode("cp1252", errors="replace")
    daftar, peringatan = (baca_bib if ekstensi == "bib" else baca_ris)(teks)
    if not daftar and not peringatan:
        raise GagalImpor("Tidak ada referensi yang terbaca di file ini.")
    return daftar, peringatan
