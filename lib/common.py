"""Shared helpers used by both CSV format modules."""

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

CHART_HEIGHT = 360
AGING_ORDER = ["A vencer", "Vencido 1-15d", "Vencido 16-30d", "Vencido 30d+", "Sem vencimento"]

# Severity scale for aging buckets (healthy green → critical red, gray for undated) —
# validated with the dataviz skill's validate_palette.js for CVD safety; the amber's
# lower contrast is relieved by the legend, white segment borders, hover and table view.
AGING_COLORS = {
    "A vencer": "#2E8B67",
    "Vencido 1-15d": "#C79A2E",
    "Vencido 16-30d": "#CC6633",
    "Vencido 30d+": "#B23A48",
    "Sem vencimento": "#8B84A0",
}

# Camerite brand palette (sampled from camerite.com, adjusted for contrast/CVD-safety —
# validated with the dataviz skill's validate_palette.js, all checks pass).
CAMERITE_PURPLE = "#7B48EA"
CAMERITE_INK = "#29184E"
CAMERITE_GREEN = "#2E8B67"
CATEGORICAL_COLORS = ["#7B48EA", "#0090D9", "#2E8B67", "#B85FD0", "#5A3AAE", "#2C93B4"]

# Neutral gray reserved for "no information" categories, so they don't steal a vivid
# hue from real entities (e.g. the big "Sem CS" slice/area).
NEUTRAL_CATEGORY = "#8B84A0"
_NEUTRAL_NAMES = {"Sem CS", "(vazio)", "Sem status", "Sem vencimento"}


def category_color_map(values) -> dict:
    """Fixed color per category (sorted order), with neutral gray for 'no info' buckets."""
    cmap, i = {}, 0
    for v in sorted(values):
        if v in _NEUTRAL_NAMES:
            cmap[v] = NEUTRAL_CATEGORY
        else:
            cmap[v] = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            i += 1
    return cmap

px.defaults.color_discrete_sequence = CATEGORICAL_COLORS

_FONT = dict(family="Segoe UI, sans-serif", color=CAMERITE_INK)

_CSS = """
<style>
/* ---- página ---- */
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; }

/* ---- cabeçalho ---- */
.fin-header {
    background: linear-gradient(120deg, #29184E 0%, #4A2BA0 55%, #7B48EA 100%);
    border-radius: 16px;
    padding: 26px 32px 22px 32px;
    margin-bottom: 1.2rem;
}
.fin-header h1 {
    color: #FFFFFF;
    font-size: 1.7rem;
    font-weight: 700;
    margin: 0;
    padding: 0;
}
.fin-header p {
    color: rgba(255, 255, 255, 0.78);
    font-size: 0.95rem;
    margin: 6px 0 0 0;
}

/* ---- títulos de seção ---- */
.fin-section {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.15rem;
    font-weight: 700;
    color: #29184E;
    margin: 0.6rem 0 0.4rem 0;
}
.fin-section::before {
    content: "";
    display: inline-block;
    width: 5px;
    height: 1.2em;
    border-radius: 3px;
    background: #7B48EA;
}

/* ---- cards de KPI ---- */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E4DCF7;
    border-radius: 14px;
    padding: 14px 16px 12px 16px;
    box-shadow: 0 1px 3px rgba(41, 24, 78, 0.07);
    /* mesma altura para todos os cards, com ou sem a linha de delta */
    min-height: 124px;
}
[data-testid="stMetricLabel"] p {
    color: #6B5E8C;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}
[data-testid="stMetricValue"] {
    color: #29184E;
    font-weight: 700;
    font-size: 1.45rem;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem; }

/* ---- sidebar ---- */
[data-testid="stSidebar"] {
    background: #F7F4FE;
    border-right: 1px solid #E4DCF7;
}

/* ---- expander / tabelas ---- */
[data-testid="stExpander"] details {
    border: 1px solid #E4DCF7;
    border-radius: 12px;
    background: #FFFFFF;
}

/* ---- divisor ---- */
hr { border-color: #E4DCF7; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="fin-header"><h1>{title}</h1>{sub}</div>', unsafe_allow_html=True)


def section_title(text: str):
    st.markdown(f'<div class="fin-section">{text}</div>', unsafe_allow_html=True)


def style_fig(fig, height: int = CHART_HEIGHT):
    fig.update_layout(
        height=height,
        font=_FONT,
        title_font=dict(family=_FONT["family"], color=CAMERITE_INK, size=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(size=12), title_text=""),
        margin=dict(l=10, r=10, t=45, b=10),
        separators=",.",  # números no padrão brasileiro (1.234,56)
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#D8CFF2", font=dict(family=_FONT["family"], color=CAMERITE_INK)),
    )
    # automargin keeps long tick labels (client/PM names, month labels) from being clipped
    # by the tight fixed margins; axis titles are redundant with the chart titles.
    fig.update_xaxes(gridcolor="#EDE7FA", linecolor="#D8CFF2", zerolinecolor="#D8CFF2", automargin=True, title_text="")
    fig.update_yaxes(gridcolor="#EDE7FA", linecolor="#D8CFF2", zerolinecolor="#D8CFF2", automargin=True, title_text="")
    return fig


def render_chart(fig, key: str):
    # theme=None keeps our own colors/fonts — otherwise Streamlit overrides Plotly Express'
    # discrete color sequence with its own default palette.
    st.plotly_chart(fig, width="stretch", theme=None, key=key)


def read_csv_any(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_number(series) -> pd.Series:
    if not isinstance(series, pd.Series):
        return pd.to_numeric(pd.Series(series), errors="coerce").fillna(0.0)
    s = series.astype(str).str.strip().str.replace("R$", "", regex=False).str.strip()
    has_comma = s.str.contains(",", na=False)
    if has_comma.any():
        # Decide o formato pelo último separador: em "1.234,56" a vírgula vem depois
        # do ponto (decimal brasileiro); em "1,234.56" é o contrário (milhar americano).
        sample = s[has_comma]
        br = (sample.str.rfind(",") > sample.str.rfind(".")).mean() >= 0.5
        if br:
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        else:
            s = s.str.replace(",", "", regex=False)
    out = pd.to_numeric(s, errors="coerce").fillna(0.0)
    out.index = series.index
    return out


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")


def format_currency(value: float) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def format_percent(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def month_label(series: pd.Series) -> pd.Series:
    return series.dt.to_period("M").astype(str)


def sidebar_multiselect(df: pd.DataFrame, column: str, label: str) -> list:
    if column not in df.columns:
        return []
    options = sorted(df[column].dropna().unique().tolist())
    return st.sidebar.multiselect(label, options, default=[])


def sidebar_date_range(df: pd.DataFrame, column: str, label: str):
    """Date-range picker in the sidebar; returns (start, end) Timestamps or None."""
    if column not in df.columns:
        return None
    valid = df[column].dropna()
    if valid.empty:
        return None
    min_d, max_d = valid.min().date(), valid.max().date()
    if min_d >= max_d:
        return None
    selected = st.sidebar.date_input(
        label,
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
        format="DD/MM/YYYY",
        help="Linhas sem data permanecem visíveis.",
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        return pd.Timestamp(selected[0]), pd.Timestamp(selected[1])
    return None


def apply_date_range(df: pd.DataFrame, column: str, date_range) -> pd.DataFrame:
    if not date_range or column not in df.columns:
        return df
    start, end = date_range
    mask = df[column].isna() | df[column].between(start, end)
    return df[mask]


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for column, selected in filters.items():
        if selected:
            mask &= df[column].isin(selected)
    return df[mask]


_MESES_ABREV = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun", 7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}


def _mes_label(p: pd.Period, com_ano: bool) -> str:
    return f"{_MESES_ABREV[p.month]}/{p.year % 100}" if com_ano else _MESES_ABREV[p.month]


def mom_delta(df: pd.DataFrame, date_col: str, value_col: str) -> str | None:
    """'+4,6% (jun vs mai)' comparing the two most recent CLOSED months, or None.
    The current calendar month is excluded — comparing a half-elapsed month against a
    full one would show a misleading drop."""
    if date_col not in df.columns:
        return None
    tmp = df.dropna(subset=[date_col])
    if tmp.empty:
        return None
    monthly = tmp.groupby(tmp[date_col].dt.to_period("M"))[value_col].sum().sort_index()
    monthly = monthly[monthly.index < pd.Timestamp.now().to_period("M")]
    if len(monthly) < 2 or monthly.iloc[-2] == 0:
        return None
    pct = (monthly.iloc[-1] - monthly.iloc[-2]) / monthly.iloc[-2] * 100
    if abs(pct) < 0.05:  # evita exibir um "-0,0%" confuso quando o mês está estável
        return None
    atual, anterior = monthly.index[-1], monthly.index[-2]
    com_ano = atual.year != anterior.year
    label = f"{_mes_label(atual, com_ano)} vs {_mes_label(anterior, com_ano)}"
    return f"{pct:+.1f}% ({label})".replace(".", ",")


def bar_by_category(df: pd.DataFrame, category_col: str, value_col: str, title: str, top_n: int | None = None):
    filled = df[category_col].fillna("(vazio)").replace("", "(vazio)")
    agg = (
        df.assign(**{category_col: filled})
        .groupby(category_col, as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=False)
    )
    if top_n:
        agg = agg.head(top_n)
    fig = px.bar(agg, x=category_col, y=value_col, title=title, color_discrete_sequence=[CAMERITE_PURPLE])
    fig.update_yaxes(tickprefix="R$ ")
    return style_fig(fig)


def bar_by_category_horizontal(
    df: pd.DataFrame, category_col: str, value_col: str, title: str, top_n: int = 10, color: str = CAMERITE_PURPLE
):
    filled = df[category_col].fillna("(vazio)").replace("", "(vazio)")
    agg = (
        df.assign(**{category_col: filled})
        .groupby(category_col, as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=True)
        .tail(top_n)
    )
    fig = px.bar(agg, x=value_col, y=category_col, orientation="h", title=title, color_discrete_sequence=[color])
    fig.update_xaxes(tickprefix="R$ ")
    return style_fig(fig, height=max(CHART_HEIGHT, 28 * len(agg)))


def pie_by_category(df: pd.DataFrame, category_col: str, value_col: str, title: str):
    filled = df[category_col].fillna("(vazio)").replace("", "(vazio)")
    agg = df.assign(**{category_col: filled}).groupby(category_col, as_index=False)[value_col].sum()
    fig = px.pie(
        agg,
        names=category_col,
        values=value_col,
        title=title,
        hole=0.45,
        color=category_col,
        color_discrete_map=category_color_map(agg[category_col].unique()),
    )
    fig.update_traces(marker=dict(line=dict(color="#FFFFFF", width=2)))
    return style_fig(fig)


def aging_bucket(vencimento, hoje) -> str:
    if pd.isna(vencimento):
        return "Sem vencimento"
    dias = (hoje - vencimento).days
    if dias <= 0:
        return "A vencer"
    if dias <= 15:
        return "Vencido 1-15d"
    if dias <= 30:
        return "Vencido 16-30d"
    return "Vencido 30d+"


def compute_kpis(df: pd.DataFrame) -> dict:
    """Base KPI figures shared by the cobranças-only and combined dashboards.
    Expects df with parsed Status/Valor columns, and optionally Desconto/Vencimento."""
    # "A receber" = only charges actually issued and pending. Rows with status
    # "Sem cobrança gerada"/"Sem status" go to their own bucket (and own KPI) so they
    # don't inflate Faturado/A Receber — in real exports they can be most of the value.
    pendente_like = df[df["Status"] == "Pendente"]
    pago = df[df["Status"] == "Pago"]
    cancelado = df[df["Status"] == "Cancelado"]
    sem_cobranca = df[~df["Status"].isin(["Pendente", "Pago", "Cancelado"])]

    total_pendente = pendente_like["Valor"].sum()
    total_pago = pago["Valor"].sum()
    total_cancelado = cancelado["Valor"].sum()
    total_sem_cobranca = sem_cobranca["Valor"].sum()
    # Faturado = tudo que foi emitido e não cancelado (recebido + pendente).
    total_faturado = total_pendente + total_pago
    n_faturado = len(pendente_like) + len(pago)
    ticket_medio = pago["Valor"].mean() if len(pago) else 0.0
    total_desconto = df["Desconto"].abs().sum() if "Desconto" in df.columns else None

    hoje = pd.Timestamp(datetime.now().date())
    taxa_inadimplencia = None
    vencido = pendente_like.iloc[0:0]
    if "Vencimento" in df.columns:
        vencido = pendente_like[pendente_like["Vencimento"] < hoje]
        taxa_inadimplencia = (vencido["Valor"].sum() / total_pendente * 100) if total_pendente else 0.0

    # Prazo médio de recebimento (DSO): dias entre emissão e pagamento das cobranças pagas.
    prazo_medio = None
    if "Pago em" in df.columns and "Emissão" in df.columns:
        com_datas = pago.dropna(subset=["Pago em", "Emissão"])
        if len(com_datas):
            prazo_medio = (com_datas["Pago em"] - com_datas["Emissão"]).dt.days.mean()

    return {
        "pendente_like": pendente_like,
        "pago": pago,
        "cancelado": cancelado,
        "sem_cobranca": sem_cobranca,
        "total_sem_cobranca": total_sem_cobranca,
        "vencido": vencido,
        "total_pendente": total_pendente,
        "total_pago": total_pago,
        "total_cancelado": total_cancelado,
        "total_faturado": total_faturado,
        "n_faturado": n_faturado,
        "total_vencido": vencido["Valor"].sum(),
        "ticket_medio": ticket_medio,
        "total_desconto": total_desconto,
        "taxa_inadimplencia": taxa_inadimplencia,
        "prazo_medio": prazo_medio,
        "hoje": hoje,
    }


def aging_chart(pendente_like: pd.DataFrame, hoje, title: str, color_col: str | None = None):
    aging = pendente_like.copy()
    aging["Faixa"] = aging["Vencimento"].apply(lambda v: aging_bucket(v, hoje))
    group_cols = ["Faixa"] + ([color_col] if color_col else [])
    agg = aging.groupby(group_cols, as_index=False)["Valor"].sum()
    agg["Faixa"] = pd.Categorical(agg["Faixa"], categories=AGING_ORDER, ordered=True)
    agg = agg.sort_values("Faixa")
    if color_col:
        color_kwargs = {"color_discrete_map": category_color_map(agg[color_col].unique())}
    else:
        color_kwargs = {"color_discrete_sequence": [CAMERITE_PURPLE]}

    if color_col:
        # Aging buckets are an ordered progression (a vencer → vencido 30d+), so a stacked
        # area reads as a smoother trend than blocky stacked bars — and holds up better with
        # many series stacked (e.g. one per CS).
        fig = px.area(agg, x="Faixa", y="Valor", color=color_col, title=title, **color_kwargs)
        for trace in fig.data:
            trace.fillcolor = trace.line.color  # pin the fill before the line color is overwritten below
            trace.line.update(width=1.5, color="white")
    else:
        fig = px.bar(agg, x="Faixa", y="Valor", title=title, **color_kwargs)

    fig.update_yaxes(tickprefix="R$ ")
    return style_fig(fig)


def top_clients_aging_chart(pendente_like: pd.DataFrame, hoje, category_col: str, title: str, top_n: int = 10):
    """Top-N clients by open value, each bar stacked by aging bucket (with % share on hover)."""
    tmp = pendente_like.copy()
    tmp[category_col] = tmp[category_col].fillna("(vazio)").replace("", "(vazio)")
    tmp["Faixa"] = tmp["Vencimento"].apply(lambda v: aging_bucket(v, hoje))

    totals = tmp.groupby(category_col)["Valor"].sum().sort_values(ascending=True).tail(top_n)
    agg = tmp[tmp[category_col].isin(totals.index)].groupby([category_col, "Faixa"], as_index=False)["Valor"].sum()
    agg["Pct"] = agg["Valor"] / agg[category_col].map(totals) * 100

    fig = px.bar(
        agg,
        x="Valor",
        y=category_col,
        color="Faixa",
        orientation="h",
        title=title,
        color_discrete_map=AGING_COLORS,
        # totals is ascending; reversed here so the biggest client lands at the top of the chart
        category_orders={"Faixa": AGING_ORDER, category_col: totals.index.tolist()[::-1]},
        custom_data=["Pct"],
    )
    fig.update_traces(
        marker_line=dict(color="#FFFFFF", width=1),
        hovertemplate="%{y}<br>R$ %{x:,.2f} — %{customdata[0]:.1f}% do total em aberto<extra>%{fullData.name}</extra>",
    )
    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", yanchor="top", y=-0.08, x=0, font=dict(size=11)),
    )
    fig.update_xaxes(tickprefix="R$ ")
    return style_fig(fig, height=max(CHART_HEIGHT, 32 * len(totals) + 60))


def bar_month_recebido_pendente(df: pd.DataFrame, date_col: str, title: str):
    """Grouped bars per month: what was received vs what is still open (only issued charges)."""
    tmp = df[df["Status"].isin(["Pago", "Pendente"])].dropna(subset=[date_col]).copy()
    if tmp.empty:
        return None
    tmp["Situação"] = tmp["Status"].eq("Pago").map({True: "Recebido", False: "A Receber"})
    tmp["_p"] = tmp[date_col].dt.to_period("M")
    agg = tmp.groupby(["_p", "Situação"], as_index=False)["Valor"].sum().sort_values("_p")
    agg["Mês"] = agg["_p"].dt.strftime("%m/%Y")
    ordem = agg.drop_duplicates("_p").sort_values("_p")["Mês"].tolist()
    fig = px.bar(
        agg,
        x="Mês",
        y="Valor",
        color="Situação",
        barmode="group",
        title=title,
        color_discrete_map={"Recebido": CAMERITE_GREEN, "A Receber": CAMERITE_PURPLE},
        category_orders={"Situação": ["Recebido", "A Receber"]},
    )
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=ordem, title=None)
    fig.update_yaxes(tickprefix="R$ ", title=None)
    return style_fig(fig)


def detail_section(df: pd.DataFrame, key: str, views: dict | None = None):
    """Expander with the filtered rows behind the charts + CSV download (Excel-friendly)."""
    all_views = {"Todas as linhas": df}
    for name, data in (views or {}).items():
        all_views[name] = data

    with st.expander(f"📋 Dados detalhados — {len(df)} linhas"):
        tabs = st.tabs([f"{name} ({len(data)})" for name, data in all_views.items()])
        for tab, (name, data) in zip(tabs, all_views.items()):
            with tab:
                col_config = {}
                for c in data.columns:
                    if pd.api.types.is_datetime64_any_dtype(data[c]):
                        col_config[c] = st.column_config.DatetimeColumn(c, format="DD/MM/YYYY")
                    elif pd.api.types.is_numeric_dtype(data[c]):
                        col_config[c] = st.column_config.NumberColumn(c, format="R$ %.2f")
                st.dataframe(data, width="stretch", hide_index=True, height=380, column_config=col_config)
                csv = data.to_csv(index=False, sep=";", decimal=",", date_format="%d/%m/%Y").encode("utf-8-sig")
                slug = name.lower().replace(" ", "_")
                st.download_button(
                    "⬇️ Baixar CSV",
                    csv,
                    file_name=f"{slug}.csv",
                    mime="text/csv",
                    key=f"{key}_{slug}_dl",
                )
