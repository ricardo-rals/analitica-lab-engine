"""Estatística analítica de réplicas (RF-03)."""
import math

import numpy as np
from scipy import stats as sps

from modules.validation import clean_values


def describe(values, confidence=0.95):
    """Média, desvio padrão amostral, CV% e intervalo de confiança.

    - Média:          x̄ = Σxᵢ / n
    - Desvio padrão:  s = √(Σ(xᵢ − x̄)² / (n − 1))   (amostral, ddof=1)
    - CV (RSD%):      CV = s / |x̄| · 100
    - IC:             x̄ ± t(1 − α/2, n − 1) · s / √n   (t de Student, α = 1 − confiança)
    """
    if not 0 < confidence < 1:
        raise ValueError("O nível de confiança deve estar entre 0 e 1 (ex.: 0,95).")
    x = np.array(clean_values(values))
    n = len(x)
    mean = float(x.mean())
    result = {"n": n, "mean": mean, "sd": None, "cv": None, "confidence": confidence,
              "t": None, "ci_half": None, "ci_low": None, "ci_high": None, "warnings": []}
    if n < 2:
        result["warnings"].append("Com uma única réplica não há desvio padrão nem intervalo de confiança.")
        return result

    sd = float(x.std(ddof=1))
    t = float(sps.t.ppf(1 - (1 - confidence) / 2, n - 1))
    half = t * sd / math.sqrt(n)
    result.update(sd=sd, t=t, ci_half=half, ci_low=mean - half, ci_high=mean + half)
    if mean == 0:
        result["warnings"].append("Média igual a zero: CV indefinido.")
    else:
        result["cv"] = sd / abs(mean) * 100
    return result


def grubbs(values, alpha=0.05):
    """Teste de Grubbs bilateral para um outlier.

    G = max|xᵢ − x̄| / s
    G_crít = ((n − 1)/√n) · √(t² / (n − 2 + t²)),  t = t(1 − α/(2n), n − 2)
    G > G_crít → o valor mais afastado é outlier. Só indica; quem remove é o usuário.
    """
    x = np.array(clean_values(values))
    n = len(x)
    if n < 3:
        raise ValueError("O teste de Grubbs exige ao menos 3 valores.")
    sd = float(x.std(ddof=1))
    if sd == 0:
        return {"applicable": False, "warnings": ["Todos os valores são iguais: Grubbs não se aplica."]}

    dev = np.abs(x - x.mean())
    i = int(dev.argmax())
    g = float(dev[i] / sd)
    t = float(sps.t.ppf(1 - alpha / (2 * n), n - 2))
    g_crit = (n - 1) / math.sqrt(n) * math.sqrt(t**2 / (n - 2 + t**2))
    return {"applicable": True, "suspect": float(x[i]), "index": i, "G": g, "G_crit": g_crit,
            "alpha": alpha, "is_outlier": g > g_crit, "warnings": []}
