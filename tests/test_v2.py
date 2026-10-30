"""Critérios de aceite CA-30 a CA-57 (SPEC.md, RF-09 a RF-15)."""
import pytest
from pytest import approx

from modules import (bromatology as br, control, conversions, decision, inferential, spectro, stats,
                     stoichiometry as sto, titration, uncertainty)
from utils.formatting import fmt, round_significant, significant_figures

REL = 1e-3
A = [10.10, 10.20, 10.15]
B = [10.30, 10.35, 10.25, 10.40]


# ---------------------------------------------------------------- bromatologia
def test_ca30_umidade():
    r = br.moisture([(20.0, 2.0, 21.82)])
    assert r["moisture"] == approx(9.00, rel=REL) and r["dry_matter"] == approx(91.00, rel=REL)


def test_ca31_pre_secagem():
    assert br.predried_dry_matter(30.0, 90.0) == approx(27.0)


def test_ca32_cinzas():
    r = br.ash([(20.0, 2.0, 20.12)], dry_matter=91.0)
    assert r["ash"] == approx(6.00, rel=REL)
    assert r["ash_dm"] == approx(6.593, rel=REL)
    assert r["organic_matter_dm"] == approx(93.407, rel=REL)


def test_ca33_kjeldahl():
    r = br.kjeldahl([(0.2000, 10.00)], blank=0.10, c_titrant=0.1, protein_factor=6.25)
    assert r["nitrogen"] == approx(6.934, rel=REL) and r["protein"] == approx(43.33, rel=REL)


def test_ca34_extrato_etereo():
    assert br.ether_extract([(100.0, 2.0, 100.06)])["ether_extract"] == approx(3.00, rel=REL)


def test_ca35_fda_ankom():
    r = br.adf_filter_bag([(0.5, 0.5, 0.65)], blank_initial=0.5, blank_final=0.501)
    assert r["c1"] == approx(1.002) and r["adf"] == approx(29.80, rel=REL)


def test_ca36_cnf():
    r = br.non_fiber_carbohydrates(20, 3, 6, 40)
    assert r["nfc"] == approx(31.0) and r["total_carbohydrates"] == approx(71.0)


def test_ca37_acidez_citrica():
    assert br.acidity([(10.0, 10.0)], 0.1, "Cítrico")["percent"] == approx(0.6404, rel=REL)


def test_ca38_acidez_oleo():
    r = br.acidity([(5.0, 2.0)], 0.1, "Oleico (% AGL)")
    assert r["percent"] == approx(1.130, rel=REL) and r["acid_index"] == approx(2.244, rel=REL)


def test_ca53_dornic():
    r = br.acidity([(10.0, 1.60)], 0.1111, "Lático", sample_unit="mL")
    assert r["g_per_l"] == approx(1.601, rel=REL) and r["dornic"] == approx(16.01, rel=REL)


def test_bromatologia_tolerancia_e_erros():
    r = br.moisture([(20.0, 2.0, 21.82), (20.0, 2.0, 21.60)], tolerance_cv=5)
    assert any("tolerância" in w for w in r["warnings"])
    with pytest.raises(ValueError, match="ganho de massa"):
        br.moisture([(20.0, 2.0, 22.5)])
    with pytest.raises(ValueError, match="100 %"):
        br.non_fiber_carbohydrates(40, 10, 10, 50)


# ---------------------------------------------------------------- cálculos intermediários
def test_ca39_estequiometria_rendimento():
    r = sto.stoichiometry([
        {"name": "Na2SO4", "role": "reagente", "coef": 1, "molar_mass": 142.04, "mass": 1.000},
        {"name": "BaCl2", "role": "reagente", "coef": 1, "molar_mass": 208.23, "mass": None},
        {"name": "BaSO4", "role": "produto", "coef": 1, "molar_mass": 233.39},
    ])
    assert r["limiting"] == "Na2SO4"
    theo = r["products"][0]["theoretical_mass"]
    assert theo == approx(1.6431, rel=REL)
    assert sto.yield_percent(1.58, theo)["yield"] == approx(96.16, rel=REL)


def test_estequiometria_limitante_com_duas_massas():
    r = sto.stoichiometry([
        {"name": "H2", "role": "reagente", "coef": 2, "molar_mass": 2.016, "mass": 4.0},
        {"name": "O2", "role": "reagente", "coef": 1, "molar_mass": 32.00, "mass": 16.0},
        {"name": "H2O", "role": "produto", "coef": 2, "molar_mass": 18.015},
    ])
    assert r["limiting"] == "O2"                                # 0,5 mol O2 × 2 = 1 mol H2 < 1,98 mol
    assert r["products"][0]["theoretical_mass"] == approx(18.015, rel=REL)


def test_ca40_tampao():
    r = sto.buffer(5.00, 4.76, 0.1, 1000, mm_acid=60.05, mm_base=136.08)
    assert r["base_conc"] == approx(0.06347, rel=REL) and r["acid_conc"] == approx(0.03653, rel=REL)
    assert r["base_mass"] == approx(8.638, rel=REL) and r["acid_mass"] == approx(2.193, rel=REL)


def test_ca51_ajuste_ph_tampao():
    r = sto.ph_adjust_buffer(4.76, 5.00, 4.76, 0.1, 1000, 1.0)
    assert r["titrant"] == "base" and r["volume_ml"] == approx(13.47, rel=REL)


def test_ca52_ajuste_ph_forte():
    r = sto.ph_adjust_strong(2, 3, 100, 0.1)
    assert r["titrant"] == "base" and r["volume_ml"] == approx(8.911, rel=REL)
    assert sto.ph_adjust_strong(3, 2, 100, 0.1)["titrant"] == "ácido"


def test_ca41_recuperacao_e_erros():
    assert stats.recovery(6.9, 2.0, 5.0)["recovery"] == approx(98.0)
    e = stats.errors(10.2, 10.0)
    assert e["absolute"] == approx(0.2) and e["relative"] == approx(2.0)


# ---------------------------------------------------------------- descritiva
def test_ca54_dixon_e_boxplot():
    data = [10.10, 10.12, 10.15, 10.11, 10.90]
    d = stats.dixon(data)
    assert d["is_outlier"] and d["Q"] == approx(0.9375) and d["Q_crit"] == 0.710
    assert stats.boxplot_outliers(data)["outliers"] == [10.90]


def test_descritiva_estendida():
    d = stats.describe_extended([1, 2, 2, 3, 4], weights=[1, 1, 1, 1, 4])
    assert d["median"] == 2 and d["modes"] == [2] and d["range"] == 3
    assert d["iqr"] == approx(1.0) and d["weighted_mean"] == approx(3.0)


def test_distribuicoes():
    assert stats.normal_probability(0, 1, -1.96, 1.96) == approx(0.95, rel=REL)
    assert stats.t_critical(2) == approx(4.303, rel=REL)
    assert not stats.shapiro_wilk([10.10, 10.12, 10.15, 10.11, 10.90])["normal"]


# ---------------------------------------------------------------- inferencial
def test_ca42_t_uma_amostra():
    r = inferential.t_one_sample(A, 10.00)
    assert r["t"] == approx(5.196, rel=REL) and r["df"] == 2 and r["p"] == approx(0.0351, rel=1e-2)
    assert r["significant"]


def test_ca43_teste_f():
    r = inferential.f_test(A, B)
    assert r["F"] == approx(1.667, rel=REL) and r["p"] == approx(0.7926, rel=1e-2) and not r["significant"]


def test_ca44_t_duas_amostras():
    r = inferential.t_two_sample(A, B)
    assert r["method"].startswith("t com variâncias agrupadas")
    assert r["t"] == approx(-3.873, rel=REL) and r["df"] == 5 and r["p"] == approx(0.01172, rel=1e-2)


def test_ca45_t_pareado():
    r = inferential.t_paired([10.1, 10.3, 10.2], [10.2, 10.4, 10.2])
    assert r["t"] == approx(-2.0, rel=REL) and r["p"] == approx(0.1835, rel=1e-2) and not r["significant"]


def test_ca46_anova_tukey():
    r = inferential.anova_one_way({"G1": [10.1, 10.2, 10.15], "G2": [10.3, 10.35, 10.25], "G3": [10.0, 10.05, 10.1]})
    assert r["F"] == approx(19.0, rel=REL) and r["p"] == approx(0.002536, rel=1e-2)
    sig = {(t["a"], t["b"]) for t in r["tukey"] if t["significant"]}
    assert sig == {("G1", "G2"), ("G2", "G3")}


def test_ca55_anova_dois_fatores():
    r = inferential.anova_two_way({("A1", "B1"): [10, 11], ("A1", "B2"): [12, 13],
                                   ("A2", "B1"): [14, 15], ("A2", "B2"): [20, 21]})
    e = r["effects"]
    assert e["A"]["F"] == approx(144) and e["B"]["F"] == approx(64) and e["AB"]["F"] == approx(16)
    with pytest.raises(ValueError, match="mesmo número"):
        inferential.anova_two_way({("A1", "B1"): [10, 11], ("A1", "B2"): [12],
                                   ("A2", "B1"): [14, 15], ("A2", "B2"): [20, 21]})


# ---------------------------------------------------------------- controle
def test_ca47_levey_jennings_westgard():
    r = control.levey_jennings([100, 101, 99, 104.5, 106.5], target_mean=100, target_sd=2)
    rules = [p["rules"] for p in r["points"]]
    assert rules[3] == ["1-2s"] and r["points"][3]["status"] == "alerta"
    assert set(rules[4]) == {"1-3s", "2-2s"} and r["points"][4]["status"] == "rejeição"


def test_westgard_regras_de_sequencia():
    z = [1.5, 1.2, 1.1, 1.3] + [0.5] * 6
    rules = control.westgard_rules(z)
    assert "4-1s" in rules[3] and "10x" in rules[9]
    assert "R-4s" in control.westgard_rules([2.5, -2.5])[1]


def test_carta_imr_e_estabelecimento():
    r = control.imr_chart([10, 11, 10, 12, 11, 30], baseline=5)  # estabelecimento: 5 primeiros
    assert r["mr_bar"] == approx(1.25) and r["points"][-1]["out"] and not r["warnings"]
    assert control.imr_chart([10, 11, 10, 12, 11, 30])["warnings"]  # menos de 20 medições
    lj = control.levey_jennings(list(range(1, 31)), baseline=20)
    assert lj["mean"] == approx(10.5)                           # só as 20 primeiras


# ---------------------------------------------------------------- regressão e incerteza
def test_ca56_sx0_e_intercepto():
    c = spectro.calibrate([0, 1, 2, 3, 4], [0.002, 0.101, 0.199, 0.302, 0.398])
    assert spectro.predict(c, [0.250])["s_x0"] == approx(0.01854, rel=REL)
    d = spectro.curve_diagnostics(c)
    assert d["p_b"] == approx(0.2568, rel=1e-2) and not d["intercept_significant"]


def test_diagnostico_falta_de_ajuste_e_cochran():
    c = spectro.calibrate([0, 0, 1, 1, 2, 2, 3, 3], [0.001, 0.003, 0.1, 0.104, 0.2, 0.196, 0.31, 0.3])
    d = spectro.curve_diagnostics(c)
    assert d["lack_of_fit"] is not None and not d["lack_of_fit"]["significant"]
    assert d["cochran"]["C_crit"] == approx(0.9065, rel=REL) and d["cochran"]["homoscedastic"]


def test_ca48_incerteza_padronizacao():
    c = titration.standardize(0.5105, 204.22, [25.00], 0.1)["c_real"]
    r = uncertainty.budget(c, [
        {"name": "Massa", "value": 0.5105, "uncertainty": 0.0001, "distribution": "Incerteza padrão (u)"},
        {"name": "Volume", "value": 25.00, "uncertainty": 0.02, "distribution": "Incerteza padrão (u)"},
    ])
    assert r["u_c"] == approx(8.2355e-5, rel=REL) and r["U"] == approx(1.6471e-4, rel=REL)
    assert sum(s["contribution"] for s in r["sources"]) == approx(100)


def test_incerteza_tipo_a_welch_satterthwaite():
    r = uncertainty.budget(1.0, [{"name": "Rep.", "value": 1.0, "uncertainty": 0.01,
                                  "distribution": "Tipo A (s de n repetições)", "n": 4}], k=None)
    assert r["u_c"] == approx(0.005) and r["nu_eff"] == approx(3) and r["k"] == approx(3.182, rel=REL)


# ---------------------------------------------------------------- decisão
def test_ca49_ahp():
    r = decision.ahp([[1, 3, 5], [1 / 3, 1, 3], [1 / 5, 1 / 3, 1]])
    assert r["weights"] == approx([0.637, 0.2583, 0.1047], rel=REL)
    assert r["lambda_max"] == approx(3.0385, rel=REL) and r["CR"] == approx(0.0332, rel=1e-2) and r["consistent"]


def test_ahp_inconsistente_aponta_par():
    r = decision.ahp(decision.reciprocal_matrix({(0, 1): 9, (0, 2): 1 / 9, (1, 2): 9}))
    assert not r["consistent"] and r["worst_pair"] is not None and r["warnings"]


def test_ca50_topsis():
    w = decision.ahp([[1, 3, 5], [1 / 3, 1, 3], [1 / 5, 1 / 3, 1]])["weights"]
    r = decision.topsis([[250, 98.0, 2.0], [180, 95.0, 3.0], [300, 99.5, 1.5]], w, [False, True, False])
    assert r["closeness"] == approx([0.430, 0.8133, 0.1867], rel=REL)
    assert r["ranking"] == [1, 0, 2]


# ---------------------------------------------------------------- fundamentos
def test_ca57_nbr5891():
    assert fmt(2.675, 2) == "2,68" and fmt(2.665, 2) == "2,66" and fmt(2.6651, 2) == "2,67"
    assert fmt(0.000125, 1) == "1,2e-04"


def test_algarismos_significativos():
    assert significant_figures("0,00120") == 3 and significant_figures("1,20e3") == 3
    assert round_significant(0.012345, 3) == approx(0.0123) and round_significant(1235, 3) == approx(1240)


def test_conversoes_si_e_regra_de_tres():
    assert conversions.convert_unit(760, "Pressão", "mmHg", "atm") == approx(1.0)
    assert conversions.convert_unit(25, "Temperatura", "°C", "K") == approx(298.15)
    assert conversions.convert_unit(1.5, "Massa", "g", "mg") == approx(1500)
    assert conversions.rule_of_three(a=2, b=10, c=3)["x"] == approx(15)
    assert conversions.rule_of_three(a=4, b=6, c=8, inverse=True)["x"] == approx(3)
    with pytest.raises(ValueError, match="zero absoluto"):
        conversions.convert_unit(-300, "Temperatura", "°C", "K")
