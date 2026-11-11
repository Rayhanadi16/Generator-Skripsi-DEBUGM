"""
Generator Laporan Tugas Akhir — tampilan aplikasi (Streamlit)
Jalankan:  streamlit run app.py
"""

import json
from pathlib import Path
from datetime import date

import streamlit as st

from generator import (FORMAT_DEB_SV_UGM, MARGIN_MAX_CM, MARGIN_MIN_CM, SISI_MARGIN, STRUKTUR_BAB_BAWAAN, buat_dokumen,
                       format_dari, hitung_kata, jarak_footer_cm, margin_bawaan, urutkan_kata_kunci)
from importer import daftar_tujuan, lacak_draft, susun_data, warna
from preview import halaman_html, kerangka
import autosave as asv
import pustaka as pst
import tampilan as tp
from pengaturan import MODE_WEB

if MODE_WEB:
    class _TanpaAutosave:
        """Versi web: tidak ada isian pengunjung yang ditulis ke disk server."""
        @staticmethod
        def info(): return None
        @staticmethod
        def cadangkan_sekarang(): return None
        @staticmethod
        def daftar_riwayat(): return []
    asv = _TanpaAutosave()

st.set_page_config(page_title="Generator Laporan TA", layout="wide")
st.markdown(tp.CSS, unsafe_allow_html=True)

ss = st.session_state

FIELD_IDENTITAS = ["judul_id", "judul_en", "nama", "nim", "prodi", "tahun", "pembimbing",
                   "tahun_terdaftar", "fakultas", "tempat_ttd", "tanggal_ttd"]
FIELD_PENGESAHAN = ["tanggal_ujian", "ketua_nama", "ketua_nip", "pembimbing_nip", "anggota_nama",
                    "anggota_nip", "mengetahui_jabatan", "mengetahui_nama", "mengetahui_nip"]
FIELD_TEKS = ["kata_pengantar", "intisari", "kata_kunci", "abstract", "keywords", "istilah", "daftar_pustaka"]


# ---------------------------------------------------------------------------
# State: semua isian disimpan di session_state dengan kunci datar
# ---------------------------------------------------------------------------
def isi_default():
    if ss.get("_siap"):
        return
    for k in FIELD_IDENTITAS:
        ss[f"id_{k}"] = ""
    ss["id_tahun"] = str(date.today().year)
    ss["id_fakultas"] = "Sekolah Vokasi"
    ss["id_tempat_ttd"] = "Yogyakarta"
    for k in FIELD_PENGESAHAN:
        ss[f"pg_{k}"] = ""
    for k in FIELD_TEKS:
        ss[k] = ""
    ss["jml_bab"] = len(STRUKTUR_BAB_BAWAAN)
    for i, b in enumerate(STRUKTUR_BAB_BAWAAN):
        ss[f"bab{i}_judul"] = b["judul"]
        ss[f"bab{i}_n"] = len(b["subbab"])
        for j, s in enumerate(b["subbab"]):
            ss[f"bab{i}_s{j}_judul"] = s
            ss[f"bab{i}_s{j}_isi"] = ""
    ss["jml_lampiran"] = 0
    atur_margin(margin_bawaan())
    isi_ref(pst.KOSONG)
    ss["rf_doi"] = ""
    ss["_siap"] = True


def atur_margin(nilai):
    for s in SISI_MARGIN:
        ss[f"mg_{s}"] = float(nilai[s])


def margin_sekarang():
    bawaan = margin_bawaan()
    return {s: float(ss.get(f"mg_{s}", bawaan[s])) for s in SISI_MARGIN}


def cb_margin_panduan():
    atur_margin(margin_bawaan())
    ss["_pesan"] = ("success", "Margin dikembalikan ke ukuran panduan.")


def kumpulkan_data():
    """Ubah isian form menjadi dict yang dibaca generator.py."""
    data = {
        "identitas": {k: ss.get(f"id_{k}", "") for k in FIELD_IDENTITAS},
        "pengesahan": {k: ss.get(f"pg_{k}", "") for k in FIELD_PENGESAHAN},
        "bab": [],
        "lampiran": [],
    }
    data["format"] = {f"margin_{s}_cm": v for s, v in margin_sekarang().items()}
    for k in FIELD_TEKS:
        data[k] = ss.get(k, "")
    for i in range(ss["jml_bab"]):
        bab = {"judul": ss.get(f"bab{i}_judul", ""), "subbab": []}
        for j in range(ss.get(f"bab{i}_n", 0)):
            bab["subbab"].append({"judul": ss.get(f"bab{i}_s{j}_judul", ""),
                                  "isi": ss.get(f"bab{i}_s{j}_isi", "")})
        data["bab"].append(bab)
    for k in range(ss["jml_lampiran"]):
        data["lampiran"].append({"judul": ss.get(f"lamp{k}_judul", ""),
                                 "isi": ss.get(f"lamp{k}_isi", ""),
                                 "gambar": ss.get(f"lamp{k}_gambar", "") or ""})
    return data


def muat_data(data):
    """Kebalikan kumpulkan_data(): isi form dari file progres (.json)."""
    for k in FIELD_IDENTITAS:
        ss[f"id_{k}"] = str(data.get("identitas", {}).get(k, "") or "")
    for k in FIELD_PENGESAHAN:
        ss[f"pg_{k}"] = str(data.get("pengesahan", {}).get(k, "") or "")
    for k in FIELD_TEKS:
        ss[k] = data.get(k, "") or ""
    fmt = format_dari(data)   # file progres lama tanpa "format" -> margin panduan
    atur_margin({s: fmt[f"margin_{s}_cm"] for s in SISI_MARGIN})
    babs = data.get("bab", [])
    ss["jml_bab"] = len(babs)
    for i, b in enumerate(babs):
        ss[f"bab{i}_judul"] = b.get("judul", "")
        subs = b.get("subbab", [])
        ss[f"bab{i}_n"] = len(subs)
        for j, s in enumerate(subs):
            ss[f"bab{i}_s{j}_judul"] = s.get("judul", "")
            ss[f"bab{i}_s{j}_isi"] = s.get("isi", "")
    lamps = data.get("lampiran", [])
    ss["jml_lampiran"] = len(lamps)
    for k, l in enumerate(lamps):
        ss[f"lamp{k}_judul"] = l.get("judul", "")
        ss[f"lamp{k}_isi"] = l.get("isi", "")
        ss[f"lamp{k}_gambar"] = l.get("gambar", "")


# ----- bantuan daftar pustaka (isian sementara, tidak ikut file progres) -----
FIELD_REF = ["jenis", "penulis", "lembaga", "tahun", "judul", "wadah", "volume", "nomor", "halaman", "tautan"]


def isi_ref(isian):
    for k in FIELD_REF:
        ss[f"rf_{k}"] = isian.get(k, pst.KOSONG[k])


def ref_sekarang():
    return {k: ss.get(f"rf_{k}", pst.KOSONG[k]) for k in FIELD_REF}


def _ambil_ref(doi, judul_cadangan=""):
    try:
        isi_ref(pst.ambil_crossref(doi))
        ss["_pesan"] = ("success", "Rincian referensi terisi. Periksa dulu sebelum ditambahkan.")
    except pst.GagalAmbil as e:
        isi_ref({**pst.KOSONG, "judul": judul_cadangan, "tautan": f"https://doi.org/{doi}"})
        ss["_pesan"] = ("warning", str(e))


def cb_baca_pdf_ref():
    berkas = ss.get("upload_ref_pdf")
    if berkas is None:
        ss["_pesan"] = ("warning", "Pilih file PDF jurnalnya dulu.")
        return
    try:
        doi, judul = pst.cari_doi(berkas.getvalue())
    except pst.GagalAmbil as e:
        ss["_pesan"] = ("error", str(e))
        return
    if doi:
        _ambil_ref(doi, judul)
    else:
        isi_ref({**pst.KOSONG, "judul": judul})
        ss["_pesan"] = ("warning", "DOI tidak ditemukan di PDF ini. Tempel DOI-nya atau isi rinciannya sendiri.")


def cb_cari_doi_ref():
    doi = pst.rapikan_doi(ss.get("rf_doi", ""))
    if not doi:
        ss["_pesan"] = ("warning", "DOI tidak dikenali. Contoh: 10.1257/jel.52.1.5")
        return
    _ambil_ref(doi)


def cb_tambah_ref():
    baris = pst.format_apa(ref_sekarang())
    if not ss.get("rf_judul", "").strip():
        ss["_pesan"] = ("warning", "Isi judulnya dulu.")
        return
    lama = [b.strip() for b in ss.get("daftar_pustaka", "").splitlines() if b.strip()]
    if baris in lama:
        ss["_pesan"] = ("warning", "Referensi ini sudah ada di daftar pustaka.")
        return
    ss["daftar_pustaka"] = "\n".join(lama + [baris])
    isi_ref(pst.KOSONG)
    ss["rf_doi"] = ""
    ss["_pesan"] = ("success", "Referensi ditambahkan ke daftar pustaka.")


def cb_kosongkan_ref():
    isi_ref(pst.KOSONG)
    ss["rf_doi"] = ""


def cb_muat_progres():
    berkas = ss.get("upload_progres")
    if berkas is None:
        ss["_pesan"] = ("warning", "Pilih file progres (.json) dulu.")
        return
    try:
        data = json.loads(berkas.getvalue().decode("utf-8"))
        asv.cadangkan_sekarang()
        muat_data(data)
        ss["_pesan"] = ("success", "Progres berhasil dimuat.")
    except Exception as e:
        ss["_pesan"] = ("error", f"File tidak bisa dibaca: {e}")


def cb_muat_contoh():
    asv.cadangkan_sekarang()
    folder = Path(__file__).resolve().parent
    with open(folder / "contoh_data.json", encoding="utf-8") as fh:
        muat_data(json.load(fh))
    grafik = folder / "grafik_contoh.png"
    if grafik.exists():   # gambar contoh ikut dimuat supaya tidak perlu diupload sendiri
        ss["_gambar_simpan"] = {**ss.get("_gambar_simpan", {}), grafik.name: grafik.read_bytes()}
    ss["_pesan"] = ("success", "Data contoh dimuat. Lihat hasilnya di tab Preview.")


def cb_tambah_sub(i):
    n = ss[f"bab{i}_n"]
    ss[f"bab{i}_s{n}_judul"] = ""
    ss[f"bab{i}_s{n}_isi"] = ""
    ss[f"bab{i}_n"] = n + 1


def cb_hapus_sub(i):
    if ss[f"bab{i}_n"] > 0:
        ss[f"bab{i}_n"] -= 1


def cb_tambah_bab():
    i = ss["jml_bab"]
    ss[f"bab{i}_judul"] = ""
    ss[f"bab{i}_n"] = 1
    ss[f"bab{i}_s0_judul"] = ""
    ss[f"bab{i}_s0_isi"] = ""
    ss["jml_bab"] = i + 1


def cb_hapus_bab():
    if ss["jml_bab"] > 1:
        ss["jml_bab"] -= 1


def cb_tambah_lampiran():
    k = ss["jml_lampiran"]
    ss[f"lamp{k}_judul"] = ""
    ss[f"lamp{k}_isi"] = ""
    ss[f"lamp{k}_gambar"] = ""
    ss["jml_lampiran"] = k + 1


def cb_hapus_lampiran():
    if ss["jml_lampiran"] > 0:
        ss["jml_lampiran"] -= 1


def cb_lacak_draft():
    berkas = ss.get("upload_draft")
    if berkas is None:
        ss["_pesan"] = ("warning", "Pilih file draft (.docx) dulu.")
        return
    try:
        ss["_draft"] = lacak_draft(berkas.getvalue())
    except Exception as e:
        ss["_pesan"] = ("error", f"Draft tidak bisa dibaca: {e}. Pastikan formatnya .docx.")
        return
    ss["_koreksi"] = {}
    ss["_draft_nonce"] = ss.get("_draft_nonce", 0) + 1


def cb_simpan_koreksi(id_blok, key):
    ss["_koreksi"][id_blok] = ss[key]


def cb_terapkan_draft():
    hasil = ss.get("_draft")
    if not hasil:
        return
    data, gambar = susun_data(hasil, ss.get("_koreksi", {}))
    sekarang = kumpulkan_data()
    data["identitas"] = sekarang["identitas"]
    data["pengesahan"] = sekarang["pengesahan"]
    data["format"] = sekarang["format"]      # margin yang sudah diatur tidak ikut tertimpa
    data["istilah"] = sekarang.get("istilah", "")
    for k in ("kata_pengantar", "intisari", "kata_kunci", "abstract", "keywords", "daftar_pustaka"):
        if not data.get(k):          # jangan hapus isian lama bila draft tidak memuatnya
            data[k] = sekarang.get(k, "")
    asv.cadangkan_sekarang()
    muat_data(data)
    ss["_gambar_draft"] = gambar
    ss["_pesan"] = ("success", "Isi draft sudah dimasukkan ke form. Cek tab Bab, lalu buat file Word.")


def cb_lanjutkan_autosave():
    try:
        data, gambar, logo = asv.muat()
        muat_data(data)
        ss["_gambar_simpan"] = gambar
        ss["_logo_simpan"] = logo
        ss["_pesan"] = ("success", "Pekerjaan terakhir berhasil dipulihkan.")
    except Exception as e:
        ss["_pesan"] = ("error", f"Autosave tidak bisa dibaca: {e}")
    ss["_autosave_status"] = "aktif"


def cb_mulai_baru():
    asv.cadangkan_sekarang()   # pekerjaan lama tetap aman di Riwayat versi
    ss["_autosave_status"] = "aktif"
    ss["_pesan"] = ("success", "Mulai dari awal. Pekerjaan sebelumnya tetap tersimpan di Riwayat versi.")


def cb_pulihkan_riwayat():
    pilihan = ss.get("pilih_riwayat")
    if not pilihan:
        return
    try:
        data = asv.muat_riwayat(pilihan)
        asv.cadangkan_sekarang()
        muat_data(data)
        ss["_gambar_simpan"] = asv.muat_gambar()
        ss["_pesan"] = ("success", "Versi lama berhasil dipulihkan. Versi sebelum dipulihkan juga disimpan di riwayat.")
    except Exception as e:
        ss["_pesan"] = ("error", f"Versi ini tidak bisa dibaca: {e}")


def kumpulkan_gambar():
    gambar = dict(ss.get("_gambar_simpan", {}))
    gambar.update(ss.get("_gambar_draft", {}))
    gambar.update({g.name: g.getvalue() for g in (ss.get("upload_gambar") or [])})
    return gambar


def ambil_logo():
    if ss.get("upload_logo"):
        return ss["upload_logo"].getvalue()
    return ss.get("_logo_simpan")


isi_default()

if "_autosave_status" not in ss:
    info_as = asv.info()
    ss["_autosave_status"] = "tanya" if (info_as and not info_as["kosong"]) else "aktif"
    ss["_autosave_info"] = info_as

MARGIN_PANDUAN = margin_bawaan()
margin = margin_sekarang()
margin_beda = any(abs(margin[s] - MARGIN_PANDUAN[s]) > 1e-9 for s in SISI_MARGIN)

# ---------------------------------------------------------------------------
# Sisi kiri: simpan / muat progres
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Progres")
    st.caption("Simpan isianmu sebagai file .json supaya bisa dilanjutkan lain waktu atau di komputer lain.")
    st.download_button("Simpan progres (.json)",
                       data=json.dumps(kumpulkan_data(), ensure_ascii=False, indent=2),
                       file_name="progres_ta.json", mime="application/json", use_container_width=True)
    st.file_uploader("Muat progres", type=["json"], key="upload_progres")
    st.button("Muat file progres", on_click=cb_muat_progres, use_container_width=True)
    if MODE_WEB:
        st.divider()
        st.subheader("Isianmu tidak disimpan di server")
        st.markdown('<div class="catatan-sisi">Semua isian hanya ada di tab browser ini dan hilang kalau tab ditutup '
                    'atau lama tidak dipakai. <b>Klik Simpan progres (.json) secara berkala</b>, lalu muat lagi '
                    'file itu saat mau melanjutkan.</div>', unsafe_allow_html=True)
        st.caption("Teks di kotak isian baru tercatat setelah kamu klik di luar kotak atau menekan Ctrl/Cmd + Enter.")
    else:
        st.divider()
        st.subheader("Simpan otomatis")
        st.toggle("Aktif", value=True, key="autosave_on")
        if ss["_autosave_status"] == "tanya":
            st.caption("Menunggu pilihanmu: lanjutkan pekerjaan terakhir atau mulai dari awal.")
        elif not ss.get("autosave_on", True):
            st.caption("Simpan otomatis mati. Simpan progres secara manual sebelum menutup aplikasi.")
        elif ss.get("_autosave_waktu"):
            st.caption(f"Tersimpan pukul {ss['_autosave_waktu']:%H:%M:%S}")
        else:
            st.caption("Isian tersimpan setiap ada perubahan.")
        st.caption("Teks di kotak isian baru tersimpan setelah kamu klik di luar kotak atau menekan Cmd + Enter.")
        riwayat = asv.daftar_riwayat()
        with st.expander(f"Riwayat versi ({len(riwayat)})"):
            if riwayat:
                st.selectbox("Pilih versi", [n for n, _ in riwayat], format_func=dict(riwayat).get, key="pilih_riwayat")
                st.button("Pulihkan versi ini", on_click=cb_pulihkan_riwayat, use_container_width=True)
                st.caption("Cadangan dibuat tiap 5 menit dan sebelum isian ditimpa. Disimpan 30 versi terakhir.")
            else:
                st.caption("Belum ada riwayat.")
    st.divider()
    st.button("Isi dengan data contoh", on_click=cb_muat_contoh, use_container_width=True)
    st.caption("Untuk mencoba hasilnya tanpa mengetik. "
               + ("Isian yang sedang kamu kerjakan akan tertimpa, jadi simpan progres dulu."
                  if MODE_WEB else "Isianmu sekarang dicadangkan dulu ke riwayat."))
    if MODE_WEB:
        with st.expander("Tentang data kamu"):
            st.markdown(tp.TENTANG_DATA)
    st.divider()
    st.markdown(f'<div class="catatan-sisi">Dibuat oleh <b>{tp.PEMBUAT}</b></div>', unsafe_allow_html=True)

st.markdown(tp.kop(margin, MARGIN_PANDUAN, FORMAT_DEB_SV_UGM["nama"]) + tp.watermark(), unsafe_allow_html=True)

if ss.get("_pesan"):   # pakai toast agar tata letak (dan tab yang sedang dibuka) tidak bergeser
    jenis, teks = ss.pop("_pesan")
    st.toast(teks, icon={"success": ":material/check_circle:", "warning": ":material/warning:",
                         "error": ":material/error:"}.get(jenis, ":material/info:"))

if ss["_autosave_status"] == "tanya":
    inf = ss.get("_autosave_info") or {}
    with st.container(border=True):
        st.markdown(f"**Ada pekerjaan yang tersimpan otomatis** pada {inf.get('waktu'):%d %b %Y, %H:%M}"
                    + (f", berjudul “{inf['judul']}”" if inf.get("judul") else "")
                    + f", dengan {inf.get('kata_bab', 0)} kata di bab. Mau dilanjutkan?")
        k1, k2, _ = st.columns([1, 1, 3])
        k1.button("Lanjutkan", type="primary", on_click=cb_lanjutkan_autosave, use_container_width=True)
        k2.button("Mulai dari awal", on_click=cb_mulai_baru, use_container_width=True)

NAMA_TAB = ["Draft", "Identitas", "Bagian awal", "Bab", "Pustaka & lampiran", "Gambar & logo",
            "Format halaman", "Preview", "Buat file Word"]
try:   # Streamlit baru: ingat tab yang sedang dibuka saat halaman dimuat ulang
    (tab_draft, tab_id, tab_awal, tab_bab, tab_akhir, tab_gbr,
     tab_fmt, tab_prev, tab_gen) = st.tabs(NAMA_TAB, key="tab_utama")
except TypeError:
    tab_draft, tab_id, tab_awal, tab_bab, tab_akhir, tab_gbr, tab_fmt, tab_prev, tab_gen = st.tabs(NAMA_TAB)

# ---------------------------------------------------------------------------
with tab_draft:
    st.subheader("Mulai dari draft Word")
    st.caption("Sudah punya draft? Upload di sini. Setiap paragraf dibaca dan ditebak masuk ke bagian mana, "
               "lalu kamu cek hasilnya sebelum dimasukkan ke form. Belum punya draft? Lewati tab ini dan "
               "mulai dari Identitas. Draft dari Google Docs: File, Download, Microsoft Word (.docx).")
    st.file_uploader("Draft (.docx)", type=["docx"], key="upload_draft")
    st.button("Baca draft", on_click=cb_lacak_draft, type="primary")

    hasil = ss.get("_draft")
    if hasil:
        blok = hasil["blok"]
        hitung = {"hijau": 0, "kuning": 0, "merah": 0}
        for b in blok:
            b["_warna"] = warna(b) if b["id"] not in ss["_koreksi"] else "hijau"
            hitung[b["_warna"]] += 1
        st.markdown(tp.rekap_draft(hitung), unsafe_allow_html=True)

        if hasil["catatan"]:
            st.info("**Catatan dibanding panduan**\n" + "\n".join(f"- {c}" for c in hasil["catatan"]))

        with st.expander("Struktur yang terbaca dari draft"):
            romawi = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
            for i, bab in enumerate(hasil["struktur"]):
                st.markdown(f"**BAB {romawi[i] if i < 10 else i + 1} {bab['judul'].upper()}**")
                st.markdown("\n".join(f"- {i + 1}.{j + 1} {s}" for j, s in enumerate(bab["subbab"])) or "_(belum ada subbab)_")
            if hasil["lampiran"]:
                st.markdown("**Lampiran:** " + "; ".join(hasil["lampiran"]))
            st.caption("Judul bab dan subbab bisa diubah nanti di tab Bab setelah diterapkan.")

        opsi = daftar_tujuan(hasil)
        kunci_opsi = [k for k, _ in opsi]
        label_opsi = dict(opsi)
        tampil = st.radio("Tampilkan", ["Yang perlu dicek", "Semua isi"], horizontal=True)
        st.caption("Ganti pilihan di kanan bila tebakannya salah. Judul bab/subbab, judul tabel/gambar, dan baris "
                   "daftar isi tidak ditampilkan karena sudah dipakai sebagai struktur.")
        nonce = ss["_draft_nonce"]
        ditampilkan = 0
        for b in blok:
            if b.get("peran") in ("judul", "caption"):
                continue
            if tampil.startswith("Yang perlu") and b["_warna"] == "hijau":
                continue
            ditampilkan += 1
            with st.container(border=True):
                k1, k2 = st.columns([3, 2])
                with k1:
                    if b["jenis"] == "gambar":
                        st.image(hasil["gambar"][b["file"]], width=160)
                        st.caption(f"Gambar: {b.get('judul') or '(tanpa judul)'}")
                    elif b["jenis"] == "tabel":
                        st.markdown(f"**Tabel:** {b.get('judul') or '(tanpa judul)'}")
                        st.caption(" | ".join(b["baris"][0]))
                    else:
                        teks = b["teks"]
                        st.markdown(teks if len(teks) <= 280 else teks[:280] + "…")
                    st.markdown(tp.jejak_blok(b["_warna"], b.get("yakin", 0), b.get("alasan", "")),
                                unsafe_allow_html=True)
                with k2:
                    key = f"blk{nonce}_{b['id']}"
                    nilai = ss["_koreksi"].get(b["id"], b.get("tujuan", "belum"))
                    st.selectbox("Masukkan ke", kunci_opsi, index=kunci_opsi.index(nilai) if nilai in kunci_opsi else 0,
                                 format_func=lambda k: label_opsi[k], key=key, label_visibility="collapsed",
                                 on_change=cb_simpan_koreksi, args=(b["id"], key))
        if not ditampilkan:
            st.success("Tidak ada yang perlu dicek. Pilih “Semua isi” untuk melihat seluruhnya.")

        sisa_merah = sum(1 for b in blok if ss["_koreksi"].get(b["id"], b.get("tujuan")) == "belum")
        if sisa_merah:
            st.warning(f"{sisa_merah} bagian masih belum ditempatkan dan akan dilewati.")
        st.button("Masukkan ke form", on_click=cb_terapkan_draft, type="primary")
        st.caption("Isian di tab Identitas dan margin yang sudah kamu atur tidak ditimpa. "
                   "Setelah dimasukkan, cek penempatannya di tab Preview.")

# ---------------------------------------------------------------------------
with tab_id:
    st.subheader("Halaman sampul")
    st.text_input("Judul TA (Bahasa Indonesia)", key="id_judul_id")
    st.text_input("Judul TA (Bahasa Inggris)", key="id_judul_en")
    c1, c2, c3 = st.columns(3)
    c1.text_input("Nama lengkap", key="id_nama")
    c2.text_input("NIM", key="id_nim")
    c3.text_input("Tahun penyelesaian", key="id_tahun")
    c1, c2 = st.columns(2)
    c1.text_input("Program studi", key="id_prodi", placeholder="mis. Sarjana Terapan Perbankan")
    c2.text_input("Dosen pembimbing (gelar lengkap)", key="id_pembimbing")

    st.subheader("Pernyataan bebas plagiasi")
    c1, c2, c3, c4 = st.columns(4)
    c1.text_input("Tahun terdaftar", key="id_tahun_terdaftar")
    c2.text_input("Fakultas/Sekolah", key="id_fakultas")
    c3.text_input("Tempat tanda tangan", key="id_tempat_ttd")
    c4.text_input("Tanggal tanda tangan", key="id_tanggal_ttd", placeholder="mis. 7 November 2026")

    st.subheader("Halaman pengesahan")
    st.text_input("Tanggal ujian", key="pg_tanggal_ujian", placeholder="mis. 20 November 2026")
    c1, c2 = st.columns(2)
    c1.text_input("Penguji I / Ketua Penguji", key="pg_ketua_nama")
    c2.text_input("NIP/NIKA Penguji I", key="pg_ketua_nip")
    c1, c2 = st.columns(2)
    c1.text_input("Penguji II / Sekretaris Penguji / Dosen Pembimbing", value=ss.get("id_pembimbing", ""), disabled=True,
                  placeholder="Isi Dosen pembimbing di Halaman sampul",
                  help="Penguji II adalah dosen pembimbing. Namanya diambil dari isian Dosen pembimbing di Halaman sampul.")
    c2.text_input("NIP/NIKA Penguji II", key="pg_pembimbing_nip")
    c1, c2 = st.columns(2)
    c1.text_input("Penguji III / Anggota Penguji", key="pg_anggota_nama")
    c2.text_input("NIP/NIKA Penguji III", key="pg_anggota_nip")
    st.caption("Nama Penguji II mengikuti isian Dosen pembimbing di Halaman sampul, jadi cukup diubah di sana.")
    st.text_input("Jabatan yang mengetahui", key="pg_mengetahui_jabatan",
                  placeholder="Kosongkan untuk “Ketua Program Studi <prodi>”")
    st.caption("Isi “Ketua Departemen Ekonomika dan Bisnis” bila pembimbingmu adalah Ketua Program Studi.")
    c1, c2 = st.columns(2)
    c1.text_input("Nama yang mengetahui", key="pg_mengetahui_nama")
    c2.text_input("NIP/NIKA yang mengetahui", key="pg_mengetahui_nip")

# ---------------------------------------------------------------------------
with tab_awal:
    st.subheader("Kata pengantar")
    st.text_area("Kata pengantar", key="kata_pengantar", height=200, label_visibility="collapsed",
                 placeholder="Satu baris = satu paragraf.")
    st.subheader("Intisari dan abstract")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.text_area("Intisari (Bahasa Indonesia, maks. 250 kata)", key="intisari", height=240)
        n = hitung_kata(ss["intisari"])
        (st.error if n > 250 else st.caption)(f"{n} dari 250 kata" + (". Kurangi supaya sesuai panduan." if n > 250 else ""))
        st.text_input("Kata kunci (pisahkan dengan koma)", key="kata_kunci")
        if ss["kata_kunci"]:
            st.caption(f"Diurutkan abjad: {urutkan_kata_kunci(ss['kata_kunci'])}")
    with c2:
        st.text_area("Abstract (Bahasa Inggris, maks. 250 kata)", key="abstract", height=240)
        n = hitung_kata(ss["abstract"])
        (st.error if n > 250 else st.caption)(f"{n} dari 250 kata" + (". Kurangi supaya sesuai panduan." if n > 250 else ""))
        st.text_input("Keywords (pisahkan dengan koma)", key="keywords")
        if ss["keywords"]:
            st.caption(f"Diurutkan abjad: {urutkan_kata_kunci(ss['keywords'])}")
    st.subheader("Daftar istilah")
    st.text_area("Daftar istilah (opsional)", key="istilah", height=120, label_visibility="collapsed",
                 placeholder="istilah: arti")
    st.caption("Opsional. Satu istilah per baris dengan format `istilah: arti`. Diurutkan abjad otomatis.")

# ---------------------------------------------------------------------------
with tab_bab:
    with st.expander("Cara menulis isi dan penanda khusus", expanded=False):
        st.markdown("""
- **Satu baris = satu paragraf.** Paragraf pertama setelah judul otomatis rata kiri, berikutnya menjorok 1,25 cm.
- `### Judul` untuk sub-subbab (bernomor otomatis, mis. 1.1.1)
- `1. teks`, `a. teks`, `(1) teks` untuk perincian tingkat 1, 2, dan 3
- `*kata*` untuk huruf *miring* (istilah asing), `**kata**` untuk huruf **tebal**
- Gambar (upload dulu di tab Gambar & logo): `[[GAMBAR: nama_file.png | Judul Gambar | Sumber | lebar_cm]]`
- Tabel (baris pertama = header, kolom dipisah `|`):
```
[[TABEL: Judul Tabel | Sumber]]
Tahun | Jumlah
2024 | 150
[[/TABEL]]
```
- Rumus: `[[RUMUS: Y = a + bX]]`, bernomor (1), (2), dan seterusnya di kanan

Nomor tabel dan gambar (Tabel 3.1., Gambar 4.2.) dihitung otomatis per bab. Sumber boleh dikosongkan bila hasil olahan sendiri.
""")
    for i in range(ss["jml_bab"]):
        romawi = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i] if i < 10 else str(i + 1)
        with st.expander(f"BAB {romawi}  {ss.get(f'bab{i}_judul', '').upper()}", expanded=(i == 0)):
            st.text_input("Judul bab", key=f"bab{i}_judul")
            for j in range(ss[f"bab{i}_n"]):
                st.text_input(f"Subbab {i + 1}.{j + 1}", key=f"bab{i}_s{j}_judul", placeholder="Judul subbab")
                st.text_area("Isi", key=f"bab{i}_s{j}_isi", height=180, label_visibility="collapsed",
                             placeholder="Tulis atau tempel isi subbab di sini")
            c1, c2, _ = st.columns([1, 1.4, 3])
            c1.button("Tambah subbab", key=f"tambah_sub{i}", on_click=cb_tambah_sub, args=(i,))
            c2.button("Hapus subbab terakhir", key=f"hapus_sub{i}", on_click=cb_hapus_sub, args=(i,))
    c1, c2, _ = st.columns([1, 1.4, 3.4])
    c1.button("Tambah bab", on_click=cb_tambah_bab)
    c2.button("Hapus bab terakhir", on_click=cb_hapus_bab)

# ---------------------------------------------------------------------------
with tab_gbr:
    st.subheader("Logo UGM untuk sampul")
    st.caption("Gunakan file logo resmi (PNG/JPG). Ukurannya di sampul diatur otomatis menjadi 5,5 × 5,71 cm.")
    logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg"], key="upload_logo")
    if logo:
        st.image(logo, width=120)
    elif ss.get("_logo_simpan"):
        st.image(ss["_logo_simpan"], width=120)
        st.caption("Logo dari pekerjaan tersimpan. Upload ulang hanya bila ingin mengganti.")
    st.subheader("Gambar untuk isi bab dan lampiran")
    gambar_up = st.file_uploader("Gambar (bisa banyak sekaligus)", type=["png", "jpg", "jpeg"],
                                 accept_multiple_files=True, key="upload_gambar")
    if gambar_up:
        st.caption("Pakai nama file ini di penanda [[GAMBAR: …]]:")
        kolom = st.columns(4)
        for n, g in enumerate(gambar_up):
            with kolom[n % 4]:
                st.image(g, use_container_width=True)
                st.code(g.name, language=None)

    tersimpan = list(ss.get("_gambar_simpan", {})) + list(ss.get("_gambar_draft", {}))
    if tersimpan:
        st.caption(f"{len(set(tersimpan))} gambar dari draft atau pekerjaan tersimpan sudah otomatis dipakai: "
                   + ", ".join(sorted(set(tersimpan))))

nama_gambar = sorted(set(kumpulkan_gambar()))

# ---------------------------------------------------------------------------
with tab_akhir:
    st.subheader("Daftar pustaka")
    st.text_area("Daftar pustaka", key="daftar_pustaka", height=260, label_visibility="collapsed",
                 placeholder="Tempel dari Mendeley/Zotero, satu referensi per baris.")
    n_ref = len([b for b in ss["daftar_pustaka"].splitlines() if b.strip()])
    (st.warning if 0 < n_ref < 10 else st.caption)(
        f"{n_ref} referensi. Panduan meminta minimal 10 artikel jurnal. "
        "Urutan abjad diatur otomatis; pakai `*judul*` untuk huruf miring.")

    st.subheader("Tambah referensi")
    st.caption("Upload PDF jurnal atau tempel DOI-nya, dan rinciannya diisi otomatis dari basis data Crossref lalu "
               "disusun dengan gaya APA edisi 7. Sumber tanpa DOI (buku, jurnal lokal, halaman web) bisa diisi sendiri. "
               "PDF hanya dibaca untuk mencari DOI dan tidak disimpan.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.file_uploader("PDF artikel jurnal", type=["pdf"], key="upload_ref_pdf")
        st.button("Baca PDF", on_click=cb_baca_pdf_ref)
    with c2:
        st.text_input("Atau tempel DOI", key="rf_doi", placeholder="mis. 10.1257/jel.52.1.5")
        st.button("Cari DOI", on_click=cb_cari_doi_ref)

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        c1.selectbox("Jenis sumber", pst.JENIS, key="rf_jenis")
        c2.text_input("Tahun", key="rf_tahun", placeholder="mis. 2014")
        jenis_ref = ss.get("rf_jenis", pst.JENIS[0])
        st.text_area("Penulis (satu per baris)", key="rf_penulis", height=100,
                     placeholder="Nama belakang, Nama depan\nmis. Lusardi, Annamaria")
        st.checkbox("Penulisnya lembaga atau instansi (ditulis apa adanya)", key="rf_lembaga")
        st.text_input("Judul", key="rf_judul")
        if jenis_ref == "Artikel jurnal":
            st.text_input("Nama jurnal", key="rf_wadah")
            c1, c2, c3 = st.columns(3)
            c1.text_input("Volume", key="rf_volume")
            c2.text_input("Nomor", key="rf_nomor")
            c3.text_input("Halaman", key="rf_halaman", placeholder="mis. 5-44")
            st.text_input("DOI atau tautan", key="rf_tautan")
        elif jenis_ref == "Buku":
            st.text_input("Penerbit", key="rf_wadah")
            st.text_input("DOI atau tautan (opsional)", key="rf_tautan")
        else:
            st.text_input("Nama situs atau lembaga penerbit", key="rf_wadah")
            st.text_input("Alamat web", key="rf_tautan", placeholder="https://")

        isian_ref = ref_sekarang()
        if any(str(isian_ref[k]).strip() for k in ("penulis", "judul", "wadah")):
            st.markdown(tp.pratinjau_ref(pst.format_apa(isian_ref), pst.kurang(isian_ref)), unsafe_allow_html=True)
        c1, c2, _ = st.columns([1.6, 1, 2.4])
        c1.button("Tambahkan ke daftar pustaka", type="primary", on_click=cb_tambah_ref)
        c2.button("Kosongkan", on_click=cb_kosongkan_ref)
    st.caption("Periksa huruf besar-kecil judul dan nama penulis sebelum menambahkan; data dari Crossref tidak selalu "
               "rapi. Setelah ditambahkan, barisnya masih bisa kamu sunting langsung di kotak Daftar pustaka.")

    st.subheader("Lampiran")
    if not ss["jml_lampiran"]:
        st.caption("Belum ada lampiran. Tambahkan bila laporanmu punya kuesioner, data mentah, atau dokumentasi.")
    for k in range(ss["jml_lampiran"]):
        with st.container(border=True):
            st.text_input(f"Judul lampiran {k + 1}", key=f"lamp{k}_judul")
            st.text_area("Keterangan atau isi (opsional)", key=f"lamp{k}_isi", height=100)
            pilihan = [""] + nama_gambar
            if ss.get(f"lamp{k}_gambar") and ss[f"lamp{k}_gambar"] not in pilihan:
                pilihan.append(ss[f"lamp{k}_gambar"])
            st.selectbox("Gambar lampiran (opsional, upload di tab Gambar & logo)", pilihan, key=f"lamp{k}_gambar")
    c1, c2, _ = st.columns([1.1, 1.5, 3])
    c1.button("Tambah lampiran", on_click=cb_tambah_lampiran)
    c2.button("Hapus lampiran terakhir", on_click=cb_hapus_lampiran)

# ---------------------------------------------------------------------------
with tab_fmt:
    kol_isian, kol_diagram = st.columns([5, 4], gap="large")
    with kol_isian:
        st.subheader("Margin halaman")
        st.caption("Bawaannya mengikuti panduan. Ubah di sini bila prodi atau pembimbing meminta ukuran lain; "
                   "Preview dan file Word langsung mengikuti, dan ukurannya ikut tersimpan di file progres.")
        c1, c2 = st.columns(2)
        batas = dict(min_value=MARGIN_MIN_CM, max_value=MARGIN_MAX_CM, step=0.1, format="%.2f")
        c1.number_input("Atas (cm)", key="mg_atas", **batas)
        c2.number_input("Bawah (cm)", key="mg_bawah", **batas)
        c1.number_input("Kiri (cm)", key="mg_kiri", **batas)
        c2.number_input("Kanan (cm)", key="mg_kanan", **batas)
        st.caption(f"Rentang {tp.angka(MARGIN_MIN_CM)} sampai {tp.angka(MARGIN_MAX_CM)} cm per sisi. "
                   "Sisi kiri biasanya paling lebar karena dipakai untuk jilid.")
        margin = margin_sekarang()
        margin_beda = any(abs(margin[s] - MARGIN_PANDUAN[s]) > 1e-9 for s in SISI_MARGIN)
        if margin_beda:
            st.markdown(f'<div class="beda-panduan">Margin ini berbeda dari panduan '
                        f'({tp.ringkas_margin(MARGIN_PANDUAN)}). Pastikan memang diminta prodi atau pembimbing.</div>',
                        unsafe_allow_html=True)
            st.button("Kembalikan ke margin panduan", on_click=cb_margin_panduan)
        else:
            st.markdown('<div class="sesuai-panduan">Sesuai panduan.</div>', unsafe_allow_html=True)
        st.subheader("Yang tidak berubah")
        st.caption("Kertas A4, Times New Roman 12, spasi 1,5, paragraf menjorok 1,25 cm, dan penomoran halaman "
                   "tetap mengikuti panduan. Lebar tabel, gambar, dan titik-titik daftar isi menyesuaikan bidang teks.")
    with kol_diagram:
        fmt_kini = format_dari({"format": {f"margin_{s}_cm": v for s, v in margin.items()}})
        st.markdown(tp.diagram_margin(margin, MARGIN_PANDUAN, fmt_kini["kertas_lebar_cm"], fmt_kini["kertas_tinggi_cm"],
                                      jarak_footer_cm(fmt_kini)), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
with tab_prev:
    data_prev = kumpulkan_data()
    gambar_prev = kumpulkan_gambar()
    struktur, cek = kerangka(data_prev, gambar_prev)
    if cek:
        with st.expander(f"{len(cek)} hal perlu diperhatikan", expanded=True):
            st.markdown("\n".join(f"- {c}" for c in cek))
    else:
        st.success("Tidak ada masalah yang terdeteksi.")

    mode = st.radio("Tampilan", ["Kerangka", "Tampilan halaman"], horizontal=True, key="mode_preview")
    if mode == "Kerangka":
        st.caption("Ringkasan isi setiap subbab, lengkap dengan nomor tabel dan gambar seperti di hasil akhir.")
        st.markdown("".join(tp.kerangka_bab(bab) for bab in struktur), unsafe_allow_html=True)
    else:
        zoom = st.slider("Perbesaran", 40, 100, 70, step=5, format="%d%%", key="zoom_preview")
        st.caption(f"Tiruan lembar A4 dengan margin {tp.ringkas_margin(margin)}, serta font, spasi, dan penomoran "
                   "yang sama dengan file Word. Garis putus-putus adalah batas margin, tulisan merah berarti belum "
                   "diisi. Pemotongan halaman dan nomor halaman yang pasti baru dihitung oleh Word.")
        logo_prev = ambil_logo()
        html_prev = halaman_html(data_prev, gambar_prev, logo_prev, zoom=zoom / 100)
        if hasattr(st, "iframe"):
            st.iframe(html_prev, height=1100)
        else:  # Streamlit versi lama
            import streamlit.components.v1 as components
            components.html(html_prev, height=1100, scrolling=True)

# ---------------------------------------------------------------------------
with tab_gen:
    st.subheader("Buat file Word")
    st.caption(f"Dibuat dengan margin {tp.ringkas_margin(margin)}"
               + (" (disesuaikan dari panduan)." if margin_beda else " (sesuai panduan)."))
    if st.button("Buat file Word", type="primary"):
        data = kumpulkan_data()
        gambar = kumpulkan_gambar()
        logo_bytes = ambil_logo()
        try:
            hasil, peringatan = buat_dokumen(data, gambar, logo_bytes)
            ss["_hasil"] = hasil
            ss["_peringatan"] = peringatan
        except Exception as e:
            ss.pop("_hasil", None)
            st.error(f"File Word gagal dibuat: {e}")
    if ss.get("_hasil"):
        st.success("File Word sudah dibuat. Buat ulang setiap kali isian atau margin berubah.")
        if MODE_WEB:
            st.caption("Simpan juga progresmu (.json) dari sisi kiri supaya bisa direvisi lagi nanti.")
        for w in ss.get("_peringatan", []):
            st.warning(w)
        nama_file = (ss.get("id_nim") or "laporan").replace("/", "_")
        st.download_button("Unduh .docx", data=ss["_hasil"], file_name=f"TA_{nama_file}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    st.subheader("Setelah file dibuka di Word")
    st.markdown("""
1. Klik **Yes** saat Word bertanya mau memperbarui *fields*, atau tekan **Ctrl + A** lalu **F9** (di Mac: **Cmd + A** lalu **Fn + F9**).
2. Daftar isi, daftar tabel, daftar gambar, dan daftar lampiran terisi lengkap dengan nomor halaman.
""")

# ---------------------------------------------------------------------------
# Autosave: dijalankan di akhir setiap interaksi, hanya bila ada perubahan
# ---------------------------------------------------------------------------
if not MODE_WEB and ss["_autosave_status"] == "aktif" and ss.get("autosave_on", True):
    data_as = kumpulkan_data()
    gambar_as = kumpulkan_gambar()
    logo_as = ambil_logo()
    jejak = asv.sidik({"d": data_as, "g": sorted((k, len(v)) for k, v in gambar_as.items()),
                       "l": len(logo_as or b"")})
    if jejak != ss.get("_autosave_sidik"):
        try:
            ss["_autosave_waktu"] = asv.simpan(data_as, gambar_as, logo_as)
            ss["_autosave_sidik"] = jejak
        except Exception as e:
            if not ss.get("_autosave_gagal"):
                st.toast(f"Simpan otomatis gagal: {e}. Gunakan Simpan progres manual.", icon=":material/error:")
            ss["_autosave_gagal"] = True

if MODE_WEB:   # browser bertanya dulu sebelum tab ditutup, supaya isian tidak hilang tak sengaja
    tp.pasang_peringatan_tutup(st)
