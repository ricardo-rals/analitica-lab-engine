"""Formatação pt-BR de resultados e parse de números com vírgula decimal (RNF-01, RNF-02)."""


def fmt(value, decimals=4, unit=""):
    """Número com vírgula decimal; notação científica quando |x| < 0,01 ou ≥ 1e4."""
    if value is None:
        return "—"
    x = float(value)
    if x != 0 and (abs(x) < 1e-2 or abs(x) >= 1e4):
        s = f"{x:.{decimals}e}"
    else:
        s = f"{x:.{decimals}f}"
    s = s.replace(".", ",")
    return f"{s} {unit}".strip()


def parse_number(text):
    """'12,5' ou '12.5' → 12.5. Vazio → None. Texto inválido → ValueError em português."""
    if text is None:
        return None
    s = str(text).strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "")  # ponto como separador de milhar: '1.234,5'
    try:
        return float(s.replace(",", "."))
    except ValueError:
        raise ValueError(f"Número inválido: {text!r}.") from None
