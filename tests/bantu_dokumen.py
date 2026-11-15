"""Teks seluruh dokumen (paragraf dan sel tabel, urut kemunculan) untuk membandingkan hasil sebelum dan sesudah."""
import io

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph


def teks_dokumen(docx_bytes):
    dok = docx.Document(io.BytesIO(docx_bytes))
    baris = []
    for el in dok.element.body.iterchildren():
        if el.tag.endswith("}p"):
            baris.append(Paragraph(el, dok).text)
        elif el.tag.endswith("}tbl"):
            for r in Table(el, dok).rows:
                baris.append(" | ".join(c.text for c in r.cells))
    return "\n".join(baris)
