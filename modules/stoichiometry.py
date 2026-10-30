"""Estequiometria, rendimento, soluções-tampão e ajuste de pH (RF-11).

Massas em g, volumes em mL, concentrações em mol/L, massas molares em g/mol.
"""
from modules.validation import positive

KW = 1e-14  # produto iônico da água a 25 °C


def stoichiometry(species):
    """Reagente limitante e massas teóricas.

    species: [{"name", "role": "reagente"|"produto", "coef", "molar_mass", "mass" (reagente, opcional)}].
    Avanço ξ = min(nᵢ / νᵢ) entre reagentes com massa; reagente sem massa = em excesso.
    Produto: m = ξ · ν · M ; sobra do reagente: m − ξ · ν · M.
    """
    reagents = [s for s in species if s["role"] == "reagente"]
    products = [s for s in species if s["role"] == "produto"]
    if not reagents or not products:
        raise ValueError("Informe ao menos um reagente e um produto.")
    for s in species:
        positive(f"Coeficiente de {s['name']}", s["coef"])
        positive(f"Massa molar de {s['name']}", s["molar_mass"])
    weighed = [s for s in reagents if s.get("mass") is not None]
    if not weighed:
        raise ValueError("Informe a massa de ao menos um reagente.")
    extents = {s["name"]: positive(f"Massa de {s['name']}", s["mass"]) / s["molar_mass"] / s["coef"] for s in weighed}
    limiting = min(extents, key=extents.get)
    xi = extents[limiting]
    out_reagents = [{"name": s["name"], "mol": None if s.get("mass") is None else s["mass"] / s["molar_mass"],
                     "consumed_mass": xi * s["coef"] * s["molar_mass"],
                     "excess_mass": None if s.get("mass") is None else s["mass"] - xi * s["coef"] * s["molar_mass"]}
                    for s in reagents]
    out_products = [{"name": s["name"], "mol": xi * s["coef"], "theoretical_mass": xi * s["coef"] * s["molar_mass"]}
                    for s in products]
    return {"limiting": limiting, "extent": xi, "reagents": out_reagents, "products": out_products, "warnings": []}


def yield_percent(actual, theoretical):
    """Rendimento (%) = massa real / massa teórica × 100."""
    y = positive("Massa obtida", actual) / positive("Massa teórica", theoretical) * 100
    warnings = [] if y <= 100 else ["Rendimento acima de 100 %: produto úmido ou impuro, ou erro de pesagem."]
    return {"yield": y, "warnings": warnings}


# Pares ácido/base: pKa (25 °C), (forma ácida, M), (forma básica, M).
BUFFERS = {
    "Acetato (CH₃COOH / CH₃COONa·3H₂O)": (4.76, ("Ácido acético", 60.05), ("Acetato de sódio tri-hidratado", 136.08)),
    "Fosfato (NaH₂PO₄·H₂O / Na₂HPO₄)": (7.21, ("Fosfato monossódico mono-hidratado", 137.99),
                                         ("Fosfato dissódico anidro", 141.96)),
    "TRIS (TRIS·HCl / TRIS base)": (8.07, ("TRIS·HCl", 157.60), ("TRIS base", 121.14)),
    "Amônio (NH₄Cl / NH₃)": (9.25, ("Cloreto de amônio", 53.49), ("Amônia", 17.03)),
    "Carbonato (NaHCO₃ / Na₂CO₃)": (10.33, ("Bicarbonato de sódio", 84.01), ("Carbonato de sódio anidro", 105.99)),
}


def _ph(name, value):
    if value is None:
        raise ValueError(f"Informe {name}.")
    v = float(value)
    if not 0 <= v <= 14:
        raise ValueError(f"{name} deve estar entre 0 e 14.")
    return v


def buffer(ph, pka, total_conc, volume_ml, mm_acid=None, mm_base=None):
    """Henderson–Hasselbalch: pH = pKa + log([A⁻]/[HA]).

    [A⁻] = C·r/(1 + r), [HA] = C − [A⁻], com r = 10^(pH − pKa). Massa = conc · V[L] · M.
    """
    ph, pka = _ph("pH", ph), _ph("pKa", pka)
    c = positive("Concentração total", total_conc)
    v = positive("Volume", volume_ml) / 1000
    r = 10 ** (ph - pka)
    base = c * r / (1 + r)
    acid = c - base
    warnings = ["Aproximação de Henderson–Hasselbalch: ignora força iônica e temperatura. "
                "Faça o ajuste fino com pHmetro."]
    if abs(ph - pka) > 1:
        warnings.insert(0, f"|pH − pKa| = {abs(ph - pka):.2f} > 1: baixa capacidade tamponante. "
                           "Prefira um par com pKa mais próximo do pH desejado.")
    return {"base_conc": base, "acid_conc": acid, "ratio": r,
            "base_mass": None if mm_base is None else base * v * positive("Massa molar da forma básica", mm_base),
            "acid_mass": None if mm_acid is None else acid * v * positive("Massa molar da forma ácida", mm_acid),
            "warnings": warnings}


def _alpha_base(ph, pka):
    """Fração da forma básica: α = 1 / (1 + 10^(pKa − pH))."""
    return 1 / (1 + 10 ** (pka - ph))


def ph_adjust_buffer(ph_from, ph_to, pka, total_conc, volume_ml, titrant_conc):
    """Volume de ácido/base forte para levar um tampão de pH_a a pH_b.

    n = C_T · V · (α(pH_b) − α(pH_a)) ; n > 0 → base forte, n < 0 → ácido forte ; V_t = |n| / C_t.
    """
    pa, pb, pka = _ph("pH inicial", ph_from), _ph("pH desejado", ph_to), _ph("pKa", pka)
    c = positive("Concentração do tampão", total_conc)
    v = positive("Volume", volume_ml)
    ct = positive("Concentração do titulante", titrant_conc)
    n_mmol = c * v * (_alpha_base(pb, pka) - _alpha_base(pa, pka))  # mol/L · mL = mmol
    warnings = []
    if max(abs(pa - pka), abs(pb - pka)) > 1:
        warnings.append("pH fora da faixa tamponante (pKa ± 1): resultado aproximado.")
    return {"titrant": "base" if n_mmol >= 0 else "ácido", "mmol": abs(n_mmol), "volume_ml": abs(n_mmol) / ct,
            "warnings": warnings}


def _excess_h(ph):
    """E = [H⁺] − [OH⁻] (mol/L)."""
    h = 10 ** -ph
    return h - KW / h


def ph_adjust_strong(ph_from, ph_to, volume_ml, titrant_conc):
    """Volume de ácido/base forte para ajustar uma solução não tamponada (ácido/base forte), com diluição.

    Base: V_t = V · (E_a − E_b) / (C_t + E_b)  ;  Ácido: V_t = V · (E_b − E_a) / (C_t − E_b)
    """
    pa, pb = _ph("pH inicial", ph_from), _ph("pH desejado", ph_to)
    v = positive("Volume", volume_ml)
    ct = positive("Concentração do titulante", titrant_conc)
    ea, eb = _excess_h(pa), _excess_h(pb)
    if pb == pa:
        return {"titrant": "nenhum", "volume_ml": 0.0, "warnings": []}
    if pb > pa:
        if ct + eb <= 0:
            raise ValueError("Base diluída demais para atingir esse pH.")
        vt, kind = v * (ea - eb) / (ct + eb), "base"
    else:
        if ct - eb <= 0:
            raise ValueError("Ácido diluído demais para atingir esse pH.")
        vt, kind = v * (eb - ea) / (ct - eb), "ácido"
    return {"titrant": kind, "volume_ml": vt,
            "warnings": ["Vale para soluções sem tampão (água, ácidos/bases fortes). "
                         "Com tampão ou ácido fraco, use o modo tampão."]}
