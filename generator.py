"""
Mesin pembuat laporan Tugas Akhir (.docx)
Format mengikuti: Panduan Penulisan Tugas Akhir 2025
Departemen Ekonomika dan Bisnis, Sekolah Vokasi UGM.

Fungsi utama: buat_dokumen(data, gambar, logo) -> (bytes_docx, daftar_peringatan)

Penanda (markup) yang bisa dipakai di dalam isi subbab:
  - Setiap baris = satu paragraf.
  - ### Judul             -> sub-subbab (otomatis bernomor, mis. 1.1.1)
  - 1. teks / a. teks / (1) teks -> perincian tingkat 1 / 2 / 3
  - *miring*  **tebal**   -> huruf miring (istilah asing) / tebal
  - [[GAMBAR: nama_file.png | Judul Gambar | Sumber (opsional) | lebar cm (opsional)]]
  - [[TABEL: Judul Tabel | Sumber (opsional)]]
      Kolom A | Kolom B | Kolom C      <- baris pertama = header
      isi 1   | isi 2   | isi 3
    [[/TABEL]]
  - [[RUMUS: Y = a + bX]] -> persamaan di tengah, nomor (1) di kanan
"""

import io
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ---------------------------------------------------------------------------
# ATURAN FORMAT (Bab III Panduan, subbab 3.1)
# Kalau nanti mau mendukung kampus lain, cukup buat dict baru seperti ini.
# ---------------------------------------------------------------------------
FORMAT_DEB_SV_UGM = {
    "nama": "DEB Sekolah Vokasi UGM (Panduan TA 2025)",
    "kertas_lebar_cm": 21.0,       # A4
    "kertas_tinggi_cm": 29.7,
    "margin_atas_cm": 4.0,
    "margin_kiri_cm": 4.0,
    "margin_kanan_cm": 3.0,
    "margin_bawah_cm": 3.0,
    "font": "Times New Roman",
    "ukuran_font": 12,
    "spasi_isi": 1.5,              # naskah utama
    "spasi_rapat": 1.0,            # judul tabel/gambar, daftar-daftar, pustaka, intisari
    "indent_paragraf_cm": 1.25,    # paragraf kedua dst. menjorok 1,25 cm
    "lebar_logo_cm": 5.5,
    "tinggi_logo_cm": 5.71,
    "institusi": [
        "DEPARTEMEN EKONOMIKA DAN BISNIS",
        "SEKOLAH VOKASI",
        "UNIVERSITAS GADJAH MADA",
    ],
}

# Margin boleh diubah dari aplikasi (tab "Format halaman") bila prodi/pembimbing meminta penyesuaian.
SISI_MARGIN = ("atas", "kiri", "kanan", "bawah")
MARGIN_MIN_CM, MARGIN_MAX_CM = 1.0, 6.0


def margin_bawaan(fmt=None):
    fmt = fmt or FORMAT_DEB_SV_UGM
    return {s: fmt[f"margin_{s}_cm"] for s in SISI_MARGIN}


def format_dari(data, dasar=None):
    """Salinan aturan format dengan margin dari data["format"] (bila ada dan masuk akal)."""
    fmt = dict(dasar or FORMAT_DEB_SV_UGM)
    atur = (data or {}).get("format") or {}
    for s in SISI_MARGIN:
        try:
            nilai = float(str(atur.get(f"margin_{s}_cm")).replace(",", "."))
        except (TypeError, ValueError):
            continue
        fmt[f"margin_{s}_cm"] = round(min(max(nilai, MARGIN_MIN_CM), MARGIN_MAX_CM), 2)
    return fmt


def jarak_footer_cm(fmt):
    """Nomor halaman 1,5 cm dari tepi bawah; ikut naik-turun bila margin bawah dibuat sempit."""
    return round(min(1.5, fmt["margin_bawah_cm"] / 2), 2)


KATA_SAMBUNG = {
    "di", "ke", "dari", "dan", "atau", "yang", "untuk", "pada", "dengan", "dalam",
    "terhadap", "oleh", "serta", "sebagai", "bagi", "tentang", "antara", "secara",
    "of", "and", "the", "in", "on", "for", "to", "a", "an", "at", "by", "with",
}

ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

RE_GAMBAR = re.compile(r"^\[\[\s*GAMBAR\s*:(.*)\]\]$", re.I)
RE_TABEL_BUKA = re.compile(r"^\[\[\s*TABEL\s*:(.*)\]\]$", re.I)
RE_TABEL_TUTUP = re.compile(r"^\[\[\s*/\s*TABEL\s*\]\]$", re.I)
RE_RUMUS = re.compile(r"^\[\[\s*RUMUS\s*:(.*)\]\]$", re.I)
RE_LIST1 = re.compile(r"^(\d+)\.\s+(.*)$")
RE_LIST2 = re.compile(r"^([a-z])\.\s+(.*)$")
RE_LIST3 = re.compile(r"^\((\d+)\)\s+(.*)$")


def judul_kapital(teks: str) -> str:
    """Huruf awal kapital tiap kata, kecuali kata sambung/kata depan (aturan 3.1.2 no. 6)."""
    kata = teks.strip().split()
    hasil = []
    for i, k in enumerate(kata):
        if len(k) > 1 and k.isupper():          # singkatan (UMKM, BPS) dibiarkan
            hasil.append(k)
        elif i > 0 and k.lower() in KATA_SAMBUNG:
            hasil.append(k.lower())
        else:
            hasil.append(k[:1].upper() + k[1:])
    return " ".join(hasil)


def urutkan_kata_kunci(teks: str) -> str:
    """Kata kunci diurutkan sesuai abjad (aturan 3.2.1 no. 10-11)."""
    bagian = [k.strip() for k in re.split(r"[;,]", teks or "") if k.strip()]
    return ", ".join(sorted(bagian, key=lambda s: s.lower()))


def hitung_kata(teks: str) -> int:
    return len(re.findall(r"\S+", teks or ""))


# ---------------------------------------------------------------------------
# Utilitas XML kecil
# ---------------------------------------------------------------------------
def _set_font_style(style, nama, ukuran, bold=None, italic=None):
    style.font.name = nama
    style.font.size = Pt(ukuran)
    style.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), nama)


def _tambah_field(paragraf, instruksi, teks_sementara=""):
    """Sisipkan field Word (PAGE, TOC, dll.)."""
    def fld(jenis):
        r = paragraf.add_run()
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), jenis)
        if jenis == "begin":
            el.set(qn("w:dirty"), "true")
        r._r.append(el)
        return r

    fld("begin")
    r = paragraf.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruksi} "
    r._r.append(instr)
    fld("separate")
    if teks_sementara:
        paragraf.add_run(teks_sementara)
    fld("end")


def _ulang_header_tabel(baris):
    trpr = baris._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def _jaga_baris_tidak_terpotong(baris):
    trpr = baris._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def _tulis_inline(paragraf, teks, bold=False, italic=False):
    """Tulis teks dengan dukungan **tebal** dan *miring*."""
    pola = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")
    for potongan in pola.split(teks):
        if not potongan:
            continue
        if potongan.startswith("**") and potongan.endswith("**") and len(potongan) > 4:
            r = paragraf.add_run(potongan[2:-2])
            r.bold = True
            r.italic = italic or None
        elif potongan.startswith("*") and potongan.endswith("*") and len(potongan) > 2:
            r = paragraf.add_run(potongan[1:-1])
            r.italic = True
            r.bold = bold or None
        else:
            r = paragraf.add_run(potongan)
            if bold:
                r.bold = True
            if italic:
                r.italic = True


# ---------------------------------------------------------------------------
# Pembangun dokumen
# ---------------------------------------------------------------------------
class PembangunTA:
    def __init__(self, data, gambar=None, logo=None, fmt=FORMAT_DEB_SV_UGM):
        self.data = data
        self.gambar = gambar or {}
        self.logo = logo
        self.f = fmt
        self.peringatan = []
        self.doc = Document()
        self.lebar_teks_cm = fmt["kertas_lebar_cm"] - fmt["margin_kiri_cm"] - fmt["margin_kanan_cm"]
        self.no_rumus = 0
        self._siapkan_gaya()
        self._atur_halaman(self.doc.sections[0])

    # ---------------- gaya (styles) ----------------
    def _siapkan_gaya(self):
        f = self.f
        st = self.doc.styles

        normal = st["Normal"]
        _set_font_style(normal, f["font"], f["ukuran_font"])
        pf = normal.paragraph_format
        pf.line_spacing = f["spasi_isi"]
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        # Judul bab: tengah, tebal, kapital
        h1 = st["Heading 1"]
        _set_font_style(h1, f["font"], f["ukuran_font"], bold=True, italic=False)
        h1.font.all_caps = True
        h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h1.paragraph_format.space_before = Pt(0)
        h1.paragraph_format.space_after = Pt(24)
        h1.paragraph_format.line_spacing = f["spasi_isi"]
        h1.paragraph_format.keep_with_next = True

        # Judul subbab: rata kiri, tebal
        h2 = st["Heading 2"]
        _set_font_style(h2, f["font"], f["ukuran_font"], bold=True, italic=False)
        h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h2.paragraph_format.space_before = Pt(12)
        h2.paragraph_format.space_after = Pt(0)
        h2.paragraph_format.line_spacing = f["spasi_isi"]
        h2.paragraph_format.keep_with_next = True

        # Judul sub-subbab: rata kiri
        h3 = st["Heading 3"]
        _set_font_style(h3, f["font"], f["ukuran_font"], bold=True, italic=False)
        h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h3.paragraph_format.space_before = Pt(6)
        h3.paragraph_format.space_after = Pt(0)
        h3.paragraph_format.line_spacing = f["spasi_isi"]
        h3.paragraph_format.keep_with_next = True

        def gaya_baru(nama, align, bold=False, italic=False, keep_next=False, spasi=None):
            s = st.add_style(nama, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = normal
            s.quick_style = True
            _set_font_style(s, f["font"], f["ukuran_font"], bold=bold, italic=italic)
            s.paragraph_format.alignment = align
            s.paragraph_format.line_spacing = spasi or f["spasi_rapat"]
            s.paragraph_format.keep_with_next = keep_next
            s.paragraph_format.first_line_indent = Cm(0)
            return s

        # Judul tabel di atas tabel, judul gambar di bawah gambar: tebal, tengah, 1 spasi
        s = gaya_baru("Judul Tabel", WD_ALIGN_PARAGRAPH.CENTER, bold=True, keep_next=True)
        s.paragraph_format.space_before = Pt(12)
        s.paragraph_format.space_after = Pt(6)
        s = gaya_baru("Judul Gambar", WD_ALIGN_PARAGRAPH.CENTER, bold=True)
        s.paragraph_format.space_before = Pt(6)
        s = gaya_baru("Sumber", WD_ALIGN_PARAGRAPH.LEFT)
        s.paragraph_format.space_after = Pt(12)
        s = gaya_baru("Judul Lampiran", WD_ALIGN_PARAGRAPH.LEFT, bold=True, keep_next=True)
        s.paragraph_format.space_after = Pt(12)
        gaya_baru("Isi Tabel", WD_ALIGN_PARAGRAPH.LEFT)
        s = gaya_baru("Daftar Pustaka", WD_ALIGN_PARAGRAPH.LEFT)
        s.paragraph_format.left_indent = Cm(1.27)
        s.paragraph_format.first_line_indent = Cm(-1.27)
        s.paragraph_format.space_after = Pt(6)

        # Gaya daftar isi / daftar tabel: 1 spasi, titik-titik ke nomor halaman
        kanan = Cm(self.lebar_teks_cm)
        for nama, indent in (("toc 1", 0), ("toc 2", 0.63), ("toc 3", 1.27), ("table of figures", 0)):
            s = st.add_style(nama, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = normal
            s.paragraph_format.line_spacing = f["spasi_rapat"]
            s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            s.paragraph_format.left_indent = Cm(indent)
            s.paragraph_format.space_after = Pt(4)
            s.paragraph_format.tab_stops.add_tab_stop(kanan, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

        footer = st["Footer"]
        _set_font_style(footer, f["font"], f["ukuran_font"])
        footer.paragraph_format.line_spacing = 1.0

    def _atur_halaman(self, section):
        f = self.f
        section.page_width = Cm(f["kertas_lebar_cm"])
        section.page_height = Cm(f["kertas_tinggi_cm"])
        section.top_margin = Cm(f["margin_atas_cm"])
        section.bottom_margin = Cm(f["margin_bawah_cm"])
        section.left_margin = Cm(f["margin_kiri_cm"])
        section.right_margin = Cm(f["margin_kanan_cm"])
        section.footer_distance = Cm(jarak_footer_cm(f))

    def _section_baru(self, format_nomor, posisi, mulai=1):
        """format_nomor: 'lowerRoman' / 'decimal' / None. posisi: 'tengah'/'kanan'."""
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._atur_halaman(sec)
        sec.footer.is_linked_to_previous = False
        p = sec.footer.paragraphs[0]
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        if format_nomor:
            sectpr = sec._sectPr
            pg = sectpr.find(qn("w:pgNumType"))
            if pg is None:
                pg = OxmlElement("w:pgNumType")
                sectpr.append(pg)
            pg.set(qn("w:fmt"), format_nomor)
            pg.set(qn("w:start"), str(mulai))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if posisi == "tengah" else WD_ALIGN_PARAGRAPH.RIGHT
            _tambah_field(p, "PAGE", "1")
        return sec

    # ---------------- helper paragraf ----------------
    def _p(self, teks="", align=None, bold=False, italic=False, ukuran=None, spasi=None,
           sebelum=None, sesudah=None, indent=None, style=None):
        p = self.doc.add_paragraph(style=style)
        if teks:
            _tulis_inline(p, teks, bold=bold, italic=italic)
            if ukuran:
                for r in p.runs:
                    r.font.size = Pt(ukuran)
        pf = p.paragraph_format
        if align is not None:
            pf.alignment = align
        if spasi is not None:
            pf.line_spacing = spasi
        if sebelum is not None:
            pf.space_before = Pt(sebelum)
        if sesudah is not None:
            pf.space_after = Pt(sesudah)
        if indent is not None:
            pf.first_line_indent = Cm(indent)
        return p

    def _judul_halaman(self, teks, masuk_daftar_isi=True):
        if masuk_daftar_isi:
            return self.doc.add_heading(teks, level=1)
        return self._p(teks, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, sesudah=24)

    def _ganti_halaman(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _paragraf_bebas(self, teks, spasi=None, italic=False):
        """Paragraf-paragraf biasa (kata pengantar, intisari): paragraf pertama rata kiri, berikutnya menjorok."""
        pertama = True
        for baris in [b.strip() for b in (teks or "").splitlines() if b.strip()]:
            self._p(baris, spasi=spasi, italic=italic,
                    indent=0 if pertama else self.f["indent_paragraf_cm"])
            pertama = False

    # ---------------- BAGIAN AWAL ----------------
    def sampul(self):
        d = self.data["identitas"]
        C = WD_ALIGN_PARAGRAPH.CENTER
        self._p("TUGAS AKHIR", align=C, bold=True, ukuran=14, spasi=1.0, sesudah=30)
        self._p((d.get("judul_id") or "[JUDUL TUGAS AKHIR]").upper(), align=C, bold=True, ukuran=14, spasi=1.15, sesudah=6)
        self._p((d.get("judul_en") or "[JUDUL DALAM BAHASA INGGRIS]").upper(), align=C, bold=True, italic=True, ukuran=12, spasi=1.15, sesudah=60)
        self._p("Disusun untuk memenuhi persyaratan mencapai gelar Sarjana Terapan", align=C, spasi=1.0, sesudah=24)
        self._p("Dosen Pembimbing", align=C, spasi=1.0)
        self._p(d.get("pembimbing") or "[Nama Dosen Pembimbing, gelar lengkap]", align=C, spasi=1.0, sesudah=42)

        p = self._p(align=C, spasi=1.0, sesudah=42)
        if self.logo:
            p.add_run().add_picture(io.BytesIO(self.logo), width=Cm(self.f["lebar_logo_cm"]), height=Cm(self.f["tinggi_logo_cm"]))
        else:
            r = p.add_run("[Lambang UGM 5,5 × 5,71 cm — upload logo di aplikasi]")
            r.italic = True
            r.font.color.rgb = RGBColor(0xC0, 0, 0)
            self.peringatan.append("Logo UGM belum diupload, sampul berisi penanda tempat logo.")

        self._p("Oleh:", align=C, spasi=1.0)
        self._p(judul_kapital(d.get("nama") or "[Nama Mahasiswa]"), align=C, bold=True, spasi=1.0)
        self._p(d.get("nim") or "[NIM]", align=C, spasi=1.0, sesudah=84)
        self._p((d.get("prodi") or "[NAMA PROGRAM STUDI]").upper(), align=C, bold=True, spasi=1.0)
        for baris in self.f["institusi"]:
            self._p(baris, align=C, bold=True, spasi=1.0)
        self._p(str(d.get("tahun") or "[TAHUN]"), align=C, bold=True, spasi=1.0)

    def _blok_ttd(self, sel, jabatan, nama, nip):
        dipakai = [False]

        def baris(t, bold=False, sesudah=0):
            if not dipakai[0]:
                p = sel.paragraphs[0]
                dipakai[0] = True
            else:
                p = sel.add_paragraph()
            _tulis_inline(p, t, bold=bold)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(sesudah)
            return p
        for i, j in enumerate(jabatan):
            baris(j, sesudah=48 if i == len(jabatan) - 1 else 0)
        baris(nama or "[Nama Lengkap]", bold=True)
        baris(f"NIP/NIKA {nip}" if nip else "[NIP/NIKA]")

    def pengesahan(self):
        d = self.data["identitas"]
        g = self.data.get("pengesahan", {})
        C = WD_ALIGN_PARAGRAPH.CENTER
        self._judul_halaman("HALAMAN PENGESAHAN")
        self._p("TUGAS AKHIR", align=C, bold=True, spasi=1.0, sesudah=6)
        self._p(d.get("judul_id") or "[Judul Tugas Akhir]", align=C, bold=True, spasi=1.15, sesudah=18)
        self._p("Disusun oleh:", align=C, spasi=1.0)
        self._p(judul_kapital(d.get("nama") or "[Nama Lengkap]"), align=C, bold=True, spasi=1.0)
        self._p(d.get("nim") or "[NIM]", align=C, spasi=1.0, sesudah=18)
        self._p("Telah diujikan dan diseminarkan", align=C, spasi=1.0)
        self._p(f"pada tanggal {g.get('tanggal_ujian') or '[tanggal bulan tahun]'}", align=C, spasi=1.0, sesudah=18)

        t = self.doc.add_table(rows=1, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._blok_ttd(t.cell(0, 0), ["Penguji I/", "Ketua Penguji"], g.get("ketua_nama"), g.get("ketua_nip"))
        self._blok_ttd(t.cell(0, 1), ["Penguji II/Sekretaris Penguji/", "Dosen Pembimbing Tugas Akhir"],
                       d.get("pembimbing"), g.get("pembimbing_nip"))
        self._p(sesudah=6)
        t2 = self.doc.add_table(rows=1, cols=1)
        t2.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._blok_ttd(t2.cell(0, 0), ["Penguji III/", "Anggota Penguji"], g.get("anggota_nama"), g.get("anggota_nip"))
        self._p(sesudah=6)
        self._p("Mengetahui,", align=C, spasi=1.0)
        self._p(g.get("mengetahui_jabatan") or f"Ketua Program Studi {d.get('prodi') or '[nama prodi]'}", align=C, spasi=1.0)
        self._p("Sekolah Vokasi Universitas Gadjah Mada", align=C, spasi=1.0, sesudah=48)
        self._p(g.get("mengetahui_nama") or "[Nama Lengkap]", align=C, bold=True, spasi=1.0)
        nip = g.get("mengetahui_nip")
        self._p(f"NIP/NIKA {nip}" if nip else "[NIP/NIKA]", align=C, spasi=1.0)

    def pernyataan(self):
        d = self.data["identitas"]
        self._judul_halaman("PERNYATAAN BEBAS PLAGIASI")
        self._p("Saya yang bertanda tangan di bawah ini:", spasi=1.5, sesudah=6)
        isian = [
            ("Nama", judul_kapital(d.get("nama") or "[nama lengkap]")),
            ("NIM", d.get("nim") or "[NIM]"),
            ("Tahun terdaftar", str(d.get("tahun_terdaftar") or "[tahun]")),
            ("Program studi", d.get("prodi") or "[nama prodi]"),
            ("Fakultas/Sekolah", d.get("fakultas") or "Sekolah Vokasi"),
        ]
        for label, nilai in isian:
            p = self._p(spasi=1.5, align=WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(4))
            p.add_run(f"{label}\t: {nilai}")
        self._p(sesudah=6)
        teks = (
            "Menyatakan bahwa dalam dokumen ilmiah Tugas Akhir ini tidak terdapat bagian dari karya ilmiah "
            "lain yang telah diajukan untuk memperoleh gelar akademik di suatu Lembaga Pendidikan Tinggi, "
            "dan juga tidak terdapat karya atau pendapat yang pernah ditulis atau diterbitkan oleh "
            "orang/Lembaga lain, kecuali yang secara tertulis disitasi dalam dokumen ini dan disebutkan "
            "sumbernya secara lengkap dalam daftar pustaka.\n"
            "Dengan demikian saya menyatakan bahwa dokumen ilmiah ini bebas dari unsur-unsur plagiasi dan "
            "apabila dokumen ilmiah Tugas Akhir ini di kemudian hari terbukti merupakan plagiasi dari hasil "
            "karya penulis lain dan/atau dengan sengaja mengajukan karya atau pendapat yang merupakan hasil "
            "karya penulis lain, maka penulis bersedia menerima sanksi akademik dan/atau sanksi hukum yang berlaku."
        )
        self._paragraf_bebas(teks, spasi=1.5)
        R = WD_ALIGN_PARAGRAPH.RIGHT
        tempat = d.get("tempat_ttd") or "Yogyakarta"
        tanggal = d.get("tanggal_ttd") or "[tanggal-bulan-tahun]"
        self._p(f"{tempat}, {tanggal}", align=R, spasi=1.0, sebelum=24, sesudah=12)
        p = self._p("Materai Rp 10.000,00", align=R, spasi=1.0, sesudah=36)
        p.runs[0].font.color.rgb = RGBColor(0x80, 0x80, 0x80)
        self._p(judul_kapital(d.get("nama") or "[Nama Mahasiswa]"), align=R, bold=True, spasi=1.0)
        self._p(d.get("nim") or "[NIM]", align=R, spasi=1.0)

    def kata_pengantar(self):
        d = self.data["identitas"]
        self._judul_halaman("KATA PENGANTAR")
        teks = self.data.get("kata_pengantar") or "[Tulis kata pengantar di aplikasi.]"
        self._paragraf_bebas(teks, spasi=self.f["spasi_isi"])
        R = WD_ALIGN_PARAGRAPH.RIGHT
        self._p(f"{d.get('tempat_ttd') or 'Yogyakarta'}, {d.get('tanggal_ttd') or '[tanggal]'}", align=R, spasi=1.0, sebelum=24, sesudah=48)
        self._p("Penulis", align=R, spasi=1.0)

    def _halaman_daftar(self, judul, instruksi_field, keterangan):
        self._judul_halaman(judul)
        p = self._p(spasi=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
        _tambah_field(p, instruksi_field, keterangan)

    def intisari(self):
        self._judul_halaman("INTISARI")
        teks = self.data.get("intisari") or ""
        if hitung_kata(teks) > 250:
            self.peringatan.append(f"Intisari {hitung_kata(teks)} kata, melebihi batas 250 kata.")
        self._paragraf_bebas(teks or "[Tulis intisari di aplikasi.]", spasi=self.f["spasi_rapat"])
        p = self._p(spasi=1.0, sebelum=12, indent=0)
        p.add_run("Kata kunci: ").bold = True
        p.add_run(urutkan_kata_kunci(self.data.get("kata_kunci")) or "[kata kunci]")

    def abstract(self):
        self._judul_halaman("ABSTRACT")
        teks = self.data.get("abstract") or ""
        if hitung_kata(teks) > 250:
            self.peringatan.append(f"Abstract {hitung_kata(teks)} kata, melebihi batas 250 kata.")
        self._paragraf_bebas(teks or "[Write the abstract in the app.]", spasi=self.f["spasi_rapat"], italic=True)
        p = self._p(spasi=1.0, sebelum=12, indent=0)
        r = p.add_run("Keywords: ")
        r.bold = True
        r.italic = True
        p.add_run(urutkan_kata_kunci(self.data.get("keywords")) or "[keywords]").italic = True

    def daftar_istilah(self):
        baris = [b for b in (self.data.get("istilah") or "").splitlines() if b.strip()]
        if not baris:
            return False
        self._judul_halaman("DAFTAR ISTILAH")
        entri = []
        for b in baris:
            if ":" in b:
                k, v = b.split(":", 1)
            else:
                k, v = b, ""
            entri.append((k.strip(), v.strip()))
        for k, v in sorted(entri, key=lambda e: e[0].lower()):
            p = self._p(spasi=1.0, sesudah=6, align=WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.left_indent = Cm(4.5)
            p.paragraph_format.first_line_indent = Cm(-4.5)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(4.5))
            p.add_run(k).italic = True
            p.add_run(f"\t: {v}")
        return True

    # ---------------- BAGIAN INTI ----------------
    def _isi_subbab(self, teks, no_bab, no_sub, penghitung):
        pertama_setelah_judul = True
        no_subsub = 0
        baris_list = (teks or "").splitlines()
        i = 0
        while i < len(baris_list):
            b = baris_list[i].strip()
            i += 1
            if not b:
                continue

            if b.startswith("### "):
                no_subsub += 1
                self.doc.add_heading(f"{no_bab}.{no_sub}.{no_subsub} {judul_kapital(b[4:])}", level=3)
                pertama_setelah_judul = True
                continue

            m = RE_GAMBAR.match(b)
            if m:
                self._gambar(m.group(1), no_bab, penghitung)
                pertama_setelah_judul = False
                continue

            m = RE_TABEL_BUKA.match(b)
            if m:
                isi = []
                while i < len(baris_list) and not RE_TABEL_TUTUP.match(baris_list[i].strip()):
                    if baris_list[i].strip():
                        isi.append(baris_list[i].strip())
                    i += 1
                if i >= len(baris_list):
                    self.peringatan.append(f"Bab {no_bab}: tabel '{m.group(1).strip()}' tidak ditutup dengan [[/TABEL]].")
                i += 1
                self._tabel(m.group(1), isi, no_bab, penghitung)
                pertama_setelah_judul = False
                continue

            m = RE_RUMUS.match(b)
            if m:
                self._rumus(m.group(1).strip())
                pertama_setelah_judul = False
                continue

            for pola, kiri in ((RE_LIST3, 1.9), (RE_LIST1, 0.63), (RE_LIST2, 1.27)):
                m = pola.match(b)
                if m:
                    penanda = b[: m.start(2)].strip()
                    p = self._p(spasi=self.f["spasi_isi"])
                    p.paragraph_format.left_indent = Cm(kiri + 0.63)
                    p.paragraph_format.first_line_indent = Cm(-0.63)
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(kiri + 0.63))
                    p.add_run(penanda + "\t")
                    _tulis_inline(p, m.group(2))
                    break
            else:
                self._p(b, indent=0 if pertama_setelah_judul else self.f["indent_paragraf_cm"])
                pertama_setelah_judul = False

    def _gambar(self, argumen, no_bab, penghitung):
        bagian = [x.strip() for x in argumen.split("|")]
        nama_file = bagian[0] if bagian else ""
        judul = bagian[1] if len(bagian) > 1 else ""
        sumber = bagian[2] if len(bagian) > 2 else ""
        try:
            lebar = float(bagian[3].replace(",", ".")) if len(bagian) > 3 and bagian[3] else 12.0
        except ValueError:
            lebar = 12.0
        lebar = min(lebar, self.lebar_teks_cm)

        p = self._p(align=WD_ALIGN_PARAGRAPH.CENTER, spasi=1.0, sebelum=12, indent=0)
        p.paragraph_format.keep_with_next = True
        data = self.gambar.get(nama_file)
        if data:
            try:
                p.add_run().add_picture(io.BytesIO(data), width=Cm(lebar))
            except Exception:
                data = None
                self.peringatan.append(f"Gambar '{nama_file}' tidak bisa dibaca (gunakan PNG/JPG).")
        if not data:
            r = p.add_run(f"[Gambar '{nama_file}' belum diupload]")
            r.italic = True
            r.font.color.rgb = RGBColor(0xC0, 0, 0)
            if f"Gambar '{nama_file}'" not in " ".join(self.peringatan):
                self.peringatan.append(f"Gambar '{nama_file}' dipakai di Bab {no_bab} tetapi belum diupload.")

        penghitung["gambar"] += 1
        cap = self.doc.add_paragraph(style="Judul Gambar")
        cap.add_run(f"Gambar {no_bab}.{penghitung['gambar']}. ")
        _tulis_inline(cap, judul.rstrip("."))
        if sumber:
            s = self.doc.add_paragraph(style="Sumber")
            s.alignment = WD_ALIGN_PARAGRAPH.CENTER
            s.add_run(f"Sumber: {sumber}")
        else:
            cap.paragraph_format.space_after = Pt(12)

    def _tabel(self, argumen, baris, no_bab, penghitung):
        bagian = [x.strip() for x in argumen.split("|")]
        judul = bagian[0] if bagian else ""
        sumber = bagian[1] if len(bagian) > 1 else ""
        penghitung["tabel"] += 1

        cap = self.doc.add_paragraph(style="Judul Tabel")
        cap.add_run(f"Tabel {no_bab}.{penghitung['tabel']}. ")
        _tulis_inline(cap, judul.rstrip("."))

        sel = [[c.strip() for c in b.strip().strip("|").split("|")] for b in baris] or [["(tabel kosong)"]]
        n_kolom = max(len(r) for r in sel)
        t = self.doc.add_table(rows=len(sel), cols=n_kolom)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for ri, r in enumerate(sel):
            row = t.rows[ri]
            _jaga_baris_tidak_terpotong(row)
            if ri == 0:
                _ulang_header_tabel(row)   # "Repeat Header Row"
            for ci in range(n_kolom):
                cell = row.cells[ci]
                p = cell.paragraphs[0]
                p.style = self.doc.styles["Isi Tabel"]
                if ri == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _tulis_inline(p, r[ci] if ci < len(r) else "", bold=(ri == 0))

        if sumber:
            s = self.doc.add_paragraph(style="Sumber")
            s.paragraph_format.space_before = Pt(4)
            s.add_run(f"Sumber: {sumber}")
        else:
            self._p(spasi=1.0, sesudah=6)

    def _rumus(self, rumus):
        self.no_rumus += 1
        p = self._p(spasi=self.f["spasi_isi"], align=WD_ALIGN_PARAGRAPH.LEFT, sebelum=6, sesudah=6, indent=0)
        ts = p.paragraph_format.tab_stops
        ts.add_tab_stop(Cm(self.lebar_teks_cm / 2), WD_TAB_ALIGNMENT.CENTER)
        ts.add_tab_stop(Cm(self.lebar_teks_cm), WD_TAB_ALIGNMENT.RIGHT)
        p.add_run("\t")
        _tulis_inline(p, rumus)
        p.add_run(f"\t({self.no_rumus})")

    def bab(self, no, bab):
        judul = (bab.get("judul") or "").upper()
        self.doc.add_heading(f"BAB {ROMAWI[no] if no < len(ROMAWI) else no} {judul}", level=1)
        penghitung = {"tabel": 0, "gambar": 0}
        for j, sub in enumerate(bab.get("subbab", []), start=1):
            judul_sub = (sub.get("judul") or "").strip()
            if not judul_sub:
                continue
            self.doc.add_heading(f"{no}.{j} {judul_kapital(judul_sub)}", level=2)
            isi = sub.get("isi") or ""
            if isi.strip():
                self._isi_subbab(isi, no, j, penghitung)
            else:
                p = self._p("[Isi subbab ini belum ditulis]", indent=0)
                p.runs[0].italic = True
                p.runs[0].font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        return penghitung

    # ---------------- BAGIAN AKHIR ----------------
    def daftar_pustaka(self):
        self._judul_halaman("DAFTAR PUSTAKA")
        entri = [b.strip() for b in (self.data.get("daftar_pustaka") or "").splitlines() if b.strip()]
        if not entri:
            self._p("[Tempel daftar pustaka di aplikasi, satu referensi per baris.]", indent=0)
            return
        if len(entri) < 10:
            self.peringatan.append(f"Daftar pustaka baru {len(entri)} entri. Panduan meminta minimal 10 artikel jurnal.")
        for e in sorted(entri, key=lambda s: re.sub(r"[^a-z0-9]", "", s.lower())):
            p = self.doc.add_paragraph(style="Daftar Pustaka")
            _tulis_inline(p, e)

    def lampiran(self):
        daftar = [l for l in self.data.get("lampiran", []) if (l.get("judul") or "").strip()]
        if not daftar:
            return
        self._ganti_halaman()
        self._judul_halaman("LAMPIRAN")
        for k, l in enumerate(daftar, start=1):
            if k > 1:
                self._ganti_halaman()
            p = self.doc.add_paragraph(style="Judul Lampiran")
            p.add_run(f"Lampiran {k}. {judul_kapital(l['judul'])}")
            if (l.get("isi") or "").strip():
                self._paragraf_bebas(l["isi"], spasi=self.f["spasi_isi"])
            nama = (l.get("gambar") or "").strip()
            if nama:
                data = self.gambar.get(nama)
                pp = self._p(align=WD_ALIGN_PARAGRAPH.CENTER, sebelum=12, indent=0)
                if data:
                    pp.add_run().add_picture(io.BytesIO(data), width=Cm(self.lebar_teks_cm))
                else:
                    pp.add_run(f"[Gambar '{nama}' belum diupload]").italic = True

    # ---------------- RAKIT SEMUA ----------------
    def bangun(self):
        semua_isi = "\n".join(s.get("isi") or "" for b in self.data.get("bab", []) for s in b.get("subbab", []))
        ada_tabel = bool(re.search(r"\[\[\s*TABEL\s*:", semua_isi, re.I))
        ada_gambar = bool(re.search(r"\[\[\s*GAMBAR\s*:", semua_isi, re.I))
        ada_lampiran = any((l.get("judul") or "").strip() for l in self.data.get("lampiran", []))

        # 1) Sampul: tanpa nomor halaman
        self.sampul()

        # 2) Bagian awal: nomor romawi kecil di tengah bawah
        self._section_baru("lowerRoman", "tengah", 1)
        halaman_awal = [self.pengesahan, self.pernyataan, self.kata_pengantar]
        for i, fn in enumerate(halaman_awal):
            if i:
                self._ganti_halaman()
            fn()
        self._ganti_halaman()
        self._halaman_daftar("DAFTAR ISI", 'TOC \\o "1-3" \\h \\z \\u',
                             "Klik kanan di sini lalu pilih Update Field untuk menampilkan daftar isi.")
        if ada_tabel:
            self._ganti_halaman()
            self._halaman_daftar("DAFTAR TABEL", 'TOC \\h \\z \\t "Judul Tabel,1"',
                                 "Klik kanan di sini lalu pilih Update Field.")
        if ada_gambar:
            self._ganti_halaman()
            self._halaman_daftar("DAFTAR GAMBAR", 'TOC \\h \\z \\t "Judul Gambar,1"',
                                 "Klik kanan di sini lalu pilih Update Field.")
        if ada_lampiran:
            self._ganti_halaman()
            self._halaman_daftar("DAFTAR LAMPIRAN", 'TOC \\h \\z \\t "Judul Lampiran,1"',
                                 "Klik kanan di sini lalu pilih Update Field.")
        if (self.data.get("istilah") or "").strip():
            self._ganti_halaman()
            self.daftar_istilah()
        self._ganti_halaman()
        self.intisari()
        self._ganti_halaman()
        self.abstract()

        # 3) Bagian inti: angka Arab di pojok kanan bawah, mulai dari 1
        for no, b in enumerate(self.data.get("bab", []), start=1):
            if no == 1:
                self._section_baru("decimal", "kanan", 1)
            else:
                self._ganti_halaman()
            self.bab(no, b)

        # 4) Bagian akhir
        self._ganti_halaman()
        self.daftar_pustaka()
        self.lampiran()

        # Minta Word memperbarui daftar isi otomatis saat file dibuka
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        self.doc.settings.element.append(upd)

        props = self.doc.core_properties
        props.title = self.data["identitas"].get("judul_id") or "Tugas Akhir"
        props.author = self.data["identitas"].get("nama") or ""

        buf = io.BytesIO()
        self.doc.save(buf)
        return buf.getvalue(), self.peringatan


def buat_dokumen(data, gambar=None, logo=None, fmt=None):
    """data: dict (lihat contoh_data.json). gambar: {nama_file: bytes}. logo: bytes atau None.
    Margin diambil dari data["format"] bila ada; selebihnya mengikuti FORMAT_DEB_SV_UGM."""
    return PembangunTA(data, gambar, logo, fmt or format_dari(data)).bangun()


# Struktur bab bawaan sesuai Panduan 3.2.2 (bisa diubah di aplikasi)
STRUKTUR_BAB_BAWAAN = [
    {"judul": "Pendahuluan", "subbab": ["Latar Belakang", "Rumusan Masalah", "Pertanyaan Penelitian",
                                        "Tujuan Penelitian", "Manfaat Penelitian"]},
    {"judul": "Tinjauan Pustaka", "subbab": ["Kondisi Umum/Deskripsi Topik Penelitian", "Landasan Teori",
                                             "Penelitian Terdahulu", "Hipotesis"]},
    {"judul": "Metode Penelitian", "subbab": ["Desain Penelitian", "Jenis dan Sumber Data",
                                              "Teknik Pengumpulan Data", "Teknik Analisis Data"]},
    {"judul": "Hasil dan Pembahasan", "subbab": ["Deskripsi Data", "Hasil Analisis",
                                                 "Interpretasi dan Pembahasan"]},
    {"judul": "Kesimpulan dan Saran", "subbab": ["Kesimpulan", "Saran", "Keterbatasan Penelitian"]},
]


if __name__ == "__main__":
    # Uji cepat dari Terminal:  python3 generator.py contoh_data.json
    import json
    import sys

    jalur = sys.argv[1] if len(sys.argv) > 1 else "contoh_data.json"
    with open(jalur, encoding="utf-8") as fh:
        contoh = json.load(fh)
    hasil, catatan = buat_dokumen(contoh)
    with open("hasil_contoh.docx", "wb") as fh:
        fh.write(hasil)
    print("Tersimpan: hasil_contoh.docx")
    for c in catatan:
        print(" -", c)
