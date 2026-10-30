"""Volumetria: titulação livre e padronização de soluções (RF-01, RF-02).

Volumes entram em mL e são convertidos para L dentro de cada fórmula.
"""
from modules.stats import describe
from modules.validation import clean_values, non_negative, positive

# Padrões primários usuais: massa molar em g/mol.
PRIMARY_STANDARDS = {
    "Biftalato de potássio (KHC₈H₄O₄)": 204.22,
    "Carbonato de sódio (Na₂CO₃)": 105.99,
    "Ácido oxálico di-hidratado (H₂C₂O₄·2H₂O)": 126.07,
}


def corrected_volume(volumes, blank=0.0, blank_mode="direct"):
    """Volume gasto corrigido pelo branco (mL).

    direct: V_corr = V̄_amostra − V_branco   (titulação comum)
    back:   V_corr = V_branco − V̄_amostra   (retrotitulação, ex.: DQO)
    """
    for v in clean_values(volumes, "volumes gastos"):
        positive("Volume gasto", v)
    blank = non_negative("Volume do branco", blank)
    st = describe(volumes)
    mean = st["mean"]

    if blank_mode == "direct":
        v_corr = mean - blank
        if v_corr <= 0:
            raise ValueError(f"O branco ({blank:g} mL) é maior ou igual ao volume médio gasto ({mean:g} mL).")
    elif blank_mode == "back":
        v_corr = blank - mean
        if v_corr <= 0:
            raise ValueError(f"Volume gasto na amostra ({mean:g} mL) é maior ou igual ao do branco "
                             f"({blank:g} mL): verifique o branco ou dilua a amostra.")
    else:
        raise ValueError(f"Modo de branco desconhecido: {blank_mode!r}.")
    return {"mean_volume": mean, "blank": blank, "v_corr": v_corr, "stats": st,
            "warnings": list(st["warnings"])}


def _analyte_mol(volumes, blank, c_titrant, factor, ratio):
    """n_analito = C_tit · f · V_corr[L] · r, com r = ν_analito / ν_titulante."""
    vol = corrected_volume(volumes, blank)
    c = positive("Concentração do titulante", c_titrant)
    f = positive("Fator de correção", factor)
    r = positive("Razão estequiométrica", ratio)
    n_titrant = c * f * vol["v_corr"] / 1000
    return vol, n_titrant, n_titrant * r


def analyte_concentration(volumes, blank, c_titrant, factor, v_aliquot, ratio=1.0):
    """Concentração do analito (mol/L): C = C_tit · f · V_corr · r / V_alíquota."""
    vol, n_titrant, n_analyte = _analyte_mol(volumes, blank, c_titrant, factor, ratio)
    v_al = positive("Volume da alíquota", v_aliquot)
    return {**vol, "n_titrant": n_titrant, "n_analyte": n_analyte,
            "concentration": n_analyte / (v_al / 1000), "unit": "mol/L"}


def mass_percent(volumes, blank, c_titrant, factor, m_sample, molar_mass, ratio=1.0):
    """Teor na amostra sólida (% m/m): (n_analito · M_analito) / m_amostra · 100."""
    vol, n_titrant, n_analyte = _analyte_mol(volumes, blank, c_titrant, factor, ratio)
    m = positive("Massa da amostra", m_sample)
    mm = positive("Massa molar do analito", molar_mass)
    m_analyte = n_analyte * mm
    pct = m_analyte / m * 100
    if pct > 100:
        vol["warnings"].append("Teor acima de 100 %: confira massa, volumes e estequiometria.")
    return {**vol, "n_titrant": n_titrant, "n_analyte": n_analyte, "m_analyte": m_analyte,
            "percent": pct, "unit": "% m/m"}


def normality(concentration, equivalents):
    """N = C · k, k = nº de H⁺ ou e⁻ trocados por mol (informado, nunca deduzido).

    A IUPAC desaconselha a unidade; mantida por compatibilidade com métodos antigos.
    """
    return positive("Concentração", concentration) * positive("Número de equivalentes", equivalents)


def standardize(m_standard, molar_mass_standard, volumes, c_nominal, ratio=1.0, blank=0.0):
    """Padronização com padrão primário.

    C_real = (m_padrão / M_padrão) · r / V_corr[L], com r = mol de titulante por mol de padrão
    (KHP + NaOH: r = 1; Na₂CO₃ + 2 HCl: r = 2).
    f = C_real / C_nominal
    """
    vol = corrected_volume(volumes, blank)
    m = positive("Massa do padrão", m_standard)
    mm = positive("Massa molar do padrão", molar_mass_standard)
    c_nom = positive("Concentração nominal", c_nominal)
    r = positive("Razão estequiométrica", ratio)
    n_standard = m / mm
    c_real = n_standard * r / (vol["v_corr"] / 1000)
    f = c_real / c_nom
    if not 0.90 <= f <= 1.10:
        vol["warnings"].append("Fator fora da faixa usual (0,90–1,10): verifique a solução.")
    return {**vol, "n_standard": n_standard, "c_real": c_real, "factor": f}
