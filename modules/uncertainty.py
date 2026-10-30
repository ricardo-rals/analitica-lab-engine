"""Incerteza de medição pelo GUM (RF-14.2).

Modelo de produto/quociente (y = x₁·x₂/x₃…), que cobre a maioria dos cálculos do app:
    u_c(y) / |y| = √Σ (uᵢ / xᵢ)²
Incerteza padrão de cada fonte:
    Tipo A: u = s / √n (ν = n − 1)       Tipo B: ν = ∞
    padrão: u = valor informado ; certificado: u = U / k ; retangular: u = a / √3 ; triangular: u = a / √6
ν_eff (Welch–Satterthwaite) = u_c⁴ / Σ (cᵢuᵢ)⁴ / νᵢ ;  U = k · u_c
"""
import math

from scipy import stats as sps

from modules.validation import positive

# Distribuição → divisor que leva o valor informado à incerteza padrão (None = Tipo A).
DISTRIBUTIONS = {
    "Incerteza padrão (u)": 1.0,
    "Certificado (U, k = 2)": 2.0,
    "Retangular (± a)": math.sqrt(3),
    "Triangular (± a)": math.sqrt(6),
    "Tipo A (s de n repetições)": None,
}


def standard_uncertainty(uncertainty, distribution, n=None):
    """Converte o valor informado em incerteza padrão; devolve (u, ν)."""
    if distribution not in DISTRIBUTIONS:
        raise ValueError(f"Distribuição desconhecida: {distribution!r}.")
    value = positive("Incerteza", uncertainty)
    divisor = DISTRIBUTIONS[distribution]
    if divisor is None:
        if n is None or n < 2:
            raise ValueError("Tipo A exige o número de repetições n ≥ 2.")
        return value / math.sqrt(n), n - 1
    return value / divisor, math.inf


def budget(result, sources, k=2.0):
    """Orçamento de incerteza.

    result: valor do mensurando y. sources: [{"name", "value", "uncertainty", "distribution", "n"}].
    k: fator de abrangência; None → t de Student (95 %) com ν_eff.
    """
    y = float(result)
    if y == 0:
        raise ValueError("O resultado não pode ser zero (o modelo usa incertezas relativas).")
    if not sources:
        raise ValueError("Nenhum valor informado em fontes de incerteza.")
    rows = []
    for s in sources:
        x = float(s["value"])
        if x == 0:
            raise ValueError(f"{s['name']}: o valor da grandeza não pode ser zero.")
        u, nu = standard_uncertainty(s["uncertainty"], s["distribution"], s.get("n"))
        rows.append({"name": s["name"], "value": x, "u": u, "u_rel": u / abs(x), "nu": nu})
    u_rel_c = math.sqrt(sum(r["u_rel"] ** 2 for r in rows))
    u_c = abs(y) * u_rel_c
    for r in rows:
        r["contribution"] = r["u_rel"] ** 2 / u_rel_c**2 * 100
    denom = sum((abs(y) * r["u_rel"]) ** 4 / r["nu"] for r in rows if math.isfinite(r["nu"]))
    nu_eff = u_c**4 / denom if denom > 0 else math.inf
    if k is None:
        k = 2.0 if math.isinf(nu_eff) else float(sps.t.ppf(0.975, nu_eff))
    return {"result": y, "u_c": u_c, "u_rel": u_rel_c, "nu_eff": nu_eff, "k": k, "U": k * u_c,
            "sources": rows, "warnings": []}
