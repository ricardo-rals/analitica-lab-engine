# Analytica Lab Engine

App web em Python + Streamlit que automatiza cálculos de laboratório analítico (titulação, padronização, estatística de réplicas, espectrofotometria, diluições). O analista insere só os dados experimentais; o app mostra as etapas intermediárias e o resultado final com unidade.

**O que construir está em [SPEC.md](SPEC.md).** Antes de implementar algo, confira o requisito (RF-xx) e o critério de aceite (CA-xx) correspondente. Feature nova entra primeiro no SPEC. Ao concluir, marque o status `[x]`.

## Stack

Python 3.11+, streamlit, pandas, numpy, scipy, fpdf2, pytest.

## Estrutura

```
app.py                  # UI Streamlit: sidebar (rastreabilidade, casas decimais) + abas
modules/
  validation.py         # checagens compartilhadas (vazio, ≤ 0, NaN) -> ValueError em português
  methods.py            # catálogo de análises pré-cadastradas (dureza, alcalinidade, cloretos...) + fórmula genérica
  titration.py          # titulação livre, padronização, % m/m, normalidade
  stats.py              # média, s, CV, IC (t-Student), Grubbs
  spectro.py            # Beer-Lambert, curva de calibração, LOD/LOQ
  conversions.py        # soluções: resolvedor "preencha todos menos um" (molar, comum, %, molalidade,
                        #   densidade, C1V1), reagente comercial, mistura, FD, conversões
utils/
  report.py             # exportação CSV e PDF
  formatting.py         # formatação pt-BR / notação científica, parse de vírgula decimal
tests/                  # pytest, um teste por CA-xx do SPEC
```

## Comandos

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Deploy (GitHub Pages via stlite)

- O app roda **no navegador** (stlite = Streamlit sobre Pyodide). `index.html` carrega os `.py` listados nele. O workflow `.github/workflows/pages.yml` roda o pytest e publica `index.html`, `app.py`, `modules/` e `utils/` a cada push na `main`.
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
- **`.py` novo precisa entrar na lista do `index.html`**, senão não existe no navegador. O `tests/test_app.py` acusa se faltar algum.
- **Pyodide não tem `ssl`:** `utils/report.py` cria substitutos para as classes HTTPS antes de importar o fpdf2. Pacote novo com binário próprio precisa ter build para o Pyodide; teste no navegador antes de adicionar.
- **Compatibilidade de versão do Streamlit:** o stlite embute uma versão mais antiga que a do `.venv`. Evite APIs recém-lançadas, como `width="stretch"`.
- **Análise pré-cadastrada é dado, não código.** Nova análise = nova entrada no catálogo de `methods.py`. Só crie função própria quando o cálculo não couber na fórmula genérica (ex.: especiação da alcalinidade, dureza magnesiana).
- **DQO é retrotitulação:** `V_corr = V_branco − V_amostra`, o inverso das outras análises. O modo do branco vem do catálogo, nunca fixo na fórmula.
- **Normalidade:** a IUPAC desaconselha a unidade. Só calcule com o nº de equivalentes informado pelo usuário, nunca deduzido.
