"""Analytica Lab Engine — interface Streamlit.

Toda a química está em modules/; aqui ficam só entrada, exibição e exportação.
Campos numéricos são texto para aceitar vírgula decimal (RNF-02).
"""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from modules import conversions, methods, spectro, stats, titration
from utils import report
from utils.formatting import fmt, parse_number

st.set_page_config(page_title="Analytica Lab Engine", page_icon="⚗️", layout="wide")

# ---------------------------------------------------------------- sidebar
st.sidebar.title("⚗️ Analytica Lab Engine")
st.sidebar.caption("Cálculos de laboratório analítico")
st.sidebar.subheader("Rastreabilidade")
sample_id = st.sidebar.text_input("ID da amostra")
analyst = st.sidebar.text_input("Analista")
lot = st.sidebar.text_input("Lote do reagente / titulante")
st.sidebar.subheader("Exibição")
D = st.sidebar.slider("Casas decimais", 2, 6, 4)


# ---------------------------------------------------------------- helpers de UI
def to_input(x):
    return "" if x is None else f"{x:g}".replace(".", ",")


def num(label, default=None, key=None, help=None):
    """Campo numérico em texto; inválido → erro sob o campo e None (o cálculo pede o valor)."""
    raw = st.text_input(label, to_input(default), key=key, help=help)
    try:
        return parse_number(raw)
    except ValueError as e:
        st.error(str(e))
        return None


def column_editor(label, defaults, key, rows=6):
    df = pd.DataFrame({label: [to_input(v) for v in defaults] + [""] * max(rows - len(defaults), 0)})
    return st.data_editor(df, key=key, num_rows="dynamic", hide_index=True)[label]


def parse_column(series):
    return [x for x in (parse_number(v) for v in series) if x is not None]


def parse_nan(v):
    x = parse_number(v)
    return float("nan") if x is None else x


def show_error(e):
    """Campo ainda não preenchido é orientação (info), o resto é erro."""
    msg = str(e)
    (st.info if msg.startswith(("Informe", "Nenhum valor")) else st.error)(msg)


def show_table(rows):
    st.dataframe(pd.DataFrame(rows, columns=["Etapa", "Valor"]), hide_index=True)


def show_warnings(warnings):
    for w in warnings:
        st.warning(w)


def stats_rows(s, unit=""):
    rows = [("Réplicas (n)", str(s["n"])), ("Média", fmt(s["mean"], D, unit))]
    if s["sd"] is not None:
        rows += [("Desvio padrão (s)", fmt(s["sd"], D, unit)),
                 ("CV / RSD", fmt(s["cv"], 2, "%")),
                 (f"IC {s['confidence']:.0%} (t = {fmt(s['t'], 3)})", "± " + fmt(s["ci_half"], D, unit))]
    return rows


def grubbs_note(values, alpha=0.05):
    if len(values) < 3:
        return
    g = stats.grubbs(values, alpha)
    if not g["applicable"]:
        return
    a = fmt(alpha, 2)
    if g["is_outlier"]:
        st.warning(f"Grubbs (α = {a}): {fmt(g['suspect'], D)} é outlier (G = {fmt(g['G'], 3)} > "
                   f"G crítico = {fmt(g['G_crit'], 3)}). Avalie repetir ou remover essa réplica.")
    else:
        st.caption(f"Grubbs (α = {a}): nenhum outlier (G = {fmt(g['G'], 3)} ≤ {fmt(g['G_crit'], 3)}).")


def values_text(values, unit=""):
    return "; ".join(fmt(v, D) for v in values) + (f" {unit}" if unit else "")


def export(title, inputs, steps, results, key):
    now = datetime.now()
    meta = {"Amostra": sample_id or "—", "Analista": analyst or "—", "Lote do reagente": lot or "—",
            "Data/hora": now.strftime("%d/%m/%Y %H:%M")}
    rep = {"title": title, "inputs": inputs, "steps": steps, "results": results}
    name = f"{key}_{now:%Y%m%d_%H%M}"
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Exportar CSV", report.to_csv(rep, meta), f"{name}.csv", "text/csv", key=f"{key}_csv")
    c2.download_button("⬇️ Exportar PDF", report.to_pdf(rep, meta), f"{name}.pdf", "application/pdf",
                       key=f"{key}_pdf")


def use_factor(f):
    """Callback: leva o f da Padronização para os campos de fator das outras abas (RF-02.3)."""
    txt = f"{f:.4f}".replace(".", ",")
    st.session_state["factor"] = f
    st.session_state["tit_f"] = txt
    for k, m in methods.METHODS.items():
        if m["kind"] == "titration":
            st.session_state[f"an_{k}_f"] = txt


# ---------------------------------------------------------------- curva de calibração (compartilhada)
def curve_inputs(key, unit):
    st.markdown("**Padrões da curva** — valores de exemplo, substitua pelos seus")
    std = st.data_editor(
        pd.DataFrame({f"Concentração ({unit})": ["0", "1", "2", "3", "4"],
                      "Absorbância": ["0,002", "0,101", "0,199", "0,302", "0,398"]}),
        key=f"{key}_std", num_rows="dynamic", hide_index=True)
    st.markdown("**Leituras da amostra**")
    smp = column_editor("Absorbância", [0.250], f"{key}_smp", rows=3)
    fd = num("Fator de diluição (FD)", 1, f"{key}_fd")
    return std, smp, fd


def curve_result(std, smp, fd, unit):
    """Calcula curva + amostra e mostra gráficos; devolve (resultado, linhas p/ relatório)."""
    xs = [parse_nan(v) for v in std.iloc[:, 0]]
    ys = [parse_nan(v) for v in std.iloc[:, 1]]
    curve = spectro.calibrate(xs, ys)
    absorbances = parse_column(smp)
    pred = spectro.predict(curve, absorbances, fd)

    st.metric("Concentração da amostra", fmt(pred["concentration"], D, unit))
    curve_rows = [("Equação", f"A = {fmt(curve['a'], D)}·c + {fmt(curve['b'], D)}"),
                  ("R²", fmt(curve["r2"], 5)),
                  ("s y/x", fmt(curve["s_yx"], D)),
                  ("LOD", fmt(curve["lod"], D, unit)),
                  ("LOQ", fmt(curve["loq"], D, unit))]
    steps = curve_rows + stats_rows(pred["stats"]) + [
        ("Concentração lida na curva", fmt(pred["c_read"], D, unit)),
        ("Fator de diluição", fmt(pred["dilution"], D))]
    show_table(steps)
    show_warnings(curve["warnings"] + pred["warnings"])
    show_curve(curve, unit, (pred["c_read"], pred["mean_absorbance"]))
    inputs = [("Padrões (conc.)", values_text(curve["x"], unit)),
              ("Padrões (absorbância)", values_text(curve["y"])),
              ("Leituras da amostra", values_text(absorbances))]
    return pred["concentration"], inputs, steps


def show_curve(curve, unit, sample):
    x = alt.X("c:Q", title=f"Concentração ({unit})")
    y = alt.Y("A:Q", title="Absorbância")
    pts = pd.DataFrame({"c": curve["x"], "A": curve["y"]})
    xmax = max(curve["x"] + [sample[0]])
    line = pd.DataFrame({"c": [0.0, xmax]})
    line["A"] = curve["a"] * line["c"] + curve["b"]
    chart = (alt.Chart(pts).mark_circle(size=80).encode(x, y)
             + alt.Chart(line).mark_line().encode(x, y)
             + alt.Chart(pd.DataFrame({"c": [sample[0]], "A": [sample[1]]}))
             .mark_point(shape="diamond", size=160, filled=True, color="#e4572e").encode(x, y))
    res = pd.DataFrame({"c": curve["x"], "r": curve["residuals"]})
    resid = (alt.Chart(res).mark_circle(size=60).encode(x, alt.Y("r:Q", title="Resíduo"))
             + alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(strokeDash=[4, 4]).encode(y="z:Q"))
    c1, c2 = st.columns(2)
    c1.altair_chart(chart.properties(title="Curva de calibração (◆ amostra)"))
    c2.altair_chart(resid.properties(title="Resíduos"))


# ---------------------------------------------------------------- abas
def page_analyses():
    key = st.selectbox("Análise", list(methods.METHODS), format_func=lambda k: methods.METHODS[k]["name"],
                       key="an_method")
    m = methods.METHODS[key]
    if m["kind"] == "titration":
        info = f"**{m['reference']}** · Titulante: {m['titrant']} · Indicador: {m['indicator']} · Resultado em {m['unit']}"
    else:
        info = f"**{m['reference']}** · {m['reagent']} · λ = {m['wavelength_nm']} nm · Resultado em {m['unit']}"
    st.info(info + (f"\n\n{m['notes']}" if m["notes"] else ""))
    (titration_method if m["kind"] == "titration" else spectro_method)(key, m)


def save_method_result(key, value):
    st.session_state.setdefault("method_results", {})[key] = value


def derived_results(key):
    """Dureza magnesiana e especiação da alcalinidade com os últimos resultados calculados."""
    res = st.session_state.get("method_results", {})
    try:
        if key in ("dureza_total", "dureza_calcica") and {"dureza_total", "dureza_calcica"} <= res.keys():
            mg = methods.magnesium_hardness(res["dureza_total"], res["dureza_calcica"])
            st.metric("Dureza magnesiana (total − cálcica)", fmt(mg, D, "mg CaCO₃/L"))
        if key in ("alcalinidade_p", "alcalinidade_t") and {"alcalinidade_p", "alcalinidade_t"} <= res.keys():
            sp = methods.alkalinity_speciation(res["alcalinidade_p"], res["alcalinidade_t"])
            st.markdown("**Especiação da alcalinidade (SM 2320 B)**")
            show_table([("Hidróxido (OH⁻)", fmt(sp["hydroxide"], D, "mg CaCO₃/L")),
                        ("Carbonato (CO₃²⁻)", fmt(sp["carbonate"], D, "mg CaCO₃/L")),
                        ("Bicarbonato (HCO₃⁻)", fmt(sp["bicarbonate"], D, "mg CaCO₃/L"))])
        else:
            return
        st.caption("Calculado com o último resultado de cada análise do par nesta sessão.")
    except ValueError as e:
        show_error(e)


def titration_method(key, m):
    k = f"an_{key}"
    p_zero = key == "alcalinidade_p" and st.checkbox("Não houve viragem com fenolftaleína (P = 0)", key=f"{k}_p0")
    col_in, col_out = st.columns([1, 1.4])
    if p_zero:
        save_method_result(key, 0.0)
        with col_out:
            st.metric(m["name"], fmt(0, D, m["unit"]))
            derived_results(key)
        return

    with col_in:
        vols = column_editor("Volume gasto (mL)", [], f"{k}_vols")
        back = m["blank_mode"] == "back"
        blank = num("Volume gasto no branco (mL)", None if back else 0, f"{k}_blank",
                    help="Retrotitulação: o branco gasta MAIS que a amostra." if back else None)
        c = num(f"Concentração do {m['titrant']} (mol/L)", m["c_default"], f"{k}_c")
        f = num("Fator de correção (f)", st.session_state.get("factor", 1), f"{k}_f")
        v = num("Volume da amostra (mL)", m["v_default"], f"{k}_v")
        fd = num("Fator de diluição (FD)", 1, f"{k}_fd")

    with col_out:
        try:
            values = parse_column(vols)
            r = methods.run_titration(key, values, blank, c, f, v, fd)
        except ValueError as e:
            show_error(e)
            return
        u = m["unit"]
        st.metric(m["name"], fmt(r["result"], D, u))
        steps = stats_rows(r["stats"], "mL") + [
            ("Branco", fmt(r["blank"], D, "mL")),
            ("Volume corrigido " + ("(branco − amostra)" if back else "(amostra − branco)"), fmt(r["v_corr"], D, "mL")),
            ("Espécie de expressão", fmt(r["mmol"], D, "mmol")),
            ("Resultado na amostra analisada", fmt(r["result_measured"], D, u)),
            ("Fator de diluição", fmt(r["dilution"], D))]
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        save_method_result(key, r["result"])
        derived_results(key)
        inputs = [("Método", f"{m['name']} ({m['reference']})"), ("Volumes gastos", values_text(values, "mL")),
                  ("Branco", fmt(blank, D, "mL")), (f"Concentração do {m['titrant']}", fmt(c, D, "mol/L")),
                  ("Fator de correção", fmt(f, D)), ("Volume da amostra", fmt(v, D, "mL"))]
        export(m["name"], inputs, steps, [(m["name"], fmt(r["result"], D, u))], k)


def spectro_method(key, m):
    k = f"an_{key}"
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        std, smp, fd = curve_inputs(k, m["unit"])
    with col_out:
        try:
            result, inputs, steps = curve_result(std, smp, fd, m["unit"])
        except ValueError as e:
            show_error(e)
            return
        export(m["name"], [("Método", f"{m['name']} ({m['reference']}, {m['wavelength_nm']} nm)")] + inputs,
               steps, [(m["name"], fmt(result, D, m["unit"]))], k)


def page_titration():
    mode = st.radio("Calcular", ["Concentração do analito (mol/L)", "Teor na amostra (% m/m)"],
                    horizontal=True, key="tit_mode")
    conc_mode = mode.startswith("Concentração")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        st.caption("Valores de exemplo — substitua pelos seus.")
        vols = column_editor("Volume gasto (mL)", [10.10, 10.20, 10.15], "tit_vols")
        blank = num("Volume do branco (mL)", 0.05, "tit_blank")
        c = num("Concentração do titulante (mol/L)", 0.1, "tit_c")
        f = num("Fator de correção (f)", st.session_state.get("factor", 1), "tit_f")
        r_ = num("Razão estequiométrica r (mol analito / mol titulante)", 1, "tit_r")
        if conc_mode:
            v_al = num("Volume da alíquota (mL)", 25, "tit_val")
            k_eq = num("Nº de equivalentes (opcional, para normalidade)", None, "tit_k")
        else:
            m_s = num("Massa da amostra (g)", 2.0, "tit_m")
            mm = num("Massa molar do analito (g/mol)", 60.05, "tit_mm")

    with col_out:
        try:
            values = parse_column(vols)
            if conc_mode:
                r = titration.analyte_concentration(values, blank, c, f, v_al, r_)
                label, value, unit = "Concentração do analito", r["concentration"], "mol/L"
            else:
                r = titration.mass_percent(values, blank, c, f, m_s, mm, r_)
                label, value, unit = "Teor", r["percent"], "% m/m"
        except ValueError as e:
            show_error(e)
            return
        st.metric(label, fmt(value, D, unit))
        steps = stats_rows(r["stats"], "mL") + [
            ("Branco", fmt(r["blank"], D, "mL")),
            ("Volume corrigido", fmt(r["v_corr"], D, "mL")),
            ("Titulante consumido", fmt(r["n_titrant"], D, "mol")),
            ("Analito", fmt(r["n_analyte"], D, "mol"))]
        if not conc_mode:
            steps.append(("Massa de analito", fmt(r["m_analyte"], D, "g")))
        results = [(label, fmt(value, D, unit))]
        if conc_mode and k_eq is not None:
            try:
                n_ = titration.normality(value, k_eq)
                results.append(("Normalidade", fmt(n_, D, "N")))
                st.metric("Normalidade", fmt(n_, D, "N"))
                st.caption("A IUPAC desaconselha a unidade normalidade; prefira mol/L.")
            except ValueError as e:
                show_error(e)
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        inputs = [("Volumes gastos", values_text(values, "mL")), ("Branco", fmt(blank, D, "mL")),
                  ("Concentração do titulante", fmt(c, D, "mol/L")), ("Fator de correção", fmt(f, D)),
                  ("Razão estequiométrica", fmt(r_, D))]
        inputs += ([("Volume da alíquota", fmt(v_al, D, "mL"))] if conc_mode else
                   [("Massa da amostra", fmt(m_s, D, "g")), ("Massa molar do analito", fmt(mm, D, "g/mol"))])
        export("Titulação", inputs, steps, results, "titulacao")


def page_standardization():
    options = list(titration.PRIMARY_STANDARDS) + ["Outro padrão"]
    std = st.selectbox("Padrão primário", options, key="pad_std")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        mm = num("Massa molar do padrão (g/mol)", titration.PRIMARY_STANDARDS.get(std), f"pad_mm_{std}")
        m = num("Massa do padrão (g)", 0.5105, "pad_m")
        vols = column_editor("Volume gasto (mL)", [25.00], "pad_vols")
        blank = num("Volume do branco (mL)", 0, "pad_blank")
        c_nom = num("Concentração nominal do titulante (mol/L)", 0.1, "pad_cnom")
        r_ = num("Razão r (mol titulante / mol padrão)", 2 if "Na₂CO₃" in std else 1, f"pad_r_{std}",
                 help="KHP + NaOH: 1 · Na₂CO₃ + 2 HCl: 2")
    with col_out:
        try:
            values = parse_column(vols)
            r = titration.standardize(m, mm, values, c_nom, r_, blank)
        except ValueError as e:
            show_error(e)
            return
        c1, c2 = st.columns(2)
        c1.metric("Concentração real", fmt(r["c_real"], D, "mol/L"))
        c2.metric("Fator de correção (f)", fmt(r["factor"], D))
        steps = stats_rows(r["stats"], "mL") + [
            ("Volume corrigido", fmt(r["v_corr"], D, "mL")),
            ("Padrão (m / M)", fmt(r["n_standard"], D, "mol"))]
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        st.button("Usar este fator nas abas Análises e Titulação", on_click=use_factor, args=(r["factor"],))
        if "factor" in st.session_state:
            st.caption(f"Fator em uso nas outras abas: {fmt(st.session_state['factor'], 4)}")
        inputs = [("Padrão", std), ("Massa molar", fmt(mm, D, "g/mol")), ("Massa do padrão", fmt(m, D, "g")),
                  ("Volumes gastos", values_text(values, "mL")), ("Branco", fmt(blank, D, "mL")),
                  ("Concentração nominal", fmt(c_nom, D, "mol/L")), ("Razão r", fmt(r_, D))]
        export("Padronização", inputs, steps, [("Concentração real", fmt(r["c_real"], D, "mol/L")),
                                               ("Fator de correção", fmt(r["factor"], D))], "padronizacao")


def page_statistics():
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        st.caption("Valores de exemplo — substitua pelos seus.")
        vals = column_editor("Valor", [10.10, 10.12, 10.15, 10.11, 10.90], "est_vals", rows=8)
        unit = st.text_input("Unidade (opcional)", key="est_unit")
        conf = st.select_slider("Nível de confiança", [0.90, 0.95, 0.99], 0.95, format_func=lambda x: f"{x:.0%}",
                                key="est_conf")
        alpha = st.select_slider("α do teste de Grubbs", [0.01, 0.05, 0.10], 0.05, key="est_alpha")
    with col_out:
        try:
            values = parse_column(vals)
            s = stats.describe(values, conf)
            st.metric("Média", fmt(s["mean"], D, unit))
            if s["ci_half"] is not None:
                st.markdown(f"**Resultado:** {fmt(s['mean'], D)} ± {fmt(s['ci_half'], D)} {unit} "
                            f"(IC {conf:.0%}, n = {s['n']})")
            steps = stats_rows(s, unit)
            show_table(steps)
            grubbs_note(values, alpha)
        except ValueError as e:
            show_error(e)
            return
        show_warnings(s["warnings"])
        export("Estatística de réplicas", [("Valores", values_text(values, unit))], steps,
               [("Média", fmt(s["mean"], D, unit))], "estatistica")


def page_spectro():
    mode = st.radio("Modo", ["Curva de calibração", "Beer-Lambert direto (A = ε·l·c)"], horizontal=True,
                    key="esp_mode")
    col_in, col_out = st.columns([1, 1.4])
    if mode.startswith("Beer"):
        with col_in:
            a = num("Absorbância (A)", None, "esp_a")
            eps = num("Absortividade molar ε (L·mol⁻¹·cm⁻¹)", None, "esp_eps")
            path = num("Caminho óptico l (cm)", 1, "esp_l")
        with col_out:
            try:
                st.metric("Concentração", fmt(spectro.beer_lambert(a, eps, path), D, "mol/L"))
                st.caption("c = A / (ε · l)")
            except ValueError as e:
                show_error(e)
        return

    with col_in:
        unit = st.text_input("Unidade de concentração", "mg/L", key="esp_unit")
        std, smp, fd = curve_inputs("esp", unit)
    with col_out:
        try:
            result, inputs, steps = curve_result(std, smp, fd, unit)
        except ValueError as e:
            show_error(e)
            return
        export("Espectrofotometria — curva de calibração", inputs, steps,
               [("Concentração da amostra", fmt(result, D, unit))], "espectro")


def page_dilution():
    st.subheader("C₁·V₁ = C₂·V₂")
    st.caption("Preencha três campos e deixe em branco o que quer calcular.")
    cols = st.columns(4)
    with cols[0]:
        c1 = num("C₁ (estoque)", None, "dil_c1")
    with cols[1]:
        v1 = num("V₁ (alíquota)", None, "dil_v1")
    with cols[2]:
        c2 = num("C₂ (final)", None, "dil_c2")
    with cols[3]:
        v2 = num("V₂ (final)", None, "dil_v2")
    if [c1, v1, c2, v2].count(None) == 4:
        st.info("Informe três dos quatro valores.")
    else:
        try:
            r = conversions.c1v1(c1, v1, c2, v2)
            st.metric(f"{dict(c1='C₁', v1='V₁', c2='C₂', v2='V₂')[r['solved']]} calculado", fmt(r["value"], D))
            show_warnings(r["warnings"])
        except ValueError as e:
            show_error(e)

    st.divider()
    st.subheader("Fator de diluição")
    cols = st.columns(2)
    with cols[0]:
        vf = num("Volume final (mL)", 100, "fd_vf")
    with cols[1]:
        va = num("Volume da alíquota (mL)", 10, "fd_va")
    try:
        st.metric("FD = V final / V alíquota", fmt(conversions.dilution_factor(vf, va), D))
    except ValueError as e:
        show_error(e)

    st.divider()
    st.subheader("Conversão de unidades")
    cols = st.columns(4)
    with cols[0]:
        val = num("Valor", 0.1, "conv_val")
    with cols[1]:
        u_from = st.selectbox("De", conversions.UNITS, key="conv_from")
    with cols[2]:
        u_to = st.selectbox("Para", conversions.UNITS, index=2, key="conv_to")
    with cols[3]:
        mm = num("Massa molar (g/mol)", 58.44, "conv_mm")
    try:
        st.metric("Resultado", fmt(conversions.convert_concentration(val, u_from, u_to, mm), D, u_to))
        st.caption("mg/L ≈ ppm em solução aquosa diluída.")
    except ValueError as e:
        show_error(e)


tabs = st.tabs(["🧪 Análises", "⚗️ Titulação", "🎯 Padronização", "📊 Estatística", "🌈 Espectrofotometria",
                "💧 Diluição"])
for tab, page in zip(tabs, [page_analyses, page_titration, page_standardization, page_statistics, page_spectro,
                            page_dilution]):
    with tab:
        page()
