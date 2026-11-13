"""
Preview laporan sebelum di-generate.

- kerangka(data, gambar)        -> ringkasan struktur per bab/subbab (untuk dicek cepat)
- halaman_html(data, gambar, logo) -> HTML tiruan lembar A4 (margin, font, spasi, penomoran sama dengan .docx)

Aturan dan penanda diambil dari generator.py supaya penomoran tabel/gambar/rumus identik dengan hasil Word.
"""

import base64
import html
import re

from generator import (FORMAT_DEB_SV_UGM, RE_GAMBAR, RE_LIST1, RE_LIST2, RE_LIST3, RE_RUMUS, RE_TABEL_BUKA,
                       RE_TABEL_TUTUP, ROMAWI, format_dari, hitung_kata, jarak_footer_cm, judul_kapital,
                       urutkan_kata_kunci)


def romawi(n):
    return ROMAWI[n] if n < len(ROMAWI) else str(n)


# ---------------------------------------------------------------------------
# Pengurai isi subbab (sama persis dengan aturan di generator._isi_subbab)
# ---------------------------------------------------------------------------
def uraikan_isi(teks):
    baris = (teks or "").splitlines()
    i = 0
    while i < len(baris):
        b = baris[i].strip()
        i += 1
        if not b:
            continue
        if b.startswith("### "):
            yield ("subsub", b[4:])
            continue
        m = RE_GAMBAR.match(b)
        if m:
            bagian = [x.strip() for x in m.group(1).split("|")]
            bagian += [""] * (4 - len(bagian))
            yield ("gambar", bagian[:4])
            continue
        m = RE_TABEL_BUKA.match(b)
        if m:
            isi, tertutup = [], False
            while i < len(baris):
                if RE_TABEL_TUTUP.match(baris[i].strip()):
                    tertutup = True
                    i += 1
                    break
                if baris[i].strip():
                    isi.append(baris[i].strip())
                i += 1
            bagian = [x.strip() for x in m.group(1).split("|")] + [""]
            sel = [[c.strip() for c in r.strip().strip("|").split("|")] for r in isi]
            yield ("tabel", bagian[0], bagian[1], sel, tertutup)
            continue
        m = RE_RUMUS.match(b)
        if m:
            yield ("rumus", m.group(1).strip())
            continue
        for pola, lvl in ((RE_LIST3, 2), (RE_LIST1, 0), (RE_LIST2, 1)):
            m = pola.match(b)
            if m:
                yield ("list", lvl, b[: m.start(2)].strip(), m.group(2))
                break
        else:
            yield ("para", b)


# ---------------------------------------------------------------------------
# Kerangka
# ---------------------------------------------------------------------------
def kerangka(data, gambar=None):
    gambar = gambar or {}
    hasil, peringatan = [], []
    no_rumus = 0
    for bi, bab in enumerate(data.get("bab", []), start=1):
        n_tabel = n_gambar = 0
        subs = []
        for sj, sub in enumerate(bab.get("subbab", []), start=1):
            if not (sub.get("judul") or "").strip():
                continue
            info = {"no": f"{bi}.{sj}", "judul": judul_kapital(sub["judul"]), "paragraf": 0, "kata": 0,
                    "subsub": [], "tabel": [], "gambar": [], "rumus": 0}
            n_subsub = 0
            for el in uraikan_isi(sub.get("isi")):
                if el[0] in ("para", "list"):
                    info["paragraf"] += 1
                    info["kata"] += hitung_kata(el[-1])
                elif el[0] == "subsub":
                    n_subsub += 1
                    info["subsub"].append(f"{bi}.{sj}.{n_subsub} {judul_kapital(el[1])}")
                elif el[0] == "tabel":
                    n_tabel += 1
                    info["tabel"].append(f"Tabel {bi}.{n_tabel}. {el[1] or '(tanpa judul)'}")
                    if not el[4]:
                        peringatan.append(f"Tabel {bi}.{n_tabel} belum ditutup dengan [[/TABEL]].")
                elif el[0] == "gambar":
                    n_gambar += 1
                    ada = el[1][0] in gambar
                    info["gambar"].append(f"Gambar {bi}.{n_gambar}. {el[1][1] or '(tanpa judul)'}"
                                          + ("" if ada else " (file belum diupload)"))
                    if not ada:
                        peringatan.append(f"Gambar {bi}.{n_gambar} memakai file '{el[1][0]}' yang belum diupload.")
                elif el[0] == "rumus":
                    no_rumus += 1
                    info["rumus"] += 1
            if info["paragraf"] == 0 and not info["tabel"] and not info["gambar"]:
                peringatan.append(f"Subbab {bi}.{sj} {info['judul']} masih kosong.")
            subs.append(info)
        hasil.append({"judul": f"BAB {romawi(bi)} {(bab.get('judul') or '').upper()}", "subbab": subs})

    for k, nama in (("intisari", "Intisari"), ("abstract", "Abstract")):
        n = hitung_kata(data.get(k))
        if n == 0:
            peringatan.append(f"{nama} belum diisi.")
        elif n > 250:
            peringatan.append(f"{nama} {n} kata, melebihi batas 250 kata.")
    n_ref = len([b for b in (data.get("daftar_pustaka") or "").splitlines() if b.strip()])
    if n_ref < 10:
        peringatan.append(f"Daftar pustaka {n_ref} entri (panduan: minimal 10 artikel jurnal).")
    for k, nama in (("judul_id", "Judul"), ("nama", "Nama"), ("nim", "NIM"), ("prodi", "Program studi"),
                    ("pembimbing", "Dosen pembimbing")):
        if not (data.get("identitas", {}).get(k) or "").strip():
            peringatan.append(f"{nama} di tab Identitas belum diisi.")
    return hasil, peringatan


# ---------------------------------------------------------------------------
# Tampilan halaman (HTML)
# ---------------------------------------------------------------------------
def _inline(teks):
    t = html.escape(teks or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
    return t


def _ph(teks):
    return f'<span class="ph">{html.escape(teks)}</span>'


def _img(data, gaya=""):
    if data[:4] == b"\x89PNG":
        mime = "image/png"
    elif data[:3] == b"GIF":
        mime = "image/gif"
    else:
        mime = "image/jpeg"
    return f'<img src="data:{mime};base64,{base64.b64encode(data).decode()}" style="{gaya}">'


class PreviewHTML:
    def __init__(self, data, gambar=None, logo=None, fmt=FORMAT_DEB_SV_UGM):
        self.d = data
        self.id = data.get("identitas", {})
        self.pg = data.get("pengesahan", {})
        self.gambar = gambar or {}
        self.logo = logo
        self.f = fmt
        self.lebar = fmt["kertas_lebar_cm"] - fmt["margin_kiri_cm"] - fmt["margin_kanan_cm"]
        self.halaman = []
        self.daftar_tabel, self.daftar_gambar = [], []
        self.no_rumus = 0

    def lembar(self, label, isi, nomor=""):
        self.halaman.append((label, isi, nomor))

    def para(self, teks, pertama=False, kelas=""):
        indent = "0" if pertama else f"{self.f['indent_paragraf_cm']}cm"
        return f'<p class="p {kelas}" style="text-indent:{indent}">{_inline(teks)}</p>'

    def paragraf_bebas(self, teks, kelas=""):
        baris = [b.strip() for b in (teks or "").splitlines() if b.strip()]
        return "".join(self.para(b, i == 0, kelas) for i, b in enumerate(baris))

    # ----- bagian awal -----
    def sampul(self):
        i = self.id
        logo = (_img(self.logo, f"width:{self.f['lebar_logo_cm']}cm;height:{self.f['tinggi_logo_cm']}cm")
                if self.logo else '<div class="logo-ph">Lambang UGM<br>5,5 × 5,71 cm<br>(belum diupload)</div>')
        isi = f"""
        <div class="c" style="line-height:1.15">
          <p class="b" style="font-size:14pt;margin-bottom:22pt">TUGAS AKHIR</p>
          <p class="b" style="font-size:14pt">{html.escape((i.get('judul_id') or '').upper()) or _ph('[JUDUL TUGAS AKHIR]')}</p>
          <p class="b i" style="margin:4pt 0 44pt">{html.escape((i.get('judul_en') or '').upper()) or _ph('[JUDUL BAHASA INGGRIS]')}</p>
          <p style="margin-bottom:18pt">Disusun untuk memenuhi persyaratan mencapai gelar Sarjana Terapan</p>
          <p>Dosen Pembimbing</p>
          <p style="margin-bottom:32pt">{html.escape(i.get('pembimbing') or '') or _ph('[Nama Dosen Pembimbing]')}</p>
          <div style="margin-bottom:32pt">{logo}</div>
          <p>Oleh:</p>
          <p class="b">{html.escape(judul_kapital(i.get('nama') or '')) or _ph('[Nama Mahasiswa]')}</p>
          <p style="margin-bottom:60pt">{html.escape(i.get('nim') or '') or _ph('[NIM]')}</p>
          <p class="b">{html.escape((i.get('prodi') or '').upper()) or _ph('[NAMA PROGRAM STUDI]')}</p>
          {''.join(f'<p class="b">{x}</p>' for x in self.f['institusi'])}
          <p class="b">{html.escape(str(i.get('tahun') or '')) or _ph('[TAHUN]')}</p>
        </div>"""
        self.lembar("Sampul <span class=\"ket\">tanpa nomor halaman</span>", isi)

    def _ttd(self, jabatan, nama, nip):
        return (f'<div class="c ttd">{"<br>".join(jabatan)}<div style="height:44pt"></div>'
                f'<b>{html.escape(nama or "") or _ph("[Nama Lengkap]")}</b><br>'
                f'{("NIP/NIKA " + html.escape(nip)) if nip else _ph("[NIP/NIKA]")}</div>')

    def pengesahan(self):
        i, g = self.id, self.pg
        isi = f"""
        <h1>HALAMAN PENGESAHAN</h1>
        <div class="c" style="line-height:1.2">
          <p class="b">TUGAS AKHIR</p>
          <p class="b" style="margin-bottom:14pt">{html.escape(i.get('judul_id') or '') or _ph('[Judul]')}</p>
          <p>Disusun oleh:</p>
          <p class="b">{html.escape(judul_kapital(i.get('nama') or '')) or _ph('[Nama]')}</p>
          <p style="margin-bottom:14pt">{html.escape(i.get('nim') or '') or _ph('[NIM]')}</p>
          <p>Telah diujikan dan diseminarkan</p>
          <p style="margin-bottom:14pt">pada tanggal {html.escape(g.get('tanggal_ujian') or '') or _ph('[tanggal]')}</p>
        </div>
        <div style="display:flex;justify-content:space-around;line-height:1.2">
          {self._ttd(['Penguji I/', 'Ketua Penguji'], g.get('ketua_nama'), g.get('ketua_nip'))}
          {self._ttd(['Penguji II/Sekretaris Penguji/', 'Dosen Pembimbing Tugas Akhir'], i.get('pembimbing'), g.get('pembimbing_nip'))}
        </div>
        <div style="line-height:1.2;margin-top:10pt">{self._ttd(['Penguji III/', 'Anggota Penguji'], g.get('anggota_nama'), g.get('anggota_nip'))}</div>
        <div class="c" style="line-height:1.2;margin-top:10pt">Mengetahui,<br>
          {html.escape(g.get('mengetahui_jabatan') or ('Ketua Program Studi ' + (i.get('prodi') or '[prodi]')))}<br>
          Sekolah Vokasi Universitas Gadjah Mada<div style="height:44pt"></div>
          <b>{html.escape(g.get('mengetahui_nama') or '') or _ph('[Nama Lengkap]')}</b><br>
          {('NIP/NIKA ' + html.escape(g['mengetahui_nip'])) if g.get('mengetahui_nip') else _ph('[NIP/NIKA]')}
        </div>"""
        self.lembar("Halaman Pengesahan", isi, "i")

    def pernyataan(self):
        i = self.id
        baris = [("Nama", judul_kapital(i.get("nama") or "")), ("NIM", i.get("nim")),
                 ("Tahun terdaftar", i.get("tahun_terdaftar")), ("Program studi", i.get("prodi")),
                 ("Fakultas/Sekolah", i.get("fakultas") or "Sekolah Vokasi")]
        tabel = "".join(f'<tr><td style="width:4cm">{k}</td><td>: {html.escape(str(v or "")) or _ph("[...]")}</td></tr>'
                        for k, v in baris)
        isi = f"""<h1>PERNYATAAN BEBAS PLAGIASI</h1>
        <p class="p">Saya yang bertanda tangan di bawah ini:</p>
        <table class="plain">{tabel}</table>
        <p class="p" style="margin-top:8pt">Menyatakan bahwa dalam dokumen ilmiah Tugas Akhir ini tidak terdapat bagian dari karya ilmiah lain … (teks pernyataan baku)</p>
        <div style="text-align:right;line-height:1.2;margin-top:20pt">
          {html.escape(i.get('tempat_ttd') or 'Yogyakarta')}, {html.escape(i.get('tanggal_ttd') or '') or _ph('[tanggal]')}<br>
          <span style="color:#888">Materai Rp 10.000,00</span><div style="height:30pt"></div>
          <b>{html.escape(judul_kapital(i.get('nama') or '')) or _ph('[Nama]')}</b><br>{html.escape(i.get('nim') or '')}
        </div>"""
        self.lembar("Pernyataan Bebas Plagiasi", isi, "ii")

    def kata_pengantar(self):
        teks = self.d.get("kata_pengantar")
        isi = "<h1>KATA PENGANTAR</h1>" + (self.paragraf_bebas(teks) if (teks or "").strip()
                                             else f'<p>{_ph("[Kata pengantar belum ditulis]")}</p>')
        isi += '<div style="text-align:right;line-height:1.2;margin-top:20pt">Penulis</div>'
        self.lembar("Kata Pengantar", isi, "iii")

    def daftar(self, judul, entri, label):
        baris = "".join(
            f'<div class="toc" style="padding-left:{ind}cm"><span>{html.escape(t)}</span><span class="dots"></span><span class="pg">#</span></div>'
            for t, ind in entri) or f'<p>{_ph("(kosong)")}</p>'
        self.lembar(label, f"<h1>{judul}</h1>{baris}<p class='note'># nomor halaman diisi otomatis oleh Word</p>")

    def intisari_abstract(self):
        for kunci, judul, kk, label_kk, miring in (("intisari", "INTISARI", "kata_kunci", "Kata kunci", False),
                                                   ("abstract", "ABSTRACT", "keywords", "Keywords", True)):
            teks = self.d.get(kunci) or ""
            n = hitung_kata(teks)
            badge = f'<span class="{"bad" if n > 250 else "ok"}">{n}/250 kata</span>'
            isi = f"<h1>{judul}</h1>"
            isi += self.paragraf_bebas(teks, "rapat" + (" i" if miring else "")) if teks.strip() else f"<p>{_ph('[belum diisi]')}</p>"
            kunci_urut = urutkan_kata_kunci(self.d.get(kk))
            isi += (f'<p class="rapat {"i" if miring else ""}" style="margin-top:12pt"><b>{label_kk}:</b> '
                    f'{html.escape(kunci_urut) or _ph("[belum diisi]")}</p>')
            self.lembar(f"{judul.title()} {badge}", isi)

    # ----- bab -----
    def bab(self, no, bab):
        out = [f"<h1>BAB {romawi(no)} {html.escape((bab.get('judul') or '').upper())}</h1>"]
        n_tabel = n_gambar = 0
        for sj, sub in enumerate(bab.get("subbab", []), start=1):
            if not (sub.get("judul") or "").strip():
                continue
            out.append(f'<h2>{no}.{sj} {html.escape(judul_kapital(sub["judul"]))}</h2>')
            pertama, n_subsub, kosong = True, 0, True
            for el in uraikan_isi(sub.get("isi")):
                kosong = False
                if el[0] == "subsub":
                    n_subsub += 1
                    out.append(f'<h3>{no}.{sj}.{n_subsub} {html.escape(judul_kapital(el[1]))}</h3>')
                    pertama = True
                elif el[0] == "para":
                    out.append(self.para(el[1], pertama))
                    pertama = False
                elif el[0] == "list":
                    kiri = [0.63, 1.27, 1.9][el[1]]
                    out.append(f'<div class="li" style="padding-left:{kiri + 0.63}cm"><span class="mk">{html.escape(el[2])}</span>{_inline(el[3])}</div>')
                elif el[0] == "rumus":
                    self.no_rumus += 1
                    out.append(f'<div class="eq"><span></span><span>{_inline(el[1])}</span><span>({self.no_rumus})</span></div>')
                    pertama = False
                elif el[0] == "tabel":
                    n_tabel += 1
                    judul, sumber, sel, tertutup = el[1], el[2], el[3], el[4]
                    self.daftar_tabel.append(f"Tabel {no}.{n_tabel}. {judul}")
                    n_kol = max([len(r) for r in sel] or [1])
                    rows = ""
                    for ri, r in enumerate(sel or [["(tabel kosong)"]]):
                        tag = "th" if ri == 0 else "td"
                        rows += "<tr>" + "".join(f"<{tag}>{_inline(r[c] if c < len(r) else '')}</{tag}>" for c in range(n_kol)) + "</tr>"
                    out.append(f'<p class="cap">Tabel {no}.{n_tabel}. {_inline(judul.rstrip("."))}</p><table class="grid">{rows}</table>')
                    if sumber:
                        out.append(f'<p class="src">Sumber: {_inline(sumber)}</p>')
                    if not tertutup:
                        out.append(f'<p>{_ph("Tabel ini belum ditutup dengan [[/TABEL]]")}</p>')
                    pertama = False
                elif el[0] == "gambar":
                    n_gambar += 1
                    nama, judul, sumber, lebar = el[1]
                    try:
                        lebar = min(float(lebar.replace(",", ".")) if lebar else 12.0, self.lebar)
                    except ValueError:
                        lebar = 12.0
                    self.daftar_gambar.append(f"Gambar {no}.{n_gambar}. {judul}")
                    data = self.gambar.get(nama)
                    gbr = _img(data, f"width:{lebar}cm") if data else (
                        f'<div class="img-ph" style="width:{lebar}cm">Gambar “{html.escape(nama)}” belum diupload</div>')
                    out.append(f'<div class="fig">{gbr}</div><p class="cap" style="margin-top:4pt">Gambar {no}.{n_gambar}. {_inline(judul.rstrip("."))}</p>')
                    out.append(f'<p class="src c">Sumber: {_inline(sumber)}</p>' if sumber else '<div style="height:8pt"></div>')
                    pertama = False
            if kosong:
                out.append(f'<p>{_ph("[Isi subbab ini belum ditulis]")}</p>')
        self.lembar(f"Bab {romawi(no)} <span class=\"ket\">bisa lebih dari satu halaman</span>", "".join(out), "")

    def pustaka(self):
        entri = [b.strip() for b in (self.d.get("daftar_pustaka") or "").splitlines() if b.strip()]
        entri.sort(key=lambda s: re.sub(r"[^a-z0-9]", "", s.lower()))
        isi = "<h1>DAFTAR PUSTAKA</h1>" + ("".join(f'<p class="ref">{_inline(e)}</p>' for e in entri)
                                            or f"<p>{_ph('[Daftar pustaka belum diisi]')}</p>")
        self.lembar(f"Daftar Pustaka <span class=\"ket\">{len(entri)} entri, diurutkan abjad</span>", isi)

    def lampiran(self):
        daftar = [l for l in self.d.get("lampiran", []) if (l.get("judul") or "").strip()]
        if not daftar:
            return []
        out = ["<h1>LAMPIRAN</h1>"]
        for k, l in enumerate(daftar, start=1):
            out.append(f'<p class="lamp">Lampiran {k}. {html.escape(judul_kapital(l["judul"]))}</p>')
            out.append(self.paragraf_bebas(l.get("isi")))
            nama = (l.get("gambar") or "").strip()
            if nama:
                data = self.gambar.get(nama)
                out.append(f'<div class="fig">{_img(data, f"width:{self.lebar}cm") if data else _ph("gambar belum diupload")}</div>')
        self.lembar("Lampiran", "".join(out))
        return [f"Lampiran {k}. {judul_kapital(l['judul'])}" for k, l in enumerate(daftar, start=1)]

    # ----- rakit -----
    def bangun(self, zoom=0.75):
        self.sampul()
        self.pengesahan()
        self.pernyataan()
        self.kata_pengantar()
        idx_daftar = len(self.halaman)

        bab_html_awal = len(self.halaman)
        for no, b in enumerate(self.d.get("bab", []), start=1):
            self.bab(no, b)
        bab_pages = self.halaman[bab_html_awal:]
        del self.halaman[bab_html_awal:]
        self.pustaka()
        akhir = self.halaman[bab_html_awal:]
        del self.halaman[bab_html_awal:]
        daftar_lamp = self.lampiran()
        akhir += self.halaman[bab_html_awal:]
        del self.halaman[bab_html_awal:]

        # Daftar isi dibuat dari struktur
        toc = [("HALAMAN PENGESAHAN", 0), ("PERNYATAAN BEBAS PLAGIASI", 0), ("KATA PENGANTAR", 0), ("DAFTAR ISI", 0)]
        if self.daftar_tabel:
            toc.append(("DAFTAR TABEL", 0))
        if self.daftar_gambar:
            toc.append(("DAFTAR GAMBAR", 0))
        if daftar_lamp:
            toc.append(("DAFTAR LAMPIRAN", 0))
        if (self.d.get("istilah") or "").strip():
            toc.append(("DAFTAR ISTILAH", 0))
        toc += [("INTISARI", 0), ("ABSTRACT", 0)]
        for no, b in enumerate(self.d.get("bab", []), start=1):
            toc.append((f"BAB {romawi(no)} {(b.get('judul') or '').upper()}", 0))
            for sj, s in enumerate(b.get("subbab", []), start=1):
                if (s.get("judul") or "").strip():
                    toc.append((f"{no}.{sj} {judul_kapital(s['judul'])}", 0.63))
                    n3 = 0
                    for el in uraikan_isi(s.get("isi")):
                        if el[0] == "subsub":
                            n3 += 1
                            toc.append((f"{no}.{sj}.{n3} {judul_kapital(el[1])}", 1.27))
        toc.append(("DAFTAR PUSTAKA", 0))
        if daftar_lamp:
            toc.append(("LAMPIRAN", 0))

        sisip = []
        self.halaman, simpan = [], self.halaman
        self.daftar("DAFTAR ISI", toc, "Daftar Isi")
        if self.daftar_tabel:
            self.daftar("DAFTAR TABEL", [(t, 0) for t in self.daftar_tabel], "Daftar Tabel")
        if self.daftar_gambar:
            self.daftar("DAFTAR GAMBAR", [(t, 0) for t in self.daftar_gambar], "Daftar Gambar")
        if daftar_lamp:
            self.daftar("DAFTAR LAMPIRAN", [(t, 0) for t in daftar_lamp], "Daftar Lampiran")
        istilah = [b for b in (self.d.get("istilah") or "").splitlines() if b.strip()]
        if istilah:
            pasang = sorted(((b.split(":", 1) + [""])[:2] for b in istilah), key=lambda x: x[0].strip().lower())
            isi = "<h1>DAFTAR ISTILAH</h1>" + "".join(
                f'<div class="rapat" style="display:flex"><i style="width:4.5cm;flex:none">{html.escape(k.strip())}</i>: {html.escape(v.strip())}</div>'
                for k, v in pasang)
            self.lembar("Daftar Istilah", isi)
        self.intisari_abstract()
        sisip = self.halaman
        self.halaman = simpan[:idx_daftar] + sisip + bab_pages + akhir

        # nomor romawi untuk bagian awal
        lembar_html = []
        for idx, (label, isi, _) in enumerate(self.halaman):
            if idx == 0:
                kaki = ""
            elif label.startswith(("Bab ", "Daftar Pustaka", "Lampiran")):
                kaki = '<div class="foot r">nomor halaman, angka Arab</div>'
            else:
                kaki = '<div class="foot g">nomor halaman, romawi kecil</div>'
            lembar_html.append(f'<div class="label">{label}</div><div class="page">{isi}{kaki}</div>')
        return self._bungkus("".join(lembar_html), zoom)

    def _bungkus(self, isi, zoom):
        f = self.f
        meja, tinta, redup, merah = (("#14161D", "#E8EAF0", "#A8AEBF", "#F4978E") if getattr(self, "gelap", False)
                                     else ("#ECEEF3", "#1B1F2E", "#5E6477", "#B3261E"))
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body {{ background:{meja}; margin:0; padding:4px 0 24px; font-family:"Avenir Next","Segoe UI",system-ui,sans-serif; }}
        .wrap {{ zoom:{zoom}; display:flex; flex-direction:column; align-items:center; }}
        .label {{ font: 600 17px "Avenir Next","Segoe UI",system-ui,sans-serif; color:{tinta}; margin:26px 0 8px; width:{f['kertas_lebar_cm']}cm; }}
        .label .ket {{ font-weight:400; color:{redup}; margin-left:8px; }}
        .label .bad, .label .ok {{ font-weight:500; margin-left:8px; font-variant-numeric:tabular-nums; }}
        .label .bad {{ color:{merah}; }} .label .ok {{ color:{redup}; }}
        .page {{ box-sizing:border-box; background:#fff; width:{f['kertas_lebar_cm']}cm; min-height:{f['kertas_tinggi_cm']}cm;
                 padding:{f['margin_atas_cm']}cm {f['margin_kanan_cm']}cm {f['margin_bawah_cm']}cm {f['margin_kiri_cm']}cm;
                 border:1px solid #D5D8E0; box-shadow:0 2px 0 #D5D8E0; position:relative;
                 font-family:"{f['font']}", "Times New Roman", Times, serif; font-size:{f['ukuran_font']}pt;
                 line-height:{f['spasi_isi']}; text-align:justify; color:#000; }}
        .page::before {{ content:""; position:absolute; pointer-events:none;
                 top:{f['margin_atas_cm']}cm; bottom:{f['margin_bawah_cm']}cm; left:{f['margin_kiri_cm']}cm; right:{f['margin_kanan_cm']}cm;
                 border:1px dashed rgba(74,58,167,.38); }}
        .foot {{ position:absolute; bottom:{jarak_footer_cm(f)}cm; left:0; right:0; text-align:center; font-size:12pt; }}
        .foot.g, .foot.r {{ color:#8A90A2; font-size:10pt; font-family:"Avenir Next","Segoe UI",system-ui,sans-serif; }}
        .foot.r {{ text-align:right; right:{f['margin_kanan_cm']}cm; }}
        p {{ margin:0; }}
        h1 {{ font-size:12pt; text-align:center; font-weight:bold; text-transform:uppercase; margin:0 0 24pt; }}
        h2 {{ font-size:12pt; font-weight:bold; text-align:left; margin:12pt 0 0; }}
        h3 {{ font-size:12pt; font-weight:bold; text-align:left; margin:6pt 0 0; }}
        .c {{ text-align:center; }} .b {{ font-weight:bold; }} .i {{ font-style:italic; }}
        .rapat {{ line-height:1; margin-bottom:0; }}
        .li {{ text-indent:-0.63cm; }} .li .mk {{ display:inline-block; width:0.63cm; text-indent:0; }}
        .eq {{ display:flex; justify-content:space-between; margin:6pt 0; }} .eq span:first-child {{ width:1cm; }}
        .cap {{ text-align:center; font-weight:bold; line-height:1; margin:12pt 0 6pt; }}
        .src {{ line-height:1; margin:3pt 0 12pt; text-align:left; }} .src.c {{ text-align:center; }}
        .fig {{ text-align:center; margin-top:12pt; line-height:1; }}
        table.grid {{ border-collapse:collapse; margin:0 auto; width:100%; line-height:1; text-align:left; }}
        table.grid th, table.grid td {{ border:1px solid #000; padding:1px 4px; }} table.grid th {{ text-align:center; }}
        table.plain td {{ padding:0; vertical-align:top; }}
        .ttd {{ margin:0 auto; }}
        .toc {{ display:flex; line-height:1; margin-bottom:4pt; text-align:left; }}
        .toc .dots {{ flex:1; border-bottom:1px dotted #000; margin:0 3px 4px; }} .toc .pg {{ color:#999; }}
        .note {{ font: 11px "Avenir Next","Segoe UI",system-ui,sans-serif; color:#8A90A2; margin-top:12pt; }}
        .ref {{ line-height:1; padding-left:1.27cm; text-indent:-1.27cm; margin-bottom:6pt; text-align:left; }}
        .lamp {{ font-weight:bold; margin:12pt 0; text-align:left; }}
        .ph {{ color:#B3261E; font-style:italic; background:#FCEEEC; }}
        .logo-ph, .img-ph {{ display:inline-flex; align-items:center; justify-content:center; text-align:center;
                 border:1.5px dashed #B3261E; color:#B3261E; font: italic 11pt sans-serif; background:#FCEEEC; }}
        .logo-ph {{ width:{f['lebar_logo_cm']}cm; height:{f['tinggi_logo_cm']}cm; line-height:1.4; }}
        .img-ph {{ height:4cm; }}
        </style></head><body><div class="wrap">{isi}</div></body></html>"""


def halaman_html(data, gambar=None, logo=None, zoom=0.75, fmt=None, gelap=False):
    """gelap hanya menggelapkan meja di sekeliling lembar; lembarnya tetap putih seperti kertas hasil cetak."""
    pratinjau = PreviewHTML(data, gambar, logo, fmt or format_dari(data))
    pratinjau.gelap = gelap
    return pratinjau.bangun(zoom)
