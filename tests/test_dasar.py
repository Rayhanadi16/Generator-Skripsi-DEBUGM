from conftest import tombol


def test_aplikasi_terbuka_tanpa_exception(aplikasi):
    assert not aplikasi.exception


def test_data_contoh_menjadi_docx(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    assert not at.exception
    assert at.session_state["id_judul_id"]

    at = tombol(at, "Buat file Word").click().run()
    assert not at.exception
    hasil = at.session_state["_hasil"]
    isi = hasil if isinstance(hasil, bytes) else hasil.getvalue()
    assert isi[:2] == b"PK"   # .docx adalah arsip zip
