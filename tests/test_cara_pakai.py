"""Tombol Cara Pakai di pojok kanan atas: menuju buku panduan, dan tidak mengganggu tombol tema."""
import pembaruan as pb
import pengaturan
from conftest import tombol


def tautan(at):
    return [t.proto for t in at.get("link_button")]


def test_tombol_cara_pakai_menuju_buku_panduan(aplikasi):
    cara = [t for t in tautan(aplikasi) if t.label == "Cara Pakai"]
    assert len(cara) == 1
    assert cara[0].url == pengaturan.LINK_PANDUAN
    assert pengaturan.LINK_PANDUAN.startswith("https://drive.google.com/")


def test_tanpa_link_tombolnya_tidak_ada(aplikasi, monkeypatch):
    monkeypatch.setattr(pengaturan, "LINK_PANDUAN", "")
    aplikasi.run()
    assert not aplikasi.exception
    assert not [t for t in tautan(aplikasi) if t.label == "Cara Pakai"]
    tombol(aplikasi, f"Yang baru (versi {pb.VERSI})").click().run()
    assert not any("Baca buku panduan" in m.value for m in aplikasi.markdown)
    assert aplikasi.button(key="ganti_tema").label == "Ganti ke mode gelap"


def test_tombol_tema_tetap_berfungsi(aplikasi):
    assert aplikasi.button(key="ganti_tema").label == "Ganti ke mode gelap"
    aplikasi.button(key="ganti_tema").click().run()
    assert not aplikasi.exception
    assert aplikasi.session_state["mode_gelap"] is True
    assert aplikasi.button(key="ganti_tema").label == "Ganti ke mode terang"
    assert [t for t in tautan(aplikasi) if t.label == "Cara Pakai"]


def test_jendela_yang_baru_memuat_link_panduan(aplikasi):
    tombol(aplikasi, f"Yang baru (versi {pb.VERSI})").click().run()
    assert any("Baca buku panduan" in m.value and pengaturan.LINK_PANDUAN in m.value for m in aplikasi.markdown)


def test_versi_1_12_tercatat():
    assert pb.VERSI == "1.12"
    assert pb.PEMBARUAN[0]["poin"] == ["Tombol Cara Pakai di pojok kanan atas membuka buku panduan penggunaan (PDF)."]
