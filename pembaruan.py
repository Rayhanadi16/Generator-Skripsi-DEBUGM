"""
Riwayat pembaruan yang ditampilkan di jendela "Yang baru".

Menulis pengumuman baru: tambahkan satu entri di PALING ATAS daftar PEMBARUAN.
Poin ditulis dalam bahasa pengunjung: apa yang sekarang bisa mereka lakukan, bukan istilah teknis.
"""

from datetime import date

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
         "Oktober", "November", "Desember"]

PEMBARUAN = [
    {
        "versi": "1.7",
        "tanggal": date(2026, 11, 15),
        "judul": "PDF pratinjau",
        "poin": [
            "Setelah file Word dibuat, kamu bisa langsung membuat PDF pratinjau untuk dikirim ke pembimbing.",
            "Untuk pengumpulan resmi tetap simpan PDF dari Word, karena pemotongan halamannya bisa sedikit berbeda.",
        ],
    },
    {
        "versi": "1.6",
        "tanggal": date(2026, 11, 15),
        "judul": "Rujukan silang otomatis",
        "poin": [
            "Tulis [[REF: #label]] di kalimat, dan aplikasi menggantinya dengan nomor yang benar, misalnya Tabel 4.2.",
            "Nomornya ikut berubah sendiri kalau kamu menambah atau memindahkan tabel, gambar, atau rumus.",
        ],
    },
    {
        "versi": "1.5",
        "tanggal": date(2026, 11, 14),
        "judul": "Tabel dari Excel atau CSV",
        "poin": [
            "Tabel hasil olah data bisa langsung disisipkan dari file .xlsx atau .csv lewat tab Bab, tanpa mengetik ulang.",
            "Angka ditulis dengan format Indonesia (1.250.000 dan 3,14), dan tabelnya masih bisa disunting sesudahnya.",
        ],
    },
    {
        "versi": "1.4",
        "tanggal": date(2026, 11, 14),
        "judul": "Impor pustaka dari Zotero atau Mendeley",
        "poin": [
            "Daftar pustaka bisa diisi sekaligus dari file .bib atau .ris hasil ekspor Zotero atau Mendeley.",
            "Kamu memilih dulu referensi mana yang dipakai, dan yang sudah ada tidak ditambahkan dua kali.",
        ],
    },
    {
        "versi": "1.3",
        "tanggal": date(2026, 11, 14),
        "judul": "Cek sitasi",
        "poin": [
            "Kutipan di isi bab sekarang dicocokkan dengan daftar pustaka. Kutipan yang belum punya entri dan "
            "entri yang tidak pernah dikutip muncul di tab Preview dan tab Pustaka & lampiran.",
            "Sumber pada gambar dan tabel ikut diperiksa.",
        ],
    },
    {
        "versi": "1.2",
        "tanggal": date(2026, 11, 13),
        "judul": "Simpan otomatis di browser",
        "poin": [
            "Isian, gambar, dan logo sekarang tersimpan otomatis di perangkatmu sendiri, jadi bisa dilanjutkan "
            "saat aplikasi dibuka lagi di browser yang sama.",
            "Ada tombol Hapus simpanan di perangkat ini, untuk dipakai di komputer bersama.",
        ],
    },
    {
        "versi": "1.1",
        "tanggal": date(2026, 11, 13),
        "judul": "Tampilan baru",
        "poin": [
            "Tampilan lebih rapi di ponsel, dan ada mode gelap lewat tombol di pojok kanan atas.",
            "Preview halaman ikut menyesuaikan mode gelap.",
            "Pengambilan rincian referensi dari DOI atau PDF jurnal sudah diperbaiki.",
        ],
    },
    {
        "versi": "1.0",
        "tanggal": date(2026, 11, 11),
        "judul": "Versi web pertama",
        "poin": ["Generator laporan tugas akhir bisa dipakai langsung dari browser."],
    },
]

VERSI = PEMBARUAN[0]["versi"]


def tanggal_teks(tanggal):
    return f"{tanggal.day} {BULAN[tanggal.month - 1]} {tanggal.year}"
