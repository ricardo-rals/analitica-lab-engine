"""Cartas de controle: Levey-Jennings com regras de Westgard e Shewhart I-MR (RF-13.4).

Média e desvio alvo vêm das N primeiras medições (fase de estabelecimento, padrão N = 20),
salvo quando o usuário informa alvo e s (ex.: certificado do material de controle).
"""
import numpy as np

from modules.validation import clean_values, positive

BASELINE = 20

# Regra → (descrição, gravidade). 1-2s só alerta; as demais rejeitam a corrida.
WESTGARD = {
    "1-2s": ("1 ponto além de ±2s", "alerta"),
    "1-3s": ("1 ponto além de ±3s", "rejeição"),
    "2-2s": ("2 pontos seguidos além de 2s do mesmo lado", "rejeição"),
    "R-4s": ("2 pontos seguidos em lados opostos, além de ±2s (amplitude > 4s)", "rejeição"),
    "4-1s": ("4 pontos seguidos além de 1s do mesmo lado", "rejeição"),
    "10x": ("10 pontos seguidos do mesmo lado da média", "rejeição"),
}


def _baseline(x, baseline):
    """Valores da fase de estabelecimento + avisos."""
    warnings = []
    if len(x) < baseline:
        warnings.append(f"Só há {len(x)} medições: o alvo foi calculado com todas, não com as {baseline} "
                        "primeiras recomendadas.")
    return x[:baseline], warnings


def westgard_rules(z):
    """Regras de Westgard violadas em cada ponto, a partir dos escores z."""
    out = []
    for i, zi in enumerate(z):
        rules = []
        if abs(zi) > 3:
            rules.append("1-3s")
        elif abs(zi) > 2:
            rules.append("1-2s")
        if i >= 1:
            prev = z[i - 1]
            if (zi > 2 and prev > 2) or (zi < -2 and prev < -2):
                rules.append("2-2s")
            if (zi > 2 and prev < -2) or (zi < -2 and prev > 2):
                rules.append("R-4s")
        if i >= 3 and (all(v > 1 for v in z[i - 3:i + 1]) or all(v < -1 for v in z[i - 3:i + 1])):
            rules.append("4-1s")
        if i >= 9 and (all(v > 0 for v in z[i - 9:i + 1]) or all(v < 0 for v in z[i - 9:i + 1])):
            rules.append("10x")
        out.append(rules)
    return out


def levey_jennings(values, target_mean=None, target_sd=None, baseline=BASELINE):
    """Carta de Levey-Jennings: LC = alvo; alerta ±2s; ação ±3s; z = (x − alvo) / s."""
    x = np.array(clean_values(values, "medições"))
    warnings = []
    if (target_mean is None) != (target_sd is None):
        raise ValueError("Informe alvo e desvio juntos, ou deixe os dois em branco para usar as primeiras medições.")
    if target_mean is None:
        base, warnings = _baseline(x, baseline)
        if len(base) < 2:
            raise ValueError("São necessárias ao menos 2 medições para estimar a média e o desvio.")
        mean, sd = float(base.mean()), float(base.std(ddof=1))
        if sd == 0:
            raise ValueError("Desvio zero na fase de estabelecimento: a carta não se aplica.")
    else:
        mean, sd = float(target_mean), positive("Desvio alvo", target_sd)
    z = ((x - mean) / sd).tolist()
    rules = westgard_rules(z)
    points = []
    for i, (v, zi, r) in enumerate(zip(x.tolist(), z, rules), 1):
        status = "rejeição" if any(WESTGARD[k][1] == "rejeição" for k in r) else ("alerta" if r else "ok")
        points.append({"index": i, "value": v, "z": zi, "rules": r, "status": status})
    limits = {f"{k:+d}s": mean + k * sd for k in (-3, -2, -1, 1, 2, 3)}
    return {"mean": mean, "sd": sd, "limits": limits, "points": points, "warnings": warnings,
            "rejected": sum(p["status"] == "rejeição" for p in points),
            "alerts": sum(p["status"] == "alerta" for p in points)}


def imr_chart(values, baseline=BASELINE):
    """Shewhart individuais e amplitude móvel (I-MR).

    MRᵢ = |xᵢ − xᵢ₋₁| ; LC = x̄ ; LSC/LIC = x̄ ± 2,66·MR̄ ; carta MR: LSC = 3,267·MR̄ (LIC = 0).
    """
    x = np.array(clean_values(values, "medições"))
    if len(x) < 3:
        raise ValueError("A carta I-MR exige ao menos 3 medições.")
    base, warnings = _baseline(x, baseline)
    mr_base = np.abs(np.diff(base))
    mean, mr_bar = float(base.mean()), float(mr_base.mean())
    ucl, lcl, mr_ucl = mean + 2.66 * mr_bar, mean - 2.66 * mr_bar, 3.267 * mr_bar
    mr = [None] + np.abs(np.diff(x)).tolist()
    points = [{"index": i, "value": v, "mr": m, "out": not lcl <= v <= ucl,
               "mr_out": m is not None and m > mr_ucl} for i, (v, m) in enumerate(zip(x.tolist(), mr), 1)]
    return {"mean": mean, "mr_bar": mr_bar, "ucl": ucl, "lcl": lcl, "mr_ucl": mr_ucl, "points": points,
            "warnings": warnings}
