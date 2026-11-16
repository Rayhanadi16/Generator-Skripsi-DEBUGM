"""
Periksa tulisan: mencari kata tidak baku di isi laporan dan menawarkan bentuk bakunya.

- muat_kata_baku()                  -> ({tidak_baku: baku}, {kata yang hanya dicocokkan utuh}); dibaca sekali
- saran_untuk(kata)                 -> bentuk baku untuk satu kata (termasuk yang berimbuhan), atau None
- cari_tidak_baku(data, abaikan)    -> daftar temuan {kata, saran, jumlah, lokasi: [(kunci_isian, label, cuplikan)]}
- ganti_semua(isian, kata, saran)   -> mengganti di semua kunci isian; mengembalikan jumlah penggantian

Daftar katanya ada di data/kata_tidak_baku.csv (kolom tidak_baku, baku, catatan):
- catatan "utuh"     : hanya dicocokkan sebagai kata utuh, boleh diikuti -nya, -lah, -pun, -kah. Dipakai untuk
                       bentuk yang sudah berimbuhan (merubah) dan kata yang awalannya menipu (nampak: "menampakkan"
                       adalah bentuk baku dari "tampak", bukan me- + nampak).
- catatan "ragu: ..." : belum dipakai. Baris ini menunggu dicek manusia; hapus kata "ragu" untuk mengaktifkannya.

Yang tidak diperiksa: abstract, daftar pustaka, kutipan langsung dalam tanda petik, kutipan (Nama, tahun),
teks *miring*, dan isi penanda [[...]].
"""

import csv
import functools
import re
from pathlib import Path

import sitasi

BERKAS_KATA = Path(__file__).resolve().parent / "data" / "kata_tidak_baku.csv"
ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

# urut dari yang terpanjang, supaya "meng" dicoba sebelum "me"
AWALAN = ["memper", "diper", "meng", "meny", "peng", "mem", "men", "pem", "pen", "per", "ter", "ber",
          "di", "me", "pe", "se", "ke"]
KLITIK = ["nya", "lah", "pun", "kah"]
AKHIRAN = ["kannya", "annya", "inya", "kan", "an", "i"] + KLITIK

RE_KATA = re.compile(r"[^\W\d_]+")
RE_LEWATI = [
    re.compile(r"\[\[.*?\]\]"),                              # penanda, termasuk [[REF: ...]] di tengah kalimat
    re.compile(r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’'),            # kutipan langsung
    re.compile(r"(?<!\*)\*(?!\*)[^*\n]+?(?<!\*)\*(?!\*)"),   # *miring* (bukan **tebal**)
    re.compile(r"https?://\S+|\S+@\S+\.\S+"),
]


@functools.lru_cache(maxsize=1)
def muat_kata_baku():
    peta, utuh = {}, set()
    with open(BERKAS_KATA, encoding="utf-8", newline="") as berkas:
        for baris in csv.DictReader(berkas):
            salah, benar = baris["tidak_baku"].strip().lower(), baris["baku"].strip()
            catatan = (baris.get("catatan") or "").strip().lower()
            if not salah or not benar or catatan.startswith("ragu"):
                continue
            peta[salah] = benar
            if catatan.startswith("utuh"):
                utuh.add(salah)
    return peta, utuh


@functools.lru_cache(maxsize=20000)
def saran_untuk(kata):
    """Bentuk baku untuk satu kata huruf kecil, atau None bila katanya tidak ada di daftar."""
    peta, utuh = muat_kata_baku()
    for klitik in [""] + KLITIK:
        dasar = kata[: len(kata) - len(klitik)] if klitik else kata
        if (not klitik or kata.endswith(klitik)) and dasar in peta:
            return peta[dasar] + klitik
    for awalan in AWALAN + [""]:
        if not kata.startswith(awalan):
            continue
        sisa = kata[len(awalan):]
        for akhiran in AKHIRAN + [""]:
            if not (awalan or akhiran) or (akhiran and not sisa.endswith(akhiran)):
                continue
            if akhiran.startswith("i") and not awalan:
                continue    # akhiran -i tanpa awalan terlalu sering menipu: "trendi" bukan trend + -i
            dasar = sisa[: len(sisa) - len(akhiran)] if akhiran else sisa
            if len(dasar) >= 3 and dasar in peta and dasar not in utuh:
                saran = awalan + peta[dasar] + akhiran
                if dikenal_id(saran):   # "penelitan" bukan pen- + elit + -an: "penelitean" bukan kata
                    return saran
    return None


def pola_kapital(asli, pengganti):
    """Analisa -> Analisis, ANALISA -> ANALISIS, analisa -> analisis."""
    if asli.isupper() and len(asli) > 1:
        return pengganti.upper()
    if asli[:1].isupper():
        return pengganti[:1].upper() + pengganti[1:]
    return pengganti


def _rentang_dilewati(teks):
    rentang = [m.span() for pola in RE_LEWATI for m in pola.finditer(teks)]
    for m in sitasi.RE_KURUNG.finditer(teks):      # (Santoso, 2021): nama di dalam kutipan bukan urusan ejaan
        if any(sitasi.RE_BAGIAN.match(b.strip()) for b in m.group(1).split(";")):
            rentang.append(m.span())
    return rentang


def kata_diperiksa(teks):
    """Hasilkan (awal, akhir, kata) untuk setiap kata yang boleh diperiksa di satu teks."""
    teks = teks or ""
    lewati = _rentang_dilewati(teks)
    for m in RE_KATA.finditer(teks):
        if not any(a <= m.start() < b for a, b in lewati):
            yield m.start(), m.end(), m.group(0)


def _temuan_di_teks(teks):
    for awal, akhir, kata in kata_diperiksa(teks):
        saran = saran_untuk(kata.lower())
        if saran:
            yield awal, akhir, kata, saran


def _cuplikan(teks, awal, akhir, lebar=45):
    kiri, kanan = max(0, awal - lebar), min(len(teks), akhir + lebar)
    potong = lambda t: re.sub(r"\s+", " ", t)   # noqa: E731
    return (("…" if kiri else "") + potong(teks[kiri:awal]) + "⟦" + teks[awal:akhir] + "⟧"
            + potong(teks[akhir:kanan]) + ("…" if kanan < len(teks) else ""))


def bagian_teks(data):
    """(kunci_isian, label lokasi, teks) untuk setiap bagian yang diperiksa, urut seperti di laporan."""
    yield "id_judul_id", "Judul TA", (data.get("identitas") or {}).get("judul_id", "")
    yield "kata_pengantar", "Kata pengantar", data.get("kata_pengantar", "")
    yield "intisari", "Intisari", data.get("intisari", "")
    for i, bab in enumerate(data.get("bab", [])):
        rom = ROMAWI[i + 1] if i + 1 < len(ROMAWI) else str(i + 1)
        yield f"bab{i}_judul", f"Judul Bab {rom}", bab.get("judul", "")
        for j, sub in enumerate(bab.get("subbab", [])):
            yield f"bab{i}_s{j}_judul", f"Bab {rom}, judul subbab {i + 1}.{j + 1}", sub.get("judul", "")
            yield f"bab{i}_s{j}_isi", f"Bab {rom}, {i + 1}.{j + 1}", sub.get("isi", "")


def cari_tidak_baku(data, abaikan=()):
    abaikan = {a.lower() for a in abaikan}
    temuan = {}
    for kunci, label, teks in bagian_teks(data):
        for awal, akhir, kata, saran in _temuan_di_teks(teks or ""):
            k = kata.lower()
            if k in abaikan:
                continue
            t = temuan.setdefault(k, {"kata": k, "saran": saran, "jumlah": 0, "lokasi": []})
            t["jumlah"] += 1
            t["lokasi"].append((kunci, label, _cuplikan(teks, awal, akhir)))
    return list(temuan.values())


def ganti_di_teks(teks, kata, saran):
    """Ganti semua kemunculan `kata` (kata utuh, di luar bagian yang dilewati) dengan `saran`; pola kapital dijaga."""
    hasil, terakhir, jumlah = [], 0, 0
    for awal, akhir, asli in kata_diperiksa(teks):
        if asli.lower() == kata.lower():
            hasil += [teks[terakhir:awal], pola_kapital(asli, saran)]
            terakhir = akhir
            jumlah += 1
    return "".join(hasil) + teks[terakhir:], jumlah


def kunci_isian(isian):
    """Kunci session_state yang diperiksa, dari isian berkunci datar (lihat kumpulkan_data di app.py)."""
    kunci = ["id_judul_id", "kata_pengantar", "intisari"]
    for i in range(isian.get("jml_bab", 0)):
        kunci.append(f"bab{i}_judul")
        for j in range(isian.get(f"bab{i}_n", 0)):
            kunci += [f"bab{i}_s{j}_judul", f"bab{i}_s{j}_isi"]
    return kunci


def ganti_semua(isian, kata, saran):
    total = 0
    for kunci in kunci_isian(isian):
        teks = isian.get(kunci) or ""
        if not teks:
            continue
        baru, n = ganti_di_teks(teks, kata, saran)
        if n:
            isian[kunci] = baru
            total += n
    return total


# ---------------------------------------------------------------------------
# Kemungkinan typo dan istilah asing belum miring (kamus Hunspell, dibaca dengan spylls)
# ---------------------------------------------------------------------------
FOLDER_KAMUS = Path(__file__).resolve().parent / "kamus"
KLITIK_LEPAS = {"nya", "lah", "kah", "pun", "ku", "mu"}        # sisa kata berhubung: "data-nya"
# imbuhan gabungan yang sah tetapi tidak selalu dikenali kamus: ketidakpastian, keberhasilan, pemberdayaan
AWALAN_GABUNGAN = ["ketidak", "keber", "keter", "pember", "pemer", "berke", "berpe", "terper"]
# Awalan sengau hanya sah di depan huruf tertentu. Tanpa ini "mengunakan" lolos sebagai men- + gunakan.
HURUF_SESUDAH = {"men": "cdjtz", "pen": "cdjtz", "meng": "aeioughkq", "peng": "aeioughkq", "mem": "bfpv",
                 "pem": "bfpv", "meny": "aeiou", "me": "lmnrwy", "pe": "lmnrwy"}
# bentuk terikat yang ditulis dengan tanda hubung atau serangkai: sub-subbab, non-pemerintah
BENTUK_TERIKAT = {"sub", "non", "antar", "pra", "pasca", "anti", "multi", "semi", "intra", "inter", "supra", "ultra",
                  "eks", "pro", "kontra", "swa", "tuna", "maha", "nara", "adi", "dwi", "tri", "catur", "panca", "eka"}


@functools.lru_cache(maxsize=2)
def _kamus(bahasa):
    """Kamus dimuat sekali per proses (sekitar 0,1 detik), lalu dipakai semua pengunjung."""
    from spylls.hunspell import Dictionary
    return Dictionary.from_files(str(FOLDER_KAMUS / bahasa))


@functools.lru_cache(maxsize=1)
def _istilah_dikenal():
    """Istilah teknis yang sah tetapi tidak ada di kamus (data/istilah_dikenal.txt)."""
    berkas = BERKAS_KATA.parent / "istilah_dikenal.txt"
    return {b.strip().lower() for b in berkas.read_text(encoding="utf-8").splitlines() if b.strip() and not b.startswith("#")}


@functools.lru_cache(maxsize=100000)
def dikenal_id(kata):
    """True bila kata (huruf kecil) dikenal kamus bahasa Indonesia, langsung atau lewat imbuhan gabungan."""
    kamus = _kamus("id_ID")
    if kamus.lookup(kata) or kata in BENTUK_TERIKAT or kata in _istilah_dikenal():
        return True
    for awalan in ("te", "be", "pe"):        # terencana = ter- + rencana, berencana, perencana: r-nya luluh
        if kata.startswith(awalan + "r") and kamus.lookup(kata[len(awalan):]):
            return True
    for klitik in KLITIK + ["ku", "mu"]:     # datanya, hasilnya: kata yang sah + klitik
        if kata.endswith(klitik) and len(kata) - len(klitik) >= 3 and dikenal_id(kata[: -len(klitik)]):
            return True
    for awalan in AWALAN:                    # menjorok = men- + jorok, dicek = di- + cek
        sisa = kata[len(awalan):]
        if (kata.startswith(awalan) and len(sisa) >= 3 and sisa[0] in HURUF_SESUDAH.get(awalan, sisa[0])
                and kamus.lookup(sisa)):
            return True
    for awalan in AWALAN:                    # dikomunikasikan = di- + komunikasi + -kan (kata serapan berimbuhan)
        sisa = kata[len(awalan):]
        if not kata.startswith(awalan) or not sisa or sisa[0] not in HURUF_SESUDAH.get(awalan, sisa[0]):
            continue
        for akhiran in AKHIRAN:
            dasar = sisa[: len(sisa) - len(akhiran)]
            if sisa.endswith(akhiran) and len(dasar) >= 5 and kamus.lookup(dasar):   # 5 huruf: "perusahan" tetap typo
                return True
    for awalan in AWALAN_GABUNGAN:
        if not kata.startswith(awalan):
            continue
        sisa = kata[len(awalan):]
        for akhiran in AKHIRAN + [""]:
            dasar = sisa[: len(sisa) - len(akhiran)] if akhiran and sisa.endswith(akhiran) else (sisa if not akhiran else "")
            if len(dasar) >= 4 and kamus.lookup(dasar):
                return True
    return False


@functools.lru_cache(maxsize=100000)
def dikenal_en(kata):
    return _kamus("en_US").lookup(kata)


def _jarak(a, b):
    """Jarak sunting (Levenshtein) antara dua kata."""
    sebelum = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        kini = [i]
        for j, cb in enumerate(b, start=1):
            kini.append(min(sebelum[j] + 1, kini[j - 1] + 1, sebelum[j - 1] + (ca != cb)))
        sebelum = kini
    return sebelum[-1]


@functools.lru_cache(maxsize=5000)
def saran_ejaan(kata, maks=3):
    """Saran ejaan untuk satu kata. Lambat (sampai sekitar satu detik per kata), jadi hanya untuk yang ditampilkan.

    Yang ditawarkan hanya saran yang dekat dengan kata aslinya: yang berjarak satu suntingan bila ada, kalau
    tidak ada baru yang berjarak dua. Saran yang lebih jauh biasanya kata lain, bukan pembetulan.
    """
    calon = []
    if kata.endswith("kan") and dikenal_id(kata[:-3] + "kkan"):      # menunjukan -> menunjukkan
        calon.append(kata[:-3] + "kkan")
    for s in _kamus("id_ID").suggest(kata):
        if s.lower() not in calon and " " not in s and "-" not in s:
            calon.append(s.lower())
        if len(calon) >= 8:
            break
    dekat = [c for c in calon if _jarak(kata, c) <= 1] or [c for c in calon if _jarak(kata, c) <= 2]
    return tuple(dekat[:maks])


def _kata_dikecualikan(data):
    """Kata yang tidak perlu dicek: daftar istilah, nama di Identitas dan Pengesahan, dan isi daftar pustaka."""
    sumber = [data.get("daftar_pustaka", ""), data.get("kata_kunci", "")]
    sumber += [baris.split(":", 1)[0] for baris in (data.get("istilah") or "").splitlines()]
    sumber += [(data.get("identitas") or {}).get(k, "") for k in ("nama", "pembimbing", "prodi", "fakultas")]
    sumber += [v for k, v in (data.get("pengesahan") or {}).items() if k.endswith("_nama")]
    return {m.group(0).lower() for teks in sumber for m in RE_KATA.finditer(teks or "")}


def _awal_kalimat(teks, awal):
    sebelum = teks[:awal].rstrip(" \t\"“‘'(*")
    return not sebelum or sebelum[-1] in ".!?:\n"


def periksa_ejaan(data, abaikan=()):
    """Satu lintasan untuk dua daftar: {"typo": [...], "asing": [...]}, masing-masing {kata, jumlah, lokasi}."""
    abaikan = {a.lower() for a in abaikan} | _kata_dikecualikan(data)
    hasil = {"typo": {}, "asing": {}}
    for kunci, label, teks in bagian_teks(data):
        teks = teks or ""
        naratif = [m.span("nama") for m in sitasi.RE_NARATIF.finditer(teks)]     # Santoso dan Putri (2021)
        for awal, akhir, kata in kata_diperiksa(teks):
            k = kata.lower()
            if len(k) < 3 or k in KLITIK_LEPAS or k in abaikan:
                continue
            if kata.isupper():                                             # singkatan: BPS, OJK, ROA
                continue
            if kata[0].isupper() and not _awal_kalimat(teks, awal):        # nama diri di tengah kalimat
                continue
            if any(a <= awal < b for a, b in naratif):
                continue
            if (awal and teks[awal - 1].isdigit()) or (akhir < len(teks) and teks[akhir].isdigit()):
                continue                                                   # x1, 2SLS, H1
            if dikenal_id(k) or saran_untuk(k):                            # kata tidak baku sudah punya bagiannya sendiri
                continue
            jenis = "asing" if dikenal_en(k) else "typo"
            t = hasil[jenis].setdefault(k, {"kata": k, "jumlah": 0, "lokasi": []})
            t["jumlah"] += 1
            t["lokasi"].append((kunci, label, _cuplikan(teks, awal, akhir)))
    return {jenis: list(daftar.values()) for jenis, daftar in hasil.items()}


def cari_typo(data, abaikan=()):
    return periksa_ejaan(data, abaikan)["typo"]


def cari_istilah_asing(data, abaikan=()):
    return periksa_ejaan(data, abaikan)["asing"]


def miringkan_di_teks(teks, kata):
    hasil, terakhir, jumlah = [], 0, 0
    for awal, akhir, asli in kata_diperiksa(teks):
        if asli.lower() == kata.lower():
            hasil += [teks[terakhir:awal], f"*{asli}*"]
            terakhir = akhir
            jumlah += 1
    return "".join(hasil) + teks[terakhir:], jumlah


def jadikan_miring(isian, kata):
    """Bungkus semua kemunculan `kata` dengan *...* di semua kunci isian; mengembalikan jumlahnya."""
    total = 0
    for kunci in kunci_isian(isian):
        teks = isian.get(kunci) or ""
        if teks:
            baru, n = miringkan_di_teks(teks, kata)
            if n:
                isian[kunci] = baru
                total += n
    return total


def ringkasan(data, abaikan=()):
    """Jumlah ketiga jenis temuan dan satu kalimat ringkas untuk Preview dan tahap Buat file (None bila bersih)."""
    ejaan = periksa_ejaan(data, abaikan)
    jumlah = {"tidak_baku": len(cari_tidak_baku(data, abaikan)), "typo": len(ejaan["typo"]), "asing": len(ejaan["asing"])}
    bagian = [f"{n} {nama}" for n, nama in ((jumlah["tidak_baku"], "kata tidak baku"), (jumlah["typo"], "kemungkinan typo"),
                                           (jumlah["asing"], "istilah asing belum miring")) if n]
    if not bagian:
        return jumlah, None
    daftar = bagian[0] if len(bagian) == 1 else ", ".join(bagian[:-1]) + (", dan " if len(bagian) > 2 else " dan ") + bagian[-1]
    return jumlah, f"Ada {daftar}. Lihat tab Periksa tulisan."
