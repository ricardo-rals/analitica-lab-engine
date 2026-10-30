"""Seção Gestão: decisão multicritério AHP → TOPSIS (RF-15)."""
import pandas as pd
import streamlit as st

from modules import decision
from ui.common import (bar_chart, didactic, editor, export, f, num, parse_number, select_slider, set_fields,
                       show_error, show_table, show_warnings)

SAATY = [1 / 9, 1 / 7, 1 / 5, 1 / 3, 1.0, 3.0, 5.0, 7.0, 9.0]
SAATY_TEXT = {1: "igual importância", 3: "moderadamente", 5: "fortemente", 7: "muito fortemente", 9: "extremamente"}
DEFAULT_CRITERIA = ["Custo por análise (R$)", "Recuperação (%)", "Tempo (h)"]
DEFAULT_ALTERNATIVES = [("Método A", 250, 98.0, 2.0), ("Método B", 180, 95.0, 3.0), ("Método C", 300, 99.5, 1.5)]


def criteria_names():
    df = editor(pd.DataFrame({"Critério": DEFAULT_CRITERIA + ["", ""]}), "dec_criteria")
    return [c.strip() for c in df["Critério"] if isinstance(c, str) and c.strip()]


def saaty_label(v, a, b):
    if v == 1:
        return "1 · igual importância"
    if v > 1:
        return f"{int(v)} · {a} {SAATY_TEXT[int(v)]} mais importante"
    k = int(round(1 / v))
    return f"1/{k} · {b} {SAATY_TEXT[k]} mais importante"


def page_decision():
    didactic("**AHP:** em vez de dar pesos de cabeça, compare os critérios **dois a dois** (escala de Saaty 1–9). "
             "Os pesos saem do autovetor principal da matriz. A **razão de consistência** RC ≤ 0,10 garante que os "
             "julgamentos não se contradizem (se A > B e B > C, então A > C). **TOPSIS:** ranqueia as alternativas "
             "pela proximidade da solução ideal (melhor valor em cada critério) e distância da pior. "
             "C = 1 é a alternativa ideal.", key="dec")
    st.caption("Ex.: escolher método analítico, fornecedor ou equipamento. Defina os critérios abaixo; eles valem "
               "para as duas etapas.")
    names = criteria_names()
    if len(names) < 2:
        st.info("Informe ao menos 2 critérios.")
        return
    if len(names) != len(set(names)):
        st.error("Os nomes dos critérios devem ser diferentes.")
        return
    tab1, tab2 = st.tabs(["1️⃣ AHP — pesos dos critérios", "2️⃣ TOPSIS — ranking das alternativas"])
    with tab1:
        weights = ahp_view(names)
    with tab2:
        topsis_view(names, weights)


def ahp_view(names):
    n = len(names)
    st.caption("Para cada par, quanto o primeiro critério é mais importante que o segundo?")
    defaults = {(0, 1): 3.0, (0, 2): 5.0, (1, 2): 3.0}
    upper = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = names[i], names[j]
            upper[(i, j)] = select_slider(f"**{a}** × **{b}**", SAATY, f"ahp_{a}|{b}",
                                          defaults.get((i, j), 1.0) if names[:3] == DEFAULT_CRITERIA else 1.0,
                                          format_func=lambda v, a=a, b=b: saaty_label(v, a, b))
    try:
        r = decision.ahp(decision.reciprocal_matrix(upper))
    except ValueError as e:
        show_error(e)
        return None
    c1, c2, c3 = st.columns(3)
    c1.metric("λmax", f(r["lambda_max"], "", 3))
    c2.metric("IC", f(r["CI"], "", 4))
    c3.metric("RC", f(r["CR"], "", 3))
    if r["consistent"]:
        st.success(f"Julgamentos consistentes (RC = {f(r['CR'], '', 3)} ≤ 0,10).")
    else:
        i, j = r["worst_pair"]
        st.warning(f"RC = {f(r['CR'], '', 3)} > 0,10: julgamentos inconsistentes. Revise primeiro a comparação "
                   f"**{names[i]} × {names[j]}**.")
    show_table([(nm, f(w * 100, "%", 1)) for nm, w in zip(names, r["weights"])], ("Critério", "Peso"))
    st.altair_chart(bar_chart(names, [w * 100 for w in r["weights"]], "Peso (%)", "Critério"))
    st.button("Usar estes pesos no TOPSIS", on_click=set_fields,
              args=({f"top_w_{nm}": f"{w:.4f}".replace(".", ",") for nm, w in zip(names, r["weights"])},))
    return r["weights"]


def topsis_view(names, ahp_weights):
    st.caption("Uma linha por alternativa, com o valor de cada critério.")
    use_defaults = names == DEFAULT_CRITERIA
    rows = DEFAULT_ALTERNATIVES if use_defaults else [("", *[""] * len(names))] * 3
    df = editor(pd.DataFrame({"Alternativa": [r[0] for r in rows] + [""],
                              **{nm: [str(r[i + 1]).replace(".", ",") for r in rows] + [""] for i, nm in enumerate(names)}}),
                f"top_matrix_{'|'.join(names)}")
    st.markdown("**Tipo e peso de cada critério**")
    cols = st.columns(len(names))
    benefit, weights = [], []
    for col, nm in zip(cols, names):
        with col:
            default_cost = use_defaults and nm != "Recuperação (%)"
            kind = select_slider(nm, ["custo (menor é melhor)", "benefício (maior é melhor)"], f"top_b_{nm}",
                                 "custo (menor é melhor)" if default_cost else "benefício (maior é melhor)")
            benefit.append(kind.startswith("benefício"))
            w0 = None if ahp_weights is None else ahp_weights[names.index(nm)]
            weights.append(num("Peso", w0, f"top_w_{nm}"))
    try:
        if any(w is None for w in weights):
            raise ValueError("Informe o peso de todos os critérios (ou use os pesos do AHP).")
        alts, matrix = [], []
        for i, row in enumerate(df.itertuples(index=False), 1):
            name, *vals = row
            name = name.strip() if isinstance(name, str) else ""
            parsed = [parse_number(v) for v in vals]
            if not name and all(v is None for v in parsed):
                continue
            if not name or any(v is None for v in parsed):
                raise ValueError(f"Linha {i}: preencha o nome e todos os critérios.")
            alts.append(name)
            matrix.append(parsed)
        r = decision.topsis(matrix, weights, benefit)
    except ValueError as e:
        show_error(e)
        return
    best = r["ranking"][0]
    st.success(f"Melhor alternativa: **{alts[best]}** (C = {f(r['closeness'][best], '', 3)}).")
    table = [(str(pos), alts[i], f(r["closeness"][i], "", 4), f(r["d_plus"][i], "", 4), f(r["d_minus"][i], "", 4))
             for pos, i in enumerate(r["ranking"], 1)]
    show_table(table, ("Posição", "Alternativa", "C (proximidade)", "D⁺ (ao ideal)", "D⁻ (ao anti-ideal)"))
    st.altair_chart(bar_chart([alts[i] for i in r["ranking"]], [r["closeness"][i] for i in r["ranking"]],
                              "Proximidade relativa C", "Alternativa").properties(title="Ranking TOPSIS"))
    show_warnings(r["warnings"])
    export("Decisão multicritério (AHP + TOPSIS)",
           [(nm, f"peso {f(w)} · {'benefício' if b else 'custo'}") for nm, w, b in zip(names, weights, benefit)],
           [(f"{t[0]}º {t[1]}", f"C = {t[2]}") for t in table], [("Melhor alternativa", alts[best])], "decisao")
