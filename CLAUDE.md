# Analytica Lab Engine

App web em Python + Streamlit que automatiza cálculos de laboratório analítico: análises de água, bromatologia, titulação, espectrofotometria, soluções, estequiometria/pH, estatística (descritiva, inferencial, cartas de controle, incerteza GUM) e decisão multicritério (AHP/TOPSIS). O analista insere só os dados experimentais; o app mostra as etapas intermediárias e o resultado final com unidade.

A revisão da analista química já foi incorporada ao SPEC.md, na tabela **Registro de decisões**. Decisão marcada `D` foi técnica e pode ser revista pela analista.

**O que construir está em [SPEC.md](SPEC.md).** Antes de implementar algo, confira o requisito (RF-xx) e o critério de aceite (CA-xx) correspondente. Feature nova entra primeiro no SPEC. Ao concluir, marque o status `[x]`.

## Stack

Python 3.11+, streamlit, pandas, numpy, scipy, fpdf2, pytest.

## Estrutura

```
app.py                  # entrada: sidebar (rastreabilidade, casas, modo didático) + st.navigation por seções
ui/                     # páginas, uma por seção: rotina, solucoes, estatistica, gestao, ajuda
  common.py             # helpers: widgets com persistência entre páginas, editores, formatação, exportação, modo didático
modules/
  validation.py         # checagens compartilhadas (vazio, ≤ 0, NaN) -> ValueError em português
  methods.py            # catálogo de análises pré-cadastradas (dureza, alcalinidade, cloretos...) + fórmula genérica
  titration.py          # titulação livre, padronização, % m/m, normalidade
  stats.py              # descritiva, IC (t-Student), Grubbs, Dixon, boxplot, normal/t, Shapiro, erros, recuperação
  spectro.py            # Beer-Lambert, curva de calibração, LOD/LOQ, s_x0, diagnóstico (IC, falta de ajuste, Cochran)
  bromatology.py        # umidade, cinzas, Kjeldahl, extrato etéreo, FDA (Ankom), CNF, acidez
  stoichiometry.py      # reagente limitante, rendimento, tampão (Henderson–Hasselbalch), ajuste de pH
  inferential.py        # testes t (1 amostra, 2 amostras com F, pareado), F, ANOVA 1 fator + Tukey, ANOVA 2 fatores
  control.py            # Levey-Jennings + regras de Westgard, Shewhart I-MR
  uncertainty.py        # orçamento de incerteza GUM (produto/quociente, Welch–Satterthwaite)
  decision.py           # AHP (autovetor, RC) e TOPSIS
  conversions.py        # soluções: resolvedor "preencha todos menos um" (molar, comum, %, molalidade,
                        #   densidade, C1V1), reagente comercial, mistura, FD, conversões
utils/
  report.py             # exportação CSV e PDF
  formatting.py         # formatação pt-BR com arredondamento NBR 5891, algarismos significativos, parse de vírgula
docs/guia.md            # guia de uso exibido na página "Como usar" (uma seção ## por expander)
tests/                  # pytest: test_calculos/test_v2 = um teste por CA-xx; test_app = cada página renderiza
```

## Comandos

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Deploy (GitHub Pages via stlite)

- O app roda **no navegador** (stlite = Streamlit sobre Pyodide). `index.html` carrega os `.py` listados nele. O workflow `.github/workflows/pages.yml` roda o pytest e publica `index.html`, `404.html`, `app.py`, `modules/`, `utils/`, `ui/` e `docs/` a cada push na `main`.
- A navegação muda a URL (`/repo/bromatologia`). Recarregar nessa URL cai no `404.html`, que redireciona para a raiz do app.
- Testar como em produção: `python -m http.server 8765` e abra `http://127.0.0.1:8765/index.html`. A primeira carga leva cerca de 30 s.

## Convenções

- **`modules/` nunca importa streamlit.** Funções puras, testáveis sem UI.
- **Erros:** entradas inválidas lançam `ValueError` com mensagem em português. Avisos não bloqueantes (extrapolação, R² baixo, fator fora da faixa) voltam junto do resultado (chave `warnings` no dict). A UI mostra erros com `st.error` e avisos com `st.warning`.
- **Retorno dos cálculos:** dict com intermediários + resultado final, para a UI exibir as etapas e o relatório reaproveitar.
- **Docstring de cada função de cálculo:** fórmula aplicada e unidades de entrada e saída.
- **Unidades internas:** volumes em mL na interface, convertidos para L dentro da fórmula. Deixe a conversão explícita no código.
- **Idioma:** interface, mensagens e comentários em português do Brasil. Nomes de código em inglês.

## Armadilhas

- **Não crie `modules/statistics.py`:** esconde o módulo `statistics` da stdlib. O nome certo é `stats.py`.
- **Desvio padrão amostral:** `np.std(x, ddof=1)`. O padrão do numpy (`ddof=0`) está errado para réplicas.
- **IC usa t-Student com n−1 graus de liberdade**, nunca z. Com 3 réplicas a diferença é grande.
- **Vírgula decimal:** usuários brasileiros digitam `12,5`. Todo parse de texto passa por `utils/formatting.py`.
- **Grubbs só indica o outlier.** Nunca remova o valor automaticamente; quem decide é o usuário.
- **`.py` (ou `.md` lido pelo app) novo precisa entrar na lista do `index.html`**, senão não existe no navegador. O `tests/test_app.py` acusa se faltar algum.
- **Pyodide não tem `ssl`:** `utils/report.py` cria substitutos para as classes HTTPS antes de importar o fpdf2. Pacote novo com binário próprio precisa ter build para o Pyodide; teste no navegador antes de adicionar.
- **Compatibilidade de versão do Streamlit:** o stlite 0.85.1 embute o **Streamlit 1.45.1** (o `.venv` tem uma versão mais nova). Evite APIs recém-lançadas, como `width="stretch"`; na dúvida, teste no navegador.
- **Widgets de página sempre pelos helpers de `ui/common.py`** (`num`, `select`, `radio`, `editor`...). Com `st.navigation`, o Streamlit apaga o estado dos widgets da página que sai de cena; os helpers guardam o valor em `_keep_<key>` e restauram. Um `st.text_input` direto perde o valor ao trocar de página.
- **Preencher campo por código** (exemplo do modo didático, fator f da padronização): use o callback `set_fields`, nunca atribua direto em `st.session_state[key]` de widget já renderizado.
- **Arredondamento NBR 5891:** `fmt` arredonda sobre `repr(float)` com `Decimal` (2,675 → 2,68). Não troque por f-string de float, que arredonda o binário (2,675 → 2,67).
- **Teste significativo não é erro:** a UI mostra em amarelo (`st.warning`); vermelho (`st.error`) é só entrada inválida, e o `tests/test_app.py` falha se uma página mostrar `st.error` com os valores padrão.
- **Análise pré-cadastrada é dado, não código.** Nova análise = nova entrada no catálogo de `methods.py`. Só crie função própria quando o cálculo não couber na fórmula genérica (ex.: especiação da alcalinidade, dureza magnesiana).
- **DQO é retrotitulação:** `V_corr = V_branco − V_amostra`, o inverso das outras análises. O modo do branco vem do catálogo, nunca fixo na fórmula.
- **Normalidade:** a IUPAC desaconselha a unidade. Só calcule com o nº de equivalentes informado pelo usuário, nunca deduzido.
