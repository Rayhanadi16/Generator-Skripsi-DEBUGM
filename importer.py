"""
Pembaca draft mentah (.docx) → struktur laporan TA.

Lapis 1 (aturan pasti): Styles Word (Heading 1/2/3), pola "BAB II", "2.1 Judul",
         "Tabel 3.1 ...", "Gambar 4.2 ...", "Sumber: ...", "Kata kunci:", "DAFTAR PUSTAKA", dst.
Lapis 2 (tebakan): ciri paragraf (pendek, tebal, kapital) + kata khas tiap bagian
         ("bertujuan", "kuesioner", "signifikan", ...) + konteks paragraf sebelumnya.

Setiap blok mendapat label tujuan + skor keyakinan (0–1) + alasan, supaya
pengguna bisa mengoreksi di layar review sebelum diterapkan ke form.

Fungsi utama:
    hasil = lacak_draft(bytes_docx)
    data, gambar = susun_data(hasil, pilihan)   # pilihan = {id_blok: kunci_tujuan}
"""

import difflib
import io
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from generator import STRUKTUR_BAB_BAWAAN, hitung_kata, judul_kapital

YAKIN_TINGGI = 0.85   # hijau
YAKIN_SEDANG = 0.6    # di bawah YAKIN_TINGGI = kuning; 0 = merah (belum ditempatkan)

# ---------------------------------------------------------------------------
# Pola Lapis 1
# ---------------------------------------------------------------------------
RE_BAB = re.compile(r"^BAB\s+([IVXL]+|\d+)\b[\s.:\-–—]*(.*)$", re.I)
RE_SUB = re.compile(r"^(\d+)\.(\d+)\.?\s+(\S.*)$")
RE_SUBSUB = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.?\s+(\S.*)$")
RE_SUB_HURUF = re.compile(r"^([A-H])\.\s+(\S.*)$")
RE_CAP_TABEL = re.compile(r"^Tabel\s+\d+(?:[.\-]\d+)*\.?\s*[:.\-–]?\s*(.*)$", re.I)
RE_CAP_GAMBAR = re.compile(r"^(?:Gambar|Grafik|Bagan)\s+\d+(?:[.\-]\d+)*\.?\s*[:.\-–]?\s*(.*)$", re.I)
RE_SUMBER = re.compile(r"^Sumber\s*:\s*(.+)$", re.I)
RE_KATA_KUNCI = re.compile(r"^Kata[\s\-]*kunci\s*:?\s*(.*)$", re.I)
RE_KEYWORDS = re.compile(r"^Key[\s\-]*words?\s*:?\s*(.*)$", re.I)
RE_LAMPIRAN = re.compile(r"^Lampiran\s+(\d+|[A-Z])\s*[.:\-–]?\s*(.*)$", re.I)
RE_CATATAN = re.compile(r"^(\[?\s*(catatan|note|todo|revisi|komentar|cek lagi|tanya dosen)\b|\(\s*catatan)", re.I)
RE_TOC = re.compile(r"(\.{3,}|…{2,}|\t)\s*[ivxlc\d]+\s*$", re.I)
RE_PUSTAKA = re.compile(r"^[A-Z][^()]{1,150}?\(\s*(\d{4}[a-z]?|n\.?\s?d\.?|t\.?\s?t\.?)\s*\)")

BAGIAN_DEPAN = {
    "KATA PENGANTAR": "kata_pengantar", "PRAKATA": "kata_pengantar",
    "INTISARI": "intisari", "ABSTRAK": "intisari", "RINGKASAN": "intisari",
    "ABSTRACT": "abstract",
    "DAFTAR PUSTAKA": "pustaka", "REFERENSI": "pustaka", "DAFTAR REFERENSI": "pustaka",
    "BIBLIOGRAFI": "pustaka", "REFERENCES": "pustaka", "DAFTAR RUJUKAN": "pustaka",
    "LAMPIRAN": "lampiran", "LAMPIRAN-LAMPIRAN": "lampiran",
    "DAFTAR ISI": "abaikan", "DAFTAR TABEL": "abaikan", "DAFTAR GAMBAR": "abaikan",
    "DAFTAR LAMPIRAN": "abaikan", "DAFTAR ISTILAH": "abaikan", "GLOSARIUM": "abaikan",
    "HALAMAN PENGESAHAN": "abaikan", "LEMBAR PENGESAHAN": "abaikan", "HALAMAN PERSETUJUAN": "abaikan",
    "PERNYATAAN BEBAS PLAGIASI": "abaikan", "HALAMAN PERNYATAAN": "abaikan",
    "PERNYATAAN KEASLIAN": "abaikan", "HALAMAN JUDUL": "abaikan", "MOTTO": "abaikan",
    "HALAMAN PERSEMBAHAN": "abaikan", "PERSEMBAHAN": "abaikan",
}

SINONIM_BAB = {
    0: ["pendahuluan"],
    1: ["tinjauan pustaka", "kajian pustaka", "landasan teori dan pengembangan hipotesis", "kajian teori",
        "tinjauan pustaka dan pengembangan hipotesis"],
    2: ["metode penelitian", "metodologi penelitian", "metode", "metodologi"],
    3: ["hasil dan pembahasan", "hasil penelitian dan pembahasan", "analisis dan pembahasan", "pembahasan"],
    4: ["kesimpulan dan saran", "penutup", "simpulan dan saran", "kesimpulan dan rekomendasi", "simpulan"],
}

SINONIM_SUBBAB = {
    "Latar Belakang": ["latar belakang", "latar belakang masalah"],
    "Rumusan Masalah": ["rumusan masalah", "perumusan masalah", "identifikasi masalah", "permasalahan"],
    "Pertanyaan Penelitian": ["pertanyaan penelitian", "research question"],
    "Tujuan Penelitian": ["tujuan penelitian", "tujuan"],
    "Manfaat Penelitian": ["manfaat penelitian", "manfaat", "kegunaan penelitian"],
    "Kondisi Umum/Deskripsi Topik Penelitian": ["kondisi umum", "deskripsi topik", "gambaran umum",
                                                "profil", "state of the art"],
    "Landasan Teori": ["landasan teori", "kerangka teori", "kajian teori", "tinjauan teori"],
    "Penelitian Terdahulu": ["penelitian terdahulu", "penelitian sebelumnya", "kajian empiris",
                             "tinjauan penelitian terdahulu"],
    "Hipotesis": ["hipotesis", "pengembangan hipotesis", "hipotesis penelitian"],
    "Desain Penelitian": ["desain penelitian", "rancangan penelitian", "jenis penelitian", "pendekatan penelitian"],
    "Jenis dan Sumber Data": ["jenis dan sumber data", "sumber data", "jenis data", "data penelitian"],
    "Teknik Pengumpulan Data": ["teknik pengumpulan data", "metode pengumpulan data", "pengumpulan data",
                                "populasi dan sampel"],
    "Teknik Analisis Data": ["teknik analisis data", "metode analisis data", "analisis data",
                             "definisi operasional variabel", "alat analisis"],
    "Deskripsi Data": ["deskripsi data", "statistik deskriptif", "gambaran responden", "karakteristik responden"],
    "Hasil Analisis": ["hasil analisis", "hasil penelitian", "hasil uji", "analisis data penelitian"],
    "Interpretasi dan Pembahasan": ["interpretasi dan pembahasan", "pembahasan", "diskusi"],
    "Kesimpulan": ["kesimpulan", "simpulan"],
    "Saran": ["saran", "rekomendasi", "implikasi"],
    "Keterbatasan Penelitian": ["keterbatasan penelitian", "keterbatasan", "limitasi",
                                "limitasi dan peluang riset mendatang"],
}

# Lapis 2: kata khas (frasa kuat = bobot 3, frasa umum = bobot 1)
KATA_KHAS = {
    (0, "Latar Belakang"): (["latar belakang", "fenomena", "data menunjukkan", "berdasarkan data"],
                            ["meningkat", "menurun", "persen", "%", "perkembangan", "saat ini", "di indonesia",
                             "tahun", "pertumbuhan"]),
    (0, "Rumusan Masalah"): (["rumusan masalah", "permasalahan utama", "masalah dalam penelitian ini",
                              "ruang lingkup penelitian", "batasan penelitian"],
                             ["kesenjangan", "gap", "belum banyak", "masih terbatas", "batasan"]),
    (0, "Pertanyaan Penelitian"): (["pertanyaan penelitian"], ["apakah", "bagaimana", "seberapa besar"]),
    (0, "Tujuan Penelitian"): (["tujuan penelitian", "bertujuan untuk", "tujuan dari penelitian"],
                               ["untuk mengetahui", "untuk menganalisis", "untuk menguji"]),
    (0, "Manfaat Penelitian"): (["manfaat penelitian", "manfaat teoretis", "manfaat teoritis", "manfaat praktis"],
                                ["diharapkan dapat", "kontribusi", "bermanfaat", "menjadi referensi"]),
    (1, "Kondisi Umum/Deskripsi Topik Penelitian"): (["gambaran umum", "kondisi umum", "profil perusahaan",
                                                      "sejarah singkat"], ["didirikan", "berlokasi", "visi", "misi"]),
    (1, "Landasan Teori"): (["landasan teori", "dikemukakan oleh", "didefinisikan sebagai"],
                            ["teori", "menurut", "definisi", "konsep", "merupakan suatu"]),
    (1, "Penelitian Terdahulu"): (["penelitian terdahulu", "penelitian sebelumnya", "dalam penelitiannya"],
                                  ["menemukan bahwa", "hasil penelitian", "et al", "studi oleh", "meneliti"]),
    (1, "Hipotesis"): (["hipotesis", "h1:", "h2:", "h0:", "ha:"], ["dugaan sementara"]),
    (2, "Desain Penelitian"): (["desain penelitian", "pendekatan kuantitatif", "pendekatan kualitatif",
                                "jenis penelitian ini"], ["deskriptif", "studi kasus", "eksplanatori"]),
    (2, "Jenis dan Sumber Data"): (["data primer", "data sekunder", "sumber data"],
                                   ["bps", "world bank", "diperoleh dari", "laporan tahunan"]),
    (2, "Teknik Pengumpulan Data"): (["teknik pengumpulan data", "kuesioner", "teknik sampling",
                                      "purposive sampling", "rumus slovin"],
                                     ["wawancara", "observasi", "populasi", "sampel", "responden"]),
    (2, "Teknik Analisis Data"): (["teknik analisis", "analisis regresi", "uji validitas", "uji reliabilitas",
                                   "definisi operasional"],
                                  ["regresi", "uji t", "uji f", "spss", "eviews", "stata", "skala likert",
                                   "variabel"]),
    (3, "Deskripsi Data"): (["statistik deskriptif", "karakteristik responden", "deskripsi data"],
                            ["rata-rata", "frekuensi", "mayoritas responden", "jenis kelamin", "sebanyak"]),
    (3, "Hasil Analisis"): (["hasil uji", "nilai signifikansi", "r square", "t hitung", "t-hitung",
                             "f hitung", "p-value"],
                            ["signifikan", "koefisien", "diterima", "ditolak", "sig."]),
    (3, "Interpretasi dan Pembahasan"): (["sejalan dengan penelitian", "hal ini sejalan", "temuan ini",
                                          "berbeda dengan penelitian"],
                                         ["mengindikasikan", "hal ini menunjukkan", "pembahasan", "implikasi"]),
    (4, "Kesimpulan"): (["dapat disimpulkan", "disimpulkan bahwa", "kesimpulan"],
                        ["berdasarkan hasil penelitian", "secara keseluruhan"]),
    (4, "Saran"): (["disarankan", "saran bagi", "rekomendasi"], ["sebaiknya", "perlu", "diharapkan pihak"]),
    (4, "Keterbatasan Penelitian"): (["keterbatasan", "penelitian selanjutnya", "penelitian mendatang"],
                                     ["terbatas pada", "belum mencakup"]),
}
KATA_KHAS_DEPAN = {
    "kata_pengantar": (["puji syukur", "terima kasih kepada", "alhamdulillah", "penulis menyadari"],
                       ["rahmat", "karunia", "bimbingan"]),
}
STOPWORD_EN = {"the", "of", "and", "this", "study", "is", "are", "was", "were", "results", "to", "in", "on",
               "which", "that", "with", "by", "aims", "show", "using"}
STOPWORD_ID = {"yang", "dan", "di", "ini", "dengan", "untuk", "dari", "pada", "adalah", "dalam", "penelitian"}


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/ ]", " ", (t or "").lower())).strip()


def _mirip(a, b):
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def cocokkan_subbab(teks):
    """Cari nama subbab baku yang paling mirip. Return (bab_bawaan, nama, skor) atau None."""
    n = _norm(teks)
    terbaik = None
    for bi, bab in enumerate(STRUKTUR_BAB_BAWAAN):
        for nama in bab["subbab"]:
            for s in SINONIM_SUBBAB.get(nama, [nama.lower()]):
                skor = 1.0 if n == s else (0.85 if n.startswith(s + " ") or n.endswith(" " + s) else _mirip(n, s))
                if terbaik is None or skor > terbaik[2]:
                    terbaik = (bi, nama, skor)
    return terbaik if terbaik and terbaik[2] >= 0.78 else None


def cocokkan_bab(teks):
    n = _norm(teks)
    terbaik = None
    for bi, daftar in SINONIM_BAB.items():
        for s in daftar:
            skor = 1.0 if n == s else _mirip(n, s)
            if terbaik is None or skor > terbaik[1]:
                terbaik = (bi, skor)
    return terbaik[0] if terbaik and terbaik[1] >= 0.82 else None


# ---------------------------------------------------------------------------
# Ekstraksi blok
# ---------------------------------------------------------------------------
def _teks_markup(p):
    """Teks paragraf; huruf miring dipertahankan sebagai *...*."""
    hasil, kelompok, miring_now = [], [], None
    def tutup():
        if not kelompok:
            return
        t = "".join(kelompok)
        if miring_now and t.strip():
            kiri = len(t) - len(t.lstrip())
            kanan = len(t) - len(t.rstrip())
            hasil.append(t[:kiri] + "*" + t.strip() + "*" + (t[len(t) - kanan:] if kanan else ""))
        else:
            hasil.append(t)
    for r in p.runs:
        m = bool(r.italic)
        if miring_now is None or m != miring_now:
            tutup()
            kelompok, miring_now = [], m
        kelompok.append(r.text)
    tutup()
    t = "".join(hasil) if p.runs else p.text
    return re.sub(r"\s+", " ", t).strip()


def _ciri(p):
    teks = p.text.strip()
    runs = [r for r in p.runs if r.text.strip()]
    gaya = p.style.name if p.style is not None else ""
    gaya_tebal = bool(p.style is not None and p.style.font.bold)
    tebal = bool(runs) and all((r.bold is True) or (r.bold is None and gaya_tebal) for r in runs)
    huruf = re.sub(r"[^A-Za-z]", "", teks)
    ukuran = max([r.font.size.pt for r in runs if r.font.size] or [0])
    numpr = p._p.pPr.numPr if p._p.pPr is not None else None
    if numpr is None and p.style is not None:
        spr = p.style.element.pPr
        numpr = spr.numPr if spr is not None else None
    ilvl = None
    if numpr is not None and numpr.ilvl is not None:
        ilvl = int(numpr.ilvl.val)
    elif numpr is not None:
        ilvl = 0
    return {
        "gaya": gaya,
        "tebal": tebal,
        "kapital": len(huruf) >= 3 and huruf.isupper(),
        "tengah": p.alignment == WD_ALIGN_PARAGRAPH.CENTER,
        "ukuran": ukuran,
        "kata": len(teks.split()),
        "list_lvl": ilvl,
    }


def ekstrak_blok(data_docx):
    doc = Document(io.BytesIO(data_docx))
    blok, gambar = [], {}
    n_gbr = 0
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            p = Paragraph(el, doc)
            # gambar yang ditempel di paragraf
            for blip in el.iter(qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                part = doc.part.related_parts.get(rid) if rid else None
                if part is None:
                    continue
                n_gbr += 1
                ext = (part.content_type.split("/")[-1] or "png").replace("jpeg", "jpg")
                if ext not in ("png", "jpg", "gif", "bmp"):
                    ext = "png"
                nama = f"draft_gambar_{n_gbr}.{ext}"
                gambar[nama] = part.blob
                blok.append({"jenis": "gambar", "file": nama, "teks": f"[gambar: {nama}]"})
            if p.text.strip():
                blok.append({"jenis": "paragraf", "teks": p.text.strip(), "markup": _teks_markup(p), "ciri": _ciri(p)})
        elif el.tag == qn("w:tbl"):
            t = Table(el, doc)
            baris = []
            for row in t.rows:
                sel, sebelumnya = [], None
                for c in row.cells:
                    if c._tc is sebelumnya:      # sel gabungan terbaca berulang
                        continue
                    sebelumnya = c._tc
                    sel.append(re.sub(r"\s+", " ", c.text).strip().replace("|", "/"))
                if any(sel):
                    baris.append(sel)
            if baris:
                ringkas = " | ".join(baris[0])
                blok.append({"jenis": "tabel", "baris": baris, "teks": f"[tabel {len(baris)} baris: {ringkas}]"})
    for i, b in enumerate(blok):
        b["id"] = i
    return blok, gambar


# ---------------------------------------------------------------------------
# Pelacakan
# ---------------------------------------------------------------------------
def _seperti_judul(b):
    if b["jenis"] != "paragraf":
        return False
    c, t = b["ciri"], b["teks"].rstrip(":").strip()
    if c["kata"] > 12 or len(t) > 110 or not t:
        return False
    if t[-1] in ".,;" and c["kata"] > 3:
        return False
    if c["gaya"].lower().startswith(("heading", "judul", "title")):
        return True
    return c["tebal"] or c["kapital"] or (c["tengah"] and c["kata"] <= 8) or c["ukuran"] >= 13


def _tebak(teks):
    """Lapis 2: tebak tujuan dari kata khas. Return (tujuan, skor, alasan) atau None."""
    t = " " + teks.lower() + " "
    kandidat = []
    for kunci, (kuat, umum) in list(KATA_KHAS.items()) + list(KATA_KHAS_DEPAN.items()):
        cocok = [k for k in kuat if k in t]
        skor = 3 * len(cocok) + sum(1 for k in umum if k in t)
        if kunci == (0, "Pertanyaan Penelitian") and teks.rstrip().endswith("?"):
            skor += 3
            cocok.append("kalimat tanya")
        if skor:
            contoh = (cocok or [k for k in umum if k in t])[:2]
            kandidat.append((skor, kunci, contoh))
    kata = re.findall(r"[a-z]+", t)
    en = sum(1 for k in kata if k in STOPWORD_EN)
    idn = sum(1 for k in kata if k in STOPWORD_ID)
    if len(kata) > 25 and en >= 6 and en > 3 * idn:
        kandidat.append((4, "abstract", ["teks berbahasa Inggris"]))
    if RE_PUSTAKA.match(teks.strip()):
        kandidat.append((4, "pustaka", ["pola Nama (Tahun)"]))
    if not kandidat:
        return None
    kandidat.sort(key=lambda x: -x[0])
    skor, kunci, contoh = kandidat[0]
    if skor < 2:
        return None
    if len(kandidat) > 1 and kandidat[1][0] == skor:
        skor -= 1   # imbang → kurang yakin
    return kunci, skor, "kata khas: " + ", ".join(f"“{c}”" for c in contoh)


class Pelacak:
    def __init__(self, blok):
        self.blok = blok
        self.struktur = []        # [{"judul", "bawaan", "subbab": [nama], "yakin"}]
        self.lampiran = []        # [judul]
        self.catatan = []
        self.ada_struktur = False

    # ----- struktur -----
    def _bab_baru(self, judul, bawaan, yakin):
        if bawaan is not None:
            for i, b in enumerate(self.struktur):
                if b["bawaan"] == bawaan and b["yakin"] <= 0.5:
                    b["judul"], b["yakin"] = judul, yakin
                    return i
        self.struktur.append({"judul": judul, "bawaan": bawaan, "subbab": [], "yakin": yakin})
        return len(self.struktur) - 1

    def _pastikan_bab_bawaan(self, bawaan):
        for i, b in enumerate(self.struktur):
            if b["bawaan"] == bawaan:
                return i
        return self._bab_baru(STRUKTUR_BAB_BAWAAN[bawaan]["judul"], bawaan, 0.5)

    def _pastikan_subbab(self, bi, nama):
        for j, s in enumerate(self.struktur[bi]["subbab"]):
            if _norm(s) == _norm(nama):
                return j
        self.struktur[bi]["subbab"].append(nama)
        return len(self.struktur[bi]["subbab"]) - 1

    def _label(self, b, tujuan, yakin, alasan, peran="isi"):
        b["tujuan"], b["yakin"], b["alasan"], b["peran"] = tujuan, round(yakin, 2), alasan, peran

    # ----- jalan utama -----
    def jalankan(self):
        B = self.blok
        bagian = None          # None / "bab" / kunci bagian depan
        bi = sj = None         # bab & subbab aktif
        yakin_konteks = 0.0
        lamp_aktif = None
        tebakan_terakhir = None
        dipakai = set()

        # Pra-pasang judul tabel / gambar dan sumbernya ke blok tabel / gambar
        for i, b in enumerate(B):
            if b["jenis"] not in ("tabel", "gambar"):
                continue
            pola = RE_CAP_TABEL if b["jenis"] == "tabel" else RE_CAP_GAMBAR
            urutan = [i - 1, i + 1] if b["jenis"] == "tabel" else [i + 1, i - 1]
            for k in urutan:
                if 0 <= k < len(B) and k not in dipakai and B[k]["jenis"] == "paragraf":
                    m = pola.match(B[k]["teks"])
                    if m and B[k]["ciri"]["kata"] <= 30:
                        b["judul"] = m.group(1).strip().rstrip(".")
                        dipakai.add(k)
                        self._label(B[k], "abaikan", 0.95, f"dipakai sebagai judul {b['jenis']}", "caption")
                        break
            ujung = max([k for k in dipakai if abs(k - i) == 1] + [i])
            k = ujung + 1
            if k < len(B) and B[k]["jenis"] == "paragraf":
                m = RE_SUMBER.match(B[k]["teks"])
                if m:
                    b["sumber"] = m.group(1).strip()
                    dipakai.add(k)
                    self._label(B[k], "abaikan", 0.95, f"dipakai sebagai sumber {b['jenis']}", "caption")
            if not b.get("judul"):
                b["judul"] = ""

        list_counter = {}
        for i, b in enumerate(B):
            if i in dipakai:
                continue
            teks = b["teks"]
            c = b.get("ciri", {})
            gaya = (c.get("gaya") or "").lower()
            atas = _norm(teks).upper()
            judulish = _seperti_judul(b)

            if b["jenis"] == "paragraf" and c.get("list_lvl") is None:
                list_counter = {}

            # --- baris daftar isi ("BAB I ....... 1") → abaikan
            if b["jenis"] == "paragraf" and RE_TOC.search(teks):
                self._label(b, "abaikan", 0.9, "baris daftar isi", "abaikan")
                continue

            # --- judul bagian depan/belakang (KATA PENGANTAR, DAFTAR PUSTAKA, ...)
            if b["jenis"] == "paragraf" and c["kata"] <= 5 and atas in BAGIAN_DEPAN:
                bagian = BAGIAN_DEPAN[atas]
                bi = sj = None
                lamp_aktif = None
                self._label(b, "abaikan", 0.95, f"judul bagian “{teks}”", "judul")
                continue

            # --- BAB
            m = RE_BAB.match(teks) if b["jenis"] == "paragraf" else None
            if m and c["kata"] <= 12 and not (teks.endswith(".") and c["kata"] > 6):
                judul = m.group(2).strip()
                if not judul and i + 1 < len(B) and _seperti_judul(B[i + 1]) and not RE_SUB.match(B[i + 1]["teks"]):
                    judul = B[i + 1]["teks"]
                    dipakai.add(i + 1)
                    self._label(B[i + 1], "abaikan", 0.95, "judul bab (baris kedua)", "judul")
                bawaan = cocokkan_bab(judul)
                if bawaan is None:
                    bawaan = len(self.struktur) if len(self.struktur) < len(STRUKTUR_BAB_BAWAAN) else None
                bi = self._bab_baru(judul_kapital(judul.lower()) if judul.isupper() else judul_kapital(judul),
                                    bawaan, 0.95)
                sj, bagian, yakin_konteks = None, "bab", 0.95
                self.ada_struktur = True
                self._label(b, "abaikan", 0.95, "judul bab (pola “BAB …”)", "judul")
                continue
            if gaya.startswith("heading 1") and b["jenis"] == "paragraf":
                bawaan = cocokkan_bab(teks)
                bi = self._bab_baru(judul_kapital(teks.lower() if teks.isupper() else teks), bawaan, 0.9)
                sj, bagian, yakin_konteks = None, "bab", 0.9
                self.ada_struktur = True
                self._label(b, "abaikan", 0.9, "judul bab (Style Heading 1)", "judul")
                continue
            if judulish and c["kata"] <= 6 and cocokkan_bab(teks) is not None and not cocokkan_subbab(teks):
                bawaan = cocokkan_bab(teks)
                bi = self._bab_baru(judul_kapital(teks.lower() if teks.isupper() else teks), bawaan, 0.8)
                sj, bagian, yakin_konteks = None, "bab", 0.8
                self.ada_struktur = True
                self._label(b, "abaikan", 0.8, "judul bab (mirip nama bab baku)", "judul")
                continue

            # --- Lampiran n
            m = RE_LAMPIRAN.match(teks) if b["jenis"] == "paragraf" else None
            if m and c["kata"] <= 14 and (bagian == "lampiran" or judulish):
                self.lampiran.append(judul_kapital(m.group(2).strip() or f"Lampiran {m.group(1)}"))
                lamp_aktif = len(self.lampiran) - 1
                bagian = "lampiran"
                self._label(b, "abaikan", 0.95, "judul lampiran", "judul")
                continue

            # --- kata kunci / keywords
            if b["jenis"] == "paragraf":
                m = RE_KATA_KUNCI.match(teks)
                if m and c["kata"] <= 25:
                    b["nilai"] = m.group(1).strip()
                    self._label(b, "kata_kunci", 0.95, "baris “Kata kunci:”")
                    continue
                m = RE_KEYWORDS.match(teks)
                if m and c["kata"] <= 25:
                    b["nilai"] = m.group(1).strip()
                    self._label(b, "keywords", 0.95, "baris “Keywords:”")
                    continue

            # --- di dalam bagian depan/belakang
            if bagian in ("kata_pengantar", "intisari", "abstract", "pustaka", "abaikan"):
                self._label(b, bagian, 0.9, "berada di bawah judul bagian")
                continue
            if bagian == "lampiran":
                if lamp_aktif is None:
                    self.lampiran.append("Lampiran")
                    lamp_aktif = 0
                self._label(b, f"lamp|{lamp_aktif}", 0.85, "berada di bawah judul lampiran")
                continue

            # --- subbab & sub-subbab
            if b["jenis"] == "paragraf":
                m3 = RE_SUBSUB.match(teks)
                if (m3 and c["kata"] <= 15 and not teks.endswith(".")) or gaya.startswith("heading 3"):
                    if bi is not None and sj is not None:
                        judul = m3.group(4) if m3 else teks
                        b["markup"] = "### " + judul_kapital(judul.rstrip(":"))
                        self._label(b, f"bab|{bi}|{sj}", yakin_konteks, "sub-subbab", "subsub")
                        continue

                m2 = RE_SUB.match(teks)
                nomor_cocok = m2 and c["kata"] <= 15 and not (teks.endswith(".") and c["kata"] > 6)
                huruf = RE_SUB_HURUF.match(teks) if judulish else None
                if nomor_cocok or gaya.startswith("heading 2") or huruf:
                    judul = (m2.group(3) if nomor_cocok else (huruf.group(2) if huruf else teks)).rstrip(":").strip()
                    if bi is None:   # subbab tanpa judul BAB sebelumnya
                        cocok = cocokkan_subbab(judul)
                        bawaan = (int(m2.group(1)) - 1) if nomor_cocok else (cocok[0] if cocok else 0)
                        bawaan = min(max(bawaan, 0), len(STRUKTUR_BAB_BAWAAN) - 1)
                        bi = self._pastikan_bab_bawaan(bawaan)
                        bagian = "bab"
                    sj = self._pastikan_subbab(bi, judul_kapital(judul))
                    yakin_konteks = 0.95 if (nomor_cocok or gaya.startswith("heading")) else 0.8
                    self.ada_struktur = True
                    self._label(b, "abaikan", yakin_konteks, "judul subbab", "judul")
                    continue

                if judulish and c["kata"] <= 8:
                    cocok = cocokkan_subbab(teks.rstrip(":"))
                    if cocok:
                        if bi is None:
                            bi = self._pastikan_bab_bawaan(cocok[0])
                            bagian = "bab"
                        sj = self._pastikan_subbab(bi, cocok[1])
                        yakin_konteks = 0.8
                        self.ada_struktur = True
                        self._label(b, "abaikan", 0.8, f"judul subbab (mirip “{cocok[1]}”)", "judul")
                        continue
                    if bi is not None and not RE_CATATAN.match(teks):
                        sj = self._pastikan_subbab(bi, judul_kapital(teks.rstrip(":")))
                        yakin_konteks = 0.65
                        self._label(b, "abaikan", 0.65, "judul tidak dikenal, dianggap subbab baru", "judul")
                        continue

            # --- catatan pribadi di draft
            if b["jenis"] == "paragraf" and RE_CATATAN.match(teks):
                self._label(b, "abaikan", 0.6, "terlihat seperti catatan/komentar, bukan isi", "catatan")
                continue

            # --- perincian Word (bernomor otomatis)
            if b["jenis"] == "paragraf" and c.get("list_lvl") is not None:
                lvl = min(c["list_lvl"], 2)
                for k in list(list_counter):
                    if k > lvl:
                        del list_counter[k]
                list_counter[lvl] = list_counter.get(lvl, 0) + 1
                n = list_counter[lvl]
                awalan = [f"{n}.", f"{chr(96 + min(n, 26))}.", f"({n})"][lvl]
                b["markup"] = f"{awalan} {b['markup']}"

            # --- isi: ikut konteks bab/subbab
            if bagian == "bab" and bi is not None:
                if sj is not None:
                    self._label(b, f"bab|{bi}|{sj}", yakin_konteks, "berada di bawah judul subbab")
                    continue
                tebak = _tebak(teks) if b["jenis"] == "paragraf" else None
                bawaan = self.struktur[bi]["bawaan"]
                if tebak and isinstance(tebak[0], tuple) and tebak[0][0] == bawaan:
                    j = self._pastikan_subbab(bi, tebak[0][1])
                    self._label(b, f"bab|{bi}|{j}", min(0.6, 0.3 + 0.1 * tebak[1]),
                                f"di bab ini tapi belum ada judul subbab; {tebak[2]}")
                    tebakan_terakhir = b["tujuan"]
                elif tebakan_terakhir and tebakan_terakhir.startswith(f"bab|{bi}|"):
                    self._label(b, tebakan_terakhir, 0.4, "mengikuti paragraf sebelumnya")
                else:
                    self._label(b, "belum", 0, "di dalam bab, tapi belum jelas masuk subbab mana")
                continue

            # --- baris pembuka sebelum bagian apa pun (judul skripsi, nama, versi draft)
            if bagian is None and not self.struktur and b["jenis"] == "paragraf" and (
                    judulish or c["kata"] <= 6) and not _tebak(teks):
                self._label(b, "abaikan", 0.6, "kemungkinan halaman judul / keterangan draft", "abaikan")
                continue

            # --- di luar struktur apa pun → Lapis 2 penuh
            tebak = _tebak(teks) if b["jenis"] == "paragraf" else None
            if tebak:
                kunci, skor, alasan = tebak
                yakin = min(0.65, 0.3 + 0.1 * skor)
                if isinstance(kunci, tuple):
                    bi2 = self._pastikan_bab_bawaan(kunci[0])
                    j = self._pastikan_subbab(bi2, kunci[1])
                    self._label(b, f"bab|{bi2}|{j}", yakin, alasan)
                else:
                    self._label(b, kunci, yakin, alasan)
                tebakan_terakhir = b["tujuan"]
            elif tebakan_terakhir and b["jenis"] in ("paragraf", "tabel", "gambar"):
                self._label(b, tebakan_terakhir, 0.4, "tidak ada kata khas; mengikuti paragraf sebelumnya")
            else:
                self._label(b, "belum", 0, "tidak ditemukan petunjuk")

        self._rapikan_struktur()
        self._buat_catatan()
        return self

    def _rapikan_struktur(self):
        """Urutkan subbab tebakan mengikuti urutan baku panduan, dan bab tebakan mengikuti urutan bab."""
        if self.ada_struktur:
            urut = sorted(range(len(self.struktur)),
                          key=lambda i: (self.struktur[i]["bawaan"] if self.struktur[i]["bawaan"] is not None else i, i))
            if urut != list(range(len(self.struktur))):
                lama_ke_baru = {lama: baru for baru, lama in enumerate(urut)}
                self.struktur = [self.struktur[i] for i in urut]
                for b in self.blok:
                    t = b.get("tujuan", "")
                    if t.startswith("bab|"):
                        _, i, j = t.split("|")
                        b["tujuan"] = f"bab|{lama_ke_baru[int(i)]}|{j}"
            return
        # Draft tanpa struktur sama sekali: pakai struktur baku lengkap agar bagian kosong terlihat
        lama = self.struktur
        baru = []
        peta = {}
        for bawaan, bab in enumerate(STRUKTUR_BAB_BAWAAN):
            subs = list(bab["subbab"])
            idx_lama = next((i for i, b in enumerate(lama) if b["bawaan"] == bawaan), None)
            if idx_lama is not None:
                for j, s in enumerate(lama[idx_lama]["subbab"]):
                    if s not in subs:
                        subs.append(s)
                    peta[(idx_lama, j)] = (bawaan, subs.index(s))
            baru.append({"judul": bab["judul"], "bawaan": bawaan, "subbab": subs, "yakin": 0.5})
        for b in self.blok:
            t = b.get("tujuan", "")
            if t.startswith("bab|"):
                _, i, j = t.split("|")
                ni, nj = peta[(int(i), int(j))]
                b["tujuan"] = f"bab|{ni}|{nj}"
        self.struktur = baru

    def _buat_catatan(self):
        nama_ada = {_norm(s) for b in self.struktur for s in b["subbab"]}
        for b in self.struktur:
            for s in b["subbab"]:
                cocok = cocokkan_subbab(s)
                if cocok:
                    nama_ada.add(_norm(cocok[1]))
        for bi, bab in enumerate(STRUKTUR_BAB_BAWAAN):
            if not any(b["bawaan"] == bi for b in self.struktur):
                self.catatan.append(f"Bab “{bab['judul']}” tidak ditemukan di draft.")
                continue
            kurang = [s for s in bab["subbab"]
                      if not any(_norm(x) in nama_ada for x in SINONIM_SUBBAB.get(s, [s.lower()]) + [s.lower()])]
            if kurang:
                self.catatan.append(f"Bab {['I','II','III','IV','V'][bi]} belum punya subbab: {', '.join(kurang)}.")
        terisi = {b.get("tujuan") for b in self.blok if b.get("peran") in ("isi", "subsub")}
        kosong = [f"{i + 1}.{j + 1} {s}" for i, bab in enumerate(self.struktur)
                  for j, s in enumerate(bab["subbab"]) if f"bab|{i}|{j}" not in terisi]
        if kosong:
            self.catatan.append(f"Subbab yang belum ada isinya: {', '.join(kosong)}.")
        isi = {}
        for b in self.blok:
            if b.get("tujuan") in ("intisari", "abstract"):
                isi[b["tujuan"]] = isi.get(b["tujuan"], 0) + hitung_kata(b["teks"])
        for k, n in isi.items():
            if n > 250:
                self.catatan.append(f"{k.capitalize()} {n} kata, melebihi batas 250 kata.")
        n_pustaka = sum(1 for b in self.blok if b.get("tujuan") == "pustaka")
        if n_pustaka and n_pustaka < 10:
            self.catatan.append(f"Daftar pustaka terbaca {n_pustaka} entri (panduan: minimal 10 artikel jurnal).")


def lacak_draft(data_docx):
    blok, gambar = ekstrak_blok(data_docx)
    p = Pelacak(blok).jalankan()
    return {"blok": blok, "gambar": gambar, "struktur": p.struktur,
            "lampiran": p.lampiran, "catatan": p.catatan}


# ---------------------------------------------------------------------------
# Pilihan tujuan untuk layar review
# ---------------------------------------------------------------------------
ROMAWI = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def daftar_tujuan(hasil):
    """[(kunci, label)] untuk dropdown di layar review."""
    opsi = [("belum", "Belum ditempatkan"), ("abaikan", "Abaikan (tidak dimasukkan)"),
            ("kata_pengantar", "Kata Pengantar"), ("intisari", "Intisari"), ("kata_kunci", "Kata Kunci"),
            ("abstract", "Abstract"), ("keywords", "Keywords")]
    for i, bab in enumerate(hasil["struktur"]):
        r = ROMAWI[i] if i < len(ROMAWI) else str(i + 1)
        for j, s in enumerate(bab["subbab"]):
            opsi.append((f"bab|{i}|{j}", f"Bab {r} › {i + 1}.{j + 1} {s}"))
    opsi.append(("pustaka", "Daftar Pustaka"))
    for k, l in enumerate(hasil["lampiran"]):
        opsi.append((f"lamp|{k}", f"Lampiran {k + 1}. {l}"))
    return opsi


def warna(b):
    if b.get("tujuan") == "belum" or not b.get("yakin"):
        return "merah"
    return "hijau" if b["yakin"] >= YAKIN_TINGGI else "kuning"


# ---------------------------------------------------------------------------
# Susun hasil akhir → format data generator
# ---------------------------------------------------------------------------
def _baris_blok(b):
    if b["jenis"] == "tabel":
        judul = b.get("judul") or "Judul tabel belum ada"
        sumber = b.get("sumber", "")
        kepala = f"[[TABEL: {judul} | {sumber}]]" if sumber else f"[[TABEL: {judul}]]"
        return [kepala] + [" | ".join(r) for r in b["baris"]] + ["[[/TABEL]]"]
    if b["jenis"] == "gambar":
        judul = b.get("judul") or "Judul gambar belum ada"
        sumber = b.get("sumber", "")
        return [f"[[GAMBAR: {b['file']} | {judul} | {sumber}]]"]
    return [b.get("markup") or b["teks"]]


def susun_data(hasil, pilihan=None):
    """pilihan: {id_blok: kunci_tujuan} hasil koreksi pengguna (boleh kosong)."""
    pilihan = pilihan or {}
    data = {"kata_pengantar": "", "intisari": "", "kata_kunci": "", "abstract": "", "keywords": "",
            "daftar_pustaka": "", "bab": [], "lampiran": []}
    teks = {k: [] for k in ("kata_pengantar", "intisari", "abstract", "pustaka")}
    isi_sub = {}
    isi_lamp = {}
    gambar_lamp = {}
    for b in hasil["blok"]:
        t = pilihan.get(b["id"], b.get("tujuan", "belum"))
        if t in ("belum", "abaikan"):
            continue
        if t in ("kata_kunci", "keywords"):
            data[t] = b.get("nilai") or re.sub(r"^[^:]*:\s*", "", b["teks"])
        elif t in teks:
            teks[t].extend(_baris_blok(b) if b["jenis"] == "paragraf" else [])
        elif t.startswith("bab|"):
            _, i, j = t.split("|")
            isi_sub.setdefault((int(i), int(j)), []).extend(_baris_blok(b))
        elif t.startswith("lamp|"):
            k = int(t.split("|")[1])
            if b["jenis"] == "gambar":
                gambar_lamp.setdefault(k, b["file"])
            isi_lamp.setdefault(k, []).extend(_baris_blok(b) if b["jenis"] == "paragraf" else [])
    data["kata_pengantar"] = "\n".join(teks["kata_pengantar"])
    data["intisari"] = "\n".join(teks["intisari"])
    data["abstract"] = "\n".join(x.strip("*") for x in teks["abstract"])
    data["daftar_pustaka"] = "\n".join(teks["pustaka"])
    for i, bab in enumerate(hasil["struktur"]):
        data["bab"].append({"judul": bab["judul"],
                            "subbab": [{"judul": s, "isi": "\n".join(isi_sub.get((i, j), []))}
                                       for j, s in enumerate(bab["subbab"])]})
    for k, l in enumerate(hasil["lampiran"]):
        data["lampiran"].append({"judul": l, "isi": "\n".join(isi_lamp.get(k, [])),
                                 "gambar": gambar_lamp.get(k, "")})
    return data, dict(hasil["gambar"])


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "rb") as fh:
        h = lacak_draft(fh.read())
    hitung = {"hijau": 0, "kuning": 0, "merah": 0}
    for b in h["blok"]:
        hitung[warna(b)] += 1
        print(f"{b['id']:>3} {warna(b):6} {b.get('yakin', 0):.2f} {b.get('tujuan', ''):14} | "
              f"{b['teks'][:60]!r:64} | {b.get('alasan', '')}")
    print("\nStruktur:")
    for i, bab in enumerate(h["struktur"]):
        print(f"  BAB {ROMAWI[i]} {bab['judul']}: {bab['subbab']}")
    print("Lampiran:", h["lampiran"])
    print("Catatan:", *h["catatan"], sep="\n  - ")
    print(hitung)
