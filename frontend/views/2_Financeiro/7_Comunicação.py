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

def fetch(endpoint: str, params: dict = None):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=30)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None

def delete(endpoint: str):
    try:
        r = httpx.delete(f"{BACKEND_URL}{endpoint}", timeout=30)
        return r.json() if r.status_code < 400 else None
    except Exception:
        return None

# ─── Data & State ───────────────────────────────────────────────────

settings_data = fetch("/api/comunicacao/settings") or {
    "robo_ativo": True,
    "mensagens_ativas": True,
    "notificar_erro": True,
    "notificar_sucesso": False,
    "whatsapp_provider": "Evolution API",
    "gmail_method": "SMTP Fallback",
    "template_wa_cobranca": "iAudit: Seu boleto vence em {vencimento}. Valor: R$ {valor}. Linha: {linha}",
    "template_wa_atraso": "iAudit: Constatamos que seu boleto venceu em {vencimento}. Regularize para evitar protesto.",
    "template_wa_alerta": "🚨 IAudit Alerta: Empresa {empresa} possui pendência {tipo}. Situação: {situacao}."
}

# ─── UI Content ──────────────────────────────────────────────────────

st.markdown("""
<div class="glass-card" style="margin-bottom: 2rem; padding: 1.5rem;">
    <h1 style='margin: 0; color: #f8fafc; font-size: 1.8rem;'>Centro de Controle de Mensagens</h1>
    <p style='margin: 0.5rem 0 0 0; color: #94a3b8; font-size: 0.95rem;'>
        Monitore a automação e configure as regras de envio do robô IAudit.
    </p>
</div>
""", unsafe_allow_html=True)

# Robot & Messaging Status Banner
c_stat1, c_stat2 = st.columns(2)
with c_stat1:
    robot_status = "ATIVO" if settings_data.get("robo_ativo") else "INATIVO"
    robot_color = "#10b981" if settings_data.get("robo_ativo") else "#ef4444"
    st.markdown(f"""
    <div class="glass-card" style="margin-bottom: 1rem; border-left: 5px solid {robot_color}; padding: 1rem;">
        <span style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Motor do Robô:</span>
        <b style="color: {robot_color}; margin-left: 0.5rem;">{robot_status}</b>
    </div>
    """, unsafe_allow_html=True)

with c_stat2:
    msg_status = "LIBERADO" if settings_data.get("mensagens_ativas") else "BLOQUEADO"
    msg_color = "#10b981" if settings_data.get("mensagens_ativas") else "#ef4444"
    st.markdown(f"""
    <div class="glass-card" style="margin-bottom: 1rem; border-left: 5px solid {msg_color}; padding: 1rem;">
        <span style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Disparo de Mensagens:</span>
        <b style="color: {msg_color}; margin-left: 0.5rem;">{msg_status}</b>
    </div>
    """, unsafe_allow_html=True)

tab_mon, tab_cfg = st.tabs(["Monitoramento", "Configuração do Sistema"])

with tab_mon:
    # ─── Metrics ────────────────────────────────────────────────────────
    stats = fetch("/api/comunicacao/stats") or {"total": 0, "sent": 0, "failed": 0, "success_rate": 0}

    st.markdown('<div class="stats-container">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Total Tentativas</p>
            <p style="color: #f8fafc; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['total']}</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Enviados</p>
            <p style="color: #10b981; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['sent']}</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Falhas</p>
            <p style="color: #ef4444; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['failed']}</p>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        color = "#10b981" if stats['success_rate'] > 90 else "#f59e0b" if stats['success_rate'] > 70 else "#ef4444"
        st.markdown(f"""
        <div class="glass-card" style="text-align: center; padding: 1rem;">
            <p style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Taxa de Entrega</p>
            <p style="color: {color}; font-size: 1.5rem; font-weight: 800; margin: 0;">{stats['success_rate']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── Logs Table ──────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Histórico de Comunicações</div>', unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("Buscar por destinatário ou assunto", placeholder="ex: cafe@empresa.com...")
    with col_f2:
        channel_filter = st.selectbox("Canal", ["Todos", "email", "whatsapp"])
    with col_f3:
        status_filter = st.selectbox("Status", ["Todos", "sent", "failed", "pending"])

    params = {}
    if channel_filter != "Todos": params["channel"] = channel_filter
    if status_filter != "Todos": params["status"] = status_filter

    raw_logs = fetch("/api/comunicacao/logs", params=params) or []

    if not raw_logs:
        st.info("Nenhum log de comunicação encontrado.")
    else:
        df = pd.DataFrame(raw_logs)
        if search:
            df = df[df['recipient'].str.contains(search, case=False) | df['subject'].str.contains(search, case=False, na=False)]
        
        df['Horário'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        df['Canal'] = df['channel'].apply(lambda x: "Email" if x == "email" else "WhatsApp")
        df['Destinatário'] = df['recipient']
        df['Status'] = df['status'].apply(lambda x: "Enviado" if x == "sent" else "Falha" if x == "failed" else "Pendente")
        
        st.dataframe(
            df[['Horário', 'Canal', 'Destinatário', 'Status', 'subject']], 
            use_container_width=True, 
            hide_index=True,
            column_config={"subject": "Assunto/Conteúdo"}
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Atualizar Logs", use_container_width=True):
            st.rerun()
    with col_btn2:
        if st.button("Limpar Todo o Histórico", use_container_width=True, type="secondary"):
            if delete("/api/comunicacao/logs"):
                st.success("Logs removidos!")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Error details
    failures = [l for l in raw_logs if l['status'] == 'failed']
    if failures:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📉 Ver Detalhes de Erros Recentes"):
            for fail in failures[:10]:
                st.error(f"**{fail['timestamp']}** | **{fail['recipient']}**\n\nErro: {fail.get('error_message', 'Erro desconhecido')}")

with tab_cfg:
    st.subheader("Configurações do Robô e Mensagens")
    
    with st.form("system_settings_form"):
        col_cfg1, col_cfg2 = st.columns(2)
        
        with col_cfg1:
            st.markdown("#### ✅ Controles Mestres")
            new_robo_ativo = st.toggle("Ativar Motor do Robô (Consultas)", value=settings_data.get("robo_ativo"))
            new_msgs_ativas = st.toggle("Ativar Envio de Mensagens (WhatsApp/Gmail)", value=settings_data.get("mensagens_ativas"))
            st.caption("Quando desligado, o sistema não realizará disparos de qualquer natureza.")
            
            st.markdown("---")
            st.markdown("#### 📧 Regras de Notificação")
            new_notif_erro = st.checkbox("Notificar ao encontrar irregularidades", value=settings_data.get("notificar_erro"))
            new_notif_sucesso = st.checkbox("Notificar ao concluir com sucesso", value=settings_data.get("notificar_sucesso"))
            
        with col_cfg2:
            st.markdown("#### ☁️ Provedores")
            new_wa_provider = st.selectbox("WhatsApp Gateway", ["Evolution API", "Twilio", "Z-API", "Web.js (Local)"], index=0)
            new_gmail_method = st.selectbox("Metodo E-mail", ["Resend API", "SMTP Fallback (Gmail)", "Direct SMTP"], index=1)
            
            st.markdown("---")
            st.markdown("#### ⏱️ Limites de Automação")
            st.number_input("Máximo de tentativas por consulta", min_value=1, max_value=10, value=3)
            st.number_input("Intervalo entre tentativas (min)", min_value=1, max_value=60, value=5)

        st.markdown("---")
        st.markdown("#### 📝 Templates de Mensagem (WhatsApp/Texto)")
        st.info("Tags disponíveis: `{vencimento}`, `{valor}`, `{linha}`, `{empresa}`, `{tipo}`, `{situacao}`")
        
        new_template_wa_cobranca = st.text_area(
            "Fatura Emitida (Contexto: Boleto)", 
            value=settings_data.get("template_wa_cobranca"),
            help="Mensagem enviada quando um novo boleto é gerado."
        )
        new_template_wa_atraso = st.text_area(
            "Fatura Vencida (Contexto: Cobranca)", 
            value=settings_data.get("template_wa_atraso"),
            help="Aviso amigável de vencimento."
        )
        new_template_wa_alerta = st.text_area(
            "Alertas de Consultas (Contexto: CND/Fiscal)", 
            value=settings_data.get("template_wa_alerta"),
            help="Mensagem enviada quando o robô encontra irregularidades."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        save_btn = st.form_submit_button("SALVAR TODAS AS CONFIGURAÇÕES", use_container_width=True, type="primary")
        
        if save_btn:
            new_payload = {
                "robo_ativo": new_robo_ativo,
                "mensagens_ativas": new_msgs_ativas,
                "notificar_erro": new_notif_erro,
                "notificar_sucesso": new_notif_sucesso,
                "whatsapp_provider": new_wa_provider,
                "gmail_method": new_gmail_method,
                "template_wa_cobranca": new_template_wa_cobranca,
                "template_wa_atraso": new_template_wa_atraso,
                "template_wa_alerta": new_template_wa_alerta
            }
            res = post("/api/comunicacao/settings", new_payload)
            if res:
                st.success("Configurações e Templates salvos com sucesso!")
                st.rerun()

st.markdown("---")
st.caption("iAudit Communication Monitor & Control v2.0 - Advanced AI Messaging Engine")
