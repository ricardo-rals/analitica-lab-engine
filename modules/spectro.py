"""Espectrofotometria: Lei de Beer-Lambert e curva de calibração (RF-04)."""
import math

import numpy as np
from scipy import stats as sps

from modules.stats import describe
from modules.validation import clean_values, non_negative, positive


def beer_lambert(absorbance, epsilon, path=1.0):
    """A = ε · l · c  →  c = A / (ε · l)

    ε em L·mol⁻¹·cm⁻¹, l em cm, c em mol/L.
    """
    a = non_negative("Absorbância", absorbance)
    return a / (positive("Absortividade molar (ε)", epsilon) * positive("Caminho óptico", path))


def calibrate(concentrations, absorbances):
    """Regressão linear por mínimos quadrados: A = a·c + b.

    s_y/x = √(Σ resíduos² / (n − 2))   (desvio padrão dos resíduos)
    LOD = 3,3 · s_y/x / a ;  LOQ = 10 · s_y/x / a
    """
    x = np.asarray(concentrations, dtype=float)
    y = np.asarray(absorbances, dtype=float)
    if x.shape != y.shape:
        raise ValueError("Concentrações e absorbâncias devem ter o mesmo número de pontos.")
    empty = np.isnan(x) & np.isnan(y)
    x, y = x[~empty], y[~empty]
    if np.isnan(x).any() or np.isnan(y).any():
        raise ValueError("Há padrão com concentração ou absorbância em branco.")
    if len(x) < 3:
        raise ValueError("A curva de calibração exige ao menos 3 padrões.")
    for c in x:
        non_negative("Concentração do padrão", c)
    for a in y:
        non_negative("Absorbância do padrão", a)
    if len(set(x)) < 2:
        raise ValueError("Os padrões precisam ter concentrações diferentes.")

    fit = sps.linregress(x, y)
    a, b = float(fit.slope), float(fit.intercept)
    if a <= 0:
        raise ValueError("Inclinação da curva ≤ 0: a absorbância não cresce com a concentração.")
    residuals = y - (a * x + b)
    s_yx = math.sqrt(float((residuals**2).sum()) / (len(x) - 2))
    r2 = float(fit.rvalue**2)
    warnings = []
    if r2 < 0.995:
        warnings.append(f"R² = {r2:.4f} abaixo de 0,995: linearidade questionável.")
    return {"a": a, "b": b, "r2": r2, "s_yx": s_yx, "lod": 3.3 * s_yx / a, "loq": 10 * s_yx / a,
            "x": x.tolist(), "y": y.tolist(), "residuals": residuals.tolist(),
            "a_min": float(y.min()), "a_max": float(y.max()), "n": len(x), "y_mean": float(y.mean()),
            "sxx": float(((x - x.mean()) ** 2).sum()), "se_a": float(fit.stderr), "se_b": float(fit.intercept_stderr),
            "warnings": warnings}


def predict(curve, absorbances, dilution=1.0):
    """Concentração da amostra pela curva: c = (Ā − b) / a · FD."""
    for v in clean_values(absorbances, "absorbâncias da amostra"):
        non_negative("Absorbância da amostra", v)
    fd = positive("Fator de diluição", dilution)
    st = describe(absorbances)
    a_mean = st["mean"]
    c_read = (a_mean - curve["b"]) / curve["a"]
    warnings = []  # leitura única é o normal no espectro: sem aviso de "réplica única"
    if not curve["a_min"] <= a_mean <= curve["a_max"]:
        warnings.append("Absorbância fora da faixa dos padrões: resultado extrapolado.")
    if c_read < curve["lod"]:
        warnings.append("Abaixo do limite de detecção (LOD): analito não detectado.")
    elif c_read < curve["loq"]:
        warnings.append("Abaixo do limite de quantificação (LOQ): resultado apenas indicativo.")
    m = st["n"]
    # s_x0 = (s_y/x / a) · √(1/m + 1/n + (ȳ0 − ȳ)² / (a² · Σ(xᵢ − x̄)²))   (m leituras da amostra)
    s_x0 = curve["s_yx"] / curve["a"] * math.sqrt(
        1 / m + 1 / curve["n"] + (a_mean - curve["y_mean"]) ** 2 / (curve["a"] ** 2 * curve["sxx"]))
    return {"mean_absorbance": a_mean, "stats": st, "c_read": c_read, "dilution": fd,
            "concentration": c_read * fd, "s_x0": s_x0 * fd, "warnings": warnings}


def curve_diagnostics(curve, alpha=0.05):
    """Diagnóstico da curva (RF-14.1).

    IC de a e b: estimativa ± t(1 − α/2, n − 2) · erro padrão; teste de b = 0: t = b / se_b.
    Falta de ajuste (exige réplicas por nível): F = (SQ_faj / (k − 2)) / (SQ_ep / (n − k)),
      SQ_ep = Σ (yᵢⱼ − ȳᵢ)² (erro puro), SQ_faj = SQ_res − SQ_ep.
    Homocedasticidade: Cochran (RDC 166/2017), C = s²_máx / Σ s²ᵢ por nível; exige o mesmo nº de
      réplicas (≥ 2) em ≥ 2 níveis. C_crít = 1 / (1 + (k − 1) / F(1 − α/k; ν, (k − 1)ν)), ν = réplicas − 1.
    """
    x, y = np.array(curve["x"]), np.array(curve["y"])
    n = len(x)
    t = float(sps.t.ppf(1 - alpha / 2, n - 2))
    t_b = curve["b"] / curve["se_b"] if curve["se_b"] > 0 else math.inf
    p_b = float(2 * sps.t.sf(abs(t_b), n - 2))
    result = {"ci_a": (curve["a"] - t * curve["se_a"], curve["a"] + t * curve["se_a"]),
              "ci_b": (curve["b"] - t * curve["se_b"], curve["b"] + t * curve["se_b"]),
              "t_b": t_b, "p_b": p_b, "intercept_significant": p_b < alpha,
              "lack_of_fit": None, "cochran": None, "notes": []}
    levels = {lv: y[x == lv] for lv in np.unique(x)}
    k = len(levels)
    if k < n and k > 2:
        ss_pe = sum(((g - g.mean()) ** 2).sum() for g in levels.values())
        ss_res = float((np.array(curve["residuals"]) ** 2).sum())
        if ss_pe > 0:
            f = ((ss_res - ss_pe) / (k - 2)) / (ss_pe / (n - k))
            p = float(sps.f.sf(f, k - 2, n - k))
            result["lack_of_fit"] = {"F": float(f), "p": p, "significant": p < alpha}
    else:
        result["notes"].append("Falta de ajuste: repita leituras em pelo menos um nível de concentração para avaliar.")
    reps = [g for g in levels.values() if len(g) >= 2]
    sizes = {len(g) for g in reps}
    if len(reps) >= 2 and len(sizes) == 1:
        var = np.array([g.var(ddof=1) for g in reps])
        if var.sum() > 0:
            kc, nu = len(reps), sizes.pop() - 1
            c = float(var.max() / var.sum())
            f = sps.f.ppf(1 - alpha / kc, nu, (kc - 1) * nu)
            c_crit = float(1 / (1 + (kc - 1) / f))
            result["cochran"] = {"C": c, "C_crit": c_crit, "homoscedastic": c <= c_crit}
    else:
        result["notes"].append("Homocedasticidade (Cochran): exige ao menos 2 níveis com o mesmo nº de réplicas.")
    return result
