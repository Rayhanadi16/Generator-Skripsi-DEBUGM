import pytest

import periksa_tulisan as pt
from conftest import ke_tahap, tombol


def _data(*isi, pustaka="", abstract="", judul="Judul"):
    return {"identitas": {"judul_id": judul}, "kata_pengantar": "", "intisari": "", "abstract": abstract,
            "daftar_pustaka": pustaka,
            "bab": [{"judul": "Pendahuluan", "subbab": [{"judul": f"Sub {n}", "isi": teks}
                                                         for n, teks in enumerate(isi, start=1)]}]}


def _kata(data, abaikan=()):
    return {t["kata"]: t["saran"] for t in pt.cari_tidak_baku(data, abaikan)}


def test_kata_dasar():
    assert _kata(_data("Data dianalisa untuk mengukur resiko dan efektifitas.")) == {
        "dianalisa": "dianalisis", "resiko": "risiko", "efektifitas": "efektivitas"}


@pytest.mark.parametrize("kata, saran", [
    ("menganalisa", "menganalisis"), ("resikonya", "risikonya"), ("mempraktekkan", "mempraktikkan"),
    ("perijinan", "perizinan"), ("menghimbau", "mengimbau"), ("kehandalan", "keandalan"),
    ("antrian", "antrean"), ("ketrampilan", "keterampilan"), ("berhutang", "berutang"),
    ("merubah", "mengubah"), ("dirubah", "diubah"), ("merubahnya", "mengubahnya"),
    ("mempengaruhi", "memengaruhi"), ("kerjasama", "kerja sama"), ("nampaknya", "tampaknya"),
])
def test_bentuk_berimbuhan(kata, saran):
    assert pt.saran_untuk(kata) == saran


@pytest.mark.parametrize("kata", [
    "rubah", "perubahan", "mengubah", "menampakkan", "trendi", "responden", "respons", "indeks", "kompleks",
    "konteks", "ditandatangani", "pertanggungjawaban", "elite", "analisis", "praktik", "memperhatikan", "risiko",
])
def test_kata_baku_tidak_ditandai(kata):
    assert pt.saran_untuk(kata) is None


@pytest.mark.parametrize("asli, hasil", [("analisa", "analisis"), ("Analisa", "Analisis"), ("ANALISA", "ANALISIS")])
def test_pola_kapital(asli, hasil):
    assert pt.ganti_di_teks(f"Hasil {asli} data.", "analisa", "analisis") == (f"Hasil {hasil} data.", 1)


def test_bagian_yang_dilewati():
    isi = ('Menurut penulisnya, "analisa itu penting" (Analisa Group, 2021). Istilah *analisa* dipakai di sini. '
           "[[TABEL: Hasil analisa | Analisa, 2020]]\nA | B\n[[/TABEL]]\nLihat [[REF: #analisa]].")
    assert _kata(_data(isi, pustaka="Analisa, B. (2020). Analisa resiko.", abstract="The analisa of resiko.")) == {}


def test_tebal_tetap_diperiksa():
    assert _kata(_data("Kata **analisa** ditebalkan.")) == {"analisa": "analisis"}


def test_judul_dan_lokasi():
    data = _data("Teks bersih.", "Ada resiko di sini.", judul="Analisa Resiko Usaha")
    temuan = {t["kata"]: t for t in pt.cari_tidak_baku(data)}
    assert temuan["resiko"]["jumlah"] == 2
    assert [(k, l) for k, l, _ in temuan["resiko"]["lokasi"]] == [("id_judul_id", "Judul TA"), ("bab0_s1_isi", "Bab I, 1.2")]
    assert "⟦resiko⟧" in temuan["resiko"]["lokasi"][1][2]


def test_abaikan():
    data = _data("Data dianalisa untuk mengukur resiko.")
    assert _kata(data, abaikan=["Resiko"]) == {"dianalisa": "dianalisis"}


def test_ganti_semua_di_beberapa_subbab():
    isian = {"jml_bab": 1, "bab0_n": 2, "id_judul_id": "Analisa Usaha", "kata_pengantar": "", "intisari": "",
             "bab0_judul": "Pendahuluan", "bab0_s0_judul": "Satu", "bab0_s1_judul": "Dua",
             "bab0_s0_isi": "Hasil analisa pertama. Menurut *analisa* lama.",
             "bab0_s1_isi": 'ANALISA kedua, "analisa" dalam kutipan.', "daftar_pustaka": "Analisa, B. (2020)."}
    assert pt.ganti_semua(isian, "analisa", "analisis") == 3
    assert isian["id_judul_id"] == "Analisis Usaha"
    assert isian["bab0_s0_isi"] == "Hasil analisis pertama. Menurut *analisa* lama."
    assert isian["bab0_s1_isi"] == 'ANALISIS kedua, "analisa" dalam kutipan.'
    assert isian["daftar_pustaka"] == "Analisa, B. (2020)."


def test_baris_ragu_belum_dipakai():
    peta, _ = pt.muat_kata_baku()
    assert "manager" not in peta and "amandemen" not in peta
    assert len(peta) >= 200


def test_daftar_kata_konsisten():
    peta, utuh = pt.muat_kata_baku()
    assert not [b for b in peta.values() if b.lower() in peta], "bentuk baku tidak boleh terdaftar sebagai tidak baku"
    assert "rubah" not in peta and utuh <= set(peta)


def test_data_contoh_tanpa_temuan_palsu(data_contoh):
    assert pt.cari_tidak_baku(data_contoh) == []


def test_tab_di_aplikasi_ganti_dan_abaikan(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    at.session_state["bab0_s1_isi"] = "Data dianalisa untuk mengukur resiko."
    at.session_state["bab1_s0_isi"] = "Resiko itu dianalisa lagi."
    at = ke_tahap(at, "periksa")
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Format halaman", "Preview", "Periksa tulisan"]
    assert any("2 kata tidak baku" in m.value for m in at.markdown)

    next(b for b in at.button if b.key == "ganti_dianalisa").click().run()
    assert at.session_state["bab0_s1_isi"] == "Data dianalisis untuk mengukur resiko."
    assert at.session_state["bab1_s0_isi"] == "Resiko itu dianalisis lagi."

    next(b for b in at.button if b.key == "abaikan_resiko").click().run()
    assert at.session_state["abaikan_kata"] == ["resiko"]
    assert not any(b.key == "ganti_resiko" for b in at.button)

    at = ke_tahap(at, "buat")                       # pengingat hilang karena satu-satunya temuan sudah diabaikan
    assert not any("kata tidak baku" in i.value for i in at.info)
    at = ke_tahap(at, "periksa")
    next(b for b in at.button if b.key == "kembalikan_resiko").click().run()
    assert at.session_state["abaikan_kata"] == []
    at = ke_tahap(at, "buat")
    assert any("Ada 1 kata tidak baku" in i.value for i in at.info)


def test_daftar_abaikan_ikut_dimuat_dan_file_lama_tetap_termuat(aplikasi, data_contoh):
    at = aplikasi
    # jalur pemulihan simpan otomatis: isian yang sudah punya daftar abaikan
    at.session_state["_sb_terima"] = {"isian": {**data_contoh, "abaikan_kata": ["resiko"]}, "gambar": {}, "logo": None}
    at.run()
    assert not at.exception and at.session_state["abaikan_kata"] == ["resiko"]
    # contoh_data.json belum punya kunci abaikan_kata, sama seperti file progres lama
    at = tombol(at, "Isi dengan data contoh").click().run()
    assert not at.exception and at.session_state["abaikan_kata"] == []


def test_baris_ringkas_di_preview(data_contoh):
    import preview
    data_contoh["bab"][0]["subbab"][1]["isi"] = "Ada resiko dan analisa."
    assert "Ada 2 kata tidak baku. Lihat tab Periksa tulisan." in preview.kerangka(data_contoh, {})[1]
    data_contoh["abaikan_kata"] = ["resiko"]
    assert "Ada 1 kata tidak baku. Lihat tab Periksa tulisan." in preview.kerangka(data_contoh, {})[1]
