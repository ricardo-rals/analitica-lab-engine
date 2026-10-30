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
    assert "Visão geral" in [e.label for e in at.expander]   # aba Como usar carregou o guia


def test_aba_solucoes():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    calc = at.selectbox(key="sol_calc")
    for option in calc.options:
        at.selectbox(key="sol_calc").set_value(option).run()
        assert not at.exception, option
        assert not at.error, (option, [e.value for e in at.error])

    at.selectbox(key="sol_calc").set_value("Concentração molar / quanto pesar (mol/L)").run()
    for key, value in [("mol_c", "0,10"), ("mol_mm", "58,44"), ("mol_v", "500")]:
        at.text_input(key=key).input(value).run()
    assert "2,9220 g" in [m.value for m in at.metric]           # CA-22 pela interface

    at.selectbox(key="sol_calc").set_value("Reagente comercial concentrado (ácidos e bases)").run()
    at.text_input(key="reag_cf").input("0,1").run()
    at.text_input(key="reag_vf").input("1000").run()
    assert "8,2807 mL" in [m.value for m in at.metric]          # CA-25 pela interface


def test_index_html_lista_todos_os_py():
    """O stlite só enxerga os arquivos listados no index.html."""
    root = Path(__file__).parent.parent
    html = (root / "index.html").read_text(encoding="utf-8")
    py = [p.relative_to(root).as_posix() for d, pat in (("modules", "*.py"), ("utils", "*.py"), ("docs", "*.md"))
          for p in (root / d).glob(pat)]
    missing = [p for p in py + ["app.py"] if f'"{p}"' not in html]
    assert not missing, f"Faltam no index.html: {missing}"


def test_pdf_com_simbolos_quimicos():
    rep = {"title": "Dureza — CaCO₃", "inputs": [("ε", "1,0 L·mol⁻¹·cm⁻¹")], "steps": [("x̄ ≤ √n", "1")],
           "results": [("Resultado", "100,09 mg CaCO₃/L")]}
    meta = {"Analista": "Ana"}
    assert report.to_pdf(rep, meta).startswith(b"%PDF")
    assert "CaCO₃".encode() in report.to_csv(rep, meta)
