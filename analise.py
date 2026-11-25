"""Projeto Final MCEQ 12576 — TAP (proxy) x estouro de custo em projetos de software.

Vai dos dados brutos (zip do Zenodo) até todos os números e a figura do artigo.
Uso:  python analise.py
Saídas: dados/limpos/seera_limpo.csv, resultados/*.csv|json|md|png

O plano de análise está em docs/protocolo.md (registrado antes de rodar os testes).
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from baixar_dados import garantir_dados

RAIZ = Path(__file__).resolve().parent
DIR_LIMPOS = RAIZ / "dados" / "limpos"
DIR_RES = RAIZ / "resultados"
ARQ_BRUTO_NO_ZIP = "The SEERA Dataset/Dataset Files/SEERA dataset original raw data.xlsx"

ALFA = 0.05
N_BOOT = 10_000
SEMENTE = 2026

GRUPO_COM = "Com aprovação formal"
GRUPO_SEM = "Sem aprovação formal"

ORG_TIPO = {1: "Empresa pública de software", 2: "Universidade", 3: "Ministério federal",
            4: "Diretoria federal", 5: "Empresa privada de software", 6: "Depto. de TI corporativo",
            7: "Freelancer", 8: "Telecom"}
METODOLOGIA = {1: "Cascata", 2: "Ágil", 3: "Híbrida", 4: "Nenhuma", 6: "Prototipação", 7: "Outra"}


# --------------------------------------------------------------------------- 1. carga
def ler_aba(xlsx: bytes, aba: str) -> pd.DataFrame:
    """Lê uma aba do arquivo bruto: linha 0 = atributo, linha 1 = sub-atributo, dados a partir da linha 2."""
    df = pd.read_excel(io.BytesIO(xlsx), sheet_name=aba, header=None)
    topo = df.iloc[0].ffill()
    sub = df.iloc[1]
    nomes = [str(t).strip() if pd.isna(s) else str(s).strip() for t, s in zip(topo, sub)]
    corpo = df.iloc[2:].reset_index(drop=True)
    corpo.columns = nomes
    corpo = corpo.loc[:, ~corpo.columns.duplicated()]
    id_col = corpo.columns[0]
    corpo = corpo.rename(columns={id_col: "projID"})
    corpo = corpo[pd.to_numeric(corpo["projID"], errors="coerce").notna()]
    corpo["projID"] = corpo["projID"].astype(int)
    return corpo


def carregar_brutos() -> pd.DataFrame:
    zip_path = garantir_dados()
    with zipfile.ZipFile(zip_path) as z:
        xlsx = z.read(ARQ_BRUTO_NO_ZIP)
    geral = ler_aba(xlsx, "General Information")
    esforco = ler_aba(xlsx, "Effort")
    usuarios = ler_aba(xlsx, "Users")
    projeto = ler_aba(xlsx, "Project")

    df = geral[["projID", "Year of project (Main)", "Organization id", "Organization type",
                "Contract price", "Actual incurred costs", "% project gain (loss) (Main)"]].copy()
    df = df.merge(esforco[["projID", "Estimated Effort (Main)", "Actual effort (Main)"]], on="projID")
    df = df.merge(usuarios[["projID", "Review and approval of the requirements"]], on="projID")
    df = df.merge(projeto[["projID", "Methodology"]], on="projID")
    assert len(df) == 120, f"esperado 120 projetos, obtido {len(df)}"
    return df


# --------------------------------------------------------------------------- 2. limpeza
def para_bool(v) -> bool | None:
    s = str(v).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = pd.DataFrame({
        "projID": df["projID"],
        "ano": pd.to_numeric(df["Year of project (Main)"], errors="coerce"),
        "org_id": pd.to_numeric(df["Organization id"], errors="coerce").astype("Int64"),
        "org_tipo": pd.to_numeric(df["Organization type"], errors="coerce").map(ORG_TIPO),
        "metodologia": pd.to_numeric(df["Methodology"], errors="coerce").map(METODOLOGIA),
        "aprovacao_requisitos": df["Review and approval of the requirements"].map(para_bool),
        "preco_contratado": pd.to_numeric(df["Contract price"], errors="coerce"),
        "custo_real": pd.to_numeric(df["Actual incurred costs"], errors="coerce"),
        "ganho_perda_original": pd.to_numeric(df["% project gain (loss) (Main)"], errors="coerce"),
        "esforco_estimado_h": pd.to_numeric(df["Estimated Effort (Main)"], errors="coerce"),
        "esforco_real_h": pd.to_numeric(df["Actual effort (Main)"], errors="coerce"),
    })
    out["grupo"] = out["aprovacao_requisitos"].map({True: GRUPO_COM, False: GRUPO_SEM})

    bruto_custo = df["Actual incurred costs"].astype(str).str.strip()
    bruto_preco = df["Contract price"].astype(str).str.strip()
    valido = out["preco_contratado"].notna() & out["custo_real"].notna() & (out["preco_contratado"] > 0)
    # cada projeto excluído é contado em um único motivo (o primeiro que se aplica)
    faltante = (bruto_custo == "?") | (bruto_preco == "?")
    custo_ne = ~faltante & (bruto_custo == "Not exist")
    preco_ne = ~faltante & ~custo_ne & (bruto_preco == "Not exist")
    motivos = {
        "preco_e_custo_faltantes('?')": int(faltante.sum()),
        "custo_real_nao_apurado('Not exist')": int(custo_ne.sum()),
        "preco_contratado_inexistente('Not exist')": int(preco_ne.sum()),
        "preco<=0": int((out["preco_contratado"].notna() & out["custo_real"].notna()
                         & (out["preco_contratado"] <= 0)).sum()),
        "vi_faltante": int((valido & out["grupo"].isna()).sum()),
    }
    motivos["outros"] = int((~valido).sum()) - sum(v for k, v in motivos.items() if k != "vi_faltante")

    # VD primária: estouro de custo (%)
    out["estouro_custo_pct"] = np.where(
        valido, (out["custo_real"] - out["preco_contratado"]) / out["preco_contratado"] * 100, np.nan)
    # VD exploratória: estouro de esforço (%)
    out["estouro_esforco_pct"] = ((out["esforco_real_h"] - out["esforco_estimado_h"])
                                  / out["esforco_estimado_h"] * 100)

    # checagem: a VD deve ser exatamente o oposto do "% project gain (loss)" calculado pelos autores
    chk = out.dropna(subset=["estouro_custo_pct", "ganho_perda_original"])
    max_dif = float(np.max(np.abs(chk["estouro_custo_pct"] + chk["ganho_perda_original"] * 100))) if len(chk) else 0.0
    motivos["checagem_max_diferenca_vs_base(pp)"] = round(max_dif, 9)

    out["incluido_analise_principal"] = valido & out["grupo"].notna()
    return out, motivos


# --------------------------------------------------------------------------- 3. estatística
def descritiva(x: np.ndarray) -> dict:
    q1, med, q3 = np.percentile(x, [25, 50, 75])
    return {"n": int(len(x)), "media": float(np.mean(x)), "dp": float(np.std(x, ddof=1)),
            "mediana": float(med), "q1": float(q1), "q3": float(q3),
            "min": float(np.min(x)), "max": float(np.max(x)),
            "pct_estouro_pos": float(np.mean(x > 0) * 100), "pct_zero": float(np.mean(x == 0) * 100),
            "pct_abaixo": float(np.mean(x < 0) * 100)}


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """δ = P(X > Y) − P(X < Y). Positivo => valores do grupo x tendem a ser maiores."""
    dif = x[:, None] - y[None, :]
    return float((np.sum(dif > 0) - np.sum(dif < 0)) / (len(x) * len(y)))


def hedges_g(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    j = 1 - 3 / (4 * (nx + ny) - 9)
    return float(j * (np.mean(x) - np.mean(y)) / sp)


def bootstrap_ic(x: np.ndarray, y: np.ndarray, fn, rng: np.random.Generator, n_boot: int = N_BOOT):
    est = np.empty(n_boot)
    for b in range(n_boot):
        est[b] = fn(rng.choice(x, len(x), replace=True), rng.choice(y, len(y), replace=True))
    lo, hi = np.percentile(est, [2.5, 97.5])
    return float(lo), float(hi)


def efeito_detectavel_80(nx: int, ny: int, alfa: float = ALFA, poder: float = 0.80) -> float:
    """Menor d de Cohen detectável com poder 80% (teste t unilateral, aprox. variâncias iguais)."""
    gl = nx + ny - 2
    tcrit = stats.t.ppf(1 - alfa, gl)
    lo, hi = 0.0, 5.0
    for _ in range(100):
        d = (lo + hi) / 2
        ncp = d * np.sqrt(nx * ny / (nx + ny))
        if 1 - stats.nct.cdf(tcrit, gl, ncp) < poder:
            lo = d
        else:
            hi = d
    return float((lo + hi) / 2)


def comparar(sem: np.ndarray, com: np.ndarray, rng: np.random.Generator) -> dict:
    """Aplica exatamente a regra do protocolo: Welch se ambos normais, senão Mann-Whitney."""
    sw_sem = stats.shapiro(sem)
    sw_com = stats.shapiro(com)
    normal = (sw_sem.pvalue > ALFA) and (sw_com.pvalue > ALFA)

    welch = stats.ttest_ind(sem, com, equal_var=False, alternative="greater")
    mw = stats.mannwhitneyu(sem, com, alternative="greater", method="asymptotic")

    delta = cliffs_delta(sem, com)
    g = hedges_g(sem, com)
    r = {
        "shapiro_sem": {"W": float(sw_sem.statistic), "p": float(sw_sem.pvalue)},
        "shapiro_com": {"W": float(sw_com.statistic), "p": float(sw_com.pvalue)},
        "normalidade_ok": bool(normal),
        "teste_decisor": "Welch (t)" if normal else "Mann-Whitney U",
        "welch": {"t": float(welch.statistic), "gl": float(welch.df), "p_unilateral": float(welch.pvalue)},
        "mann_whitney": {"U": float(mw.statistic), "p_unilateral": float(mw.pvalue)},
        "dif_medias": float(np.mean(sem) - np.mean(com)),
        "dif_medianas": float(np.median(sem) - np.median(com)),
        "hedges_g": g,
        "cliffs_delta": delta,
        "prob_superioridade": float((delta + 1) / 2),
    }
    r["ic95_dif_medias"] = bootstrap_ic(sem, com, lambda a, b: np.mean(a) - np.mean(b), rng)
    r["ic95_dif_medianas"] = bootstrap_ic(sem, com, lambda a, b: np.median(a) - np.median(b), rng)
    r["ic95_hedges_g"] = bootstrap_ic(sem, com, hedges_g, rng)
    r["ic95_cliffs_delta"] = bootstrap_ic(sem, com, cliffs_delta, rng)
    p = r["welch"]["p_unilateral"] if normal else r["mann_whitney"]["p_unilateral"]
    r["p_decisor"] = p
    r["rejeita_H0"] = bool(p < ALFA)
    r["d_detectavel_poder80"] = efeito_detectavel_80(len(sem), len(com))
    return r


def magnitude_cliff(d: float) -> str:
    a = abs(d)
    return "desprezível" if a < 0.147 else "pequeno" if a < 0.33 else "médio" if a < 0.474 else "grande"


# --------------------------------------------------------------------------- 4. figura
def ponto_medio_ic(ax, pos, x, rng, cor):
    m = np.mean(x)
    boots = np.array([np.mean(rng.choice(x, len(x), replace=True)) for _ in range(N_BOOT)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    ax.errorbar(pos + 0.28, m, yerr=[[m - lo], [hi - m]], fmt="D", color=cor, ms=6, capsize=4, lw=1.5,
                label="Média e IC 95% (bootstrap)" if pos == 1 else None)


def figura(df_c: pd.DataFrame, df_e: pd.DataFrame, rng: np.random.Generator, caminho: Path,
           coluna: bool = False) -> None:
    """coluna=False: painéis lado a lado (vídeo/slides); coluna=True: empilhados, largura de 1 coluna ACM."""
    cores = {GRUPO_SEM: "#c0392b", GRUPO_COM: "#2471a3"}
    ordem = [GRUPO_SEM, GRUPO_COM]
    if coluna:
        plt.rcParams.update({"font.size": 7})
        fig, axes = plt.subplots(2, 1, figsize=(3.4, 5.0), dpi=300)
    else:
        plt.rcParams.update({"font.size": 10})
        fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), dpi=200)
    paineis = [(axes[0], df_c, "estouro_custo_pct", "(a) Confirmatória: estouro de custo"),
               (axes[1], df_e, "estouro_esforco_pct", "(b) Exploratória: estouro de esforço")]
    for ax, dados, col, titulo in paineis:
        grupos = [dados.loc[dados["grupo"] == g, col].to_numpy() for g in ordem]
        ax.boxplot(grupos, positions=[1, 2], widths=0.45, showfliers=False,
                   medianprops={"color": "black", "lw": 1.5}, boxprops={"color": "#555"},
                   whiskerprops={"color": "#555"}, capprops={"color": "#555"})
        for i, (g, x) in enumerate(zip(ordem, grupos), start=1):
            jit = rng.uniform(-0.12, 0.12, len(x))
            ax.scatter(np.full(len(x), i) + jit, x, s=14, alpha=0.55, color=cores[g], edgecolor="none")
            ponto_medio_ic(ax, i, x, rng, cores[g])
        ax.axhline(0, color="#888", lw=0.8, ls="--")
        ax.set_xticks([1, 2], [f"Sem aprovação\nformal (n={len(grupos[0])})",
                               f"Com aprovação\nformal (n={len(grupos[1])})"])
        ax.set_ylabel(f"Estouro de {'custo' if 'custo' in col else 'esforço'} (%)")
        ax.set_title(titulo, fontsize=8 if coluna else 10)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(loc="upper right", fontsize=6 if coluna else 7, frameon=False)
    if not coluna:
        fig.text(0.5, 0.005, "Caixa = Q1–mediana–Q3; pontos = projetos; linha tracejada = 0% (sem estouro). "
                 "Fonte: SEERA (Mustafa e Osman, 2020).", ha="center", fontsize=7, color="#444")
    fig.tight_layout(rect=(0, 0.03 if not coluna else 0, 1, 1))
    fig.savefig(caminho)
    plt.close(fig)


# --------------------------------------------------------------------------- 5. principal
def br(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows
    DIR_LIMPOS.mkdir(parents=True, exist_ok=True)
    DIR_RES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEMENTE)

    brutos = carregar_brutos()
    limpo, exclusoes = limpar(brutos)
    limpo.to_csv(DIR_LIMPOS / "seera_limpo.csv", index=False, encoding="utf-8")

    # ---- confirmatória
    conf = limpo[limpo["incluido_analise_principal"]].copy()
    sem = conf.loc[conf["grupo"] == GRUPO_SEM, "estouro_custo_pct"].to_numpy(float)
    com = conf.loc[conf["grupo"] == GRUPO_COM, "estouro_custo_pct"].to_numpy(float)
    res_conf = comparar(sem, com, rng)

    # ---- exploratória (n = 120)
    expl = limpo[limpo["grupo"].notna() & limpo["estouro_esforco_pct"].notna()].copy()
    sem_e = expl.loc[expl["grupo"] == GRUPO_SEM, "estouro_esforco_pct"].to_numpy(float)
    com_e = expl.loc[expl["grupo"] == GRUPO_COM, "estouro_esforco_pct"].to_numpy(float)
    res_expl = comparar(sem_e, com_e, rng)

    # ---- descritiva
    linhas = []
    for nome_vd, base, col in [("Estouro de custo (%)", conf, "estouro_custo_pct"),
                               ("Estouro de esforço (%)", expl, "estouro_esforco_pct")]:
        for g in [GRUPO_SEM, GRUPO_COM]:
            d = descritiva(base.loc[base["grupo"] == g, col].to_numpy(float))
            linhas.append({"VD": nome_vd, "grupo": g, **d,
                           "n_organizacoes": int(base.loc[base["grupo"] == g, "org_id"].nunique())})
    tab = pd.DataFrame(linhas)
    tab.to_csv(DIR_RES / "tabela_descritiva.csv", index=False, encoding="utf-8")

    # ---- perfil dos grupos (para discutir confundimento; apenas descritivo)
    perfil = {}
    for g in [GRUPO_SEM, GRUPO_COM]:
        sub = conf[conf["grupo"] == g]
        perfil[g] = {
            "org_tipo_%": (sub["org_tipo"].value_counts(normalize=True) * 100).round(1).to_dict(),
            "metodologia_%": (sub["metodologia"].value_counts(normalize=True) * 100).round(1).to_dict(),
            "ano_mediana": float(sub["ano"].median()),
            "preco_contratado_mediana": float(sub["preco_contratado"].median()),
        }

    figura(conf, expl, rng, DIR_RES / "figura1.png")
    figura(conf, expl, rng, DIR_RES / "figura1_coluna.png", coluna=True)

    resultados = {
        "base": {"nome": "SEERA Software Cost Estimation Dataset v1", "doi": "10.5281/zenodo.3987969",
                 "licenca": "CC-BY 4.0", "n_total": int(len(limpo))},
        "parametros": {"alfa": ALFA, "n_bootstrap": N_BOOT, "semente": SEMENTE, "H1": "unilateral (sem > com)"},
        "exclusoes_analise_principal": exclusoes,
        "n_analise_principal": {"total": int(len(conf)), GRUPO_SEM: int(len(sem)), GRUPO_COM: int(len(com))},
        "n_projetos_por_grupo_total": limpo["grupo"].value_counts().to_dict(),
        "confirmatoria_estouro_custo": res_conf,
        "exploratoria_estouro_esforco": res_expl,
        "perfil_grupos_analise_principal": perfil,
        "numero_de_testes_de_hipotese": 2,
    }
    with (DIR_RES / "resultados.json").open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # ---- resumo legível
    rc, re_ = res_conf, res_expl
    t = tab.set_index(["VD", "grupo"])
    linhas_md = [
        "# Resultados (gerados por analise.py)",
        "",
        f"Projetos na base: {len(limpo)}. Na análise confirmatória: {len(conf)} "
        f"({len(sem)} sem aprovação formal, {len(com)} com aprovação formal).",
        f"Exclusões: {exclusoes}",
        "",
        "## Descritiva",
        "",
        "| VD | Grupo | n | Média | DP | Mediana | Q1–Q3 | Mín–Máx | % com estouro | % zero | Orgs |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (vd, g), r in t.iterrows():
        linhas_md.append(f"| {vd} | {g} | {int(r.n)} | {br(r.media)} | {br(r.dp)} | {br(r.mediana)} | "
                         f"{br(r.q1)} a {br(r.q3)} | {br(r['min'])} a {br(r['max'])} | {br(r.pct_estouro_pos)} | "
                         f"{br(r.pct_zero)} | {int(r.n_organizacoes)} |")
    for titulo, r in [("Confirmatória — estouro de custo", rc), ("Exploratória — estouro de esforço", re_)]:
        linhas_md += [
            "", f"## {titulo}", "",
            f"- Shapiro-Wilk: sem W={r['shapiro_sem']['W']:.3f} p={r['shapiro_sem']['p']:.2g}; "
            f"com W={r['shapiro_com']['W']:.3f} p={r['shapiro_com']['p']:.2g} → normalidade_ok={r['normalidade_ok']}",
            f"- Teste decisor (regra do protocolo): **{r['teste_decisor']}**",
            f"- Mann-Whitney U={r['mann_whitney']['U']:.1f}, p unilateral={r['mann_whitney']['p_unilateral']:.4f}",
            f"- Welch t={r['welch']['t']:.3f}, gl={r['welch']['gl']:.1f}, p unilateral={r['welch']['p_unilateral']:.4f}",
            f"- Decisão (α=0,05): {'rejeita H0' if r['rejeita_H0'] else 'não rejeita H0'}",
            f"- Diferença de médias (sem − com) = {br(r['dif_medias'])} pp, IC95% [{br(r['ic95_dif_medias'][0])}; {br(r['ic95_dif_medias'][1])}]",
            f"- Diferença de medianas = {br(r['dif_medianas'])} pp, IC95% [{br(r['ic95_dif_medianas'][0])}; {br(r['ic95_dif_medianas'][1])}]",
            f"- Cliff's δ = {r['cliffs_delta']:.3f} ({magnitude_cliff(r['cliffs_delta'])}), "
            f"IC95% [{r['ic95_cliffs_delta'][0]:.3f}; {r['ic95_cliffs_delta'][1]:.3f}]; P(sem > com) = {r['prob_superioridade']:.3f}",
            f"- Hedges g = {r['hedges_g']:.3f}, IC95% [{r['ic95_hedges_g'][0]:.3f}; {r['ic95_hedges_g'][1]:.3f}]",
            f"- Menor d detectável com poder 80%: {r['d_detectavel_poder80']:.2f}",
        ]
    linhas_md += ["", "## Perfil dos grupos (confirmatória, apenas descritivo)", "",
                  "```", json.dumps(perfil, ensure_ascii=False, indent=2), "```"]
    (DIR_RES / "resumo.md").write_text("\n".join(linhas_md) + "\n", encoding="utf-8")
    print("\n".join(linhas_md))


if __name__ == "__main__":
    main()
