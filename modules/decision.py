"""Decisão multicritério: AHP e TOPSIS (RF-15)."""
import math

import numpy as np

# Índice aleatório de Saaty (IA) para n = 1…10.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def reciprocal_matrix(upper):
    """Monta a matriz recíproca a partir do triângulo superior: aⱼᵢ = 1 / aᵢⱼ, diagonal = 1.

    upper: {(i, j): valor} para i < j.
    """
    n = max(max(i, j) for i, j in upper) + 1
    a = np.ones((n, n))
    for (i, j), v in upper.items():
        if v is None or v <= 0:
            raise ValueError("As comparações devem ser números positivos (escala de Saaty 1/9 a 9).")
        a[i, j], a[j, i] = v, 1 / v
    return a


def ahp(matrix):
    """AHP: pesos pelo autovetor principal; IC = (λmax − n)/(n − 1); RC = IC / IA.

    RC > 0,10 → inconsistente; indica o par cuja comparação mais destoa dos pesos (aᵢⱼ vs wᵢ/wⱼ).
    """
    a = np.asarray(matrix, dtype=float)
    n = a.shape[0]
    if a.ndim != 2 or a.shape != (n, n) or n < 2:
        raise ValueError("A matriz de comparação deve ser quadrada, com ao menos 2 critérios.")
    if n > 10:
        raise ValueError("O índice aleatório de Saaty está tabelado até 10 critérios.")
    if (a <= 0).any():
        raise ValueError("As comparações devem ser números positivos.")
    if not np.allclose(a * a.T, 1, rtol=1e-6):
        raise ValueError("A matriz não é recíproca (aⱼᵢ deve ser 1/aᵢⱼ).")
    eigvals, eigvecs = np.linalg.eig(a)
    i = int(np.argmax(eigvals.real))
    lam = float(eigvals.real[i])
    w = np.abs(eigvecs[:, i].real)
    w = w / w.sum()
    ci = (lam - n) / (n - 1)
    cr = ci / RANDOM_INDEX[n] if RANDOM_INDEX[n] else 0.0
    warnings, worst = [], None
    if cr > 0.10:
        dev = {(p, q): abs(math.log(a[p, q] * w[q] / w[p])) for p in range(n) for q in range(p + 1, n)}
        worst = max(dev, key=dev.get)
        warnings.append(f"RC = {cr:.3f} > 0,10: julgamentos inconsistentes. Revise primeiro a comparação "
                        f"entre os critérios {worst[0] + 1} e {worst[1] + 1}.")
    return {"weights": w.tolist(), "lambda_max": lam, "CI": ci, "CR": cr, "consistent": cr <= 0.10,
            "worst_pair": worst, "warnings": warnings}


def topsis(matrix, weights, benefit):
    """TOPSIS.

    rᵢⱼ = xᵢⱼ / √Σᵢ xᵢⱼ² ; vᵢⱼ = wⱼ·rᵢⱼ ; ideal = melhor de cada critério (máx. se benefício, mín. se custo)
    D⁺ / D⁻ = distância euclidiana à solução ideal / anti-ideal ; C = D⁻ / (D⁺ + D⁻) (1 = melhor)
    """
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2:
        raise ValueError("São necessárias ao menos 2 alternativas.")
    m = x.shape[1]
    w = np.asarray(weights, dtype=float)
    ben = np.asarray(benefit, dtype=bool)
    if len(w) != m or len(ben) != m:
        raise ValueError("Informe um peso e um tipo (benefício/custo) para cada critério.")
    if (w < 0).any() or w.sum() == 0:
        raise ValueError("Os pesos devem ser não negativos e não todos zero.")
    if np.isnan(x).any():
        raise ValueError("Há células em branco na matriz de decisão.")
    if (x < 0).any():
        raise ValueError("Os valores da matriz de decisão não podem ser negativos.")
    norms = np.sqrt((x**2).sum(0))
    if (norms == 0).any():
        raise ValueError("Um critério tem todos os valores iguais a zero.")
    v = x / norms * (w / w.sum())
    ideal = np.where(ben, v.max(0), v.min(0))
    anti = np.where(ben, v.min(0), v.max(0))
    d_plus = np.sqrt(((v - ideal) ** 2).sum(1))
    d_minus = np.sqrt(((v - anti) ** 2).sum(1))
    total = d_plus + d_minus
    closeness = np.where(total == 0, 0.5, d_minus / np.where(total == 0, 1, total))
    order = np.argsort(-closeness).tolist()
    return {"closeness": closeness.tolist(), "d_plus": d_plus.tolist(), "d_minus": d_minus.tolist(),
            "ranking": order, "warnings": []}
