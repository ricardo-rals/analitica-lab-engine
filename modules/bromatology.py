"""Bromatologia: composição de alimentos e rações (RF-09). Resultados em % (g/100 g).

Cada função recebe as réplicas como linhas de pesagens/volumes (uma tupla por réplica),
calcula o resultado de cada réplica e devolve média, estatística e avisos.
Base seca: X(%MS) = X(%MN) / MS(%) × 100.
"""
from modules.stats import describe
from modules.validation import non_negative, positive

DEFAULT_TOLERANCE_CV = 5.0  # % — padrão do app; o laboratório ajusta na tela conforme o POP

# Fatores de Jones (N → proteína).
NITROGEN_FACTORS = {
    "Geral / rações / carnes": 6.25,
    "Leite e derivados": 6.38,
    "Trigo (grão inteiro)": 5.83,
    "Farinha de trigo": 5.70,
    "Soja": 5.71,
    "Arroz": 5.95,
    "Amendoim, castanhas": 5.46,
    "Gelatina": 5.55,
}

# Ácido de expressão da acidez: (massa molar g/mol, nº de H⁺ ionizáveis k).
ACIDS = {
    "Cítrico": (192.12, 3),
    "Acético": (60.05, 1),
    "Lático": (90.08, 1),
    "Málico": (134.09, 2),
    "Tartárico": (150.09, 2),
    "Oleico (% AGL)": (282.47, 1),
}

KOH_MOLAR_MASS = 56.11


def _require_rows(rows):
    if not rows:
        raise ValueError("Nenhum valor informado em réplicas.")


def _check_percent(name, x):
    if not 0 <= x <= 100:
        raise ValueError(f"{name} fora de 0–100 % ({x:.4g} %): confira as pesagens.")


def _summary(values, tolerance_cv):
    """Estatística das réplicas + aviso de tolerância (CV acima do limite → repetir)."""
    st = describe(values)
    warnings = list(st["warnings"])
    if tolerance_cv is not None and st["cv"] is not None and st["cv"] > tolerance_cv:
        warnings.append(f"CV entre réplicas ({st['cv']:.2f} %) acima da tolerância ({tolerance_cv:g} %): "
                        "repita a análise.")
    return st, warnings


def to_dry_basis(value_mn, dry_matter):
    """X(%MS) = X(%MN) / MS × 100."""
    ms = positive("Matéria seca", dry_matter)
    if ms > 100:
        raise ValueError("A matéria seca não pode passar de 100 %.")
    return value_mn / ms * 100


def _with_dry_basis(result, key, dry_matter):
    result[f"{key}_dm"] = None if dry_matter is None else to_dry_basis(result[key], dry_matter)
    return result


def moisture(rows, tolerance_cv=DEFAULT_TOLERANCE_CV):
    """Umidade por secagem em estufa (105 °C até massa constante).

    rows: [(m_tara, m_amostra, m_tara+seca)] em g.
    U (%) = (m_tara + m_amostra − m_tara+seca) / m_amostra × 100 ;  MS (%) = 100 − U
    """
    _require_rows(rows)
    reps = []
    for i, (tare, sample, dried) in enumerate(rows, 1):
        tare = positive(f"Tara (réplica {i})", tare)
        sample = positive(f"Massa da amostra (réplica {i})", sample)
        dried = positive(f"Tara + amostra seca (réplica {i})", dried)
        if dried > tare + sample:
            raise ValueError(f"Réplica {i}: massa após a secagem maior que antes (ganho de massa).")
        if dried < tare:
            raise ValueError(f"Réplica {i}: massa após a secagem menor que a tara.")
        reps.append((tare + sample - dried) / sample * 100)
    st, warnings = _summary(reps, tolerance_cv)
    return {"replicates": reps, "moisture": st["mean"], "dry_matter": 100 - st["mean"], "stats": st,
            "warnings": warnings}


def predried_dry_matter(asa, ase):
    """Pré-secagem (amostras úmidas): MS total (%) = ASA (%) × ASE (%) / 100.

    ASA = amostra seca ao ar (55–60 °C); ASE = amostra seca em estufa (105 °C).
    """
    asa = positive("ASA", asa)
    ase = positive("ASE", ase)
    _check_percent("ASA", asa)
    _check_percent("ASE", ase)
    return asa * ase / 100


def _residue(rows, labels):
    """% de resíduo pesado: (m_recipiente+resíduo − m_recipiente) / m_amostra × 100."""
    _require_rows(rows)
    reps = []
    for i, (vessel, sample, final) in enumerate(rows, 1):
        vessel = positive(f"{labels[0]} (réplica {i})", vessel)
        sample = positive(f"Massa da amostra (réplica {i})", sample)
        final = positive(f"{labels[1]} (réplica {i})", final)
        residue = final - vessel
        if residue < 0:
            raise ValueError(f"Réplica {i}: massa final menor que a do recipiente vazio.")
        if residue > sample:
            raise ValueError(f"Réplica {i}: resíduo maior que a amostra.")
        reps.append(residue / sample * 100)
    return reps


def ash(rows, dry_matter=None, tolerance_cv=DEFAULT_TOLERANCE_CV):
    """Cinzas (matéria mineral), mufla 550 °C / 5 h.

    rows: [(m_cadinho, m_amostra, m_cadinho+cinzas)] em g.
    MM (%) = (m_cadinho+cinzas − m_cadinho) / m_amostra × 100 ;  MO (%MS) = 100 − MM (%MS)
    """
    reps = _residue(rows, ("Cadinho", "Cadinho + cinzas"))
    st, warnings = _summary(reps, tolerance_cv)
    r = _with_dry_basis({"replicates": reps, "ash": st["mean"], "stats": st, "warnings": warnings},
                        "ash", dry_matter)
    r["organic_matter_dm"] = None if r["ash_dm"] is None else 100 - r["ash_dm"]
    return r


def ether_extract(rows, dry_matter=None, tolerance_cv=DEFAULT_TOLERANCE_CV):
    """Extrato etéreo (Soxhlet, éter de petróleo).

    rows: [(m_balão, m_amostra, m_balão+gordura)] em g.
    EE (%) = (m_balão+gordura − m_balão) / m_amostra × 100
    """
    reps = _residue(rows, ("Balão", "Balão + gordura"))
    st, warnings = _summary(reps, tolerance_cv)
    return _with_dry_basis({"replicates": reps, "ether_extract": st["mean"], "stats": st, "warnings": warnings},
                           "ether_extract", dry_matter)


def kjeldahl(rows, blank, c_titrant, factor=1.0, ratio=1.0, protein_factor=6.25, dry_matter=None,
             tolerance_cv=DEFAULT_TOLERANCE_CV):
    """Proteína bruta por Kjeldahl (NH₃ recolhida em ácido bórico, titulação direta com ácido).

    rows: [(m_amostra g, V_titulante mL)].
    N (%) = (V − V_branco) · C · f · r · 14,007 / (m · 1000) · 100 ;  PB (%) = N (%) · F
    r = mol de N por mol de titulante (HCl → 1; H₂SO₄ → 2).
    """
    _require_rows(rows)
    blank = non_negative("Volume do branco", blank)
    c = positive("Concentração do titulante", c_titrant)
    f = positive("Fator de correção", factor)
    r = positive("Razão r", ratio)
    pf = positive("Fator de conversão N → proteína", protein_factor)
    reps = []
    for i, (mass, volume) in enumerate(rows, 1):
        m = positive(f"Massa da amostra (réplica {i})", mass)
        v = positive(f"Volume gasto (réplica {i})", volume)
        if v <= blank:
            raise ValueError(f"Réplica {i}: volume gasto ({v:g} mL) menor ou igual ao branco ({blank:g} mL).")
        reps.append((v - blank) * c * f * r * 14.007 / (m * 1000) * 100)
    st, warnings = _summary(reps, tolerance_cv)
    n = st["mean"]
    _check_percent("Nitrogênio", n)
    protein = n * pf
    _check_percent("Proteína bruta", protein)
    return _with_dry_basis({"replicates": reps, "nitrogen": n, "protein": protein, "protein_factor": pf,
                            "stats": st, "warnings": warnings}, "protein", dry_matter)


def adf_filter_bag(rows, blank_initial, blank_final, dry_matter=None, tolerance_cv=DEFAULT_TOLERANCE_CV):
    """FDA pelo saquinho filtrante (Ankom).

    rows: [(W1 saco vazio, W2 amostra, W3 saco + resíduo seco)] em g.
    C1 = massa final do saco branco seco / massa inicial do branco
    FDA (%) = (W3 − W1 · C1) / W2 × 100
    """
    _require_rows(rows)
    c1 = positive("Branco final", blank_final) / positive("Branco inicial", blank_initial)
    reps = []
    for i, (w1, w2, w3) in enumerate(rows, 1):
        w1 = positive(f"W1 saco (réplica {i})", w1)
        w2 = positive(f"W2 amostra (réplica {i})", w2)
        w3 = positive(f"W3 saco + resíduo (réplica {i})", w3)
        residue = w3 - w1 * c1
        if residue < 0:
            raise ValueError(f"Réplica {i}: resíduo negativo (W3 < W1 · C1).")
        if residue > w2:
            raise ValueError(f"Réplica {i}: resíduo maior que a amostra.")
        reps.append(residue / w2 * 100)
    st, warnings = _summary(reps, tolerance_cv)
    return _with_dry_basis({"replicates": reps, "adf": st["mean"], "c1": c1, "stats": st, "warnings": warnings},
                           "adf", dry_matter)


def non_fiber_carbohydrates(protein, ether_extract, ash, ndf):
    """CNF (%MS) = 100 − (PB + EE + MM + FDN) ; CT (%MS) = 100 − (PB + EE + MM).

    FDN (ou FDNcp) é digitado: o app não faz a análise de FDN (decisão 7 do SPEC).
    """
    parts = {"PB": protein, "EE": ether_extract, "MM": ash, "FDN": ndf}
    vals = {k: non_negative(k, v) for k, v in parts.items()}
    for k, v in vals.items():
        _check_percent(k, v)
    total = sum(vals.values())
    if total > 100:
        raise ValueError(f"PB + EE + MM + FDN = {total:.2f} %: a soma das frações passa de 100 %, revise os resultados.")
    return {"nfc": 100 - total, "total_carbohydrates": 100 - (vals["PB"] + vals["EE"] + vals["MM"]), "warnings": []}


def acidity(rows, c_titrant, acid, factor=1.0, sample_unit="g", blank=0.0, tolerance_cv=DEFAULT_TOLERANCE_CV):
    """Acidez titulável com NaOH (ou KOH), expressa no ácido predominante.

    rows: [(quantidade de amostra em g ou mL, V_titulante mL)].
    % (m/m ou m/v) = V · C · f · M / (k · m · 10)
    g/L (amostra em mL) = V · C · f · M / (k · V_amostra)    (mmol · g/mol = mg; mg/mL = g/L)
    °Dornic (leite, ácido lático) = g/L × 10                 (1 °D = 0,1 g/L de ácido lático)
    Índice de acidez (mg KOH/g, amostra em g) = V · C · f · 56,11 / m
    Acidez em solução normal (mL/100 g ou mL/100 mL) = V · C · f · 100 / m
    """
    _require_rows(rows)
    if acid not in ACIDS:
        raise ValueError(f"Ácido desconhecido: {acid!r}.")
    if sample_unit not in ("g", "mL"):
        raise ValueError("Unidade da amostra deve ser g ou mL.")
    mm, k = ACIDS[acid]
    c = positive("Concentração do titulante", c_titrant)
    f = positive("Fator de correção", factor)
    blank = non_negative("Volume do branco", blank)
    reps, volumes, amounts = [], [], []
    for i, (amount, volume) in enumerate(rows, 1):
        a = positive(f"Quantidade de amostra (réplica {i})", amount)
        v = positive(f"Volume gasto (réplica {i})", volume) - blank
        if v <= 0:
            raise ValueError(f"Réplica {i}: volume gasto menor ou igual ao branco.")
        reps.append(v * c * f * mm / (k * a * 10))
        volumes.append(v)
        amounts.append(a)
    st, warnings = _summary(reps, tolerance_cv)
    pct = st["mean"]
    by_volume = sample_unit == "mL"
    g_l = pct * 10 if by_volume else None
    mean_ratio = sum(v / a for v, a in zip(volumes, amounts)) / len(volumes)  # mL de titulante por g (ou mL)
    return {"replicates": reps, "percent": pct, "percent_unit": "% m/v" if by_volume else "% m/m",
            "g_per_l": g_l, "dornic": g_l * 10 if (by_volume and acid == "Lático") else None,
            "acid_index": None if by_volume else mean_ratio * c * f * KOH_MOLAR_MASS,
            "normal_solution": mean_ratio * c * f * 100, "stats": st, "warnings": warnings}
