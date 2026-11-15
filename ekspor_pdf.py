"""
Ekspor PDF pratinjau: file .docx diubah ke PDF oleh LibreOffice.

- cari_soffice()        -> jalur program LibreOffice, atau None
- tersedia()            -> True bila LibreOffice ada
- ke_pdf(docx_bytes)    -> pdf_bytes; melempar GagalPdf dengan pesan siap tampil

Kenapa tidak cukup `soffice --convert-to pdf`: daftar isi, daftar tabel, dan daftar gambar di file Word adalah field
yang baru terisi saat dibuka. Konversi langsung menghasilkan daftar kosong. Jadi LibreOffice dijalankan dengan profil
sementara yang sudah berisi satu makro Basic: buka dokumen, perbarui semua indeks, ekspor PDF, lalu keluar.

Makro dipilih, bukan skrip Python UNO, karena tidak butuh Python milik LibreOffice (yang di macOS tidak bisa
dijalankan dari luar aplikasinya) dan tidak butuh paket python3-uno di server.

Semua file sementara, termasuk profil LibreOffice, ada di satu folder tempfile yang dihapus setelah konversi,
berhasil atau gagal. Profil sementara juga membuat pemakaian bersamaan tidak saling bentrok.
"""

import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

MAC_SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")


class GagalPdf(Exception):
    """Pesannya sudah siap ditampilkan ke pengguna."""


def cari_soffice():
    for nama in ("soffice", "libreoffice"):
        jalur = shutil.which(nama)
        if jalur:
            return jalur
    return str(MAC_SOFFICE) if MAC_SOFFICE.exists() else None


def tersedia():
    return cari_soffice() is not None


# Makro yang ditaruh di profil sementara. Dipanggil sebagai macro:///Standard.Module1.KePdf("masuk", "keluar").
MAKRO = '''Sub KePdf(masuk As String, keluar As String)
    Dim buka(0) As New com.sun.star.beans.PropertyValue
    Dim simpan(0) As New com.sun.star.beans.PropertyValue
    Dim dok As Object, indeks As Object
    Dim putaran As Integer, i As Integer
    On Error GoTo Selesai
    buka(0).Name = "Hidden"
    buka(0).Value = True
    dok = StarDesktop.loadComponentFromURL(ConvertToURL(masuk), "_blank", 0, buka())
    indeks = dok.getDocumentIndexes()
    For putaran = 1 To 2
        For i = 0 To indeks.getCount() - 1
            indeks.getByIndex(i).update()
        Next i
    Next putaran
    dok.getTextFields().refresh()
    simpan(0).Name = "FilterName"
    simpan(0).Value = "writer_pdf_Export"
    dok.storeToURL(ConvertToURL(keluar), simpan())
    dok.close(True)
Selesai:
    StarDesktop.terminate()
End Sub
'''

def _modul_makro():
    from xml.sax.saxutils import escape
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">\n'
            '<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" '
            f'script:language="StarBasic">{escape(MAKRO)}</script:module>\n')


def _opsi(profil):
    return ["--headless", "--invisible", "--norestore", "--nologo", "--nodefault", "--nolockcheck",
            f"-env:UserInstallation={profil.as_uri()}"]


def _siapkan_profil(soffice, profil, batas_detik):
    """Biarkan LibreOffice membuat profilnya dulu, baru makro ditaruh.

    Saat profil dibuat, LibreOffice menyalin pustaka makro bawaannya (Standard/Module1) dan menimpa apa pun yang
    sudah ada di sana. Jadi makro ditulis sesudahnya, menggantikan isi Module1 yang memang sudah terdaftar.
    """
    subprocess.run([soffice, *_opsi(profil), "--terminate_after_init"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=batas_detik, check=False)
    modul = profil / "user" / "basic" / "Standard" / "Module1.xba"
    if not modul.parent.exists():
        raise GagalPdf("LibreOffice tidak bisa menyiapkan profil sementaranya. Simpan sebagai PDF dari Word.")
    modul.write_text(_modul_makro(), encoding="utf-8")


def ke_pdf(docx_bytes, batas_detik=90):
    soffice = cari_soffice()
    if not soffice:
        raise GagalPdf("LibreOffice tidak ditemukan, jadi PDF tidak bisa dibuat di sini. "
                       "Buka file Word-nya, lalu simpan sebagai PDF dari Word.")
    with tempfile.TemporaryDirectory(prefix="ta_pdf_") as folder:     # dihapus begitu blok ini selesai
        folder = Path(folder).resolve()
        masuk, keluar, profil = folder / "laporan.docx", folder / "laporan.pdf", folder / "profil"
        masuk.write_bytes(docx_bytes)
        try:
            _siapkan_profil(soffice, profil, batas_detik)
        except subprocess.TimeoutExpired:
            raise GagalPdf(f"LibreOffice tidak siap dalam {batas_detik} detik. Coba lagi, atau simpan sebagai PDF "
                           "dari Word.") from None
        perintah = [soffice, *_opsi(profil), f'macro:///Standard.Module1.KePdf("{masuk}","{keluar}")']
        proses = subprocess.Popen(perintah, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  start_new_session=(os.name == "posix"))
        try:
            _, galat = proses.communicate(timeout=batas_detik)
        except subprocess.TimeoutExpired:
            _hentikan(proses)
            raise GagalPdf(f"Pembuatan PDF melebihi {batas_detik} detik lalu dihentikan. Coba lagi, atau simpan "
                           "sebagai PDF dari Word.") from None
        if not keluar.exists() or keluar.stat().st_size == 0:
            rinci = (galat or b"").decode("utf-8", "replace").strip().splitlines()[-1:]
            raise GagalPdf("LibreOffice gagal mengubah file ini ke PDF. Simpan sebagai PDF dari Word."
                           + (f" (Rincian: {rinci[0][:200]})" if rinci else ""))
        return keluar.read_bytes()


def _hentikan(proses):
    """Matikan LibreOffice beserta proses anaknya."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proses.pid), signal.SIGKILL)
        else:
            proses.kill()
    except (OSError, ProcessLookupError):
        pass
    try:
        proses.communicate(timeout=5)
    except Exception:
        pass
