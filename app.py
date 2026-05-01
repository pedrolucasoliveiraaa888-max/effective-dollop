import streamlit as st
import sys
import os
import pandas as pd

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_config, get_connection
from modules.estoque import render_estoque
from modules.clientes import render_clientes
from modules.vendas import render_vendas
from modules.importexport import render_importexport
from modules.crediario import render_crediario
from modules.configuracoes import render_configuracoes

# ─── CONFIGURAÇÃO DA PÁGINA ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Gestão de Loja & PDV",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS CUSTOMIZADO ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2744 0%, #2E4057 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e8eaf0 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 15px !important;
        padding: 6px 0 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #4a5a7a !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2E4057, #1a2744);
        border: none;
        color: white;
        font-weight: bold;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3d5270, #2E4057);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(46,64,87,0.4);
    }
    [data-testid="metric-container"] {
        background: #f8f9fc;
        border: 1px solid #e1e5ee;
        border-radius: 10px;
        padding: 12px 16px;
    }
    h1 { color: #1a2744 !important; }
    h2, h3 { color: #2E4057 !important; }
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        font-weight: 500;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── INICIALIZAR BANCO DE DADOS ───────────────────────────────────────────────
init_db()


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
def render_dashboard():
    nome_loja = get_config("nome_loja") or "Minha Loja"
    st.title(f"🏪 {nome_loja} — Dashboard")

    conn = get_connection()

    total_produtos = conn.execute("SELECT COUNT(*) FROM produtos WHERE ativo=1").fetchone()[0]
    total_clientes = conn.execute("SELECT COUNT(*) FROM clientes WHERE ativo=1").fetchone()[0]
    total_vendas = conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
    receita_total = conn.execute("SELECT COALESCE(SUM(total),0) FROM vendas").fetchone()[0]
    cred_pendente = conn.execute(
        "SELECT COALESCE(SUM(valor_parcela),0) FROM crediario WHERE status='pendente'"
    ).fetchone()[0]
    estq_baixo = conn.execute(
        "SELECT COUNT(*) FROM produtos WHERE ativo=1 AND quantidade <= quantidade_minima"
    ).fetchone()[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Produtos Ativos", total_produtos)
    col2.metric("👥 Clientes Ativos", total_clientes)
    col3.metric("🛒 Total de Vendas", total_vendas)

    col4, col5, col6 = st.columns(3)
    col4.metric("💰 Receita Total", f"R$ {receita_total:,.2f}")
    col5.metric("📋 Crediário Pendente", f"R$ {cred_pendente:,.2f}")
    col6.metric("⚠️ Estoque Baixo", estq_baixo,
                delta=f"-{estq_baixo} produtos" if estq_baixo > 0 else None,
                delta_color="inverse")

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📈 Últimas Vendas")
        ultimas_vendas = conn.execute("""
            SELECT v.numero_venda, COALESCE(c.nome, 'Consumidor Final') as cliente,
                   v.total, v.tipo_pagamento, v.criado_em
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            ORDER BY v.criado_em DESC LIMIT 10
        """).fetchall()

        if ultimas_vendas:
            df_uv = pd.DataFrame([dict(r) for r in ultimas_vendas])
            df_uv["total"] = df_uv["total"].apply(lambda x: f"R$ {x:,.2f}")
            mapa_pag = {
                "dinheiro": "💵 Dinheiro", "cartao_credito": "💳 C. Crédito",
                "cartao_debito": "💳 C. Débito", "pix": "📱 PIX",
                "crediario": "📋 Crediário", "cheque": "📝 Cheque"
            }
            df_uv["tipo_pagamento"] = df_uv["tipo_pagamento"].map(mapa_pag).fillna(df_uv["tipo_pagamento"])
            df_uv.columns = ["Nº Venda", "Cliente", "Total", "Pagamento", "Data/Hora"]
            st.dataframe(df_uv, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda registrada ainda.")

    with col_b:
        st.subheader("⚠️ Parcelas Vencidas")
        parc_venc = conn.execute("""
            SELECT c.nome, cr.numero_parcela, cr.total_parcelas,
                   cr.valor_parcela, cr.data_vencimento
            FROM crediario cr
            JOIN clientes c ON cr.cliente_id = c.id
            WHERE cr.status = 'pendente' AND cr.data_vencimento <= DATE('now')
            ORDER BY cr.data_vencimento LIMIT 10
        """).fetchall()

        if parc_venc:
            df_pv = pd.DataFrame([dict(r) for r in parc_venc])
            df_pv["valor_parcela"] = df_pv["valor_parcela"].apply(lambda x: f"R$ {x:,.2f}")
            df_pv["parcela"] = df_pv.apply(
                lambda r: f"{r['numero_parcela']}/{r['total_parcelas']}", axis=1
            )
            df_pv = df_pv[["nome", "parcela", "valor_parcela", "data_vencimento"]]
            df_pv.columns = ["Cliente", "Parcela", "Valor", "Vencimento"]
            st.dataframe(df_pv, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Nenhuma parcela vencida!")

        st.divider()
        st.subheader("📦 Produtos com Estoque Baixo")
        prod_baixo = conn.execute("""
            SELECT codigo, nome, quantidade, quantidade_minima
            FROM produtos
            WHERE ativo=1 AND quantidade <= quantidade_minima
            ORDER BY quantidade LIMIT 8
        """).fetchall()

        if prod_baixo:
            df_pb = pd.DataFrame([dict(r) for r in prod_baixo])
            df_pb.columns = ["Código", "Produto", "Qtd. Atual", "Qtd. Mínima"]
            st.dataframe(df_pb, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os produtos com estoque adequado!")

    conn.close()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    nome_loja = get_config("nome_loja") or "Minha Loja"

    st.markdown(f"""
    <div style='text-align:center; padding: 10px 0 20px 0;'>
        <div style='font-size:40px;'>🏪</div>
        <div style='font-size:18px; font-weight:bold; color:#fff;'>{nome_loja}</div>
        <div style='font-size:11px; color:#aab4c8; margin-top:4px;'>Sistema de Gestão & PDV</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    conn = get_connection()
    vendas_hoje = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(total),0) FROM vendas WHERE DATE(criado_em) = DATE('now')"
    ).fetchone()
    parcelas_venc = conn.execute(
        "SELECT COUNT(*) FROM crediario WHERE status='pendente' AND data_vencimento <= DATE('now')"
    ).fetchone()
    estoque_baixo = conn.execute(
        "SELECT COUNT(*) FROM produtos WHERE ativo=1 AND quantidade <= quantidade_minima"
    ).fetchone()
    conn.close()

    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.08); border-radius:8px; padding:10px; margin-bottom:12px;'>
        <div style='font-size:11px; color:#aab4c8; margin-bottom:6px;'>📅 HOJE</div>
        <div style='font-size:13px;'>🛒 <b>{vendas_hoje[0]}</b> vendas — R$ {vendas_hoje[1]:,.2f}</div>
        <div style='font-size:13px; color:{"#ff6b6b" if parcelas_venc[0] > 0 else "#69db7c"};'>
            {'⚠️' if parcelas_venc[0] > 0 else '✅'} <b>{parcelas_venc[0]}</b> parcelas vencidas
        </div>
        <div style='font-size:13px; color:{"#ff6b6b" if estoque_baixo[0] > 0 else "#69db7c"};'>
            {'⚠️' if estoque_baixo[0] > 0 else '✅'} <b>{estoque_baixo[0]}</b> produtos c/ estoque baixo
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    pagina = st.radio(
        "Navegação",
        [
            "🏠 Dashboard",
            "📦 Estoque",
            "👥 Clientes",
            "🛒 Vendas / PDV",
            "📂 Importar / Exportar",
            "📋 Crediário",
            "⚙️ Configurações",
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown(
        "<div style='font-size:10px; color:#6b7a99; text-align:center;'>v1.0 — Loja PDV System</div>",
        unsafe_allow_html=True
    )

# ─── ROTEAMENTO ───────────────────────────────────────────────────────────────
if pagina == "🏠 Dashboard":
    render_dashboard()
elif pagina == "📦 Estoque":
    render_estoque()
elif pagina == "👥 Clientes":
    render_clientes()
elif pagina == "🛒 Vendas / PDV":
    render_vendas()
elif pagina == "📂 Importar / Exportar":
    render_importexport()
elif pagina == "📋 Crediário":
    render_crediario()
elif pagina == "⚙️ Configurações":
    render_configuracoes()
