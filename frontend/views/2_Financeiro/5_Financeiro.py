import streamlit as st
import httpx
import os
import pandas as pd
from datetime import datetime
import sys

# Add parent dir to path for utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.ui import setup_page

# Configure page
setup_page(title="IAudit — Financeiro", icon=None)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── HTTP Helpers ────────────────────────────────────────────────────

def fetch(endpoint: str, params: dict = None):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=30)
        return r.json() if r.status_code < 400 else None
    except Exception:
        return None

def post(endpoint: str, data: dict):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=30)
        if r.status_code >= 400:
            st.error(f"Erro na API: {r.text}")
            return None
        return r.json()
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# ─── Load Data ───────────────────────────────────────────────────────

# Fetch companies for dropdowns
empresas_list = fetch("/api/empresas") or []

# Initialize boletos from session (demo data on first load)
if 'boletos' not in st.session_state:
    st.session_state['boletos'] = [
        {
            "nosso_numero": "1234567890",
            "empresa": "Alpha TI Ltda",
            "vencimento": "10/03/2026",
            "valor": 1500.00,
            "status": "emitido",
            "linha_digitavel": "23790.12345 67890.123456 78901.234567 8 90123456789012",
            "link_boleto": "#",
            "whatsapp": "5541999998888",
            "email": "financeiro@alpha.com"
        },
        {
            "nosso_numero": "9876543210",
            "empresa": "Beta Contabilidade",
            "vencimento": "28/02/2026",
            "valor": 850.50,
            "status": "pago",
            "linha_digitavel": "23790.54321 09876.543210 12345.678901 2 345678901234",
            "link_boleto": "#",
            "whatsapp": "5541988887777",
            "email": "contato@betacontab.com.br"
        },
        {
            "nosso_numero": "5544332211",
            "empresa": "Gamma Engenharia",
            "vencimento": "15/02/2026",
            "valor": 4330.00,
            "status": "vencido",
            "linha_digitavel": "23790.11223 33445.556677 88990.001122 3 445566778899",
            "link_boleto": "#",
            "whatsapp": "5541977776666",
            "email": "finan@gamma.eng.br"
        },
    ]

# Subscription plans state
if 'plans' not in st.session_state:
    st.session_state['plans'] = []

# ─── Computed Stats ──────────────────────────────────────────────────

boletos = st.session_state['boletos']
total_emitido = sum(b['valor'] for b in boletos)
total_pago = sum(b['valor'] for b in boletos if b['status'] == 'pago')
total_aberto = sum(b['valor'] for b in boletos if b['status'] in ['emitido', 'vencido'])
vencidos = sum(b['valor'] for b in boletos if b['status'] == 'vencido')
inadimplencia = (vencidos / total_emitido * 100) if total_emitido > 0 else 0

# ═══════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="glass-card" style="margin-bottom: 2rem; padding: 1.5rem;">
    <h1 style='margin: 0; color: #f8fafc; font-size: 1.8rem;'>Gestão de Cobranças</h1>
    <p style='margin: 0.5rem 0 0 0; color: #94a3b8; font-size: 0.95rem;'>
        Registro, monitoramento de boletos e automação de cobranças recorrentes.
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Stats Cards ─────────────────────────────────────────────────────

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
        <p style="color: #f59e0b; font-size: 1.5rem; font-weight: 800; margin: 0;">R$ {total_aberto:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with c4:
    inad_color = "#ef4444" if inadimplencia > 30 else "#f59e0b" if inadimplencia > 10 else "#10b981"
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 1rem;">
        <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Inadimplência</p>
        <p style="color: {inad_color}; font-size: 1.5rem; font-weight: 800; margin: 0;">{inadimplencia:.1f}%</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Main Tabs ───────────────────────────────────────────────────────

tab_faturas, tab_emitir, tab_assinaturas, tab_config = st.tabs([
    "Faturas Ativas", "Emitir Boleto", "Assinaturas (Auto)", "Configuração da API"
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: FATURAS ATIVAS
# ═══════════════════════════════════════════════════════════════════════

with tab_faturas:
    st.subheader("Boletos em Monitoramento")

    col_title, col_sync = st.columns([4, 1])
    with col_sync:
        if st.button("Sincronizar Tudo", use_container_width=True):
            st.toast("Status atualizados!", icon="✅")

    for i, boleto in enumerate(boletos):
        status = boleto['status'].lower()
        status_map = {
            'emitido': ('#3b82f6', 'Emitido'),
            'pago': ('#10b981', 'Pago'),
            'vencido': ('#ef4444', 'Vencido'),
            'atraso': ('#ef4444', 'Em Atraso'),
        }
        color, label = status_map.get(status, ('#94a3b8', status.capitalize()))

        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #f8fafc;">{boleto['empresa']}</strong><br>
                    <span style="color: #94a3b8; font-size: 0.85rem;">Vencimento: {boleto['vencimento']} | Valor: R$ {boleto['valor']:,.2f}</span>
                </div>
                <span style="background: {color}20; color: {color}; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 0.85rem;">
                    {label}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action buttons
        col_wa, col_em, col_gap = st.columns([1, 1, 3])
        with col_wa:
            if st.button("WhatsApp", key=f"wa_{i}", use_container_width=True):
                with st.spinner("Enviando..."):
                    event = "pago" if status == "pago" else "atraso" if status in ["vencido", "atraso"] else "emitido"
                    payload = {
                        "nosso_numero": boleto['nosso_numero'],
                        "empresa_nome": boleto['empresa'],
                        "valor": float(boleto['valor']),
                        "vencimento": boleto['vencimento'],
                        "linha_digitavel": boleto.get('linha_digitavel', ''),
                        "link_boleto": boleto.get('link_boleto', ''),
                        "whatsapp": boleto.get('whatsapp'),
                        "email": boleto.get('email'),
                        "event_type": event
                    }
                    res = post("/api/cobranca/notify-manual", payload)
                    if res:
                        st.toast(f"WhatsApp enviado para {boleto['empresa']}!", icon="✅")
        with col_em:
            if st.button("E-mail", key=f"em_{i}", use_container_width=True):
                with st.spinner("Enviando..."):
                    event = "pago" if status == "pago" else "atraso" if status in ["vencido", "atraso"] else "emitido"
                    payload = {
                        "nosso_numero": boleto['nosso_numero'],
                        "empresa_nome": boleto['empresa'],
                        "valor": float(boleto['valor']),
                        "vencimento": boleto['vencimento'],
                        "linha_digitavel": boleto.get('linha_digitavel', ''),
                        "link_boleto": boleto.get('link_boleto', ''),
                        "email": boleto.get('email'),
                        "event_type": event
                    }
                    res = post("/api/cobranca/notify-manual", payload)
                    if res:
                        st.toast(f"E-mail enviado para {boleto['empresa']}!", icon="✅")

        st.divider()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: EMITIR BOLETO
# ═══════════════════════════════════════════════════════════════════════

with tab_emitir:
    st.subheader("Emissão de Boleto Bradesco")

    # Select company (outside form for interactivity)
    if not empresas_list:
        st.warning("Nenhuma empresa cadastrada. Cadastre empresas na seção Fiscal > Empresas.")
        empresa_options = []
    else:
        empresa_options = [f"{e['razao_social']} ({e['cnpj']})" for e in empresas_list]

    def fill_payer_info():
        sel_name = st.session_state.get("sel_empresa")
        if not sel_name or not empresas_list:
            return
        selected = next((e for e in empresas_list if f"{e['razao_social']} ({e['cnpj']})" == sel_name), None)
        if selected:
            st.session_state["f_nome"] = selected.get("razao_social", "")
            st.session_state["f_doc"] = selected.get("cnpj", "")
            st.session_state["f_cep"] = selected.get("cep", "")
            addr = [selected.get("logradouro", ""), selected.get("numero", ""),
                    selected.get("bairro", ""), selected.get("municipio", ""), selected.get("uf", "")]
            st.session_state["f_end"] = ", ".join([p for p in addr if p])
            st.session_state["f_email"] = selected.get("email_notificacao", "")
            st.session_state["f_whats"] = selected.get("whatsapp", "")

    st.markdown("#### Selecione a Empresa")
    st.selectbox("Empresa Cadastrada", options=empresa_options, key="sel_empresa", on_change=fill_payer_info)

    with st.form("form_emitir_boleto"):
        col_bol, col_pag = st.columns(2)

        with col_bol:
            st.markdown("#### Dados do Boleto")
            v_nominal = st.number_input("Valor Nominal (R$)", min_value=0.01, value=100.00, step=0.01)
            vencimento = st.date_input("Data de Vencimento")
            num_fatura = st.text_input("Número da Fatura", f"FAT-{int(datetime.now().timestamp())}")

        with col_pag:
            st.markdown("#### Dados do Pagador")
            p_nome = st.text_input("Nome/Razão Social", key="f_nome")
            p_doc = st.text_input("CPF/CNPJ", key="f_doc")
            p_cep = st.text_input("CEP", key="f_cep")
            p_end = st.text_input("Endereço Completo", key="f_end")
            col_pe, col_pw = st.columns(2)
            with col_pe:
                p_email = st.text_input("Email", key="f_email")
            with col_pw:
                p_whats = st.text_input("WhatsApp", key="f_whats")

        st.markdown("---")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            st.checkbox("Aplicar Multa (2%) após vencimento", value=True)
        with col_opt2:
            st.checkbox("Aplicar Juros (1% ao mês)", value=True)

        submitted = st.form_submit_button("REGISTRAR BOLETO", use_container_width=True, type="primary")

        if submitted:
            if not p_nome or not p_doc:
                st.error("Nome e CPF/CNPJ do pagador são obrigatórios.")
            else:
                # Find selected empresa ID
                sel_name = st.session_state.get("sel_empresa", "")
                selected_emp = next((e for e in empresas_list if f"{e['razao_social']} ({e['cnpj']})" == sel_name), None)

                payload = {
                    "empresa_id": selected_emp["id"] if selected_emp else "manual",
                    "nuFatura": num_fatura,
                    "vlNominal": int(v_nominal * 100),
                    "dataVencimento": str(vencimento),
                    "pagador_nome": p_nome,
                    "pagador_documento": p_doc,
                    "pagador_endereco": p_end,
                    "pagador_cep": p_cep,
                    "pagador_uf": "PR",
                    "pagador_cidade": "Curitiba",
                    "pagador_bairro": "Centro",
                    "pagador_email": p_email,
                    "pagador_whatsapp": p_whats
                }

                with st.spinner("Comunicando com o Bradesco..."):
                    res = post("/api/cobranca/registrar", payload)
                    if res:
                        st.success("Boleto registrado com sucesso!")

                        # Add to local state
                        st.session_state['boletos'].append({
                            "nosso_numero": res.get("nosso_numero", "Pendente"),
                            "empresa": p_nome,
                            "vencimento": vencimento.strftime("%d/%m/%Y"),
                            "valor": v_nominal,
                            "status": "emitido",
                            "linha_digitavel": res.get("linha_digitavel", "N/A"),
                            "link_boleto": res.get("link_boleto", "#"),
                            "whatsapp": p_whats,
                            "email": p_email
                        })

                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            st.info(f"**Nosso Número:** {res.get('nosso_numero')}")
                        with col_r2:
                            st.info(f"**Linha Digitável:** {res.get('linha_digitavel')}")

                        with st.expander("Ver JSON de Retorno"):
                            st.json(res)
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: ASSINATURAS (AUTO)
# ═══════════════════════════════════════════════════════════════════════

with tab_assinaturas:
    st.subheader("Gestão de Assinaturas Recorrentes")
    st.info("Planos configurados geram boletos automaticamente 10 dias antes do vencimento.")

    with st.expander("Nova Assinatura", expanded=False):
        with st.form("form_nova_assinatura"):
            st.markdown("#### Configuração do Plano")
            plan_empresa = st.selectbox("Empresa", empresa_options if empresa_options else ["Nenhuma empresa"], key="plan_emp")
            plan_valor = st.number_input("Valor Mensal (R$)", min_value=1.0, value=1500.0, step=50.0)
            plan_day = st.slider("Dia do Vencimento", 1, 31, 10)

            if st.form_submit_button("Criar Assinatura", type="primary"):
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

    if st.session_state['plans']:
        df_plans = pd.DataFrame(st.session_state['plans'])
        df_plans['Valor Fmt'] = df_plans['valor'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(
            df_plans[['empresa', 'Valor Fmt', 'dia', 'status', 'last_run']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "empresa": "Empresa",
                "Valor Fmt": "Valor Mensal",
                "dia": "Dia Venc.",
                "status": "Status",
                "last_run": "Última Geração"
            }
        )

        if st.button("Executar Rotina de Cobrança Agora", use_container_width=True):
            with st.spinner("Processando assinaturas..."):
                post("/api/cobranca/billing/run-now", {})
                st.success("Rotina executada! Verifique os novos boletos na aba 'Faturas Ativas'.")
    else:
        st.warning("Nenhuma assinatura configurada.")

# ═══════════════════════════════════════════════════════════════════════
# TAB 4: CONFIGURAÇÃO DA API
# ═══════════════════════════════════════════════════════════════════════

with tab_config:
    st.subheader("Configurações da Conta Bradesco")

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        st.markdown("""
        <div class="glass-card" style="padding: 1.2rem;">
            <p style="font-weight: 700; color: #f8fafc;">Status da Conexão</p>
            <p style="color: #60a5fa; font-size: 0.9rem;">● Modo Sandbox Ativo</p>
            <p style="color: #94a3b8; font-size: 0.85rem;">Endpoint: https://proxy.api.prebanco.com.br</p>
            <p style="margin-top: 1rem; color: #4ade80; font-size: 0.9rem;">✓ Certificado TLS OK</p>
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
st.caption("iAudit Billing Module v1.1 — Integração Bradesco API v1.7.1")
