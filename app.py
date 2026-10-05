import streamlit as st
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os
import re


# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Gestão de Inadimplência CCB & IA Local",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .kpi-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 8px;
    }
    .kpi-label {
        font-size: 13px;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .ai-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #6366f1;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# 2. Leitura das credenciais
load_dotenv()
DB_HOST = os.getenv("HOST")
#DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


# 3. Função de conexão com cache do Streamlit
@st.cache_resource
def get_db_engine():
    """
    Cria a engine do SQLAlchemy no padrão pymssql 
    mssql+pymssql://SERVER/DATABASE (usando a autenticação do Windows do ambiente local)
    """
   
    connection_url = f"mssql+pymssql://{DB_HOST}/{DB_NAME}"
    
    engine = create_engine(connection_url, pool_pre_ping=True)
    return engine

engine = get_db_engine()

#===============================================
#4. Pegando dados do banco
#===============================================

@st.cache_data(ttl=300)  # Cache dos dados por 5 minutos
def carregar_dados():
    """
    Realiza o SELECT cruzando as tabelas reais existentes:
    TbContratos, TbParcelas, TbPagamentos e TbAcionamentos
    """
    query = text("""
    SELECT 
        c.ccb AS ccb,
        c.NomeCliente AS NomeCliente,
        c.CPF AS CPF,
        c.ValorContrato AS ValorContrato,
        c.NumParcelas AS NumParcelas,
        SUM(p.ValorParcela) AS TotalEmAtraso,
        COUNT(DISTINCT p.NumParcela) AS QtdParcelasAtraso,
        MAX(DATEDIFF(day, p.DtVencimentoOriginal, GETDATE())) AS DiasAtrasoMaximo,
        COUNT(DISTINCT a.DataAcionamento) AS TotalAcionamentos,
        MAX(a.DataAcionamento) AS UltimoAcionamento
    FROM TbContratos c
    INNER JOIN TbParcelas p ON c.ccb = p.ccb
    LEFT JOIN TbPagamentos pag ON p.ccb = pag.ccb AND p.NumParcela = pag.NumParcela
    LEFT JOIN TbAcionamentos a ON c.ccb = a.ccb
    WHERE pag.DataPagamento IS NULL 
      AND p.DtVencimentoOriginal < GETDATE()
    GROUP BY c.ccb, c.NomeCliente, c.CPF, c.ValorContrato, c.NumParcelas
    """)
    
    # Abre a conexão explicitamente com o engine do SQLAlchemy
    with engine.connect() as conn:
        df = pd.read_sql(query, con=conn)
    
    # Preenche valores nulos do último acionamento
    if not df.empty:
        df['UltimoAcionamento'] = df['UltimoAcionamento'].astype(str).replace({'None': 'Sem Registro', 'NaT': 'Sem Registro'})
        df['TotalAcionamentos'] = df['TotalAcionamentos'].fillna(0).astype(int)
        df['DiasAtrasoMaximo'] = df['DiasAtrasoMaximo'].fillna(0).astype(int)
    else:
        # Cria um DataFrame vazio com as colunas caso não retorne nenhum registro
        df = pd.DataFrame(columns=[
            'ccb', 'NomeCliente', 'CPF', 'ValorContrato', 'NumParcelas',
            'TotalEmAtraso', 'QtdParcelasAtraso', 'DiasAtrasoMaximo',
            'TotalAcionamentos', 'UltimoAcionamento'
        ])
        
    return df


# ==========================================
# 5. INTEGRAÇÃO COM OLLAMA (QWEN2.5:3B)
# ==========================================
def consultar_ollama_qwen(prompt):
    """Envia a requisição para o Qwen 2.5 local rodando no Ollama."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=180)
        if response.status_code == 200:
            return response.json().get('response', 'Erro: Resposta vazia da IA.')
        else:
            return f"⚠️ Erro HTTP {response.status_code} na API do Ollama."
    except requests.exceptions.ConnectionError:
        return "❌ **Não foi possível conectar ao Ollama.** Verifique se o serviço está ativo rodando `ollama serve` ou `ollama run qwen2.5:3b`."
    except Exception as e:
        return f"❌ Erro na consulta: {str(e)}"


# ==========================================
# 6. BARRA LATERAL (FILTROS DE COBRANÇA)
# ==========================================
#st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
st.sidebar.title("Filtros de Alerta CCB")

max_acionamentos = st.sidebar.slider(
    "Máximo de Acionamentos Realizados:",
    min_value=0, max_value=5, value=2,
    help="Identifica CCBs com dívida e baixa cobertura operacional."
)

min_dias_atraso = st.sidebar.slider(
    "Mínimo de Dias de Atraso:",
    min_value=15, max_value=120, value=30
)

# ==========================================
# 7. DASHBOARD PRINCIPAL
# ==========================================
st.markdown("""
<div class="hero-container">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 26px; color: #f8fafc;">🛡️ Gestão de Inadimplência em contratos usando a IA Qwen 2.5</h1>
            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px;">
                Análise de Contratos, Parcelas e Réguas de Acionamento via Inteligência Artificial Local
            </p>
        </div>
        <div>
            <span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600;">
                🤖 Modelo: qwen2.5:3b
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Carregar dados consolidando as tabelas SQL
df_inadimplencia = carregar_dados()

# Filtro dos contratos críticos
df_criticos = df_inadimplencia[
    (df_inadimplencia['TotalAcionamentos'] <= max_acionamentos) &
    (df_inadimplencia['DiasAtrasoMaximo'] >= min_dias_atraso)
]

# Cards de Métricas (KPIs)
col1, col2, col3, col4 = st.columns(4)

total_devido = df_inadimplencia['TotalEmAtraso'].sum()
montante_critico = df_criticos['TotalEmAtraso'].sum()
qtd_ccbs_criticas = len(df_criticos)
media_dias = df_criticos['DiasAtrasoMaximo'].mean() if not df_criticos.empty else 0

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Montante Total Atrasado</div>
        <div class="kpi-value">R$ {total_devido:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card" style="border-color: #ef4444;">
        <div class="kpi-label" style="color: #f87171;">Montante Pouco Cobrado</div>
        <div class="kpi-value" style="color: #f87171;">R$ {montante_critico:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">CCBs Alvo de Cobrança</div>
        <div class="kpi-value">{qtd_ccbs_criticas}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Média Atraso Alvos</div>
        <div class="kpi-value">{media_dias:.0f} dias</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Abas de Navegação
tab_tabela, tab_ia, tab_graficos = st.tabs(["📋 CCBs Prioritárias", "🤖 Recomendações da IA (Qwen)", "📊 Visualizações"])

# TAB 1: VISÃO GERAL
with tab_tabela:
    st.subheader("Contratos com Alta Inadimplência vs. Baixo Histórico de Acionamento")
    if df_criticos.empty:
        st.info("Nenhuma CCB encontrada para os filtros selecionados.")
    else:
        df_show = df_criticos.copy()
        df_show['ValorContrato'] = df_show['ValorContrato'].apply(lambda x: f"R$ {x:,.2f}")
        df_show['TotalEmAtraso'] = df_show['TotalEmAtraso'].apply(lambda x: f"R$ {x:,.2f}")
        df_show['DiasAtrasoMaximo'] = df_show['DiasAtrasoMaximo'].apply(lambda x: f"{x} dias")
        
        st.dataframe(
            df_show[['ccb', 'NomeCliente', 'CPF', 'ValorContrato', 'QtdParcelasAtraso', 'TotalEmAtraso', 'DiasAtrasoMaximo', 'TotalAcionamentos', 'UltimoAcionamento']],
            column_config={
                "ccb": "Nº CCB",
                "NomeCliente": "Cliente",
                "CPF": "CPF/CNPJ",
                "ValorContrato": "Valor do Contrato",
                "QtdParcelasAtraso": "Parcelas Abertas",
                "TotalEmAtraso": "Dívida Acumulada",
                "DiasAtrasoMaximo": "Maior Atraso",
                "TotalAcionamentos": "Acionamentos",
                "UltimoAcionamento": "Última Cobrança"
            },
            use_container_width=True,
            hide_index=True
        )

# TAB 2: RECOMENDADOR IA COM QWEN 2.5
with tab_ia:
    st.subheader("🤖 Consultor Estratégico de Cobrança (Qwen 2.5 Português)")
    st.markdown("Selecione um contrato para solicitar à IA uma proposta de régua e abordagem personalizada.")
    
    if df_criticos.empty:
        st.warning("Ajuste os filtros na barra lateral para exibir contratos para análise.")
    else:
        ccb_selecionada = st.selectbox(
            "Selecione a CCB para Analisar:",
            options=df_criticos['ccb'].tolist(),
            format_func=lambda x: f"{x} - {df_criticos[df_criticos['ccb']==x]['NomeCliente'].values[0]}"
        )
        
        dados_ccb = df_criticos[df_criticos['ccb'] == ccb_selecionada].iloc[0]
        
        st.markdown(f"""
        **Detalhes do Contrato Selecionado:**  
        • **Cliente:** {dados_ccb['NomeCliente']} | **Doc:** {dados_ccb['CPF']}  
        • **CCB:** {dados_ccb['ccb']} | **Valor Original Contrato:** R\$ {dados_ccb['ValorContrato']:,.2f}  
        • **Parcelas em Atraso:** {dados_ccb['QtdParcelasAtraso']} parcela(s) | **Dívida Atrasada:** R\$ {dados_ccb['TotalEmAtraso']:,.2f} ({dados_ccb['DiasAtrasoMaximo']} dias de atraso)  
        • **Total de Acionamentos Registrados:** {dados_ccb['TotalAcionamentos']} contato(s)
        """)
        
        if st.button("🚀 Gerar Diagnóstico e Estratégia via Qwen 2.5"):
            prompt_qwen = f"""
            Você é um especialista em cobrança corporativa e recuperação de crédito no Brasil.
            Analise o seguinte contrato inadimplente:

            - Nome do Cliente: {dados_ccb['NomeCliente']}
            - Número do Contrato/CCB: {dados_ccb['ccb']}
            - Valor Total do Contrato: R$ {dados_ccb['ValorContrato']:.2f}
            - Quantidade de Parcelas em Atraso: {dados_ccb['QtdParcelasAtraso']}
            - Valor Acumulado em Atraso: R$ {dados_ccb['TotalEmAtraso']:.2f}
            - Dias de Atraso do Vencimento Mais Antigo: {dados_ccb['DiasAtrasoMaximo']} dias
            - Histórico de Acionamentos Efetuados: Apenas {dados_ccb['TotalAcionamentos']} tentativa(s) até o momento.

            IMPORTANTE: Sempre formate valores monetários com o símbolo completo de moeda brasileira "R$" (exemplo: R$ 5.000,00).
            Com base nisso, forneça em Português do Brasil:
            1. **Nível de Prioridade:** (Baixa, Média ou Crítica) e justificativa.
            2. **Canal Recomendado de Cobrança:** (ex: WhatsApp corporativo, Ligação executiva, Notificação formal) e tom da conversa.
            3. **Opções de Renegociação:** Sugestão de proposta para quitação ou reparcelamento.
            4. **Script de Abordagem Rápido:** Uma mensagem em 3 linhas para o operador enviar ao cliente.
            """
            
            with st.spinner("O Qwen 2.5 está processando a análise estratégica em português..."):
                resposta = consultar_ollama_qwen(prompt_qwen)
                resposta_corrigida = re.sub(r'\bR\s+(\d)', r'R$ \1', resposta)
                resposta_exibicao = resposta_corrigida.replace("R$", "R\\$")
                st.markdown('<div class="ai-box">', unsafe_allow_html=True)
                st.markdown(f"### 💡 Recomendação Estratégica — {dados_ccb['NomeCliente']} ({dados_ccb['ccb']})")
                st.markdown(resposta_exibicao)
                st.markdown('</div>', unsafe_allow_html=True)

# TAB 3: GRÁFICOS INTERATIVOS
with tab_graficos:
    st.subheader("📊 Análise Gráfica dos Contratos")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        fig_atraso = px.bar(
            df_inadimplencia,
            x='ccb',
            y='TotalEmAtraso',
            color='DiasAtrasoMaximo',
            title='Valor Devido por CCB vs. Dias em Atraso',
            labels={'TotalEmAtraso': 'Valor Devido (R$)', 'ccb': 'CCB', 'DiasAtrasoMaximo': 'Dias Atraso'},
            color_continuous_scale='Reds'
        )
        # 1. Configura o eixo X para ser tratado como texto/categoria e desativa a notação k/M
        fig_atraso.update_xaxes(type='category')
        fig_atraso.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color='#f8fafc',
            title_font=dict(color='#FFFFFF', size=18)
        )
        st.plotly_chart(fig_atraso, use_container_width=True)
        
    with col_g2:
        fig_aciona = px.scatter(
            df_inadimplencia,
            x='TotalAcionamentos',
            y='TotalEmAtraso',
            size='DiasAtrasoMaximo',
            hover_name='NomeCliente',
            title='Matriz: Dívida x Acionamentos Efetuados',
            labels={'TotalAcionamentos': 'Qtd de Acionamentos', 'TotalEmAtraso': 'Valor em Atraso (R$)'}
        )
        fig_aciona.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color='#f8fafc',
            title_font=dict(color='#FFFFFF', size=18)
        )
        st.plotly_chart(fig_aciona, use_container_width=True)

st.divider()
st.caption("🛡️️ Sistema Local de Análise de Crédito e Cobrança | Qwen 2.5 Open Source")