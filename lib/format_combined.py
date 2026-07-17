"""Cross-referenced dashboard: cobrancas.csv (billing detail, has Vencimento/Desconto)
enriched with notas.csv's PartnerManager (shown in the UI as "CS"), joined on the
'Nota' column present in both exports."""

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import format_cobrancas
from lib.common import (
    CAMERITE_GREEN,
    CAMERITE_PURPLE,
    aging_chart,
    apply_date_range,
    apply_filters,
    bar_by_category_horizontal,
    bar_month_recebido_pendente,
    compute_kpis,
    detail_section,
    line_month_by_category,
    render_chart,
    section_title,
    sidebar_date_range,
    sidebar_multiselect,
    style_fig,
    top_clients_aging_chart,
)


def load(cobrancas_raw: pd.DataFrame, notas_raw: pd.DataFrame) -> pd.DataFrame:
    cob = format_cobrancas.load(cobrancas_raw)
    cob["Nota"] = cob["Nota"].astype(str).str.strip()

    notas_slim = notas_raw[["Nota", "PartnerManager"]].rename(columns={"PartnerManager": "CS"})
    notas_slim["Nota"] = notas_slim["Nota"].astype(str).str.strip()
    notas_slim["CS"] = notas_slim["CS"].replace("", pd.NA)
    notas_slim = notas_slim.drop_duplicates(subset="Nota")

    merged = cob.merge(notas_slim, on="Nota", how="left", indicator="_match")
    # Distinguish "no matching nota in the export" from "nota matched but CS empty" so the
    # caller can warn about a misaligned export instead of silently diluting the CS charts.
    merged.attrs["cobrancas_sem_nota"] = int((merged["_match"] == "left_only").sum())
    merged = merged.drop(columns="_match")
    merged["CS"] = merged["CS"].fillna("Sem CS")
    return merged


def _taxa_inadimplencia_por_cs(pendente_like: pd.DataFrame, hoje) -> pd.DataFrame:
    tmp = pendente_like.copy()
    tmp["Vencido"] = tmp["Vencimento"] < hoje
    total = tmp.groupby("CS", as_index=False)["Valor"].sum().rename(columns={"Valor": "Total"})
    vencido = (
        tmp[tmp["Vencido"]].groupby("CS", as_index=False)["Valor"].sum().rename(columns={"Valor": "Vencido"})
    )
    out = total.merge(vencido, on="CS", how="left")
    out["Vencido"] = out["Vencido"].fillna(0)
    out["Taxa"] = (out["Vencido"] / out["Total"] * 100).where(out["Total"] > 0, 0)
    return out.sort_values("Taxa", ascending=True)


def render(df: pd.DataFrame):
    st.sidebar.header("Filtros")
    periodo = sidebar_date_range(df, "Vencimento", "Período (vencimento)")
    filters = {
        "Status": sidebar_multiselect(df, "Status", "Status"),
        "Tipo": sidebar_multiselect(df, "Tipo", "Tipo"),
        "Forma": sidebar_multiselect(df, "Forma", "Forma de pagamento"),
        "Whitelabel": sidebar_multiselect(df, "Whitelabel", "Cliente"),
        "CS": sidebar_multiselect(df, "CS", "CS"),
    }
    df = apply_date_range(df, "Vencimento", periodo)
    df = apply_filters(df, filters)

    if df.empty:
        st.info("Nenhuma linha para os filtros atuais.")
        return

    kpis = compute_kpis(df)
    format_cobrancas.render_kpis(kpis, df)

    cols = st.columns(2)
    with cols[0]:
        render_chart(
            aging_chart(kpis["pendente_like"], kpis["hoje"], "Aging de Recebíveis em Aberto", height=460), "aging"
        )
    with cols[1]:
        fig_month = bar_month_recebido_pendente(
            df, "Vencimento", "Recebido vs A Receber por Mês (Vencimento)", height=460
        )
        if fig_month:
            render_chart(fig_month, "mes")

    section_title("Evolução Carteira por CS")
    fig_cs = line_month_by_category(df, "Vencimento", "CS", "Valor Emitido por Mês, por CS (Vencimento)", height=420)
    if fig_cs:
        render_chart(fig_cs, "mes_cs")
    else:
        st.info("Sem cobranças com vencimento nos filtros atuais.")

    render_chart(
        top_clients_aging_chart(
            kpis["pendente_like"], kpis["hoje"], "Whitelabel", "Top 20 Clientes por Valor em Aberto (por Aging)", top_n=20
        ),
        "top_clientes",
    )
    render_chart(
        bar_by_category_horizontal(
            kpis["pago"], "Whitelabel", "Valor", "Top 20 Clientes por Valor Pago", top_n=20, color=CAMERITE_GREEN
        ),
        "top_clientes_pago",
    )

    st.divider()
    section_title("Dados por CS")

    render_chart(
        aging_chart(kpis["pendente_like"], kpis["hoje"], "Aging de Recebíveis por CS", color_col="CS"),
        "aging_cs",
    )

    cols = st.columns(2)
    with cols[0]:
        taxa_cs = _taxa_inadimplencia_por_cs(kpis["pendente_like"], kpis["hoje"])
        fig_taxa = px.bar(
            taxa_cs,
            x="Taxa",
            y="CS",
            orientation="h",
            title="Taxa de Inadimplência por CS",
            color_discrete_sequence=[CAMERITE_PURPLE],
        )
        fig_taxa.update_xaxes(ticksuffix="%")
        render_chart(style_fig(fig_taxa, height=max(360, 28 * len(taxa_cs))), "taxa_cs")
    with cols[1]:
        desconto_df = df.assign(DescontoAbs=df["Desconto"].abs())
        render_chart(
            bar_by_category_horizontal(
                desconto_df, "CS", "DescontoAbs", "Descontos Concedidos por CS", top_n=10
            ),
            "desconto_cs",
        )

    detail_section(
        df,
        key="combined",
        views={"Vencidas": kpis["vencido"].sort_values("Valor", ascending=False)},
    )
