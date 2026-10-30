"""Soluções: preparo, diluição, mistura e conversão de unidades (RF-05, RF-08).

Unidades fixas de bancada: massa em g, volume em mL, massa molar em g/mol.
"""
import math

from modules.validation import non_negative, positive


def _solve(left, right, labels, k=1.0):
    """Resolve a única variável em branco (None) em  k · Π(left) = Π(right).

    Todas as fórmulas de preparo de solução têm essa forma (ex.: C·M·V/1000 = m).
    left/right: {nome: valor ou None}; labels: {nome: rótulo para mensagens de erro}.
    """
    given = {**left, **right}
    missing = [n for n, v in given.items() if v is None]
    if len(missing) != 1:
        raise ValueError(f"Deixe exatamente um dos {len(given)} campos em branco.")
    vals = {n: positive(labels[n], v) for n, v in given.items() if v is not None}
    solved = missing[0]

    def prod(names):
        return math.prod(vals[n] for n in names if n != solved)

    if solved in left:
        vals[solved] = prod(right) / (k * prod(left))
    else:
        vals[solved] = k * prod(left) / prod(right)
    return {**vals, "solved": solved, "value": vals[solved], "warnings": []}


def c1v1(c1=None, v1=None, c2=None, v2=None):
    """C₁·V₁ = C₂·V₂ — resolve a única variável deixada em branco (None).

    Unidades livres, desde que C₁/C₂ e V₁/V₂ estejam na mesma unidade entre si.
    """
    r = _solve({"c1": c1, "v1": v1}, {"c2": c2, "v2": v2}, {"c1": "C₁", "v1": "V₁", "c2": "C₂", "v2": "V₂"})
    if r["c2"] > r["c1"]:
        r["warnings"].append("C₂ maior que C₁: isso não é uma diluição.")
    return r


def common_concentration(c=None, m=None, v=None):
    """Concentração comum: C [g/L] = m [g] / V [L]  →  C · V[mL] / 1000 = m."""
    return _solve({"c": c, "v": v}, {"m": m},
                  {"c": "Concentração", "v": "Volume", "m": "Massa"}, k=1 / 1000)


def molar_concentration(c=None, m=None, mm=None, v=None):
    """Concentração molar: C [mol/L] = m / (M · V[L])  →  C · M · V[mL] / 1000 = m.

    Com m em branco responde "quanto pesar". Sal hidratado: use a massa molar do hidrato.
    """
    return _solve({"c": c, "mm": mm, "v": v}, {"m": m},
                  {"c": "Concentração", "mm": "Massa molar", "v": "Volume", "m": "Massa"}, k=1 / 1000)


def molality(b=None, m_solute=None, mm=None, m_solvent=None):
    """Molalidade: b [mol/kg] = m_soluto / (M · m_solvente[kg])  →  b · M · m_solvente[g] / 1000 = m_soluto."""
    return _solve({"b": b, "mm": mm, "m_solvent": m_solvent}, {"m_solute": m_solute},
                  {"b": "Molalidade", "mm": "Massa molar", "m_solvent": "Massa do solvente",
                   "m_solute": "Massa do soluto"}, k=1 / 1000)


PERCENT_KINDS = ["m/m", "m/v", "v/v"]


def percent(kind, p=None, solute=None, solution=None):
    """Porcentagem: p = soluto / solução · 100  →  p · solução / 100 = soluto.

    m/m: g/g · m/v: g por mL de solução · v/v: mL/mL.
    """
    if kind not in PERCENT_KINDS:
        raise ValueError(f"Tipo de porcentagem inválido. Use: {', '.join(PERCENT_KINDS)}.")
    r = _solve({"p": p, "solution": solution}, {"solute": solute},
               {"p": "Porcentagem", "solution": "Solução", "solute": "Soluto"}, k=1 / 100)
    if kind != "m/v" and r["solute"] > r["solution"]:
        raise ValueError(f"Em % {kind} o soluto não pode ser maior que a solução.")
    return r


def density(d=None, m=None, v=None):
    """Densidade: d [g/mL] = m [g] / V [mL]  →  d · V = m."""
    return _solve({"d": d, "v": v}, {"m": m}, {"d": "Densidade", "v": "Volume", "m": "Massa"})


# Reagentes concentrados usuais: (título % m/m, densidade g/mL, massa molar g/mol). Valores típicos de rótulo.
COMMERCIAL_REAGENTS = {
    "Ácido clorídrico (HCl) 37 %": (37, 1.19, 36.46),
    "Ácido sulfúrico (H₂SO₄) 98 %": (98, 1.84, 98.08),
    "Ácido nítrico (HNO₃) 65 %": (65, 1.39, 63.01),
    "Ácido fosfórico (H₃PO₄) 85 %": (85, 1.69, 98.00),
    "Ácido acético glacial 99,7 %": (99.7, 1.05, 60.05),
    "Hidróxido de amônio (NH₃) 28 %": (28, 0.90, 17.03),
}


def commercial_reagent(density_g_ml, purity, molar_mass, c_final=None, v_final=None):
    """Reagente concentrado comercial (ex.: HCl 37 %, d 1,19).

    C [mol/L] = d [g/mL] · 1000 · (título % / 100) / M
    Volume a pipetar para preparar V_final de C_final: V = C_final · V_final / C
    """
    d = positive("Densidade", density_g_ml)
    t = positive("Título (% m/m)", purity)
    if t > 100:
        raise ValueError("O título não pode passar de 100 %.")
    mm = positive("Massa molar", molar_mass)
    c = d * 1000 * t / 100 / mm
    result = {"c": c, "c_g_l": c * mm, "volume": None, "warnings": []}
    if c_final is not None or v_final is not None:
        cf = positive("Concentração desejada", c_final)
        vf = positive("Volume final desejado", v_final)
        if cf > c:
            raise ValueError("A concentração desejada é maior que a do reagente concentrado.")
        result["volume"] = cf * vf / c
    return result


def mix(concentrations, volumes):
    """Mistura de soluções do mesmo soluto: C_final = Σ(Cᵢ · Vᵢ) / ΣVᵢ."""
    if len(concentrations) != len(volumes):
        raise ValueError("Cada solução precisa de concentração e volume.")
    if not concentrations:
        raise ValueError("Nenhum valor informado em soluções da mistura.")
    cs = [non_negative("Concentração", c) for c in concentrations]
    vs = [positive("Volume", v) for v in volumes]
    v_total = sum(vs)
    return {"c": sum(c * v for c, v in zip(cs, vs)) / v_total, "v_total": v_total, "warnings": []}


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


# Fração adimensional de cada unidade: 1 % = 10⁻², 1 ‰ = 10⁻³, 1 ppm = 10⁻⁶, 1 ppb = 10⁻⁹.
FRACTIONS = {"%": 1e-2, "‰": 1e-3, "ppm": 1e-6, "ppb": 1e-9}


def convert_fraction(value, from_unit, to_unit):
    """% ↔ ‰ ↔ ppm ↔ ppb (mesma base: m/m, v/v ou m/v aquosa)."""
    if from_unit not in FRACTIONS or to_unit not in FRACTIONS:
        raise ValueError(f"Unidade não suportada. Use: {', '.join(FRACTIONS)}.")
    return non_negative("Valor", value) * FRACTIONS[from_unit] / FRACTIONS[to_unit]


# Grandeza → {unidade: fator para a unidade base}. Base: g, mL, kPa.
SI_UNITS = {
    "Massa": {"kg": 1000.0, "g": 1.0, "mg": 1e-3, "µg": 1e-6},
    "Volume": {"L": 1000.0, "mL": 1.0, "µL": 1e-3},
    "Pressão": {"atm": 101.325, "kPa": 1.0, "bar": 100.0, "mmHg": 101.325 / 760},
}
TEMPERATURE_UNITS = ["°C", "K", "°F"]


def convert_unit(value, quantity, from_unit, to_unit):
    """Conversão por fator: valor · fator(de) / fator(para). Temperatura tem escala com deslocamento."""
    if quantity == "Temperatura":
        return convert_temperature(value, from_unit, to_unit)
    units = SI_UNITS.get(quantity)
    if units is None or from_unit not in units or to_unit not in units:
        raise ValueError("Unidade não suportada.")
    v = non_negative("Valor", value)
    return v * units[from_unit] / units[to_unit]


def convert_temperature(value, from_unit, to_unit):
    """°C ↔ K ↔ °F: K = °C + 273,15 ; °F = °C × 9/5 + 32. Abaixo de 0 K → erro."""
    if from_unit not in TEMPERATURE_UNITS or to_unit not in TEMPERATURE_UNITS:
        raise ValueError("Unidade de temperatura não suportada.")
    if value is None:
        raise ValueError("Informe Valor.")
    v = float(value)
    kelvin = {"°C": v + 273.15, "K": v, "°F": (v - 32) * 5 / 9 + 273.15}[from_unit]
    if kelvin < 0:
        raise ValueError("Temperatura abaixo do zero absoluto (0 K).")
    return {"°C": kelvin - 273.15, "K": kelvin, "°F": (kelvin - 273.15) * 9 / 5 + 32}[to_unit]


def rule_of_three(a=None, b=None, c=None, x=None, inverse=False):
    """Regra de três: a está para b assim como c está para x.

    Direta: a/b = c/x  →  a·x = b·c ;  Inversa: a·b = c·x.
    """
    labels = {"a": "A", "b": "B", "c": "C", "x": "X"}
    if inverse:
        return _solve({"a": a, "b": b}, {"c": c, "x": x}, labels)
    return _solve({"a": a, "x": x}, {"b": b, "c": c}, labels)
