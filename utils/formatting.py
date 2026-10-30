"""Formatação pt-BR de resultados e parse de números com vírgula decimal (RNF-01, RNF-02, RF-11.6)."""
from decimal import ROUND_HALF_EVEN, Decimal


def _dec(x):
    """Decimal a partir do texto curto do float (repr), não do binário: 2.675 vira 2,675 exato.

    Assim o arredondamento segue o número que o analista vê, como manda a NBR 5891.
    """
    return Decimal(repr(float(x)))


def fmt(value, decimals=4, unit=""):
    """Número com vírgula decimal e arredondamento ABNT NBR 5891 (regra do par para o 5).

    Notação científica quando |x| < 0,01 ou ≥ 1e4.
    """
    if value is None:
        return "—"
    x = float(value)
    # format() de Decimal arredonda com ROUND_HALF_EVEN = NBR 5891 sobre o valor decimal exato.
    if x != 0 and (abs(x) < 1e-2 or abs(x) >= 1e4):
        mantissa, exp = format(_dec(x), f".{decimals}e").split("e")
        s = f"{mantissa}e{int(exp):+03d}"  # expoente com 2 dígitos: 1,23e-04
    else:
        s = format(_dec(x), f".{decimals}f")
    s = s.replace(".", ",")
    return f"{s} {unit}".strip()


def round_nbr(value, decimals):
    """Arredonda a `decimals` casas pela NBR 5891 e devolve float."""
    return float(_dec(value).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN))


def significant_figures(text):
    """Nº de algarismos significativos de um número digitado (zeros à esquerda não contam).

    Zeros à direita de um inteiro sem vírgula ('1200') são ambíguos; conta-se como significativos.
    """
    s = str(text).strip().replace(" ", "").lstrip("+-").replace(",", ".")
    mantissa = s.lower().split("e")[0]
    try:
        Decimal(mantissa)
    except ArithmeticError:
        raise ValueError(f"Número inválido: {text!r}.") from None
    digits = mantissa.replace(".", "").lstrip("0")
    return max(len(digits), 1)


def round_significant(value, n):
    """Arredonda a n algarismos significativos pela NBR 5891."""
    if n < 1:
        raise ValueError("O número de algarismos significativos deve ser ao menos 1.")
    d = _dec(value)
    if d == 0:
        return 0.0
    return round_nbr(value, n - 1 - d.adjusted())


def parse_number(text):
    """'12,5' ou '12.5' → 12.5. Vazio → None. Texto inválido → ValueError em português."""
    if text is None:
        return None
    s = str(text).strip().replace(" ", "")
    if not s or s.lower() == "nan":
        return None
    if "," in s and "." in s:
        s = s.replace(".", "")  # ponto como separador de milhar: '1.234,5'
    try:
        return float(s.replace(",", "."))
    except ValueError:
        raise ValueError(f"Número inválido: {text!r}.") from None
