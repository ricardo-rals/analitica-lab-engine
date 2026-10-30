"""Helpers de interface compartilhados pelas páginas.

Persistência entre páginas: com st.navigation, o Streamlit descarta o estado dos widgets da página
que sai de cena. Cada widget daqui guarda o valor em `_keep_<key>` e o restaura ao voltar.
"""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from modules import stats
from utils import report
from utils.formatting import fmt, parse_number

KEEP = "_keep_"


def dec():
    """Casas decimais escolhidas na barra lateral."""
    return st.session_state.get("decimais", 4)


def f(value, unit="", decimals=None):
    """Formata com as casas da barra lateral (NBR 5891)."""
    return fmt(value, dec() if decimals is None else decimals, unit)


def to_input(x):
    if x is None:
        return ""
    return x if isinstance(x, str) else f"{x:g}".replace(".", ",")


# ---------------------------------------------------------------- persistência de widgets
def keep(widget, label, key, default_kw="value", **kw):
    """Cria o widget restaurando o último valor (mesmo após trocar de página)."""
    saved = KEEP + key
    if key not in st.session_state and saved in st.session_state:
        st.session_state[key] = st.session_state[saved]
        kw.pop(default_kw, None)  # valor vem do estado; passar default junto gera aviso do Streamlit
    value = widget(label, key=key, **kw)
    st.session_state[saved] = st.session_state[key]
    return value


def set_fields(values):
    """Callback: preenche campos (ex.: exemplo, fator f) mesmo que estejam em outra página."""
    for key, value in values.items():
        st.session_state.pop(key, None)
        st.session_state[KEEP + key] = value


def num(label, default=None, key=None, help=None):
    """Campo numérico em texto (aceita vírgula); inválido → erro sob o campo e None."""
    raw = keep(st.text_input, label, key, value=to_input(default), help=help)
    try:
        return parse_number(raw)
    except ValueError as e:
        st.error(str(e))
        return None


def select(label, options, key, index=0, **kw):
    return keep(st.selectbox, label, key, default_kw="index", options=options, index=index, **kw)


def radio(label, options, key, index=0, **kw):
    return keep(st.radio, label, key, default_kw="index", options=options, index=index, **kw)


def checkbox(label, key, value=False, **kw):
    return keep(st.checkbox, label, key, value=value, **kw)


def text(label, key, value="", **kw):
    return keep(st.text_input, label, key, value=value, **kw)


def select_slider(label, options, key, value, **kw):
    return keep(st.select_slider, label, key, options=options, value=value, **kw)


def editor(default_df, key, **kw):
    """st.data_editor que sobrevive à troca de página (base = última tabela editada)."""
    base = "_base_" + key
    if key not in st.session_state:
        st.session_state[base] = st.session_state.get(KEEP + key, default_df)
    out = st.data_editor(st.session_state[base], key=key, num_rows="dynamic", hide_index=True, **kw)
    st.session_state[KEEP + key] = out
    return out


def column_editor(label, defaults, key, rows=6):
    df = pd.DataFrame({label: [to_input(v) for v in defaults] + [""] * max(rows - len(defaults), 0)})
    return editor(df, key)[label]


def table_editor(columns, key, rows=4, defaults=None):
    """Tabela de texto com várias colunas (ex.: réplicas de pesagens)."""
    defaults = defaults or []
    data = {c: [to_input(r[i]) for r in defaults] + [""] * max(rows - len(defaults), 0)
            for i, c in enumerate(columns)}
    return editor(pd.DataFrame(data), key)


# ---------------------------------------------------------------- parse
def parse_column(series):
    return [x for x in (parse_number(v) for v in series) if x is not None]


def parse_nan(v):
    x = parse_number(v)
    return float("nan") if x is None else x


def parse_rows(df):
    """Linhas completas da tabela como tuplas de float; linha toda vazia é ignorada, parcial é erro."""
    rows = []
    for i, row in enumerate(df.itertuples(index=False), 1):
        vals = [parse_number(v) for v in row]
        if all(v is None for v in vals):
            continue
        if any(v is None for v in vals):
            raise ValueError(f"Linha {i} da tabela está incompleta.")
        rows.append(tuple(vals))
    return rows


# ---------------------------------------------------------------- exibição
def show_error(e):
    """Campo ainda não preenchido é orientação (info), o resto é erro."""
    msg = str(e)
    (st.info if msg.startswith(("Informe", "Nenhum valor", "Deixe exatamente")) else st.error)(msg)


def show_table(rows, columns=("Etapa", "Valor")):
    st.dataframe(pd.DataFrame(rows, columns=list(columns)), hide_index=True)


def show_warnings(warnings):
    for w in warnings:
        st.warning(w)


def stats_rows(s, unit=""):
    rows = [("Réplicas (n)", str(s["n"])), ("Média", f(s["mean"], unit))]
    if s["sd"] is not None:
        rows += [("Desvio padrão (s)", f(s["sd"], unit)),
                 ("CV / RSD", f(s["cv"], "%", 2)),
                 (f"IC {s['confidence']:.0%} (t = {f(s['t'], '', 3)})", "± " + f(s["ci_half"], unit))]
    return rows


def grubbs_note(values, alpha=0.05):
    if len(values) < 3:
        return
    g = stats.grubbs(values, alpha)
    if not g["applicable"]:
        return
    a = f(alpha, "", 2)
    if g["is_outlier"]:
        st.warning(f"Grubbs (α = {a}): {f(g['suspect'])} é outlier (G = {f(g['G'], '', 3)} > "
                   f"G crítico = {f(g['G_crit'], '', 3)}). Avalie repetir ou remover essa réplica.")
    else:
        st.caption(f"Grubbs (α = {a}): nenhum outlier (G = {f(g['G'], '', 3)} ≤ {f(g['G_crit'], '', 3)}).")


def values_text(values, unit=""):
    return "; ".join(f(v) for v in values) + (f" {unit}" if unit else "")


def conclusion(text, significant):
    (st.warning if significant else st.success)(text)  # significativo é achado, não erro de entrada


def export(title, inputs, steps, results, key):
    now = datetime.now()
    meta = {"Amostra": st.session_state.get("sample_id") or "—",
            "Analista": st.session_state.get("analyst") or "—",
            "Lote do reagente": st.session_state.get("lot") or "—",
            "Data/hora": now.strftime("%d/%m/%Y %H:%M")}
    rep = {"title": title, "inputs": inputs, "steps": steps, "results": results}
    name = f"{key}_{now:%Y%m%d_%H%M}"
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Exportar CSV", report.to_csv(rep, meta), f"{name}.csv", "text/csv", key=f"{key}_csv")
    c2.download_button("⬇️ Exportar PDF", report.to_pdf(rep, meta), f"{name}.pdf", "application/pdf",
                       key=f"{key}_pdf")


# ---------------------------------------------------------------- modo didático (RF-16.1)
def didactic(explanation, example=None, key=None):
    """Explicação da fórmula e botão para carregar valores de exemplo, quando o modo didático está ligado."""
    if not st.session_state.get("didatico"):
        return
    with st.expander("📘 Entenda o cálculo", expanded=True):
        st.markdown(explanation)
        if example:
            st.button("Carregar exemplo", on_click=set_fields, args=(example,), key=f"ex_{key}")


def example_df(columns, rows):
    """DataFrame de texto para carregar em tabelas pelo modo didático."""
    return pd.DataFrame({c: [to_input(r[i]) for r in rows] + [""] * 2 for i, c in enumerate(columns)})


# ---------------------------------------------------------------- gráficos
def bar_chart(labels, values, x_title, y_title):
    df = pd.DataFrame({"item": labels, "valor": values})
    return alt.Chart(df).mark_bar().encode(x=alt.X("valor:Q", title=x_title),
                                           y=alt.Y("item:N", title=y_title, sort="-x"))
