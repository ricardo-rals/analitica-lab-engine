"""Seção Rotina: análises de água, bromatologia, titulação, padronização e espectrofotometria."""
import altair as alt
import pandas as pd
import streamlit as st

from modules import bromatology as br
from modules import methods, spectro, titration
from ui.common import (checkbox, column_editor, didactic, editor, example_df, export, f, grubbs_note, num,
                       parse_column, parse_nan, parse_rows, radio, select, set_fields, show_error, show_table,
                       show_warnings, stats_rows, table_editor, text, values_text)


def factor_default():
    return st.session_state.get("factor", 1)


def factor_keys():
    """Campos de fator f que recebem o valor da Padronização (RF-02.3)."""
    keys = ["tit_f", "brom_kj_f", "brom_ac_f"]
    return keys + [f"an_{k}_f" for k, m in methods.METHODS.items() if m["kind"] == "titration"]


def use_factor(value):
    st.session_state["factor"] = value
    set_fields({k: f"{value:.4f}".replace(".", ",") for k in factor_keys()})


# ---------------------------------------------------------------- curva de calibração (compartilhada)
def curve_inputs(key, unit):
    st.markdown("**Padrões da curva** — valores de exemplo, substitua pelos seus")
    std = editor(pd.DataFrame({f"Concentração ({unit})": ["0", "1", "2", "3", "4"],
                               "Absorbância": ["0,002", "0,101", "0,199", "0,302", "0,398"]}), f"{key}_std")
    st.markdown("**Leituras da amostra**")
    smp = column_editor("Absorbância", [0.250], f"{key}_smp", rows=3)
    fd = num("Fator de diluição (FD)", 1, f"{key}_fd")
    return std, smp, fd


def curve_result(std, smp, fd, unit):
    """Calcula curva + amostra, mostra gráficos e diagnóstico; devolve (resultado, entradas, etapas)."""
    curve = spectro.calibrate([parse_nan(v) for v in std.iloc[:, 0]], [parse_nan(v) for v in std.iloc[:, 1]])
    absorbances = parse_column(smp)
    pred = spectro.predict(curve, absorbances, fd)

    st.metric("Concentração da amostra", f"{f(pred['concentration'], unit)} ± {f(pred['s_x0'])}")
    st.caption("± s_x0: desvio padrão da concentração estimada pela curva.")
    steps = [("Equação", f"A = {f(curve['a'])}·c + {f(curve['b'])}"), ("R²", f(curve["r2"], "", 5)),
             ("s y/x", f(curve["s_yx"])), ("LOD", f(curve["lod"], unit)), ("LOQ", f(curve["loq"], unit))]
    steps += stats_rows(pred["stats"]) + [("Concentração lida na curva", f(pred["c_read"], unit)),
                                         ("s_x0", f(pred["s_x0"], unit)), ("Fator de diluição", f(pred["dilution"]))]
    show_table(steps)
    show_warnings(curve["warnings"] + pred["warnings"])
    show_curve(curve, unit, (pred["c_read"], pred["mean_absorbance"]))
    show_diagnostics(curve)
    inputs = [("Padrões (conc.)", values_text(curve["x"], unit)), ("Padrões (absorbância)", values_text(curve["y"])),
              ("Leituras da amostra", values_text(absorbances))]
    return pred["concentration"], inputs, steps


def show_curve(curve, unit, sample):
    x = alt.X("c:Q", title=f"Concentração ({unit})")
    y = alt.Y("A:Q", title="Absorbância")
    pts = pd.DataFrame({"c": curve["x"], "A": curve["y"]})
    line = pd.DataFrame({"c": [0.0, max(curve["x"] + [sample[0]])]})
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


def show_diagnostics(curve):
    """RF-14.1: IC de a e b, teste do intercepto, falta de ajuste e Cochran."""
    d = spectro.curve_diagnostics(curve)
    with st.expander("🔬 Diagnóstico da curva (IC, intercepto, falta de ajuste, homocedasticidade)"):
        rows = [("IC 95 % da inclinação a", f"{f(d['ci_a'][0])} a {f(d['ci_a'][1])}"),
                ("IC 95 % do intercepto b", f"{f(d['ci_b'][0])} a {f(d['ci_b'][1])}"),
                ("Teste b = 0", f"t = {f(d['t_b'], '', 3)}; p = {f(d['p_b'], '', 4)} → "
                 + ("intercepto significativo" if d["intercept_significant"] else "intercepto não significativo"))]
        if d["lack_of_fit"]:
            lof = d["lack_of_fit"]
            rows.append(("Falta de ajuste", f"F = {f(lof['F'], '', 3)}; p = {f(lof['p'], '', 4)} → "
                         + ("modelo linear inadequado" if lof["significant"] else "modelo linear adequado")))
        if d["cochran"]:
            c = d["cochran"]
            rows.append(("Homocedasticidade (Cochran)", f"C = {f(c['C'], '', 4)}; C crít = {f(c['C_crit'], '', 4)} → "
                         + ("homocedástico" if c["homoscedastic"] else "heterocedástico")))
        show_table(rows, ("Teste", "Resultado"))
        for note in d["notes"]:
            st.caption(note)


# ---------------------------------------------------------------- análises de água (catálogo)
def page_analyses():
    key = select("Análise", list(methods.METHODS), "an_method", format_func=lambda k: methods.METHODS[k]["name"])
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
            st.metric("Dureza magnesiana (total − cálcica)", f(mg, "mg CaCO₃/L"))
        elif key in ("alcalinidade_p", "alcalinidade_t") and {"alcalinidade_p", "alcalinidade_t"} <= res.keys():
            sp = methods.alkalinity_speciation(res["alcalinidade_p"], res["alcalinidade_t"])
            st.markdown("**Especiação da alcalinidade (SM 2320 B)**")
            show_table([("Hidróxido (OH⁻)", f(sp["hydroxide"], "mg CaCO₃/L")),
                        ("Carbonato (CO₃²⁻)", f(sp["carbonate"], "mg CaCO₃/L")),
                        ("Bicarbonato (HCO₃⁻)", f(sp["bicarbonate"], "mg CaCO₃/L"))])
        else:
            return
        st.caption("Calculado com o último resultado de cada análise do par nesta sessão.")
    except ValueError as e:
        show_error(e)


def titration_method(key, m):
    k = f"an_{key}"
    p_zero = key == "alcalinidade_p" and checkbox("Não houve viragem com fenolftaleína (P = 0)", f"{k}_p0")
    col_in, col_out = st.columns([1, 1.4])
    if p_zero:
        save_method_result(key, 0.0)
        with col_out:
            st.metric(m["name"], f(0, m["unit"]))
            derived_results(key)
        return

    back = m["blank_mode"] == "back"
    with col_in:
        vols = column_editor("Volume gasto (mL)", [], f"{k}_vols")
        blank = num("Volume gasto no branco (mL)", None if back else 0, f"{k}_blank",
                    help="Retrotitulação: o branco gasta MAIS que a amostra." if back else None)
        c = num(f"Concentração do {m['titrant']} (mol/L)", m["c_default"], f"{k}_c")
        fac = num("Fator de correção (f)", factor_default(), f"{k}_f")
        v = num("Volume da amostra (mL)", m["v_default"], f"{k}_v")
        fd = num("Fator de diluição (FD)", 1, f"{k}_fd")

    with col_out:
        try:
            values = parse_column(vols)
            r = methods.run_titration(key, values, blank, c, fac, v, fd)
        except ValueError as e:
            show_error(e)
            return
        u = m["unit"]
        st.metric(m["name"], f(r["result"], u))
        steps = stats_rows(r["stats"], "mL") + [
            ("Branco", f(r["blank"], "mL")),
            ("Volume corrigido " + ("(branco − amostra)" if back else "(amostra − branco)"), f(r["v_corr"], "mL")),
            ("Espécie de expressão", f(r["mmol"], "mmol")),
            ("Resultado na amostra analisada", f(r["result_measured"], u)),
            ("Fator de diluição", f(r["dilution"]))]
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        save_method_result(key, r["result"])
        derived_results(key)
        inputs = [("Método", f"{m['name']} ({m['reference']})"), ("Volumes gastos", values_text(values, "mL")),
                  ("Branco", f(blank, "mL")), (f"Concentração do {m['titrant']}", f(c, "mol/L")),
                  ("Fator de correção", f(fac)), ("Volume da amostra", f(v, "mL"))]
        export(m["name"], inputs, steps, [(m["name"], f(r["result"], u))], k)


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
               steps, [(m["name"], f(result, m["unit"]))], k)


# ---------------------------------------------------------------- titulação livre
def page_titration():
    didactic("**Titulação:** o volume gasto, descontado o branco, dá os mols de titulante "
             "(`n = C · f · V`). A estequiometria (r) converte em mols de analito; dividindo pelo volume da "
             "alíquota sai a concentração, ou multiplicando pela massa molar e dividindo pela massa da amostra "
             "sai o teor (% m/m).",
             {"tit_vols": example_df(["Volume gasto (mL)"], [(10.10,), (10.20,), (10.15,)]), "tit_blank": "0,05",
              "tit_c": "0,1", "tit_f": "1", "tit_r": "1", "tit_val": "25"}, "tit")
    mode = radio("Calcular", ["Concentração do analito (mol/L)", "Teor na amostra (% m/m)"], "tit_mode",
                 horizontal=True)
    conc_mode = mode.startswith("Concentração")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        st.caption("Valores de exemplo — substitua pelos seus.")
        vols = column_editor("Volume gasto (mL)", [10.10, 10.20, 10.15], "tit_vols")
        blank = num("Volume do branco (mL)", 0.05, "tit_blank")
        c = num("Concentração do titulante (mol/L)", 0.1, "tit_c")
        fac = num("Fator de correção (f)", factor_default(), "tit_f")
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
                r = titration.analyte_concentration(values, blank, c, fac, v_al, r_)
                label, value, unit = "Concentração do analito", r["concentration"], "mol/L"
            else:
                r = titration.mass_percent(values, blank, c, fac, m_s, mm, r_)
                label, value, unit = "Teor", r["percent"], "% m/m"
        except ValueError as e:
            show_error(e)
            return
        st.metric(label, f(value, unit))
        steps = stats_rows(r["stats"], "mL") + [
            ("Branco", f(r["blank"], "mL")), ("Volume corrigido", f(r["v_corr"], "mL")),
            ("Titulante consumido", f(r["n_titrant"], "mol")), ("Analito", f(r["n_analyte"], "mol"))]
        if not conc_mode:
            steps.append(("Massa de analito", f(r["m_analyte"], "g")))
        results = [(label, f(value, unit))]
        if conc_mode and k_eq is not None:
            try:
                n_ = titration.normality(value, k_eq)
                results.append(("Normalidade", f(n_, "N")))
                st.metric("Normalidade", f(n_, "N"))
                st.caption("A IUPAC desaconselha a unidade normalidade; prefira mol/L.")
            except ValueError as e:
                show_error(e)
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        inputs = [("Volumes gastos", values_text(values, "mL")), ("Branco", f(blank, "mL")),
                  ("Concentração do titulante", f(c, "mol/L")), ("Fator de correção", f(fac)),
                  ("Razão estequiométrica", f(r_))]
        inputs += ([("Volume da alíquota", f(v_al, "mL"))] if conc_mode else
                   [("Massa da amostra", f(m_s, "g")), ("Massa molar do analito", f(mm, "g/mol"))])
        export("Titulação", inputs, steps, results, "titulacao")


# ---------------------------------------------------------------- padronização
def page_standardization():
    options = list(titration.PRIMARY_STANDARDS) + ["Outro padrão"]
    std = select("Padrão primário", options, "pad_std")
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
        c1.metric("Concentração real", f(r["c_real"], "mol/L"))
        c2.metric("Fator de correção (f)", f(r["factor"]))
        steps = stats_rows(r["stats"], "mL") + [("Volume corrigido", f(r["v_corr"], "mL")),
                                               ("Padrão (m / M)", f(r["n_standard"], "mol"))]
        show_table(steps)
        grubbs_note(values)
        show_warnings(r["warnings"])
        st.button("Usar este fator nas outras páginas (Análises, Titulação, Bromatologia)", on_click=use_factor,
                  args=(r["factor"],))
        if "factor" in st.session_state:
            st.caption(f"Fator em uso nas outras páginas: {f(st.session_state['factor'], '', 4)}")
        inputs = [("Padrão", std), ("Massa molar", f(mm, "g/mol")), ("Massa do padrão", f(m, "g")),
                  ("Volumes gastos", values_text(values, "mL")), ("Branco", f(blank, "mL")),
                  ("Concentração nominal", f(c_nom, "mol/L")), ("Razão r", f(r_))]
        export("Padronização", inputs, steps, [("Concentração real", f(r["c_real"], "mol/L")),
                                               ("Fator de correção", f(r["factor"]))], "padronizacao")


# ---------------------------------------------------------------- espectrofotometria
def page_spectro():
    didactic("**Curva de calibração:** os padrões dão a reta `A = a·c + b` por mínimos quadrados. A amostra é "
             "lida na reta ao contrário: `c = (A − b) / a`. O LOD (3,3·s/a) e o LOQ (10·s/a) vêm da dispersão dos "
             "pontos em torno da reta (s y/x). O **s_x0** é a incerteza da concentração lida.", key="esp")
    mode = radio("Modo", ["Curva de calibração", "Beer-Lambert direto (A = ε·l·c)"], "esp_mode", horizontal=True)
    col_in, col_out = st.columns([1, 1.4])
    if mode.startswith("Beer"):
        with col_in:
            a = num("Absorbância (A)", None, "esp_a")
            eps = num("Absortividade molar ε (L·mol⁻¹·cm⁻¹)", None, "esp_eps")
            path = num("Caminho óptico l (cm)", 1, "esp_l")
        with col_out:
            try:
                st.metric("Concentração", f(spectro.beer_lambert(a, eps, path), "mol/L"))
                st.caption("c = A / (ε · l)")
            except ValueError as e:
                show_error(e)
        return

    with col_in:
        unit = text("Unidade de concentração", "esp_unit", "mg/L")
        std, smp, fd = curve_inputs("esp", unit)
    with col_out:
        try:
            result, inputs, steps = curve_result(std, smp, fd, unit)
        except ValueError as e:
            show_error(e)
            return
        export("Espectrofotometria — curva de calibração", inputs, steps,
               [("Concentração da amostra", f(result, unit))], "espectro")


# ---------------------------------------------------------------- bromatologia (RF-09)
BROM_ANALYSES = ["Umidade e matéria seca", "Cinzas e matéria orgânica", "Proteína bruta (Kjeldahl)",
                 "Extrato etéreo (Soxhlet)", "Fibra em detergente ácido (FDA)", "Acidez",
                 "📋 Ficha da amostra e CNF"]


def sheet():
    """Ficha da amostra atual (ID da barra lateral): {análise: resultado em %MN}."""
    sid = st.session_state.get("sample_id") or "(sem ID)"
    return sid, st.session_state.setdefault("fichas", {}).setdefault(sid, {})


def dry_matter_input(key):
    """MS para base seca: vem da umidade já calculada na ficha ou é digitada."""
    _, data = sheet()
    if "MS" in data:
        st.caption(f"Base seca com MS = {f(data['MS'], '%', 2)} (da umidade desta ficha).")
        return data["MS"]
    return num("MS (%) para expressar em base seca (opcional)", None, f"{key}_ms")


def tolerance_input(key):
    return num("Tolerância: CV máximo entre réplicas (%)", br.DEFAULT_TOLERANCE_CV, f"{key}_tol",
               help="Padrão do app; ajuste conforme o POP do laboratório.")


def brom_output(title, key, metrics, r, inputs, extra_steps=(), unit="%"):
    """Bloco comum de resultado: métricas, réplicas, estatística, avisos, ficha e exportação."""
    cols = st.columns(len(metrics))
    for col, (label, value, u) in zip(cols, metrics):
        col.metric(label, "—" if value is None else f(value, u, 2))
    steps = [(f"Réplica {i}", f(v, unit)) for i, v in enumerate(r["replicates"], 1)]
    steps += stats_rows(r["stats"], unit) + list(extra_steps)
    show_table(steps)
    grubbs_note(r["replicates"])
    show_warnings(r["warnings"])
    sid, data = sheet()
    st.caption(f"Resultado guardado na ficha da amostra **{sid}**.")
    export(title, inputs, steps, [(label, "—" if v is None else f(v, u, 2)) for label, v, u in metrics], key)
    return data


def page_bromatology():
    st.caption("Composição de alimentos e rações em % (g/100 g), na matéria natural (MN) e na matéria seca (MS). "
               "Os resultados de cada análise vão para a ficha da amostra (ID na barra lateral).")
    kind = select("Análise", BROM_ANALYSES, "brom_kind")
    {BROM_ANALYSES[0]: brom_moisture, BROM_ANALYSES[1]: brom_ash, BROM_ANALYSES[2]: brom_kjeldahl,
     BROM_ANALYSES[3]: brom_ether, BROM_ANALYSES[4]: brom_adf, BROM_ANALYSES[5]: brom_acidity,
     BROM_ANALYSES[6]: brom_sheet}[kind]()


def brom_moisture():
    st.info("**Estufa a 105 °C até massa constante** · AOAC 930.15 / 934.01")
    didactic("`Umidade (%) = (tara + amostra − tara+seca) / amostra × 100` e `MS = 100 − umidade`. "
             "**Pré-secagem** (silagem, forragem verde): `MS = ASA × ASE / 100`, onde ASA é a amostra seca ao ar "
             "(55–60 °C) e ASE a seca em estufa (105 °C).",
             {"brom_um_rows": example_df(["Tara (g)", "Amostra (g)", "Tara + amostra seca (g)"],
                                         [(20.0, 2.0, 21.82), (20.5, 2.001, 22.3205)])}, "brom_um")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["Tara (g)", "Amostra (g)", "Tara + amostra seca (g)"], "brom_um_rows")
        tol = tolerance_input("brom_um")
        pre = checkbox("Amostra pré-seca (ASA)", "brom_um_pre")
        asa = num("ASA (%)", None, "brom_um_asa") if pre else None
    with col_out:
        try:
            r = br.moisture(parse_rows(df), tol)
            ms = br.predried_dry_matter(asa, r["dry_matter"]) if pre else r["dry_matter"]
        except ValueError as e:
            show_error(e)
            return
        data = brom_output("Umidade e matéria seca", "brom_um",
                           [("Umidade", 100 - ms, "%"), ("Matéria seca", ms, "%")], r,
                           [("Condições", "Estufa 105 °C até massa constante")]
                           + ([("ASA", f(asa, "%"))] if pre else []),
                           [("ASE (MS a 105 °C)", f(r["dry_matter"], "%"))] if pre else [])
        data.update({"Umidade": 100 - ms, "MS": ms})


def brom_ash():
    st.info("**Mufla a 550 °C por 5 h** · AOAC 942.05")
    didactic("`MM (%) = (cadinho+cinzas − cadinho) / amostra × 100`. Na base seca, `MO (%MS) = 100 − MM (%MS)`.",
             {"brom_mm_rows": example_df(["Cadinho (g)", "Amostra (g)", "Cadinho + cinzas (g)"],
                                         [(20.0, 2.0, 20.12), (21.0, 2.0, 21.1205)])}, "brom_mm")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["Cadinho (g)", "Amostra (g)", "Cadinho + cinzas (g)"], "brom_mm_rows")
        tol = tolerance_input("brom_mm")
        ms = dry_matter_input("brom_mm")
    with col_out:
        try:
            r = br.ash(parse_rows(df), ms, tol)
        except ValueError as e:
            show_error(e)
            return
        data = brom_output("Cinzas e matéria orgânica", "brom_mm",
                           [("Cinzas (MN)", r["ash"], "%"), ("Cinzas (MS)", r["ash_dm"], "%"),
                            ("Matéria orgânica (MS)", r["organic_matter_dm"], "%")], r,
                           [("Condições", "Mufla 550 °C / 5 h")])
        data["MM"] = r["ash"]


def brom_kjeldahl():
    st.info("**Kjeldahl** · digestão com H₂SO₄ e catalisador CuSO₄/K₂SO₄ · NH₃ recolhida em ácido bórico e "
            "titulada com ácido padronizado · AOAC 984.13 / 2001.11")
    didactic("`N (%) = (V − V branco) × C × f × r × 14,007 / (m × 1000) × 100` e `PB = N × F`. "
             "O fator F converte nitrogênio em proteína (6,25 supõe 16 % de N na proteína).",
             {"brom_kj_rows": example_df(["Massa da amostra (g)", "Volume gasto (mL)"], [(0.2, 10.0), (0.2010, 10.02)]),
              "brom_kj_blank": "0,1", "brom_kj_c": "0,1"}, "brom_kj")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["Massa da amostra (g)", "Volume gasto (mL)"], "brom_kj_rows")
        blank = num("Volume do branco (mL)", 0, "brom_kj_blank")
        acid = radio("Titulante", ["HCl (r = 1)", "H₂SO₄ (r = 2)"], "brom_kj_acid", horizontal=True)
        c = num("Concentração do titulante (mol/L)", 0.1, "brom_kj_c")
        fac = num("Fator de correção (f)", factor_default(), "brom_kj_f")
        matrix = select("Matriz (fator N → proteína)", list(br.NITROGEN_FACTORS) + ["Outro"], "brom_kj_matrix")
        pf = num("Fator F", br.NITROGEN_FACTORS.get(matrix), f"brom_kj_pf_{matrix}")
        tol = tolerance_input("brom_kj")
        ms = dry_matter_input("brom_kj")
    with col_out:
        try:
            r = br.kjeldahl(parse_rows(df), blank, c, fac, 2 if acid.startswith("H₂SO₄") else 1, pf, ms, tol)
        except ValueError as e:
            show_error(e)
            return
        data = brom_output("Proteína bruta (Kjeldahl)", "brom_kj",
                           [("Nitrogênio (MN)", r["nitrogen"], "%"), ("Proteína bruta (MN)", r["protein"], "%"),
                            ("Proteína bruta (MS)", r["protein_dm"], "%")],
                           {**r, "replicates": [v * r["protein_factor"] for v in r["replicates"]],
                            "stats": {**r["stats"], "mean": r["protein"],
                                      "sd": None if r["stats"]["sd"] is None else r["stats"]["sd"] * r["protein_factor"],
                                      "ci_half": None if r["stats"]["ci_half"] is None
                                      else r["stats"]["ci_half"] * r["protein_factor"]}},
                           [("Catalisador", "CuSO₄/K₂SO₄"), ("Titulante", acid), ("Concentração", f(c, "mol/L")),
                            ("Branco", f(blank, "mL")), ("Fator F", f(pf, "", 2))],
                           [("Nitrogênio (média)", f(r["nitrogen"], "%"))])
        data["PB"] = r["protein"]


def brom_ether():
    st.info("**Soxhlet com éter de petróleo** · AOAC 920.39")
    didactic("`EE (%) = (balão+gordura − balão) / amostra × 100`: a gordura extraída fica no balão, que é pesado "
             "antes e depois da extração (após evaporar o solvente).",
             {"brom_ee_rows": example_df(["Balão (g)", "Amostra (g)", "Balão + gordura (g)"],
                                         [(100.0, 2.0, 100.06), (98.5, 2.0, 98.5605)])}, "brom_ee")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["Balão (g)", "Amostra (g)", "Balão + gordura (g)"], "brom_ee_rows")
        tol = tolerance_input("brom_ee")
        ms = dry_matter_input("brom_ee")
    with col_out:
        try:
            r = br.ether_extract(parse_rows(df), ms, tol)
        except ValueError as e:
            show_error(e)
            return
        data = brom_output("Extrato etéreo", "brom_ee", [("EE (MN)", r["ether_extract"], "%"),
                                                         ("EE (MS)", r["ether_extract_dm"], "%")], r,
                           [("Método", "Soxhlet"), ("Solvente", "Éter de petróleo")])
        data["EE"] = r["ether_extract"]


def brom_adf():
    st.info("**Saquinho filtrante (Ankom)** com correção pelo saco branco · AOAC 973.18")
    didactic("`FDA (%) = (W3 − W1 × C1) / W2 × 100`. W1 = saco vazio, W2 = amostra, W3 = saco + resíduo seco. "
             "O saco branco (sem amostra) corrige a variação de massa do próprio saco: "
             "`C1 = massa final do branco / massa inicial`.",
             {"brom_fda_rows": example_df(["W1 saco (g)", "W2 amostra (g)", "W3 saco + resíduo (g)"],
                                          [(0.5, 0.5, 0.65), (0.502, 0.501, 0.6515)]),
              "brom_fda_bi": "0,5", "brom_fda_bf": "0,501"}, "brom_fda")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["W1 saco (g)", "W2 amostra (g)", "W3 saco + resíduo (g)"], "brom_fda_rows")
        bi = num("Saco branco: massa inicial (g)", None, "brom_fda_bi")
        bf = num("Saco branco: massa final seca (g)", None, "brom_fda_bf")
        tol = tolerance_input("brom_fda")
        ms = dry_matter_input("brom_fda")
    with col_out:
        try:
            r = br.adf_filter_bag(parse_rows(df), bi, bf, ms, tol)
        except ValueError as e:
            show_error(e)
            return
        data = brom_output("Fibra em detergente ácido", "brom_fda", [("FDA (MN)", r["adf"], "%"),
                                                                      ("FDA (MS)", r["adf_dm"], "%")], r,
                           [("Método", "Saquinho filtrante (Ankom)"), ("Branco", f"{f(bi, 'g')} → {f(bf, 'g')}")],
                           [("C1 (correção do branco)", f(r["c1"], "", 4))])
        data["FDA"] = r["adf"]


def brom_acidity():
    st.info("**Acidez titulável** com NaOH padronizado · IAL 016/IV; óleos: AOCS Ca 5a-40")
    didactic("`% = V × C × f × M / (k × m × 10)`: os mols de NaOH (`V·C·f`) divididos pelo nº de H⁺ do ácido (k) "
             "dão os mols de ácido; vezes a massa molar dá a massa. Amostra líquida (mL): `g/L = % × 10`. "
             "Leite: `°Dornic = g/L de ácido lático × 10`.",
             {"brom_ac_rows": example_df(["Amostra (g ou mL)", "Volume de NaOH (mL)"], [(10.0, 10.0), (10.0, 10.05)]),
              "brom_ac_c": "0,1", "brom_ac_acid": "Cítrico", "brom_ac_unit": "g"}, "brom_ac")
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        df = table_editor(["Amostra (g ou mL)", "Volume de NaOH (mL)"], "brom_ac_rows")
        unit = radio("Amostra medida em", ["g", "mL"], "brom_ac_unit", horizontal=True)
        acid = select("Ácido de expressão", list(br.ACIDS), "brom_ac_acid")
        c = num("Concentração do NaOH (mol/L)", 0.1, "brom_ac_c")
        fac = num("Fator de correção (f)", factor_default(), "brom_ac_f")
        tol = tolerance_input("brom_ac")
    with col_out:
        try:
            r = br.acidity(parse_rows(df), c, acid, fac, unit, tolerance_cv=tol)
        except ValueError as e:
            show_error(e)
            return
        metrics = [(f"Acidez ({r['percent_unit']}, {acid.split(' ')[0].lower()})", r["percent"], "%")]
        if r["g_per_l"] is not None:
            metrics.append(("Concentração", r["g_per_l"], "g/L"))
        if r["dornic"] is not None:
            metrics.append(("Acidez Dornic", r["dornic"], "°D"))
        if r["acid_index"] is not None and acid.startswith("Oleico"):
            metrics.append(("Índice de acidez", r["acid_index"], "mg KOH/g"))
        per = "100 mL" if unit == "mL" else "100 g"
        data = brom_output("Acidez", "brom_ac", metrics, r,
                           [("Ácido de expressão", acid), ("Titulante", f"NaOH {f(c, 'mol/L')}"), ("Fator", f(fac))],
                           [("Acidez em solução normal", f(r["normal_solution"], f"mL/{per}"))])
        data["Acidez"] = r["percent"]


def brom_sheet():
    sid, data = sheet()
    st.subheader(f"Ficha da amostra: {sid}")
    st.caption("Troque o ID da amostra na barra lateral para abrir outra ficha.")
    if not data:
        st.info("Nenhuma análise calculada ainda para esta amostra.")
        return
    ms = data.get("MS")
    names = {"Umidade": "Umidade", "MS": "Matéria seca", "MM": "Cinzas (MM)", "PB": "Proteína bruta (PB)",
             "EE": "Extrato etéreo (EE)", "FDA": "FDA", "Acidez": "Acidez"}
    rows = []
    for k, label in names.items():
        if k in data:
            dm = "—" if ms is None or k in ("Umidade", "MS", "Acidez") else f(br.to_dry_basis(data[k], ms), "%", 2)
            rows.append((label, f(data[k], "%", 2), dm))
    show_table(rows, ("Análise", "Matéria natural", "Matéria seca"))
    if ms is None:
        st.info("Calcule a umidade desta amostra para expressar os resultados e o CNF em base seca.")
        return

    st.markdown("**Carboidratos não fibrosos (CNF)** — tudo em %MS")
    ndf = num("FDN ou FDNcp (% MS) — informe o valor (o app não faz a análise de FDN)", None, "brom_fdn")
    missing = [k for k in ("PB", "EE", "MM") if k not in data]
    rows_out = list(rows)
    if missing:
        st.info(f"Para o CNF faltam nesta ficha: {', '.join(missing)}.")
    else:
        dm = {k: br.to_dry_basis(data[k], ms) for k in ("PB", "EE", "MM")}
        try:
            mo = 100 - dm["MM"]
            st.metric("Matéria orgânica (MS)", f(mo, "%", 2))
            if ndf is not None:
                r = br.non_fiber_carbohydrates(dm["PB"], dm["EE"], dm["MM"], ndf)
                c1, c2 = st.columns(2)
                c1.metric("CNF (MS)", f(r["nfc"], "%", 2))
                c2.metric("Carboidratos totais (MS)", f(r["total_carbohydrates"], "%", 2))
                st.caption("CNF = 100 − (PB + EE + MM + FDN) · CT = 100 − (PB + EE + MM)")
                rows_out += [("FDN (informado)", "—", f(ndf, "%", 2)), ("CNF", "—", f(r["nfc"], "%", 2)),
                             ("Carboidratos totais", "—", f(r["total_carbohydrates"], "%", 2))]
            rows_out.append(("Matéria orgânica", "—", f(mo, "%", 2)))
        except ValueError as e:
            show_error(e)
    export(f"Ficha bromatológica — {sid}", [("Amostra", sid)],
           [(a, f"MN {b} · MS {c}") for a, b, c in rows_out], [], "brom_ficha")
