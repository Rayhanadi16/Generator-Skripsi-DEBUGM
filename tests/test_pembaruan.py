import pembaruan as pb
from conftest import tombol


def _versi(teks):
    return tuple(int(x) for x in teks.split("."))


def test_terurut_dari_yang_terbaru():
    versi = [_versi(e["versi"]) for e in pb.PEMBARUAN]
    assert versi == sorted(versi, reverse=True)
    tanggal = [e["tanggal"] for e in pb.PEMBARUAN]
    assert tanggal == sorted(tanggal, reverse=True)


def test_versi_sama_dengan_entri_teratas():
    assert pb.VERSI == pb.PEMBARUAN[0]["versi"]


def test_setiap_entri_punya_poin():
    for e in pb.PEMBARUAN:
        assert e["judul"].strip()
        assert e["poin"] and all(p.strip() for p in e["poin"])


def test_tanggal_teks():
    assert pb.tanggal_teks(pb.PEMBARUAN[-1]["tanggal"]) == "11 November 2026"


def _ada_tombol(at, label):
    return any(b.label == label for b in at.button)


def test_jendela_menunggu_cek_simpanan(aplikasi):
    # tanpa browser, status simpan otomatis tetap "cek", jadi jendela belum boleh dibuka
    assert aplikasi.session_state["_autosave_status"] == "cek"
    assert not _ada_tombol(aplikasi, "Oke, mulai")


def test_jendela_hanya_sekali_per_sesi(aplikasi):
    at = aplikasi
    at.session_state["_autosave_status"] = "aktif"
    at.run()
    assert _ada_tombol(at, "Oke, mulai")

    tombol(at, "Oke, mulai").click().run()
    assert at.session_state["_yang_baru"] == "tutup"
    assert not _ada_tombol(at, "Oke, mulai")

    tombol(at, "Isi dengan data contoh").click().run()   # rerun biasa tidak membuka jendela lagi
    assert not _ada_tombol(at, "Oke, mulai")

    tombol(at, f"Yang baru (versi {pb.VERSI})").click().run()   # tombol di sidebar membukanya kembali
    assert _ada_tombol(at, "Oke, mulai")
