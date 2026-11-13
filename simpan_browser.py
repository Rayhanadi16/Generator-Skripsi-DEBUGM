"""
Simpan otomatis untuk mode web: isian disimpan di browser pengunjung (IndexedDB), bukan di server.

Streamlit berjalan di server dan IndexedDB hanya bisa disentuh dari browser, jadi jembatannya satu
komponen st.components.v2 tanpa tampilan selain satu baris status.

- pasang(...)        -> dipanggil sekali per putaran skrip; mengirim perintah dan mengembalikan jawaban browser
- TERSEDIA           -> False di Streamlit lama yang belum punya st.components.v2
- jaga_tutup()       -> browser bertanya dulu sebelum tab ditutup

Yang disimpan hanya keadaan terakhir (tanpa riwayat versi) dan hanya terbaca di browser yang sama.
"""

import base64

import streamlit as st

TERSEDIA = hasattr(getattr(st, "components", None), "v2")

_JS = """
const DB = "generator_ta", TOKO = "simpanan";

function buka() {
  return new Promise((selesai, gagal) => {
    const minta = indexedDB.open(DB, 1);
    minta.onupgradeneeded = () => minta.result.createObjectStore(TOKO);
    minta.onsuccess = () => selesai(minta.result);
    minta.onerror = () => gagal(minta.error);
  });
}

// nilai null berarti hapus kunci itu
async function tulis(pasangan) {
  const db = await buka();
  return new Promise((selesai, gagal) => {
    const t = db.transaction(TOKO, "readwrite");
    for (const [kunci, nilai] of Object.entries(pasangan)) {
      if (nilai === null) t.objectStore(TOKO).delete(kunci);
      else t.objectStore(TOKO).put(nilai, kunci);
    }
    t.oncomplete = () => { db.close(); selesai(); };
    t.onerror = () => { db.close(); gagal(t.error); };
  });
}

async function baca(daftarKunci) {
  const db = await buka();
  return new Promise((selesai, gagal) => {
    const t = db.transaction(TOKO, "readonly");
    const hasil = {};
    for (const kunci of daftarKunci) {
      const minta = t.objectStore(TOKO).get(kunci);
      minta.onsuccess = () => { hasil[kunci] = minta.result ?? null; };
    }
    t.oncomplete = () => { db.close(); selesai(hasil); };
    t.onerror = () => { db.close(); gagal(t.error); };
  });
}

async function kosongkan() {
  const db = await buka();
  return new Promise((selesai, gagal) => {
    const t = db.transaction(TOKO, "readwrite");
    t.objectStore(TOKO).clear();
    t.oncomplete = () => { db.close(); selesai(); };
    t.onerror = () => { db.close(); gagal(t.error); };
  });
}

const jam = (ms) => new Date(ms).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
const tanggal = (ms) => new Date(ms).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });

export default function (komponen) {
  const { data, setStateValue, parentElement } = komponen;
  // bertahan selama halaman terbuka, supaya perintah yang sama tidak dijalankan dua kali
  const S = (window.__simpanTA ??= { lapor: false, sidik: null, muat: null, hapus: null, teks: "" });

  let baris = parentElement.querySelector(".status-simpan");
  if (!baris) {
    baris = document.createElement("div");
    baris.className = "catatan-sisi status-simpan";
    baris.setAttribute("role", "status");
    parentElement.appendChild(baris);
  }
  const status = (teks) => { S.teks = teks; baris.textContent = teks; };
  baris.textContent = S.teks;
  const gagal = (apa, err) => {
    status(apa + " Pakai Simpan progres (.json) sebagai gantinya.");
    console.error("simpan_browser:", err);
  };

  if (!S.lapor) {
    S.lapor = true;
    baca(["info"]).then(({ info }) => {
      setStateValue("info", info ? { ...info, ada: true, waktu_teks: tanggal(info.waktu) } : { ada: false });
      status(info ? "Tersimpan di perangkat ini pada " + tanggal(info.waktu) + "."
                  : "Belum ada simpanan di perangkat ini.");
    }).catch((err) => {
      setStateValue("info", { ada: false, mati: true });
      gagal("Browser ini tidak mengizinkan simpan otomatis.", err);
    });
  }

  if (data.hapus && data.hapus !== S.hapus) {
    S.hapus = data.hapus;
    S.sidik = null;
    kosongkan().then(() => status("Simpanan di perangkat ini sudah dihapus."))
               .catch((err) => gagal("Simpanan tidak bisa dihapus.", err));
    return;
  }

  if (data.minta && data.minta !== S.muat) {
    S.muat = data.minta;
    baca(["isian", "gambar", "logo"]).then((isi) => setStateValue("muatan", { nonce: data.minta, ...isi }))
      .catch((err) => { setStateValue("muatan", { nonce: data.minta, galat: true }); gagal("Simpanan tidak bisa dibaca.", err); });
    return;
  }

  if (data.mati) { status("Simpan otomatis mati."); return; }

  if (data.simpan && data.sidik !== S.sidik) {
    S.sidik = data.sidik;
    const waktu = Date.now();
    const pasangan = { isian: data.isian, info: { ...data.info, waktu } };
    if ("gambar" in data) pasangan.gambar = data.gambar;   // tidak dikirim ulang bila gambarnya tidak berubah
    if ("logo" in data) pasangan.logo = data.logo;
    tulis(pasangan).then(() => status("Tersimpan di perangkat ini pukul " + jam(waktu) + "."))
      .catch((err) => { S.sidik = null; gagal("Simpan otomatis gagal, mungkin penyimpanan browser penuh.", err); });
  } else if (S.teks === "Simpan otomatis mati.") {
    status("Simpan otomatis aktif.");
  }
}
"""

_JS_JAGA = """
export default function () {
  if (window.__jagaTutup) return;
  window.__jagaTutup = true;
  window.addEventListener("beforeunload", (e) => { e.preventDefault(); e.returnValue = ""; });
}
"""

if TERSEDIA:
    _komponen = st.components.v2.component("simpan_browser", js=_JS, isolate_styles=False)
    _jaga = st.components.v2.component("jaga_tutup", js=_JS_JAGA)


def ke_b64(isi):
    return base64.b64encode(isi).decode("ascii") if isi else None


def dari_b64(teks):
    return base64.b64decode(teks) if teks else None


def _abaikan():
    pass


def pasang(perintah):
    """Kirim perintah ke browser; kembalikan (info, muatan) terakhir yang dilaporkan browser, atau None."""
    hasil = _komponen(key="simpan_browser", data=perintah, on_info_change=_abaikan, on_muatan_change=_abaikan)
    return hasil.get("info"), hasil.get("muatan")


def jaga_tutup():
    _jaga(key="jaga_tutup")
