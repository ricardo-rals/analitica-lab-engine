"""Analytica Lab Engine — entrada do app Streamlit.

Toda a química está em modules/; as páginas ficam em ui/ (uma por seção da navegação).
Campos numéricos são texto para aceitar vírgula decimal (RNF-02).
"""
import streamlit as st

from ui import ajuda, estatistica, gestao, rotina, solucoes

st.set_page_config(page_title="Analytica Lab Engine", page_icon="⚗️", layout="wide")

st.sidebar.title("⚗️ Analytica Lab Engine")
st.sidebar.caption("Cálculos de laboratório analítico · primeira vez? Veja **📖 Como usar**")
st.sidebar.subheader("Rastreabilidade")
st.sidebar.text_input("ID da amostra", key="sample_id")
st.sidebar.text_input("Analista", key="analyst")
st.sidebar.text_input("Lote do reagente / titulante", key="lot")
st.sidebar.subheader("Exibição")
st.sidebar.slider("Casas decimais", 2, 6, 4, key="decimais")
st.sidebar.toggle("📘 Modo didático", key="didatico",
                  help="Mostra a explicação de cada cálculo e um botão para carregar um exemplo.")

PAGES = {
    "Rotina": [
        st.Page(rotina.page_analyses, title="Análises de água", icon="🧪", url_path="analises", default=True),
        st.Page(rotina.page_bromatology, title="Bromatologia", icon="🌾", url_path="bromatologia"),
        st.Page(rotina.page_titration, title="Titulação", icon="⚗️", url_path="titulacao"),
        st.Page(rotina.page_standardization, title="Padronização", icon="🎯", url_path="padronizacao"),
        st.Page(rotina.page_spectro, title="Espectrofotometria", icon="🌈", url_path="espectrofotometria"),
    ],
    "Soluções e cálculos": [
        st.Page(solucoes.page_solutions, title="Soluções", icon="💧", url_path="solucoes"),
        st.Page(solucoes.page_stoichiometry, title="Estequiometria e pH", icon="⚖️", url_path="estequiometria"),
        st.Page(solucoes.page_conversions, title="Conversões e erros", icon="🔁", url_path="conversoes"),
    ],
    "Estatística": [
        st.Page(estatistica.page_descriptive, title="Descritiva", icon="📊", url_path="descritiva"),
        st.Page(estatistica.page_distributions, title="Distribuições", icon="🔔", url_path="distribuicoes"),
        st.Page(estatistica.page_hypothesis, title="Testes de hipótese", icon="⚖️", url_path="testes"),
        st.Page(estatistica.page_anova, title="ANOVA", icon="📐", url_path="anova"),
        st.Page(estatistica.page_control, title="Cartas de controle", icon="📈", url_path="cartas"),
        st.Page(estatistica.page_uncertainty, title="Incerteza de medição", icon="🎚️", url_path="incerteza"),
    ],
    "Gestão": [
        st.Page(gestao.page_decision, title="AHP e TOPSIS", icon="🧭", url_path="decisao"),
    ],
    "Ajuda": [
        st.Page(ajuda.page_guide, title="Como usar", icon="📖", url_path="guia"),
        st.Page(ajuda.page_exercises, title="Exercícios", icon="✏️", url_path="exercicios"),
    ],
}

try:
    nav = st.navigation(PAGES, expanded=True)  # mostra as 17 páginas sem "View more"
except TypeError:  # versões antigas do Streamlit (stlite) sem o parâmetro
    nav = st.navigation(PAGES)
nav.run()
