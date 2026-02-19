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
setup_page(title="IAudit — Comunicações", icon=None)

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

def delete(endpoint: str):
    try:
        r = httpx.delete(f"{BACKEND_URL}{endpoint}", timeout=30)
        return r.json() if r.status_code < 400 else None
    except Exception:
        return None

# ─── Load Settings ───────────────────────────────────────────────────

settings_data = fetch("/api/comunicacao/settings") or {
    "robo_ativo": True,
    "mensagens_ativas": True,
    "notificar_erro": True,
    "notificar_sucesso": False,
    "whatsapp_provider": "Evolution API",
    "gmail_method": "SMTP Fallback",
    "template_wa_cobranca": "iAudit: Seu boleto vence em {vencimento}. Valor: R$ {valor}. Linha: {linha}",
    "template_wa_atraso": "iAudit: Constatamos que seu boleto venceu em {vencimento}. Regularize para evitar protesto.",
    "template_wa_alerta": "IAudit Alerta: Empresa {empresa} possui pendência {tipo}. Situação: {situacao}."
}

# ═══════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="glass-card" style="margin-bottom: 2rem; padding: 1.5rem;">
    <h1 style='margin: 0; color: #f8fafc; font-size: 1.8rem;'>Centro de Controle de Mensagens</h1>
    <p style='margin: 0.5rem 0 0 0; color: #94a3b8; font-size: 0.95rem;'>
        Monitore a automação e realize disparos manuais de cobrança e avisos.
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Main Tabs ───────────────────────────────────────────────────────

tab_auto, tab_manual = st.tabs(["Automático (Robô)", "Manual (Disparo Pontual)"])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════════════

with tab_auto:

    # Status banners
    c_stat1, c_stat2 = st.columns(2)
    with c_stat1:
        robot_active = settings_data.get("robo_ativo", False)
        robot_color = "#10b981" if robot_active else "#ef4444"
        robot_label = "ATIVO" if robot_active else "INATIVO"
        st.markdown(f"""
        <div class="glass-card" style="margin-bottom: 1rem; border-left: 5px solid {robot_color}; padding: 1rem;">
            <span style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Motor do Robô:</span>
            <b style="color: {robot_color}; margin-left: 0.5rem;">{robot_label}</b>
        </div>
        """, unsafe_allow_html=True)

    with c_stat2:
        msg_active = settings_data.get("mensagens_ativas", False)
        msg_color = "#10b981" if msg_active else "#ef4444"
        msg_label = "LIBERADO" if msg_active else "BLOQUEADO"
        st.markdown(f"""
        <div class="glass-card" style="margin-bottom: 1rem; border-left: 5px solid {msg_color}; padding: 1rem;">
            <span style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Disparo de Mensagens:</span>
            <b style="color: {msg_color}; margin-left: 0.5rem;">{msg_label}</b>
        </div>
        """, unsafe_allow_html=True)

    # ─── Metrics ─────────────────────────────────────────────────────
    stats = fetch("/api/comunicacao/stats") or {"total": 0, "sent": 0, "failed": 0, "success_rate": 0}

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Total Tentativas</p>
            <p style="color: #f8fafc; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['total']}</p>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Enviados</p>
            <p style="color: #10b981; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['sent']}</p>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Falhas</p>
            <p style="color: #ef4444; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['failed']}</p>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        rate = stats['success_rate']
        rate_color = "#10b981" if rate > 90 else "#f59e0b" if rate > 70 else "#ef4444"
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Taxa de Entrega</p>
            <p style="color: {rate_color}; font-size: 1.5rem; font-weight: 800; margin: 0;">{rate:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── Logs ────────────────────────────────────────────────────────
    st.markdown("#### Histórico de Comunicações")

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("Buscar destinatário", placeholder="ex: cafe@empresa.com...")
    with col_f2:
        channel_filter = st.selectbox("Canal", ["Todos", "email", "whatsapp"])
    with col_f3:
        status_filter = st.selectbox("Status", ["Todos", "sent", "failed", "pending"])

    params = {}
    if channel_filter != "Todos":
        params["channel"] = channel_filter
    if status_filter != "Todos":
        params["status"] = status_filter

    raw_logs = fetch("/api/comunicacao/logs", params=params) or []

    if not raw_logs:
        st.info("Nenhum log de comunicação encontrado.")
    else:
        df = pd.DataFrame(raw_logs)
        if search:
            df = df[df['recipient'].str.contains(search, case=False, na=False)]

        df['Horário'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        df['Canal'] = df['channel'].apply(lambda x: "Email" if x == "email" else "WhatsApp")
        df['Destinatário'] = df['recipient']
        df['Status'] = df['status'].apply(lambda x: "Enviado" if x == "sent" else "Falha" if x == "failed" else "Pendente")

        st.dataframe(
            df[['Horário', 'Canal', 'Destinatário', 'Status', 'subject']],
            use_container_width=True,
            hide_index=True,
            column_config={"subject": "Assunto"}
        )

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("Atualizar Logs", use_container_width=True):
            st.rerun()
    with col_b2:
        if st.button("Limpar Histórico", use_container_width=True, type="secondary"):
            if delete("/api/comunicacao/logs"):
                st.success("Logs removidos!")
                st.rerun()

    # Error details
    failures = [l for l in raw_logs if l.get('status') == 'failed']
    if failures:
        with st.expander("Ver Detalhes de Erros Recentes"):
            for fail in failures[:10]:
                st.error(f"**{fail['timestamp']}** | **{fail['recipient']}**\n\nErro: {fail.get('error_message', 'Erro desconhecido')}")

    # ─── Settings Section ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Configurações do Sistema")

    with st.form("system_settings_form"):
        col_cfg1, col_cfg2 = st.columns(2)

        with col_cfg1:
            st.markdown("##### Controles Mestres")
            new_robo_ativo = st.toggle("Ativar Motor do Robô", value=settings_data.get("robo_ativo"))
            new_msgs_ativas = st.toggle("Ativar Envio de Mensagens", value=settings_data.get("mensagens_ativas"))
            st.caption("Quando desligado, o sistema não realiza disparos.")

            st.markdown("---")
            st.markdown("##### Regras de Notificação")
            new_notif_erro = st.checkbox("Notificar irregularidades", value=settings_data.get("notificar_erro"))
            new_notif_sucesso = st.checkbox("Notificar conclusão com sucesso", value=settings_data.get("notificar_sucesso"))

        with col_cfg2:
            st.markdown("##### Provedores")
            new_wa_provider = st.selectbox("WhatsApp Gateway", ["Evolution API", "Twilio", "Z-API", "Web.js (Local)"], index=0)
            new_gmail_method = st.selectbox("Método E-mail", ["Resend API", "SMTP Fallback (Gmail)", "Direct SMTP"], index=1)

            st.markdown("---")
            st.markdown("##### Limites")
            st.number_input("Máx. tentativas por consulta", min_value=1, max_value=10, value=3)
            st.number_input("Intervalo entre tentativas (min)", min_value=1, max_value=60, value=5)

        st.markdown("---")
        st.markdown("##### Templates de Mensagem")
        st.info("Tags: `{vencimento}`, `{valor}`, `{linha}`, `{empresa}`, `{tipo}`, `{situacao}`")

        new_t1 = st.text_area("Fatura Emitida", value=settings_data.get("template_wa_cobranca"))
        new_t2 = st.text_area("Fatura Vencida", value=settings_data.get("template_wa_atraso"))
        new_t3 = st.text_area("Alertas Fiscais", value=settings_data.get("template_wa_alerta"))

        save_btn = st.form_submit_button("SALVAR CONFIGURAÇÕES", use_container_width=True, type="primary")

        if save_btn:
            payload = {
                "robo_ativo": new_robo_ativo,
                "mensagens_ativas": new_msgs_ativas,
                "notificar_erro": new_notif_erro,
                "notificar_sucesso": new_notif_sucesso,
                "whatsapp_provider": new_wa_provider,
                "gmail_method": new_gmail_method,
                "template_wa_cobranca": new_t1,
                "template_wa_atraso": new_t2,
                "template_wa_alerta": new_t3
            }
            res = post("/api/comunicacao/settings", payload)
            if res:
                st.success("Configurações salvas!")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: MANUAL (Disparo Pontual)
# ═══════════════════════════════════════════════════════════════════════

with tab_manual:
    st.subheader("Disparo de Mensagens Pontual")
    st.info("Busque uma empresa por CNPJ para ver suas pendências e enviar notificações manualmente.")

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        cnpj_input = st.text_input("CNPJ da Empresa", placeholder="00.000.000/0000-00")
    with col_s2:
        st.write("")  # spacer
        st.write("")
        btn_search = st.button("Buscar", type="primary", use_container_width=True)

    # Session state for search results
    if "manual_search_result" not in st.session_state:
        st.session_state["manual_search_result"] = None

    if btn_search:
        if not cnpj_input:
            st.warning("Digite um CNPJ para buscar.")
        else:
            with st.spinner("Buscando..."):
                res = fetch("/api/cobranca/search", params={"cnpj": cnpj_input})
                if res and res.get("found"):
                    st.session_state["manual_search_result"] = res
                    st.success("Empresa encontrada!")
                else:
                    st.session_state["manual_search_result"] = None
                    st.error("Empresa não encontrada ou sem boletos vinculados.")

    # Display search results
    data = st.session_state.get("manual_search_result")

    if data:
        empresa = data['empresa']
        found_boletos = data['boletos']

        st.markdown(f"""
        <div class="glass-card" style="padding: 1rem; margin: 1rem 0;">
            <h3 style="margin: 0; color: #f8fafc;">{empresa['razao_social']}</h3>
            <p style="margin: 0.3rem 0 0 0; color: #94a3b8;">
                Email: {empresa.get('email') or 'N/A'} | WhatsApp: {empresa.get('whatsapp') or 'N/A'}
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader(f"Boletos Encontrados ({len(found_boletos)})")

        if not found_boletos:
            st.warning("Esta empresa não possui boletos registrados.")
        else:
            for i, boleto in enumerate(found_boletos):
                b_status = boleto.get('status', '').lower()
                status_colors = {
                    'pago': '#10b981', 'emitido': '#3b82f6',
                    'atraso': '#ef4444', 'vencido': '#ef4444'
                }
                color = status_colors.get(b_status, '#94a3b8')

                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-left: 4px solid {color}; border-radius: 4px; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #f8fafc; font-size: 1.1rem;">R$ {float(boleto.get('valor', 0)):,.2f}</strong><br>
                            <span style="color: #cbd5e1;">Vencimento: {boleto.get('vencimento', 'N/A')}</span>
                        </div>
                        <span style="background: {color}20; color: {color}; padding: 3px 10px; border-radius: 4px; font-weight: bold;">
                            {b_status.upper()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Determine message type by status
                if b_status == 'pago':
                    msg_type = "pago"
                    btn_label = "Enviar Recibo"
                elif b_status in ['atraso', 'vencido']:
                    msg_type = "atraso"
                    btn_label = "Enviar Aviso de Atraso"
                else:
                    msg_type = "emitido"
                    btn_label = "Enviar Cobrança"

                col_a1, col_a2 = st.columns([1, 4])
                with col_a1:
                    if st.button(btn_label, key=f"manual_send_{i}_{boleto.get('id', i)}"):
                        with st.spinner("Enviando..."):
                            payload = {
                                "nosso_numero": boleto.get('nosso_numero', ''),
                                "empresa_nome": empresa['razao_social'],
                                "valor": float(boleto.get('valor', 0)),
                                "vencimento": boleto.get('vencimento', ''),
                                "linha_digitavel": boleto.get('linha_digitavel', ''),
                                "link_boleto": boleto.get('link_boleto', ''),
                                "whatsapp": empresa.get('whatsapp'),
                                "email": empresa.get('email'),
                                "event_type": msg_type
                            }
                            res_notif = post("/api/cobranca/notify-manual", payload)
                            if res_notif:
                                st.toast(f"Mensagem ({msg_type}) enviada!", icon="✅")
                st.divider()

st.markdown("---")
st.caption("iAudit Communication Monitor & Control v2.1")
