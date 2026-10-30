"""Diluições e conversão de unidades de concentração (RF-05)."""
from modules.validation import non_negative, positive

_LABELS = {"c1": "C₁", "v1": "V₁", "c2": "C₂", "v2": "V₂"}


def c1v1(c1=None, v1=None, c2=None, v2=None):
    """C₁·V₁ = C₂·V₂ — resolve a única variável deixada em branco (None).

    Unidades livres, desde que C₁/C₂ e V₁/V₂ estejam na mesma unidade entre si.
    """
    given = {"c1": c1, "v1": v1, "c2": c2, "v2": v2}
    missing = [k for k, v in given.items() if v is None]
    if len(missing) != 1:
        raise ValueError("Deixe exatamente um dos quatro campos em branco.")
    k = {name: positive(_LABELS[name], v) for name, v in given.items() if v is not None}
    solved = missing[0]
    if solved == "c1":
        k["c1"] = k["c2"] * k["v2"] / k["v1"]
    elif solved == "v1":
        k["v1"] = k["c2"] * k["v2"] / k["c1"]
    elif solved == "c2":
        k["c2"] = k["c1"] * k["v1"] / k["v2"]
    else:
        k["v2"] = k["c1"] * k["v1"] / k["c2"]
    warnings = []
    if k["c2"] > k["c1"]:
        warnings.append("C₂ maior que C₁: isso não é uma diluição.")
    return {**k, "solved": solved, "value": k[solved], "warnings": warnings}


def dilution_factor(v_final, v_aliquot):
    """FD = V_final / V_alíquota; C_original = C_medida · FD."""
    vf = positive("Volume final", v_final)
    va = positive("Volume da alíquota", v_aliquot)
    if va > vf:
        raise ValueError("A alíquota não pode ser maior que o volume final.")
    return vf / va


UNITS = ["mol/L", "g/L", "mg/L"]


def convert_concentration(value, from_unit, to_unit, molar_mass):
    """mol/L ↔ g/L ↔ mg/L via massa molar M (g/mol): 1 mol/L = M g/L = 1000·M mg/L.

    mg/L ≈ ppm em solução aquosa diluída.
    """
    if from_unit not in UNITS or to_unit not in UNITS:
        raise ValueError(f"Unidade não suportada. Use: {', '.join(UNITS)}.")
    v = non_negative("Concentração", value)
    mm = positive("Massa molar", molar_mass)
    per_mol_l = {"mol/L": 1.0, "g/L": mm, "mg/L": 1000 * mm}
    return v / per_mol_l[from_unit] * per_mol_l[to_unit]
