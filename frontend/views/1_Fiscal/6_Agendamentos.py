"""IAudit - Task Scheduler Page."""

import streamlit as st
from datetime import datetime
import utils.new_modules as addons
from utils.ui import setup_page

# Configure page
setup_page(title="IAudit — Agendamentos", icon=None)

# ─── Header (Standardized) ──────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div style="z-index: 1;">
        <div class="brand-title-large" style="font-size: 2.5rem;">Automação de Envio</div>
        <div class="brand-subtitle-large">Agende consultas automáticas e envio de relatórios</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── New Schedule Form ───────────────────────────────────────────────
c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Novo Agendamento</div>', unsafe_allow_html=True)
    
    # ─── QUICK PRESETS ───────────────────────────────────────────────────
    tipo_tarefa = st.radio(
        "O que você deseja agendar?",
        ["Relatório Geral", "Alerta de Risco", "Renovação Automática", "Personalizado"],
        horizontal=True
    )
    
    with st.form("scheduler_form"):
        # Auto-fill based on selection
        if tipo_tarefa == "Relatório Geral":
            def_desc = "Relatório Semanal de Conformidade"
            def_acao = "Enviar Relatório por E-mail"
        elif tipo_tarefa == "Alerta de Risco":
            def_desc = "Monitoramento de Irregularidades (Diário)"
            def_acao = "Disparar Alerta de Irregularidade"
        elif tipo_tarefa == "Renovação Automática":
            def_desc = "Renovação de CNDs Vencidas"
            def_acao = "Renovar Certidões Automaticamente"
        else:
            def_desc = ""
            def_acao = "Enviar Relatório por E-mail"
            
        descricao = st.text_input("Descrição", value=def_desc)
        
        c_time1, c_time2 = st.columns(2)
        with c_time1:
            data_envio = st.date_input("Data de Início", min_value=datetime.today())
        with c_time2:
            hora_envio = st.time_input("Horário", value=datetime.now().time())
            
        with st.expander("Opções Avançadas", expanded=(tipo_tarefa == "Personalizado")):
            tipo_acao = st.selectbox(
                "Ação Executada",
                [
                    "Enviar Relatório por E-mail",
                    "Disparar Alerta de Irregularidade",
                    "Renovar Certidões Automaticamente"
                ],
                index=0 if def_acao == "Enviar Relatório por E-mail" else 1 if def_acao == "Disparar Alerta de Irregularidade" else 2
            )
            destinatarios = st.text_input("Emails (Opcional)", placeholder="seunome@empresa.com")
            repetir = st.checkbox("Repetir semanalmente?", value=True)
        
        submitted = st.form_submit_button("Confirmar Agendamento", type="primary")
        
        if submitted:
            if not descricao:
                st.warning("Digite uma descrição.")
            else:
                job_data = {
                    "descricao": descricao,
                    "data": data_envio.strftime("%d/%m/%Y"),
                    "hora": hora_envio.strftime("%H:%M"),
                    "acao": tipo_acao,
                    "status": "Aguardando"
                }
                addons.schedule_job(job_data)
                st.success("Agendado com sucesso!")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Próximas Execuções</div>', unsafe_allow_html=True)
    
    jobs = addons.get_scheduled_jobs()
    
    if not jobs:
        st.info("Nenhuma tarefa agendada.")
        # Mock some examples for visual feedback if empty
        st.markdown("""
        <div style="opacity: 0.5;">
            <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <b>Exemplo: Envio Semanal</b><br>
                <small>20/12/2026 • 08:00</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, job in enumerate(jobs):
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: bold; font-size: 1.1rem;">{job['descricao']}</span>
                    <span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">{job['status']}</span>
                </div>
                <div style="margin-top: 0.5rem; color: #94a3b8; font-size: 0.9rem;">
                    {job['data']} às {job['hora']}<br>
                    {job['acao']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
            
st.markdown("---")
st.caption("O sistema processará as filas automaticamente no horário programado.")
