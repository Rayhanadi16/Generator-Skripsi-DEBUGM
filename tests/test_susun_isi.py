import io
import zipfile

from PIL import Image

import susun_isi as si
from conftest import ke_tahap, tombol

TEKS = "\n".join([
    "Paragraf pertama yang cukup panjang untuk dipotong cuplikannya nanti.",
    "",
    "### Sub Satu",
    "[[GAMBAR: a.png | Grafik Penjualan | BPS (2024) | 10 | #jual]]",
    "[[TABEL: Statistik | Data primer]]",
    "Tahun | Jumlah",
    "2024 | 150",
    "[[/TABEL]]",
    "[[RUMUS: Y = a + bX | #model]]",
    "1. butir pertama",
    "Paragraf penutup.",
])


def png(warna):
    wadah = io.BytesIO()
    Image.new("RGB", (40, 30), warna).save(wadah, "PNG")
    return wadah.getvalue()


def test_pecah_blok_mengenali_semua_jenis():
    blok = si.pecah_blok(TEKS)
    assert [b["jenis"] for b in blok] == ["paragraf", "subjudul", "gambar", "tabel", "rumus", "daftar", "paragraf"]
    tabel = blok[3]
    assert (tabel["baris_awal"], tabel["baris_akhir"]) == (4, 7)
    assert tabel["teks"].count("\n") == 3 and tabel["data"]["judul"] == "Statistik"
    assert blok[2]["data"] == {"file": "a.png", "judul": "Grafik Penjualan", "sumber": "BPS (2024)",
                               "lebar": 10.0, "label": "jual"}
    assert blok[4]["data"] == {"rumus": "Y = a + bX", "label": "model"}


def test_pecah_blok_tabel_tidak_ditutup_dan_teks_kosong():
    blok = si.pecah_blok("Awal\n[[TABEL: T]]\na | b")
    assert blok[1]["jenis"] == "tabel" and blok[1]["baris_akhir"] == 2 and not blok[1]["data"]["tertutup"]
    assert si.pecah_blok("") == [] and si.pecah_blok(None) == []


def test_pilihan_letak():
    pilihan = si.pilihan_letak(TEKS)
    label = [l for _, l in pilihan]
    assert pilihan[0] == (0, "Di awal subbab") and pilihan[-1] == (7, "Di akhir subbab")
    assert label[1] == "Setelah paragraf 1: Paragraf pertama yang cukup panjang untu…"
    assert "Setelah Gambar: Grafik Penjualan" in label and "Setelah Tabel: Statistik" in label
    assert "Setelah sub-subbab: Sub Satu" in label and "Setelah paragraf 2: Paragraf penutup." in label
    assert si.pilihan_letak("") == [(0, "Di akhir subbab")]


def test_sisipkan_gambar_awal_tengah_akhir():
    teks = "Satu\nDua\nTiga"
    assert si.sisipkan_gambar(teks, 0, "g.png", "J").splitlines()[0] == "[[GAMBAR: g.png | J |  | 12]]"
    assert si.sisipkan_gambar(teks, 1, "g.png", "J", "S", 8.5).splitlines() == [
        "Satu", "[[GAMBAR: g.png | J | S | 8.5]]", "Dua", "Tiga"]
    assert si.sisipkan_gambar(teks, 3, "g.png", "J").splitlines()[-1].startswith("[[GAMBAR")
    assert si.sisipkan_gambar("", 0, "g.png", "J") == "[[GAMBAR: g.png | J |  | 12]]"


def test_sisip_setelah_tabel_tidak_memecah_tabel():
    hasil = si.sisipkan_gambar(TEKS, 4, "g.png", "J")
    blok = si.pecah_blok(hasil)
    assert [b["jenis"] for b in blok][3:5] == ["tabel", "gambar"]
    assert blok[3]["teks"] == si.pecah_blok(TEKS)[3]["teks"]


def test_penanda_aman_dari_pemisah_dan_penutup():
    penanda = si.penanda_gambar("a.png", "Laba | Rugi ]] 2024", "BPS]]\n(2024)", 12)
    data = si.pecah_blok(penanda)[0]
    assert data["jenis"] == "gambar"
    assert data["data"]["judul"] == "Laba / Rugi ] 2024" and data["data"]["sumber"] == "BPS] (2024)"
    assert si.pecah_blok(si.penanda_gambar("a.png", "#tagar", "", 12))[0]["data"]["judul"] == "tagar"


def test_nama_bentrok_diberi_nama_baru():
    simpanan = {"grafik.png": b"A", "grafik-2.png": b"B"}
    assert si.nama_bebas("grafik.png", b"A", simpanan) == "grafik.png"
    assert si.nama_bebas("grafik.png", b"B", simpanan) == "grafik-2.png"
    assert si.nama_bebas("grafik.png", b"C", simpanan) == "grafik-3.png"
    assert si.nama_bebas("baru.jpg", b"C", simpanan) == "baru.jpg"


def urutan_dokumen(isi_docx):
    """Isi badan dokumen berurutan: teks paragraf, atau '<gambar>' untuk paragraf yang memuat gambar."""
    from docx import Document
    hasil = []
    for p in Document(io.BytesIO(isi_docx)).paragraphs:
        if p._p.xpath(".//pic:pic"):
            hasil.append("<gambar>")
        elif p.text.strip():
            hasil.append(p.text.strip())
    return hasil


def hasil_docx(at):
    hasil = at.session_state["_hasil"]
    return hasil if isinstance(hasil, bytes) else hasil.getvalue()


def test_tambah_gambar_dari_subbab_masuk_word(aplikasi):
    at = aplikasi
    at.session_state["id_judul_id"] = "Judul Uji"
    at.session_state["bab0_s0_isi"] = "Paragraf satu uji.\nParagraf dua uji."
    at = at.run()
    at = at.button(key="tg_0_0").click().run()
    n = at.session_state["_pn"]
    at.file_uploader(key=f"pn_file{n}").upload("grafik.png", png("red"), "image/png")
    at.text_input(key=f"pn_judul{n}").set_value("Grafik Uji")
    at.selectbox(key=f"pn_letak{n}").set_value(1)
    at = at.run()
    at = at.button(key=f"pn_sisip{n}").click().run()
    assert not at.exception
    assert at.session_state["bab0_s0_isi"].splitlines() == [
        "Paragraf satu uji.", "[[GAMBAR: grafik.png | Grafik Uji |  | 12]]", "Paragraf dua uji."]
    assert at.session_state["_panel"] is None

    # nama sama, isi beda: gambar pertama tidak tertimpa
    at = at.button(key="tg_0_0").click().run()
    n = at.session_state["_pn"]
    at.file_uploader(key=f"pn_file{n}").upload("grafik.png", png("blue"), "image/png")
    at.text_input(key=f"pn_judul{n}").set_value("Grafik Kedua")
    at = at.run()
    at = at.button(key=f"pn_sisip{n}").click().run()
    simpanan = at.session_state["_gambar_simpan"]
    assert simpanan["grafik.png"] == png("red") and simpanan["grafik-2.png"] == png("blue")

    at = tombol(ke_tahap(at, "buat"), "Buat file Word").click().run()
    assert not at.exception
    isi = hasil_docx(at)
    assert len([n for n in zipfile.ZipFile(io.BytesIO(isi)).namelist() if n.startswith("word/media/")]) == 2
    urut = urutan_dokumen(isi)
    k = urut.index("Paragraf satu uji.")
    assert urut[k + 1] == "<gambar>" and urut[k + 2].startswith("Gambar 1.1. Grafik Uji")
    assert urut.index("Paragraf dua uji.") > k + 2


def test_tambah_gambar_ditolak_tanpa_file_atau_judul(aplikasi):
    at = aplikasi.button(key="tg_0_0").click().run()
    n = at.session_state["_pn"]
    at = at.button(key=f"pn_sisip{n}").click().run()
    assert at.session_state["bab0_s0_isi"] == "" and at.session_state["_panel"] is not None
    at.file_uploader(key=f"pn_file{n}").upload("a.png", png("red"), "image/png")
    at = at.run()
    at = at.button(key=f"pn_sisip{n}").click().run()
    assert at.session_state["bab0_s0_isi"] == ""


# ---------------- Atur susunan ----------------
def jenis(teks):
    return [b["jenis"] for b in si.pecah_blok(teks)]


def test_pindah_naik_turun_melewati_tabel_utuh():
    turun = si.pindah_blok(TEKS, 2, 1)          # gambar turun melewati tabel
    assert jenis(turun) == ["paragraf", "subjudul", "tabel", "gambar", "rumus", "daftar", "paragraf"]
    assert si.pecah_blok(turun)[2]["teks"] == si.pecah_blok(TEKS)[3]["teks"]
    assert si.pindah_blok(turun, 3, -1) == TEKS  # naik lagi mengembalikan teks semula
    naik = si.pindah_blok(TEKS, 3, -1)           # tabel naik melewati gambar
    assert jenis(naik) == jenis(turun) and si.pecah_blok(naik)[2]["teks"].count("\n") == 3


def test_pindah_di_batas_tidak_mengubah_teks():
    assert si.pindah_blok(TEKS, 0, -1) == TEKS and si.pindah_blok(TEKS, 6, 1) == TEKS
    assert not si.bisa_pindah(TEKS, 0, -1) and si.bisa_pindah(TEKS, 0, 1)


def test_pindah_melewati_baris_kosong_hanya_menukar_dua_blok():
    teks = "Satu *miring*\n\n[[GAMBAR: a.png | J]]\nTiga"
    assert si.pindah_blok(teks, 1, -1) == "[[GAMBAR: a.png | J]]\n\nSatu *miring*\nTiga"


def test_ubah_gambar_mempertahankan_label():
    baru = si.ubah_gambar(TEKS, 2, judul="Judul Baru", lebar=8)
    data = si.pecah_blok(baru)[2]["data"]
    assert data == {"file": "a.png", "judul": "Judul Baru", "sumber": "BPS (2024)", "lebar": 8.0, "label": "jual"}
    assert si.pecah_blok(si.ubah_gambar(TEKS, 2, file="b.png"))[2]["data"]["file"] == "b.png"
    selain = lambda t: [b["teks"] for k, b in enumerate(si.pecah_blok(t)) if k != 2]
    assert selain(baru) == selain(TEKS)
    assert si.ubah_gambar(TEKS, 0, judul="X") == TEKS   # bukan gambar: tidak disentuh


def test_hapus_blok_tidak_menyentuh_yang_lain():
    baru = si.hapus_blok(TEKS, 2)
    assert baru.splitlines() == [b for b in TEKS.splitlines() if not b.startswith("[[GAMBAR")]
    assert jenis(si.hapus_blok(TEKS, 3)) == ["paragraf", "subjudul", "gambar", "rumus", "daftar", "paragraf"]


def test_nomor_blok_sama_dengan_rujukan_setelah_dipindah():
    import rujukan
    isi = "Lihat [[REF: #a]] dan [[REF: #b]].\n[[GAMBAR: a.png | A]]\nTengah\n[[GAMBAR: b.png | B]]"
    data = {"bab": [{"judul": "Satu", "subbab": [{"judul": "S", "isi": isi}]}]}
    assert si.nomor_blok(data, 0, 0) == {1: "Gambar 1.1", 3: "Gambar 1.2"}
    data["bab"][0]["subbab"][0]["isi"] = si.pindah_blok(si.pindah_blok(isi, 3, -1), 2, -1)   # b naik dua kali
    peta, _ = rujukan.peta_label(data)
    assert peta == {"b": "Gambar 1.1", "a": "Gambar 1.2"}
    assert si.nomor_blok(data, 0, 0) == {1: "Gambar 1.1", 2: "Gambar 1.2"}
    siap = rujukan.siapkan(data["bab"][0]["subbab"][0]["isi"], peta)
    assert siap.splitlines()[0] == "Lihat Gambar 1.2 dan Gambar 1.1."


def test_pemakaian_gambar():
    data = {"bab": [{"judul": "B", "subbab": [{"judul": "S", "isi": "[[GAMBAR: a.png | A]]"},
                                               {"judul": "T", "isi": "[[GAMBAR: a.png | A lagi]]"}]}],
            "lampiran": [{"judul": "L", "isi": "", "gambar": "c.png"}]}
    assert si.pemakaian_gambar(data) == {"a.png": ["1.1", "1.2"], "c.png": ["Lampiran 1"]}


def test_atur_susunan_pindah_ubah_hapus(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    i, j = next((i, j) for i in range(at.session_state["jml_bab"]) for j in range(at.session_state[f"bab{i}_n"])
                if "[[GAMBAR" in at.session_state[f"bab{i}_s{j}_isi"])
    kunci = f"bab{i}_s{j}_isi"
    awal = at.session_state[kunci]
    k = jenis(awal).index("gambar")
    at = at.button(key=f"as_{i}_{j}").click().run()
    at = at.button(key=f"naik_{i}_{j}_{k}").click().run()
    assert not at.exception
    assert jenis(at.session_state[kunci]).index("gambar") == k - 1
    assert sorted(at.session_state[kunci].splitlines()) == sorted(awal.splitlines())

    at = at.button(key=f"ubah_{i}_{j}_{k - 1}").click().run()
    n = at.session_state["_pn"]
    at.slider(key=f"pn_lebar{n}").set_value(8.0)
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert si.pecah_blok(at.session_state[kunci])[k - 1]["data"]["lebar"] == 8.0

    at = tombol(ke_tahap(at, "buat"), "Buat file Word").click().run()
    urut = urutan_dokumen(hasil_docx(at))
    sebelum = si.pecah_blok(at.session_state[kunci])[k]["teks"]     # blok yang tadinya di atas gambar
    assert urut.index("<gambar>") < next(n for n, t in enumerate(urut) if t.startswith(sebelum[:30]))

    at = ke_tahap(at, "isi")
    at = at.button(key=f"hapus_{i}_{j}_{k - 1}").click().run()
    assert "gambar" in jenis(at.session_state[kunci])            # klik pertama baru konfirmasi
    at = at.button(key=f"hapus_{i}_{j}_{k - 1}").click().run()
    assert "gambar" not in jenis(at.session_state[kunci])
    assert "grafik_contoh.png" in at.session_state["_gambar_simpan"]


def test_gambar_tanpa_file_tidak_error(aplikasi):
    at = aplikasi
    at.session_state["bab0_s0_isi"] = "Awal\n[[GAMBAR: hilang.png | Tanpa File]]"
    at = at.run()
    at = at.button(key="as_0_0").click().run()
    assert not at.exception
    at = at.button(key="unggah_0_0_1").click().run()
    n = at.session_state["_pn"]
    at.file_uploader(key=f"pn_file{n}").upload("apa-saja.png", png("green"), "image/png")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert at.session_state["_gambar_simpan"]["hilang.png"] == png("green")


# ---------------- Sub-subbab ----------------
def test_sisipkan_subjudul_awal_tengah_akhir_dan_dibersihkan():
    teks = "Satu\nDua"
    assert si.sisipkan_subjudul(teks, 0, "Awal").splitlines() == ["### Awal", "Satu", "Dua"]
    assert si.sisipkan_subjudul(teks, 1, "Tengah").splitlines() == ["Satu", "### Tengah", "Dua"]
    assert si.sisipkan_subjudul(teks, 2, "Akhir").splitlines() == ["Satu", "Dua", "### Akhir"]
    assert si.sisipkan_subjudul("", 0, "  ### Judul #1 \n baru ") == "### Judul 1 baru"


def test_ubah_dan_hapus_subjudul_tidak_menghapus_paragraf():
    teks = "### A\nIsi A\n### B\nIsi B"
    assert si.ubah_subjudul(teks, 2, "B Baru").splitlines() == ["### A", "Isi A", "### B Baru", "Isi B"]
    assert si.ubah_subjudul(teks, 1, "X") == teks
    assert si.hapus_blok(teks, 0).splitlines() == ["Isi A", "### B", "Isi B"]


def _nomor_subsub_word(data):
    from generator import buat_dokumen
    from docx import Document
    hasil = buat_dokumen(data, {})
    isi = hasil[0] if isinstance(hasil, tuple) else hasil
    isi = isi if isinstance(isi, bytes) else isi.getvalue()
    return [p.text for p in Document(io.BytesIO(isi)).paragraphs if p.style.name == "Heading 3"]


def test_nomor_subsubbab_mengikuti_urutan_baru(data_contoh):
    isi = "### Pertama\nIsi pertama\n### Kedua\nIsi kedua"
    data_contoh["bab"][1]["subbab"][0]["isi"] = isi
    data_contoh["bab"][1]["subbab"][1]["isi"] = ""
    assert si.nomor_blok(data_contoh, 1, 0) == {0: "2.1.1", 2: "2.1.2"}
    assert _nomor_subsub_word(data_contoh) == ["2.1.1 Pertama", "2.1.2 Kedua"]
    turun = si.pindah_blok(si.pindah_blok(isi, 0, 1), 1, 1)     # judul Pertama turun melewati dua blok
    assert turun.splitlines() == ["Isi pertama", "### Kedua", "### Pertama", "Isi kedua"]
    data_contoh["bab"][1]["subbab"][0]["isi"] = turun
    assert _nomor_subsub_word(data_contoh) == ["2.1.1 Kedua", "2.1.2 Pertama"]
    data_contoh["bab"][1]["subbab"][0]["isi"] = si.hapus_blok(turun, 1)
    assert _nomor_subsub_word(data_contoh) == ["2.1.1 Pertama"]


def test_tambah_subsubbab_lewat_tombol(aplikasi):
    at = aplikasi
    at.session_state["bab1_s0_isi"] = "Paragraf awal.\nParagraf akhir."
    at = at.run()
    at = at.button(key="ts_1_0").click().run()
    n = at.session_state["_pn"]
    assert any("Akan menjadi 2.1.1" in c.value for c in at.caption)
    at = at.button(key=f"pn_sisip{n}").click().run()          # judul kosong ditolak
    assert "###" not in at.session_state["bab1_s0_isi"]
    at.text_input(key=f"pn_judul{n}").set_value("Teori Dasar")
    at.selectbox(key=f"pn_letak{n}").set_value(1)
    at = at.run()
    at = at.button(key=f"pn_sisip{n}").click().run()
    assert not at.exception
    assert at.session_state["bab1_s0_isi"].splitlines() == ["Paragraf awal.", "### Teori Dasar", "Paragraf akhir."]

    at = at.button(key="as_1_0").click().run()
    at = at.button(key="turun_1_0_1").click().run()
    assert at.session_state["bab1_s0_isi"].splitlines() == ["Paragraf awal.", "Paragraf akhir.", "### Teori Dasar"]
    at = at.button(key="ubah_1_0_2").click().run()
    n = at.session_state["_pn"]
    at.text_input(key=f"pn_judul{n}").set_value("Teori Baru")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert at.session_state["bab1_s0_isi"].endswith("### Teori Baru")
    at = at.button(key="hapus_1_0_2").click().run()
    at = at.button(key="hapus_1_0_2").click().run()
    assert at.session_state["bab1_s0_isi"].split() == "Paragraf awal. Paragraf akhir.".split()
