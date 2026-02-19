import streamlit as st
import os
from utils.ui import setup_page

# ─── SETUP ──────────────────────────────────────────────────────────
setup_page(title="IAudit — Automação Fiscal", icon=None, layout="wide")

# ─── CUSTOM CSS ─────────────────────────────────────────────────────
# Visual branding and common styles are now handled globally.


# ─── NAVIGATION ───────────────────────────────────────────────────

pages = {
    "Estratégia": [
        st.Page("app.py", title="Início", icon=None, default=True),
    ],
    "Fiscal": [
        st.Page("views/1_Fiscal/1_Dashboard.py", title="Dashboard", icon=None),
        st.Page("views/1_Fiscal/2_Empresas.py", title="Empresas", icon=None),
        st.Page("views/1_Fiscal/3_Carregar.py", title="Upload", icon=None),
        st.Page("views/1_Fiscal/6_Agendamentos.py", title="Agendas", icon=None),
        st.Page("views/1_Fiscal/4_Detalhes.py", title="Monitor", icon=None),
    ],
    "Financeiro": [
        st.Page("views/2_Financeiro/5_Financeiro.py", title="Cobranças", icon=None),
        st.Page("views/2_Financeiro/7_Comunicação.py", title="Mensagens", icon=None),
    ]
}

pg = st.navigation(pages)

# ─── SIDEBAR ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0; text-align: center;">
        <div style="font-weight: 700; font-size: 1.5rem; color: #f8fafc; letter-spacing: -0.5px;">
            <span style="color: #60a5fa;">IAudit</span>
        </div>
        <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">System v2.2 (Modular)</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    domain_name = os.getenv("DOMAIN_NAME", "iaudit.alanturing.com")
    st.caption(f"Connected to: {domain_name}")

# ─── HERO SECTION ────────────────────────────────────────────────────
# The hero section should only show if we are on the Home page
if pg.title == "Início":
    st.markdown("""
    <div class="hero-container">
        <div class="hero-logo-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="m9 12 2 2 4-4"/>
            </svg>
        </div>
        <div class="hero-badge">IAudit v2.2</div>
        <h1 class="hero-title">IAudit</h1>
        <div style="font-size: 1.2rem; margin-top: -1rem; color: var(--text-accent); font-weight: 500; opacity: 0.9;">Plataforma Modular de Automação</div>
        <p class="hero-subtitle">
            Módulos independentes para Auditoria Fiscal e Gestão Financeira. <br>
            Escolha uma área para começar.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─── NAVIGATION CARDS ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="medium")

    with c1:
        st.markdown("""
        <div class="glass-card" style="animation: fadeIn 0.6s ease-out 0.2s backwards;">
            <div class="card-icon"></div>
            <div class="card-title">Fiscal</div>
            <div class="card-desc">Visualize indicadores e status de conformidade.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Fiscal", type="primary", use_container_width=True, key="btn_fiscal"):
            st.switch_page("views/1_Fiscal/1_Dashboard.py")

    with c2:
        st.markdown("""
        <div class="glass-card" style="animation: fadeIn 0.6s ease-out 0.4s backwards;">
            <div class="card-icon"></div>
            <div class="card-title">Empresas</div>
            <div class="card-desc">Gerencie o cadastro de empresas e filiais.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Gerenciar Empresas", type="secondary", use_container_width=True, key="btn_empresas"):
            st.switch_page("views/1_Fiscal/2_Empresas.py")

    with c3:
        st.markdown("""
        <div class="glass-card" style="animation: fadeIn 0.6s ease-out 0.6s backwards;">
            <div class="card-icon"></div>
            <div class="card-title">Financeiro</div>
            <div class="card-desc">Cobre seus clientes via API Bradesco.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Gestão Financeira", type="secondary", use_container_width=True, key="btn_financeiro"):
            st.switch_page("views/2_Financeiro/5_Financeiro.py")

    with c4:
        st.markdown("""
        <div class="glass-card" style="animation: fadeIn 0.6s ease-out 0.8s backwards;">
            <div class="card-icon"></div>
            <div class="card-title">Mensagens</div>
            <div class="card-desc">Configure robôs e réguas de comunicação.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Centro de Mensagens", type="secondary", use_container_width=True, key="btn_comunicacao"):
            st.switch_page("views/2_Financeiro/7_Comunicação.py")

else:
    # Run the selected page
    pg.run()

# ─── FOOTER ──────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; margin-top: 6rem; padding-bottom: 2rem; color: #475569;">
    <p style="font-size: 0.875rem;">&copy; 2024 IAudit. Todos os direitos reservados.</p>
</div>
""", unsafe_allow_html=True)
