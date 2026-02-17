"""IAudit - Empresa Detail Page."""

import streamlit as st
import httpx
import pandas as pd
import os

from utils.ui import setup_page

# Configure page & load global CSS (Theme persistence)
setup_page(title="IAudit — Detalhes", icon=None)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def fetch(endpoint: str, params: dict | None = None, timeout: int = 60):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=timeout)
        if r.status_code == 404:
            st.toast("Empresa não encontrada na base da Receita Federal", icon=None)
            return None
        elif r.status_code >= 500:
            st.toast("Erro de conexão com o servidor de dados", icon=None)
            return None
            
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # Fallback to internal list for browsing, but NOT for direct queries
        if endpoint == "/api/empresas":
             from components.mock_data import get_mock_companies
             if "mock_companies" not in st.session_state:
                 st.session_state.mock_companies = get_mock_companies(150)
             return st.session_state.mock_companies
             
        return None



def put(endpoint: str, json_data: dict):
    try:
        r = httpx.put(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def post(endpoint: str, json_data: dict | None = None):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


# ─── Header ──────────────────────────────────────────────────────────
# ─── Header ──────────────────────────────────────────────────────────
# ─── Header (Standardized) ──────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div style="z-index: 1;">
        <div class="brand-title-large" style="font-size: 2.5rem;">Detalhes da Empresa</div>
        <div class="brand-subtitle-large">Histórico, CNDs e Monitoramento Individual</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Select Empresa ──────────────────────────────────────────────────
empresas = fetch("/api/empresas", {"limit": 500})

if not empresas:
    st.info("Nenhuma empresa cadastrada.")
    st.stop()

# Check if coming from Empresas page
pre_selected = st.session_state.get("detail_empresa_id")

# If we have a pre-selected ID from the previous page, use it directly to avoid selectbox sync issues
if pre_selected:
    # Verify it exists in options
    if any(e["id"] == pre_selected for e in empresas):
        pass
    else:
        st.warning(f"Empresa ID {pre_selected} não encontrada na lista atual.")

empresa_options = [(e["id"], f"{e['razao_social']} ({e['cnpj']})") for e in empresas]
default_idx = 0
if pre_selected:
    for i, (eid, _) in enumerate(empresa_options):
        if eid == pre_selected:
            default_idx = i
            break

# Add a "Back" button for better UX
if st.button("Voltar para Lista"):
    st.switch_page("pages/2_Empresas.py")

selected = st.selectbox(
    "Selecione a Empresa",
    options=empresa_options,
    index=default_idx,
    format_func=lambda x: x[1],
    key="empresa_selector" # Add key for state management
)

if not selected:
    st.stop()

empresa_id = selected[0]

# If the user manually changes the selectbox, update the detail_empresa_id for consistency
if empresa_id != pre_selected:
    st.session_state.detail_empresa_id = empresa_id

empresa = fetch(f"/api/empresas/{empresa_id}")

if not empresa:
    st.error("Empresa não encontrada ou erro ao carregar dados.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()


# ─── Tabs ────────────────────────────────────────────────────────────
tab_resumo, tab_historico, tab_config = st.tabs(["Resumo", "Histórico", "Configuração"])

# ─── Tab: Resumo ─────────────────────────────────────────────────────
with tab_resumo:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Dados Cadastrais</div>', unsafe_allow_html=True)
        
        # Helper to format table rows
        def row(label, value):
            return f"<tr><td class='label'>{label}</td><td class='value'>{value}</td></tr>"
            
        st.markdown(f"""
<table class="iaudit-table">
{row('Razão Social', empresa.get('razao_social', ''))}
{row('CNPJ', empresa.get('cnpj', ''))}
{row('IE PR', empresa.get('inscricao_estadual_pr', '-') or '-')}
{row('Email', empresa.get('email_notificacao', '-') or '-')}
{row('WhatsApp', empresa.get('whatsapp', '-') or '-')}
{row('Status', 'Ativa' if empresa.get('ativo') else 'Inativa')}
</table>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Agendamento</div>', unsafe_allow_html=True)
        period_labels = {
            "diario": "Diário",
            "semanal": "Semanal",
            "quinzenal": "Quinzenal",
            "mensal": "Mensal",
        }
        day_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        dia_info = ""
        p = empresa.get("periodicidade", "")
        if p == "semanal" and empresa.get("dia_semana") is not None:
            dia_info = f" ({day_names[empresa['dia_semana']]})"
        elif p in ("quinzenal", "mensal") and empresa.get("dia_mes") is not None:
            dia_info = f" (dia {empresa['dia_mes']})"

        st.markdown(f"""
<table class="iaudit-table">
{row('Periodicidade', f"{period_labels.get(p, p)}{dia_info}")}
{row('Horário',(empresa.get('horario', '08:00:00')))}
{row('Cadastrado em', (empresa.get('created_at', '') or '')[:10])}
{row('Atualizado em', (empresa.get('updated_at', '') or '')[:10])}
</table>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Latest results
    st.markdown("---")
    st.markdown("#### Últimos Resultados")
    
    col_results = st.columns(3)
    
    idx = 0
    for tipo, label in [("cnd_federal", "CND Federal"), ("cnd_pr", "CND PR"), ("fgts_regularidade", "FGTS")]:
        with col_results[idx]:
            consultas = fetch("/api/consultas", {
                "empresa_id": empresa_id,
                "tipo": tipo,
                "limit": 1,
            })
            
            st.markdown('<div class="kpi-card" style="min-height: 180px;">', unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin-top:0;'>{label}</h3>", unsafe_allow_html=True)
            
            # Initialize variables to avoid NameError if no results
            c = {}
            situacao = ""
            status = ""

            if consultas:
                c = consultas[0]
                situacao = c.get("situacao", "")
                status = c.get("status", "")
                # ... (existing formatting logic) ...
                
            # Automation Buttons based on Type
            import subprocess
            import sys
            import os
            
            if tipo == "fgts_regularidade":
                if st.button("Automação Caixa", key=f"btn_bot_caixa_{tipo}", help="Abre o navegador oficial para baixar a certidão original"):
                    with st.spinner("Iniciando Caixa Bot..."):
                        script_path = os.path.join("frontend", "utils", "run_bot.py")
                        subprocess.Popen([sys.executable, script_path, empresa.get("cnpj", "")])
                        st.toast("Navegador aberto! Resolva o CAPTCHA no site da Caixa.", icon=None)
            
            elif tipo == "cnd_federal":
                if st.button("Automação Federal", key=f"btn_bot_fed_{tipo}", help="Abre o navegador da Receita Federal para emitir a CND original"):
                    with st.spinner("Iniciando Federal Bot..."):
                        script_path = os.path.join("frontend", "utils", "run_bot_federal.py")
                        subprocess.Popen([sys.executable, script_path, empresa.get("cnpj", "")])
                        st.toast("Navegador aberto! Resolva o CAPTCHA no site da Receita.", icon=None)

            elif tipo == "cnd_pr":
                if st.button("Automação Estadual", key=f"btn_bot_pr_{tipo}", help="Abre o navegador da SEFAZ PR para emitir a CND original"):
                    with st.spinner("Iniciando SEFAZ PR Bot..."):
                        script_path = os.path.join("frontend", "utils", "run_bot_pr.py")
                        subprocess.Popen([sys.executable, script_path, empresa.get("cnpj", "")])
                        st.toast("Navegador aberto! Resolva o CAPTCHA no site da SEFAZ.", icon=None)
                
                # Replica Download Button
                from utils.caixa_crf import generate_caixa_crf
                try:
                    pdf_crf = generate_caixa_crf(empresa)
                    st.download_button(
                        label="Baixar CRF (Modelo Caixa)",
                        data=pdf_crf,
                        file_name=f"CRF_{empresa.get('cnpj')}.pdf",
                        mime="application/pdf",
                        key="btn_crf_replica",
                        help="Gera um PDF modelo Caixa com os dados atuais do sistema"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar modelo: {e}")
                
                status_color = "#94a3b8"
                if situacao == "positiva": status_color = "#f87171" # Bad
                elif situacao == "negativa": status_color = "#4ade80" # Good
                elif situacao == "regular": status_color = "#4ade80" # Good
                elif situacao == "irregular": status_color = "#f87171" # Bad
                
                st.markdown(f"<p style='color: {status_color}; font-size: 1.2rem; font-weight: bold;'>{(situacao or status).upper()}</p>", unsafe_allow_html=True)
                
                data_exec = str(c.get("data_execucao", ""))
                data_disp = data_exec[0:10] if len(data_exec) >= 10 else "—"
                st.markdown(f"<p style='color: #cbd5e1; font-size: 0.9rem;'> {data_disp if data_exec else 'Pendente'}</p>", unsafe_allow_html=True)
                
                pdf = c.get("pdf_url")
                if pdf:
                    st.markdown(f"<a href='{pdf}' target='_blank' style='color: #60a5fa; text-decoration: none;'>Download PDF</a>", unsafe_allow_html=True)
            else:
                 st.markdown("<p style='color: #94a3b8;'>Sem dados</p>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1

    # Force query button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Forçar Nova Consulta Agora", key="force_detail", type="primary"):
        result = post(f"/api/empresas/{empresa_id}/force-query", {
            "tipos": ["cnd_federal", "cnd_pr"]
        })
        if result:
            st.success(result.get("message", "Consulta agendada!"))
            st.rerun()

# ─── Tab: Histórico ──────────────────────────────────────────────────
with tab_historico:
    st.markdown("#### Histórico de Consultas")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipo_filter = st.selectbox(
            "Tipo",
            ["Todos", "cnd_federal", "cnd_pr", "fgts_regularidade"],
            key="hist_tipo",
        )
    with col_f2:
        status_filter = st.selectbox(
            "Status",
            ["Todos", "agendada", "processando", "concluida", "erro"],
            key="hist_status",
        )

    params = {"empresa_id": empresa_id, "limit": 50}
    if tipo_filter != "Todos":
        params["tipo"] = tipo_filter
    if status_filter != "Todos":
        params["status"] = status_filter

    consultas = fetch("/api/consultas", params)

    if consultas:
        df = pd.DataFrame(consultas)

        tipo_labels = {
            "cnd_federal": "CND Federal",
            "cnd_pr": "CND PR",
            "fgts_regularidade": "FGTS",
        }
        status_emojis = {
            "agendada": "Agendada",
            "processando": "Processando",
            "concluida": "Concluída",
            "erro": "Erro",
        }
        situacao_emojis = {
            "positiva": "Positiva",
            "negativa": "Negativa",
            "regular": "Regular",
            "irregular": "Irregular",
            "erro": "Erro",
        }

        df["Tipo"] = df["tipo"].map(tipo_labels).fillna(df["tipo"])
        df["Status"] = df["status"].map(status_emojis).fillna(df["status"])
        df["Situação"] = df["situacao"].map(situacao_emojis).fillna("—")
        df["Agendada"] = df["data_agendada"].apply(lambda x: x[:16] if x else "")
        df["Executada"] = df["data_execucao"].apply(lambda x: x[:16] if x else "—")
        df["Tentativas"] = df["tentativas"]

        display_df = df[["Tipo", "Status", "Situação", "Agendada", "Executada", "Tentativas"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # PDF download links
        pdfs = df[df["pdf_url"].notna() & (df["pdf_url"] != "")]
        if not pdfs.empty:
            st.markdown("#### PDFs Disponíveis")
            for _, row in pdfs.iterrows():
                st.markdown(
                    f"- [{row['Tipo']} — {row['Executada']}]({row['pdf_url']})"
                )
    else:
        st.info("Nenhuma consulta registrada para esta empresa.")

# ─── Tab: Configuração ───────────────────────────────────────────────
with tab_config:
    st.markdown("#### Editar Configuração")

    with st.form("edit_config"):
        c1, c2 = st.columns(2)
        with c1:
            new_email = st.text_input(
                "Email para Notificação",
                value=empresa.get("email_notificacao", "") or "",
            )
            new_whatsapp = st.text_input(
                "WhatsApp",
                value=empresa.get("whatsapp", "") or "",
            )
            new_ie = st.text_input(
                "Inscrição Estadual PR",
                value=empresa.get("inscricao_estadual_pr", "") or "",
            )
        with c2:
            period_options = ["diario", "semanal", "quinzenal", "mensal"]
            current_period = empresa.get("periodicidade", "mensal")
            new_period = st.selectbox(
                "Periodicidade",
                period_options,
                index=period_options.index(current_period) if current_period in period_options else 3,
            )
            new_horario = st.text_input(
                "Horário (HH:MM:SS)",
                value=empresa.get("horario", "08:00:00"),
            )
            new_ativo = st.checkbox("Ativo", value=empresa.get("ativo", True))

        if st.form_submit_button("Salvar Alterações"):
            update_data = {
                "email_notificacao": new_email or None,
                "whatsapp": new_whatsapp or None,
                "inscricao_estadual_pr": new_ie or None,
                "periodicidade": new_period,
                "horario": new_horario,
                "ativo": new_ativo,
            }
            result = put(f"/api/empresas/{empresa_id}", update_data)
            if result:
                st.success("Configuração atualizada com sucesso!")
                st.rerun()
