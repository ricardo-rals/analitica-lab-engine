## Visão geral

O **Analytica Lab Engine** faz os cálculos de rotina do laboratório analítico. Você digita só o que mediu na bancada (volumes gastos, branco, massas, absorbâncias) e o app mostra:

1. **O resultado final**, em destaque e com unidade.
2. **As etapas do cálculo** (volume médio, branco descontado, volume corrigido, mols...), para conferir ou transcrever no caderno.
3. **A estatística das réplicas**: desvio padrão, CV, intervalo de confiança e teste de outlier.
4. **Avisos** quando algo foge do esperado (extrapolação da curva, fator fora da faixa, valor abaixo do LOQ...).

Tudo roda no seu navegador: os dados digitados **não são enviados a nenhum servidor**. Por isso, recarregar a página apaga o que foi digitado; exporte o relatório antes de sair.

## Primeiros passos

1. Preencha a **barra lateral** com o ID da amostra, o analista e o lote do reagente. Esses dados vão no cabeçalho dos relatórios exportados.
2. Escolha a aba do cálculo. Para as análises de rotina (dureza, cloretos, DQO...), use a aba **🧪 Análises**.
3. Digite as réplicas na tabela e confira os parâmetros já preenchidos.
4. O resultado aparece à direita na hora, sem botão de "calcular".
5. Exporte em **CSV** ou **PDF** pelos botões abaixo do resultado.

Algumas abas vêm com **valores de exemplo**. Substitua pelos seus dados.

## Como digitar números

- **Vírgula ou ponto** como separador decimal: `10,15` e `10.15` dão o mesmo valor. `1.234,5` é lido como mil duzentos e trinta e quatro vírgula cinco.
- **Tabelas de réplicas**: clique numa célula e digite. Para incluir mais réplicas, use a linha vazia no fim da tabela (ou o **+**). Para apagar, selecione a linha pela caixa à esquerda e pressione **Delete**.
- Células vazias são ignoradas: não precisa preencher todas as linhas.
- Número inválido (ex.: `1o,2`) mostra um erro vermelho logo abaixo do campo.

## 🧪 Análises pré-cadastradas

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
4. Clique em **"Usar este fator nas abas Análises e Titulação"** para preencher o f automaticamente nas outras abas.

Fator fora de 0,90–1,10 gera um aviso: provavelmente há erro de preparo da solução ou de pesagem.

## 📊 Estatística de réplicas

Cole ou digite qualquer série de valores (resultados, volumes, leituras). O app calcula:

- **Média, desvio padrão amostral (s) e CV/RSD%.**
- **Intervalo de confiança** com t de Student (n − 1 graus de liberdade), a 90, 95 ou 99%. O resultado sai no formato `média ± IC`, pronto para o laudo.
- **Teste de Grubbs** para um outlier, com α ajustável.

O Grubbs **só indica** o valor suspeito; o app nunca remove réplica sozinho. Se decidir descartar, apague a linha na tabela e registre o motivo. O teste exige pelo menos 3 valores.

## 🌈 Espectrofotometria

**Curva de calibração** (o mais comum):

1. Digite os padrões: concentração e absorbância.
2. Digite a(s) leitura(s) da amostra. Com várias leituras, o app usa a média.
3. Informe o fator de diluição, se a amostra foi diluída antes da leitura.

O app mostra a equação `A = a·c + b`, o **R²**, o **LOD** (3,3·s/a) e o **LOQ** (10·s/a), o gráfico da curva com a amostra marcada (◆) e o **gráfico de resíduos**. Resíduos espalhados ao acaso em torno de zero indicam boa linearidade; uma curvatura nos resíduos indica que a faixa linear foi excedida.

Avisos importantes:
- **R² < 0,995**: linearidade questionável. Reveja os padrões.
- **Fora da faixa dos padrões**: o resultado foi extrapolado. Dilua a amostra ou amplie a curva.
- **Abaixo do LOD / LOQ**: reporte como "< LOD" ou "< LOQ", não como valor numérico.

**Beer-Lambert direto**: quando a absortividade molar (ε) é conhecida, `c = A / (ε · l)`, com o resultado em mol/L.

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

## Avisos e erros

| Cor | Significado | O que fazer |
|---|---|---|
| 🔵 Azul | Falta preencher algum campo | Complete os dados |
| 🟡 Amarelo | O cálculo foi feito, mas algo merece atenção | Leia o aviso e avalie antes de liberar o resultado |
| 🔴 Vermelho | Dado impossível (volume negativo, branco maior que a amostra, inclinação zero...) | Corrija a entrada; nenhum resultado é mostrado |

## Relatórios

- **CSV**: abre direto no Excel em português (separador `;`, acentos corretos). Traz rastreabilidade, entradas, etapas e resultado.
- **PDF**: o mesmo conteúdo, pronto para imprimir ou anexar. Símbolos químicos aparecem simplificados (CaCO₃ → CaCO3) por limitação da fonte do PDF.
- O nome do arquivo leva o tipo de cálculo e a data/hora.

## Dúvidas frequentes

**A primeira abertura demora, é normal?** Sim. Na primeira vez o navegador baixa o Python e as bibliotecas científicas (cerca de 30 s). Depois fica em cache e abre bem mais rápido.

**Perdi o que tinha digitado.** Recarregar ou fechar a página apaga os dados, porque nada é salvo em servidor. Exporte o relatório ao terminar cada amostra.

**Quantas casas decimais usar?** Ajuste em **Exibição → Casas decimais** na barra lateral. Valores muito pequenos (< 0,01) ou muito grandes (≥ 10 000) aparecem em notação científica, ex.: `1,0100e-03`.

**O resultado é confiável?** As fórmulas são conferidas por testes automáticos com valores calculados à mão, rodados a cada atualização do sistema. Mesmo assim, a liberação do resultado é responsabilidade do analista: confira as etapas exibidas.
