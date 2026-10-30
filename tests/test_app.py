"""Testes da UI: cada página renderiza sem exceção, os exemplos calculam o esperado e os campos persistem."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from modules import bromatology as br
from modules.methods import METHODS
from utils import report
from utils.formatting import fmt

ROOT = Path(__file__).parent.parent
PAGES = [("rotina", "page_analyses"), ("rotina", "page_bromatology"), ("rotina", "page_titration"),
         ("rotina", "page_standardization"), ("rotina", "page_spectro"), ("solucoes", "page_solutions"),
         ("solucoes", "page_stoichiometry"), ("solucoes", "page_conversions"), ("estatistica", "page_descriptive"),
         ("estatistica", "page_distributions"), ("estatistica", "page_hypothesis"), ("estatistica", "page_anova"),
         ("estatistica", "page_control"), ("estatistica", "page_uncertainty"), ("gestao", "page_decision"),
         ("ajuda", "page_guide"), ("ajuda", "page_exercises")]


def page(module, fn, didactic=False):
    at = AppTest.from_string(f"from ui.{module} import {fn}\n{fn}()", default_timeout=60)
    if didactic:
        at.session_state["didatico"] = True
    return at.run()


def ok(at, context=""):
    assert not at.exception, (context, at.exception)
    assert not at.error, (context, [e.value for e in at.error])


def metrics(at):
    return [m.value for m in at.metric]


def test_app_inicia_com_navegacao():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    ok(at)
    assert at.selectbox(key="an_method").value == "dureza_total"


@pytest.mark.parametrize("module,fn", PAGES)
def test_pagina_renderiza(module, fn):
    ok(page(module, fn), fn)


@pytest.mark.parametrize("module,fn", PAGES)
def test_pagina_renderiza_no_modo_didatico(module, fn):
    ok(page(module, fn, didactic=True), fn)


@pytest.mark.parametrize("module,fn,selector", [
    ("rotina", "page_analyses", "an_method"), ("rotina", "page_bromatology", "brom_kind"),
    ("solucoes", "page_solutions", "sol_calc"), ("solucoes", "page_stoichiometry", "sto_calc"),
    ("solucoes", "page_conversions", "conv_calc"), ("estatistica", "page_distributions", "dist_calc"),
    ("estatistica", "page_hypothesis", "hyp_test"), ("ajuda", "page_exercises", "exe_mod")])
def test_todas_as_opcoes_dos_seletores(module, fn, selector):
    at = page(module, fn)
    for option in at.selectbox(key=selector).options:
        at.selectbox(key=selector).set_value(option).run()
        ok(at, option)


def test_selecao_de_metodos_por_chave():
    at = page("rotina", "page_analyses")
    for key in METHODS:
        at.selectbox(key="an_method").set_value(key).run()
        ok(at, key)


def test_radios_de_anova_e_cartas():
    at = page("estatistica", "page_anova")
    at.radio(key="anova_kind").set_value("Dois fatores (com repetição)").run()
    ok(at)
    assert any("Interação A × B: efeito significativo" in w.value for w in at.warning)   # CA-55
    at = page("estatistica", "page_control")
    at.radio(key="cc_kind").set_value("Shewhart I-MR").run()
    ok(at)


def test_exemplos_padrao_das_paginas():
    assert "0,0404 mol/L" in metrics(page("rotina", "page_titration"))            # CA-02
    assert "0,9999" in metrics(page("rotina", "page_standardization"))            # CA-04
    at = page("estatistica", "page_descriptive")
    assert any("10,9000 é outlier" in w.value for w in at.warning)                 # CA-06 (Grubbs e Dixon)
    at = page("gestao", "page_decision")
    assert any("Método B" in s.value for s in at.success)                          # CA-50


BROM_EXAMPLES = [  # (opção, botão, resultado esperado = módulo calculando as mesmas réplicas do exemplo)
    (0, "ex_brom_um", lambda: br.moisture([(20.0, 2.0, 21.82), (20.5, 2.001, 22.3205)])["moisture"]),
    (1, "ex_brom_mm", lambda: br.ash([(20.0, 2.0, 20.12), (21.0, 2.0, 21.1205)])["ash"]),
    (2, "ex_brom_kj", lambda: br.kjeldahl([(0.2, 10.0), (0.201, 10.02)], 0.1, 0.1)["protein"]),
    (3, "ex_brom_ee", lambda: br.ether_extract([(100.0, 2.0, 100.06), (98.5, 2.0, 98.5605)])["ether_extract"]),
    (4, "ex_brom_fda", lambda: br.adf_filter_bag([(0.5, 0.5, 0.65), (0.502, 0.501, 0.6515)], 0.5, 0.501)["adf"]),
]


@pytest.mark.parametrize("index,button,expected", BROM_EXAMPLES)
def test_bromatologia_exemplos_do_modo_didatico(index, button, expected):
    at = page("rotina", "page_bromatology", didactic=True)
    at.selectbox(key="brom_kind").set_value(at.selectbox(key="brom_kind").options[index]).run()
    at.button(key=button).click().run()
    ok(at, button)
    assert fmt(expected(), 2, "%") in metrics(at), (button, metrics(at))


def test_ficha_da_amostra_calcula_cnf():
    at = page("rotina", "page_bromatology", didactic=True)
    options = at.selectbox(key="brom_kind").options
    for i, button in [(0, "ex_brom_um"), (1, "ex_brom_mm"), (2, "ex_brom_kj"), (3, "ex_brom_ee")]:
        at.selectbox(key="brom_kind").set_value(options[i]).run()
        at.button(key=button).click().run()
    at.selectbox(key="brom_kind").set_value(options[-1]).run()
    at.text_input(key="brom_fdn").input("20").run()
    ok(at)
    assert any(m.label == "CNF (MS)" for m in at.metric)


def test_aba_solucoes():
    at = page("solucoes", "page_solutions")
    at.selectbox(key="sol_calc").set_value("Concentração molar / quanto pesar (mol/L)").run()
    for key, value in [("mol_c", "0,10"), ("mol_mm", "58,44"), ("mol_v", "500")]:
        at.text_input(key=key).input(value).run()
    assert "2,9220 g" in metrics(at)                                                # CA-22
    at.selectbox(key="sol_calc").set_value("Reagente comercial concentrado (ácidos e bases)").run()
    at.text_input(key="reag_cf").input("0,1").run()
    at.text_input(key="reag_vf").input("1000").run()
    assert "8,2807 mL" in metrics(at)                                               # CA-25


def test_incerteza_com_exemplo():
    at = page("estatistica", "page_uncertainty", didactic=True)
    at.button(key="ex_unc").click().run()
    ok(at)
    assert any("1,6471e-04" in m for m in metrics(at)), metrics(at)                # CA-48


def test_exercicio_corrige_resposta():
    at = page("ajuda", "page_exercises")
    key = next(t.key for t in at.text_input if t.key.startswith("exe_ans_"))
    at.text_input(key=key).input("25").run()
    assert at.success                                                               # 25 mL (diluição)


def test_campo_persiste_ao_trocar_de_pagina():
    script = ("import streamlit as st\nfrom ui.common import num\n"
              "if st.session_state.get('outra_pagina'):\n    st.write('outra página')\n"
              "else:\n    num('Campo', None, 'campo')\n")
    at = AppTest.from_string(script).run()
    at.text_input(key="campo").input("12,5").run()
    at.session_state["outra_pagina"] = True
    at.run()                                                                        # widget some (troca de página)
    assert "campo" not in at.session_state
    at.session_state["outra_pagina"] = False
    at.run()                                                                        # volta: valor restaurado
    assert at.text_input(key="campo").value == "12,5"


def test_index_html_lista_todos_os_arquivos():
    """O stlite só enxerga os arquivos listados no index.html."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    files = [p.relative_to(ROOT).as_posix() for d, pat in (("modules", "*.py"), ("utils", "*.py"), ("ui", "*.py"),
                                                          ("docs", "*.md")) for p in (ROOT / d).glob(pat)]
    missing = [p for p in files + ["app.py"] if f'"{p}"' not in html]
    assert not missing, f"Faltam no index.html: {missing}"


def test_pdf_com_simbolos_quimicos():
    rep = {"title": "Dureza — CaCO₃", "inputs": [("ε", "1,0 L·mol⁻¹·cm⁻¹")], "steps": [("x̄ ≤ √n", "1")],
           "results": [("Resultado", "100,09 mg CaCO₃/L")]}
    meta = {"Analista": "Ana"}
    assert report.to_pdf(rep, meta).startswith(b"%PDF")
    assert "CaCO₃".encode() in report.to_csv(rep, meta)


def test_carta_de_controle_com_exemplo():
    at = page("estatistica", "page_control", didactic=True)
    at.button(key="ex_cc").click().run()
    ok(at)
    assert "2 · 1" in metrics(at)                         # rejeições: corrida 23 (2-2s) e 25 (1-3s); alerta: 22 (1-2s)
