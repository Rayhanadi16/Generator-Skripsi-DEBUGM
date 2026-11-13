"""
Tampilan aplikasi: gaya (CSS) dan potongan HTML kecil yang dipakai app.py.

Warna diambil dari meja administrasi: kertas putih di atas meja abu kebiruan,
teks warna tinta, dan satu aksen ungu tinta stempel untuk hal yang bisa diklik.
"""

import html

WARNA = {
    "kertas": "#FFFFFF",
    "meja": "#ECEEF3",
    "tinta": "#1B1F2E",
    "redup": "#5E6477",
    "stempel": "#4A3AA7",
    "stempel_muda": "#ECEAF8",
    "garis": "#D5D8E0",
    "merah": "#B3261E",
    "kuning": "#8F5800",
    "hijau": "#2E7D4F",
}

PEMBUAT = "@rayhanadi16_"

CSS = """
<style>
:root {
  /* --redup dan --kuning dipilih agar tetap 4,5:1 di atas --meja dan --stempel-muda, bukan hanya di atas putih */
  --kertas:#FFFFFF; --meja:#ECEEF3; --tinta:#1B1F2E; --redup:#5E6477;
  --stempel:#4A3AA7; --stempel-tua:#392C86; --stempel-muda:#ECEAF8; --garis:#D5D8E0;
  --tepi:#8A90A0;   /* tepi kotak isian dan tombol: 3:1 terhadap kertas */
  --merah:#B3261E; --kuning:#8F5800; --hijau:#2E7D4F;
  --lapis:#F7F8FA; --lapis2:#F1F2F6; --kertas-ungu:#F7F6FD; --samar:#6A7083;
  --di-stempel:#FFFFFF;   /* teks di atas warna stempel */
  --ui:"Avenir Next","Segoe UI",system-ui,-apple-system,sans-serif;
  --judul:"Charter","Iowan Old Style","Cambria",Georgia,serif;
}

/* ---------- dasar ---------- */
.stApp { background:var(--meja); color:var(--tinta); }
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp [data-baseweb="tab"], .stApp [data-baseweb="select"] div, .stApp summary,
.stApp [data-testid="stCaptionContainer"],
.kop, .catatan-sisi, .pratinjau-ref, .rekap, .jejak, .kerangka, .dm, .dm-ket, .beda-panduan, .sesuai-panduan {
  font-family:var(--ui); }
.stApp h1, .stApp h2, .stApp h3 { font-family:var(--judul); color:var(--tinta); letter-spacing:-0.01em; }
.stApp h2 { font-size:1.5rem; font-weight:700; padding:0.2rem 0 0.1rem; }
.stApp h3 { font-size:1.2rem; font-weight:700; padding:1.1rem 0 0.2rem; }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {
  color:var(--redup); font-size:0.875rem; line-height:1.5; opacity:1; }
header[data-testid="stHeader"] { background:transparent; }

/* lembar kerja: isi utama duduk di atas "kertas" */
[data-testid="stMainBlockContainer"] {
  max-width:1120px; background:var(--kertas); border:1px solid var(--garis);
  border-radius:4px; box-shadow:0 2px 0 var(--garis);
  padding:2.25rem 2.75rem 3rem; margin:2.5rem auto 3rem; }
@media (max-width:820px) {
  /* jarak atas memberi tempat untuk tombol pembuka sisi kiri, supaya tidak menimpa judul */
  [data-testid="stMainBlockContainer"] { padding:3.5rem 1rem 2rem; margin:0.5rem auto 1.5rem; border-radius:0; }
}

/* tombol tema: ikon saja di pojok kanan atas lembar; labelnya tetap ada untuk pembaca layar */
[data-testid="stMainBlockContainer"] { position:relative; }
.st-key-tombol_tema { position:absolute; top:0.8rem; right:1rem; width:auto; z-index:5; }
.stApp .st-key-tombol_tema button { width:44px; height:44px; min-height:44px; padding:0; }
.st-key-tombol_tema button [data-testid="stIconMaterial"] { font-size:1.4rem; margin:0; }
.st-key-tombol_tema button [data-testid="stMarkdownContainer"] {
  position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; }

/* ---------- kop ---------- */
.kop { display:flex; align-items:flex-end; justify-content:space-between; gap:2rem; flex-wrap:wrap;
       padding-bottom:1.1rem; border-bottom:2px solid var(--tinta); margin-bottom:0.9rem; }
.kop h1 { font-family:var(--judul); font-size:2.1rem; line-height:1.1; font-weight:700; margin:0; padding:0; }
.kop p { margin:0.45rem 0 0; color:var(--redup); font-size:0.98rem; max-width:34rem; line-height:1.5; }
.kop-format { font-size:0.85rem; color:var(--redup); line-height:1.55; text-align:right; }
.kop-format b { color:var(--tinta); font-weight:600; }
.kop-format .ubah { color:var(--stempel); font-weight:600; }
@media (max-width:820px) { .kop { gap:0.9rem; } .kop h1 { font-size:1.7rem; } .kop-format { text-align:left; } }

/* ---------- tab (role=... untuk Streamlit baru, data-baseweb untuk versi lama) ---------- */
/* sembilan tab harus terlihat semua: di layar sempit turun ke baris kedua, bukan digulir ke samping */
.stTabs [role="tablist"] { gap:0 1rem; flex-wrap:wrap; overflow:visible; border-bottom:1px solid var(--garis); }
.stTabs [role="tab"] { padding:0.85rem 0 0.8rem; height:auto; min-height:44px; min-width:44px; justify-content:center; color:var(--redup);
  background:transparent; cursor:pointer; }
.stTabs button[aria-label^="Scroll tabs"] { display:none; }
.stTabs [role="tab"] p { font-size:0.95rem; font-weight:500; font-family:var(--ui); color:inherit; }
.stTabs [role="tab"]:hover { color:var(--tinta); }
.stTabs [role="tab"][aria-selected="true"] { color:var(--stempel); }
.stTabs [role="tab"][aria-selected="true"] p { font-weight:700; }
.stTabs [role="tab"]:focus-visible { outline:2px solid var(--stempel); outline-offset:-2px; }
.stTabs .react-aria-SelectionIndicator, .stTabs [data-baseweb="tab-highlight"] { background:var(--stempel); height:3px; }
.stTabs [data-baseweb="tab-border"] { display:none; }
.stTabs [role="tabpanel"] { padding-top:1.5rem; }

/* ---------- isian ---------- */
.stApp [data-testid="stWidgetLabel"] p { font-size:0.875rem; font-weight:600; color:var(--tinta); }
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div,
.stApp [data-testid="stNumberInputContainer"], .stApp [data-testid="stTextInputRootElement"],
.stApp [data-testid="stTextAreaRootElement"] {
  background:var(--kertas); border:1px solid var(--tepi); border-radius:3px; }
.stApp [data-baseweb="base-input"], .stApp input, .stApp textarea,
.stApp [data-testid="stTextInputRootElement"] > div, .stApp [data-testid="stTextAreaRootElement"] > div {
  background:var(--kertas); color:var(--tinta); }
.stApp [data-testid="stNumberInputContainer"] [data-baseweb="input"] { border:0; }
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="textarea"]:focus-within,
.stApp [data-testid="stNumberInputContainer"]:focus-within, .stApp [data-testid="stTextInputRootElement"]:focus-within,
.stApp [data-testid="stTextAreaRootElement"]:focus-within {
  border-color:var(--stempel); box-shadow:0 0 0 1px var(--stempel), 0 0 0 4px var(--stempel-muda); }
.stApp textarea { line-height:1.6; }
.stApp input::placeholder, .stApp textarea::placeholder { color:var(--samar); opacity:1; }

/* ---------- tombol ---------- */
.stApp :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"]) {
  border-radius:3px; border:1px solid var(--tepi); background:var(--kertas); color:var(--tinta);
  padding:0.45rem 0.95rem; box-shadow:none; }
.stApp :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"]):active { transform:translateY(1px); }
.stApp :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"]):disabled {
  cursor:not-allowed; background:var(--lapis2); border-color:var(--garis); color:var(--redup); }
.stApp input:disabled { cursor:not-allowed; }
@media (max-width:820px) {
  .stApp button, .stApp [data-testid="stBaseButton-secondary"], .stApp [data-testid="stBaseButton-primary"] {
    min-height:44px; min-width:44px; }
}
.stApp :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"]) p { font-size:0.9rem; font-weight:600; }
.stApp [data-testid="stBaseButton-secondary"]:hover { border-color:var(--stempel); color:var(--stempel); background:var(--kertas); }
.stApp :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"]):focus-visible {
  outline:2px solid var(--stempel); outline-offset:2px; }
.stApp [data-testid="stBaseButton-primary"] { background:var(--stempel); border-color:var(--stempel); color:var(--di-stempel); }
.stApp [data-testid="stBaseButton-primary"]:hover { background:var(--stempel-tua); border-color:var(--stempel-tua); color:var(--di-stempel); }
.stApp [data-testid="stBaseButton-primary"] p { color:var(--di-stempel); }

/* ---------- panel lipat & kotak ---------- */
.stApp [data-testid="stExpander"] details { border:1px solid var(--garis); border-radius:3px; background:var(--kertas); }
.stApp [data-testid="stExpander"] summary { padding:0.8rem 1rem; }
.stApp [data-testid="stExpander"] summary p { font-weight:600; font-size:0.95rem; }
.stApp [data-testid="stExpander"] summary:hover { color:var(--stempel); }
.stApp [data-testid="stFileUploaderDropzone"] { background:var(--lapis); border:1px dashed var(--tepi); border-radius:3px; }
.stApp code { background:var(--lapis2); color:var(--tinta); border-radius:2px; font-size:0.85em; }
.stApp [data-testid="stAlertContainer"] { border-radius:3px; }
.stApp hr { border-color:var(--garis); margin:1.2rem 0; }

/* ---------- sisi kiri ---------- */
[data-testid="stSidebar"] { background:var(--lapis); border-right:1px solid var(--garis); }
[data-testid="stSidebar"] h2 { font-size:1.15rem; padding-top:0; }
[data-testid="stSidebar"] h3 { font-size:1rem; padding-top:0.4rem; }
.catatan-sisi { font-size:0.875rem; margin-bottom:0.6rem; color:var(--redup); line-height:1.55; }
.catatan-sisi b { color:var(--tinta); font-weight:600; }

/* ---------- pratinjau referensi ---------- */
.pratinjau-ref { border:1px solid var(--garis); background:var(--kertas-ungu); padding:0.75rem 1rem; margin:0.3rem 0 0.9rem;
  border-radius:3px; }
.pratinjau-ref .hasil { font-family:"Times New Roman",Times,serif; font-size:1.02rem; line-height:1.45;
  padding-left:2rem; text-indent:-2rem; overflow-wrap:anywhere; }
.pratinjau-ref .ket { font-size:0.8rem; color:var(--redup); margin-bottom:0.35rem; }
.pratinjau-ref .kurang { font-size:0.84rem; color:var(--kuning); margin-top:0.5rem; font-weight:600; }

/* ---------- watermark pembuat ---------- */
.cap-pembuat { position:fixed; right:1.1rem; bottom:0.9rem; z-index:999; pointer-events:none; user-select:none;
  font-family:var(--judul); font-weight:700; font-size:1.05rem; color:var(--stempel); opacity:0.42;
  border:2px solid currentColor; border-radius:3px; padding:0.2rem 0.6rem; transform:rotate(-4deg); }
/* di ponsel cap ini menutupi isian; nama pembuat tetap ada di sisi kiri */
@media (max-width:820px) { .cap-pembuat { display:none; } }
.stApp input:disabled { -webkit-text-fill-color:var(--tinta); color:var(--tinta); opacity:1; }
.stApp [data-testid="stTextInputRootElement"]:has(input:disabled),
.stApp [data-testid="stTextInputRootElement"]:has(input:disabled) > div,
.stApp [data-testid="stTextInputRootElement"]:has(input:disabled) input { background:var(--lapis2); }

/* ---------- status pelacakan draft ---------- */
.titik { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; vertical-align:baseline; }
.titik.hijau { background:var(--hijau); } .titik.kuning { background:var(--kuning); } .titik.merah { background:var(--merah); }
.rekap { display:flex; flex-wrap:wrap; border:1px solid var(--garis); border-radius:3px; margin:0.6rem 0 1rem; }
.rekap div { flex:1 1 9rem; padding:0.85rem 1.1rem; border-right:1px solid var(--garis); }
.rekap div:last-child { border-right:0; }
.rekap strong { display:block; font-family:var(--judul); font-size:1.9rem; line-height:1.1; font-variant-numeric:tabular-nums; }
.rekap span.ket { font-size:0.85rem; color:var(--redup); }
.jejak { font-size:0.82rem; color:var(--redup); margin-top:0.15rem; }

/* ---------- kerangka ---------- */
.kerangka { border-top:1px solid var(--garis); padding:0.95rem 0 0.6rem; }
.kerangka h4 { font-family:var(--judul); font-size:1.02rem; font-weight:700; margin:0 0 0.45rem; padding:0; }
.kerangka .sub { display:flex; gap:0.75rem; align-items:baseline; padding:0.2rem 0; font-size:0.92rem; }
.kerangka .no { flex:none; width:2.4rem; color:var(--redup); font-variant-numeric:tabular-nums; }
.kerangka .nm { flex:1; }
.kerangka .rc { flex:none; color:var(--redup); font-size:0.84rem; font-variant-numeric:tabular-nums; text-align:right; }
.kerangka .rc.kosong { color:var(--merah); font-weight:600; }
.kerangka .anak { margin:0 0 0.15rem 3.15rem; font-size:0.86rem; color:var(--redup); }

/* ---------- diagram margin ---------- */
.dm { display:grid; grid-template-columns:auto minmax(0,1fr) auto; grid-template-rows:auto auto auto;
      align-items:center; justify-items:center; gap:0.5rem 0.75rem; max-width:23rem; margin:0 auto; }
.dm .nilai { font-size:0.85rem; line-height:1.3; text-align:center; color:var(--redup); font-variant-numeric:tabular-nums; }
.dm .nilai b { display:block; font-size:1.02rem; color:var(--tinta); font-weight:700; }
.dm .nilai.beda b { color:var(--stempel); }
.dm-kertas { grid-column:2; grid-row:2; position:relative; width:100%; aspect-ratio:21/29.7;
      border:1px solid var(--tepi); box-shadow:3px 3px 0 var(--garis);
      background:repeating-linear-gradient(135deg, var(--stempel-muda) 0 5px, var(--kertas-ungu) 5px 10px); }
.dm-teks { position:absolute; background-color:var(--kertas); outline:1px dashed var(--stempel);
      background-image:repeating-linear-gradient(to bottom, transparent 0 7px, var(--garis) 7px 8px);
      background-origin:content-box; background-clip:content-box; box-sizing:border-box; padding:7px 6px 6px;
      transition:top .18s ease, right .18s ease, bottom .18s ease, left .18s ease; }
.dm-hal { position:absolute; left:0; right:0; text-align:center; font-size:0.62rem; color:var(--redup); line-height:1; transform:translateY(50%); }
@media (prefers-reduced-motion:reduce) { .dm-teks { transition:none; } }
.dm-ket { text-align:center; font-size:0.85rem; color:var(--redup); margin-top:0.9rem; }
.dm-ket b { color:var(--tinta); font-weight:600; }
.beda-panduan { border:1px solid var(--stempel); background:var(--stempel-muda); padding:0.7rem 0.9rem;
      font-size:0.9rem; line-height:1.5; margin:0.4rem 0 0.8rem; border-radius:3px; }
.sesuai-panduan { font-size:0.9rem; color:var(--redup); margin:0.4rem 0 0.8rem; }
</style>
"""

# Mode gelap: meja yang sama di malam hari. Stempel dibuat lebih terang supaya tetap terbaca di atas gelap,
# dan teks di atasnya berbalik menjadi gelap.
CSS_GELAP = """
<style>
:root {
  color-scheme:dark;
  --kertas:#1E212B; --meja:#14161D; --tinta:#E8EAF0; --redup:#A8AEBF;
  --stempel:#B3A6F5; --stempel-tua:#C9BFFA; --stempel-muda:#2D2950; --garis:#343846;
  --tepi:#7C8398;
  --merah:#F4978E; --kuning:#E5B454; --hijau:#7CCB9E;
  --lapis:#191C24; --lapis2:#2A2E3B; --kertas-ungu:#252238; --samar:#8E94A6;
  --di-stempel:#14161D;
}
.stApp p, .stApp li, .stApp label, .stApp summary, .stApp [data-testid="stWidgetLabel"] { color:var(--tinta); }
.stTabs [role="tab"] [data-testid="stMarkdownContainer"] { color:inherit; }

/* komponen bawaan Streamlit yang membawa warna terangnya sendiri */
.stApp [data-testid="stAlertContainer"] { background:var(--lapis2); border:1px solid var(--garis); color:var(--tinta); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { border-color:var(--hijau); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { border-color:var(--kuning); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { border-color:var(--merah); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) { border-color:var(--stempel); }
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] summary:hover { background:var(--lapis); }
.stApp [data-testid="stFileUploaderDropzone"] :not(button, button *) { color:var(--redup); }
.stApp [data-testid="stFileUploaderFile"] * { color:var(--tinta); }
.stApp [data-testid="stNumberInputContainer"] button { background:transparent; color:var(--tinta); }
.stApp [data-testid="stNumberInputContainer"] button:hover { background:var(--lapis2); }
.stApp [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--garis); }
.stApp [data-testid="stCode"], .stApp pre { background:var(--lapis2); color:var(--tinta); }
.stApp [data-testid="stHeader"] button, .stApp [data-testid="stSidebar"] button[kind="headerNoPadding"],
.stApp [data-testid="stExpandSidebarButton"] { color:var(--tinta); }
[data-testid="stToast"] { background:var(--lapis2); color:var(--tinta); border:1px solid var(--garis); }
[data-testid="stToast"] * { color:var(--tinta); }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul { background:var(--lapis2); }
[data-baseweb="popover"] [role="option"] { color:var(--tinta); }
[data-baseweb="popover"] [role="option"]:hover, [data-baseweb="popover"] [role="option"][aria-selected="true"] {
  background:var(--stempel-muda); }
[data-baseweb="tooltip"] > div { background:var(--lapis2); color:var(--tinta); }
.stApp [data-baseweb="select"] svg { fill:var(--tinta); }
.stApp [data-baseweb="select"] div { color:var(--tinta); background-color:transparent; }
.stApp [data-baseweb="select"] > div { background-color:var(--kertas); }
</style>
"""


def css(gelap=False):
    return CSS + (CSS_GELAP if gelap else "")


TENTANG_DATA = """
- Isian, draft, gambar, dan logo yang kamu unggah hanya dipakai untuk menyusun laporanmu selama tab ini terbuka.
- Tidak ada yang disimpan ke penyimpanan server dan tidak ada akun. Setelah tab ditutup, isian tidak bisa dipulihkan.
- File progres (.json) berisi seluruh isianmu. Simpan di tempat yang aman dan jangan dibagikan sembarangan.
- Hasilnya mengikuti Panduan TA DEB SV UGM 2025. Tetap cek file Word-nya terhadap panduan dan arahan pembimbing sebelum dikumpulkan.
"""


def pasang_peringatan_tutup(st):
    """Versi web: browser bertanya dulu sebelum tab ditutup atau dimuat ulang, supaya isian tidak hilang tak sengaja."""
    import streamlit.components.v1 as components
    components.html("""<script>
      try {
        const w = window.parent;
        if (!w.__jagaTutup) {
          w.__jagaTutup = true;
          w.addEventListener("beforeunload", function (e) { e.preventDefault(); e.returnValue = ""; });
        }
      } catch (err) {}
    </script>""", height=0)


def angka(x):
    """4.0 -> '4', 2.54 -> '2,54' (gaya penulisan Indonesia)."""
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def ringkas_margin(m):
    return f"atas {angka(m['atas'])}, kiri {angka(m['kiri'])}, kanan {angka(m['kanan'])}, bawah {angka(m['bawah'])} cm"


def kop(margin, bawaan, nama_format):
    beda = any(abs(margin[s] - bawaan[s]) > 1e-9 for s in margin)
    catatan = '<br><span class="ubah">Margin disesuaikan dari panduan</span>' if beda else ""
    return f"""
<div class="kop">
  <div>
    <h1>Generator laporan tugas akhir</h1>
    <p>Tulis isinya saja. Margin, font, spasi, dan penomoran halaman diatur otomatis saat file Word dibuat.</p>
  </div>
  <div class="kop-format"><b>{html.escape(nama_format)}</b><br>
    A4, Times New Roman 12, spasi 1,5<br>Margin {ringkas_margin(margin)}{catatan}</div>
</div>"""


def pratinjau_ref(baris, kurang):
    """Tampilkan satu entri daftar pustaka seperti di hasil Word (*...* menjadi huruf miring)."""
    import re
    isi = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html.escape(baris))
    catatan = f'<div class="kurang">Belum diisi: {html.escape(", ".join(kurang))}</div>' if kurang else ""
    return (f'<div class="pratinjau-ref"><div class="ket">Hasil yang akan ditambahkan</div>'
            f'<div class="hasil">{isi}</div>{catatan}</div>')


def watermark():
    return f'<div class="cap-pembuat" aria-hidden="true">{html.escape(PEMBUAT)}</div>'


def diagram_margin(margin, bawaan, lebar_kertas=21.0, tinggi_kertas=29.7, jarak_footer=1.5):
    """Miniatur lembar A4: area berarsir = margin, area putih bergaris = bidang teks."""
    def persen(nilai, total):
        return f"{nilai / total * 100:.3f}%"

    def nilai(sisi, label):
        beda = " beda" if abs(margin[sisi] - bawaan[sisi]) > 1e-9 else ""
        return f'<div class="nilai{beda}">{label}<b>{angka(margin[sisi])} cm</b></div>'

    lebar_teks = lebar_kertas - margin["kiri"] - margin["kanan"]
    tinggi_teks = tinggi_kertas - margin["atas"] - margin["bawah"]
    return f"""
<div class="dm" role="img" aria-label="Diagram margin halaman: {ringkas_margin(margin)}">
  <div style="grid-column:2;grid-row:1">{nilai('atas', 'Atas')}</div>
  <div style="grid-column:1;grid-row:2">{nilai('kiri', 'Kiri')}</div>
  <div class="dm-kertas">
    <div class="dm-teks" style="top:{persen(margin['atas'], tinggi_kertas)};bottom:{persen(margin['bawah'], tinggi_kertas)};left:{persen(margin['kiri'], lebar_kertas)};right:{persen(margin['kanan'], lebar_kertas)}"></div>
    <div class="dm-hal" style="bottom:{persen(jarak_footer, tinggi_kertas)}">nomor halaman</div>
  </div>
  <div style="grid-column:3;grid-row:2">{nilai('kanan', 'Kanan')}</div>
  <div style="grid-column:2;grid-row:3">{nilai('bawah', 'Bawah')}</div>
</div>
<div class="dm-ket">Bidang teks <b>{angka(lebar_teks)} × {angka(tinggi_teks)} cm</b> di kertas A4 {angka(lebar_kertas)} × {angka(tinggi_kertas)} cm</div>"""


def rekap_draft(hitung):
    return f"""
<div class="rekap">
  <div><strong>{hitung['hijau']}</strong><span class="ket"><span class="titik hijau"></span>Sudah yakin</span></div>
  <div><strong>{hitung['kuning']}</strong><span class="ket"><span class="titik kuning"></span>Perlu dicek</span></div>
  <div><strong>{hitung['merah']}</strong><span class="ket"><span class="titik merah"></span>Belum ditempatkan</span></div>
</div>"""


def jejak_blok(warna, yakin, alasan):
    label = {"hijau": "Yakin", "kuning": "Perlu dicek", "merah": "Belum ditempatkan"}[warna]
    alasan = f", {html.escape(alasan)}" if alasan else ""
    return f'<div class="jejak"><span class="titik {warna}"></span>{label} {int(yakin * 100)}%{alasan}</div>'


def kerangka_bab(bab):
    baris = []
    for s in bab["subbab"]:
        kosong = s["paragraf"] == 0 and not s["tabel"] and not s["gambar"]
        if kosong:
            rinci = "masih kosong"
        else:
            rinci = f"{s['paragraf']} paragraf, {s['kata']} kata"
            if s["rumus"]:
                rinci += f", {s['rumus']} rumus"
        baris.append(f'<div class="sub"><span class="no">{s["no"]}</span><span class="nm">{html.escape(s["judul"])}</span>'
                     f'<span class="rc{" kosong" if kosong else ""}">{rinci}</span></div>')
        for x in s["subsub"] + s["tabel"] + s["gambar"]:
            baris.append(f'<div class="anak">{html.escape(x)}</div>')
    if not baris:
        baris.append('<div class="anak" style="margin-left:0">Belum ada subbab.</div>')
    return f'<div class="kerangka"><h4>{html.escape(bab["judul"])}</h4>{"".join(baris)}</div>'
