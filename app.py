import streamlit as st

from lib import format_cobrancas, format_combined, format_notas
from lib.common import inject_css, page_header, read_csv_any

st.set_page_config(page_title="Dashboards CS", page_icon="💰", layout="wide")
inject_css()
st.markdown(
    """
    <style>
    /* Esconde o que o Streamlit Cloud injeta apontando pro fonte.
       Cosmético apenas - o repo continua público no GitHub. */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stAppDeployButton"],
    .stAppDeployButton { display: none !important; }
    [class*="viewerBadge"] { display: none !important; }
    .stApp a[href^="https://github.com"],
    .stApp a[href^="https://share.streamlit.io"],
    .stApp a[href^="https://streamlit.io"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
FORMATS = [format_cobrancas, format_notas]

page_header(
    "💰 Dashboard Camerite - Time CS",
    "Importe os exports de cobranças e notas para acompanhar recebíveis, inadimplência e a carteira por CS.",
)

modo = st.radio(
    "Como deseja importar?",
    ["📄 Um arquivo (cobranças OU notas)", "🔗 Cobranças + Notas (cruzado)"],
    horizontal=True,
)

if modo.startswith("📄"):
    uploaded = st.file_uploader(
        "Faça upload do CSV de cobranças ou de notas para gerar o dashboard", type=["csv"]
    )
    if uploaded is None:
        st.info("Envie um arquivo CSV para começar (formato 'cobranças' ou 'notas').")
        st.stop()

    raw = read_csv_any(uploaded)
    fmt = next((f for f in FORMATS if f.detect(list(raw.columns))), None)

    if fmt is None:
        st.error("Não reconheci esse formato de CSV. Colunas encontradas: " + ", ".join(raw.columns))
        st.stop()

    df = fmt.load(raw)
    st.caption(f"{len(df)} linhas importadas")
    fmt.render(df)

else:
    col1, col2 = st.columns(2)
    with col1:
        cob_file = st.file_uploader("CSV de Cobranças", type=["csv"], key="cob_upload")
    with col2:
        notas_file = st.file_uploader("CSV de Notas", type=["csv"], key="notas_upload")

    if cob_file is None or notas_file is None:
        st.info("Envie os dois arquivos para gerar o dashboard cruzado.")
        st.stop()

    cob_raw = read_csv_any(cob_file)
    notas_raw = read_csv_any(notas_file)

    if not format_cobrancas.detect(list(cob_raw.columns)):
        st.error("O arquivo em 'CSV de Cobranças' não parece ter o formato esperado (falta a coluna Vencimento).")
        st.stop()
    if not format_notas.detect(list(notas_raw.columns)):
        st.error("O arquivo em 'CSV de Notas' não parece ter o formato esperado (falta a coluna PartnerManager).")
        st.stop()

    df = format_combined.load(cob_raw, notas_raw)
    st.caption(f"{len(df)} linhas de cobranças, cruzadas com {len(notas_raw)} notas")

    sem_nota = df.attrs.get("cobrancas_sem_nota", 0)
    if sem_nota:
        st.warning(
            f"⚠️ {sem_nota} de {len(df)} cobranças não encontraram nota correspondente no cruzamento "
            "e aparecem como 'Sem CS'. Confira se os dois exports cobrem o mesmo período."
        )

    format_combined.render(df)
