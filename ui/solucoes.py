"""Seção Soluções e cálculos: preparo de soluções, estequiometria/pH, conversões e erros."""
import pandas as pd
import streamlit as st

from modules import conversions, stats
from modules import stoichiometry as sto
from ui.common import (didactic, editor, example_df, f, num, parse_number, radio, select, show_error, show_table,
                       show_warnings, text)
from utils.formatting import round_significant, significant_figures


# ---------------------------------------------------------------- soluções (RF-05, RF-08)
def solver_form(key, fn, fields, formula, **fixed):
    """Formulário "preencha todos menos um": fields = [(nome, rótulo, unidade)]; fn resolve o que faltar."""
    st.caption(f"`{formula}` — preencha todos os campos menos o que quer calcular.")
    vals = {}
    for col, (name, label, unit) in zip(st.columns(len(fields)), fields):
        with col:
            vals[name] = num(f"{label} ({unit})" if unit else label, None, f"{key}_{name}")
    if all(v is None for v in vals.values()):
        st.info("Preencha os valores conhecidos.")
        return
    try:
        r = fn(**fixed, **vals)
    except ValueError as e:
        show_error(e)
        return
    _, label, unit = next(fl for fl in fields if fl[0] == r["solved"])
    st.metric(f"{label} calculado", f(r["value"], unit))
    show_warnings(r["warnings"])


def percent_form():
    kind = radio("Tipo", conversions.PERCENT_KINDS, "pct_kind", horizontal=True, format_func=lambda k: f"% {k}")
    solute = ("Volume do soluto", "mL") if kind == "v/v" else ("Massa do soluto", "g")
    solution = ("Massa da solução", "g") if kind == "m/m" else ("Volume da solução", "mL")
    solver_form(f"pct_{kind.replace('/', '')}", conversions.percent,
                [("p", "Porcentagem", f"% {kind}"), ("solute", *solute), ("solution", *solution)],
                "% = soluto / solução × 100", kind=kind)


def reagent_form():
    st.caption("`C = d · 1000 · (título / 100) / M` — ácidos e bases concentrados comerciais. "
               "Valores típicos de rótulo: confira o frasco.")
    name = select("Reagente", list(conversions.COMMERCIAL_REAGENTS) + ["Outro"], "reag_name")
    t0, d0, mm0 = conversions.COMMERCIAL_REAGENTS.get(name, (None, None, None))
    cols = st.columns(3)
    with cols[0]:
        t = num("Título (% m/m)", t0, f"reag_t_{name}")
    with cols[1]:
        d = num("Densidade (g/mL)", d0, f"reag_d_{name}")
    with cols[2]:
        mm = num("Massa molar (g/mol)", mm0, f"reag_mm_{name}")
    st.markdown("**Preparar uma solução diluída** (opcional)")
    cols = st.columns(2)
    with cols[0]:
        cf = num("Concentração desejada (mol/L)", None, "reag_cf")
    with cols[1]:
        vf = num("Volume final (mL)", None, "reag_vf")
    try:
        r = conversions.commercial_reagent(d, t, mm, cf, vf)
    except ValueError as e:
        show_error(e)
        return
    c1, c2 = st.columns(2)
    c1.metric("Concentração do reagente", f(r["c"], "mol/L"))
    c2.metric("Concentração comum", f(r["c_g_l"], "g/L"))
    if r["volume"] is not None:
        st.metric("Volume do reagente a pipetar", f(r["volume"], "mL"))
        st.caption(f"Pipete o reagente sobre parte da água e complete até {f(vf, 'mL', 1)}. "
                   "Sempre o ácido sobre a água, nunca o contrário.")


def mix_form():
    st.caption("`C final = Σ(Cᵢ · Vᵢ) / ΣVᵢ` — soluções do mesmo soluto, na mesma unidade de concentração.")
    df = editor(pd.DataFrame({"Concentração": [""] * 3, "Volume (mL)": [""] * 3}), "mix")
    try:
        pairs = [(parse_number(c), parse_number(v)) for c, v in zip(df.iloc[:, 0], df.iloc[:, 1])]
        pairs = [p for p in pairs if p != (None, None)]
        if any(None in p for p in pairs):
            raise ValueError("Há solução com concentração ou volume em branco.")
        r = conversions.mix([c for c, _ in pairs], [v for _, v in pairs])
    except ValueError as e:
        show_error(e)
        return
    c1, c2 = st.columns(2)
    c1.metric("Concentração final", f(r["c"]))
    c2.metric("Volume total", f(r["v_total"], "mL"))


def dilution_factor_form():
    st.caption("`FD = V final / V alíquota` — multiplique o resultado medido pelo FD.")
    cols = st.columns(2)
    with cols[0]:
        vf = num("Volume final (mL)", 100, "fd_vf")
    with cols[1]:
        va = num("Volume da alíquota (mL)", 10, "fd_va")
    try:
        st.metric("Fator de diluição", f(conversions.dilution_factor(vf, va)))
    except ValueError as e:
        show_error(e)


def unit_form(key, units, convert, default_to, caption, with_mm=False):
    cols = st.columns(4 if with_mm else 3)
    with cols[0]:
        val = num("Valor", None, f"{key}_val")
    with cols[1]:
        u_from = select("De", units, f"{key}_from")
    with cols[2]:
        u_to = select("Para", units, f"{key}_to", index=default_to)
    extra = []
    if with_mm:
        with cols[3]:
            extra = [num("Massa molar (g/mol)", None, f"{key}_mm")]
    try:
        st.metric("Resultado", f(convert(val, u_from, u_to, *extra), u_to))
    except ValueError as e:
        show_error(e)
    st.caption(caption)


SOLUTION_CALCS = {
    "Concentração molar / quanto pesar (mol/L)": lambda: solver_form(
        "mol", conversions.molar_concentration,
        [("c", "Concentração", "mol/L"), ("mm", "Massa molar", "g/mol"), ("v", "Volume", "mL"), ("m", "Massa", "g")],
        "C = m / (M · V)"),
    "Concentração comum (g/L)": lambda: solver_form(
        "cc", conversions.common_concentration,
        [("c", "Concentração", "g/L"), ("v", "Volume", "mL"), ("m", "Massa", "g")], "C = m / V"),
    "Diluição (C₁·V₁ = C₂·V₂)": lambda: solver_form(
        "dil", conversions.c1v1,
        [("c1", "C₁ (estoque)", ""), ("v1", "V₁ (alíquota)", ""), ("c2", "C₂ (final)", ""), ("v2", "V₂ (final)", "")],
        "C₁·V₁ = C₂·V₂ (mesma unidade dos dois lados)"),
    "Reagente comercial concentrado (ácidos e bases)": reagent_form,
    "Porcentagem (% m/m, % m/v, % v/v)": percent_form,
    "Molalidade (mol/kg)": lambda: solver_form(
        "molal", conversions.molality,
        [("b", "Molalidade", "mol/kg"), ("mm", "Massa molar", "g/mol"), ("m_solvent", "Massa do solvente", "g"),
         ("m_solute", "Massa do soluto", "g")], "b = m soluto / (M · m solvente)"),
    "Densidade": lambda: solver_form(
        "dens", conversions.density, [("d", "Densidade", "g/mL"), ("v", "Volume", "mL"), ("m", "Massa", "g")],
        "d = m / V"),
    "Mistura de soluções": mix_form,
    "Fator de diluição": dilution_factor_form,
    "Conversão mol/L ↔ g/L ↔ mg/L": lambda: unit_form(
        "conv", conversions.UNITS, conversions.convert_concentration, 2,
        "1 mol/L = M g/L. mg/L ≈ ppm em solução aquosa diluída.", with_mm=True),
    "Conversão % ↔ ‰ ↔ ppm ↔ ppb": lambda: unit_form(
        "frac", list(conversions.FRACTIONS), conversions.convert_fraction, 2, "1 % = 10 ‰ = 10⁴ ppm = 10⁷ ppb."),
}


def page_solutions():
    didactic("**Preencha tudo menos o que quer descobrir.** Todas essas fórmulas são do tipo "
             "`produto de um lado = produto do outro` (ex.: `C · M · V = m`), então qualquer variável pode ser a "
             "incógnita. Unidades fixas: massa em g, volume em mL, massa molar em g/mol.",
             {"sol_calc": "Concentração molar / quanto pesar (mol/L)", "mol_c": "0,1", "mol_mm": "58,44",
              "mol_v": "500"}, "sol")
    calc = select("Cálculo", list(SOLUTION_CALCS), "sol_calc")
    SOLUTION_CALCS[calc]()


# ---------------------------------------------------------------- estequiometria e pH (RF-11)
def stoich_form():
    st.caption("Uma linha por espécie. Reagente sem massa = em excesso. O avanço da reação é limitado pelo "
               "reagente com menor `n / coeficiente`.")
    df = editor(pd.DataFrame({"Espécie": ["Na₂SO₄", "BaCl₂", "BaSO₄", "NaCl"],
                              "Papel": ["reagente", "reagente", "produto", "produto"],
                              "Coeficiente": ["1", "1", "1", "2"],
                              "Massa molar (g/mol)": ["142,04", "208,23", "233,39", "58,44"],
                              "Massa (g)": ["1", "", "", ""]}), "sto_species",
                column_config={"Papel": st.column_config.SelectboxColumn(options=["reagente", "produto"])})
    try:
        species = []
        for i, row in enumerate(df.itertuples(index=False), 1):
            name, role, coef, mm, mass = row
            name = name.strip() if isinstance(name, str) else ""
            if not name:
                continue
            if role not in ("reagente", "produto"):
                raise ValueError(f"Linha {i}: escolha o papel (reagente ou produto).")
            species.append({"name": name, "role": role, "coef": parse_number(coef),
                            "molar_mass": parse_number(mm), "mass": parse_number(mass) if role == "reagente" else None})
        r = sto.stoichiometry(species)
    except (ValueError, TypeError) as e:
        show_error(e)
        return
    st.metric("Reagente limitante", r["limiting"])
    show_table([(p["name"], f(p["mol"], "mol"), f(p["theoretical_mass"], "g")) for p in r["products"]],
               ("Produto", "Quantidade teórica", "Massa teórica"))
    show_table([(g["name"], f(g["consumed_mass"], "g"), "em excesso (sem massa)" if g["excess_mass"] is None
                 else f(g["excess_mass"], "g")) for g in r["reagents"]], ("Reagente", "Consumido", "Sobra"))

    st.markdown("**Rendimento**")
    names = [p["name"] for p in r["products"]]
    prod = select("Produto obtido", names, "sto_yield_prod")
    actual = num("Massa obtida (g)", None, "sto_yield_m")
    if actual is not None:
        theo = next(p["theoretical_mass"] for p in r["products"] if p["name"] == prod)
        try:
            y = sto.yield_percent(actual, theo)
            st.metric("Rendimento", f(y["yield"], "%", 2))
            show_warnings(y["warnings"])
        except ValueError as e:
            show_error(e)


def buffer_form():
    name = select("Par ácido/base", list(sto.BUFFERS) + ["Outro"], "buf_pair")
    pka0, (acid_name, mm_a0), (base_name, mm_b0) = sto.BUFFERS.get(name, (None, ("Forma ácida", None),
                                                                           ("Forma básica", None)))
    cols = st.columns(4)
    with cols[0]:
        ph = num("pH desejado", None, "buf_ph")
    with cols[1]:
        pka = num("pKa", pka0, f"buf_pka_{name}")
    with cols[2]:
        c = num("Concentração total (mol/L)", 0.1, "buf_c")
    with cols[3]:
        v = num("Volume (mL)", 1000, "buf_v")
    cols = st.columns(2)
    with cols[0]:
        mm_a = num(f"M {acid_name} (g/mol)", mm_a0, f"buf_mma_{name}")
    with cols[1]:
        mm_b = num(f"M {base_name} (g/mol)", mm_b0, f"buf_mmb_{name}")
    try:
        r = sto.buffer(ph, pka, c, v, mm_a, mm_b)
    except ValueError as e:
        show_error(e)
        return
    c1, c2 = st.columns(2)
    c1.metric(f"{acid_name}", f(r["acid_mass"], "g") if r["acid_mass"] is not None else f(r["acid_conc"], "mol/L"))
    c2.metric(f"{base_name}", f(r["base_mass"], "g") if r["base_mass"] is not None else f(r["base_conc"], "mol/L"))
    show_table([("[HA] forma ácida", f(r["acid_conc"], "mol/L")), ("[A⁻] forma básica", f(r["base_conc"], "mol/L")),
                ("Razão [A⁻]/[HA]", f(r["ratio"]))])
    if acid_name == "Ácido acético" and r["acid_mass"] is not None:
        st.caption(f"Ácido acético glacial (d ≈ 1,049 g/mL): {f(r['acid_mass'] / 1.049, 'mL')}.")
    show_warnings(r["warnings"])


def ph_adjust_form():
    mode = radio("Solução", ["Tamponada (par ácido/base)", "Sem tampão (ácido/base forte, água)"], "phadj_mode",
                 horizontal=True)
    cols = st.columns(4)
    with cols[0]:
        pa = num("pH atual", None, "phadj_a")
    with cols[1]:
        pb = num("pH desejado", None, "phadj_b")
    with cols[2]:
        v = num("Volume da solução (mL)", None, "phadj_v")
    with cols[3]:
        ct = num("Concentração do ácido/base forte (mol/L)", 1, "phadj_ct")
    try:
        if mode.startswith("Tamponada"):
            cols = st.columns(2)
            with cols[0]:
                pka = num("pKa do tampão", None, "phadj_pka")
            with cols[1]:
                c = num("Concentração total do tampão (mol/L)", None, "phadj_c")
            r = sto.ph_adjust_buffer(pa, pb, pka, c, v, ct)
            st.caption("`n = C_T · V · (α(pH desejado) − α(pH atual))`, com `α = 1 / (1 + 10^(pKa − pH))`.")
        else:
            r = sto.ph_adjust_strong(pa, pb, v, ct)
            st.caption("Balanço de `[H⁺] − [OH⁻]` com a diluição causada pelo titulante.")
    except ValueError as e:
        show_error(e)
        return
    titrant = {"base": "base forte (ex.: NaOH)", "ácido": "ácido forte (ex.: HCl)"}.get(r["titrant"], "nada")
    st.metric(f"Adicionar {titrant}", f(r["volume_ml"], "mL"))
    show_warnings(r["warnings"])


STOICH_CALCS = {"Estequiometria e rendimento": stoich_form, "Solução tampão": buffer_form,
                "Ajuste de pH": ph_adjust_form}


def page_stoichiometry():
    didactic("**Estequiometria:** mols = massa / massa molar. Cada reagente permite um avanço `n / coeficiente`; "
             "o menor é o do **reagente limitante**, que define quanto produto se forma. "
             "**Rendimento** = obtido / teórico × 100. **Tampão:** Henderson–Hasselbalch "
             "`pH = pKa + log([A⁻]/[HA])` dá a razão entre as formas básica e ácida.", key="sto")
    calc = select("Cálculo", list(STOICH_CALCS), "sto_calc")
    STOICH_CALCS[calc]()


# ---------------------------------------------------------------- conversões e erros (RF-10, RF-11.5)
def si_form():
    quantity = select("Grandeza", list(conversions.SI_UNITS) + ["Temperatura"], "si_q")
    units = conversions.TEMPERATURE_UNITS if quantity == "Temperatura" else list(conversions.SI_UNITS[quantity])
    cols = st.columns(3)
    with cols[0]:
        val = num("Valor", None, f"si_val_{quantity}")
    with cols[1]:
        u_from = select("De", units, f"si_from_{quantity}")
    with cols[2]:
        u_to = select("Para", units, f"si_to_{quantity}", index=1)
    try:
        st.metric("Resultado", f(conversions.convert_unit(val, quantity, u_from, u_to), u_to))
    except ValueError as e:
        show_error(e)


def rule_of_three_form():
    inverse = radio("Proporção", ["Direta", "Inversa"], "r3_kind", horizontal=True) == "Inversa"
    st.caption("Inversa: quando uma grandeza aumenta, a outra diminui (ex.: nº de pessoas × tempo)."
               if inverse else "Direta: A está para B assim como C está para X.")
    key = "r3i" if inverse else "r3d"
    solver_form(key, conversions.rule_of_three, [("a", "A", ""), ("b", "B", ""), ("c", "C", ""), ("x", "X", "")],
                "A · B = C · X" if inverse else "A / B = C / X", inverse=inverse)


def sig_figs_form():
    st.caption("Arredondamento pela **ABNT NBR 5891**: se o algarismo descartado é 5 seguido só de zeros, "
               "arredonda-se para o par (2,65 → 2,6; 2,75 → 2,8).")
    cols = st.columns(2)
    with cols[0]:
        raw = text("Número", "sf_num")
    with cols[1]:
        n = num("Arredondar para quantos algarismos significativos?", None, "sf_n")
    if not raw:
        st.info("Digite um número.")
        return
    try:
        st.metric("Algarismos significativos", significant_figures(raw))
        if n is not None:
            rounded = repr(round_significant(parse_number(raw), int(n)))
            st.metric(f"Com {int(n)} significativos", rounded.removesuffix(".0").replace(".", ","))
    except ValueError as e:
        show_error(e)


def errors_form():
    st.markdown("**Erro absoluto e relativo**")
    cols = st.columns(2)
    with cols[0]:
        x = num("Valor obtido", None, "err_x")
    with cols[1]:
        ref = num("Valor de referência (verdadeiro/certificado)", None, "err_ref")
    if x is not None and ref is not None:
        try:
            e = stats.errors(x, ref)
            c1, c2 = st.columns(2)
            c1.metric("Erro absoluto (x − ref)", f(e["absolute"]))
            c2.metric("Erro relativo", f(e["relative"], "%", 2))
        except ValueError as err:
            show_error(err)
    st.divider()
    st.markdown("**Recuperação (ensaio de fortificação)**")
    cols = st.columns(3)
    with cols[0]:
        cu = num("Amostra sem fortificação", None, "rec_cu")
    with cols[1]:
        cs = num("Amostra fortificada", None, "rec_cs")
    with cols[2]:
        ca = num("Quantidade adicionada", None, "rec_ca")
    if None not in (cu, cs, ca):
        try:
            r = stats.recovery(cs, cu, ca)
            st.metric("Recuperação", f(r["recovery"], "%", 1))
            show_warnings(r["warnings"])
        except ValueError as err:
            show_error(err)
    st.caption("Recuperação = (fortificada − sem fortificação) / adicionada × 100. Mede a exatidão (erro "
               "sistemático); a precisão (erro aleatório) é medida pelo desvio padrão e pelo CV das réplicas.")


CONVERSION_CALCS = {"Unidades SI": si_form, "Regra de três": rule_of_three_form,
                    "Algarismos significativos (NBR 5891)": sig_figs_form, "Erros e recuperação": errors_form}


def page_conversions():
    didactic("**Regra de três direta:** `A/B = C/X` → `X = B·C/A`. **Inversa:** `A·B = C·X`. "
             "**Erro relativo** expressa o erro como % do valor verdadeiro, o que permite comparar medidas de "
             "grandezas diferentes.", key="conv")
    calc = select("Cálculo", list(CONVERSION_CALCS), "conv_calc")
    CONVERSION_CALCS[calc]()
