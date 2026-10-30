"""Checagens de entrada compartilhadas pelos módulos de cálculo.

Toda falha vira ValueError com mensagem em português, pronta para a UI exibir.
"""
import math


def _to_float(name, value):
    if value is None:
        raise ValueError(f"Informe {name}.")
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Valor inválido em {name}: {value!r}.") from None
    if math.isnan(x):
        raise ValueError(f"Informe {name}.")
    if math.isinf(x):
        raise ValueError(f"{name} não pode ser infinito.")
    return x


def positive(name, value):
    """Grandeza física estritamente positiva (volume, massa, concentração...)."""
    x = _to_float(name, value)
    if x <= 0:
        raise ValueError(f"{name} deve ser maior que zero (recebido: {x:g}).")
    return x


def non_negative(name, value):
    """Grandeza que pode ser zero, mas não negativa (branco, absorbância...)."""
    x = _to_float(name, value)
    if x < 0:
        raise ValueError(f"{name} não pode ser negativo (recebido: {x:g}).")
    return x


def clean_values(values, name="réplicas"):
    """Lista de réplicas sem as células vazias (None/NaN vindos do data_editor)."""
    out = []
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        out.append(_to_float(name, v))
    if not out:
        raise ValueError(f"Nenhum valor informado em {name}.")
    return out
