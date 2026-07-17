"""Dashboard for the 'notas.csv' export (invoices with partner-manager attribution)."""

import pandas as pd
import streamlit as st

from lib.common import (
    CAMERITE_GREEN,
    apply_date_range,
    apply_filters,
    bar_by_category_horizontal,
    bar_month_recebido_pendente,
    detail_section,
    format_currency,
    format_percent,
    line_month_by_category,
    mom_delta,
    render_chart,
    section_title,
    sidebar_date_range,
    sidebar_multiselect,
    to_date,
    to_number,
)


def detect(columns: list[str]) -> bool:
    return "PartnerManager" in columns


def _split_whitelabel(value: str) -> str:
    if not isinstance(value, str):
        return "(sem nome)"
    parts = value.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]
    return value.strip()


def load(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    # The source CSV has two columns literally named "Status" (nota status, cobrança status);
    # pandas auto-renames the second occurrence to "Status.1" — that's the one we care about.
    status_col = "Status.1" if "Status.1" in df.columns else "Status"

    df["Valor"] = to_number(df["Valor"])
    df["Autorização"] = to_date(df["Autorização"])
    df["Cliente"] = df["Whitelabel"].apply(_split_whitelabel)
    df["Status"] = df[status_col].replace("", "Sem status").fillna("Sem status")
    # The export calls it "PartnerManager"; in the UI the role is called CS.
    df = df.rename(columns={"PartnerManager": "CS"})
    df["CS"] = df["CS"].replace("", "Sem CS").fillna("Sem CS")
    return df


def render(df: pd.DataFrame):
    st.sidebar.header("Filtros")
    periodo = sidebar_date_range(df, "Autorização", "Período (autorização)")
    filters = {
        "Status": sidebar_multiselect(df, "Status", "Status"),
        "Tipo": sidebar_multiselect(df, "Tipo", "Tipo"),
        "Método": sidebar_multiselect(df, "Método", "Método de pagamento"),
        "CS": sidebar_multiselect(df, "CS", "CS"),
        "Cliente": sidebar_multiselect(df, "Cliente", "Cliente"),
    }
    df = apply_date_range(df, "Autorização", periodo)
    df = apply_filters(df, filters)

    if df.empty:
        st.info("Nenhuma linha para os filtros atuais.")
        return

    # Same KPI pattern as the cobranças dashboard: faturado = pago + pendente,
    # with "Sem status" split out so it doesn't inflate the totals.
    pendente = df[df["Status"] == "Pendente"]
    pago = df[df["Status"] == "Pago"]
    cancelado = df[df["Status"] == "Cancelado"]
    sem_status = df[~df["Status"].isin(["Pendente", "Pago", "Cancelado"])]

    total_pendente = pendente["Valor"].sum()
    total_pago = pago["Valor"].sum()
    total_cancelado = cancelado["Valor"].sum()
    total_sem_status = sem_status["Valor"].sum()
    total_faturado = total_pendente + total_pago
    ticket_medio = pago["Valor"].mean() if len(pago) else 0.0
    qtd_pendente = len(pendente)
    pct_sem_cs = (
        (pendente["CS"] == "Sem CS").sum() / qtd_pendente * 100 if qtd_pendente else 0.0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Total Faturado",
        format_currency(total_faturado),
        delta=f"{len(pendente) + len(pago)} notas emitidas",
        delta_color="off",
    )
    c2.metric(
        "Total a Receber",
        format_currency(total_pendente),
        delta=f"{qtd_pendente} notas pendentes",
        delta_color="off",
    )
    c3.metric(
        "Total Recebido",
        format_currency(total_pago),
        delta=mom_delta(pago, "Autorização", "Valor"),
    )
    c4.metric(
        "Total Cancelado",
        format_currency(total_cancelado),
        delta=f"{len(cancelado)} notas canceladas",
        delta_color="off",
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric(
        "Sem Status",
        format_currency(total_sem_status),
        delta=f"{len(sem_status)} notas (fora do faturado)",
        delta_color="off",
    )
    c6.metric("Ticket Médio (Pago)", format_currency(ticket_medio))
    c7.metric("Pendente sem CS", format_percent(pct_sem_cs))
    c8.metric("Notas no Período", f"{len(df)}")

    fig_month = bar_month_recebido_pendente(df, "Autorização", "Recebido vs A Receber por Mês (Autorização)")
    if fig_month:
        render_chart(fig_month, "mes")

    section_title("Evolução Carteira por CS")
    fig_cs = line_month_by_category(df, "Autorização", "CS", "Valor Emitido por Mês, por CS (Autorização)", height=420)
    if fig_cs:
        render_chart(fig_cs, "mes_cs")
    else:
        st.info("Sem notas com data de autorização nos filtros atuais.")

    render_chart(
        bar_by_category_horizontal(pendente, "Cliente", "Valor", "Top 20 Clientes por Valor Pendente", top_n=20),
        "top_clientes",
    )
    render_chart(
        bar_by_category_horizontal(
            pago, "Cliente", "Valor", "Top 20 Clientes por Valor Pago", top_n=20, color=CAMERITE_GREEN
        ),
        "top_clientes_pago",
    )

    cols = st.columns(2)
    with cols[0]:
        render_chart(
            bar_by_category_horizontal(pendente, "CS", "Valor", "Valor Pendente por CS", top_n=10),
            "por_cs",
        )
    with cols[1]:
        render_chart(
            bar_by_category_horizontal(pago, "CS", "Valor", "Valor Pago por CS", top_n=10, color=CAMERITE_GREEN),
            "por_cs_pago",
        )

    detail_section(
        df,
        key="notas",
        views={"Pendentes": pendente.sort_values("Valor", ascending=False)},
    )
