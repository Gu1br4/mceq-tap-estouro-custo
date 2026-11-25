# Resultados (gerados por analise.py)

Projetos na base: 120. Na análise confirmatória: 64 (33 sem aprovação formal, 31 com aprovação formal).
Exclusões: {"preco_e_custo_faltantes('?')": 39, "custo_real_nao_apurado('Not exist')": 16, "preco_contratado_inexistente('Not exist')": 1, 'preco<=0': 0, 'vi_faltante': 0, 'outros': 0, 'checagem_max_diferenca_vs_base(pp)': 0.0}

## Descritiva

| VD | Grupo | n | Média | DP | Mediana | Q1–Q3 | Mín–Máx | % com estouro | % zero | Orgs |
|---|---|---|---|---|---|---|---|---|---|---|
| Estouro de custo (%) | Sem aprovação formal | 33 | 9,3 | 37,8 | 0,0 | 0,0 a 0,0 | -50,0 a 150,0 | 24,2 | 54,5 | 16 |
| Estouro de custo (%) | Com aprovação formal | 31 | -1,3 | 36,2 | 0,0 | -10,1 a 0,0 | -63,0 a 122,2 | 22,6 | 38,7 | 13 |
| Estouro de esforço (%) | Sem aprovação formal | 70 | 91,8 | 151,8 | 50,0 | 17,5 a 100,0 | -66,7 a 1.100,0 | 77,1 | 15,7 | 32 |
| Estouro de esforço (%) | Com aprovação formal | 50 | 89,0 | 83,7 | 66,7 | 50,0 a 100,0 | -8,3 a 380,0 | 86,0 | 12,0 | 22 |

## Confirmatória — estouro de custo

- Shapiro-Wilk: sem W=0.630 p=6.7e-08; com W=0.751 p=7.3e-06 → normalidade_ok=False
- Teste decisor (regra do protocolo): **Mann-Whitney U**
- Mann-Whitney U=600.5, p unilateral=0.1047
- Welch t=1.147, gl=62.0, p unilateral=0.1279
- Decisão (α=0,05): não rejeita H0
- Diferença de médias (sem − com) = 10,6 pp, IC95% [-6,9; 28,4]
- Diferença de medianas = 0,0 pp, IC95% [0,0; 3,6]
- Cliff's δ = 0.174 (pequeno), IC95% [-0.102; 0.431]; P(sem > com) = 0.587
- Hedges g = 0.283, IC95% [-0.198; 0.775]
- Menor d detectável com poder 80%: 0.63

## Exploratória — estouro de esforço

- Shapiro-Wilk: sem W=0.592 p=1.2e-12; com W=0.822 p=3e-06 → normalidade_ok=False
- Teste decisor (regra do protocolo): **Mann-Whitney U**
- Mann-Whitney U=1521.5, p unilateral=0.8898
- Welch t=0.133, gl=111.8, p unilateral=0.4474
- Decisão (α=0,05): não rejeita H0
- Diferença de médias (sem − com) = 2,9 pp, IC95% [-36,9; 47,0]
- Diferença de medianas = -16,7 pp, IC95% [-50,0; 10,0]
- Cliff's δ = -0.131 (desprezível), IC95% [-0.336; 0.071]; P(sem > com) = 0.435
- Hedges g = 0.022, IC95% [-0.410; 0.291]
- Menor d detectável com poder 80%: 0.46

## Perfil dos grupos (confirmatória, apenas descritivo)

```
{
  "Sem aprovação formal": {
    "org_tipo_%": {
      "Empresa privada de software": 45.5,
      "Diretoria federal": 36.4,
      "Universidade": 6.1,
      "Empresa pública de software": 6.1,
      "Freelancer": 3.0,
      "Ministério federal": 3.0
    },
    "metodologia_%": {
      "Cascata": 36.4,
      "Ágil": 30.3,
      "Híbrida": 30.3,
      "Outra": 3.0
    },
    "ano_mediana": 2016.0,
    "preco_contratado_mediana": 400000.0
  },
  "Com aprovação formal": {
    "org_tipo_%": {
      "Empresa privada de software": 41.9,
      "Diretoria federal": 41.9,
      "Freelancer": 9.7,
      "Universidade": 3.2,
      "Ministério federal": 3.2
    },
    "metodologia_%": {
      "Híbrida": 48.4,
      "Cascata": 25.8,
      "Ágil": 22.6,
      "Nenhuma": 3.2
    },
    "ano_mediana": 2012.0,
    "preco_contratado_mediana": 225000.0
  }
}
```
