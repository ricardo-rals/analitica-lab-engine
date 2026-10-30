"""Seção Estatística: descritiva, distribuições, testes de hipótese, ANOVA, cartas de controle e incerteza."""
import io
import math

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from modules import control, inferential, stats, uncertainty
from ui.common import (bar_chart, column_editor, conclusion, didactic, editor, example_df, export, f, grubbs_note,
                       num, parse_column, parse_number, parse_rows, radio, select, select_slider, set_fields,
                       show_error, show_table, show_warnings, stats_rows, table_editor, text, values_text)

ALPHAS = [0.01, 0.05, 0.10]


def alpha_input(key):
    return select_slider("Nível de significância α", ALPHAS, key, 0.05,
                         format_func=lambda a: f"{a:g} (confiança {1 - a:.0%})")


# ---------------------------------------------------------------- descritiva (RF-03, RF-12)
def page_descriptive():
    didactic("**Tendência central:** média (sensível a outliers) e mediana (robusta). **Dispersão:** variância "
             "`s² = Σ(x − x̄)²/(n − 1)`, desvio padrão s, CV = s/x̄ × 100 e amplitude. **Outliers:** Grubbs (n ≥ 3, "
             "supõe normalidade), Dixon (3 a 10 valores) e boxplot (fora de Q1 − 1,5·IQR ou Q3 + 1,5·IQR). "
             "Teste indica, mas quem decide remover é o analista.",
             {"est_rows": example_df(["Valor", "Peso (opcional)"],
                                     [(10.10, ""), (10.12, ""), (10.15, ""), (10.11, ""), (10.90, "")])}, "est")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        st.caption("Valores de exemplo — substitua pelos seus. O peso só é usado na média ponderada.")
        df = table_editor(["Valor", "Peso (opcional)"], "est_rows", rows=8,
                          defaults=[(10.10, None), (10.12, None), (10.15, None), (10.11, None), (10.90, None)])
        unit = text("Unidade (opcional)", "est_unit")
        conf = select_slider("Nível de confiança", [0.90, 0.95, 0.99], "est_conf", 0.95,
                             format_func=lambda x: f"{x:.0%}")
        alpha = select_slider("α do teste de Grubbs", ALPHAS, "est_alpha", 0.05)
    with col_out:
        try:
            pairs = [(parse_number(v), parse_number(w)) for v, w in zip(df.iloc[:, 0], df.iloc[:, 1])]
            values = [v for v, _ in pairs if v is not None]
            weights = [w for v, w in pairs if v is not None]
            use_w = any(w is not None for w in weights)
            if use_w and any(w is None for w in weights):
                raise ValueError("Informe o peso de todos os valores, ou de nenhum.")
            s = stats.describe(values, conf)
            d = stats.describe_extended(values, weights if use_w else None)
        except ValueError as e:
            show_error(e)
            return
        st.metric("Média", f(s["mean"], unit))
        if s["ci_half"] is not None:
            st.markdown(f"**Resultado:** {f(s['mean'])} ± {f(s['ci_half'])} {unit} (IC {conf:.0%}, n = {s['n']})")
        steps = stats_rows(s, unit) + [
            ("Mediana", f(d["median"], unit)),
            ("Moda", "amodal" if d["modes"] is None else "; ".join(f(m) for m in d["modes"])),
            ("Variância (s²)", "—" if d["variance"] is None else f(d["variance"])),
            ("Erro padrão da média (s/√n)", "—" if d["sem"] is None else f(d["sem"], unit)),
            ("Mínimo · máximo", f"{f(d['min'])} · {f(d['max'])}"), ("Amplitude", f(d["range"], unit)),
            ("Q1 · Q3", f"{f(d['q1'])} · {f(d['q3'])}"), ("IQR (Q3 − Q1)", f(d["iqr"], unit))]
        if d["weighted_mean"] is not None:
            steps.append(("Média ponderada", f(d["weighted_mean"], unit)))
        show_table(steps)
        outlier_tests(values, alpha)
        show_warnings(s["warnings"])
        distribution_charts(values, unit)
        export("Estatística descritiva", [("Valores", values_text(values, unit))], steps,
               [("Média", f(s["mean"], unit))], "estatistica")


def outlier_tests(values, alpha):
    st.markdown("**Valores discrepantes**")
    grubbs_note(values, alpha)
    if 3 <= len(values) <= 10:
        dx = stats.dixon(values)
        if dx["applicable"]:
            msg = (f"Dixon (95 %): Q = {f(dx['Q'], '', 3)} {'>' if dx['is_outlier'] else '≤'} "
                   f"Q crítico = {f(dx['Q_crit'], '', 3)}")
            if dx["is_outlier"]:
                st.warning(f"{msg} → {f(dx['suspect'])} é outlier.")
            else:
                st.caption(f"{msg} → nenhum outlier.")
    box = stats.boxplot_outliers(values)
    fences = f"limites {f(box['lower_fence'])} a {f(box['upper_fence'])}"
    if box["outliers"]:
        st.warning(f"Boxplot ({fences}): fora dos limites {values_text(box['outliers'])}.")
    else:
        st.caption(f"Boxplot ({fences}): nenhum valor fora dos limites.")


def distribution_charts(values, unit):
    if len(values) < 3:
        return
    df = pd.DataFrame({"valor": values})
    x_title = f"Valor ({unit})" if unit else "Valor"
    hist = alt.Chart(df).mark_bar(opacity=0.7).encode(alt.X("valor:Q", bin=alt.Bin(maxbins=10), title=x_title),
                                                       alt.Y("count():Q", title="Frequência"))
    box = alt.Chart(df).mark_boxplot(extent=1.5).encode(alt.X("valor:Q", title=x_title))
    c1, c2 = st.columns(2)
    c1.altair_chart(hist.properties(title="Histograma"))
    c2.altair_chart(box.properties(title="Boxplot", height=120))


# ---------------------------------------------------------------- distribuições (RF-12.3)
def page_distributions():
    didactic("**Normal:** 68 % dos valores ficam a ±1s da média, 95 % a ±1,96s e 99,7 % a ±3s. O **escore z** diz "
             "quantos desvios um valor está da média. A **t de Student** substitui a normal quando s é estimado de "
             "poucas réplicas: o t crítico cai para 1,96 só com muitos graus de liberdade. **Shapiro–Wilk** testa "
             "se os dados podem ser considerados normais (p ≥ α).", key="dist")
    calc = select("Cálculo", ["Probabilidade na normal", "Escore z", "t crítico (Student)", "Teste de normalidade"],
                  "dist_calc")
    try:
        if calc == "Probabilidade na normal":
            cols = st.columns(4)
            with cols[0]:
                mean = num("Média", 0, "dist_mean")
            with cols[1]:
                sd = num("Desvio padrão", 1, "dist_sd")
            with cols[2]:
                lo = num("Limite inferior (vazio = −∞)", -1.96, "dist_lo")
            with cols[3]:
                hi = num("Limite superior (vazio = +∞)", 1.96, "dist_hi")
            if mean is None:
                raise ValueError("Informe Média.")
            p = stats.normal_probability(mean, sd, lo, hi)
            st.metric("Probabilidade", f(p * 100, "%", 2))
            normal_curve(mean, sd, lo, hi)
        elif calc == "Escore z":
            cols = st.columns(3)
            with cols[0]:
                x = num("Valor x", None, "z_x")
            with cols[1]:
                mean = num("Média", None, "z_mean")
            with cols[2]:
                sd = num("Desvio padrão", None, "z_sd")
            if x is None or mean is None:
                raise ValueError("Informe o valor e a média.")
            z = stats.z_score(x, mean, sd)
            st.metric("z = (x − média) / s", f(z, "", 3))
            st.caption("|z| ≤ 2: satisfatório · 2 < |z| < 3: questionável · |z| ≥ 3: insatisfatório "
                       "(critério usual em ensaios de proficiência, ISO 13528).")
        elif calc == "t crítico (Student)":
            cols = st.columns(2)
            with cols[0]:
                df_ = num("Graus de liberdade (n − 1)", 2, "tc_df")
            with cols[1]:
                conf = select_slider("Confiança", [0.90, 0.95, 0.99], "tc_conf", 0.95, format_func=lambda c: f"{c:.0%}")
            if df_ is None:
                raise ValueError("Informe os graus de liberdade.")
            st.metric("t crítico bilateral", f(stats.t_critical(df_, conf), "", 3))
        else:
            values = parse_column(column_editor("Valor", [10.10, 10.12, 10.15, 10.11, 10.90], "norm_vals", rows=10))
            alpha = alpha_input("norm_alpha")
            r = stats.shapiro_wilk(values, alpha)
            msg = f"Shapiro–Wilk: W = {f(r['W'], '', 4)}; p = {f(r['p'], '', 4)}"
            (st.success if r["normal"] else st.warning)(
                f"{msg} → " + ("os dados podem ser considerados normais." if r["normal"]
                               else "os dados NÃO seguem distribuição normal (cuidado com testes que a supõem)."))
            distribution_charts(values, "")
    except ValueError as e:
        show_error(e)


def normal_curve(mean, sd, lo, hi):
    xs = np.linspace(mean - 4 * sd, mean + 4 * sd, 200)
    df = pd.DataFrame({"x": xs, "densidade": np.exp(-((xs - mean) / sd) ** 2 / 2) / (sd * math.sqrt(2 * math.pi))})
    df["área"] = (df["x"] >= (-np.inf if lo is None else lo)) & (df["x"] <= (np.inf if hi is None else hi))
    line = alt.Chart(df).mark_line().encode(x=alt.X("x:Q", title="x"), y=alt.Y("densidade:Q", title="Densidade"))
    area = alt.Chart(df[df["área"]]).mark_area(opacity=0.4).encode(x="x:Q", y="densidade:Q")
    st.altair_chart((area + line).properties(title="Distribuição normal (área = probabilidade)"))


# ---------------------------------------------------------------- testes de hipótese (RF-13.1, RF-13.2)
TESTS = ["t: uma amostra × valor de referência", "t: duas amostras independentes", "t: pareado (mesmas amostras)",
         "F: comparar precisões (variâncias)"]


def page_hypothesis():
    didactic("**Hipótese nula (H₀):** não há diferença. Se o **valor-p** for menor que α, rejeita-se H₀: a diferença "
             "é estatisticamente significativa. **t uma amostra:** compara a média com um valor de referência "
             "(ex.: certificado do MRC) — mede exatidão. **t duas amostras:** o teste F decide antes se as variâncias "
             "são iguais (t agrupado) ou não (t de Welch). **Pareado:** as mesmas amostras medidas de dois modos. "
             "**F:** compara precisões.",
             {"hyp_a": example_df(["Valor"], [(10.10,), (10.20,), (10.15,)]),
              "hyp_b": example_df(["Valor"], [(10.30,), (10.35,), (10.25,), (10.40,)]), "hyp_ref": "10"}, "hyp")
    test = select("Teste", TESTS, "hyp_test")
    alpha = alpha_input("hyp_alpha")
    one = test.startswith("t: uma")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Série A**" if not one else "**Amostra**")
        a = parse_column(column_editor("Valor", [], "hyp_a", rows=8))
    with cols[1]:
        if one:
            ref = num("Valor de referência", None, "hyp_ref")
        else:
            st.markdown("**Série B**")
            b = parse_column(column_editor("Valor", [], "hyp_b", rows=8))
    try:
        if one:
            if ref is None:
                raise ValueError("Informe o valor de referência.")
            r = inferential.t_one_sample(a, ref, alpha)
            rows = [("Média", f(r["mean"])), ("Viés (média − referência)", f(r["bias"]))]
        elif test.startswith("t: duas"):
            r = inferential.t_two_sample(a, b, alpha)
            rows = [("Média A · B", f"{f(r['mean_a'])} · {f(r['mean_b'])}"), ("Método", r["method"]),
                    ("Teste F prévio", f"F = {f(r['f_test']['F'], '', 3)}; p = {f(r['f_test']['p'], '', 4)}")]
        elif test.startswith("t: pareado"):
            r = inferential.t_paired(a, b, alpha)
            rows = [("Média das diferenças (A − B)", f(r["mean_diff"]))]
        else:
            r = inferential.f_test(a, b, alpha)
            rows = [("F = s²maior / s²menor", f(r["F"], "", 4)), ("gl", f"{r['df_num']} e {r['df_den']}"),
                    ("p", f(r["p"], "", 4)), ("F crítico (bilateral)", f(r["F_crit"], "", 3))]
    except ValueError as e:
        show_error(e)
        return
    if "t" in r:
        rows += [("t", f(r["t"], "", 4)), ("Graus de liberdade", f(r["df"], "", 2)), ("Valor-p", f(r["p"], "", 4)),
                 ("t crítico (bilateral)", f(r["t_crit"], "", 3))]
    conclusion(r["conclusion"], r["significant"])
    show_table(rows, ("Item", "Valor"))
    inputs = [("Série A", values_text(a))] + ([("Referência", f(ref))] if one else [("Série B", values_text(b))])
    export(test, inputs, rows, [("Conclusão", r["conclusion"])], "hipotese")


# ---------------------------------------------------------------- ANOVA (RF-13.3)
def page_anova():
    didactic("**ANOVA** compara 3 ou mais médias de uma vez, separando a variação **entre** grupos da variação "
             "**dentro** dos grupos: `F = QM entre / QM dentro`. F grande (p < α) = ao menos um grupo difere. "
             "O **teste de Tukey** diz quais pares diferem. Na ANOVA de **dois fatores**, testa-se cada fator e a "
             "**interação** (o efeito de um fator depende do nível do outro).",
             {"anova1": example_df(["Grupo", "Valor"], [("G1", 10.1), ("G1", 10.2), ("G1", 10.15), ("G2", 10.3),
                                                        ("G2", 10.35), ("G2", 10.25), ("G3", 10.0), ("G3", 10.05),
                                                        ("G3", 10.1)])}, "anova")
    kind = radio("Tipo", ["Um fator", "Dois fatores (com repetição)"], "anova_kind", horizontal=True)
    alpha = alpha_input("anova_alpha")
    if kind == "Um fator":
        st.caption("Uma linha por medição: nome do grupo (analista, equipamento, dia...) e valor.")
        df = table_editor(["Grupo", "Valor"], "anova1", rows=12)
        try:
            groups = {}
            for i, (g, v) in enumerate(df.itertuples(index=False), 1):
                g = g.strip() if isinstance(g, str) else ""
                x = parse_number(v)
                if not g and x is None:
                    continue
                if not g or x is None:
                    raise ValueError(f"Linha {i} incompleta (grupo e valor).")
                groups.setdefault(g, []).append(x)
            if not groups:
                raise ValueError("Nenhum valor informado em grupos.")
            r = inferential.anova_one_way(groups, alpha)
        except ValueError as e:
            show_error(e)
            return
        conclusion(r["conclusion"], r["significant"])
        table = [(src, f(ss, "", 4), str(dfv), "—" if ms is None else f(ms, "", 4),
                  "—" if fv is None else f(fv, "", 3), "—" if p is None else f(p, "", 4))
                 for src, ss, dfv, ms, fv, p in r["table"]]
        show_table(table, ("Fonte", "SQ", "gl", "QM", "F", "p"))
        st.markdown("**Tukey HSD (comparações par a par)**")
        show_table([(f"{t['a']} × {t['b']}", f(t["diff"]), f(t["p"], "", 4), "sim" if t["significant"] else "não")
                    for t in r["tukey"]], ("Par", "Diferença", "p", "Diferem?"))
        st.altair_chart(bar_chart(list(r["means"]), list(r["means"].values()), "Média", "Grupo")
                        .properties(title="Médias dos grupos"))
        export("ANOVA de um fator", [(g, values_text(v)) for g, v in groups.items()],
               [(row[0], f"SQ {row[1]} · gl {row[2]} · F {row[4]} · p {row[5]}") for row in table],
               [("Conclusão", r["conclusion"])], "anova1")
    else:
        st.caption("Uma linha por medição: nível do fator A, nível do fator B e valor. Mesmo nº de repetições em "
                   "todas as combinações.")
        df = table_editor(["Fator A", "Fator B", "Valor"], "anova2", rows=12,
                          defaults=[("A1", "B1", 10), ("A1", "B1", 11), ("A1", "B2", 12), ("A1", "B2", 13),
                                    ("A2", "B1", 14), ("A2", "B1", 15), ("A2", "B2", 20), ("A2", "B2", 21)])
        try:
            cells = {}
            for i, (fa, fb, v) in enumerate(df.itertuples(index=False), 1):
                fa = fa.strip() if isinstance(fa, str) else ""
                fb = fb.strip() if isinstance(fb, str) else ""
                x = parse_number(v)
                if not fa and not fb and x is None:
                    continue
                if not fa or not fb or x is None:
                    raise ValueError(f"Linha {i} incompleta.")
                cells.setdefault((fa, fb), []).append(x)
            if not cells:
                raise ValueError("Nenhum valor informado em medições.")
            r = inferential.anova_two_way(cells, alpha)
        except ValueError as e:
            show_error(e)
            return
        names = {"A": "Fator A", "B": "Fator B", "AB": "Interação A × B"}
        table = [(names[k], f(e["SS"], "", 4), str(e["df"]), f(e["MS"], "", 4), f(e["F"], "", 3), f(e["p"], "", 4),
                  "sim" if e["significant"] else "não") for k, e in r["effects"].items()]
        table.append(("Erro", f(r["error"]["SS"], "", 4), str(r["error"]["df"]), f(r["error"]["MS"], "", 4), "—", "—", "—"))
        show_table(table, ("Fonte", "SQ", "gl", "QM", "F", "p", "Significativo?"))
        for k, e in r["effects"].items():
            conclusion(f"{names[k]}: " + ("efeito significativo" if e["significant"] else "sem efeito significativo")
                       + f" (p = {f(e['p'], '', 4)}).", e["significant"])
        export("ANOVA de dois fatores", [(f"{a} × {b}", values_text(v)) for (a, b), v in cells.items()],
               [(row[0], f"F {row[4]} · p {row[5]}") for row in table], [], "anova2")


# ---------------------------------------------------------------- cartas de controle (RF-13.4)
# 20 corridas de estabelecimento em torno de 100 e 5 novas, com desvios para mostrar as regras.
CONTROL_EXAMPLE = [100.5, 99.2, 101.8, 98.9, 100.3, 102.1, 99.7, 97.9, 100.9, 101.2, 99.4, 100.1, 98.6, 101.5,
                   100.8, 99.1, 102.4, 98.2, 100.6, 99.8, 101.9, 103.4, 103.6, 100.2, 105.5]


def page_control():
    didactic("**Levey-Jennings:** a média e o desvio alvo vêm das **20 primeiras** medições do material de "
             "controle. Cada nova medição é comparada com os limites ±2s (alerta) e ±3s (ação). As **regras de "
             "Westgard** pegam também tendências: 2 pontos seguidos além de 2s, 4 além de 1s, 10 do mesmo lado. "
             "**I-MR (Shewhart):** limites pela amplitude móvel média (x̄ ± 2,66·MR̄).",
             {"cc_rows": example_df(["Data / corrida", "Valor"], [(f"Corrida {i}", v) for i, v in enumerate(
                 CONTROL_EXAMPLE, 1)])}, "cc")
    kind = radio("Carta", ["Levey-Jennings + Westgard", "Shewhart I-MR"], "cc_kind", horizontal=True)
    st.caption("Enquanto o app não guarda histórico, mantenha a série num CSV: importe, acrescente as novas medições "
               "e exporte de novo.")
    up = st.file_uploader("Importar série (CSV com coluna 'Valor'; 'Data' opcional)", type=["csv"], key="cc_upload")
    if up is not None:
        try:
            imported = read_series_csv(up.getvalue())
            st.button(f"Carregar {len(imported)} medições do arquivo", on_click=set_fields, args=({"cc_rows": imported},))
        except ValueError as e:
            show_error(e)
    col_in, col_out = st.columns([1, 2])
    with col_in:
        df = editor(pd.DataFrame({"Data / corrida": [""] * 10, "Valor": [""] * 10}), "cc_rows")
        base = num("Medições da fase de estabelecimento", control.BASELINE, "cc_base")
        mean = sd = None
        if kind.startswith("Levey"):
            st.caption("Ou informe alvo e s (ex.: certificado do controle):")
            mean = num("Média alvo (opcional)", None, "cc_mean")
            sd = num("Desvio alvo (opcional)", None, "cc_sd")
    with col_out:
        try:
            labels, values = [], []
            for i, (lab, v) in enumerate(df.itertuples(index=False), 1):
                x = parse_number(v)
                if x is None:
                    continue
                labels.append(lab if isinstance(lab, str) and lab.strip() else str(i))
                values.append(x)
            if base is None or base < 2:
                raise ValueError("A fase de estabelecimento precisa de ao menos 2 medições.")
            if kind.startswith("Levey"):
                r = control.levey_jennings(values, mean, sd, int(base))
            else:
                r = control.imr_chart(values, int(base))
        except ValueError as e:
            show_error(e)
            return
        show_warnings(r["warnings"])
        if kind.startswith("Levey"):
            lj_view(r, labels)
        else:
            imr_view(r, labels)


def read_series_csv(raw):
    text_ = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text_), sep=None, engine="python", dtype=str)
    cols = {c.strip().lower(): c for c in df.columns}
    if "valor" not in cols:
        raise ValueError("O CSV precisa de uma coluna chamada 'Valor'.")
    data_col = next((cols[c] for c in cols if c.startswith("data")), None)
    out = pd.DataFrame({"Data / corrida": df[data_col].fillna("") if data_col else [""] * len(df),
                        "Valor": df[cols["valor"]].fillna("")})
    return pd.concat([out, pd.DataFrame({"Data / corrida": [""] * 5, "Valor": [""] * 5})], ignore_index=True)


def lj_view(r, labels):
    c1, c2, c3 = st.columns(3)
    c1.metric("Média alvo", f(r["mean"]))
    c2.metric("Desvio alvo (s)", f(r["sd"]))
    c3.metric("Rejeições · alertas", f"{r['rejected']} · {r['alerts']}")
    pts = pd.DataFrame({"n": [p["index"] for p in r["points"]], "corrida": labels, "valor": [p["value"] for p in r["points"]],
                        "status": [p["status"] for p in r["points"]],
                        "regras": [", ".join(p["rules"]) or "—" for p in r["points"]]})
    rules = pd.DataFrame({"y": [r["mean"]] + list(r["limits"].values()),
                          "nível": ["média"] + list(r["limits"]),
                          "tipo": ["média"] + ["±3s" if "3" in k else "±2s" if "2" in k else "±1s" for k in r["limits"]]})
    color = alt.Color("status:N", scale=alt.Scale(domain=["ok", "alerta", "rejeição"],
                                                  range=["#4c78a8", "#f2a541", "#e4572e"]), title="Status")
    line = alt.Chart(pts).mark_line(color="#888").encode(x=alt.X("n:Q", title="Medição"), y=alt.Y("valor:Q", title="Valor",
                                                                                                    scale=alt.Scale(zero=False)))
    dots = alt.Chart(pts).mark_circle(size=90).encode(x="n:Q", y="valor:Q", color=color,
                                                      tooltip=["corrida", "valor", "regras"])
    limits = alt.Chart(rules).mark_rule().encode(
        y="y:Q", strokeDash=alt.StrokeDash("tipo:N", title="Limite"),
        color=alt.value("#999"))
    st.altair_chart((limits + line + dots).properties(title="Levey-Jennings", height=360))
    bad = [p for p in r["points"] if p["rules"]]
    if bad:
        show_table([(labels[p["index"] - 1], f(p["value"]), f(p["z"], "", 2), ", ".join(p["rules"]),
                     "; ".join(control.WESTGARD[k][0] for k in p["rules"]), p["status"]) for p in bad],
                   ("Corrida", "Valor", "z", "Regras", "Significado", "Status"))
    else:
        st.success("Nenhuma regra de Westgard violada: processo sob controle.")
    out = pts.assign(z=[round(p["z"], 3) for p in r["points"]])[["corrida", "valor", "z", "regras", "status"]]
    st.download_button("⬇️ Exportar série (CSV)", out.rename(columns={"corrida": "Data", "valor": "Valor"})
                       .to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), "carta_controle.csv", "text/csv")


def imr_view(r, labels):
    c1, c2, c3 = st.columns(3)
    c1.metric("Linha central", f(r["mean"]))
    c2.metric("LIC · LSC", f"{f(r['lcl'])} · {f(r['ucl'])}")
    c3.metric("MR̄ · LSC(MR)", f"{f(r['mr_bar'])} · {f(r['mr_ucl'])}")
    pts = pd.DataFrame({"n": [p["index"] for p in r["points"]], "valor": [p["value"] for p in r["points"]],
                        "mr": [p["mr"] for p in r["points"]],
                        "fora": ["sim" if p["out"] else "não" for p in r["points"]]})
    color = alt.Color("fora:N", scale=alt.Scale(domain=["não", "sim"], range=["#4c78a8", "#e4572e"]),
                      title="Fora dos limites")

    def chart(y, limits, title):
        base = alt.Chart(pts).encode(x=alt.X("n:Q", title="Medição"))
        lines = alt.Chart(pd.DataFrame({"y": limits})).mark_rule(strokeDash=[4, 4], color="#999").encode(y="y:Q")
        return (base.mark_line(color="#888").encode(y=alt.Y(f"{y}:Q", scale=alt.Scale(zero=False), title=title))
                + base.mark_circle(size=80).encode(y=f"{y}:Q", color=color) + lines).properties(title=title, height=250)

    st.altair_chart(chart("valor", [r["lcl"], r["mean"], r["ucl"]], "Individuais (I)"))
    st.altair_chart(chart("mr", [r["mr_bar"], r["mr_ucl"]], "Amplitude móvel (MR)"))
    out = [p for p in r["points"] if p["out"] or p["mr_out"]]
    if out:
        show_table([(labels[p["index"] - 1], f(p["value"]), "sim" if p["out"] else "não",
                     "sim" if p["mr_out"] else "não") for p in out], ("Corrida", "Valor", "Fora (I)", "Fora (MR)"))
    else:
        st.success("Todos os pontos dentro dos limites.")


# ---------------------------------------------------------------- incerteza (RF-14.2)
SOURCE_COLUMNS = ["Fonte", "Valor da grandeza", "Incerteza informada", "Distribuição", "n (Tipo A)"]
STANDARDIZATION_EXAMPLE = pd.DataFrame({
    "Fonte": ["Massa do padrão (balança)", "Volume gasto (bureta)", "", ""],
    "Valor da grandeza": ["0,5105", "25", "", ""],
    "Incerteza informada": ["0,0001", "0,02", "", ""],
    "Distribuição": ["Incerteza padrão (u)", "Incerteza padrão (u)", None, None],
    "n (Tipo A)": ["", "", "", ""]})


def page_uncertainty():
    didactic("**GUM em 4 passos:** (1) liste as fontes de incerteza; (2) converta cada uma em incerteza padrão "
             "(certificado: U/k; tolerância ±a: a/√3 retangular ou a/√6 triangular; repetições: s/√n); "
             "(3) combine: em fórmulas de produto/quociente, as **incertezas relativas** somam em quadratura, "
             "`u_c/y = √Σ(uᵢ/xᵢ)²`; (4) expanda: `U = k·u_c` (k = 2 ≈ 95 %). O gráfico mostra qual fonte pesa mais.",
             {"unc_y": "0,09999", "unc_unit": "mol/L", "unc_rows": STANDARDIZATION_EXAMPLE}, "unc")
    st.caption("Modelo de produto/quociente (ex.: `C = m / (M·V)`, titulações, diluições). Informe o resultado e o "
               "valor de cada grandeza com sua incerteza.")
    cols = st.columns(3)
    with cols[0]:
        y = num("Resultado (y)", None, "unc_y")
    with cols[1]:
        unit = text("Unidade", "unc_unit")
    with cols[2]:
        kmode = radio("Fator de abrangência", ["k = 2", "k pela t de Student (ν_eff)"], "unc_k")
    df = editor(pd.DataFrame({c: [""] * 4 if c != "Distribuição" else [None] * 4 for c in SOURCE_COLUMNS}), "unc_rows",
                column_config={"Distribuição": st.column_config.SelectboxColumn(options=list(uncertainty.DISTRIBUTIONS))})
    try:
        if y is None:
            raise ValueError("Informe o Resultado (y).")
        sources = []
        for i, row in enumerate(df.itertuples(index=False), 1):
            name, val, unc, dist, n = row
            name = name.strip() if isinstance(name, str) else ""
            if not name and parse_number(val) is None and parse_number(unc) is None:
                continue
            if not dist:
                raise ValueError(f"Linha {i}: escolha a distribuição.")
            nn = parse_number(n)
            sources.append({"name": name or f"Fonte {i}", "value": parse_number(val), "uncertainty": parse_number(unc),
                            "distribution": dist, "n": None if nn is None else int(nn)})
            if sources[-1]["value"] is None:
                raise ValueError(f"Linha {i}: informe o valor da grandeza.")
        r = uncertainty.budget(y, sources, 2.0 if kmode == "k = 2" else None)
    except ValueError as e:
        show_error(e)
        return
    st.metric("Resultado com incerteza expandida", f"{f(r['result'])} ± {f(r['U'])} {unit}")
    st.caption(f"k = {f(r['k'], '', 2)}, ~95 % · u_c = {f(r['u_c'])} {unit} · incerteza relativa "
               f"{f(r['u_rel'] * 100, '%', 3)} · ν_eff = {'∞' if math.isinf(r['nu_eff']) else f(r['nu_eff'], '', 1)}")
    rows = [(s["name"], f(s["value"]), f(s["u"]), f(s["u_rel"] * 100, "%", 4), f(s["contribution"], "%", 1))
            for s in r["sources"]]
    show_table(rows, ("Fonte", "Valor", "u (padrão)", "u relativa", "Contribuição"))
    st.altair_chart(bar_chart([s["name"] for s in r["sources"]], [s["contribution"] for s in r["sources"]],
                              "Contribuição para a variância (%)", "Fonte").properties(title="Orçamento de incerteza"))
    export("Incerteza de medição (GUM)", [(s[0], f"{s[1]} (u = {s[2]})") for s in rows],
           [(s[0], f"contribuição {s[4]}") for s in rows],
           [("Resultado", f"{f(r['result'])} ± {f(r['U'])} {unit} (k = {f(r['k'], '', 2)})")], "incerteza")
