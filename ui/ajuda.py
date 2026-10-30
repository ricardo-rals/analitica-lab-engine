"""Seção Ajuda: guia de uso e exercícios com gabarito (RF-16.2)."""
from pathlib import Path

import streamlit as st

from modules import bromatology as br
from modules import control, conversions, decision, inferential, spectro, stats, titration, uncertainty
from modules import stoichiometry as sto
from ui.common import f, num, select

GUIDE = Path(__file__).parent.parent / "docs" / "guia.md"


def page_guide():
    """Guia de uso: docs/guia.md, uma seção (## título) por expander."""
    text = GUIDE.read_text(encoding="utf-8")
    for i, section in enumerate(text.removeprefix("## ").split("\n## ")):
        title, _, body = section.partition("\n")
        with st.expander(title, expanded=i == 0):
            st.markdown(body)


def _curve():
    return spectro.calibrate([0, 1, 2, 3, 4], [0.002, 0.101, 0.199, 0.302, 0.398])


# Gabarito calculado pelos próprios módulos: o exercício nunca diverge do que o app calcula.
EXERCISES = [
    {"module": "1 · Fundamentos", "title": "Diluição de HCl",
     "statement": "Quantos mL de HCl 1,0 mol/L são necessários para preparar 250 mL de HCl 0,10 mol/L?",
     "answer": lambda: conversions.c1v1(c1=1.0, c2=0.10, v2=250)["v1"], "unit": "mL",
     "solution": "C₁·V₁ = C₂·V₂ → V₁ = 0,10 × 250 / 1,0 = **25 mL**. Página: Soluções → Diluição."},
    {"module": "1 · Fundamentos", "title": "Ácido sulfúrico concentrado",
     "statement": "Qual a concentração (mol/L) do H₂SO₄ comercial 98 % m/m, densidade 1,84 g/mL (M = 98,08 g/mol)?",
     "answer": lambda: conversions.commercial_reagent(1.84, 98, 98.08)["c"], "unit": "mol/L",
     "solution": "C = d × 1000 × título / M = 1,84 × 1000 × 0,98 / 98,08 ≈ **18,4 mol/L**."},
    {"module": "1 · Fundamentos", "title": "Porcentagem em ppm",
     "statement": "Uma amostra tem 0,25 % m/m de um contaminante. Quanto é isso em ppm?",
     "answer": lambda: conversions.convert_fraction(0.25, "%", "ppm"), "unit": "ppm",
     "solution": "1 % = 10⁴ ppm → 0,25 × 10 000 = **2500 ppm**."},
    {"module": "2 · Intermediários", "title": "Rendimento de precipitação",
     "statement": "1,000 g de Na₂SO₄ (142,04 g/mol) reage com BaCl₂ em excesso e forma BaSO₄ (233,39 g/mol). "
                  "Foram obtidos 1,5800 g de BaSO₄. Qual o rendimento (%)?",
     "answer": lambda: sto.yield_percent(1.58, 1.0 / 142.04 * 233.39)["yield"], "unit": "%",
     "solution": "n = 1,000/142,04 = 7,040 mmol → teórico 7,040 × 233,39 = 1,6431 g → 1,5800/1,6431 × 100 = "
                 "**96,16 %**."},
    {"module": "2 · Intermediários", "title": "Fator de correção do NaOH",
     "statement": "0,4084 g de biftalato de potássio (204,22 g/mol) consumiram 20,10 mL de NaOH ~0,1 mol/L. "
                  "Qual o fator de correção?",
     "answer": lambda: titration.standardize(0.4084, 204.22, [20.10], 0.1)["factor"], "unit": "",
     "solution": "C real = (0,4084/204,22) / 0,02010 = 0,09949 mol/L → f = 0,09949/0,1 ≈ **0,9949**."},
    {"module": "2 · Intermediários", "title": "Tampão fosfato",
     "statement": "Quantos gramas de Na₂HPO₄ (141,96 g/mol) para 500 mL de tampão fosfato 0,10 mol/L a pH 7,00 "
                  "(pKa 7,21)?",
     "answer": lambda: sto.buffer(7.0, 7.21, 0.1, 500, 137.99, 141.96)["base_mass"], "unit": "g",
     "solution": "[A⁻]/[HA] = 10^(7,00 − 7,21) = 0,617 → [A⁻] = 0,10 × 0,617/1,617 = 0,0381 mol/L → "
                 "0,0381 × 0,500 × 141,96 ≈ **2,71 g**."},
    {"module": "3 · Descritiva", "title": "Coeficiente de variação",
     "statement": "Réplicas: 10,10 · 10,20 · 10,15 mg/L. Qual o CV (%)?",
     "answer": lambda: stats.describe([10.10, 10.20, 10.15])["cv"], "unit": "%",
     "solution": "x̄ = 10,15; s = 0,050 → CV = 0,050/10,15 × 100 ≈ **0,49 %**."},
    {"module": "3 · Descritiva", "title": "Teste de Dixon",
     "statement": "Valores: 10,10 · 10,12 · 10,15 · 10,11 · 10,90. Qual o Q de Dixon do valor suspeito?",
     "answer": lambda: stats.dixon([10.10, 10.12, 10.15, 10.11, 10.90])["Q"], "unit": "",
     "solution": "Q = (10,90 − 10,15)/(10,90 − 10,10) = **0,9375** > Q crítico 0,710 (n = 5) → outlier."},
    {"module": "4 · Inferencial e CQ", "title": "Exatidão contra MRC",
     "statement": "Réplicas 10,10 · 10,20 · 10,15; valor certificado 10,00. Qual o t calculado?",
     "answer": lambda: inferential.t_one_sample([10.10, 10.20, 10.15], 10.0)["t"], "unit": "",
     "solution": "t = (10,15 − 10,00)/(0,05/√3) = **5,196** > t crítico 4,303 (gl 2, 95 %) → diferença significativa."},
    {"module": "4 · Inferencial e CQ", "title": "Levey-Jennings",
     "statement": "Controle com média 100 e s = 2. Uma corrida deu 106,5. Qual o escore z?",
     "answer": lambda: control.levey_jennings([106.5], 100, 2)["points"][0]["z"], "unit": "",
     "solution": "z = (106,5 − 100)/2 = **3,25** > 3 → viola a regra 1-3s: rejeitar a corrida."},
    {"module": "5 · Regressão e incerteza", "title": "LOD da curva",
     "statement": "Curva: c = 0, 1, 2, 3, 4 mg/L; A = 0,002 · 0,101 · 0,199 · 0,302 · 0,398. Qual o LOD (mg/L)?",
     "answer": lambda: _curve()["lod"], "unit": "mg/L",
     "solution": "a = 0,0993; s y/x = 0,00166 → LOD = 3,3 × 0,00166/0,0993 ≈ **0,055 mg/L**."},
    {"module": "5 · Regressão e incerteza", "title": "Incerteza expandida",
     "statement": "C = m/(M·V) = 0,09999 mol/L, com m = 0,5105 g (u = 0,0001 g) e V = 25,00 mL (u = 0,02 mL). "
                  "Qual a incerteza expandida U (k = 2), em mol/L?",
     "answer": lambda: uncertainty.budget(0.09999, [
         {"name": "m", "value": 0.5105, "uncertainty": 0.0001, "distribution": "Incerteza padrão (u)"},
         {"name": "V", "value": 25.0, "uncertainty": 0.02, "distribution": "Incerteza padrão (u)"}])["U"],
     "unit": "mol/L",
     "solution": "u_c/C = √((0,0001/0,5105)² + (0,02/25)²) = 8,24×10⁻⁴ → u_c = 8,24×10⁻⁵ → U = 2u_c ≈ "
                 "**1,65×10⁻⁴ mol/L**."},
    {"module": "6 · AHP e TOPSIS", "title": "Peso no AHP",
     "statement": "Critérios custo, exatidão e tempo. Custo é 3× mais importante que exatidão e 5× que tempo; "
                  "exatidão é 3× mais importante que tempo. Qual o peso do custo (fração de 0 a 1)?",
     "answer": lambda: decision.ahp([[1, 3, 5], [1 / 3, 1, 3], [1 / 5, 1 / 3, 1]])["weights"][0], "unit": "",
     "solution": "Autovetor principal normalizado: **0,637** (63,7 %); RC = 0,033 → consistente."},
    {"module": "Bromatologia", "title": "Proteína bruta",
     "statement": "Kjeldahl: 0,2000 g de amostra, 10,00 mL de HCl 0,1000 mol/L (branco 0,10 mL), F = 6,25. "
                  "Qual a PB (%)?",
     "answer": lambda: br.kjeldahl([(0.2, 10.0)], 0.10, 0.1)["protein"], "unit": "%",
     "solution": "N = 9,90 × 0,1 × 14,007/(0,2 × 1000) × 100 = 6,934 % → PB = 6,934 × 6,25 = **43,33 %**."},
]


def page_exercises():
    st.caption("Resolva e confira. Tolerância de 1 % em relação ao gabarito.")
    modules_ = list(dict.fromkeys(e["module"] for e in EXERCISES))
    mod = select("Módulo", modules_, "exe_mod")
    items = [e for e in EXERCISES if e["module"] == mod]
    title = select("Exercício", [e["title"] for e in items], f"exe_title_{mod}")
    ex = next(e for e in items if e["title"] == title)
    st.markdown(f"#### {ex['title']}\n{ex['statement']}")
    label = f"Sua resposta ({ex['unit']})" if ex["unit"] else "Sua resposta"
    answer = num(label, None, f"exe_ans_{mod}_{title}")
    correct = ex["answer"]()
    if answer is not None:
        if abs(answer - correct) <= 0.01 * abs(correct):
            st.success("✔ Correto!")
        else:
            st.error("✘ Ainda não. Revise o cálculo ou veja a resolução.")
    with st.expander("Ver resolução"):
        st.markdown(ex["solution"])
        st.caption(f"Gabarito exato: {f(correct, ex['unit'], 4)}")
