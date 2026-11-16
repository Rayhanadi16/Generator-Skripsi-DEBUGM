import io

import docx

from conftest import ke_tahap, tombol


def _label(at, daftar):
    return [x.label for x in daftar]


def test_hanya_tab_tahap_aktif_yang_tampil(aplikasi):
    at = aplikasi
    assert [t.label for t in at.tabs] == ["Draft", "Identitas", "Bagian awal", "Bab"]
    assert [t.label for t in ke_tahap(at, "bahan").tabs] == ["Pustaka & lampiran", "Gambar & logo"]
    assert [t.label for t in ke_tahap(at, "periksa").tabs][:2] == ["Format halaman", "Preview"]
    at = ke_tahap(at, "buat")
    assert not at.exception and len(at.tabs) == 0
    assert any(b.label == "Buat file Word" for b in at.button)


def test_isian_tahap_1_sampai_ke_dokumen(aplikasi):
    at = aplikasi
    next(x for x in at.text_input if x.label == "Judul TA (Bahasa Indonesia)").set_value("Judul Uji Navigasi")
    next(x for x in at.text_input if x.label == "Nama lengkap").set_value("Penulis Uji")
    at.run()
    at = ke_tahap(at, "bahan")
    at = ke_tahap(at, "periksa")
    at = tombol(ke_tahap(at, "buat"), "Buat file Word").click().run()
    assert not at.exception
    hasil = at.session_state["_hasil"]
    dok = docx.Document(io.BytesIO(hasil if isinstance(hasil, bytes) else hasil.getvalue()))
    teks = "\n".join(p.text for p in dok.paragraphs)
    assert "JUDUL UJI NAVIGASI" in teks.upper() and "Penulis Uji" in teks


def test_pindah_bolak_balik_tidak_menghilangkan_isian(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    at.session_state["mg_atas"] = 3.5
    at.run()
    sebelum = {k: at.session_state[k] for k in ("id_judul_id", "bab0_s0_isi", "bab3_s1_isi", "lamp0_judul",
                                                "lamp1_isi", "daftar_pustaka", "intisari", "pg_ketua_nama")}
    assert all(sebelum.values())
    for kunci in ("buat", "periksa", "bahan", "buat", "isi", "periksa", "isi"):
        at = ke_tahap(at, kunci)
        assert not at.exception
    assert {k: at.session_state[k] for k in sebelum} == sebelum
    assert at.session_state["mg_atas"] == 3.5
    assert at.session_state["jml_bab"] == 5 and at.session_state["jml_lampiran"] == 2
    assert next(x for x in at.text_input if x.label == "Judul TA (Bahasa Indonesia)").value == sebelum["id_judul_id"]


def test_gambar_contoh_tetap_ada_setelah_pindah_tahap(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    for kunci in ("bahan", "periksa", "buat"):
        at = ke_tahap(at, kunci)
    assert "grafik_contoh.png" in at.session_state["_gambar_simpan"]
    at = tombol(at, "Buat file Word").click().run()
    assert not any("belum diupload" in w.value and "grafik_contoh" in w.value for w in at.warning)
