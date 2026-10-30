"""Estatística analítica de réplicas: descritiva, outliers, distribuições e exatidão (RF-03, RF-11.5, RF-12)."""
import math

import numpy as np
from scipy import stats as sps

from modules.validation import clean_values, positive


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


def describe_extended(values, weights=None):
    """Tendência central e dispersão completas.

    Mediana, moda (valores mais frequentes; None se todos aparecem uma vez), média ponderada
    x̄w = Σwᵢxᵢ / Σwᵢ, variância s², amplitude, quartis (interpolação linear), IQR = Q3 − Q1,
    erro padrão da média s/√n.
    """
    x = np.array(clean_values(values))
    n = len(x)
    uniq, counts = np.unique(x, return_counts=True)
    modes = uniq[counts == counts.max()].tolist() if counts.max() > 1 else None
    q1, q3 = (float(q) for q in np.percentile(x, [25, 75]))
    result = {"n": n, "mean": float(x.mean()), "median": float(np.median(x)), "modes": modes,
              "min": float(x.min()), "max": float(x.max()), "range": float(x.max() - x.min()),
              "q1": q1, "q3": q3, "iqr": q3 - q1, "variance": None, "sd": None, "sem": None,
              "weighted_mean": None, "warnings": []}
    if n >= 2:
        sd = float(x.std(ddof=1))
        result.update(variance=sd**2, sd=sd, sem=sd / math.sqrt(n))
    if weights is not None:
        w = np.array([positive("Peso", v) for v in weights])
        if len(w) != n:
            raise ValueError("Informe um peso para cada valor.")
        result["weighted_mean"] = float((w * x).sum() / w.sum())
    return result


# Valores críticos do Q de Dixon (95 %, bilateral) — Rorabacher (1991).
DIXON_Q95 = {3: 0.970, 4: 0.829, 5: 0.710, 6: 0.625, 7: 0.568, 8: 0.526, 9: 0.493, 10: 0.466}


def dixon(values):
    """Q de Dixon para o valor mais suspeito (extremo): Q = |suspeito − vizinho| / amplitude.

    Q > Q_crít(95 %) → outlier. Válido para 3 ≤ n ≤ 10.
    """
    x = sorted(clean_values(values))
    n = len(x)
    if not 3 <= n <= 10:
        raise ValueError("O teste de Dixon vale para 3 a 10 valores.")
    spread = x[-1] - x[0]
    if spread == 0:
        return {"applicable": False, "warnings": ["Todos os valores são iguais: Dixon não se aplica."]}
    q_low, q_high = (x[1] - x[0]) / spread, (x[-1] - x[-2]) / spread
    suspect, q = (x[-1], q_high) if q_high >= q_low else (x[0], q_low)
    crit = DIXON_Q95[n]
    return {"applicable": True, "suspect": suspect, "Q": q, "Q_crit": crit, "is_outlier": q > crit,
            "warnings": []}


def boxplot_outliers(values):
    """Regra do boxplot: fora de [Q1 − 1,5·IQR ; Q3 + 1,5·IQR] é discrepante."""
    d = describe_extended(values)
    low, high = d["q1"] - 1.5 * d["iqr"], d["q3"] + 1.5 * d["iqr"]
    x = clean_values(values)
    return {"lower_fence": low, "upper_fence": high, "outliers": [v for v in x if v < low or v > high]}


def normal_probability(mean, sd, lower=None, upper=None):
    """P(lower < X < upper) para X ~ Normal(média, s); limite None = infinito."""
    s = positive("Desvio padrão", sd)
    if lower is not None and upper is not None and lower >= upper:
        raise ValueError("O limite inferior deve ser menor que o superior.")
    lo = 0.0 if lower is None else sps.norm.cdf(lower, mean, s)
    hi = 1.0 if upper is None else sps.norm.cdf(upper, mean, s)
    return float(hi - lo)


def z_score(x, mean, sd):
    """z = (x − média) / s."""
    return (x - mean) / positive("Desvio padrão", sd)


def t_critical(df, confidence=0.95):
    """t bilateral: t(1 − α/2, gl)."""
    if df < 1:
        raise ValueError("Os graus de liberdade devem ser ao menos 1.")
    if not 0 < confidence < 1:
        raise ValueError("O nível de confiança deve estar entre 0 e 1.")
    return float(sps.t.ppf(1 - (1 - confidence) / 2, df))


def shapiro_wilk(values, alpha=0.05):
    """Teste de normalidade de Shapiro–Wilk: p < α → os dados não seguem distribuição normal."""
    x = clean_values(values)
    if len(x) < 3:
        raise ValueError("O teste de Shapiro–Wilk exige ao menos 3 valores.")
    w, p = sps.shapiro(x)
    return {"W": float(w), "p": float(p), "normal": bool(p >= alpha), "alpha": alpha}


def errors(measured, reference):
    """Erro absoluto E = x − x_ref ; erro relativo E% = (x − x_ref) / x_ref × 100."""
    ref = float(reference)
    if ref == 0:
        raise ValueError("O valor de referência não pode ser zero.")
    e = float(measured) - ref
    return {"absolute": e, "relative": e / ref * 100}


def recovery(c_spiked, c_unspiked, c_added):
    """Recuperação (%) = (C_fortificada − C_não fortificada) / C_adicionada × 100."""
    added = positive("Concentração adicionada", c_added)
    r = (float(c_spiked) - float(c_unspiked)) / added * 100
    warnings = [] if 80 <= r <= 120 else [f"Recuperação de {r:.1f} % fora da faixa usual de 80–120 %."]
    return {"recovery": r, "warnings": warnings}
