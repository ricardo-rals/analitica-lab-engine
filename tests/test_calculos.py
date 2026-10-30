"""Um teste por critério de aceite do SPEC.md (seção 6)."""
import pytest
from pytest import approx

from modules import conversions, methods, spectro, stats, titration
from utils.formatting import fmt, parse_number

REPL = [10.10, 10.20, 10.15]
STD_C = [0, 1, 2, 3, 4]
STD_A = [0.002, 0.101, 0.199, 0.302, 0.398]
REL = 1e-3


def test_ca01_volume_corrigido():
    r = titration.corrected_volume(REPL, 0.05)
    assert r["mean_volume"] == approx(10.15, rel=REL)
    assert r["v_corr"] == approx(10.10, rel=REL)


def test_ca02_concentracao_analito():
    r = titration.analyte_concentration(REPL, 0.05, 0.1000, 1.000, 25.00)
    assert r["concentration"] == approx(0.04040, rel=REL)


def test_ca03_percentual_massa():
    r = titration.mass_percent(REPL, 0.05, 0.1000, 1.000, 2.000, 60.05)
    assert r["percent"] == approx(3.03, rel=REL)


def test_ca04_padronizacao():
    r = titration.standardize(0.5105, 204.22, [25.00], 0.1)
    assert r["c_real"] == approx(0.09999, rel=REL)
    assert r["factor"] == approx(0.9999, rel=REL)


def test_ca05_estatistica():
    r = stats.describe(REPL)
    assert r["sd"] == approx(0.0500, rel=REL)
    assert r["cv"] == approx(0.493, rel=REL)
    assert r["ci_half"] == approx(0.1242, rel=REL)


def test_ca06_grubbs():
    r = stats.grubbs([10.10, 10.12, 10.15, 10.11, 10.90])
    assert r["is_outlier"] and r["suspect"] == 10.90
    assert r["G"] == approx(1.786, rel=REL)
    assert r["G_crit"] == approx(1.715, rel=REL)


def test_ca07_curva():
    c = spectro.calibrate(STD_C, STD_A)
    assert c["a"] == approx(0.0993, rel=REL)
    assert c["b"] == approx(0.0018, rel=REL)
    assert c["r2"] > 0.9999


def test_ca08_amostra_pela_curva():
    r = spectro.predict(spectro.calibrate(STD_C, STD_A), [0.250])
    assert r["concentration"] == approx(2.50, rel=REL)


def test_ca09_lod_loq():
    c = spectro.calibrate(STD_C, STD_A)
    assert c["lod"] == approx(0.055, rel=1e-2)
    assert c["loq"] == approx(0.167, rel=1e-2)


def test_ca10_branco_maior_que_volume():
    with pytest.raises(ValueError, match="branco"):
        titration.corrected_volume(REPL, 10.20)


@pytest.mark.parametrize("call", [
    lambda: titration.corrected_volume([None, float("nan")], 0),
    lambda: titration.corrected_volume([10.1, -1], 0),
    lambda: titration.analyte_concentration(REPL, 0, 0, 1, 25),
    lambda: spectro.calibrate([1, 1, 1], [0.1, 0.1, 0.1]),
    lambda: stats.grubbs([1, 2]),
    lambda: conversions.c1v1(c1=1, v1=None, c2=None, v2=100),
])
def test_ca11_entradas_invalidas(call):
    with pytest.raises(ValueError):
        call()


def test_ca12_c1v1():
    r = conversions.c1v1(c1=1.0, c2=0.1, v2=100)
    assert r["solved"] == "v1" and r["v1"] == approx(10.0)


def test_ca13_dureza_total():
    r = methods.run_titration("dureza_total", [5.00], 0, 0.0100, 1, 50.00)
    assert r["result"] == approx(100.09, rel=REL)


def test_ca14_dureza_magnesiana():
    assert methods.magnesium_hardness(100.09, 60.00) == approx(40.09)


def test_ca15_cloretos():
    r = methods.run_titration("cloretos", [4.20], 0.20, 0.0141, 1, 100.0)
    assert r["result"] == approx(20.0, rel=1e-2)


def test_ca16_alcalinidade_total():
    r = methods.run_titration("alcalinidade_t", [10.00], 0, 0.0100, 1, 100.0)
    assert r["result"] == approx(100.09, rel=REL)


def test_ca17_especiacao_alcalinidade():
    assert methods.alkalinity_speciation(3, 10) == {"hydroxide": 0.0, "carbonate": 6, "bicarbonate": 4}


def test_ca18_dqo():
    r = methods.run_titration("dqo", [7.50], 10.00, 0.2500, 1, 20.00)
    assert r["result"] == approx(250, rel=REL)


def test_ca19_dqo_amostra_maior_que_branco():
    with pytest.raises(ValueError):
        methods.run_titration("dqo", [10.50], 10.00, 0.2500, 1, 20.00)


def test_ca21_concentracao_comum():
    assert conversions.common_concentration(m=5.0, v=250)["c"] == approx(20.0)


def test_ca22_quanto_pesar():
    r = conversions.molar_concentration(c=0.10, mm=58.44, v=500)
    assert r["solved"] == "m" and r["m"] == approx(2.922, rel=REL)


def test_ca23_molalidade():
    assert conversions.molality(m_solute=5.844, mm=58.44, m_solvent=500)["b"] == approx(0.200, rel=REL)


def test_ca24_porcentagem_mv():
    assert conversions.percent("m/v", p=0.9, solution=500)["solute"] == approx(4.5)


def test_ca25_reagente_comercial():
    r = conversions.commercial_reagent(1.19, 37, 36.46, c_final=0.1, v_final=1000)
    assert r["c"] == approx(12.08, rel=REL)
    assert r["volume"] == approx(8.28, rel=REL)


def test_ca26_mistura():
    assert conversions.mix([0.1, 0.4], [100, 200])["c"] == approx(0.300)


def test_ca27_conversao_fracao():
    assert conversions.convert_fraction(0.5, "%", "ppm") == approx(5000)


def test_ca28_densidade():
    assert conversions.density(d=1.84, v=10)["m"] == approx(18.4)


@pytest.mark.parametrize("call", [
    lambda: conversions.percent("m/m", solute=30, solution=20),
    lambda: conversions.molar_concentration(c=0.1, mm=58.44),
    lambda: conversions.commercial_reagent(1.19, 120, 36.46),
    lambda: conversions.mix([0.1], [100, 200]),
])
def test_ca29_solucoes_invalidas(call):
    with pytest.raises(ValueError):
        call()


def test_formatacao_pt_br():
    assert fmt(10.1, 2, "mL") == "10,10 mL"
    assert fmt(0.000123, 2) == "1,23e-04"
    assert parse_number("1.234,5") == 1234.5
    assert parse_number("12,5") == parse_number("12.5") == 12.5
    assert parse_number("  ") is None
    with pytest.raises(ValueError):
        parse_number("abc")


def test_ca20_ferro_espectro():
    r = methods.run_spectro("ferro", STD_C, STD_A, [0.250], dilution=2)
    assert r["result"] == approx(5.00, rel=REL)
