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
            "a_min": float(y.min()), "a_max": float(y.max()), "warnings": warnings}


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
    return {"mean_absorbance": a_mean, "stats": st, "c_read": c_read, "dilution": fd,
            "concentration": c_read * fd, "warnings": warnings}
