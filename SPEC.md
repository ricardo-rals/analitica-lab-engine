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

## 4. Requisitos não funcionais

- **RNF-01 Formatação:** resultados com casas decimais configuráveis (padrão 4); notação científica quando |x| < 0,01 ou ≥ 1e4. Exibição com vírgula decimal (pt-BR).
- **RNF-02 Entrada:** campos de texto/colagem aceitam vírgula ou ponto decimal.
- **RNF-03 Erros:** módulos de cálculo lançam `ValueError` com mensagem em português; a UI captura e mostra com `st.error`. Avisos (não bloqueantes) retornados junto do resultado e mostrados com `st.warning`.
- **RNF-04 Separação:** `modules/` não importa Streamlit (testável sem UI).
- **RNF-05 Idioma:** toda a interface em português do Brasil.
- **RNF-06 Comentários:** cada função de cálculo documenta a fórmula aplicada e as unidades.

## 5. Interface

Sidebar: navegação + rastreabilidade (RF-06.3) + casas decimais (RNF-01).
Abas: **Análises** (RF-07, primeira aba, a mais usada no dia a dia) · **Titulação** (cálculo livre) · **Padronização** · **Estatística** · **Espectrofotometria** · **Diluição**.
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

## 7. Plano de entrega

1. **Fase 1 — núcleo:** estrutura de pastas, `stats.py`, `titration.py` (RF-01, RF-02), testes CA-01 a CA-06, CA-10, CA-11.
2. **Fase 2 — espectro e diluição:** `spectro.py`, `conversions.py`, testes CA-07 a CA-09, CA-12.
3. **Fase 3 — análises pré-cadastradas:** `methods.py` (RF-07), testes CA-13 a CA-20.
4. **Fase 4 — UI:** `app.py` com as 6 abas, formatação, avisos.
5. **Fase 5 — relatórios:** CSV e PDF com rastreabilidade.
