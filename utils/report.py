"""Exportação de relatórios em CSV e PDF (RF-06).

`report` = {"title": str, "inputs": [(rótulo, valor)], "steps": [...], "results": [...]}
`meta`   = rastreabilidade {rótulo: valor} (amostra, analista, lote, data/hora).
"""
import csv
import http.client
import io
import urllib.request

# ponytail: no navegador (stlite/Pyodide) não há ssl, então as classes HTTPS não existem
# e o import do fpdf2 quebra. O fpdf2 só usa isso para imagens por URL, que não usamos.
if not hasattr(http.client, "HTTPSConnection"):
    http.client.HTTPSConnection = http.client.HTTPConnection
if not hasattr(urllib.request, "HTTPSHandler"):
    urllib.request.HTTPSHandler = urllib.request.HTTPHandler

from fpdf import FPDF  # noqa: E402

SECTIONS = [("inputs", "Entradas"), ("steps", "Etapas do cálculo"), ("results", "Resultado")]


def to_csv(report, meta):
    """CSV com ';' (vírgula é o decimal no Excel pt-BR) e BOM para os acentos abrirem certo."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Seção", "Item", "Valor"])
    w.writerow(["Análise", "Cálculo", report["title"]])
    w.writerows(["Rastreabilidade", k, v] for k, v in meta.items())
    for key, label in SECTIONS:
        w.writerows([label, k, v] for k, v in report[key])
    return buf.getvalue().encode("utf-8-sig")


# ponytail: fonte Helvetica embutida só tem latin-1, então índices/sobrescritos viram texto simples.
# Embutir uma TTF (ex.: DejaVuSans) se o laudo precisar dos símbolos originais.
_LATIN1 = str.maketrans({
    **{chr(0x2080 + i): str(i) for i in range(10)},          # ₀..₉
    "⁻": "-", "⁺": "+", "⁰": "0", "⁴": "4",
    "−": "-", "–": "-", "—": "-", "≤": "<=", "≥": ">=", "≙": "=", "√": "raiz ",
    "α": "alfa", "ε": "epsilon", "λ": "lambda", "̄": "", "→": "->",
})


def _t(text):
    return str(text).translate(_LATIN1).encode("latin-1", "replace").decode("latin-1")


def to_pdf(report, meta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Analytica Lab Engine", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, _t(report["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for label, rows in [("Rastreabilidade", list(meta.items()))] + [(lbl, report[k]) for k, lbl in SECTIONS]:
        if not rows:
            continue
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, _t(label), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        with pdf.table(col_widths=(70, 120), first_row_as_headings=False) as table:
            for k, v in rows:
                row = table.row()
                row.cell(_t(k))
                row.cell(_t(v))
        pdf.ln(3)
    return bytes(pdf.output())
