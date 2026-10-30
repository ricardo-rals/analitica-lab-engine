# SPEC — Analytica Lab Engine

> Fonte da verdade do que o sistema deve fazer. Toda feature nasce aqui (requisito + critério de aceite) antes de virar código.
> Status: `[ ]` pendente · `[~]` parcial · `[x]` feito.

## 1. Visão

Software web (Streamlit) para laboratório analítico: o analista **só insere os dados experimentais** (réplicas, branco, massas, concentrações conhecidas) e o sistema calcula e mostra **cada etapa intermediária** e o **resultado final com unidade**, pronto para laudo.

**Usuário:** analista/técnico de laboratório químico. Sabe a química, não quer fazer conta na mão nem em planilha frágil.

**Princípios**
- Mostrar o caminho, não só o resultado (volume médio → branco subtraído → mols → concentração).
- Recusar dado fisicamente impossível com mensagem clara, nunca devolver `NaN`/`inf`.
- Toda fórmula testada contra valor calculado à mão (seção 6).

## 2. Escopo

**Dentro (v1):** análises pré-cadastradas (dureza, alcalinidade, cloretos, acidez, OD, DQO), titulação livre, padronização, estatística de réplicas, espectrofotometria (Beer-Lambert e curva de calibração), diluições/conversão de unidade, exportação CSV/PDF.

**Fora (v1), candidatos a v2:** teste t/F entre métodos, cartas de controle, incerteza de medição (GUM), importação de arquivo de equipamento, login/multiusuário, banco de dados.

## 3. Requisitos funcionais

### RF-01 Titulação (`modules/titration.py`)
- [x] **RF-01.1 Volume corrigido:** `V_corr = média(V_réplicas) − V_branco` (mL). Mostra média das réplicas, branco e V_corr.
- [x] **RF-01.2 Concentração do analito:** `C_analito = (C_tit · f · V_corr · r) / V_alíquota`, onde `r = ν_analito / ν_titulante` (razão estequiométrica da reação, padrão 1).
- [x] **RF-01.3 Teor na amostra sólida:** `% m/m = (C_tit · f · V_corr[L] · r · M_analito) / m_amostra · 100`.
- [x] **RF-01.4 Normalidade (opcional):** `N = C · k`, com `k` = nº de equivalentes informado pelo usuário (H⁺ ou e⁻ trocados). Exibir aviso de que a IUPAC desaconselha a unidade.
- **Validações:** réplicas vazias; volume ≤ 0; branco < 0; branco ≥ média das réplicas (V_corr ≤ 0); C_tit, f, V_alíquota, m_amostra, M ≤ 0.

### RF-02 Padronização de solução (`modules/titration.py`)
- [x] **RF-02.1** A partir de padrão primário: `C_real = (m_padrão / M_padrão) · r / V_gasto[L]`; `f = C_real / C_nominal`.
- [x] **RF-02.2** Padrões pré-cadastrados (selectbox) com massa molar: biftalato de potássio (204,22 g/mol), Na₂CO₃ (105,99 g/mol), ácido oxálico di-hidratado (126,07 g/mol); opção "outro" com M manual.
- [x] **RF-02.3** O `f` calculado pode ser enviado para a aba de Titulação (via `st.session_state`).
- **Validações:** f fora de 0,90–1,10 → aviso (não erro): "fator fora da faixa usual, verifique a solução".

### RF-03 Estatística de réplicas (`modules/stats.py`)
- [x] **RF-03.1** n, média, desvio padrão amostral (`ddof=1`), CV/RSD% = `s / x̄ · 100`.
- [x] **RF-03.2 Intervalo de confiança:** `x̄ ± t(1−α/2, n−1) · s / √n`, nível selecionável (90/95/99%, padrão 95%).
- [x] **RF-03.3 Outlier — teste de Grubbs** (bilateral, n ≥ 3): `G = max|xᵢ − x̄| / s`; `G_crít = ((n−1)/√n) · √(t² / (n−2+t²))`, com `t = t(α/(2n), n−2)`. Indica o valor suspeito e se é rejeitado. **Não remove sozinho**: o usuário decide.
- [x] **RF-03.4** Reutilizável: titulação e espectro chamam as mesmas funções para as réplicas.
- **Validações:** n < 2 → sem desvio/IC (mensagem); n < 3 → sem Grubbs; s = 0 → CV = 0 e Grubbs não aplicável; média = 0 → CV indefinido (mensagem).

### RF-04 Espectrofotometria (`modules/spectro.py`)
- [x] **RF-04.1 Beer-Lambert direto:** `c = A / (ε · l)` (ε em L·mol⁻¹·cm⁻¹, l em cm, padrão 1 cm).
- [x] **RF-04.2 Curva de calibração:** regressão linear `A = a·c + b` (mínimos quadrados) sobre padrões (tabela editável c × A). Mostrar a, b, R², equação.
- [x] **RF-04.3 Concentração da amostra:** `c = (A − b) / a`; se várias leituras, usar a média (RF-03).
- [x] **RF-04.4 LOD/LOQ:** `s_y/x = √(Σresíduos² / (n−2))`; `LOD = 3,3 · s_y/x / a`; `LOQ = 10 · s_y/x / a`.
- [x] **RF-04.5 Gráfico:** pontos + reta + amostra marcada; gráfico de resíduos.
- **Validações:** < 3 padrões; a = 0; ε ou l ≤ 0; A < 0; R² < 0,995 → aviso; A da amostra fora da faixa dos padrões → aviso de extrapolação; c < LOQ → aviso "abaixo do limite de quantificação".

### RF-05 Diluição e unidades (`modules/conversions.py`)
- [x] **RF-05.1** `C₁V₁ = C₂V₂` resolvendo qualquer uma das quatro variáveis deixada em branco.
- [x] **RF-05.2** Fator de diluição `FD = V_final / V_alíquota`, aplicável ao resultado de RF-01 e RF-04 (`C_original = C_medida · FD`).
- [x] **RF-05.3** Conversão mol/L ↔ g/L ↔ mg/L (= ppm em solução aquosa diluída), usando M.

### RF-06 Relatórios (`utils/report.py`)
- [x] **RF-06.1** Exportar CSV com entradas, intermediários e resultado de cada cálculo.
- [x] **RF-06.2** Exportar PDF (fpdf2) com cabeçalho de rastreabilidade: **ID da amostra, analista, data/hora, lote do reagente/titulante**, mais entradas, intermediários e resultado.
- [x] **RF-06.3** Campos de rastreabilidade na sidebar, compartilhados entre as abas.

### RF-07 Análises pré-cadastradas (`modules/methods.py`)
Seção onde o analista escolhe a análise (ex.: "Dureza total") e preenche só o que aquela análise pede. Fórmula, titulante, indicador, massa molar de expressão e unidade já vêm prontos.

- [x] **RF-07.1 Catálogo como dado:** cada análise é uma entrada (dict) com nome, referência normativa, titulante, indicador, razão estequiométrica `r`, massa molar de expressão `M`, unidade, modo do branco e instruções curtas. Análise nova = nova entrada, sem código novo.
- [x] **RF-07.2 Fórmula genérica** (titulação de amostra líquida):
  `resultado [mg/L] = V_corr[mL] · C_tit · f · r · M[g/mol] · 1000 / V_amostra[mL]`
- [x] **RF-07.3 Modo do branco:** `direto` (`V_corr = V_amostra − V_branco`) ou `retrotitulação` (`V_corr = V_branco − V_amostra`, usado na DQO).
- [x] **RF-07.4 Catálogo v1:**

| Análise | Referência | Titulante | Indicador | r | M (g/mol) | Unidade |
|---------|-----------|-----------|-----------|---|-----------|---------|
| Dureza total | SM 2340 C | EDTA | Negro de eriocromo T, pH 10 | 1 | 100,09 | mg CaCO₃/L |
| Dureza cálcica | SM 3500-Ca B | EDTA | Murexida, pH 12–13 | 1 | 100,09 | mg CaCO₃/L |
| Dureza magnesiana | derivada | — | — | — | — | mg CaCO₃/L (= total − cálcica) |
| Alcalinidade P e T | SM 2320 B | H₂SO₄ | Fenolftaleína (P) / pH 4,5 (T) | 1 | 100,09 | mg CaCO₃/L |
| Cloretos (Mohr) | SM 4500-Cl⁻ B | AgNO₃ | K₂CrO₄ | 1 | 35,45 | mg Cl⁻/L |
| Acidez | SM 2310 B | NaOH | Fenolftaleína | ½ | 100,09 | mg CaCO₃/L |
| Oxigênio dissolvido (Winkler) | SM 4500-O C | Na₂S₂O₃ | Amido | ¼ | 32,00 | mg O₂/L |
| DQO (refluxo, titulométrico) | SM 5220 C | Sulfato ferroso amoniacal | Ferroína | ¼ | 32,00 | mg O₂/L (retrotitulação) |

- [x] **RF-07.4b Catálogo v1 — espectrofotométricas** (usam a curva de calibração do RF-04; resultado `c = (A − b)/a · FD`):

| Análise | Referência | Reagente / princípio | λ (nm) | Unidade |
|---------|-----------|----------------------|--------|---------|
| Sulfato | SM 4500-SO₄²⁻ E | BaCl₂, turbidimétrico | 420 | mg SO₄²⁻/L |
| Ferro total | SM 3500-Fe B | 1,10-fenantrolina | 510 | mg Fe/L |
| Fosfato | SM 4500-P E | Ácido ascórbico (azul de molibdênio) | 880 | mg P/L |
| Nitrito | SM 4500-NO₂⁻ B | Sulfanilamida + NED (colorimétrico) | 543 | mg N-NO₂⁻/L |

- [x] **RF-07.5 Especiação da alcalinidade** (SM 2320 B, a partir de P e T em mg CaCO₃/L):

| Condição | OH⁻ | CO₃²⁻ | HCO₃⁻ |
|----------|-----|-------|-------|
| P = 0 | 0 | 0 | T |
| P < T/2 | 0 | 2P | T − 2P |
| P = T/2 | 0 | 2P | 0 |
| P > T/2 | 2P − T | 2(T − P) | 0 |
| P = T | T | 0 | 0 |

- [x] **RF-07.6** Usa as mesmas réplicas, branco, fator `f` (pode vir da Padronização, RF-02.3), estatística (RF-03) e diluição (RF-05.2) das outras abas.
- **Validações:** as mesmas de RF-01; V_corr ≤ 0 no modo `retrotitulação` → erro "volume da amostra maior que o do branco"; dureza cálcica > total → erro; P > T → erro.

### RF-08 Cálculos básicos de soluções (`modules/conversions.py`)
Cálculos do dia a dia de preparo de soluções. Em cada fórmula o usuário **preenche todas as variáveis menos uma**, e o app resolve a que ficou em branco (ex.: "quanto pesar?", "qual o volume?").
Unidades fixas de bancada: massa em g, volume em mL, massa molar em g/mol.

- [x] **RF-08.1 Concentração comum:** `C [g/L] = m [g] / V [L]`.
- [x] **RF-08.2 Concentração molar (molaridade):** `C [mol/L] = m / (M · V [L])`. Uso principal: quanto pesar, `m = C · M · V`.
- [x] **RF-08.3 Molalidade:** `b [mol/kg] = m_soluto / (M · m_solvente [kg])`.
- [x] **RF-08.4 Porcentagens:** `% m/m = m_soluto / m_solução · 100`; `% m/v = m_soluto [g] / V_solução [mL] · 100`; `% v/v = V_soluto / V_solução · 100`.
- [x] **RF-08.5 Densidade:** `d [g/mL] = m / V`.
- [x] **RF-08.6 Reagente comercial concentrado** (ex.: HCl 37 %): `C [mol/L] = d [g/mL] · 1000 · (título % / 100) / M`; opcionalmente, o volume do reagente para preparar `V_final` de `C_final`: `V = C_final · V_final / C`.
- [x] **RF-08.7 Mistura de soluções do mesmo soluto:** `C_final = Σ(Cᵢ · Vᵢ) / ΣVᵢ`.
- [x] **RF-08.8 Conversão de frações:** % ↔ ‰ ↔ ppm ↔ ppb (1 % = 10⁴ ppm = 10⁷ ppb).
- [x] **RF-08.9** A diluição (RF-05) passa para a mesma aba, que é renomeada para **Soluções**.
- **Validações:** exatamente um campo em branco; valores ≤ 0 → erro; % m/m e % v/v: soluto > solução → erro; título do reagente > 100 % → erro; mistura com listas de tamanhos diferentes → erro.

### Registro de decisões (revisão da analista química)

`A` = decidido pela analista · `D` = decisão técnica tomada pelo dev onde a analista não tinha a resposta (revisável).

| # | Tema | Decisão | Origem |
|---|---|---|---|
| 1 | Tolerância entre réplicas | CV máximo **configurável por análise na tela**, padrão 5 %. Acima disso, aviso "repetir a análise". O laboratório ajusta ao seu POP | D |
| 2 | Umidade | Estufa 105 °C até massa constante; pré-secagem (ASA × ASE) disponível como opção | A + D |
| 3 | Cinzas | Mufla 550 °C / 5 h (registrado no laudo) | A |
| 4 | Kjeldahl | Ácido bórico + titulação direta; catalisador CuSO₄/K₂SO₄ registrado no laudo; tabela de fatores de Jones | A |
| 5 | Extrato etéreo | Soxhlet, éter de petróleo (o modo saquinho sai do escopo) | A |
| 6 | FDA | Saquinho filtrante (Ankom) com correção do branco; sem correção para cinzas (modo convencional sai do escopo) | A + D |
| 7 | FDN | **Não há análise de FDN.** O CNF recebe o valor de FDN (ou FDNcp) **digitado** na ficha da amostra, vindo de outra fonte. Assim o CNF continua possível sem criar a análise | A + D |
| 8 | Variante do CNF | Fórmula padrão `100 − (PB + EE + MM + FDN)`; o campo aceita FDN ou FDNcp (mesma fórmula). Variante com ureia fica fora (YAGNI) | D |
| 9 | Acidez | Saída em % (m/m ou m/v) **e** em concentração (g/L, para amostras líquidas); °Dornic incluído; índice de acidez e acidez em solução normal mantidos | A |
| 10 | Ferramenta × ensino | **Ambos:** modo didático (explicação + exemplo carregável) e página de exercícios com gabarito | A |
| 11 | Ajuste de pH | Incluído: modo tampão (fração da base pelo pKa) e modo ácido/base forte (balanço de H⁺/OH⁻ com diluição) | A |
| 12 | Arredondamento | **ABNT NBR 5891** em toda a exibição de resultados, mais uma calculadora de algarismos significativos | A |
| 13 | Cartas de controle | Média e s alvo calculados das **20 primeiras medições** (configurável; com menos de 20, usa todas com aviso). Série importada/exportada em CSV enquanto não há histórico persistente | A + D |
| 14 | Validação de métodos (RDC 166) | Módulo completo **adiado**; entra o diagnóstico da curva (IC de a e b, teste do intercepto, falta de ajuste, homocedasticidade por Cochran, s_x0) | D |
| 15 | Regressão múltipla | Fora do escopo | A |
| 16 | Regressão ponderada e Monte Carlo | Adiados (P3, sem demanda concreta) | D |
| 17 | ANOVA de dois fatores | Incluída (delineamento balanceado, com repetição) | A |
| 18 | Tampão bicarbonato | Corrigido para o par **HCO₃⁻/CO₃²⁻ (pKa 10,33)**: o par do pKa 6,35 (CO₂/HCO₃⁻) não tem forma ácida pesável. Citrato sai do catálogo (triprótico, Henderson–Hasselbalch simples não se aplica) e fica via "Outro" | D |
| 19 | Navegação | `st.navigation` com seções (testado no stlite: Streamlit 1.45.1). Campos e tabelas preservados ao trocar de página | D |

### RF-09 Bromatologia (`modules/bromatology.py`) — % (g/100 g)
- [x] **RF-09.0 Base comum:** réplicas com média, s, CV e Grubbs (RF-03); aviso quando CV > tolerância (decisão 1); conversão para base seca `X(%MS) = X(%MN) / MS × 100`.
- [x] **RF-09.0.1 Ficha da amostra:** os resultados de cada análise ficam na sessão (MN e MS); MO e CNF/CT calculados quando os dados existem; exportação CSV/PDF da ficha.
- [x] **RF-09.1 Umidade/MS:** `U = (m_tara + m_amostra − m_tara+seca) / m_amostra × 100`; `MS = 100 − U`; pré-secagem `MS = ASA × ASE / 100`.
- [x] **RF-09.2 Cinzas/MO:** `MM = (m_cad+cinzas − m_cad) / m_amostra × 100`; `MO(%MS) = 100 − MM(%MS)`.
- [x] **RF-09.3 Proteína bruta (Kjeldahl):** `N = (V − V_branco) × C × f × r × 14,007 / (m × 1000) × 100`; `PB = N × F`.
- [x] **RF-09.4 Extrato etéreo (Soxhlet):** `EE = (m_balão+gordura − m_balão) / m_amostra × 100`.
- [x] **RF-09.5 FDA (Ankom):** `FDA = (W3 − W1 × C1) / W2 × 100`; `C1 = branco final / branco inicial`.
- [x] **RF-09.6 CNF:** `CNF = 100 − (PB + EE + MM + FDN)`; `CT = 100 − (PB + EE + MM)`, tudo em %MS.
- [x] **RF-09.7 Acidez:** `% = V × C × f × M / (k × m × 10)` (m em g ou mL); `g/L = V × C × f × M / (k × V_amostra)`; `°D = g/L de ácido lático × 10`; `IA = V × C × f × 56,11 / m`; `mL N/100 g = V × f × 100 / (m × c)`.
- **Validações:** massas ≤ 0; ganho de massa na umidade; resíduo > amostra; resultado fora de 0–100 %; branco ≥ volume; CNF < 0 → erro; PB + EE + MM + FDN > 100 → erro.

### RF-10 Fundamentos (`modules/conversions.py`)
- [x] **RF-10.1** Conversor SI: massa (kg, g, mg, µg), volume (L, mL, µL), temperatura (°C, K, °F), pressão (atm, kPa, bar, mmHg).
- [x] **RF-10.2** Regra de três direta e inversa (resolvedor "preencha todos menos um").
- [x] **RF-10.3** Algarismos significativos: contar e arredondar a n significativos pela NBR 5891.

### RF-11 Cálculos intermediários (`modules/stoichiometry.py`)
- [x] **RF-11.1 Estequiometria:** reagente limitante, massas teóricas dos produtos e sobra dos reagentes em excesso. Reagente sem massa informada = em excesso.
- [x] **RF-11.2 Rendimento:** `% = massa real / massa teórica × 100`.
- [x] **RF-11.3 Tampão:** Henderson–Hasselbalch → concentrações e massas das formas ácida e básica; aviso se |pH − pKa| > 1.
- [x] **RF-11.4 Ajuste de pH:** tampão: `n_base = C_T × V × (α(pH_b) − α(pH_a))`, `α = 1 / (1 + 10^(pKa − pH))`; forte: `V_t = V × (E_a − E_b) / (C_t + E_b)` com `E = [H⁺] − [OH⁻]` (base) e o simétrico para ácido.
- [x] **RF-11.5 Erros e exatidão:** erro absoluto e relativo; recuperação `(C_fort − C_não fort) / C_adic × 100`.
- [x] **RF-11.6 NBR 5891:** `utils/formatting.fmt` arredonda pela regra do par sobre a representação decimal.

### RF-12 Estatística descritiva (`modules/stats.py`)
- [x] **RF-12.1** Mediana, moda, média ponderada, variância, amplitude, quartis, IQR, erro padrão da média.
- [x] **RF-12.2** Q de Dixon (n = 3–10, 95 %) e regra do boxplot (1,5 × IQR), além do Grubbs.
- [x] **RF-12.3** Normal: probabilidade entre limites e escore z; t crítico; Shapiro–Wilk; histograma com curva normal; boxplot.

### RF-13 Inferencial e controle (`modules/inferential.py`, `modules/control.py`)
- [x] **RF-13.1** Teste t: uma amostra × referência; duas amostras (F decide entre agrupado e Welch); pareado. Conclusão em português.
- [x] **RF-13.2** Teste F de variâncias (bilateral).
- [x] **RF-13.3** ANOVA de um fator com Tukey; ANOVA de dois fatores balanceada com repetição.
- [x] **RF-13.4** Cartas I-MR (Shewhart) e Levey-Jennings com regras de Westgard (1-2s alerta; 1-3s, 2-2s, R-4s, 4-1s, 10x rejeição); alvo das N primeiras medições; CSV de entrada e saída.

### RF-14 Regressão e incerteza (`modules/spectro.py`, `modules/uncertainty.py`)
- [x] **RF-14.1** Diagnóstico da curva: IC de a e b, teste de b = 0, falta de ajuste (com réplicas por nível), homocedasticidade por Cochran (RDC 166), `s_x0`.
- [x] **RF-14.2** Orçamento de incerteza (GUM): tipo A `s/√n`, tipo B (padrão, certificado k, retangular, triangular); combinação relativa para modelos de produto/quociente; ν_eff (Welch–Satterthwaite); U = k·u_c (k = 2 ou t(ν_eff)); contribuição de cada fonte; exemplo pronto da padronização.

### RF-15 Decisão multicritério (`modules/decision.py`)
- [x] **RF-15.1 AHP:** pesos pelo autovetor principal, λmax, IC, RC (IA de Saaty), aviso se RC > 0,10 indicando o par mais incoerente.
- [x] **RF-15.2 TOPSIS:** normalização vetorial, pesos (do AHP ou digitados), benefício/custo, D⁺, D⁻, proximidade e ranking; exportação PDF.

### RF-16 Modo didático e exercícios (`ui/`)
- [x] **RF-16.1** Chave "Modo didático" na barra lateral: cada tela nova mostra "📘 Entenda o cálculo" (fórmula explicada) e um botão "Carregar exemplo".
- [x] **RF-16.2** Página de exercícios: banco de exercícios por módulo; o usuário responde e o app corrige com tolerância, mostrando a resolução.

## 4. Requisitos não funcionais

- **RNF-01 Formatação:** resultados com casas decimais configuráveis (padrão 4); notação científica quando |x| < 0,01 ou ≥ 1e4. Exibição com vírgula decimal (pt-BR).
- **RNF-02 Entrada:** campos de texto/colagem aceitam vírgula ou ponto decimal.
- **RNF-03 Erros:** módulos de cálculo lançam `ValueError` com mensagem em português; a UI captura e mostra com `st.error`. Avisos (não bloqueantes) retornados junto do resultado e mostrados com `st.warning`.
- **RNF-04 Separação:** `modules/` não importa Streamlit (testável sem UI).
- **RNF-05 Idioma:** toda a interface em português do Brasil.
- **RNF-06 Comentários:** cada função de cálculo documenta a fórmula aplicada e as unidades.

## 5. Interface

Sidebar: navegação + rastreabilidade (RF-06.3) + casas decimais (RNF-01).
Navegação lateral por seções (`st.navigation`):
- **Rotina:** Análises (água) · Bromatologia · Titulação · Padronização · Espectrofotometria (com diagnóstico da curva)
- **Soluções e cálculos:** Soluções · Estequiometria e pH · Conversões e erros
- **Estatística:** Descritiva · Distribuições · Testes de hipótese · ANOVA · Cartas de controle · Incerteza
- **Gestão:** AHP / TOPSIS
- **Ajuda:** Como usar · Exercícios
Na aba Análises: selectbox da análise → card com referência, titulante e indicador → entradas → etapas → resultado.
Cada aba: entradas (parâmetros + `st.data_editor` para réplicas) → bloco "Etapas do cálculo" → resultado final destacado (`st.metric`) → botões de exportação.

## 6. Critérios de aceite (valores de referência)

Viram testes em `tests/`. Tolerância relativa 1e-3 salvo indicação.

| ID | Entrada | Esperado |
|----|---------|----------|
| CA-01 | Réplicas 10,10 · 10,20 · 10,15 mL; branco 0,05 mL | média 10,15 mL; V_corr 10,10 mL |
| CA-02 | CA-01 + C_tit 0,1000 mol/L, f 1,000, r 1, alíquota 25,00 mL | C_analito 0,04040 mol/L |
| CA-03 | CA-01 + C_tit 0,1000, f 1,000, r 1, M 60,05 g/mol, m_amostra 2,000 g | 3,03 % m/m |
| CA-04 | Biftalato 0,5105 g, V_gasto 25,00 mL, C_nominal 0,1 mol/L, r 1 | C_real 0,09999 mol/L; f 0,9999 |
| CA-05 | 10,10 · 10,20 · 10,15 | s 0,0500; CV 0,493 %; IC95 10,15 ± 0,1242 |
| CA-06 | 10,10 · 10,12 · 10,15 · 10,11 · 10,90 (α 0,05) | G ≈ 1,786 > G_crít ≈ 1,715 → 10,90 é outlier |
| CA-07 | Padrões c 0,1,2,3,4 mg/L; A 0,002 · 0,101 · 0,199 · 0,302 · 0,398 | a 0,0993; b 0,0018; R² > 0,9999 |
| CA-08 | CA-07 + amostra A 0,250 | c ≈ 2,50 mg/L |
| CA-09 | CA-07 | LOD ≈ 0,055 mg/L; LOQ ≈ 0,17 mg/L |
| CA-10 | Branco 10,20 com média 10,15 | `ValueError` (V_corr ≤ 0) |
| CA-11 | Réplicas vazias / volume negativo / a = 0 | `ValueError` com mensagem em português |
| CA-12 | C₁ 1,0 mol/L, C₂ 0,1 mol/L, V₂ 100 mL, V₁ em branco | V₁ 10,0 mL |
| CA-13 | Dureza total: EDTA 0,0100 mol/L, f 1, V 5,00 mL, branco 0, amostra 50,00 mL | 100,09 mg CaCO₃/L |
| CA-14 | Dureza total 100,09; cálcica 60,00 | magnesiana 40,09 mg CaCO₃/L |
| CA-15 | Cloretos: AgNO₃ 0,0141 mol/L, V 4,20 mL, branco 0,20 mL, amostra 100,0 mL | ≈ 20,0 mg Cl⁻/L |
| CA-16 | Alcalinidade T: H₂SO₄ 0,0100 mol/L, V 10,00 mL, amostra 100,0 mL | 100,09 mg CaCO₃/L |
| CA-17 | Especiação P 3, T 10 (mg CaCO₃/L) | OH⁻ 0; CO₃²⁻ 6; HCO₃⁻ 4 |
| CA-18 | DQO: FAS 0,2500 mol/L, branco 10,00 mL, amostra 7,50 mL, V_amostra 20,00 mL | 250 mg O₂/L |
| CA-19 | DQO com amostra 10,50 mL e branco 10,00 mL | `ValueError` |
| CA-20 | Ferro: curva do CA-07, amostra A 0,250, FD 2 | ≈ 5,00 mg Fe/L |
| CA-21 | Concentração comum: m 5,0 g, V 250 mL | 20,0 g/L |
| CA-22 | Quanto pesar: NaCl 0,10 mol/L, 500 mL, M 58,44 | m 2,922 g |
| CA-23 | Molalidade: 5,844 g NaCl (M 58,44) em 500 g de água | 0,200 mol/kg |
| CA-24 | % m/v 0,9 %, V 500 mL, massa em branco | 4,5 g |
| CA-25 | HCl 37 %, d 1,19 g/mL, M 36,46; preparar 1000 mL de 0,1 mol/L | C 12,08 mol/L; V 8,28 mL |
| CA-26 | Mistura: 100 mL de 0,1 mol/L + 200 mL de 0,4 mol/L | 0,300 mol/L |
| CA-27 | 0,5 % → ppm | 5000 ppm |
| CA-28 | Densidade 1,84 g/mL, V 10 mL, massa em branco | 18,4 g |
| CA-29 | % m/m com soluto 30 g e solução 20 g; dois campos em branco | `ValueError` |
| CA-30 | Umidade: tara 20,0000 g; amostra 2,0000 g; tara + seca 21,8200 g | U 9,00 %; MS 91,00 % |
| CA-31 | Pré-secagem: ASA 30,0 %; ASE 90,0 % | MS 27,0 % |
| CA-32 | Cinzas: cadinho 20,0000; amostra 2,0000; cadinho + cinzas 20,1200 g; MS 91,00 % | MM 6,00 % MN; 6,59 % MS |
| CA-33 | Kjeldahl: m 0,2000 g; V 10,00; branco 0,10 mL; HCl 0,1000 mol/L; F 6,25 | N 6,934 %; PB 43,33 % |
| CA-34 | EE: balão 100,0000; amostra 2,0000; balão + gordura 100,0600 g | 3,00 % |
| CA-35 | FDA: W1 0,5000; W2 0,5000; W3 0,6500 g; branco 0,5000 → 0,5010 g | 29,80 % |
| CA-36 | CNF: PB 20; EE 3; MM 6; FDN 40 | CNF 31,0 %; CT 71,0 % |
| CA-37 | Acidez cítrica: NaOH 0,1000; V 10,00 mL; m 10,00 g | 0,640 % |
| CA-38 | Óleo: 0,1000 mol/L; V 2,00 mL; m 5,00 g | 1,13 % oleico; IA 2,24 mg KOH/g |
| CA-39 | 1,000 g Na₂SO₄ (142,04) → BaSO₄ (233,39); obtido 1,5800 g | Teórico 1,6431 g; 96,16 % |
| CA-40 | Tampão acetato pH 5,00; pKa 4,76; 0,1 mol/L; 1 L | A⁻ 0,06347; HA 0,03653 mol/L; NaAc·3H₂O 8,638 g; HAc 2,193 g |
| CA-41 | Recuperação: 2,0 → 6,9 com 5,0 adicionado | 98,0 % |
| CA-42 | t uma amostra 10,10 · 10,20 · 10,15 × 10,00 | t 5,196; gl 2; p 0,035 → significativa |
| CA-43 | F: A = 10,10 · 10,20 · 10,15; B = 10,30 · 10,35 · 10,25 · 10,40 | F 1,667; p 0,79 → iguais |
| CA-44 | t duas amostras (A, B), agrupado | t −3,873; gl 5; p 0,0117 |
| CA-45 | t pareado 10,1 · 10,3 · 10,2 × 10,2 · 10,4 · 10,2 | t −2,000; gl 2; p 0,184 |
| CA-46 | ANOVA 10,1 · 10,2 · 10,15 / 10,3 · 10,35 · 10,25 / 10,0 · 10,05 · 10,1 | F 19,00; p 0,0025; Tukey: só G1×G2 (p 0,024) e G2×G3 (p 0,002) diferem |
| CA-47 | Levey-Jennings alvo 100, s 2: 100 · 101 · 99 · 104,5 · 106,5 | 104,5 → 1-2s; 106,5 → 1-3s e 2-2s |
| CA-48 | Incerteza da padronização: m 0,5105 (u 0,0001); V 25,00 (u 0,02) | C 0,09999; u_c 8,24×10⁻⁵; U 1,65×10⁻⁴ mol/L |
| CA-49 | AHP [[1, 3, 5], [1/3, 1, 3], [1/5, 1/3, 1]] | 0,637 · 0,258 · 0,105; λmax 3,039; RC 0,033 |
| CA-50 | TOPSIS (CA-49; A 250/98,0/2,0; B 180/95,0/3,0; C 300/99,5/1,5) | 0,430 · 0,813 · 0,187 → B > A > C |
| CA-51 | Ajuste de pH, tampão acetato 0,1 mol/L, 1 L, 4,76 → 5,00, NaOH 1 mol/L | 13,47 mL |
| CA-52 | Ajuste de pH, ácido forte 100 mL pH 2 → 3, NaOH 0,1 mol/L | 8,911 mL |
| CA-53 | °Dornic: 1,60 mL NaOH 0,1111 mol/L; 10 mL de leite | 1,60 g/L ácido lático; 16,0 °D |
| CA-54 | Dixon: 10,10 · 10,12 · 10,15 · 10,11 · 10,90 | Q 0,9375 > 0,710 → outlier |
| CA-55 | ANOVA 2 fatores 2×2, n = 2: A1B1 10, 11; A1B2 12, 13; A2B1 14, 15; A2B2 20, 21 | F_A 144; F_B 64; F_AB 16 |
| CA-56 | s_x0 da curva do CA-07, amostra A 0,250 (1 leitura) | 0,0185 mg/L; teste b = 0: p 0,257 (não significativo) |
| CA-57 | NBR 5891 com 2 casas: 2,675 → 2,68; 2,665 → 2,66; 2,6651 → 2,67 | — |

## 7. Plano de entrega

1. **Fase 1 — núcleo:** estrutura de pastas, `stats.py`, `titration.py` (RF-01, RF-02), testes CA-01 a CA-06, CA-10, CA-11.
2. **Fase 2 — espectro e diluição:** `spectro.py`, `conversions.py`, testes CA-07 a CA-09, CA-12.
3. **Fase 3 — análises pré-cadastradas:** `methods.py` (RF-07), testes CA-13 a CA-20.
4. **Fase 4 — UI:** `app.py` com as 6 abas, formatação, avisos.
5. **Fase 5 — relatórios:** CSV e PDF com rastreabilidade.
6. **Fase 6 — soluções:** RF-08 em `conversions.py`, aba Diluição vira Soluções, testes CA-21 a CA-29.
7. **Fase 7 — núcleo v2:** módulos RF-09 a RF-15, testes CA-30 a CA-57.
8. **Fase 8 — UI v2:** navegação por seções, persistência dos campos entre páginas, telas novas, modo didático e exercícios (RF-16), guia atualizado.
