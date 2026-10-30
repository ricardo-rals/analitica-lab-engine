"""Estatística inferencial: testes t, F e ANOVA (RF-13.1 a RF-13.3).

Todos devolvem estatística, graus de liberdade, valor-p, valor crítico e conclusão em português.
"""
from itertools import combinations

import numpy as np
from scipy import stats as sps

from modules.validation import clean_values


def _check_alpha(alpha):
    if not 0 < alpha < 1:
        raise ValueError("O nível de significância α deve estar entre 0 e 1 (ex.: 0,05).")


def _conclusion(p, alpha, yes, no):
    conf = f"{1 - alpha:.0%}"
    return (f"{yes} a {conf} (p = {p:.4f} < α = {alpha:g})." if p < alpha
            else f"{no} a {conf} (p = {p:.4f} ≥ α = {alpha:g}).")


def _sample(values, name, minimum=2):
    x = np.array(clean_values(values, name))
    if len(x) < minimum:
        raise ValueError(f"{name}: são necessários ao menos {minimum} valores.")
    return x


def t_one_sample(values, reference, alpha=0.05):
    """t = (x̄ − μ₀) / (s/√n), gl = n − 1. Ex.: resultado × valor certificado do MRC."""
    _check_alpha(alpha)
    x = _sample(values, "Amostra")
    if x.std(ddof=1) == 0:
        raise ValueError("Desvio padrão zero: o teste t não se aplica.")
    t, p = sps.ttest_1samp(x, float(reference))
    df = len(x) - 1
    return {"t": float(t), "df": df, "p": float(p), "t_crit": float(sps.t.ppf(1 - alpha / 2, df)),
            "mean": float(x.mean()), "bias": float(x.mean() - reference), "significant": bool(p < alpha),
            "conclusion": _conclusion(p, alpha, "A média difere do valor de referência",
                                      "Não há diferença significativa em relação à referência")}


def f_test(a, b, alpha=0.05):
    """F = s²_maior / s²_menor (bilateral). F significativo → precisões (variâncias) diferentes."""
    _check_alpha(alpha)
    xa, xb = _sample(a, "Amostra A"), _sample(b, "Amostra B")
    va, vb = xa.var(ddof=1), xb.var(ddof=1)
    if min(va, vb) == 0:
        raise ValueError("Variância zero em uma das amostras: o teste F não se aplica.")
    (vn, dfn), (vd, dfd) = sorted([(va, len(xa) - 1), (vb, len(xb) - 1)], reverse=True)
    f = vn / vd
    p = min(1.0, 2 * min(sps.f.sf(f, dfn, dfd), sps.f.cdf(f, dfn, dfd)))
    return {"F": float(f), "df_num": dfn, "df_den": dfd, "p": float(p),
            "F_crit": float(sps.f.ppf(1 - alpha / 2, dfn, dfd)), "significant": bool(p < alpha),
            "conclusion": _conclusion(p, alpha, "As variâncias são diferentes",
                                      "As variâncias são estatisticamente iguais")}


def t_two_sample(a, b, alpha=0.05):
    """Duas amostras independentes. O teste F decide: variâncias iguais → t agrupado; senão → Welch."""
    _check_alpha(alpha)
    xa, xb = _sample(a, "Amostra A"), _sample(b, "Amostra B")
    f = f_test(xa, xb, alpha)
    equal = not f["significant"]
    res = sps.ttest_ind(xa, xb, equal_var=equal)
    df = float(res.df)
    return {"t": float(res.statistic), "df": df, "p": float(res.pvalue), "t_crit": float(sps.t.ppf(1 - alpha / 2, df)),
            "method": "t com variâncias agrupadas" if equal else "t de Welch (variâncias diferentes)",
            "f_test": f, "mean_a": float(xa.mean()), "mean_b": float(xb.mean()),
            "significant": bool(res.pvalue < alpha),
            "conclusion": _conclusion(res.pvalue, alpha, "As médias são diferentes",
                                      "Não há diferença significativa entre as médias")}


def t_paired(a, b, alpha=0.05):
    """t pareado sobre as diferenças dᵢ = aᵢ − bᵢ (mesmas amostras, dois métodos/analistas)."""
    _check_alpha(alpha)
    xa, xb = _sample(a, "Série A"), _sample(b, "Série B")
    if len(xa) != len(xb):
        raise ValueError("O teste pareado exige o mesmo número de valores nas duas séries.")
    d = xa - xb
    if d.std(ddof=1) == 0:
        raise ValueError("Diferenças todas iguais: o teste t pareado não se aplica.")
    t, p = sps.ttest_rel(xa, xb)
    df = len(d) - 1
    return {"t": float(t), "df": df, "p": float(p), "t_crit": float(sps.t.ppf(1 - alpha / 2, df)),
            "mean_diff": float(d.mean()), "significant": bool(p < alpha),
            "conclusion": _conclusion(p, alpha, "Os métodos/séries diferem",
                                      "Não há diferença significativa entre as séries")}


def anova_one_way(groups, alpha=0.05):
    """ANOVA de um fator + Tukey HSD. groups: {nome: valores}.

    SQ_entre = Σ nᵢ(x̄ᵢ − x̄)² ; SQ_dentro = ΣΣ (xᵢⱼ − x̄ᵢ)² ; F = QM_entre / QM_dentro
    """
    _check_alpha(alpha)
    if len(groups) < 2:
        raise ValueError("A ANOVA precisa de ao menos 2 grupos (para 2, prefira o teste t).")
    data = {name: _sample(v, name) for name, v in groups.items()}
    allx = np.concatenate(list(data.values()))
    gm = allx.mean()
    ss_b = sum(len(x) * (x.mean() - gm) ** 2 for x in data.values())
    ss_w = sum(((x - x.mean()) ** 2).sum() for x in data.values())
    df_b, df_w = len(data) - 1, len(allx) - len(data)
    if ss_w == 0:
        raise ValueError("Variação zero dentro dos grupos: a ANOVA não se aplica.")
    f = (ss_b / df_b) / (ss_w / df_w)
    p = float(sps.f.sf(f, df_b, df_w))
    names = list(data)
    tukey = sps.tukey_hsd(*data.values())
    pairs = [{"a": names[i], "b": names[j], "diff": float(data[names[i]].mean() - data[names[j]].mean()),
              "p": float(tukey.pvalue[i, j]), "significant": bool(tukey.pvalue[i, j] < alpha)}
             for i, j in combinations(range(len(names)), 2)]
    table = [("Entre grupos", ss_b, df_b, ss_b / df_b, f, p), ("Dentro dos grupos", ss_w, df_w, ss_w / df_w, None, None),
             ("Total", ss_b + ss_w, df_b + df_w, None, None, None)]
    return {"F": float(f), "p": p, "F_crit": float(sps.f.ppf(1 - alpha, df_b, df_w)), "table": table,
            "means": {n: float(x.mean()) for n, x in data.items()}, "tukey": pairs, "significant": p < alpha,
            "conclusion": _conclusion(p, alpha, "Há diferença entre os grupos",
                                      "Não há diferença significativa entre os grupos")}


def anova_two_way(cells, alpha=0.05):
    """ANOVA de dois fatores com repetição, delineamento balanceado.

    cells: {(nível_A, nível_B): valores}, mesmo nº de repetições n em todas as combinações.
    SQ_A = b·n·Σ(x̄ᵢ.. − x̄)² ; SQ_B = a·n·Σ(x̄.ⱼ. − x̄)² ; SQ_AB = n·ΣΣ(x̄ᵢⱼ. − x̄ᵢ.. − x̄.ⱼ. + x̄)² ;
    SQ_erro = ΣΣΣ(xᵢⱼₖ − x̄ᵢⱼ.)²
    """
    _check_alpha(alpha)
    a_levels = list(dict.fromkeys(k[0] for k in cells))
    b_levels = list(dict.fromkeys(k[1] for k in cells))
    if len(a_levels) < 2 or len(b_levels) < 2:
        raise ValueError("Cada fator precisa de ao menos 2 níveis.")
    try:
        y = np.array([[clean_values(cells[(i, j)], f"{i} × {j}") for j in b_levels] for i in a_levels], float)
    except KeyError as e:
        raise ValueError(f"Falta a combinação {e.args[0]} (o delineamento deve ser completo).") from None
    except ValueError as e:
        if "inhomogeneous" in str(e) or "sequence" in str(e):
            raise ValueError("Todas as combinações devem ter o mesmo número de repetições.") from None
        raise
    a, b, n = y.shape
    if n < 2:
        raise ValueError("São necessárias ao menos 2 repetições por combinação.")
    gm, ma, mb, mc = y.mean(), y.mean((1, 2)), y.mean((0, 2)), y.mean(2)
    ss = {"A": b * n * ((ma - gm) ** 2).sum(), "B": a * n * ((mb - gm) ** 2).sum(),
          "AB": n * ((mc - ma[:, None] - mb[None, :] + gm) ** 2).sum(), "erro": ((y - mc[..., None]) ** 2).sum()}
    df = {"A": a - 1, "B": b - 1, "AB": (a - 1) * (b - 1), "erro": a * b * (n - 1)}
    if ss["erro"] == 0:
        raise ValueError("Variação zero entre repetições: a ANOVA não se aplica.")
    mse = ss["erro"] / df["erro"]
    effects = {}
    for k in ("A", "B", "AB"):
        f = (ss[k] / df[k]) / mse
        p = float(sps.f.sf(f, df[k], df["erro"]))
        effects[k] = {"SS": float(ss[k]), "df": df[k], "MS": float(ss[k] / df[k]), "F": float(f), "p": p,
                      "F_crit": float(sps.f.ppf(1 - alpha, df[k], df["erro"])), "significant": p < alpha}
    return {"effects": effects, "error": {"SS": float(ss["erro"]), "df": df["erro"], "MS": float(mse)},
            "a_levels": a_levels, "b_levels": b_levels, "cell_means": mc.tolist(), "alpha": alpha}
