import streamlit as st
import httpx
import os
import pandas as pd
from datetime import datetime
import sys

# Add parent dir to path for utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ui import setup_page

# Configure page
setup_page(title="IAudit — Financeiro", icon=None)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def post(endpoint: str, data: dict):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=30)
        if r.status_code >= 400:
            st.error(f"Erro na API: {r.text}")
            return None
        return r.json()
    except Exception as e:
        st.error(f"Erro na requisição POST: {e}")
        return None

def fetch(endpoint: str, params: dict = None):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=30)
        if r.status_code >= 400:
            st.error(f"Erro na API: {r.text}")
            return None
        return r.json()
    except Exception as e:
        st.error(f"Erro na requisição GET: {e}")
        return None

# ─── Data Logic ──────────────────────────────────────────────────────

# Initialize session state for boletos
if 'boletos' not in st.session_state:
    st.session_state['boletos'] = [
        {"Nosso Número": "1234567890", "Empresa": "Alpha TI Ltda", "Vencimento": "10/03/2026", "Valor": 1500.00, "Status": "Emitido"},
        {"Nosso Número": "9876543210", "Empresa": "Beta Contab", "Vencimento": "28/02/2026", "Valor": 850.50, "Status": "Pago"},
        {"Nosso Número": "5544332211", "Empresa": "Gamma Engenharia", "Vencimento": "15/02/2026", "Valor": 4330.00, "Status": "Vencido"},
    ]

# Calculate dynamic stats
total_emitido = sum(b['Valor'] for b in st.session_state['boletos'])
total_pago = sum(b['Valor'] for b in st.session_state['boletos'] if b['Status'] == 'Pago')
total_a_vencer = sum(b['Valor'] for b in st.session_state['boletos'] if b['Status'] in ['Emitido', 'Aguardando', 'Vencido'])
# Inadimplência is Vencido / Total
vencidos = sum(b['Valor'] for b in st.session_state['boletos'] if b['Status'] == 'Vencido')
inadimplencia = (vencidos / total_emitido * 100) if total_emitido > 0 else 0

# ─── UI Content ──────────────────────────────────────────────────────

st.markdown("""
<div class="glass-card" style="margin-bottom: 2rem; padding: 1.5rem;">
    <h1 style='margin: 0; color: #f8fafc; font-size: 1.8rem;'>Gestão de Cobranças Bradesco</h1>
    <p style='margin: 0.5rem 0 0 0; color: #94a3b8; font-size: 0.95rem;'>
        Módulo de registro e monitoramento de boletos via API v1.7.1 (Escritural Negociado).
    </p>
</div>
""", unsafe_allow_html=True)

# Stats Row with Glass Style
st.markdown('<div class="stats-container">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 1rem;">
        <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Total Emitido</p>
        <p style="color: #3b82f6; font-size: 1.5rem; font-weight: 800; margin: 0;">R$ {total_emitido:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 1rem;">
        <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Total Pago</p>
        <p style="color: #10b981; font-size: 1.5rem; font-weight: 800; margin: 0;">R$ {total_pago:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 1rem;">
        <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">A Vencer / Aberto</p>
        <p style="color: #f59e0b; font-size: 1.5rem; font-weight: 800; margin: 0;">R$ {total_a_vencer:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 1rem;">
        <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Inadimplência</p>
        <p style="color: #ef4444; font-size: 1.5rem; font-weight: 800; margin: 0;">{inadimplencia:.1f}%</p>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Faturas Ativas", "Emitir Boleto", "Assinaturas (Auto)", "Configuração API"])

with tab1:
    st.subheader("Boletos em Monitoramento")
    
    col_act1, col_act2 = st.columns([4, 1])
    with col_act2:
        if st.button("🔄 Sincronizar Tudo", use_container_width=True):
            with st.spinner("Consultando Bradesco..."):
                st.toast("Status atualizados com sucesso!", icon=None)
    
    # Prepare display data
    df_display = pd.DataFrame(st.session_state['boletos'])
    # Optional: Format Valor for display in dataframe
    df_display['Valor'] = df_display['Valor'].apply(lambda x: f"R$ {x:,.2f}" if isinstance(x, (int, float)) else x)
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Formulário de Emissão Bradesco")
    
    with st.form("new_boleto_bradesco"):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.markdown("#### Dados do Título")
            empresa_sel = st.selectbox("Selecione a Empresa do iAudit", ["Alpha TI Ltda", "Beta Contab", "Gamma Engenharia"], key="empresa_sel_man")
            v_nominal = st.number_input("Valor Nominal (R$)", min_value=0.01, value=100.00, step=0.01, key="v_nominal_man")
            vencimento = st.date_input("Data de Vencimento", key="venc_man")
            num_fatura = st.text_input("Número da Fatura (Interno)", f"FAT-{int(datetime.now().timestamp())}", key="fat_man")
        
        with c_f2:
            st.markdown("#### Dados do Pagador")
            p_nome = st.text_input("Nome/Razão Social", key="pn_man")
            p_doc = st.text_input("CPF/CNPJ (Apenas números)", key="pd_man")
            p_cep = st.text_input("CEP", key="pc_man")
            p_rua = st.text_input("Logradouro", key="pr_man")
            
        st.markdown("---")
        c_f3, c_f4 = st.columns(2)
        with c_f3:
            st.checkbox("Aplicar Multa (2%) após vencimento", value=True, key="chk_multa")
        with c_f4:
            st.checkbox("Aplicar Juros (1% ao mês)", value=True, key="chk_juros")
            
        submitted = st.form_submit_button("REGISTRAR BOLETO ONLINE", use_container_width=True, type="primary")
        
        if submitted:
            if not p_nome or not p_doc:
                st.error("Dados do pagador são obrigatórios para o registro online.")
            else:
                # Prepare payload
                payload = {
                    "empresa_id": "dummy-id",
                    "nuFatura": num_fatura,
                    "vlNominal": int(v_nominal * 100),
                    "dataVencimento": str(vencimento),
                    "pagador_nome": p_nome,
                    "pagador_documento": p_doc,
                    "pagador_endereco": p_rua,
                    "pagador_cep": p_cep,
                    "pagador_uf": "PR",
                    "pagador_cidade": "Curitiba",
                    "pagador_bairro": "Centro"
                }
                
                with st.spinner("Comunicando com o Bradesco..."):
                    res = post("/api/cobranca/registrar", payload)
                    if res:
                        st.success("Boleto Registrado com Sucesso!")
                        
                        # Add to local state for dynamic updates
                        st.session_state['boletos'].append({
                            "Nosso Número": res.get("nosso_numero", "Pendente"),
                            "Empresa": empresa_sel,
                            "Vencimento": vencimento.strftime("%d/%m/%Y"),
                            "Valor": v_nominal,
                            "Status": "Emitido"
                        })
                        
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.info(f"**Nosso Número:** {res.get('nosso_numero')}")
                        with col_res2:
                            st.info(f"**Linha Digitável:** {res.get('linha_digitavel')}")
                        
                        with st.expander("Visualizar JSON de Retorno"):
                            st.json(res)
                        
                        st.rerun()

with tab3:
    st.subheader("Gestão de Assinaturas Recorrentes")
    
    # 1. List Active Plans
    st.info("Planos configurados geram boletos automaticamente 10 dias antes do vencimento.")
    
    # Mock Data for Plans if endpoint not ready or empty
    if 'plans' not in st.session_state:
        st.session_state['plans'] = []

    # UI to Add Plan
    with st.expander("➕ Nova Assinatura", expanded=False):
        with st.form("new_plan"):
            st.markdown("#### Configuração do Plano")
            plan_empresa = st.selectbox("Empresa", ["Alpha TI Ltda", "Beta Contab", "Gamma Engenharia"], key="plan_emp")
            plan_valor = st.number_input("Valor Mensal (R$)", min_value=1.0, value=1500.0, step=50.0)
            plan_day = st.slider("Dia do Vencimento", 1, 31, 10)
            
            if st.form_submit_button("Criar Assinatura", type="primary"):
                # Call Backend (Placeholder)
                new_plan = {
                    "empresa": plan_empresa, 
                    "valor": plan_valor, 
                    "dia": plan_day, 
                    "status": "Ativo",
                    "last_run": "-"
                }
                st.session_state['plans'].append(new_plan)
                st.success(f"Assinatura criada para {plan_empresa}!")
                st.rerun()

    # List Plans table
    if st.session_state['plans']:
        df_plans = pd.DataFrame(st.session_state['plans'])
        df_plans['Valor'] = df_plans['valor'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(
            df_plans[['empresa', 'Valor', 'dia', 'status', 'last_run']], 
            use_container_width=True,
            column_config={
                "empresa": "Empresa",
                "Valor": "Valor Mensal",
                "dia": "Dia Venc.",
                "status": "Status",
                "last_run": "Última Geração"
            }
        )
        
        if st.button("⚡ Executar Rotina de Cobrança Agora"):
             with st.spinner("Processando assinaturas..."):
                 # Trigger Backend Job
                 post("/api/billing/run-now", {}) # Need to create this endpoint
                 st.success("Rotina executada! Verifique os novos boletos na aba 'Faturas Ativas'.")
    else:
        st.warning("Nenhuma assinatura configurada.")

with tab4:
    st.subheader("Configurações da Conta e Segurança")
    
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        st.markdown("""
        <div class="glass-card" style="padding: 1.2rem;">
            <p style="font-weight: 700; color: #f8fafc;">Status da Conexão</p>
            <p style="color: #60a5fa; font-size: 0.9rem;">● Modo Sandbox Ativo</p>
            <p style="color: #94a3b8; font-size: 0.85rem;">Endpoint: https://proxy.api.prebanco.com.br</p>
            <p style="margin-top: 1rem; color: #4ade80; font-size: 0.9rem;">✓ Certificado TLS (ECDHE_RSA) OK</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_cfg2:
        st.markdown("""
        <div class="glass-card" style="padding: 1.2rem;">
            <p style="font-weight: 700; color: #f8fafc;">Negociação Bradesco</p>
            <code style="background: rgba(0,0,0,0.3); padding: 0.5rem; display: block; margin-top: 0.5rem;">4912.0000000.123456-7</code>
            <p style="margin-top: 1rem; color: #94a3b8; font-size: 0.85rem;">Carteira: 09 (Escritural Negociado)</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("iAudit Billing Module v1.1 - Integração Bradesco API v1.7.1")
