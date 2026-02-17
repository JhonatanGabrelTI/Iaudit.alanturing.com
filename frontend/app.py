import streamlit as st
import os
from utils.ui import setup_page
setup_page(title="IAudit — Automação Fiscal", icon="🔍")


# ─── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 IAudit")
    st.markdown("**Automação Fiscal**")
    st.markdown("---")
    st.markdown("### Navegação")
    st.markdown("""
    - 📊 **Dashboard**
    - 🏢 **Empresas**
    - 📤 **Upload**
    - 🔍 **Detalhes**
    """)
    st.markdown("---")
    
    # Get domain from environment variable, default to alanturing.com
    domain_name = os.getenv("DOMAIN_NAME", "iaudit.alanturing.com")
    
    st.markdown(
        f"<small style='color:#64748b'>v1.0.0 • {domain_name}</small>",
        unsafe_allow_html=True,
    )

# ─── Main Page ───────────────────────────────────────────────────────
# Hero - Centered & Modern with Animation
st.markdown("""
<style>
@keyframes fadeInDown {
from {
opacity: 0;
transform: translateY(-30px);
}
to {
opacity: 1;
transform: translateY(0);
}
}

@keyframes shimmer {
0% {
background-position: -200% center;
}
100% {
background-position: 200% center;
}
}

.hero-title {
background: linear-gradient(90deg, #60a5fa, #a78bfa, #60a5fa);
background-size: 200% auto;
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
animation: shimmer 4s linear infinite, fadeInDown 0.8s ease-out;
}

.hero-subtitle {
animation: fadeInDown 0.8s ease-out 0.2s backwards;
}

.hero-description {
animation: fadeInDown 0.8s ease-out 0.4s backwards;
}
</style>

<div style="text-align: center; padding: 3rem 1rem 2rem 1rem;">
<h1 class="hero-title" style="font-size: 3.5rem; font-weight: 700; margin-bottom: 1rem;">
🔍 IAudit
</h1>
<p class="hero-subtitle" style="color: #cbd5e1; font-size: 1.4rem; max-width: 700px; margin: 0 auto 1rem auto;">
Monitoramento Inteligente de Certidões
</p>
<p class="hero-description" style="color: #94a3b8; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
Automatize consultas fiscais e trabalhistas com alertas em tempo real
</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Cards de Navegação com Animações
st.markdown("""
<style>
@keyframes slideInUp {
from {
opacity: 0;
transform: translateY(30px);
}
to {
opacity: 1;
transform: translateY(0);
}
}

.nav-card {
background: linear-gradient(135deg, #1e293b, #334155);
padding: 2.5rem 1.5rem;
border-radius: 20px;
text-align: center;
border: 1px solid #475569;
min-height: 240px;
box-shadow: 0 8px 24px rgba(0,0,0,0.4);
transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
position: relative;
overflow: hidden;
animation: slideInUp 0.6s ease-out backwards;
}

.nav-card::before {
content: '';
position: absolute;
top: 0;
left: -100%;
width: 100%;
height: 100%;
background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.1), transparent);
transition: left 0.5s ease;
}

.nav-card:hover::before {
left: 100%;
}

.nav-card:hover {
transform: translateY(-8px) scale(1.02);
box-shadow: 0 16px 48px rgba(59, 130, 246, 0.4);
border-color: #60a5fa;
}

.nav-card-icon {
font-size: 3.5rem;
margin-bottom: 1.2rem;
display: inline-block;
transition: transform 0.3s ease;
}

.nav-card:hover .nav-card-icon {
transform: scale(1.2) rotate(5deg);
}
    
    .nav-card-badge {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: rgba(239, 68, 68, 0.9);
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.5);
    }
</style>

<h3 style='text-align: center; color: #f1f5f9; margin-bottom: 2.5rem; animation: fadeInDown 0.8s ease-out 0.6s backwards;'>⚡ Acesso Rápido</h3>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3, gap="large")

with c1:
    st.markdown("""<div class="nav-card" style="animation-delay: 0.2s;">
<span class="nav-card-badge">3 novos</span>
<div class="nav-card-icon">📊</div>
<h3 style="color: #f1f5f9; margin-bottom: 0.8rem;">Dashboard</h3>
<p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">KPIs e alertas ativos</p>
</div>""", unsafe_allow_html=True)
    if st.button("🚀 Acessar", key="b1", use_container_width=True):
        st.switch_page("pages/1_📊_Dashboard.py")

with c2:
    st.markdown("""<div class="nav-card" style="animation-delay: 0.4s;">
<div class="nav-card-icon">🏢</div>
<h3 style="color: #f1f5f9; margin-bottom: 0.8rem;">Empresas</h3>
<p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">Consultar CNPJs</p>
</div>""", unsafe_allow_html=True)
    if st.button("🔍 Consultar", key="b2", use_container_width=True):
        st.switch_page("pages/2_🏢_Empresas.py")

with c3:
    st.markdown("""<div class="nav-card" style="animation-delay: 0.6s;">
<div class="nav-card-icon">📤</div>
<h3 style="color: #f1f5f9; margin-bottom: 0.8rem;">Upload</h3>
<p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">Importar CSV</p>
</div>""", unsafe_allow_html=True)
    if st.button("📥 Importar", key="b3", use_container_width=True):
        st.switch_page("pages/3_📤_Upload.py")
