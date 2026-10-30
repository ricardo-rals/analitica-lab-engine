"""Catálogo de análises pré-cadastradas (RF-07).

Cada análise é DADO: incluir uma nova é acrescentar uma entrada em METHODS.
Referências: Standard Methods for the Examination of Water and Wastewater (SM).

Titulométricas — fórmula única:
    resultado [mg/L] = V_corr[mL] · C_tit[mol/L] · f · r · M[g/mol] · 1000 / V_amostra[mL] · FD
    r = mol da espécie de expressão (CaCO₃, Cl⁻, O₂) por mol de titulante.
Espectrofotométricas — curva de calibração:
    resultado = (Ā − b) / a · FD
"""
from modules.spectro import calibrate, predict
from modules.titration import corrected_volume
from modules.validation import non_negative, positive


def _titration(name, reference, titrant, indicator, ratio, molar_mass, unit, c_default, v_default,
               blank_mode="direct", notes=""):
    # c_default (mol/L) e v_default (mL): valores usuais do método, só para pré-preencher a UI.
    return {"kind": "titration", "name": name, "reference": reference, "titrant": titrant,
            "indicator": indicator, "ratio": ratio, "molar_mass": molar_mass, "unit": unit,
            "c_default": c_default, "v_default": v_default, "blank_mode": blank_mode, "notes": notes}


def _spectro(name, reference, reagent, wavelength_nm, unit, notes=""):
    return {"kind": "spectro", "name": name, "reference": reference, "reagent": reagent,
            "wavelength_nm": wavelength_nm, "unit": unit, "notes": notes}


METHODS = {
    # Ca²⁺ + Mg²⁺ complexados 1:1 pelo EDTA; expresso como CaCO₃.
    "dureza_total": _titration("Dureza total", "SM 2340 C", "EDTA", "Negro de eriocromo T (tampão pH 10)",
                               1, 100.09, "mg CaCO₃/L", 0.01, 50),
    # pH 12–13 precipita Mg(OH)₂: o EDTA titula só o Ca²⁺.
    "dureza_calcica": _titration("Dureza cálcica", "SM 3500-Ca B", "EDTA", "Murexida (NaOH, pH 12–13)",
                                 1, 100.09, "mg CaCO₃/L", 0.01, 50),
    # Alcalinidade com H₂SO₄: 1 mol H₂SO₄ neutraliza o equivalente a 1 mol CaCO₃.
    "alcalinidade_p": _titration("Alcalinidade parcial (P)", "SM 2320 B", "H₂SO₄",
                                 "Fenolftaleína (até pH 8,3)", 1, 100.09, "mg CaCO₃/L", 0.01, 100),
    "alcalinidade_t": _titration("Alcalinidade total (T)", "SM 2320 B", "H₂SO₄",
                                 "Verde de bromocresol / pH 4,5", 1, 100.09, "mg CaCO₃/L", 0.01, 100,
                                 notes="Use o volume total desde o início da titulação (inclui o da etapa P)."),
    # Mohr: Ag⁺ + Cl⁻ → AgCl; fim com Ag₂CrO₄ vermelho-tijolo.
    "cloretos": _titration("Cloretos (Mohr)", "SM 4500-Cl⁻ B", "AgNO₃", "K₂CrO₄", 1, 35.45, "mg Cl⁻/L",
                           0.0141, 100),
    # 2 NaOH neutralizam o equivalente a 1 CaCO₃ → r = ½.
    "acidez": _titration("Acidez", "SM 2310 B", "NaOH", "Fenolftaleína (até pH 8,3)", 0.5, 100.09,
                         "mg CaCO₃/L", 0.02, 100),
    # Winkler: O₂ → 2 I₂ → 4 S₂O₃²⁻ → r = ¼.
    "oxigenio_dissolvido": _titration("Oxigênio dissolvido (Winkler)", "SM 4500-O C", "Na₂S₂O₃", "Amido",
                                      0.25, 32.00, "mg O₂/L", 0.025, 200,
                                      notes="V_amostra = volume titulado já descontado o deslocado pelos reagentes."),
    # Retrotitulação do Cr₂O₇²⁻ restante com Fe²⁺: 4 Fe²⁺ ≙ 1 O₂ → r = ¼; V_corr = V_branco − V_amostra.
    "dqo": _titration("DQO (refluxo, titulométrico)", "SM 5220 C", "Sulfato ferroso amoniacal (FAS)",
                      "Ferroína", 0.25, 32.00, "mg O₂/L", 0.25, 20, blank_mode="back",
                      notes="Branco = água destilada submetida ao mesmo refluxo."),
    "sulfato": _spectro("Sulfato", "SM 4500-SO₄²⁻ E", "BaCl₂ (turbidimétrico)", 420, "mg SO₄²⁻/L"),
    "ferro": _spectro("Ferro total", "SM 3500-Fe B", "1,10-fenantrolina", 510, "mg Fe/L"),
    "fosfato": _spectro("Fosfato", "SM 4500-P E", "Ácido ascórbico (azul de molibdênio)", 880, "mg P/L"),
    "nitrito": _spectro("Nitrito", "SM 4500-NO₂⁻ B", "Sulfanilamida + NED", 543, "mg N-NO₂⁻/L"),
}


def _get(key, kind):
    m = METHODS.get(key)
    if m is None or m["kind"] != kind:
        raise ValueError(f"Análise desconhecida: {key!r}.")
    return m


def run_titration(key, volumes, blank, c_titrant, factor, v_sample, dilution=1.0):
    """Aplica a fórmula titulométrica genérica à análise `key` do catálogo."""
    m = _get(key, "titration")
    vol = corrected_volume(volumes, blank, m["blank_mode"])
    c = positive("Concentração do titulante", c_titrant)
    f = positive("Fator de correção", factor)
    v_s = positive("Volume da amostra", v_sample)
    fd = positive("Fator de diluição", dilution)
    mmol = vol["v_corr"] * c * f * m["ratio"]       # mL · mol/L = mmol da espécie de expressão
    mg_l = mmol * m["molar_mass"] * 1000 / v_s     # mmol · g/mol = mg; ÷ mL · 1000 = mg/L
    return {**vol, "method": m, "mmol": mmol, "result_measured": mg_l, "dilution": fd,
            "result": mg_l * fd, "unit": m["unit"]}


def run_spectro(key, std_concentrations, std_absorbances, sample_absorbances, dilution=1.0):
    """Curva de calibração + concentração da amostra para a análise `key`."""
    m = _get(key, "spectro")
    curve = calibrate(std_concentrations, std_absorbances)
    pred = predict(curve, sample_absorbances, dilution)
    return {**pred, "curve": curve, "method": m, "result": pred["concentration"], "unit": m["unit"],
            "warnings": curve["warnings"] + pred["warnings"]}


def magnesium_hardness(total, calcium):
    """Dureza magnesiana = dureza total − dureza cálcica (ambas em mg CaCO₃/L)."""
    t = non_negative("Dureza total", total)
    ca = non_negative("Dureza cálcica", calcium)
    if ca > t:
        raise ValueError("A dureza cálcica não pode ser maior que a total.")
    return t - ca


def alkalinity_speciation(p, t):
    """Hidróxido, carbonato e bicarbonato a partir de P e T (SM 2320 B), em mg CaCO₃/L.

    P ≤ T/2: OH⁻ = 0,      CO₃²⁻ = 2P,       HCO₃⁻ = T − 2P
    P > T/2: OH⁻ = 2P − T, CO₃²⁻ = 2(T − P), HCO₃⁻ = 0
    (os casos P = 0, P = T/2 e P = T da tabela da norma caem nessas duas fórmulas)
    """
    p = non_negative("Alcalinidade P", p)
    t = non_negative("Alcalinidade T", t)
    if p > t:
        raise ValueError("A alcalinidade P não pode ser maior que a T.")
    if p <= t / 2:
        return {"hydroxide": 0.0, "carbonate": 2 * p, "bicarbonate": t - 2 * p}
    return {"hydroxide": 2 * p - t, "carbonate": 2 * (t - p), "bicarbonate": 0.0}
