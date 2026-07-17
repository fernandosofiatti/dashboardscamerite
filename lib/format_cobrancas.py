"""Dashboard for the 'cobrancas.csv' export (billing charges with due dates and discounts)."""

import pandas as pd
import streamlit as st

from lib.common import (
    CAMERITE_GREEN,
    aging_chart,
    apply_date_range,
    apply_filters,
    bar_by_category_horizontal,
    bar_month_recebido_pendente,
    compute_kpis,
    detail_section,
    format_currency,
    format_percent,
    mom_delta,
    pie_by_category,
    render_chart,
    sidebar_date_range,
    sidebar_multiselect,
    to_date,
    to_number,
    top_clients_aging_chart,
)


def detect(columns: list[str]) -> bool:
    return "Vencimento" in columns


def load(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["Valor"] = to_number(df["Valor"])
    df["Desconto"] = to_number(df.get("Desconto", 0))
    df["Vencimento"] = to_date(df["Vencimento"])
    df["Emissão"] = to_date(df["Emissão"])
    df["Pago em"] = to_date(df.get("Pago em"))
    df["Status"] = df["Status"].replace({"undefined": "Sem cobrança gerada"}).fillna("Sem status")
    return df


def render_kpis(kpis: dict, df: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Total Faturado",
        format_currency(kpis["total_faturado"]),
        delta=f"{kpis['n_faturado']} cobranças emitidas",
        delta_color="off",
    )
    c2.metric(
        "Total a Receber",
        format_currency(kpis["total_pendente"]),
        delta=f"{len(kpis['pendente_like'])} cobranças pendentes",
        delta_color="off",
    )
    c3.metric(
        "Total Recebido",
        format_currency(kpis["total_pago"]),
        delta=mom_delta(kpis["pago"], "Pago em", "Valor"),
    )
    c4.metric(
        "Vencido",
        format_currency(kpis["total_vencido"]),
        delta=f"{len(kpis['vencido'])} cobranças vencidas",
        delta_color="off",
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric(
        "Sem Cobrança Gerada",
        format_currency(kpis["total_sem_cobranca"]),
        delta=f"{len(kpis['sem_cobranca'])} cobranças (fora do faturado)",
        delta_color="off",
    )
    c6.metric("Taxa de Inadimplência", format_percent(kpis["taxa_inadimplencia"]))
    c7.metric("Ticket Médio (Pago)", format_currency(kpis["ticket_medio"]))
    c8.metric("Descontos Concedidos", format_currency(kpis["total_desconto"]))


def render(df: pd.DataFrame):
    st.sidebar.header("Filtros")
    periodo = sidebar_date_range(df, "Vencimento", "Período (vencimento)")
    filters = {
        "Status": sidebar_multiselect(df, "Status", "Status"),
        "Tipo": sidebar_multiselect(df, "Tipo", "Tipo"),
        "Forma": sidebar_multiselect(df, "Forma", "Forma de pagamento"),
        "Whitelabel": sidebar_multiselect(df, "Whitelabel", "Cliente"),
    }
    df = apply_date_range(df, "Vencimento", periodo)
    df = apply_filters(df, filters)

    if df.empty:
        st.info("Nenhuma linha para os filtros atuais.")
        return

    kpis = compute_kpis(df)
    render_kpis(kpis, df)

    cols = st.columns(2)
    with cols[0]:
        render_chart(aging_chart(kpis["pendente_like"], kpis["hoje"], "Aging de Recebíveis em Aberto"), "aging")
    with cols[1]:
        render_chart(pie_by_category(df, "Tipo", "Valor", "Distribuição por Tipo"), "tipo")

    cols = st.columns(2)
    with cols[0]:
        render_chart(pie_by_category(df, "Forma", "Valor", "Distribuição por Forma de Pagamento"), "forma")
    with cols[1]:
        fig_month = bar_month_recebido_pendente(df, "Vencimento", "Recebido vs A Receber por Mês (Vencimento)")
        if fig_month:
            render_chart(fig_month, "mes")

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

    detail_section(
        df,
        key="cobrancas",
        views={"Vencidas": kpis["vencido"].sort_values("Valor", ascending=False)},
    )
