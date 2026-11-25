# TAP × estouro de custo em projetos de software (MCEQ 12576 — Projeto Final)

**Pergunta:** projetos de software **sem** Termo de Abertura do Projeto (TAP) apresentam maior percentual de estouro no orçamento do que projetos **com** TAP?

**Operacionalização** (detalhes e justificativa em [docs/protocolo.md](docs/protocolo.md)):

- **VI (proxy de TAP):** a alta gestão revisou e aprovou formalmente os requisitos? (`Review and approval of the requirements`: sim/não)
- **VD:** estouro de custo (%) = (custo real − preço contratado) / preço contratado × 100
- **Desenho:** observacional, 2 grupos independentes; Mann-Whitney U unilateral (α = 0,05), escolhido pela regra do protocolo (Welch se houver normalidade)

## Dados

| Item | Valor |
|---|---|
| Base | *The SEERA Software Cost Estimation Dataset*, versão 1 |
| Autores | Emtinan I. Mustafa e Rasha Osman (Universidade de Cartum) |
| DOI | [10.5281/zenodo.3987969](https://doi.org/10.5281/zenodo.3987969) |
| Artigo de origem | PROMISE'20, DOI [10.1145/3416508.3417119](https://doi.org/10.1145/3416508.3417119) |
| Arquivo | `dados/brutos/The_SEERA_Dataset.zip` (md5 `b1ea3e8eb763415f0679a6fc6618de96`) |
| Data de acesso | 25/11/2026 |
| Licença | CC-BY 4.0 (redistribuição permitida com atribuição) |

Os dados brutos **nunca** são editados à mão: `analise.py` lê o `.xlsx` direto de dentro do `.zip`.

## Como reexecutar

Requer Python 3.10 ou mais novo.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python analise.py
```

Se `dados/brutos/The_SEERA_Dataset.zip` não existir, o script baixa do Zenodo e confere o MD5 (`baixar_dados.py`).
No Google Colab: envie a pasta, rode `!pip install -r requirements.txt` e `!python analise.py`.

## O que é gerado

| Arquivo | Conteúdo |
|---|---|
| `dados/limpos/seera_limpo.csv` | 120 projetos com VI, VD e a marcação de quem entrou na análise |
| `resultados/tabela_descritiva.csv` | Tabela 1 do artigo |
| `resultados/resultados.json` | todos os números do artigo (testes, p-valores, efeitos, IC) |
| `resultados/resumo.md` | os mesmos números em texto legível |
| `resultados/figura1.png` | Figura 1 do artigo |

A análise é determinística (bootstrap com `numpy.random.default_rng(2026)`): rodar de novo produz exatamente os mesmos números.

## Estrutura

```
analise.py           dados brutos -> limpeza -> descritiva -> testes -> figura
baixar_dados.py      download + conferência de MD5
requirements.txt     versões das bibliotecas
docs/protocolo.md    protocolo de 1 página (registrado antes da análise)
dados/brutos/        zip original do Zenodo
dados/limpos/        gerado pelo script
resultados/          gerado pelo script
```
