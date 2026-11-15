# Generator Laporan Tugas Akhir (Prototipe)

Aplikasi untuk menyusun laporan TA dalam format Word (.docx) sesuai
**Panduan Penulisan Tugas Akhir 2025, DEB Sekolah Vokasi UGM**.
Kamu cukup mengisi identitas, isi bab, pustaka, dan gambar. Format diatur otomatis.

> **Ini versi web**, disiapkan untuk dipakai banyak orang lewat internet. Bedanya dengan versi komputer sendiri:
> isian pengunjung **tidak disimpan di server**. Simpan otomatisnya menaruh isian, gambar, dan logo di browser
> pengunjung sendiri (IndexedDB), jadi hanya terbaca di browser dan perangkat yang sama, tanpa riwayat versi.
> Untuk pindah perangkat tetap pakai tombol **Simpan progres (.json)**. Cara meng-online-kan ada di
> `PANDUAN_DEPLOY.md`. Untuk menjalankan folder ini di komputer sendiri dengan autosave:
> `GENERATOR_MODE=lokal streamlit run app.py --server.address localhost`. Bagian tentang autosave di bawah
> hanya berlaku untuk mode lokal itu.

## Isi folder

| File | Fungsi |
|---|---|
| `app.py` | Tampilan aplikasi (Streamlit) |
| `tampilan.py` | Gaya tampilan (warna, huruf) dan diagram margin |
| `pustaka.py` | Baca DOI dari PDF, ambil data Crossref, susun entri APA 7 |
| `pengaturan.py` | Mode aplikasi: `web` (bawaan) atau `lokal` |
| `generator.py` | Mesin pembuat .docx + semua aturan format |
| `importer.py` | Pembaca & pelacak draft mentah (.docx) |
| `preview.py` | Preview kerangka & tampilan halaman sebelum generate |
| `autosave.py` | Simpan otomatis + riwayat versi (mode lokal) |
| `simpan_browser.py` | Simpan otomatis mode web: jembatan ke IndexedDB di browser pengunjung |
| `pembaruan.py` | Riwayat versi untuk jendela "Yang baru" |
| `sitasi.py` | Cek sitasi: mencocokkan kutipan di isi bab dengan daftar pustaka |
| `impor_pustaka.py` | Pembaca file .bib dan .ris dari Zotero atau Mendeley |
| `tabel_impor.py` | Pembaca tabel dari Excel (.xlsx) atau CSV |
| `rujukan.py` | Rujukan silang: label pada gambar, tabel, dan rumus, serta penanda `[[REF]]` |
| `ekspor_pdf.py` | PDF pratinjau lewat LibreOffice |
| `packages.txt` | Paket sistem untuk Streamlit Community Cloud (LibreOffice dan huruf pengganti) |
| `contoh_data.json` | Data contoh untuk mencoba |
| `grafik_contoh.png` | Gambar contoh untuk data contoh |
| `requirements.txt` | Daftar library yang dibutuhkan |
| `.streamlit/config.toml` | Pengaturan privasi (folder tersembunyi di Mac, jangan dihapus) |

## Cara menjalankan di macOS (sekali saja untuk persiapan)

1. Install Python dari https://www.python.org/downloads/macos/ (installer "universal2", cocok untuk M1/M2/M3).
2. Ekstrak zip ini, misalnya ke folder **Documents**.
3. Buka **Terminal** (Cmd + Spasi → ketik "Terminal"), lalu jalankan:

```bash
cd ~/Documents/generator-skripsi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Menjalankan aplikasi (setiap kali mau pakai)

```bash
cd ~/Documents/generator-skripsi
source venv/bin/activate
streamlit run app.py
```

Browser akan terbuka di `http://localhost:8501`. Untuk menghentikan, tekan **Ctrl + C** di Terminal.

## Cara menjalankan di Windows

1. Install Python dari https://www.python.org/downloads/windows/ dan **centang "Add python.exe to PATH"** saat install.
2. Ekstrak zip ini, misalnya ke folder **Documents**.
3. Buka **Command Prompt** (tekan Windows → ketik "cmd"), lalu jalankan sekali:

```bat
cd %USERPROFILE%\Documents\generator-skripsi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Setiap kali mau pakai:

```bat
cd %USERPROFILE%\Documents\generator-skripsi
venv\Scripts\activate
streamlit run app.py
```

## Privasi

- Aplikasi berjalan **sepenuhnya di komputermu sendiri**. Draft, isi skripsi, dan gambar tidak dikirim ke internet.
- File `.streamlit/config.toml` membuat aplikasi hanya bisa dibuka dari komputer itu sendiri
  (tidak terlihat oleh perangkat lain di Wi-Fi yang sama) dan mematikan statistik pemakaian Streamlit.
- File progres `.json` dan folder `autosave/` berisi seluruh isian skripsimu.
  **Kalau mau membagikan aplikasi ini ke teman, hapus dulu folder `autosave/`**
  (atau bagikan zip aslinya), supaya skripsimu tidak ikut terkirim.

## Cara pakai singkat

1. Klik **"Isi dengan data contoh"** di sidebar untuk melihat contohnya.
2. Isi tab **Identitas** sampai **Gambar & logo**: identitas, bagian awal, bab, pustaka & lampiran, lalu upload gambar & logo.
3. Bila perlu, sesuaikan margin di tab **Format halaman**.
4. Cek hasilnya di tab **Preview**, lalu di tab **Buat file Word** klik **Buat file Word** dan unduh file .docx.
5. Buka di **Microsoft Word**. Klik **Yes** saat diminta memperbarui *fields*
   (atau Cmd + A lalu Fn + F9). Daftar isi, tabel, gambar, dan lampiran akan terisi dengan nomor halaman.
6. Isian **tersimpan otomatis** setiap ada perubahan. Saat aplikasi dibuka lagi, klik **Lanjutkan**
   untuk meneruskan pekerjaan terakhir. Untuk cadangan di tempat lain (flashdisk, Google Drive),
   tetap bisa pakai **"Simpan progres (.json)"** di sidebar.

## Upload draft mentah (tab Draft)

Sudah punya draft di Word? Tidak perlu menyalin per subbab.

1. Upload draft `.docx` (dari Google Docs: File → Download → Microsoft Word).
2. Klik **Baca & lacak draft**. Setiap paragraf, tabel, dan gambar diberi tebakan tujuan:
   - 🟢 **Yakin**: ditemukan lewat judul jelas ("BAB II", "2.1 …", Style Heading, "DAFTAR PUSTAKA").
   - 🟡 **Perlu dicek**: ditebak dari judul tanpa nomor yang mirip nama baku, atau dari kata khas
     ("bertujuan untuk" → Tujuan Penelitian, "kuesioner" → Teknik Pengumpulan Data, dst.).
   - 🔴 **Belum ditempatkan**: tidak ada petunjuk sama sekali.
3. Betulkan yang salah lewat dropdown, lalu klik **Terapkan ke form**.

Yang dikenali otomatis: judul bab ("BAB 1", "bab ii …", "BAB III" + judul di baris berikutnya),
subbab bernomor ("1.2 …"), berhuruf ("A. …"), atau tanpa nomor yang mirip nama baku ("Latar belakang masalah");
tabel beserta judul "Tabel x …" dan "Sumber: …"; gambar yang ditempel beserta judul "Gambar x …";
daftar bernomor Word; huruf miring; Kata Pengantar, Abstrak/Intisari, Abstract, Kata kunci, Keywords,
Daftar Pustaka, Lampiran; baris daftar isi dan catatan pribadi ("Catatan: …") disarankan untuk diabaikan.
Nomor tabel/gambar dari draft diganti dengan penomoran baru per bab.

Isi teks drafmu **tidak diubah sama sekali**. Tools hanya memindahkan ke bagian yang tepat.

## Autosave

- Semua isian, gambar, dan logo disimpan otomatis ke folder `autosave/` di dalam folder aplikasi,
  setiap kali ada perubahan. Status dan jam simpan terakhir terlihat di sidebar.
- Teks di kotak isian tersimpan setelah kamu klik di luar kotak atau menekan **Cmd + Enter**
  (Windows: Ctrl + Enter). Jadi sebelum menutup browser, klik dulu di luar kotak yang sedang diketik.
- Saat aplikasi dibuka lagi: pilih **Lanjutkan** atau **Mulai dari awal**. Pekerjaan lama tidak hilang
  kalau memilih mulai dari awal, karena tetap ada di **Riwayat versi**.
- **Riwayat versi** (sidebar): cadangan dibuat tiap 5 menit dan sebelum isian ditimpa (muat progres,
  data contoh, terapkan draft, pulihkan versi). Yang disimpan 30 versi terakhir.
- Jangan membuka aplikasi di dua tab browser sekaligus, karena keduanya akan saling menimpa autosave.

## Mengatur margin (tab Format halaman)

Margin bawaan mengikuti panduan (atas 4, kiri 4, kanan 3, bawah 3 cm). Bila prodi atau pembimbing meminta
ukuran lain, ubah angkanya di tab **Format halaman** (1 sampai 6 cm per sisi, boleh desimal seperti 2,54).

- Diagram lembar A4 di sebelahnya langsung menunjukkan bidang teks yang tersisa.
- Preview dan file Word mengikuti margin baru. Lebar tabel, gambar, dan daftar isi ikut menyesuaikan.
- Margin ikut tersimpan di autosave dan file progres (.json), jadi tidak perlu diatur ulang.
- Tombol **Kembalikan ke margin panduan** mengembalikan ke 4-4-3-3.
- File Word yang sudah dibuat tidak berubah sendiri: klik **Buat file Word** lagi setelah mengubah margin.

## Menambah referensi dari PDF atau DOI (tab Pustaka & lampiran)

Di bawah kotak Daftar pustaka ada bagian **Tambah referensi**:

- **Upload PDF artikel jurnal** lalu klik **Baca PDF**: tools mencari DOI di halaman awal PDF, mengambil
  rinciannya (penulis, tahun, judul, jurnal, volume, halaman) dari basis data Crossref, lalu menyusunnya
  dengan gaya APA edisi 7. PDF hanya dibaca di memori dan tidak disimpan.
- **Tempel DOI** lalu klik **Cari DOI** bila sudah tahu DOI-nya.
- **Isi sendiri** rinciannya untuk sumber tanpa DOI: buku, jurnal lokal yang tidak terdaftar, halaman web.
- Periksa pratinjaunya, lalu klik **Tambahkan ke daftar pustaka**. Barisnya masih bisa disunting di kotak
  Daftar pustaka.

Catatan: pengambilan data butuh internet; judul dari Crossref sering memakai huruf kapital di tiap kata
(APA meminta hanya kata pertama), jadi periksa dulu. Kodenya ada di `pustaka.py`.

## Impor pustaka dari Zotero atau Mendeley (tab Pustaka & lampiran)

Punya koleksi referensi di Zotero atau Mendeley? Tidak perlu menyalin satu per satu.

1. Ekspor ke file `.bib` (BibTeX) atau `.ris`. Zotero: klik kanan koleksi, **Export Collection**, pilih BibTeX.
   Mendeley: pilih referensinya, **File**, **Export**, pilih BibTeX atau RIS. Banyak halaman jurnal juga punya tombol
   Export citation ke RIS.
2. Upload di bagian **Impor dari Zotero atau Mendeley**, lalu klik **Baca file referensi**.
3. Setiap referensi tampil dalam gaya APA 7 dengan kotak centang. Yang sudah ada di daftar pustaka ditandai dan tidak
   bisa ditambahkan lagi; yang rinciannya belum lengkap diberi catatan.
4. Klik **Tambahkan yang dicentang**.

Entri yang rusak di dalam file dilewati dan disebutkan, tanpa menggagalkan impor. Hasil impor langsung ikut diperiksa
oleh cek sitasi. Kodenya ada di `impor_pustaka.py`, tanpa library tambahan.

## Cek sitasi

Setiap kutipan di isi bab dicocokkan dengan daftar pustaka, lalu aplikasi melaporkan dua hal:

- kutipan yang tidak punya entri di daftar pustaka, lengkap dengan lokasinya (mis. Bab II, subbab 2.1);
- entri daftar pustaka yang tidak pernah dikutip.

Bentuk yang dikenali: `(Santoso, 2021)`, `(Santoso & Putri, 2021)`, `Santoso dan Putri (2021)`, `(Santoso et al., 2021)`,
`Santoso dkk. (2021)`, `(Santoso, 2021, hlm. 5)`, `(Santoso, 2021a)`, `(Santoso, 2021; Putri, 2020)`, penulis lembaga
seperti `(Bank Indonesia, 2023)` atau `(BPS, 2023)`, dan `(Santoso, t.t.)`. Kolom Sumber pada gambar dan tabel ikut
diperiksa, kecuali yang berupa data sendiri ("Data primer diolah, 2026").

Hasilnya tampil di daftar hal yang perlu diperhatikan di tab **Preview** dan di bawah kotak Daftar pustaka di tab
**Pustaka & lampiran**. Aplikasi hanya melapor: isi bab dan daftar pustaka tidak pernah diubah otomatis. Singkatan
lembaga dicocokkan dengan huruf awal namanya, jadi `(BPS, 2023)` cocok dengan entri "Badan Pusat Statistik. (2023)".
Kodenya ada di `sitasi.py`.

## Preview (tab Preview)

Lihat hasilnya sebelum generate:
- **Kerangka**: setiap bab/subbab dengan jumlah paragraf & kata, sub-subbab, serta nomor final
  tabel/gambar (mis. "Tabel 4.1."). Subbab kosong ditandai 🔴.
- **Tampilan halaman**: tiruan lembar A4 dengan margin, font, spasi, dan penomoran yang sama dengan
  file Word. Garis putus-putus = batas margin; tulisan merah = belum diisi atau gambar belum diupload.
- Di atasnya ada daftar hal yang perlu diperhatikan (identitas kosong, intisari > 250 kata, pustaka < 10, dll.).

Catatan: pemotongan halaman dan nomor halaman yang pasti baru dihitung oleh Word, jadi di preview
setiap bab tampil sebagai satu lembar yang bisa memanjang.

## Penanda khusus di isi bab

| Tulis | Hasil |
|---|---|
| satu baris | satu paragraf (paragraf pertama rata kiri, berikutnya menjorok 1,25 cm) |
| `### Judul` | sub-subbab bernomor otomatis (1.1.1) |
| `1. ` / `a. ` / `(1) ` | perincian tingkat 1 / 2 / 3 |
| `*kata*` / `**kata**` | miring (istilah asing) / tebal |
| `[[GAMBAR: file.png \| Judul \| Sumber \| lebar_cm]]` | gambar + "Gambar 4.1. Judul" di bawahnya |
| `[[TABEL: Judul \| Sumber]]` … `[[/TABEL]]` | tabel + "Tabel 3.1. Judul" di atasnya; kolom dipisah `\|` |
| `[[RUMUS: Y = a + bX]]` | persamaan di tengah, nomor (1) di kanan |
| `[[REF: #label]]` | nomor gambar, tabel, atau rumus berlabel itu, mis. "Tabel 4.2" |

## Rujukan silang

Supaya kalimat seperti "ditunjukkan pada Tabel 4.2" tidak perlu dibetulkan setiap kali urutan tabel berubah, beri label
lalu rujuk labelnya:

| Penanda | Label | Hasil rujukan |
|---|---|---|
| `[[GAMBAR: grafik_penjualan.png \| Judul \| Sumber]]` | otomatis dari nama file: `#grafik_penjualan` | Gambar 4.1 |
| `[[GAMBAR: peta.png \| Judul \| Sumber \| 10 \| #lokasi]]` | argumen berawalan `#` | Gambar 4.2 |
| `[[TABEL: Judul \| Sumber \| #statistik]]` | argumen berawalan `#` | Tabel 4.2 |
| `[[RUMUS: Y = a + bX \| #regresi]]` | argumen berawalan `#` di ujung | Persamaan (3) |

Contoh: `Hasil uji ditunjukkan pada [[REF: #statistik]].` menjadi "Hasil uji ditunjukkan pada Tabel 4.2."

- Rujukan boleh mendahului yang dirujuk dan boleh antarbab.
- Label tidak ikut tercetak, dan penanda lama tanpa label hasilnya tidak berubah.
- Label yang tidak dikenal ditulis merah miring `[rujukan #label tidak ditemukan]` di Preview dan di file Word, dan
  masuk ke daftar hal yang perlu diperhatikan. Label yang dipakai dua kali juga dilaporkan.

Penomoran untuk rujukan dihitung di `rujukan.py`, dan dipakai oleh `generator.py` maupun `preview.py` supaya nomor di
Preview dan di Word selalu sama.

## Tabel dari Excel atau CSV (tab Bab)

Di tab **Bab**, buka **Sisipkan tabel dari Excel/CSV**:

1. Upload file `.xlsx` atau `.csv`, lalu klik **Baca file tabel**.
2. Pilih sheet, baris awal (menjadi header) dan baris akhir, isi judul dan sumber, lalu pilih subbab tujuannya.
3. Periksa pratinjaunya, lalu klik **Sisipkan ke subbab**. Tabel ditulis sebagai penanda `[[TABEL]]` di akhir subbab itu.

Yang perlu diketahui:

- Yang diambil dari Excel adalah nilai hasil rumus, bukan rumusnya. Sel gabungan diisi nilai sel kiri atasnya.
- Angka ditulis dengan format Indonesia: `1.250.000` dan `3,14`. Dalam satu kolom, jumlah angka di belakang koma
  dibuat sama. Kolom tahun tidak diberi pemisah ribuan. Hilangkan centang **Pakai koma untuk desimal** untuk format
  `1,250,000` dan `3.14`.
- CSV dengan pemisah koma maupun titik koma (bawaan Excel berbahasa Indonesia) dikenali sendiri.
- Karakter `|` di dalam sel diganti `/`, karena `|` memisahkan kolom di penanda.
- Tabel lebih dari 8 kolom atau 40 baris diberi peringatan karena kemungkinan tidak muat di A4 tegak.

Karena hasilnya teks biasa di isi subbab, tabel ini ikut tersimpan otomatis dan ikut di file progres. Kodenya ada di
`tabel_impor.py`, memakai library `openpyxl`.

## PDF pratinjau (tab Buat file Word)

Setelah file Word dibuat, tombol **Buat PDF pratinjau** mengubahnya menjadi PDF lewat LibreOffice, dengan daftar isi,
daftar tabel, dan daftar gambar yang sudah terisi. Tombol ini hanya muncul bila LibreOffice ada:

- **Di komputer sendiri:** pasang LibreOffice dari https://www.libreoffice.org.
- **Di Streamlit Community Cloud:** file `packages.txt` memasang `libreoffice-writer-nogui` dan `fonts-liberation`.

Ini PDF pratinjau, bukan pengganti PDF dari Word. Server Linux tidak punya Times New Roman, jadi dipakai Liberation
Serif yang ukurannya setara, dan pemotongan halamannya bisa sedikit berbeda. Untuk pengumpulan resmi, buka file
Word-nya lalu simpan sebagai PDF dari Word.

File sementara untuk konversi dibuat di folder sementara dan dihapus begitu konversi selesai atau gagal. Konversi
dibatasi 90 detik. Kodenya ada di `ekspor_pdf.py`.

## Aturan panduan yang sudah diterapkan otomatis

- A4, margin atas 4, kiri 4, kanan 3, bawah 3 cm (bisa disesuaikan di tab Format halaman); Times New Roman 12; spasi 1,5; rata kanan-kiri
- Spasi 1 untuk judul tabel/gambar, daftar isi/tabel/gambar/lampiran, intisari, abstract, daftar pustaka
- Judul bab di tengah, tebal, kapital; subbab rata kiri, tebal; huruf awal kapital kecuali kata sambung
- Nomor halaman: sampul tanpa nomor; bagian awal romawi kecil di tengah bawah; mulai Bab I angka Arab di kanan bawah
- Urutan bagian awal: Sampul, Pengesahan, Pernyataan Bebas Plagiasi, Kata Pengantar, Daftar Isi,
  Daftar Tabel/Gambar/Lampiran (jika ada), Daftar Istilah (jika ada), Intisari, Abstract (miring)
- Penomoran tabel & gambar per bab, judul tebal di tengah tanpa titik di akhir, sumber di bawah
- Header tabel diulang otomatis bila tabel berlanjut ke halaman berikutnya
- Kata kunci & daftar pustaka diurutkan abjad; peringatan bila intisari > 250 kata atau pustaka < 10

## Mengubah aturan format

Semua angka format ada di `FORMAT_DEB_SV_UGM` di bagian atas `generator.py`.
Untuk kampus lain, salin dict itu, ubah nilainya, lalu kirimkan sebagai argumen `fmt`.
