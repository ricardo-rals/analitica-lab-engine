## Visão geral

O **Analytica Lab Engine** faz os cálculos de rotina do laboratório analítico. Você digita só o que mediu na bancada (volumes gastos, branco, massas, absorbâncias) e o app mostra:

1. **O resultado final**, em destaque e com unidade.
2. **As etapas do cálculo** (volume médio, branco descontado, volume corrigido, mols...), para conferir ou transcrever no caderno.
3. **A estatística das réplicas**: desvio padrão, CV, intervalo de confiança e teste de outlier.
4. **Avisos** quando algo foge do esperado (extrapolação da curva, fator fora da faixa, valor abaixo do LOQ...).

As páginas ficam no **menu lateral**, em cinco seções: **Rotina** (análises de água, bromatologia, titulação, padronização, espectrofotometria), **Soluções e cálculos**, **Estatística** (descritiva, distribuições, testes de hipótese, ANOVA, cartas de controle, incerteza), **Gestão** (AHP e TOPSIS) e **Ajuda** (este guia e exercícios).

Tudo roda no seu navegador: os dados digitados **não são enviados a nenhum servidor**. Por isso, recarregar a página apaga o que foi digitado; exporte o relatório antes de sair.

## Primeiros passos

1. Preencha a **barra lateral** com o ID da amostra, o analista e o lote do reagente. Esses dados vão no cabeçalho dos relatórios exportados.
2. Escolha a página no menu lateral. Para as análises de rotina de água (dureza, cloretos, DQO...), use **🧪 Análises de água**; para alimentos e rações, **🌾 Bromatologia**.
3. Digite as réplicas na tabela e confira os parâmetros já preenchidos.
4. O resultado aparece à direita na hora, sem botão de "calcular".
5. Exporte em **CSV** ou **PDF** pelos botões abaixo do resultado.

Algumas páginas vêm com **valores de exemplo**. Substitua pelos seus dados.

**Trocar de página não apaga nada:** os campos e tabelas voltam como você deixou. Só **recarregar** a página (F5) ou fechá-la apaga os dados.

**📘 Modo didático** (barra lateral): cada página passa a mostrar a explicação da fórmula e um botão **Carregar exemplo**, que preenche a tela com um caso resolvido. Bom para treinar e para conferir o app.

## Como digitar números

- **Vírgula ou ponto** como separador decimal: `10,15` e `10.15` dão o mesmo valor. `1.234,5` é lido como mil duzentos e trinta e quatro vírgula cinco.
- **Tabelas de réplicas**: clique numa célula e digite. Para incluir mais réplicas, use a linha vazia no fim da tabela (ou o **+**). Para apagar, selecione a linha pela caixa à esquerda e pressione **Delete**.
- Células vazias são ignoradas: não precisa preencher todas as linhas.
- Número inválido (ex.: `1o,2`) mostra um erro vermelho logo abaixo do campo.

## 🧪 Análises de água

Escolha a análise na lista. O quadro azul mostra a **norma de referência** (Standard Methods), o **titulante**, o **indicador** e a **unidade** do resultado. A concentração do titulante e o volume de amostra já vêm com os valores usuais do método; ajuste se o seu procedimento for diferente.

| Análise | Tipo | Resultado em |
|---|---|---|
| Dureza total / cálcica | Titulação com EDTA | mg CaCO₃/L |
| Alcalinidade P e T | Titulação com H₂SO₄ | mg CaCO₃/L |
| Cloretos (Mohr) | Titulação com AgNO₃ | mg Cl⁻/L |
| Acidez | Titulação com NaOH | mg CaCO₃/L |
| Oxigênio dissolvido (Winkler) | Titulação com Na₂S₂O₃ | mg O₂/L |
| DQO (refluxo) | Retrotitulação com FAS | mg O₂/L |
| Sulfato, ferro, fosfato, nitrito | Espectrofotometria (curva) | mg/L da espécie |

**Fórmula das titulações:**
`resultado (mg/L) = V corrigido (mL) × C titulante × f × r × M × 1000 / V amostra (mL) × FD`

**Resultados derivados:**
- **Dureza magnesiana**: calcule a dureza total e a cálcica, nessa ordem ou na inversa. Ao abrir qualquer uma das duas, aparece `magnesiana = total − cálcica`.
- **Especiação da alcalinidade** (OH⁻, CO₃²⁻, HCO₃⁻): calcule P e T. Se a amostra não ficou rosa com fenolftaleína, marque **"Não houve viragem com fenolftaleína (P = 0)"**.
- Esses valores usam o último resultado de cada análise **nesta sessão**.

**DQO é diferente:** é uma retrotitulação, então o **branco gasta mais** titulante que a amostra e o app calcula `branco − amostra`. Se a amostra gastar mais que o branco, o app recusa o cálculo: a amostra consumiu todo o dicromato. Dilua e repita.

**Para colocar uma análise nova no catálogo**, peça ao responsável pelo sistema. É uma entrada em `modules/methods.py`, sem código novo.

## 🌾 Bromatologia

Composição de alimentos e rações em **% (g/100 g)**. Cada análise aceita **réplicas** (uma linha da tabela por réplica) e mostra o resultado de cada uma, a média, o desvio, o CV e o teste de Grubbs.

| Análise | Método | Fórmula |
|---|---|---|
| Umidade e matéria seca | Estufa 105 °C até massa constante | `U = (tara + amostra − tara+seca) / amostra × 100`; `MS = 100 − U` |
| Cinzas e matéria orgânica | Mufla 550 °C / 5 h | `MM = (cadinho+cinzas − cadinho) / amostra × 100`; `MO (MS) = 100 − MM (MS)` |
| Proteína bruta | Kjeldahl, ácido bórico, catalisador CuSO₄/K₂SO₄ | `N = (V − branco) × C × f × r × 14,007 / (m × 1000) × 100`; `PB = N × F` |
| Extrato etéreo | Soxhlet, éter de petróleo | `EE = (balão+gordura − balão) / amostra × 100` |
| FDA | Saquinho filtrante (Ankom) | `FDA = (W3 − W1 × C1) / W2 × 100`, `C1 = branco final / branco inicial` |
| Acidez | Titulação com NaOH | `% = V × C × f × M / (k × m × 10)`; g/L; °Dornic; índice de acidez |

- **Tolerância entre réplicas:** acima do CV máximo (padrão 5 %, ajustável conforme o POP), o app pede para repetir a análise.
- **Base seca:** calcule primeiro a **umidade**. As outras análises da mesma amostra passam a mostrar o resultado também na matéria seca (`X (MS) = X (MN) / MS × 100`). Sem umidade, dá para digitar a MS.
- **Pré-secagem** (silagem, forragem verde): marque "Amostra pré-seca" e informe a ASA; o app calcula `MS = ASA × ASE / 100`.
- **Kjeldahl:** escolha o titulante (HCl: r = 1; H₂SO₄: r = 2) e a matriz, que define o fator N → proteína (6,25 geral; 6,38 leite; 5,70 farinha de trigo...).
- **Acidez:** escolha o ácido de expressão (cítrico, acético, lático, málico, tartárico, oleico) e se a amostra foi medida em g ou mL. Em mL, sai também a concentração em g/L; com ácido lático, a acidez **Dornic** (°D = g/L × 10). Para óleos, o ácido oleico dá o % de ácidos graxos livres e o **índice de acidez** (mg KOH/g).
- **📋 Ficha da amostra:** junta os resultados da amostra atual (ID na barra lateral) em matéria natural e seca, calcula a **matéria orgânica** e, informando a **FDN** (o app não faz essa análise; use o valor de outra fonte), o **CNF** = 100 − (PB + EE + MM + FDN) e os carboidratos totais. A ficha também é exportável.

## ⚗️ Titulação livre

Para titulações fora do catálogo. Escolha o que calcular:

- **Concentração do analito (mol/L)**: informe o volume da alíquota titulada.
- **Teor na amostra (% m/m)**: informe a massa da amostra e a massa molar do analito.

A **razão estequiométrica r** é `mol de analito ÷ mol de titulante` na reação. Exemplos: HCl + NaOH → r = 1. H₂SO₄ titulado com NaOH → r = 0,5 (um ácido consome dois NaOH).

O campo **nº de equivalentes** é opcional e só serve para expressar o resultado em normalidade (N). A IUPAC desaconselha essa unidade; prefira mol/L.

## 🎯 Padronização

Calcula a concentração real do titulante e o **fator de correção f** a partir de um padrão primário pesado.

1. Escolha o padrão (biftalato de potássio, carbonato de sódio, ácido oxálico) ou **Outro padrão** e informe a massa molar.
2. Informe a massa pesada e os volumes gastos.
3. Confira a razão **r = mol de titulante ÷ mol de padrão**. Para Na₂CO₃ com HCl já vem r = 2.
4. Clique em **"Usar este fator nas outras páginas"** para preencher o f automaticamente em Análises de água, Titulação e Bromatologia (Kjeldahl e acidez).

Fator fora de 0,90–1,10 gera um aviso: provavelmente há erro de preparo da solução ou de pesagem.

## 🌈 Espectrofotometria

**Curva de calibração** (o mais comum):

1. Digite os padrões: concentração e absorbância.
2. Digite a(s) leitura(s) da amostra. Com várias leituras, o app usa a média.
3. Informe o fator de diluição, se a amostra foi diluída antes da leitura.

O app mostra a equação `A = a·c + b`, o **R²**, o **LOD** (3,3·s/a) e o **LOQ** (10·s/a), o gráfico da curva com a amostra marcada (◆) e o **gráfico de resíduos**. Resíduos espalhados ao acaso em torno de zero indicam boa linearidade; uma curvatura nos resíduos indica que a faixa linear foi excedida.

O resultado vem com **± s_x0**, o desvio padrão da concentração lida na curva. Abra **🔬 Diagnóstico da curva** para ver:
- **IC 95 % da inclinação e do intercepto** e o **teste b = 0**: intercepto significativo indica possível interferência ou branco mal descontado;
- **falta de ajuste** (precisa de réplicas em algum nível de concentração): significativo = o modelo linear não serve;
- **homocedasticidade pelo teste de Cochran** (mesmo nº de réplicas em ≥ 2 níveis), como pede a RDC 166/2017.

Avisos importantes:
- **R² < 0,995**: linearidade questionável. Reveja os padrões.
- **Fora da faixa dos padrões**: o resultado foi extrapolado. Dilua a amostra ou amplie a curva.
- **Abaixo do LOD / LOQ**: reporte como "< LOD" ou "< LOQ", não como valor numérico.

**Beer-Lambert direto**: quando a absortividade molar (ε) é conhecida, `c = A / (ε · l)`, com o resultado em mol/L.

## 📊 Estatística descritiva

Cole ou digite qualquer série de valores (resultados, volumes, leituras). O app calcula:

- **Média, mediana e moda**; **média ponderada**, se a coluna de pesos for preenchida.
- **Desvio padrão (s), variância, CV/RSD %, amplitude, quartis, IQR e erro padrão da média.**
- **Intervalo de confiança** com t de Student (n − 1 graus de liberdade), a 90, 95 ou 99 %, no formato `média ± IC`.
- **Valores discrepantes** por três critérios: **Grubbs** (α ajustável), **Q de Dixon** (3 a 10 valores, 95 %) e **boxplot** (fora de Q1 − 1,5·IQR a Q3 + 1,5·IQR).
- **Histograma e boxplot.**

Os testes **só indicam** o valor suspeito: o app nunca remove réplica sozinho. Se decidir descartar, apague a linha e registre o motivo.

## 🔔 Distribuições

- **Probabilidade na normal:** chance de um valor cair entre dois limites, dada a média e o desvio (com gráfico da área).
- **Escore z:** `z = (x − média) / s`. Em ensaios de proficiência: |z| ≤ 2 satisfatório, 2 a 3 questionável, ≥ 3 insatisfatório.
- **t crítico:** valor da t de Student para os graus de liberdade e a confiança escolhidos.
- **Teste de normalidade (Shapiro–Wilk):** p ≥ α → os dados podem ser tratados como normais. Grubbs, testes t e ANOVA supõem normalidade.

## ⚖️ Testes de hipótese

Escolha o teste e o nível de significância α (padrão 0,05 = 95 % de confiança). A conclusão aparece em português: **verde** = sem diferença significativa; **amarelo** = diferença significativa.

| Teste | Quando usar |
|---|---|
| t: uma amostra × referência | Exatidão: a média difere do valor certificado (MRC)? Mostra o viés |
| t: duas amostras independentes | Dois métodos, analistas ou lotes. O **teste F** decide antes entre t agrupado e t de Welch |
| t: pareado | As **mesmas amostras** medidas de dois modos (as séries precisam ter o mesmo tamanho) |
| F | Comparar precisões (variâncias) de dois métodos |

## 📐 ANOVA

- **Um fator:** compara 3 ou mais grupos (analistas, equipamentos, dias). Digite uma linha por medição: nome do grupo e valor. Saem a tabela ANOVA e o **teste de Tukey**, que diz quais pares de grupos diferem.
- **Dois fatores com repetição:** uma linha por medição, com o nível de cada fator. Testa os dois fatores e a **interação** (o efeito de um fator depende do nível do outro). Todas as combinações precisam do mesmo número de repetições.

## 📈 Cartas de controle

- **Levey-Jennings + Westgard:** a média e o desvio alvo vêm das **20 primeiras medições** (configurável) ou do certificado do material de controle. Limites ±2s (alerta) e ±3s (ação). O app aponta as regras violadas: **1-2s** (alerta), **1-3s**, **2-2s**, **R-4s**, **4-1s** e **10x** (rejeição da corrida).
- **Shewhart I-MR:** carta de valores individuais (limites x̄ ± 2,66·MR̄) e de amplitude móvel (LSC = 3,267·MR̄).

**Guarde a série num CSV:** o app ainda não tem histórico. Use **Importar série** (CSV com uma coluna **Valor** e, se quiser, **Data**), acrescente as novas corridas e **exporte** de novo ao final.

## 🎚️ Incerteza de medição

Orçamento de incerteza pelo **GUM**, para resultados calculados por produto/quociente (titulações, padronizações, diluições, concentrações).

1. Informe o **resultado** e a unidade.
2. Liste as **fontes**: valor da grandeza, incerteza informada e tipo. **Incerteza padrão** (já é u); **certificado** (U com k = 2); **retangular** (tolerância ±a, ex.: vidraria classe A: u = a/√3); **triangular** (u = a/√6); **Tipo A** (desvio s de n repetições: u = s/√n).
3. O app combina as incertezas relativas, `u_c / y = √Σ(uᵢ / xᵢ)²`, e expande com **k = 2** (≈ 95 %) ou com o k da t de Student para os graus de liberdade efetivos (Welch–Satterthwaite).

O gráfico de **contribuição** mostra qual fonte domina: é onde vale investir (balança melhor, bureta de classe superior, mais réplicas). Resultado no formato do laudo: `0,1000 ± 0,0002 mol/L (k = 2)`.

## 💧 Soluções

Cálculos do dia a dia de preparo de soluções. Escolha o cálculo no seletor **Cálculo**.

**Preencha tudo menos o que quer descobrir.** Na maioria das fórmulas, deixe em branco a variável desconhecida e o app a calcula. A mesma tela responde "qual a concentração?", "quanto pesar?" e "qual o volume?". Unidades fixas: massa em **g**, volume em **mL**, massa molar em **g/mol**.

| Cálculo | Fórmula | Exemplo de uso |
|---|---|---|
| Concentração molar / quanto pesar | `C = m / (M · V)` | Quanto NaCl pesar para 500 mL de 0,1 mol/L? → 2,922 g |
| Concentração comum | `C (g/L) = m / V` | 5 g em 250 mL → 20 g/L |
| Diluição | `C₁·V₁ = C₂·V₂` | Quanto da solução 1 mol/L para fazer 100 mL de 0,1 mol/L? → 10 mL |
| Reagente comercial | `C = d · 1000 · título / M` | HCl 37 % (d 1,19) → 12,08 mol/L |
| Porcentagem | `% = soluto / solução × 100` | Soro 0,9 % m/v, 500 mL → 4,5 g de NaCl |
| Molalidade | `b = m soluto / (M · kg solvente)` | 5,844 g de NaCl em 500 g de água → 0,2 mol/kg |
| Densidade | `d = m / V` | 10 mL de H₂SO₄ (d 1,84) → 18,4 g |
| Mistura de soluções | `C = Σ(Cᵢ · Vᵢ) / ΣVᵢ` | 100 mL 0,1 + 200 mL 0,4 mol/L → 0,3 mol/L |
| Fator de diluição | `FD = V final / V alíquota` | 10 mL completados a 100 mL → FD 10 |
| Conversões | mol/L ↔ g/L ↔ mg/L; % ↔ ‰ ↔ ppm ↔ ppb | 0,5 % → 5000 ppm |

Dicas:
- **Sal hidratado** (ex.: CuSO₄·5H₂O): no "quanto pesar", use a massa molar **do hidrato** (249,69 g/mol), e não a do sal anidro.
- **Reagente comercial**: escolha o ácido ou a base na lista para preencher título, densidade e massa molar com valores típicos de rótulo. **Confira o frasco**, porque os valores variam entre fabricantes e lotes. Preencha também a concentração e o volume desejados para saber **quanto pipetar**. Sempre adicione o ácido sobre a água, nunca o contrário.
- **Porcentagem**: escolha o tipo antes. Em % m/m e % v/v o soluto não pode passar da solução.
- **Mistura**: preencha uma linha por solução. Todas devem estar na mesma unidade de concentração, e o resultado sai nessa unidade.
- **mg/L ≈ ppm** só vale em solução aquosa diluída (densidade ≈ 1 g/mL).

## ⚖️ Estequiometria e pH

- **Estequiometria e rendimento:** uma linha por espécie (reagente ou produto), com coeficiente e massa molar. Informe a massa dos reagentes pesados; reagente sem massa é considerado em excesso. O app mostra o **reagente limitante**, as massas teóricas dos produtos e a sobra dos reagentes. Informe a massa obtida para ter o **rendimento (%)**.
- **Solução tampão:** escolha o par (acetato, fosfato, TRIS, amônio, carbonato) ou "Outro", o pH, a concentração e o volume. Pela equação de Henderson–Hasselbalch, o app dá as **massas de cada forma** a pesar. Aviso quando o pH está a mais de 1 unidade do pKa (tampão fraco). Ajuste fino sempre com pHmetro.
- **Ajuste de pH:** volume de ácido ou base forte para levar a solução do pH atual ao desejado. Modo **tamponado** (precisa do pKa e da concentração do tampão) ou **sem tampão** (água, ácidos e bases fortes), já considerando a diluição.

## 🔁 Conversões e erros

- **Unidades SI:** massa (kg, g, mg, µg), volume (L, mL, µL), temperatura (°C, K, °F) e pressão (atm, kPa, bar, mmHg).
- **Regra de três** direta (`A/B = C/X`) ou inversa (`A·B = C·X`): preencha três, deixe o desconhecido em branco.
- **Algarismos significativos:** conta os significativos de um número e arredonda pela **ABNT NBR 5891**. Todo o app arredonda por essa norma: quando o algarismo descartado é 5 seguido só de zeros, fica o **par** (2,665 → 2,66; 2,675 → 2,68).
- **Erros e recuperação:** erro absoluto e relativo contra um valor de referência; **recuperação** de ensaio de fortificação, com aviso fora de 80–120 %.

## 🧭 AHP e TOPSIS

Apoio à decisão para escolher **método analítico, fornecedor ou equipamento** com vários critérios ao mesmo tempo.

1. Liste os **critérios** (ex.: custo, recuperação, tempo).
2. **AHP:** compare os critérios dois a dois na escala de Saaty (1 = igual; 3, 5, 7, 9 = moderada a extremamente mais importante). O app calcula os **pesos** e a **razão de consistência**: RC > 0,10 indica julgamentos contraditórios e aponta o par a revisar.
3. Clique em **"Usar estes pesos no TOPSIS"**.
4. **TOPSIS:** preencha uma linha por alternativa e marque cada critério como **custo** (menor é melhor) ou **benefício** (maior é melhor). O ranking sai pela **proximidade da solução ideal** (C de 0 a 1), com gráfico e exportação em PDF.

## ✏️ Exercícios

Exercícios dos seis módulos (fundamentos, cálculos intermediários, estatística descritiva, inferencial e controle de qualidade, regressão e incerteza, AHP e TOPSIS) e de bromatologia. Digite a resposta: o app confere com tolerância de 1 % e mostra a **resolução passo a passo**. O gabarito é calculado pelas mesmas funções do app.

## Avisos e erros

| Cor | Significado | O que fazer |
|---|---|---|
| 🔵 Azul | Falta preencher algum campo | Complete os dados |
| 🟡 Amarelo | O cálculo foi feito, mas algo merece atenção (ou o teste deu diferença significativa) | Leia o aviso e avalie antes de liberar o resultado |
| 🟢 Verde | Teste sem diferença significativa; processo sob controle | — |
| 🔴 Vermelho | Dado impossível (volume negativo, branco maior que a amostra, inclinação zero...) | Corrija a entrada; nenhum resultado é mostrado |

## Relatórios

- **CSV**: abre direto no Excel em português (separador `;`, acentos corretos). Traz rastreabilidade, entradas, etapas e resultado.
- **PDF**: o mesmo conteúdo, pronto para imprimir ou anexar. Símbolos químicos aparecem simplificados (CaCO₃ → CaCO3) por limitação da fonte do PDF.
- O nome do arquivo leva o tipo de cálculo e a data/hora.

## Dúvidas frequentes

**A primeira abertura demora, é normal?** Sim. Na primeira vez o navegador baixa o Python e as bibliotecas científicas (cerca de 30 s). Depois fica em cache e abre bem mais rápido.

**Perdi o que tinha digitado.** Trocar de página mantém tudo, mas recarregar (F5) ou fechar a página apaga os dados, porque nada é salvo em servidor. Exporte o relatório ao terminar cada amostra; nas cartas de controle, exporte a série em CSV.

**Quantas casas decimais usar?** Ajuste em **Exibição → Casas decimais** na barra lateral. Valores muito pequenos (< 0,01) ou muito grandes (≥ 10 000) aparecem em notação científica, ex.: `1,0100e-03`. O arredondamento segue a ABNT NBR 5891.

**O resultado é confiável?** As fórmulas são conferidas por testes automáticos com valores calculados à mão, rodados a cada atualização do sistema. Mesmo assim, a liberação do resultado é responsabilidade do analista: confira as etapas exibidas.
