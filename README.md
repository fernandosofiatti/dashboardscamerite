# Dashboard de Cobranças

Aplicação Streamlit que gera dashboards a partir de dois formatos de CSV
conhecidos: **cobranças** (com vencimento/desconto) e **notas** (com
CS/autorização — a coluna vem no export como `PartnerManager`). O formato é
detectado automaticamente pelas colunas do arquivo importado.

Na tela inicial dá pra escolher entre subir **um arquivo** (dashboard daquele
formato específico) ou **os dois juntos** — nesse caso eles são cruzados pela
coluna `Nota` (presente nos dois exports), enriquecendo as cobranças com o
CS e habilitando gráficos de aging/inadimplência/desconto quebrados por CS.
Se houver cobranças sem nota correspondente no cruzamento, um aviso mostra
quantas ficaram de fora.

## Recursos

- **Filtros** na sidebar: período (intervalo de datas) + Status/Tipo/Forma/Cliente/CS.
  Linhas sem data permanecem visíveis ao filtrar por período.
- **KPIs**: totais a receber/recebido/cancelado/vencido (com contagens), taxa de
  inadimplência, ticket médio, prazo médio de recebimento (emissão → pagamento) e
  variação do recebido vs mês anterior.
- **Gráficos**: aging, distribuições por tipo/forma, recebido vs a receber por mês,
  top clientes e recortes por CS (no modo cruzado).
- **Dados detalhados**: expander no fim da página com as linhas filtradas (aba extra
  com as vencidas/pendentes) e download em CSV compatível com Excel (`;` e vírgula decimal).
- Valores aceitam tanto ponto decimal (`1234.56`) quanto formato brasileiro (`1.234,56`).

## Como rodar

Dê duplo clique em `iniciar.bat`, ou manualmente:

```
pip install -r requirements.txt
streamlit run app.py
```

Abre automaticamente em `http://localhost:8501`.

## Estrutura

```
app.py                    # upload (um ou dois arquivos), detecção de formato, dispatch
lib/common.py             # helpers compartilhados (formatação, gráficos, filtros, KPIs base)
lib/format_cobrancas.py   # KPIs e gráficos do CSV de cobranças
lib/format_notas.py       # KPIs e gráficos do CSV de notas
lib/format_combined.py    # cobranças + notas cruzados por Nota, com gráficos por CS
```

## Adicionando um novo formato de CSV

Crie um novo módulo em `lib/` com três funções (`detect`, `load`, `render`) no
mesmo padrão de `format_cobrancas.py`/`format_notas.py`, e adicione-o à lista
`FORMATS` em `app.py`.
