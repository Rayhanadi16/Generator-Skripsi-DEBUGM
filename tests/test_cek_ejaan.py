import pytest

import periksa_tulisan as pt
from conftest import ke_tahap, tombol


def _data(isi, **lain):
    return {"identitas": {"judul_id": "Judul", **lain.pop("identitas", {})}, "kata_pengantar": "", "intisari": "",
            "bab": [{"judul": "Pendahuluan", "subbab": [{"judul": "Sub", "isi": isi}]}], **lain}


def _typo(isi, **lain):
    return [t["kata"] for t in pt.cari_typo(_data(isi, **lain), lain.get("abaikan_kata", ()))]


def _asing(isi, **lain):
    return [t["kata"] for t in pt.cari_istilah_asing(_data(isi, **lain), lain.get("abaikan_kata", ()))]


def test_typo_sederhana_tertangkap_dengan_saran():
    assert _typo("Besarnya pengaruuh perusahan itu.") == ["pengaruuh", "perusahan"]
    assert pt.saran_ejaan("pengaruuh")[0] == "pengaruh"
    assert pt.saran_ejaan("perusahan")[0] == "perusahaan"
    assert pt.saran_ejaan("menunjukan")[0] == "menunjukkan"
    assert len(pt.saran_ejaan("penelitan")) <= 3 and "penelitian" in pt.saran_ejaan("penelitan")


@pytest.mark.parametrize("kata", ["mengunakan", "pengunaan", "menbuat", "perusahan", "penelitan", "menunjukan",
                                  "pengaruuh", "berbedaa", "hasilnyaa"])
def test_typo_umum_tidak_lolos(kata):
    assert not pt.dikenal_id(kata)


def test_kalimat_uji_dari_workflow():
    isi = "Hasil penelitan menunjukan bahwa return saham berpengaruh."
    assert _typo(isi) == ["penelitan", "menunjukan"]
    assert _asing(isi) == ["return"]


@pytest.mark.parametrize("kata", [
    "dikerjakannya", "memperhitungkan", "ketidakpastian", "keberhasilan", "pemberdayaan", "terencana", "menjorok",
    "pertanggungjawaban", "memengaruhi", "mempraktikkan", "heteroskedastisitas", "normalitas", "berkelanjutan",
    "digeneralisasi", "mengoptimalkan", "sub", "dikomunikasikan", "ditranskripsikan", "direkomendasikan",
    "datanya", "dicek", "lokapasar",
])
def test_kata_benar_tidak_ditandai(kata):
    assert pt.dikenal_id(kata)


def test_yang_dilewati():
    isi = ("Menurut Sugiyono (2019), data BPS dan OJK tentang ROA di Yogyakarta memakai x1 dan 2SLS. "
           'Kutipan "pengaruuh" dan (Ghozali, 2018) serta *purposive sampling* tidak dicek. '
           "Lihat https://contoh.test/pengaruuh atau surel@contoh.test. Kata sehari-hari dan data-datanya aman.")
    assert _typo(isi) == [] and _asing(isi) == []


def test_daftar_istilah_nama_dan_pustaka_dilewati():
    isi = "Teknik winsorizing dipakai oleh Wibisonoputra. Rayhanadi menulis tentang fintech dan Kusumawardhani."
    assert set(_typo(isi)) | set(_asing(isi)) >= {"winsorizing", "fintech"}
    lain = dict(istilah="winsorizing: pemangkasan nilai ekstrem\nfintech: teknologi finansial",
                daftar_pustaka="Kusumawardhani, A. (2020). Judul.", identitas={"nama": "Rayhanadi"})
    assert _typo(isi, **lain) == [] and _asing(isi, **lain) == []


def test_abaikan_berlaku_untuk_typo_dan_istilah_asing():
    isi = "Pengaruuh return dan leverage."
    assert _typo(isi, abaikan_kata=["pengaruuh"]) == []
    assert _asing(isi, abaikan_kata=["Return"]) == ["leverage"]


def test_kata_tidak_baku_tidak_dihitung_dua_kali():
    data = _data("Data dianalisa dan resiko dihitung.")
    assert pt.cari_typo(data) == [] and len(pt.cari_tidak_baku(data)) == 2


def test_jadikan_miring():
    isian = {"jml_bab": 1, "bab0_n": 1, "id_judul_id": "", "kata_pengantar": "", "intisari": "", "bab0_judul": "B",
             "bab0_s0_judul": "S", "bab0_s0_isi": 'Return saham dan return aset, bukan "return" dalam kutipan atau *return* lama.'}
    assert pt.jadikan_miring(isian, "return") == 2
    assert isian["bab0_s0_isi"] == '*Return* saham dan *return* aset, bukan "return" dalam kutipan atau *return* lama.'
    assert pt.cari_istilah_asing({"identitas": {}, "bab": [{"judul": "B", "subbab": [{"judul": "S", "isi": isian["bab0_s0_isi"]}]}]}) == []


def test_ringkasan_tiga_jenis():
    jumlah, kalimat = pt.ringkasan(_data("Data dianalisa. Pengaruuh return besar."))
    assert jumlah == {"tidak_baku": 1, "typo": 1, "asing": 1}
    assert kalimat == ("Ada 1 kata tidak baku, 1 kemungkinan typo, dan 1 istilah asing belum miring. "
                       "Lihat tab Periksa tulisan.")
    assert pt.ringkasan(_data("Semua kata di kalimat ini benar.")) == ({"tidak_baku": 0, "typo": 0, "asing": 0}, None)


def test_data_contoh_tanpa_temuan(data_contoh):
    hasil = pt.periksa_ejaan(data_contoh)
    assert hasil == {"typo": [], "asing": []}


def test_cepat_untuk_teks_panjang(data_contoh):
    import time
    data_contoh["bab"][0]["subbab"][0]["isi"] *= 40
    mulai = time.time()
    pt.periksa_ejaan(data_contoh)
    assert time.time() - mulai < 3


def test_tab_di_aplikasi(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    # data contoh memuat "Return" di daftar istilah, jadi dipakai istilah lain di sini
    at.session_state["bab0_s1_isi"] = "Hasil penelitan menunjukan bahwa leverage saham berpengaruh."
    at = ke_tahap(at, "periksa")
    assert not at.exception
    assert any("**0 kata tidak baku**, **2 kemungkinan typo**, dan **1 istilah asing belum miring**" in m.value
               for m in at.markdown)

    next(b for b in at.button if b.key == "typo_menunjukan_menunjukkan").click().run()
    assert at.session_state["bab0_s1_isi"] == "Hasil penelitan menunjukkan bahwa leverage saham berpengaruh."
    next(b for b in at.button if b.key == "miring_leverage").click().run()
    assert at.session_state["bab0_s1_isi"] == "Hasil penelitan menunjukkan bahwa *leverage* saham berpengaruh."
    next(b for b in at.button if b.key == "abaikan_penelitan").click().run()
    assert not at.exception and at.session_state["abaikan_kata"] == ["penelitan"]
    assert any("Tidak ada kata tidak baku" in s.value for s in at.success)

    at = ke_tahap(at, "buat")
    assert not any("Periksa tulisan" in i.value for i in at.info)
