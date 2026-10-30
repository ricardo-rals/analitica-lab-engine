"""Smoke test da UI: todas as abas renderizam sem exceção, inclusive cada análise do catálogo."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from modules.methods import METHODS
from utils import report


def test_app_renderiza_todas_as_analises():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception
    metrics = [m.value for m in at.metric]
    assert "0,0404 mol/L" in metrics                         # aba Titulação, exemplo = CA-02
    assert "0,9999" in metrics                               # aba Padronização, exemplo = CA-04
    assert any("10,9000 é outlier" in w.value for w in at.warning)  # aba Estatística, exemplo = CA-06
    for key in METHODS:
        at.selectbox(key="an_method").set_value(key).run()
        assert not at.exception, key
    assert not at.error, [e.value for e in at.error]


def test_index_html_lista_todos_os_py():
    """O stlite só enxerga os arquivos listados no index.html."""
    root = Path(__file__).parent.parent
    html = (root / "index.html").read_text(encoding="utf-8")
    py = [p.relative_to(root).as_posix() for d in ("modules", "utils") for p in (root / d).glob("*.py")]
    missing = [p for p in py + ["app.py"] if f'"{p}"' not in html]
    assert not missing, f"Faltam no index.html: {missing}"


def test_pdf_com_simbolos_quimicos():
    rep = {"title": "Dureza — CaCO₃", "inputs": [("ε", "1,0 L·mol⁻¹·cm⁻¹")], "steps": [("x̄ ≤ √n", "1")],
           "results": [("Resultado", "100,09 mg CaCO₃/L")]}
    meta = {"Analista": "Ana"}
    assert report.to_pdf(rep, meta).startswith(b"%PDF")
    assert "CaCO₃".encode() in report.to_csv(rep, meta)
