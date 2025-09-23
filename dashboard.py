# dashboard.py (v1.58.0 - Adição de Treemaps de Fundos e Gestores)
import os
import streamlit as st
import pandas as pd
import sqlite3
import base64
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

# --- DICIONÁRIO DE CONFIGURAÇÃO DOS PLANOS ---
CONFIGURACOES_PLANOS = {
    "INVESTPREV": {
        "titulo": "Dashboard Consolidado (InvestPrev)",
        "filtro_investimentos": "003 - INVESTPREV",  # Nome na tabela investimentos e imoveis
        "filtro_ativos": "INVESTPREV"              # Nome na tabela Ativos (rentabilidade)
    },
    "PLANO A": {
        "titulo": "Dashboard Consolidado (Plano A)",
        "filtro_investimentos": "001 - PLANO A - BD", # VERIFICAR ESTE NOME
        "filtro_ativos": "PLANO A - BD"
    },
    "VIDAPREV": {
        "titulo": "Dashboard Consolidado (VidaPrev)",
        "filtro_investimentos": "004 - VIDAPREV", # VERIFICAR ESTE NOME
        "filtro_ativos": "VIDAPREV"
    },
    "ASSISTENCIAL": {
        "titulo": "Dashboard Consolidado (Plano Assistencial)",
        "filtro_investimentos": "009 - PLANO ASSISTENCIAL", # VERIFICAR ESTE NOME
        "filtro_ativos": "PLANO ASSISTENCIAL"
    },
    "PGA": {
        "titulo": "Dashboard Consolidado (PGA)",
        "filtro_investimentos": "500 - PGA GERAL", # VERIFICAR ESTE NOME
        "filtro_ativos": "PGA GERAL"
    }
}

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Investimentos",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- FUNÇÃO PARA CARREGAR IMAGEM ---
@st.cache_data
def get_image_as_base64(file):
    if not os.path.exists(file):
        return None
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- FUNÇÃO AUXILIAR PARA FORMATAR NÚMEROS GRANDES ---
def formatar_numero_br(num):
    if pd.isna(num):
        return ""
    if abs(num) >= 1_000_000_000:
        return f'{num / 1_000_000_000:.3f} B'.replace('.', ',')
    if abs(num) >= 1_000_000:
        return f'{num / 1_000_000:.3f} M'.replace('.', ',')
    if abs(num) >= 1_000:
        return f'{num / 1_000:.3f} K'.replace('.', ',')
    return f'{num:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")


# --- FUNÇÃO PARA INJETAR CSS CUSTOMIZADO (VERSÃO FINAL SEM BORDA) ---
def carregar_css():
    SIDEBAR_WIDTH = 260
    logo_base64 = get_image_as_base64("logo.png")

    logo_css = ""
    if logo_base64:
        logo_css = f"""
        [data-testid="stSidebar"] [data-testid="stButton"] {{
            margin-top: -65px;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] > button {{
            display: block;
            background-image: url(data:image/png;base64,{logo_base64});
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            background-color: transparent;
            border: none;
            width: {SIDEBAR_WIDTH - 20}px;
            height: 80px;
            cursor: pointer;
            margin: 0 auto;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] > button > div p {{
            font-size: 0;
        }}
        """

    st.markdown(f"""
    <style>
        /* --- SIDEBAR E GERAL (CÓDIGO SEM ALTERAÇÃO) --- */
        [data-testid="stSidebar"] {{
            width: {SIDEBAR_WIDTH}px; min-width: {SIDEBAR_WIDTH}px; max-width: {SIDEBAR_WIDTH}px;
        }}
        {logo_css}
        .main .block-container {{
            background-color: #f0f2f6; padding-top: 2rem; padding-bottom: 2rem;
        }}
        [data-testid="stSidebar"] {{ background-color: #6aa2ff; }}
        [data-testid="stSidebarNavCollapseButton"] {{ display: none; }}
        [data-testid="stSidebar"] div[role="radiogroup"] {{
            display: flex; flex-direction: column; align-items: stretch; width: 100%;
        }}

        /* --- BOTÕES DA SIDEBAR (CÓDIGO SEM ALTERAÇÃO) --- */
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{ display: none; }}
        [data-testid="stSidebar"] div[role="radiogroup"] > label {{
            display: block; margin: 5px 15px 6px 15px; border-radius: 10px;
            width: calc(100% - 30px) !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] input {{
            position: absolute !important; left: -9999px !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div {{
            display: flex; align-items: center; justify-content: center; padding: 8px 18px;
            height: 40px; border-radius: 10px; background-color: #1161e6; color: #ffffff;
            cursor: pointer; transition: background-color 0.18s ease, box-shadow 0.18s ease;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div * {{ font-size: 16px !important; font-weight: 600 !important; }}
        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover > div {{ background-color: #4185f4; }}
        [data-testid="stSidebar"] div[role="radiogroup"] input:checked + div {{
            background-color: #ffffff !important; color: #1161e6 !important;
            box-shadow: inset 6px 0 0 0 #1161e6, 0 2px 4px rgba(0,0,0,0.06) !important;
            height: 53px !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] input:checked + div * {{ color: #1161e6 !important; }}

        /* --- KPI & VAR CARDS (CÓDIGO SEM ALTERAÇÃO) --- */
        .kpi-card {{
            background-color: #ffffff; padding: 20px; border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); text-align: center;
            border-left: 6px solid #1161e6; position: relative;
        }}
        .kpi-title {{ font-size: 16px; font-weight: 600; color: #415a77; margin-bottom: 5px; }}
        .kpi-value {{ font-size: 32px; font-weight: 700; color: #0d1b2a; }}
        .var-card {{
            background-color: #ffffff; padding: 10px; border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); text-align: center;
            border-bottom: 4px solid;
        }}
        .var-title {{ font-size: 12px; color: #415a77; margin-bottom: 2px; }}
        .var-value {{ font-size: 20px; font-weight: 700; }}
        .green {{ color: #70e000; border-color: #70e000; }}
        .red {{ color: #d00000; border-color: #d00000; }}

        /* --- EFEITO DE SOMBRA NO GRÁFICO (CÓDIGO SEM ALTERAÇÃO) --- */
        .stPlotlyChart > div {{ position: relative; }}
        .stPlotlyChart > div::before {{
            content: ""; position: absolute; top: -8px; left: -8px;
            right: -8px; bottom: -8px; background: #ffffff;
            border-radius: 12px; box-shadow: 0 12px 36px rgba(13,27,42,0.14);
            z-index: 0; pointer-events: none;
        }}
        .stPlotlyChart > div .plotly-graph-div,
        .stPlotlyChart > div .plotly-graph-div * {{ position: relative; z-index: 1; }}

        /* --- ÍCONE DE INFORMAÇÃO (CÓDIGO SEM ALTERAÇÃO) --- */
        .info-icon {{
            position: absolute; top: 10px; right: 15px; width: 22px; height: 22px;
            background-color: #6aa2ff; color: white; border-radius: 50%;
            text-align: center; font-size: 15px; line-height: 22px; cursor: help;
            font-weight: bold; font-family: 'Georgia', serif;
        }}
        .info-icon .tooltip-text {{
            visibility: hidden; width: 250px; background-color: #333;
            color: #fff; text-align: center; border-radius: 6px; padding: 8px;
            position: absolute; z-index: 1; bottom: 125%; left: 50%;
            margin-left: -125px; opacity: 0; transition: opacity 0.3s;
            font-size: 13px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        .info-icon:hover .tooltip-text {{ visibility: visible; opacity: 1; }}

        /* --- ESTILO CORRIGIDO PARA O SLIDER --- */
        /* Este seletor navega a partir do container principal do slider (data-testid="stSlider"),
        passando por seus divs filhos até encontrar o primeiro div interno, que representa
        a barra preenchida. O uso de '>' torna o seletor mais específico.
        O !important é crucial para sobrescrever o estilo inline do Streamlit.
        */
        div[data-testid="stSlider"] > div > div > div:first-child {{
            background: #b7b7b7 !important;
        }}

        /* Linha do slider (trilho vazio) */
        div[data-testid="stSlider"] .st-e0 {{
            background: #1161e6 !important;
        }}

        /* 3. Estiliza a bolinha do slider */
        div[data-testid="stSlider"] .st-emotion-cache-1dj3ksd {{
            background: #ffffff !important;
            border: 4px solid #1161e6 !important;
        }}

        /* Número acima da bolinha */
        div[data-testid="stSliderThumbValue"] {{
            color: #1161e6 !important;
        }}
    </style>
    """, unsafe_allow_html=True)


# --- FUNÇÕES DE DADOS ---
NOME_BANCO_DADOS = 'meu_dashboard.db'


# --- FUNÇÃO PARA CARREGAR E CACHEAR OS DADOS ---
@st.cache_data
def carregar_dados():
    try:
        conn = sqlite3.connect(NOME_BANCO_DADOS)

        # Query para investimentos
        query_investimentos = "SELECT inv.*, cad.gestor FROM investimentos inv LEFT JOIN cadastro_fundos cad ON inv.codigo_isin_fundo = cad.codigo_isin"
        df_investimentos = pd.read_sql(query_investimentos, conn)
        if not df_investimentos.empty:
            df_investimentos['data_posicao'] = pd.to_datetime(df_investimentos['data_posicao'])
            df_investimentos['valor_total'] = pd.to_numeric(df_investimentos['valor_total'], errors='coerce')
            df_investimentos['gestor'] = df_investimentos['gestor'].fillna('Não Cadastrado')

        # Query para imóveis
        query_imoveis = "SELECT * FROM imoveis_emprestimos"
        df_imoveis = pd.read_sql_query(query_imoveis, conn)
        if not df_imoveis.empty:
            df_imoveis['data_posicao'] = pd.to_datetime(df_imoveis['data_posicao'])
            df_imoveis['valor_total'] = pd.to_numeric(df_imoveis['valor_total'], errors='coerce')

        # Query para rentabilidade dos ativos
        query_ativos = "SELECT * FROM Ativos"
        df_ativos = pd.read_sql_query(query_ativos, conn)
        if not df_ativos.empty:
            df_ativos['data_posicao'] = pd.to_datetime(df_ativos['data_posicao'])

        # --- ADIÇÃO DA NOVA TABELA ---
        query_indices = "SELECT * FROM indices_taxas"
        df_indices = pd.read_sql_query(query_indices, conn)
        if not df_indices.empty:
            df_indices['data_posicao'] = pd.to_datetime(df_indices['data_posicao'])
        # --- FIM DA ADIÇÃO ---

        conn.close()

        # Retorna os quatro DataFrames
        return df_investimentos, df_imoveis, df_ativos, df_indices

    except Exception as e:
        st.error(f"Erro ao conectar ou ler o banco de dados: {e}")
        # Retorna quatro DataFrames vazios em caso de erro
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# --- FUNÇÕES DE PÁGINA ---
def pagina_home():
    st.title("Dashboard Consolidado (Agros)")

    df_investimentos, df_imoveis, df_ativos, df_indices = carregar_dados()

    if df_investimentos.empty and df_imoveis.empty:
        st.warning("Nenhum dado encontrado.")
        return

    # --- KPIs, Evolução e Variação (CÓDIGO SEM ALTERAÇÃO) ---
    data_mais_recente = (pd.concat([df_investimentos['data_posicao'], df_imoveis['data_posicao']])
                         .dropna().max())
    patrimonio_consolidado = (
            df_investimentos[df_investimentos['data_posicao'] == data_mais_recente]['valor_total'].sum() +
            df_imoveis[df_imoveis['data_posicao'] == data_mais_recente]['valor_total'].sum())
    patrimonio_formatado = f"R$ {patrimonio_consolidado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data_formatada = data_mais_recente.strftime('%d/%m/%Y')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'''<div class="kpi-card">
                   <div class="kpi-title">PATRIMÔNIO CONSOLIDADO</div>
                   <div class="kpi-value">{patrimonio_formatado}</div>
                   <div class="info-icon">i
                       <span class="tooltip-text">
                           Soma dos valores em carteiras de Investimentos, Imóveis e Operações com Participantes.
                       </span>
                   </div>
               </div>''',
            unsafe_allow_html=True)
    with col2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">DATA DE POSIÇÃO</div><div class="kpi-value">{data_formatada}</div></div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Evolução do Patrimônio Consolidado")

    df_evol_inv = df_investimentos.groupby('data_posicao')['valor_total'].sum().reset_index().rename(
        columns={'valor_total': 'valor_investimentos'})
    df_evol_imo = df_imoveis.groupby('data_posicao')['valor_total'].sum().reset_index().rename(
        columns={'valor_total': 'valor_imoveis'})
    df_evolucao = pd.merge(df_evol_inv, df_evol_imo, on='data_posicao', how='outer').fillna(0)
    df_evolucao['Total'] = df_evolucao['valor_investimentos'] + df_evolucao['valor_imoveis']

    fig_evol = px.line(df_evolucao, x='data_posicao', y='Total', line_shape='spline')
    fig_evol.update_traces(
        line=dict(color='#1161e6', width=3),
        marker=dict(size=8, color='#4361f2', line=dict(width=1, color='#ffffff')),
        hovertemplate='<b>Data:</b> %{x|%d/%m/%Y}<br><b>Patrimônio:</b> R$ %{y:,.2f}<extra></extra>',
        text=df_evolucao['Total'].apply(formatar_numero_br),
        mode='lines+markers+text',
        textposition='top center',
        textfont=dict(size=16, color='#001f3f')
    )
    meses_map_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out',
                    11: 'Nov', 12: 'Dez'}
    tick_values = df_evolucao['data_posicao']
    tick_labels = [f"{meses_map_pt[d.month]}/{d.year}" for d in tick_values]
    fig_evol.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='<b>Data</b>', gridcolor='#e0e0e0', tickvals=tick_values, ticktext=tick_labels),
        yaxis=dict(title='<b>Patrimônio (R$)</b>', gridcolor='#e0e0e0', tickformat=',.0f'),
        margin=dict(l=40, r=40, t=40, b=40), hovermode="x unified",
        hoverlabel = dict(
            bgcolor="white",
            font_size=17,
            font_family="sans-serif"
        )
    )

    st.plotly_chart(fig_evol, use_container_width=True)
    st.markdown("---")

    st.subheader("Análise de Variação Patrimonial")
    datas_disponiveis_dt = sorted(pd.to_datetime(df_evolucao['data_posicao'].unique()))
    meses_pt_full = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho',
                     8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    opcoes_map = {f"{meses_pt_full[d.month]}/{d.year}": d for d in datas_disponiveis_dt}
    opcoes_labels = list(opcoes_map.keys())
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        label_inicial = st.selectbox("Selecione a Data Inicial:", opcoes_labels, index=0)
    with col_data2:
        label_final = st.selectbox("Selecione a Data Final:", opcoes_labels, index=len(opcoes_labels) - 1)
    data_inicial = opcoes_map[label_inicial]
    data_final = opcoes_map[label_final]
    if data_inicial >= data_final:
        st.warning("A Data Inicial deve ser anterior à Data Final para calcular a variação.")
    else:
        valor_inicial = df_evolucao.loc[df_evolucao['data_posicao'] == data_inicial, 'Total'].iloc[0]
        valor_final = df_evolucao.loc[df_evolucao['data_posicao'] == data_final, 'Total'].iloc[0]
        variacao_rs = valor_final - valor_inicial
        variacao_pct = (valor_final / valor_inicial - 1) * 100 if valor_inicial != 0 else 0
        sinal_rs = "+" if variacao_rs >= 0 else ""
        sinal_pct = "+" if variacao_pct >= 0 else ""
        cor_variacao = "green" if variacao_rs >= 0 else "red"
        variacao_rs_f = f"R$ {variacao_rs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        col_var1, col_var2 = st.columns(2)
        with col_var1:
            st.markdown(
                f'<div class="var-card {cor_variacao}"><div class="var-title">VARIAÇÃO (R$)</div><div class="var-value">{sinal_rs}{variacao_rs_f}</div></div>',
                unsafe_allow_html=True)
        with col_var2:
            st.markdown(
                f'<div class="var-card {cor_variacao}"><div class="var-title">VARIAÇÃO (%)</div><div class="var-value">{sinal_pct}{variacao_pct:.2f}%</div></div>',
                unsafe_allow_html=True)
    st.markdown("---")

    # --- ANÁLISE DA CARTEIRA DE INVESTIMENTOS (CÓDIGO SEM ALTERAÇÃO) ---
    st.subheader("Análise da Carteira de Investimentos")
    datas_analise = sorted(
        pd.to_datetime(pd.concat([df_investimentos['data_posicao'], df_imoveis['data_posicao']]).dropna().unique()),
        reverse=True)
    opcoes_map_analise = {f"{meses_pt_full[d.month]}/{d.year}": d for d in datas_analise}
    label_selecionada = st.selectbox("Selecione a data para análise da composição:", list(opcoes_map_analise.keys()),
                                     key="composicao_data")

    if not label_selecionada: return
    data_selecionada = opcoes_map_analise[label_selecionada]

    df_inv_filtrado = df_investimentos[df_investimentos['data_posicao'] == data_selecionada]
    df_imo_filtrado = df_imoveis[df_imoveis['data_posicao'] == data_selecionada]
    patrimonio_na_data = df_inv_filtrado['valor_total'].sum() + df_imo_filtrado['valor_total'].sum()

    mapa_nomes = {'001 - PLANO A - BD': 'Plano A', '003 - INVESTPREV': 'InvestPrev', '004 - VIDAPREV': 'VidaPrev',
                  '009 - PLANO ASSISTENCIAL': 'Assistencial', '500 - PGA GERAL': 'PGA'}
    cores_azuis = ['#0d47a1', '#1976d2', '#42a5f5', '#90caf9', '#bbdefb', '#e3f2fd']

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 1. ANÁLISE POR PLANOS (CÓDIGO SEM ALTERAÇÃO) ---
    col_plano1, col_plano2 = st.columns([0.8, 1.2])
    with col_plano1:
        st.markdown("##### Distribuição por Planos")
        df_planos_full = pd.concat(
            [df_inv_filtrado[['nome_plano', 'valor_total']], df_imo_filtrado[['nome_plano', 'valor_total']]])
        df_planos_agg = df_planos_full.groupby('nome_plano')['valor_total'].sum().reset_index()
        df_planos_agg['Plano'] = df_planos_agg['nome_plano'].map(mapa_nomes).fillna(df_planos_agg['nome_plano'])

        fig_rosca_plano = go.Figure(data=[
            go.Pie(labels=df_planos_agg['Plano'], values=df_planos_agg['valor_total'], hole=.4, textinfo='percent',
                   textfont_size=17, hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
                   marker=dict(colors=cores_azuis, line=dict(color='#ffffff', width=2)))])
        fig_rosca_plano.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                                      margin=dict(t=0, b=0, l=0, r=0), height=400,

                                      # --- ADICIONE ESTE BLOCO ---
                                      hoverlabel=dict(
                                          bgcolor="white",
                                          font_size=16,
                                          font_family="sans-serif"
                                      )
                                      # ---------------------------
                                      )
        st.plotly_chart(fig_rosca_plano, use_container_width=True)
    with col_plano2:
        df_tabela_plano = df_planos_agg[['Plano', 'valor_total']].copy().sort_values(by='valor_total', ascending=False)
        total_planos = df_tabela_plano['valor_total'].sum()
        if total_planos > 0:
            df_tabela_plano['%'] = (df_tabela_plano['valor_total'] / total_planos) * 100
        else:
            df_tabela_plano['%'] = 0
        df_tabela_plano['valor_total_str'] = df_tabela_plano['valor_total'].apply(lambda x: f"R$ {x:,.2f}")
        df_tabela_plano['%_str'] = df_tabela_plano['%'].apply(lambda x: f"{x:.2f}%")

        tabela_html_plano = """<table style="width:100%; border-collapse: collapse;">
                            <tr style="border-bottom: 2px solid #6aa2ff; color: #0d47a1;">
                                <th style="text-align:left; padding: 8px;">Plano</th>
                                <th style="text-align:right; padding: 8px;">Valor (R$)</th>
                                <th style="text-align:right; padding: 8px;">%</th>
                            </tr>"""
        for index, row in df_tabela_plano.iterrows():
            tabela_html_plano += f'<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 8px;">{row["Plano"]}</td><td style="text-align:right; padding: 8px;">{row["valor_total_str"]}</td><td style="text-align:right; padding: 8px;">{row["%_str"]}</td></tr>'
        tabela_html_plano += f"""<tr style="background-color: #f0f2f6; border-top: 2px solid #6aa2ff;">
                                <td style="padding: 10px; font-weight: bold;">Total</td>
                                <td style="text-align:right; padding: 10px; font-weight: bold;">R$ {total_planos:,.2f}</td>
                                <td style="text-align:right; padding: 10px; font-weight: bold;">100.00%</td>
                            </tr></table>"""
        components.html(tabela_html_plano, height=400, scrolling=True)

    st.markdown("##### Evolução da Distribuição por Planos")
    df_planos_evol = pd.concat([df_investimentos[['data_posicao', 'nome_plano', 'valor_total']],
                                df_imoveis[['data_posicao', 'nome_plano', 'valor_total']]])
    df_planos_evol_agg = df_planos_evol.groupby(['data_posicao', 'nome_plano'])['valor_total'].sum().unstack().fillna(0)
    df_planos_evol_pct = df_planos_evol_agg.div(df_planos_evol_agg.sum(axis=1), axis=0) * 100
    df_planos_evol_pct.columns = [mapa_nomes.get(col, col) for col in df_planos_evol_pct.columns]
    df_planos_evol_val = df_planos_evol_agg.copy()
    df_planos_evol_val.columns = [mapa_nomes.get(col, col) for col in df_planos_evol_val.columns]

    fig_evol_planos = go.Figure()
    planos_rotulo_cima = ['VidaPrev', 'Plano A', 'InvestPrev']
    planos_rotulo_meio = ['PGA', 'Assistencial']

    for plano in df_planos_evol_pct.columns:
        mode = 'lines'
        text_position = None
        if plano in planos_rotulo_cima:
            mode = 'lines+text'
            text_position = 'top center'
        elif plano in planos_rotulo_meio:
            mode = 'lines+text'
            text_position = 'middle center'

        fig_evol_planos.add_trace(go.Scatter(
            x=df_planos_evol_pct.index, y=df_planos_evol_pct[plano], name=plano, mode=mode,
            line_shape='spline', customdata=df_planos_evol_val[plano],
            text=[f'{y:.1f}%' for y in df_planos_evol_pct[plano]], textposition=text_position,
            textfont=dict(size=12, color="#000000"),
            hovertemplate='<b>%{x|%B de %Y}</b><br>%{data.name}: %{y:.2f}%<br>Valor: R$ %{customdata:,.2f}<extra></extra>'
        ))

    evol_tick_values_planos = df_planos_evol_pct.index
    evol_tick_labels_planos = [f"{meses_map_pt[d.month]}/{d.year}" for d in evol_tick_values_planos]
    fig_evol_planos.update_layout(hovermode='x unified', yaxis_ticksuffix='%', legend_title_text='',
                                  colorway=cores_azuis,
                                  xaxis=dict(tickvals=evol_tick_values_planos, ticktext=evol_tick_labels_planos),
                                  margin=dict(t=20, b=40, l=40, r=20),

                                  # --- ADICIONE ESTE BLOCO ---
                                  hoverlabel=dict(
                                      bgcolor="white",
                                      font_size=16,
                                      font_family="sans-serif"
                                  )
                                  # ---------------------------
                                  )
    st.plotly_chart(fig_evol_planos, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. ANÁLISE POR SEGMENTOS (CÓDIGO SEM ALTERAÇÃO) ---
    col_seg1, col_seg2 = st.columns([0.8, 1.2])
    with col_seg1:
        st.markdown("##### Distribuição por Segmentos")
        df_seg_inv = df_inv_filtrado.groupby('segmento')['valor_total'].sum().reset_index()
        df_seg_imo = df_imo_filtrado.groupby('segmento')['valor_total'].sum().reset_index()
        df_segmentos_full = pd.concat([df_seg_inv, df_seg_imo], ignore_index=True)

        fig_rosca_seg = go.Figure(data=[
            go.Pie(labels=df_segmentos_full['segmento'], values=df_segmentos_full['valor_total'], hole=.4,
                   textinfo='percent', textfont_size=17,
                   hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
                   marker=dict(colors=cores_azuis, line=dict(color='#ffffff', width=2)))])
        fig_rosca_seg.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                                    margin=dict(t=0, b=0, l=0, r=0), height=400,

                                    # --- ADICIONE ESTE BLOCO ---
                                    hoverlabel=dict(
                                        bgcolor="white",
                                        font_size=16,
                                        font_family="sans-serif"
                                    )
                                    # ---------------------------
                                    )
        st.plotly_chart(fig_rosca_seg, use_container_width=True)
    with col_seg2:
        df_tabela_seg = df_segmentos_full.copy().sort_values(by='valor_total', ascending=False)
        total_segmentos = df_tabela_seg['valor_total'].sum()
        if total_segmentos > 0:
            df_tabela_seg['%'] = (df_tabela_seg['valor_total'] / total_segmentos) * 100
        else:
            df_tabela_seg['%'] = 0
        df_tabela_seg['valor_total_str'] = df_tabela_seg['valor_total'].apply(lambda x: f"R$ {x:,.2f}")
        df_tabela_seg['%_str'] = df_tabela_seg['%'].apply(lambda x: f"{x:.2f}%")
        tabela_html_seg = """<table style="width:100%; border-collapse: collapse;">
                           <tr style="border-bottom: 2px solid #0d47a1; color: #0d47a1;">
                               <th style="text-align:left; padding: 8px;">Segmento</th>
                               <th style="text-align:right; padding: 8px;">Valor (R$)</th>
                               <th style="text-align:right; padding: 8px;">%</th>
                           </tr>"""
        for index, row in df_tabela_seg.iterrows():
            tabela_html_seg += f'<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 8px;">{row["segmento"]}</td><td style="text-align:right; padding: 8px;">{row["valor_total_str"]}</td><td style="text-align:right; padding: 8px;">{row["%_str"]}</td></tr>'
        tabela_html_seg += f"""<tr style="background-color: #f0f2f6; border-top: 2px solid #0d47a1;">
                               <td style="padding: 10px; font-weight: bold;">Total</td>
                               <td style="text-align:right; padding: 10px; font-weight: bold;">R$ {total_segmentos:,.2f}</td>
                               <td style="text-align:right; padding: 10px; font-weight: bold;">100.00%</td>
                           </tr></table>"""
        components.html(tabela_html_seg, height=400, scrolling=False)

    st.markdown("##### Evolução da Distribuição por Segmentos")
    df_seg_evol = pd.concat([df_investimentos[['data_posicao', 'segmento', 'valor_total']],
                             df_imoveis[['data_posicao', 'segmento', 'valor_total']]])
    df_seg_evol_agg = df_seg_evol.groupby(['data_posicao', 'segmento'])['valor_total'].sum().unstack().fillna(0)
    df_seg_evol_pct = df_seg_evol_agg.div(df_seg_evol_agg.sum(axis=1), axis=0) * 100
    df_seg_evol_val = df_seg_evol_agg.copy()

    fig_evol_seg = go.Figure()
    seg_rotulo_cima = ['ESTRUTURADO', 'RENDA FIXA', 'RENDA VARIÁVEL', 'EXTERIOR', 'OPERACAO COM PARTICIPANTES']
    seg_rotulo_meio = ['']

    for segmento in df_seg_evol_pct.columns:
        mode = 'lines'
        text_position = None
        if segmento in seg_rotulo_cima:
            mode = 'lines+text'
            text_position = 'top center'
        elif segmento in seg_rotulo_meio:
            mode = 'lines+text'
            text_position = 'middle center'

        fig_evol_seg.add_trace(go.Scatter(
            x=df_seg_evol_pct.index, y=df_seg_evol_pct[segmento], name=segmento, mode=mode,
            line_shape='spline', customdata=df_seg_evol_val[segmento],
            text=[f'{y:.1f}%' for y in df_seg_evol_pct[segmento]], textposition=text_position,
            textfont=dict(size=12, color="#000000"),
            hovertemplate='<b>%{x|%B de %Y}</b><br>%{data.name}: %{y:.2f}%<br>Valor: R$ %{customdata:,.2f}<extra></extra>'
        ))

    evol_tick_values_seg = df_seg_evol_pct.index
    evol_tick_labels_seg = [f"{meses_map_pt[d.month]}/{d.year}" for d in evol_tick_values_seg]
    fig_evol_seg.update_layout(hovermode='x unified', yaxis_ticksuffix='%', legend_title_text='', colorway=cores_azuis,
                               xaxis=dict(tickvals=evol_tick_values_seg, ticktext=evol_tick_labels_seg),
                               margin=dict(t=20, b=40, l=40, r=20),

                               # --- ADICIONE ESTE BLOCO ---
                               hoverlabel=dict(
                                   bgcolor="white",
                                   font_size=16,
                                   font_family="sans-serif"
                               )
                               # ---------------------------
                               )
    st.plotly_chart(fig_evol_seg, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # --- INÍCIO DO BLOCO DE RANKINGS ---
    st.markdown("---")
    st.subheader("Rankings de Performance")

    # Garante que há dados de investimento para a data selecionada
    if not df_inv_filtrado.empty:
        total_fundos = df_inv_filtrado['nome_fundo'].nunique()
        total_gestores = df_inv_filtrado['gestor'].nunique()

        # --- Ranking de Fundos ---
        num_fundos = st.slider(
            "Selecione o número de fundos para exibir:",
            min_value=5,
            max_value=total_fundos,
            value=min(10, total_fundos),
            key="num_fundos"
        )

        df_fundos = df_inv_filtrado.groupby('nome_fundo')['valor_total'].sum().nlargest(num_fundos).reset_index()

        # Calcula o percentual em relação ao patrimônio total da data
        if patrimonio_na_data > 0:
            df_fundos['percentual_patrimonio'] = (df_fundos['valor_total'] / patrimonio_na_data) * 100
        else:
            df_fundos['percentual_patrimonio'] = 0

        fig_treemap_fundos = px.treemap(
            df_fundos,
            path=[px.Constant(f"Top {num_fundos} Maiores Fundos"), 'nome_fundo'],
            values='valor_total',
            color='valor_total',
            color_continuous_scale='Blues',
            custom_data=['percentual_patrimonio']
        )
        fig_treemap_fundos.update_traces(
            texttemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Total',
            textfont_size=16,
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Patrimônio Total<extra></extra>'
        )
        fig_treemap_fundos.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_treemap_fundos, use_container_width=True)

        # --- Ranking de Gestores ---
        num_gestores = st.slider(
            "Selecione o número de gestores para exibir:",
            min_value=5,
            max_value=total_gestores,
            value=min(10, total_gestores),
            key="num_gestores"
        )

        df_gestores = df_inv_filtrado.groupby('gestor')['valor_total'].sum().nlargest(num_gestores).reset_index()

        # Calcula o percentual em relação ao patrimônio total da data
        if patrimonio_na_data > 0:
            df_gestores['percentual_patrimonio'] = (df_gestores['valor_total'] / patrimonio_na_data) * 100
        else:
            df_gestores['percentual_patrimonio'] = 0

        fig_treemap_gestores = px.treemap(
            df_gestores,
            path=[px.Constant(f"Top {num_gestores} Maiores Gestores"), 'gestor'],
            values='valor_total',
            color='valor_total',
            color_continuous_scale='Blues',
            custom_data=['percentual_patrimonio']
        )
        fig_treemap_gestores.update_traces(
            texttemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Total',
            textfont_size=16,
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Patrimônio Total<extra></extra>'
        )
        fig_treemap_gestores.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_treemap_gestores, use_container_width=True)

    else:
        st.warning("Não há dados de investimentos para a data selecionada para exibir os rankings.")
    # --- FIM DO BLOCO DE RANKINGS ---


# --- FUNÇÃO GENÉRICA PARA CRIAR PÁGINAS DE PLANOS ---
def criar_pagina_plano(nome_plano_key):
    config = CONFIGURACOES_PLANOS[nome_plano_key]
    st.title(config["titulo"])

    df_investimentos, df_imoveis, df_ativos, df_indices = carregar_dados()

    # --- FILTRAGEM DOS DADOS USANDO A CONFIGURAÇÃO DO PLANO ---
    df_investimentos_plano = df_investimentos[df_investimentos['nome_plano'] == config["filtro_investimentos"]].copy()
    df_imoveis_plano = df_imoveis[df_imoveis['nome_plano'] == config["filtro_investimentos"]].copy()

    if df_investimentos_plano.empty and df_imoveis_plano.empty:
        st.warning(f"Nenhum dado encontrado para o plano {nome_plano_key}.")
        return

    # --- KPIs, Evolução e Variação ---
    data_mais_recente = (pd.concat([df_investimentos_plano['data_posicao'], df_imoveis_plano['data_posicao']])
                         .dropna().max())
    patrimonio_consolidado = (
            df_investimentos_plano[df_investimentos_plano['data_posicao'] == data_mais_recente]['valor_total'].sum() +
            df_imoveis_plano[df_imoveis_plano['data_posicao'] == data_mais_recente]['valor_total'].sum())
    patrimonio_formatado = f"R$ {patrimonio_consolidado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data_formatada = data_mais_recente.strftime('%d/%m/%Y')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'''<div class="kpi-card">
                   <div class="kpi-title">PATRIMÔNIO CONSOLIDADO ({nome_plano_key})</div>
                   <div class="kpi-value">{patrimonio_formatado}</div>
                   <div class="info-icon">i
                       <span class="tooltip-text">
                           Soma dos valores em carteiras de Investimentos, Imóveis e Operações com Participantes para o plano {nome_plano_key}.
                       </span>
                   </div>
               </div>''',
            unsafe_allow_html=True)
    with col2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">DATA DE POSIÇÃO</div><div class="kpi-value">{data_formatada}</div></div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"Evolução do Patrimônio ({nome_plano_key})")

    df_evol_inv = df_investimentos_plano.groupby('data_posicao')['valor_total'].sum().reset_index().rename(
        columns={'valor_total': 'valor_investimentos'})
    df_evol_imo = df_imoveis_plano.groupby('data_posicao')['valor_total'].sum().reset_index().rename(
        columns={'valor_total': 'valor_imoveis'})
    df_evolucao = pd.merge(df_evol_inv, df_evol_imo, on='data_posicao', how='outer').fillna(0)
    df_evolucao['Total'] = df_evolucao['valor_investimentos'] + df_evolucao['valor_imoveis']

    fig_evol = px.line(df_evolucao, x='data_posicao', y='Total', line_shape='spline')
    fig_evol.update_traces(
        line=dict(color='#1161e6', width=3),
        marker=dict(size=8, color='#4361f2', line=dict(width=1, color='#ffffff')),
        hovertemplate='<b>Data:</b> %{x|%d/%m/%Y}<br><b>Patrimônio:</b> R$ %{y:,.2f}<extra></extra>',
        text=df_evolucao['Total'].apply(formatar_numero_br),
        mode='lines+markers+text',
        textposition='top center',
        textfont=dict(size=16, color='#001f3f')
    )
    meses_map_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out',
                    11: 'Nov', 12: 'Dez'}
    tick_values = df_evolucao['data_posicao']
    tick_labels = [f"{meses_map_pt[d.month]}/{d.year}" for d in tick_values]
    fig_evol.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='<b>Data</b>', gridcolor='#e0e0e0', tickvals=tick_values, ticktext=tick_labels),
        yaxis=dict(title='<b>Patrimônio (R$)</b>', gridcolor='#e0e0e0', tickformat=',.0f'),
        margin=dict(l=40, r=40, t=40, b=40), hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=17, font_family="sans-serif")
    )
    st.plotly_chart(fig_evol, use_container_width=True)
    st.markdown("---")

    st.subheader(f"Análise de Variação Patrimonial ({nome_plano_key})")
    datas_disponiveis_dt = sorted(pd.to_datetime(df_evolucao['data_posicao'].unique()))
    meses_pt_full = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho',
                     8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    opcoes_map = {f"{meses_pt_full[d.month]}/{d.year}": d for d in datas_disponiveis_dt}
    opcoes_labels = list(opcoes_map.keys())
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        label_inicial = st.selectbox("Selecione a Data Inicial:", opcoes_labels, index=0,
                                     key=f"{nome_plano_key}_data_inicial")
    with col_data2:
        label_final = st.selectbox("Selecione a Data Final:", opcoes_labels, index=len(opcoes_labels) - 1,
                                   key=f"{nome_plano_key}_data_final")

    data_inicial = opcoes_map[label_inicial]
    data_final = opcoes_map[label_final]

    if data_inicial >= data_final:
        st.warning("A Data Inicial deve ser anterior à Data Final para calcular a variação.")
    else:
        valor_inicial = df_evolucao.loc[df_evolucao['data_posicao'] == data_inicial, 'Total'].iloc[0]
        valor_final = df_evolucao.loc[df_evolucao['data_posicao'] == data_final, 'Total'].iloc[0]
        variacao_rs = valor_final - valor_inicial
        variacao_pct = (valor_final / valor_inicial - 1) * 100 if valor_inicial != 0 else 0
        sinal_rs = "+" if variacao_rs >= 0 else ""
        sinal_pct = "+" if variacao_pct >= 0 else ""
        cor_variacao = "green" if variacao_rs >= 0 else "red"
        variacao_rs_f = f"R$ {variacao_rs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        col_var1, col_var2 = st.columns(2)
        with col_var1:
            st.markdown(
                f'<div class="var-card {cor_variacao}"><div class="var-title">VARIAÇÃO (R$)</div><div class="var-value">{sinal_rs}{variacao_rs_f}</div></div>',
                unsafe_allow_html=True)
        with col_var2:
            st.markdown(
                f'<div class="var-card {cor_variacao}"><div class="var-title">VARIAÇÃO (%)</div><div class="var-value">{sinal_pct}{variacao_pct:.2f}%</div></div>',
                unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Análise da Carteira de Investimentos ({nome_plano_key})")

    datas_analise = sorted(pd.to_datetime(df_evolucao['data_posicao'].unique()), reverse=True)
    opcoes_map_analise = {f"{meses_pt_full[d.month]}/{d.year}": d for d in datas_analise}
    label_selecionada = st.selectbox("Selecione a data para análise da composição:", list(opcoes_map_analise.keys()),
                                     key=f"{nome_plano_key}_composicao_data")
    if not label_selecionada: return
    data_selecionada = opcoes_map_analise[label_selecionada]
    df_inv_filtrado_data = df_investimentos_plano[df_investimentos_plano['data_posicao'] == data_selecionada]
    df_imo_filtrado_data = df_imoveis_plano[df_imoveis_plano['data_posicao'] == data_selecionada]
    patrimonio_na_data = df_inv_filtrado_data['valor_total'].sum() + df_imo_filtrado_data['valor_total'].sum()
    cores_azuis = ['#0d47a1', '#1976d2', '#42a5f5', '#90caf9', '#bbdefb', '#e3f2fd']
    st.markdown("<br>", unsafe_allow_html=True)

    # ... (O resto do código da pagina_investprev continua aqui, sem alterações, apenas usando as chaves dinâmicas nos widgets como key=f"{nome_plano_key}_widget_name")
    # Eu completei o código para você abaixo, já com todas as chaves dinâmicas.

    col_seg1, col_seg2 = st.columns([0.8, 1.2])
    with col_seg1:
        st.markdown("##### Distribuição por Segmentos")
        df_seg_inv = df_inv_filtrado_data.groupby('segmento')['valor_total'].sum().reset_index()
        df_seg_imo = df_imo_filtrado_data.groupby('segmento')['valor_total'].sum().reset_index()
        df_segmentos_full = pd.concat([df_seg_inv, df_seg_imo], ignore_index=True)
        fig_rosca_seg = go.Figure(data=[
            go.Pie(labels=df_segmentos_full['segmento'], values=df_segmentos_full['valor_total'], hole=.4,
                   textinfo='percent', textfont_size=17,
                   hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
                   marker=dict(colors=cores_azuis, line=dict(color='#ffffff', width=2)))])
        fig_rosca_seg.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                                    margin=dict(t=0, b=0, l=0, r=0), height=400,
                                    hoverlabel=dict(bgcolor="white", font_size=16, font_family="sans-serif"))
        st.plotly_chart(fig_rosca_seg, use_container_width=True)

    with col_seg2:
        df_tabela_seg = df_segmentos_full.copy().sort_values(by='valor_total', ascending=False)
        total_segmentos = df_tabela_seg['valor_total'].sum()
        df_tabela_seg['%'] = (df_tabela_seg['valor_total'] / total_segmentos * 100) if total_segmentos > 0 else 0
        df_tabela_seg['valor_total_str'] = df_tabela_seg['valor_total'].apply(lambda x: f"R$ {x:,.2f}")
        df_tabela_seg['%_str'] = df_tabela_seg['%'].apply(lambda x: f"{x:.2f}%")
        tabela_html_seg = """<table style="width:100%; border-collapse: collapse;">
                           <tr style="border-bottom: 2px solid #0d47a1; color: #0d47a1;">
                               <th style="text-align:left; padding: 8px;">Segmento</th>
                               <th style="text-align:right; padding: 8px;">Valor (R$)</th>
                               <th style="text-align:right; padding: 8px;">%</th>
                           </tr>"""
        for index, row in df_tabela_seg.iterrows():
            tabela_html_seg += f'<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 8px;">{row["segmento"]}</td><td style="text-align:right; padding: 8px;">{row["valor_total_str"]}</td><td style="text-align:right; padding: 8px;">{row["%_str"]}</td></tr>'
        tabela_html_seg += f"""<tr style="background-color: #f0f2f6; border-top: 2px solid #0d47a1;">
                               <td style="padding: 10px; font-weight: bold;">Total</td>
                               <td style="text-align:right; padding: 10px; font-weight: bold;">R$ {total_segmentos:,.2f}</td>
                               <td style="text-align:right; padding: 10px; font-weight: bold;">100.00%</td>
                           </tr></table>"""
        components.html(tabela_html_seg, height=400, scrolling=False)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"##### Evolução da Distribuição por Segmentos ({nome_plano_key})")

    df_seg_evol = pd.concat([
        df_investimentos_plano[['data_posicao', 'segmento', 'valor_total']],
        df_imoveis_plano[['data_posicao', 'segmento', 'valor_total']]
    ])
    df_seg_evol_agg = df_seg_evol.groupby(['data_posicao', 'segmento'])['valor_total'].sum().unstack().fillna(0)
    df_seg_evol_pct = df_seg_evol_agg.div(df_seg_evol_agg.sum(axis=1), axis=0) * 100
    df_seg_evol_val = df_seg_evol_agg.copy()

    fig_evol_seg = go.Figure()

    seg_rotulo_cima = ['ESTRUTURADO', 'RENDA FIXA', 'RENDA VARIÁVEL', 'OPERACAO COM PARTICIPANTES']
    seg_rotulo_meio = []

    for segmento in df_seg_evol_pct.columns:
        mode = 'lines'
        text_position = None
        if segmento in seg_rotulo_cima:
            mode = 'lines+text'
            text_position = 'top center'
        elif segmento in seg_rotulo_meio:
            mode = 'lines+text'
            text_position = 'middle center'

        fig_evol_seg.add_trace(go.Scatter(
            x=df_seg_evol_pct.index,
            y=df_seg_evol_pct[segmento],
            name=segmento,
            mode=mode,
            line_shape='spline',
            customdata=df_seg_evol_val[segmento],
            text=[f'{y:.1f}%' for y in df_seg_evol_pct[segmento]],
            textposition=text_position,
            textfont=dict(size=12, color="#000000"),
            hovertemplate='<b>%{x|%B de %Y}</b><br>%{data.name}: %{y:.2f}%<br>Valor: R$ %{customdata:,.2f}<extra></extra>'
        ))

    evol_tick_values_seg = df_seg_evol_pct.index
    evol_tick_labels_seg = [f"{meses_map_pt[d.month]}/{d.year}" for d in evol_tick_values_seg]

    fig_evol_seg.update_layout(
        hovermode='x unified',
        yaxis_ticksuffix='%',
        legend_title_text='',
        colorway=cores_azuis,
        xaxis=dict(tickvals=evol_tick_values_seg, ticktext=evol_tick_labels_seg),
        margin=dict(t=20, b=40, l=40, r=20),
        hoverlabel=dict(bgcolor="white", font_size=16, font_family="sans-serif")
    )
    st.plotly_chart(fig_evol_seg, use_container_width=True)

    st.markdown("---")
    st.subheader(f"Rankings de Performance ({nome_plano_key})")

    if not df_inv_filtrado_data.empty:
        total_fundos = df_inv_filtrado_data['nome_fundo'].nunique()
        total_gestores = df_inv_filtrado_data['gestor'].nunique()
        st.markdown("##### Maiores Alocações por Fundo")
        num_fundos = st.slider(
            "Selecione o número de fundos para exibir:", min_value=min(5, total_fundos),
            max_value=total_fundos, value=min(10, total_fundos), key=f"{nome_plano_key}_num_fundos")
        df_fundos = df_inv_filtrado_data.groupby('nome_fundo')['valor_total'].sum().nlargest(num_fundos).reset_index()
        df_fundos['percentual_patrimonio'] = (
                    df_fundos['valor_total'] / patrimonio_na_data * 100) if patrimonio_na_data > 0 else 0
        fig_treemap_fundos = px.treemap(
            df_fundos, path=[px.Constant(f"Top {num_fundos} Maiores Fundos"), 'nome_fundo'],
            values='valor_total', color='valor_total', color_continuous_scale='Blues',
            custom_data=['percentual_patrimonio'])
        fig_treemap_fundos.update_traces(
            texttemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Total',
            textfont_size=16,
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Patrimônio Total<extra></extra>')
        fig_treemap_fundos.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_treemap_fundos, use_container_width=True)

        st.markdown("##### Maiores Alocações por Gestor")
        num_gestores = st.slider(
            "Selecione o número de gestores para exibir:", min_value=min(5, total_gestores),
            max_value=total_gestores, value=min(10, total_gestores), key=f"{nome_plano_key}_num_gestores")
        df_gestores = df_inv_filtrado_data.groupby('gestor')['valor_total'].sum().nlargest(num_gestores).reset_index()
        df_gestores['percentual_patrimonio'] = (
                    df_gestores['valor_total'] / patrimonio_na_data * 100) if patrimonio_na_data > 0 else 0
        fig_treemap_gestores = px.treemap(
            df_gestores, path=[px.Constant(f"Top {num_gestores} Maiores Gestores"), 'gestor'],
            values='valor_total', color='valor_total', color_continuous_scale='Blues',
            custom_data=['percentual_patrimonio'])
        fig_treemap_gestores.update_traces(
            texttemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Total',
            textfont_size=16,
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>%{customdata[0]:.2f}% do Patrimônio Total<extra></extra>')
        fig_treemap_gestores.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_treemap_gestores, use_container_width=True)
    else:
        st.warning("Não há dados de investimentos para a data selecionada para exibir os rankings.")

    st.markdown("---")
    st.subheader("Análise de Rentabilidade Acumulada (Fundos vs. Indicadores)")
    df_ativos_plano = df_ativos[df_ativos['nome_plano'] == config["filtro_ativos"]].copy()
    df_ativos_plano['rentabilidade'] = pd.to_numeric(df_ativos_plano['rentabilidade'], errors='coerce').dropna()
    df_ativos_plano['data_posicao'] = df_ativos_plano['data_posicao'].dt.to_period('M').dt.start_time
    df_indices_norm = df_indices.copy()
    df_indices_norm['data_posicao'] = df_indices_norm['data_posicao'].dt.to_period('M').dt.start_time

    lista_fundos = sorted(df_ativos_plano['nome_fundo'].unique()) if not df_ativos_plano.empty else []
    lista_indicadores = sorted(
        [col for col in df_indices_norm.columns if col not in ['data_posicao']]) if not df_indices_norm.empty else []

    fundos_selecionados = st.multiselect(
        "Selecione um ou mais fundos:", options=lista_fundos, default=lista_fundos[:1] if lista_fundos else [],
        key=f"{nome_plano_key}_rent_fundos"
    )
    indicadores_selecionados = st.multiselect(
        "Selecione um ou mais indicadores:", options=lista_indicadores,
        default=['CDI'] if 'CDI' in lista_indicadores else [], key=f"{nome_plano_key}_rent_indicadores"
    )

    all_dates_series = pd.concat([df_ativos_plano['data_posicao'], df_indices_norm['data_posicao']]).dropna()
    datas_disponiveis = all_dates_series.drop_duplicates().sort_values(ascending=False)
    opcoes_data = {d.strftime('%B de %Y'): d for d in datas_disponiveis}
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        data_inicial_str = st.selectbox("Data Inicial da Análise:", options=list(opcoes_data.keys()),
                                        index=len(opcoes_data) - 1, key=f"{nome_plano_key}_rent_data_inicial")
    with col_data2:
        data_final_str = st.selectbox("Data Final da Análise:", options=list(opcoes_data.keys()), index=0,
                                      key=f"{nome_plano_key}_rent_data_final")

    data_inicial_selecionada = opcoes_data[data_inicial_str]
    data_final_selecionada = opcoes_data[data_final_str]

    if not fundos_selecionados and not indicadores_selecionados:
        st.info("Selecione pelo menos um fundo ou indicador para visualizar o gráfico.")
    elif data_inicial_selecionada > data_final_selecionada:
        st.warning("A Data Inicial deve ser anterior ou igual à Data Final.")
    else:
        dfs_combinados = []
        if fundos_selecionados:
            df_fundos_full = df_ativos_plano[df_ativos_plano['nome_fundo'].isin(fundos_selecionados)].copy()
            df_fundos_full.sort_values(by='data_posicao', inplace=True)
            df_fundos_full['ret_acum_hist'] = df_fundos_full.groupby('nome_fundo')['rentabilidade'].transform(
                lambda x: (1 + x / 100).cumprod())
            df_fundos_periodo = df_fundos_full[(df_fundos_full['data_posicao'] >= data_inicial_selecionada) & (
                        df_fundos_full['data_posicao'] <= data_final_selecionada)].copy()
            base_values = df_fundos_periodo.groupby('nome_fundo')['ret_acum_hist'].first()
            df_fundos_periodo['base'] = df_fundos_periodo['nome_fundo'].map(base_values)
            df_fundos_periodo['retorno_acumulado'] = (df_fundos_periodo['ret_acum_hist'] / df_fundos_periodo[
                'base']) - 1
            df_fundos_periodo['Tipo'] = 'Fundo'
            df_fundos_periodo.rename(columns={'nome_fundo': 'Nome'}, inplace=True)
            dfs_combinados.append(df_fundos_periodo[['data_posicao', 'Nome', 'retorno_acumulado', 'Tipo']])

        if indicadores_selecionados:
            df_indices_long = df_indices_norm.melt(id_vars=['data_posicao'], value_vars=indicadores_selecionados,
                                                   var_name='Nome', value_name='rentabilidade')
            df_indices_long['rentabilidade'] = pd.to_numeric(df_indices_long['rentabilidade'], errors='coerce')
            df_indices_long.sort_values(by='data_posicao', inplace=True)
            df_indices_long['ret_acum_hist'] = df_indices_long.groupby('Nome')['rentabilidade'].transform(
                lambda x: (1 + x).cumprod())
            df_indices_periodo = df_indices_long[(df_indices_long['data_posicao'] >= data_inicial_selecionada) & (
                        df_indices_long['data_posicao'] <= data_final_selecionada)].copy()
            base_values_ind = df_indices_periodo.groupby('Nome')['ret_acum_hist'].first()
            df_indices_periodo['base'] = df_indices_periodo['Nome'].map(base_values_ind)
            df_indices_periodo['retorno_acumulado'] = (df_indices_periodo['ret_acum_hist'] / df_indices_periodo[
                'base']) - 1
            df_indices_periodo['Tipo'] = 'Indicador'
            dfs_combinados.append(df_indices_periodo[['data_posicao', 'Nome', 'retorno_acumulado', 'Tipo']])

        if dfs_combinados:
            df_final_plot = pd.concat(dfs_combinados, ignore_index=True).sort_values(by='data_posicao')
            fig_rentabilidade = px.line(
                df_final_plot, x='data_posicao', y='retorno_acumulado', color='Nome',
                line_dash='Tipo', line_shape='spline',
                labels={"data_posicao": "<b>Data</b>", "retorno_acumulado": "<b>Rentabilidade Acumulada (%)</b>",
                        "Nome": "<b>Ativo</b>"}
            )
            fig_rentabilidade.update_traces(mode='lines+markers')
            fig_rentabilidade.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='#e0e0e0', tickformat='%b/%Y', dtick="M1"),
                yaxis=dict(gridcolor='#e0e0e0', tickformat=".2%"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.4, title_text=""),
                margin=dict(l=40, r=40, t=40, b=40),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="white", font_size=16),
                legend_traceorder="grouped"
            )
            st.plotly_chart(fig_rentabilidade, use_container_width=True)
        else:
            st.warning("Nenhum dado encontrado para os ativos selecionados no período especificado.")

carregar_css()

# --- FUNÇÕES DE PÁGINA (agora simplificadas) ---
# Cole este bloco DEPOIS da função criar_pagina_plano

def pagina_investprev():
    criar_pagina_plano("INVESTPREV")

def pagina_plano_a():
    criar_pagina_plano("PLANO A")

def pagina_vidaprev():
    criar_pagina_plano("VIDAPREV")

def pagina_assistencial():
    criar_pagina_plano("ASSISTENCIAL")

def pagina_pga():
    criar_pagina_plano("PGA")

if "pagina_selecionada" not in st.session_state:
    st.session_state.pagina_selecionada = "🏠"


def go_home():
    st.session_state.pagina_selecionada = "🏠"


with st.sidebar:
    st.button("Home", on_click=go_home, key="logo_button")
    st.markdown(f"""
        <h3 style="font-size:15px; font-weight:600; color:#ffffff; margin: 0;
            padding: 0 16px 6px 16px; border-bottom: 2px solid rgba(255,255,255,0.4);
            width: 100%; text-align: center;">
            Navegação dos Planos
        </h3>
    """, unsafe_allow_html=True)

    paginas = {"🏠": pagina_home, "InvestPrev": pagina_investprev, "Plano A": pagina_plano_a,
               "VidaPrev": pagina_vidaprev, "Assistencial": pagina_assistencial, "PGA": pagina_pga}
    st.radio("Selecione um plano:", options=list(paginas.keys()), label_visibility="collapsed",
             key="pagina_selecionada")

paginas[st.session_state.pagina_selecionada]()