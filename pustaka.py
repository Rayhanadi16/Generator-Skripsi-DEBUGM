"""
Bantuan menyusun satu entri daftar pustaka (gaya APA edisi 7).

- cari_doi(pdf_bytes)     -> (doi atau "", judul dari metadata PDF atau "")
- ambil_crossref(doi)     -> isian (dict) dari basis data Crossref; butuh internet
- format_apa(isian)       -> teks satu baris; *...* menandai huruf miring (sama dengan penanda di generator.py)

isian = {"jenis", "penulis" (satu per baris: "Belakang, Nama Depan"), "lembaga" (bool), "tahun", "judul",
         "wadah" (nama jurnal / penerbit / nama situs), "volume", "nomor", "halaman", "tautan"}

PDF hanya dibaca di memori untuk mencari DOI; tidak disimpan.
"""

import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request

JENIS = ["Artikel jurnal", "Buku", "Halaman web atau laporan"]
RE_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>{}|\\^`]+)", re.I)
KOSONG = {"jenis": JENIS[0], "penulis": "", "lembaga": False, "tahun": "", "judul": "", "wadah": "",
          "volume": "", "nomor": "", "halaman": "", "tautan": ""}


class GagalAmbil(Exception):
    """Pesannya sudah siap ditampilkan ke pengguna."""


# ---------------------------------------------------------------------------
# DOI
# ---------------------------------------------------------------------------
def rapikan_doi(teks):
    """Terima DOI polos, 'doi:10...', atau tautan https://doi.org/10...; kembalikan DOI polos atau ''."""
    m = RE_DOI.search(urllib.parse.unquote((teks or "").strip()))
    if not m:
        return ""
    return m.group(1).rstrip(".,;:)]}'\"")


def cari_doi(pdf_bytes, maks_halaman=3):
    """Cari DOI di metadata dan beberapa halaman pertama PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise GagalAmbil("Pembaca PDF belum terpasang. Jalankan: pip install pypdf") from e
    try:
        pdf = PdfReader(io.BytesIO(pdf_bytes))
        if pdf.is_encrypted:
            pdf.decrypt("")
        meta = pdf.metadata or {}
        judul = str(meta.get("/Title") or "").strip()
        kandidat = " ".join(str(v) for v in meta.values() if v)
        for hal in pdf.pages[:maks_halaman]:
            kandidat += "\n" + (hal.extract_text() or "")
    except Exception as e:
        raise GagalAmbil("PDF ini tidak bisa dibaca. Coba tempel DOI-nya atau isi rinciannya sendiri.") from e
    # DOI kadang terpotong spasi/baris baru tepat setelah garis miring
    kandidat = re.sub(r"(10\.\d{4,9}/)\s+", r"\1", kandidat)
    if len(judul) < 8 or judul.lower() in ("untitled", "anonymous") or judul.lower().endswith((".pdf", ".doc", ".docx")) or judul.lower().startswith("microsoft word"):
        judul = ""
    return rapikan_doi(kandidat), judul


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------
def _bersih(teks):
    teks = re.sub(r"<[^>]+>", "", str(teks or ""))
    return re.sub(r"\s+", " ", teks).strip()


def dari_crossref(pesan):
    """Ubah jawaban Crossref (bagian 'message') menjadi isian."""
    isian = dict(KOSONG)
    tipe = pesan.get("type", "")
    wadah = _bersih((pesan.get("container-title") or [""])[0])
    if tipe in ("book", "monograph", "edited-book", "reference-book"):
        isian["jenis"] = "Buku"
        isian["wadah"] = _bersih(pesan.get("publisher"))
    elif tipe in ("report", "dataset", "posted-content") and not wadah:
        isian["jenis"] = "Halaman web atau laporan"
        isian["wadah"] = _bersih(pesan.get("publisher"))
    else:
        isian["wadah"] = wadah

    penulis = []
    for a in pesan.get("author") or []:
        if a.get("family"):
            penulis.append(f"{_bersih(a['family'])}, {_bersih(a.get('given'))}".rstrip(", "))
        elif a.get("name"):
            penulis.append(_bersih(a["name"]))
    isian["penulis"] = "\n".join(penulis)
    isian["lembaga"] = bool(penulis) and not any(a.get("family") for a in pesan.get("author") or [])

    for kunci in ("published-print", "published", "issued", "published-online", "created"):
        bagian = (pesan.get(kunci) or {}).get("date-parts") or [[None]]
        if bagian[0] and bagian[0][0]:
            isian["tahun"] = str(bagian[0][0])
            break
    isian["judul"] = _bersih((pesan.get("title") or [""])[0])
    sub = _bersih((pesan.get("subtitle") or [""])[0])
    if sub and sub.lower() not in isian["judul"].lower():
        isian["judul"] += f": {sub}"
    isian["volume"] = _bersih(pesan.get("volume"))
    isian["nomor"] = _bersih(pesan.get("issue"))
    isian["halaman"] = _bersih(pesan.get("page") or pesan.get("article-number"))
    if pesan.get("DOI"):
        isian["tautan"] = f"https://doi.org/{pesan['DOI']}"
    return isian


def ambil_crossref(doi, batas_detik=12):
    doi = rapikan_doi(doi)
    if not doi:
        raise GagalAmbil("DOI tidak dikenali. Contoh DOI: 10.1257/jel.52.1.5")
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    minta = urllib.request.Request(url, headers={"User-Agent": "GeneratorLaporanTA/1.0 (daftar pustaka)"})
    try:
        with urllib.request.urlopen(minta, timeout=batas_detik) as jawab:
            data = json.loads(jawab.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GagalAmbil(f"DOI {doi} tidak terdaftar di Crossref. Isi rinciannya sendiri di bawah.") from e
        raise GagalAmbil(f"Crossref menolak permintaan (kode {e.code}). Coba lagi sebentar lagi.") from e
    except Exception as e:
        raise GagalAmbil("Tidak bisa menghubungi Crossref. Periksa koneksi internet, atau isi rinciannya sendiri.") from e
    isian = dari_crossref(data.get("message") or {})
    if not isian["tautan"]:
        isian["tautan"] = f"https://doi.org/{doi}"
    return isian


# ---------------------------------------------------------------------------
# Format APA 7
# ---------------------------------------------------------------------------
def _inisial(nama_depan):
    hasil = []
    for kata in re.split(r"\s+", nama_depan.strip()):
        if not kata:
            continue
        bagian = [b for b in kata.split("-") if b]
        if bagian:
            hasil.append("-".join(b[0].upper() + "." for b in bagian))
    return " ".join(hasil)


def nama_apa(baris, lembaga=False):
    """'Lusardi, Annamaria' -> 'Lusardi, A.'; 'Annamaria Lusardi' -> 'Lusardi, A.'; lembaga ditulis apa adanya."""
    baris = re.sub(r"\s+", " ", baris).strip().strip(",")
    if not baris:
        return ""
    if lembaga:
        return baris
    if "," in baris:
        belakang, depan = (x.strip() for x in baris.split(",", 1))
    else:
        kata = baris.split(" ")
        if len(kata) == 1:      # nama tunggal, umum di Indonesia
            return baris
        belakang, depan = kata[-1], " ".join(kata[:-1])
    ini = _inisial(depan)
    return f"{belakang}, {ini}" if ini else belakang


def penulis_apa(teks, lembaga=False):
    nama = [nama_apa(b, lembaga) for b in (teks or "").splitlines()]
    nama = [n for n in nama if n]
    if not nama:
        return ""
    if len(nama) == 1:
        return nama[0]
    if len(nama) > 20:          # APA 7: 19 pertama, elipsis, lalu penulis terakhir
        return ", ".join(nama[:19]) + ", . . . " + nama[-1]
    return ", ".join(nama[:-1]) + ", & " + nama[-1]


def _titik(teks):
    teks = teks.strip()
    return teks if not teks or teks[-1] in ".?!" else teks + "."


def _halaman(teks):
    return re.sub(r"\s*[-–—]+\s*", "–", (teks or "").strip())


def _tautan(teks):
    teks = (teks or "").strip()
    doi = rapikan_doi(teks) if not teks.lower().startswith("http") or "doi.org" in teks.lower() else ""
    return f"https://doi.org/{doi}" if doi else teks


def format_apa(isian):
    i = {**KOSONG, **(isian or {})}
    judul = re.sub(r"\s+", " ", i["judul"]).strip().rstrip(".")
    wadah = re.sub(r"\s+", " ", i["wadah"]).strip().rstrip(".")
    penulis = penulis_apa(i["penulis"], i["lembaga"])
    tahun = f"({i['tahun'].strip() or 'n.d.'})."
    tautan = _tautan(i["tautan"])
    bagian = []

    if i["jenis"] == "Buku":
        inti = _titik(f"*{judul}*") if judul else ""
        bagian = [_titik(penulis), tahun, inti] if penulis else [inti, tahun]
        if wadah:
            bagian.append(_titik(wadah))
    elif i["jenis"] == "Halaman web atau laporan":
        inti = _titik(f"*{judul}*") if judul else ""
        bagian = [_titik(penulis), tahun, inti] if penulis else [inti, tahun]
        if wadah and wadah.lower() != penulis.lower().rstrip("."):
            bagian.append(_titik(wadah))
    else:   # Artikel jurnal
        inti = _titik(judul) if judul else ""
        bagian = [_titik(penulis), tahun, inti] if penulis else [inti, tahun]
        sumber = ""
        if wadah:
            vol, no, hal = i["volume"].strip(), i["nomor"].strip(), _halaman(i["halaman"])
            sumber = f"*{wadah}, {vol}*" if vol else f"*{wadah}*"
            if no:
                sumber += f"({no})"
            if hal:
                sumber += f", {hal}"
            sumber += "."
        if sumber:
            bagian.append(sumber)
    if tautan:
        bagian.append(tautan)
    return " ".join(b for b in bagian if b).strip()


def kurang(isian):
    """Daftar isian penting yang masih kosong, untuk ditampilkan sebagai pengingat."""
    i = {**KOSONG, **(isian or {})}
    perlu = [("penulis", "penulis"), ("tahun", "tahun"), ("judul", "judul")]
    if i["jenis"] == "Artikel jurnal":
        perlu += [("wadah", "nama jurnal"), ("volume", "volume"), ("halaman", "halaman")]
    elif i["jenis"] == "Buku":
        perlu += [("wadah", "penerbit")]
    else:
        perlu += [("tautan", "alamat web")]
    return [nama for kunci, nama in perlu if not str(i[kunci]).strip()]
