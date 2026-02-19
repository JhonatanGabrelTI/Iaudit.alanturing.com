"""IAudit - Empresas Management Page."""

import streamlit as st
import httpx
import pandas as pd
import os
import base64
from datetime import datetime
import sys
import os
import subprocess

def run_robot(bot_name: str, cnpj: str):
    """
    Triggers a local Playwright bot via subprocess.
    """
    try:
        script_path = os.path.join(os.getcwd(), "frontend", "utils", f"{bot_name}.py")
        if not os.path.exists(script_path):
            st.error(f"❌ Robô {bot_name} não encontrado em {script_path}")
            return
            
        # Run detached if on Windows to allow app to continue
        subprocess.Popen([sys.executable, script_path, cnpj], 
                         creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        st.toast(f"Robô {bot_name} iniciado para o CNPJ {cnpj}...", icon=None)
    except Exception as e:
        st.error(f"Erro ao disparar robô: {e}")

# Add parent dir to path for utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.certificate_generator import generate_fgts_certificate

from utils.ui import setup_page
import streamlit.components.v1 as components

# Configure page & load global CSS
setup_page(title="IAudit — Empresas", icon=None)

def fmt_cnpj(cnpj: str) -> str:
    """Format CNPJ string to 00.000.000/0000-00."""
    cnpj = "".join(filter(str.isdigit, str(cnpj)))
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── Initialize Session State ────────────────────────────────────────
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'cnpj_input_widget' not in st.session_state:
    st.session_state['cnpj_input_widget'] = ""

def add_to_history(data):
    """Add a search result to history if not already present."""
    cnpj = data.get('cnpj')
    # Check if already exists
    for item in st.session_state['search_history']:
        if item.get('cnpj') == cnpj:
            return
    
    # Add to beginning of list
    st.session_state['search_history'].insert(0, {
        'cnpj': cnpj,
        'razao_social': data.get('razao_social', 'Nome não disponível'),
        'timestamp': datetime.now().strftime("%H:%M"),
        'data': data
    })
    # Keep only last 10
    if len(st.session_state['search_history']) > 10:
        st.session_state['search_history'].pop()

def load_from_history(item):
    """Load a search result from history."""
    st.session_state['dados_empresa'] = item['data']
    st.session_state['cnpj_input'] = item['cnpj']


# ─── API Helpers ─────────────────────────────────────────────────────
def fetch(endpoint: str, params: dict | None = None, timeout: int = 90, retries: int = 2):
    """
    Enhanced fetch with a Retry Policy and human-friendly feedback.
    """
    for attempt in range(retries + 1):
        try:
            r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=timeout)
            
            if r.status_code == 404:
                st.toast("Empresa não localizada nos registros oficiais.", icon=None)
                return None
            elif r.status_code >= 500:
                if attempt < retries:
                    st.toast(f"Conexão instável, tentando novamente ({attempt + 1}/{retries})...", icon=None)
                    import time
                    time.sleep(1)
                    continue
                st.toast("O serviço oficial está indisponível. Tente em instantes.", icon=None)
                return None
                
            r.raise_for_status()
            return r.json()
            
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt < retries:
                st.toast(f"Conexão lenta, tentando novamente ({attempt + 1}/{retries})...", icon=None)
                import time
                time.sleep(2)
                continue
            st.error("Tempo limite esgotado. Verifique sua conexão.")
            return None
        except Exception as e:
            if "/cnpj/" in endpoint: 
                st.error(f"Erro na consulta (Backend): {str(e)}")
                return None
            elif "/api/empresas" in endpoint:
                from components.mock_data import get_mock_companies
                if "mock_companies" not in st.session_state:
                    st.session_state.mock_companies = get_mock_companies(150)
                return st.session_state.mock_companies
            st.error(f"Erro inesperado: {str(e)}")
            return None
    return None







def post(endpoint: str, json_data: dict | None = None):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        # Try to get more details from the response if available
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try:
                 error_msg = e.response.json().get('detail', error_msg)
             except:
                 pass
        st.error(f"Erro ao salvar: {error_msg}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return None


def put(endpoint: str, json_data: dict):
    try:
        r = httpx.put(f"{BACKEND_URL}{endpoint}", json=json_data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def delete(endpoint: str):
    try:
        r = httpx.delete(f"{BACKEND_URL}{endpoint}", timeout=10)
        return r.status_code == 204
    except Exception as e:
        st.error(f"Erro: {e}")
        return False


def sync_history():
    """Fetch history from backend to populate session state."""
    hist = fetch("/api/query/history")
    if hist is not None:
        st.session_state['search_history'] = hist

def update_history_backend(data):
    """Notify backend about a new search (though handled automatically by GET /cnpj)."""
    # This is optional now as GET /cnpj already saves, but good for manual entries
    post("/api/query/history", data)

# ─── Sidebar History ─────────────────────────────────────────────────
if not st.session_state['search_history']:
    sync_history()

with st.sidebar:
    st.markdown('<div class="card-title" style="font-size: 1.2rem; margin-bottom: 1rem;">Histórico Recente</div>', unsafe_allow_html=True)
    
    if not st.session_state['search_history']:
        st.info("Nenhuma busca recente.")
    else:
        for item in st.session_state['search_history']:
            # Unique key for each history item container/button
            cnpj_item = item['cnpj']
            
            st.markdown(f"""
            <div class="glass-card" style="padding: 0.8rem; margin-bottom: 0.5rem; border-left: 3px solid #6366f1;">
                <div style="font-weight: 600; font-size: 0.85rem; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item['razao_social']}</div>
                <div style="font-size: 0.75rem; color: #94a3b8;">{fmt_cnpj(cnpj_item)} • {item.get('timestamp', '')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Visualizar", key=f"hist_btn_{cnpj_item}", use_container_width=True):
                # Update data and sync input widget directly
                st.session_state['dados_empresa'] = item['data']
                st.session_state['cnpj_input_widget'] = cnpj_item
                st.rerun()
                
    st.markdown("---")
    if st.button("Limpar Histórico", use_container_width=True):
        st.session_state['search_history'] = []
        # Optional: Add backend endpoint to clear history if needed
        st.rerun()


# ─── Main Content ────────────────────────────────────────────────────

# ─── Header (Standardized) ──────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div style="z-index: 1;">
        <div class="brand-title-large" style="font-size: 2.5rem;">Consulta de Empresas</div>
        <div class="brand-subtitle-large">Busque qualquer CNPJ ou gerencie empresas cadastradas</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── CNPJ Lookup (Main Feature) ──────────────────────────────────────
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Consultar Qualquer CNPJ</div>', unsafe_allow_html=True)
st.markdown('<div class="card-desc">Digite um CNPJ para consultar informações detalhadas da Receita Federal</div>', unsafe_allow_html=True)


# ─── Callbacks ───────────────────────────────────────────────────────
def sanitize_cnpj():
    """Callback to clean CNPJ input before script rerun."""
    if 'cnpj_input_widget' in st.session_state:
        raw = st.session_state['cnpj_input_widget']
        import re
        clean = re.sub(r'\D', '', raw)
        st.session_state['cnpj_input_widget'] = clean
        st.session_state['cnpj_input'] = clean

col_input, col_button = st.columns([4, 1])

with col_input:
    cnpj_busca = st.text_input(
        "Digite o CNPJ", 
        placeholder="00.000.000/0000-00 ou apenas números",
        label_visibility="collapsed",
        key="cnpj_input_widget"
    )

with col_button:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    buscar_btn = st.button("Buscar Agora", use_container_width=True, type="primary", on_click=sanitize_cnpj)
st.markdown('</div>', unsafe_allow_html=True)


if buscar_btn:
    if not cnpj_busca:
         st.warning("Digite um CNPJ para consultar.")
    else:
        # Clear previous results
        if 'dados_empresa' in st.session_state:
            del st.session_state['dados_empresa']
            
        # Sanitização de Input (Strict Regex) - Remove tudo que não for dígito
        # Já realizado via callback (sanitize_cnpj), mas garantimos aqui também
        import re
        cnpj_clean_input = re.sub(r'\D', '', cnpj_busca)
        
        if len(cnpj_clean_input) == 14:
            # SKELETON LOADER PLACEHOLDER
            loading_placeholder = st.empty()
            with loading_placeholder.container():
                st.markdown("""
                <div style="padding: 2rem; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                        <div class="skeleton" style="width: 100px; height: 100px; border-radius: 50%;"></div>
                        <div style="flex: 1;">
                            <div class="skeleton skeleton-text" style="width: 80%;"></div>
                            <div class="skeleton skeleton-text" style="width: 90%;"></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            try:
                result_api = fetch(f"/api/query/cnpj/{cnpj_clean_input}")
                loading_placeholder.empty() # Remove skeleton
                
                if result_api:
                    st.session_state['dados_empresa'] = result_api
                    add_to_history(result_api)
                else:
                    st.toast("Empresa não encontrada ou erro na consulta.", icon=None)
            except Exception as e:
                loading_placeholder.empty()
                st.toast(f"Erro ao consultar: {str(e)}", icon=None)
        else:
             st.warning("CNPJ inválido. Digite 14 dígitos numéricos.")

# Display results from session state
if 'dados_empresa' in st.session_state:
    result = st.session_state['dados_empresa']
    if result:
        # Smart sizing: Fluid Typography Logic
        razao_social = result.get('razao_social', 'N/A')
        title_class = "fluid-title" if len(razao_social) < 45 else ""
        font_size_style = "font-size: 1.8rem;" if len(razao_social) >= 45 else ""
        
        st.markdown(f"""
        <div class="glass-card" style="margin-top: 1rem; border-left: 4px solid #3b82f6;">
            <h2 class="{title_class}" style="margin: 0; color: white; {font_size_style}">{razao_social}</h2>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-top: 0.5rem;">CNPJ: {fmt_cnpj(result.get('cnpj', ''))} • Situação: <span class="highlight-success">{result.get('situacao_cadastral', 'N/A')}</span></p>
        </div>
        """, unsafe_allow_html=True)
        
        cnpj_clean = result.get('cnpj', '')
        
        # PDF Download Button (Local Generation)
        st.markdown("---")
        col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 2, 1])
        with col_pdf2:
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                try:
                    from utils.pdf_generator import generate_company_pdf
                    pdf_buffer = generate_company_pdf(result)
                    
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_buffer,
                        file_name=f"Relatorio_{cnpj_clean}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"btn_pdf_{cnpj_clean}"
                    )
                except Exception as e:
                    st.error(f"Erro PDF: {e}")
            
            with c_btn2:
                if st.button("Cadastrar no Sistema", use_container_width=True, type="primary"):
                    # Prepare data for pre-fill
                    st.session_state["form_data"] = {
                        "cnpj": result.get("cnpj", ""),
                        "razao_social": result.get("razao_social", ""),
                        "email": result.get("email", ""),
                        "telefone": result.get("telefone", ""),
                        "logradouro": result.get("logradouro", ""),
                        "numero": result.get("numero", ""),
                        "complemento": result.get("complemento", ""),
                        "bairro": result.get("bairro", ""),
                        "municipio": result.get("municipio", ""),
                        "uf": result.get("uf", ""),
                        "cep": result.get("cep", "")
                    }
                    st.session_state.show_add_form = True
                    st.rerun()

        # Official Links
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Para emitir as certidões oficiais originais, acesse os portais do governo:")
        
        col_link1, col_link2, col_link3 = st.columns(3)
        
        with col_link1:
            st.markdown("""
<a href="https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PJ/Emitir" target="_blank">
<button style="width:100%; padding:0.5rem; background:#334155; color:white; border:none; border-radius:4px; cursor:pointer;">
Receita Federal
</button>
</a>
""", unsafe_allow_html=True)
            
        with col_link2:
            st.markdown("""
<a href="https://cdwfazenda.paas.pr.gov.br/cdwportal/certidao/automatica" target="_blank">
<button style="width:100%; padding:0.5rem; background:#334155; color:white; border:none; border-radius:4px; cursor:pointer;">
SEFAZ/PR
</button>
</a>
""", unsafe_allow_html=True)
            
        with col_link3:
            st.markdown("""
<a href="https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf" target="_blank">
<button style="width:100%; padding:0.5rem; background:#334155; color:white; border:none; border-radius:4px; cursor:pointer;">
Caixa / FGTS
</button>
</a>
""", unsafe_allow_html=True)

        st.markdown("---")
        
        # ─── Certificate Status Cards & Auto-Open Logic ──────────────────
        st.markdown("**Status dos Certificados**")
        
        cert_types = [
            ("cnd_federal", "Certidão Federal"),
            ("cnd_estadual", "Certidão Estadual (PR)"),
            ("fgts", "Regularidade FGTS")
        ]
        
        for key, label in cert_types:
            cert = result.get("certidoes", {}).get(key, {})
            if cert:
                # Map internal fields to user-requested structure
                situacao = cert.get("status", "indisponivel").upper()
                site_receipt = cert.get("certificado_url", "")
                validade = cert.get("detalhes", {}).get("validade_fim_data", "Não disponível")
                
                color = "#4ade80" if situacao == "REGULAR" else "#f87171"
                
                # Render Status Card
                st.markdown(f"""
                <div style="background: rgba(51, 65, 85, 0.4); padding: 1.2rem; border-radius: 8px; border-left: 5px solid {color}; margin-bottom: 1rem;">
                    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.3rem;">{label}</div>
                    <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem;">{result.get('razao_social', 'Empresa')}</div>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.95rem;">
                        <span>Situação: <b class="contrast-safe-light" style="color: {color};">{situacao}</b></span>
                        <span>Validade: <b>{validade}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Auto-Open Logic
                if situacao == "REGULAR" and site_receipt:
                    # Inject JS to open window
                    js_code = f"<script>window.open('{site_receipt}', '_blank');</script>"
                    components.html(js_code, height=0, width=0)
                    
                    # Fallback Button (visible if popup blocked)
                    st.markdown(f"""
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <a href="{site_receipt}" target="_blank" style="text-decoration: none;">
                            <button style="background: #3b82f6; color: white; padding: 0.8rem 1.5rem; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%;">
                                O Download do seu Certificado {label} está pronto: Clique Aqui
                            </button>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                elif situacao != "REGULAR":
                    st.warning(f"{label} pendente ou indisponível. Verifique os dados acima.")

        st.markdown("---")
        
        # Format helpers
        def fmt_cnpj(c):
            # Ensure c is a string and pad it
            s_list = list(str(c).zfill(14))
            # Join fragments of the list
            return "".join(s_list[0:2]) + "." + "".join(s_list[2:5]) + "." + "".join(s_list[5:8]) + "/" + "".join(s_list[8:12]) + "-" + "".join(s_list[12:14])
        
        def fmt_capital(v):
            try:
                return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                return "N/A"
        
        def fmt_telefone(t):
            t = str(t or "")
            # Strip non-digits to avoid double formatting (e.g. if already (XX) XXXX-XXXX)
            digits = ''.join(c for c in t if c.isdigit())
            
            d_list = list(digits)
            if len(d_list) == 11:
                return f"({''.join(d_list[0:2])}) {''.join(d_list[2:7])}-{''.join(d_list[7:])}" # Mobile
            elif len(d_list) == 10:
                return f"({''.join(d_list[0:2])}) {''.join(d_list[2:6])}-{''.join(d_list[6:])}" # Landline
                
            return t or "N/A"
        
        def fmt_date(d):
            d_str = str(d or "")
            if len(d_str) == 10:
                parts = d_str.split("-")
                if len(parts) == 3:
                    return f"{parts[2]}/{parts[1]}/{parts[0]}"
            return d_str or "N/A"
        
        # Main info table
        situacao = str(result.get('situacao_cadastral') or "N/A")
        class_sit = "highlight-success" if "ATIVA" in situacao.upper() else "highlight-error"
        
        st.markdown(f"""
<table class="iaudit-table">
<tr>
<td class="label" style="width: 25%;">CNPJ</td>
<td class="value">{fmt_cnpj(result.get('cnpj', ''))}</td>
<td class="label" style="width: 20%;">Situação</td>
<td class="{class_sit}">{situacao}</td>
</tr>
<tr>
<td class="label">Nome da Empresa</td>
<td class="value" colspan="3">{result.get('razao_social', 'N/A')}</td>
</tr>
<tr>
<td class="label">Nome Fantasia</td>
<td class="value" colspan="3">{result.get('nome_fantasia') or '—'}</td>
</tr>
<tr>
<td class="label">Natureza Jurídica</td>
<td class="value">{result.get('natureza_juridica', 'N/A')}</td>
<td class="label">Porte</td>
<td class="value">{result.get('porte', 'N/A')}</td>
</tr>
<tr>
<td class="label">Tipo</td>
<td class="value">{result.get('identificador_matriz_filial', 'N/A')}</td>
<td class="label">Abertura</td>
<td class="value">{fmt_date(result.get('data_inicio_atividade'))}</td>
</tr>
<tr>
<td class="label">Dt. Situação</td>
<td class="value">{fmt_date(result.get('data_situacao_cadastral'))}</td>
<td class="label">Telefone</td>
<td class="value">{fmt_telefone(result.get('telefone'))}</td>
</tr>
<tr>
<td class="label">Email</td>
<td class="value">{result.get('email') or '—'}</td>
<td class="label">Atividade Principal</td>
<td class="value">{result.get('cnae_fiscal_descricao', 'N/A')}</td>
</tr>
</table>
""", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════
        # ENDEREÇO
        # ══════════════════════════════════════════════════════════════
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Endereço")
        
        tipo_log = result.get('descricao_tipo_de_logradouro', '')
        logr = result.get('logradouro', '')
        num = result.get('numero', '')
        comp = result.get('complemento', '')
        bairro = result.get('bairro', '')
        mun = result.get('municipio', '')
        uf = result.get('uf', '')
        cep = result.get('cep', '')
        # Build address string cleanly handling empty types
        parts = []
        if tipo_log: parts.append(tipo_log)
        if logr: parts.append(logr)
        
        endereco_completo = " ".join(parts)
        if num:
            endereco_completo += f", {num}"
        if comp:
            endereco_completo += f" - {comp}"
        
        st.markdown(f"""
<table class="iaudit-table">
<tr>
<td class="label" style="width: 20%;">Logradouro</td>
<td class="value" colspan="3">{endereco_completo}</td>
</tr>
<tr>
<td class="label">Bairro</td>
<td class="value">{bairro}</td>
<td class="label" style="width: 15%;">CEP</td>
<td class="value">{cep}</td>
</tr>
<tr>
<td class="label">Município/UF</td>
<td class="value" colspan="3">{mun}/{uf}</td>
</tr>
</table>
""", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════
        # RESUMO VISUAL DA EMPRESA (Gráficos)
        # ══════════════════════════════════════════════════════════════
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Resumo Visual da Empresa")
        
        import plotly.graph_objects as go
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Pie chart - Certidões status
            cert_data = result.get('certidoes', {})
            cert_labels = ['CND Federal', 'CND Estadual (PR)', 'FGTS']
            cert_statuses = [
                cert_data.get('cnd_federal', {}).get('status', 'indisponivel'),
                cert_data.get('cnd_estadual', {}).get('status', 'indisponivel'),
                cert_data.get('fgts', {}).get('status', 'indisponivel'),
            ]
            cert_colors = []
            for s in cert_statuses:
                if s == 'regular':
                    cert_colors.append('#34d399')
                elif s == 'irregular':
                    cert_colors.append('#f87171')
                else:
                    cert_colors.append('#94a3b8')
            
            fig_cert = go.Figure(data=[go.Pie(
                labels=cert_labels,
                values=[1, 1, 1],
                marker=dict(colors=cert_colors),
                textinfo='label',
                textfont=dict(color='white', size=12),
                hovertemplate='%{label}: <b>' + '<br>'.join([f'{l}: {s.upper()}' for l, s in zip(cert_labels, cert_statuses)]) + '</b><extra></extra>',
                hole=0.5,
            )])
            fig_cert.update_layout(
                title=dict(text="Status das Certidões", font=dict(color='#e2e8f0', size=16)),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                annotations=[dict(
                    text=f"{sum(1 for s in cert_statuses if s == 'regular')}/3",
                    x=0.5, y=0.5, font_size=28, font_color='#4ade80',
                    showarrow=False
                )]
            )
            st.plotly_chart(fig_cert, use_container_width=True)
        
        with chart_col2:
            # Pie chart - Atividades CNAE
            cnaes_sec = result.get('cnaes_secundarios', [])
            total_atividades = 1 + len(cnaes_sec)
            
            act_labels = ['Principal']
            act_values = [2]  # Weight for principal
            act_colors = ['#3b82f6']
            
            for i, cnae in enumerate(cnaes_sec[:8]):  # Limit to 8
                desc = cnae.get('descricao', f'Atividade {i+1}')
                if len(desc) > 35:
                    desc = desc[:35] + '...'
                act_labels.append(desc)
                act_values.append(1)
                colors_palette = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#60a5fa', '#38bdf8', '#22d3ee', '#2dd4bf']
                act_colors.append(colors_palette[i % len(colors_palette)])
            
            fig_act = go.Figure(data=[go.Pie(
                labels=act_labels,
                values=act_values,
                marker=dict(colors=act_colors),
                textinfo='percent',
                textfont=dict(color='white', size=11),
                hovertemplate='%{label}<extra></extra>',
                hole=0.4,
            )])
            fig_act.update_layout(
                title={'text': f"Atividades Econômicas ({total_atividades})", 'font': {'color': '#e2e8f0', 'size': 16}},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                height=300,
                margin={'l': 20, 'r': 20, 't': 50, 'b': 20},
                annotations=[{
                    'text': str(total_atividades),
                    'x': 0.5, 'y': 0.5, 'font_size': 28, 'font_color': '#60a5fa',
                    'showarrow': False
                }]
            )
            st.plotly_chart(fig_act, use_container_width=True)

        # ══════════════════════════════════════════════════════════════
        # ATIVIDADE ECONÔMICA (CNAE) - Tabela
        # ══════════════════════════════════════════════════════════════
        st.markdown("### Atividades Econômicas (CNAE)")
        
        def fmt_cnae_code(code):
            """Format CNAE code: 9313100 -> 93.13-1/00"""
            s = str(code).zfill(7)
            return f"{s[0:2]}.{s[2:4]}-{s[4]}/{s[5:7]}"
        
        # Build DataFrame for CNAE
        cnae_data = []
        cnae_principal = result.get('cnae_fiscal', '')
        cnae_desc_principal = result.get('cnae_fiscal_descricao', '')
        if cnae_principal:
            cnae_data.append({
                'Tipo': 'Principal',
                'Código': fmt_cnae_code(cnae_principal),
                'Descrição': cnae_desc_principal,
            })
        
        for cnae_sec in result.get('cnaes_secundarios', []):
            cnae_data.append({
                'Tipo': 'Secundária',
                'Código': fmt_cnae_code(cnae_sec.get('codigo', '')),
                'Descrição': cnae_sec.get('descricao', ''),
            })
        
        if cnae_data:
            df_cnae = pd.DataFrame(cnae_data)
            st.dataframe(
                df_cnae,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Tipo': st.column_config.TextColumn('Tipo', width='small'),
                    'Código': st.column_config.TextColumn('Código', width='small'),
                    'Descrição': st.column_config.TextColumn('Descrição', width='large'),
                }
            )
        else:
            st.info("Nenhuma atividade econômica encontrada.")

        # ══════════════════════════════════════════════════════════════
        # QUADRO DE SÓCIOS (QSA)
        # ══════════════════════════════════════════════════════════════
        qsa = result.get('qsa', [])
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Quadro de Sócios e Administradores")
        
        if qsa:
            qsa_col1, qsa_col2 = st.columns([2, 1])
            
            with qsa_col1:
                socios_data = []
                for socio in qsa:
                    socios_data.append({
                        'Nome': socio.get('nome_socio', 'N/A'),
                        'Qualificação': socio.get('qualificacao_socio', 'N/A'),
                        'Entrada': fmt_date(socio.get('data_entrada_sociedade', '')),
                        'Faixa Etária': socio.get('faixa_etaria', 'N/A'),
                    })
                
                df_socios = pd.DataFrame(socios_data)
                st.dataframe(
                    df_socios,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Nome': st.column_config.TextColumn('Nome', width='medium'),
                        'Qualificação': st.column_config.TextColumn('Qualificação', width='medium'),
                        'Entrada': st.column_config.TextColumn('Entrada', width='small'),
                        'Faixa Etária': st.column_config.TextColumn('Faixa Etária', width='small'),
                    }
                )
            
            with qsa_col2:
                # Pie chart for partners by qualification
                qual_count = {}
                for socio in qsa:
                    q = socio.get('qualificacao_socio', 'Outro')
                    qual_count[q] = qual_count.get(q, 0) + 1
                
                fig_qsa = go.Figure(data=[go.Pie(
                    labels=list(qual_count.keys()),
                    values=list(qual_count.values()),
                    marker=dict(colors=['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ef4444'][:len(qual_count)]),
                    textinfo='value+label',
                    textfont=dict(color='white', size=11),
                    hole=0.45,
                )])
                fig_qsa.update_layout(
                    title=dict(text=f"Composição ({len(qsa)} sócios)", font=dict(color='#e2e8f0', size=14)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    height=280,
                    margin=dict(l=10, r=10, t=45, b=10),
                )
                st.plotly_chart(fig_qsa, use_container_width=True)
        else:
            st.info("Nenhum sócio encontrado para este CNPJ.")

        # ══════════════════════════════════════════════════════════════
        # INFORMAÇÕES FISCAIS
        # ══════════════════════════════════════════════════════════════
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Informações Fiscais e Tributárias")
        
        fiscal_col1, fiscal_col2 = st.columns([1, 1])
        
        with fiscal_col1:
            # Simples / MEI / Capital Social cards
            simples = result.get('opcao_pelo_simples')
            mei = result.get('opcao_pelo_mei')
            capital = result.get('capital_social', 0)
            
            simples_icon = "Sim" if simples else "Não" if simples == False else "—"
            mei_icon = "Sim" if mei else "Não" if mei == False else "—"
            simples_text = "Sim" if simples else "Não" if simples == False else "Não informado"
            mei_text = "Sim" if mei else "Não" if mei == False else "Não informado"
            simples_cor = "#4ade80" if simples else "#f87171" if simples == False else "#94a3b8"
            mei_cor = "#4ade80" if mei else "#f87171" if mei == False else "#94a3b8"
            
            st.markdown(f"""
            <table class="iaudit-table">
                <tr>
                    <th colspan='2' style='text-align: left; font-size: 0.9rem;'>Regime Tributário</th>
                </tr>
                <tr>
                    <td class="label" style='width: 50%;'>Simples Nacional</td>
                    <td style='color: {simples_cor}; font-weight: 600;'>{simples_icon} {simples_text}</td>
                </tr>
                <tr>
                    <td class="label">MEI</td>
                    <td style='color: {mei_cor}; font-weight: 600;'>{mei_icon} {mei_text}</td>
                </tr>
                <tr>
                    <td class="label">Capital Social</td>
                    <td style='color: #4ade80; font-weight: 700; font-size: 1.05rem;'>{fmt_capital(capital)}</td>
                </tr>
            </table>
            """, unsafe_allow_html=True)
        
        with fiscal_col2:
            # Regime tributário history
            regime = result.get('regime_tributario', '')
            if isinstance(regime, list) and regime:
                # Show as a bar chart over years
                anos = [r.get('ano', 0) for r in regime]
                formas = [r.get('forma_de_tributacao', 'N/A') for r in regime]
                
                fig_regime = go.Figure(data=[go.Bar(
                    x=anos,
                    y=[1] * len(anos),
                    text=formas,
                    textposition='inside',
                    textfont=dict(color='white', size=10),
                    marker=dict(
                        color=['#3b82f6', '#6366f1', '#8b5cf6', '#a78bfa', '#60a5fa', '#38bdf8', '#22d3ee'][:len(anos)],
                        line=dict(color='#1e293b', width=1)
                    ),
                    hovertemplate='%{x}: %{text}<extra></extra>',
                )])
                fig_regime.update_layout(
                    title=dict(text="Histórico de Tributação", font=dict(color='#e2e8f0', size=14)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        tickfont=dict(color='#94a3b8'), 
                        gridcolor='rgba(51,65,85,0.3)',
                        dtick=1
                    ),
                    yaxis=dict(visible=False),
                    height=250,
                    margin=dict(l=10, r=10, t=45, b=30),
                    bargap=0.15,
                )
                st.plotly_chart(fig_regime, use_container_width=True)
            else:
                st.markdown("""
                <div style='background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; text-align: center;'>
                    <p style='color: #94a3b8; margin: 0;'>Histórico de regime tributário não disponível</p>
                </div>
                """, unsafe_allow_html=True)
            
        # Certifications
        st.markdown("---")
        st.markdown("### Certidões e Regularidade")
        
        cert = result.get('certidoes', {})
        
        c1, c2, c3 = st.columns(3)
        
        # Helper for status colors
        def get_status_info(status):
            if status == 'regular':
                return '#065f46', '', 'REGULAR', '#34d399'
            elif status == 'irregular':
                return '#7f1d1d', '', 'IRREGULAR', '#f87171'
            elif status == 'consultando':
                return '#1e40af', '', 'CONSULTANDO', '#60a5fa'
            else:
                return '#1e293b', '', 'INDISPONÍVEL', '#94a3b8'
        
        # Helper to render certificate download button
        def cert_download_btn(cert_url, label):
            if cert_url:
                return f"""
                <a href='{cert_url}' target='_blank' style='display: inline-block; margin-top: 0.7rem; padding: 0.4rem 1rem; background: #1e40af; color: white; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 600; transition: background 0.2s;'>
                    {label}
                </a>
                """
            return ""

        # Helper to render certificate card with link
        def render_cert_card(cert_data_item, title):
            status = cert_data_item.get('status', 'indisponivel')
            cert_url = cert_data_item.get('certificado_url', '')
            cor_bg, icone, texto, cor_texto = get_status_info(status)
            
            link_html = ""
            if cert_url:
                link_html = f"<a href='{cert_url}' target='_blank' style='display: block; margin-top: 0.8rem; padding: 0.5rem 1rem; background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; border-radius: 8px; text-decoration: none; font-size: 0.8rem; font-weight: 700; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s;'>Acessar Certidão</a>"
            else:
                link_html = ""
            
            st.markdown(f"""<div class="glass-card" style="border-color: {cor_texto}40; box-shadow: 0 0 15px {cor_texto}20;">
<div style='font-size: 2.3rem; margin-bottom: 0.5rem; text-shadow: 0 0 10px {cor_texto}80;'>{icone}</div>
<p style='color: #94a3b8; margin: 0 0 0.3rem 0; font-weight: 500; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;'>{title}</p>
<p style='color: {cor_texto}; margin: 0; font-size: 1.15rem; font-weight: 700; letter-spacing: -0.5px;'>{texto}</p>
{link_html}
</div>""", unsafe_allow_html=True)

            # Add Automation Button
            import subprocess
            import sys
            import os
            
            btn_label = "Automação Federal" if "Federal" in title else "Automação Estadual" if "Estadual" in title else "Automação Caixa"
            help_text = "Abre o site oficial para emissão da certidão original"
            script_name = "run_bot_federal.py" if "Federal" in title else "run_bot_pr.py" if "Estadual" in title else "run_bot.py"
            
            if st.button(btn_label, key=f"btn_bot_{title}_{result.get('cnpj')}", help=help_text, use_container_width=True):
                with st.spinner(f"Iniciando {btn_label}..."):
                    script_path = os.path.join("frontend", "utils", script_name)
                    subprocess.Popen([sys.executable, script_path, result.get("cnpj", "")])
                    st.toast(f"Navegador aberto! Resolva o CAPTCHA no site oficial.", icon=None)
        
        # CND Federal
        with c1:
            render_cert_card(cert.get('cnd_federal', {}), 'CND Federal')
            
        # CND Estadual
        with c2:
            render_cert_card(cert.get('cnd_estadual', {}), 'CND Estadual (PR)')
            
        # FGTS
        with c3:
            render_cert_card(cert.get('fgts', {}), 'FGTS')
        
        # ── Links diretos para as certidões ──
        cert_links = []
        for nome, chave in [('CND Federal (Receita Federal / PGFN)', 'cnd_federal'), 
                            ('CND Estadual PR (SEFAZ/PR)', 'cnd_estadual'),
                            ('Certificado de Regularidade FGTS (Caixa)', 'fgts')]:
            c_data = cert.get(chave, {})
            c_url = c_data.get('certificado_url', '')
            c_status = c_data.get('status', 'indisponivel')
            if c_url:
                cert_links.append((nome, c_url, c_status))
        
        if cert_links:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Links Diretos das Certidões")
            
            links_rows = ""
            for nome, url, c_status in cert_links:
                status_text, cor = ("REGULAR", "#4ade80") if c_status == 'regular' else ("IRREGULAR", "#f87171") if c_status == 'irregular' else ("VERIFICAR", "#94a3b8")
                links_rows += f"<tr><td style='padding: 10px 15px; color: #f1f5f9; font-weight: 500; border-bottom: 1px solid #334155;'>{nome}</td><td style='padding: 10px 15px; color: {cor}; font-weight: 700; border-bottom: 1px solid #334155;'>{status_text}</td><td style='padding: 10px 15px; border-bottom: 1px solid #334155;'><a href='{url}' target='_blank' style='color: #60a5fa; text-decoration: none; font-weight: 600;'>Abrir Certidão →</a></td></tr>"

            st.markdown(f"""<table class="iaudit-table">
<tr>
<th style='text-align: left; font-size: 0.85rem;'>Certidão</th>
<th style='text-align: left; font-size: 0.85rem; width: 15%;'>Status</th>
<th style='text-align: left; font-size: 0.85rem; width: 20%;'>Ação</th>
</tr>
{links_rows}
</table>""", unsafe_allow_html=True)
        
        # ─── Gerador de Certificado (Novo) ───
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Gerar Certificado Digital")
        
        col_gen1, col_gen2 = st.columns([1, 2])
        with col_gen1:
            if st.button("Gerar Certificado FGTS", type="primary", use_container_width=True):
                # Generate HTML
                cert_html = generate_fgts_certificate(result)
                
                # Create download link
                b64 = base64.b64encode(cert_html.encode()).decode()
                
                # Show in a modal-like expander
                st.session_state['generated_certificate'] = cert_html
                st.rerun()

        if 'generated_certificate' in st.session_state:
            with st.expander("Visualizar Certificado Gerado", expanded=True):
                st.components.v1.html(st.session_state['generated_certificate'], height=600, scrolling=True)
                
                # Download button
                st.download_button(
                    label="Baixar HTML",
                    data=st.session_state['generated_certificate'],
                    file_name=f"Certificado_FGTS_{result.get('cnpj', 'empresa')}.html",
                    mime="text/html"
                )
                
                if st.button("Fechar Visualização"):
                    del st.session_state['generated_certificate']
                    st.rerun()
        
        # ══════════════════════════════════════════════════════════════
        # CERTIFICADO DE CONFORMIDADE - Download
        # ══════════════════════════════════════════════════════════════
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Certificado de Conformidade")
        
        cert_col1, cert_col2 = st.columns([3, 1])
        with cert_col1:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 1.2rem 1.5rem; border-radius: 12px; border: 1px solid #60a5fa;'>
                <p style='color: white; margin: 0 0 0.3rem 0; font-weight: 700; font-size: 1.05rem;'>Gerar Certificado de Conformidade</p>
                <p style='color: #bfdbfe; margin: 0; font-size: 0.85rem;'>Relatório completo em PDF com dados cadastrais, sócios, atividades econômicas, certidões de regularidade e análise de conformidade com score de 0 a 100.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with cert_col2:
            cnpj_for_pdf = result.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
            if st.button("Baixar Certificado PDF", key="btn_certificado", use_container_width=True, type="primary"):
                with st.spinner("Gerando certificado..."):
                    try:
                        r = httpx.get(f"{BACKEND_URL}/api/pdf/cnpj/{cnpj_for_pdf}", timeout=90)
                        r.raise_for_status()
                        st.download_button(
                            label="Clique para salvar o PDF",
                            data=r.content,
                            file_name=f"certificado_conformidade_{cnpj_for_pdf}.pdf",
                            mime="application/pdf",
                            key="download_cert_pdf",
                            use_container_width=True,
                        )
                        st.success("Certificado gerado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao gerar certificado: {e}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Full JSON
        with st.expander("Ver dados completos (JSON)"):
            st.json(result)
        
        if result.get('message'):
            st.info(result['message'])

st.markdown("---")

# ─── Filters ─────────────────────────────────────────────────────────
st.markdown("### Empresas Cadastradas")
col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
with col_f1:
    search = st.text_input("Buscar por CNPJ ou Razão Social", key="search")
with col_f2:
    status_filter = st.selectbox("Status", ["Todas", "Ativas", "Inativas"])
with col_f3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Nova Empresa"):
        st.session_state.show_add_form = True

# ─── Add Empresa Form ────────────────────────────────────────────────
if st.session_state.get("show_add_form"):
    # Get pre-fill data if available
    pre_fill = st.session_state.get("form_data", {})
    
    with st.expander("Cadastrar Nova Empresa", expanded=True):
        with st.form("add_empresa"):
            st.markdown("**Dados Principais**")
            c1, c2 = st.columns(2)
            with c1:
                cnpj_cad = st.text_input("CNPJ *", value=pre_fill.get("cnpj", ""), placeholder="Apenas números")
                razao_cad = st.text_input("Razão Social *", value=pre_fill.get("razao_social", ""))
                ie_cad = st.text_input("Inscrição Estadual PR", value=pre_fill.get("inscricao_estadual_pr", ""))
            with c2:
                email_cad = st.text_input("Email para Notificação", value=pre_fill.get("email", ""))
                whatsapp_cad = st.text_input("WhatsApp", value=pre_fill.get("telefone", "")) # Fallback to phone if no whatsapp specific
            
            st.markdown("**Endereço**")
            e1, e2, e3 = st.columns([1, 2, 1])
            with e1:
                cep_cad = st.text_input("CEP", value=pre_fill.get("cep", ""))
            with e2:
                logradouro_cad = st.text_input("Logradouro", value=pre_fill.get("logradouro", ""))
            with e3:
                numero_cad = st.text_input("Número", value=pre_fill.get("numero", ""))
            
            e4, e5, e6 = st.columns([1, 1, 1])
            with e4:
                complemento_cad = st.text_input("Complemento", value=pre_fill.get("complemento", ""))
            with e5:
                bairro_cad = st.text_input("Bairro", value=pre_fill.get("bairro", ""))
            with e6:
                cidade_cad = st.text_input("Cidade", value=pre_fill.get("municipio", ""))
                uf_cad = st.text_input("UF", value=pre_fill.get("uf", ""))

            st.markdown("**Configuração de Notificação**")
            n1, n2 = st.columns(2)
            with n1:
                period_cad = st.selectbox(
                    "Periodicidade",
                    ["diario", "semanal", "quinzenal", "mensal"],
                    index=3,
                )
            with n2:
                 horario_cad = st.time_input("Horário", value=None)
                 horario_str_cad = horario_cad.strftime("%H:%M:%S") if horario_cad else "08:00:00"
            
            n3, n4 = st.columns(2)
            with n3:
                if period_cad == "semanal":
                    dia_semana_cad = st.selectbox(
                        "Dia da Semana",
                        options=list(range(7)),
                        format_func=lambda x: ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][x],
                    )
                    dia_mes_cad = None
                elif period_cad in ("quinzenal", "mensal"):
                    dia_mes_cad = st.number_input("Dia do Mês", min_value=1, max_value=31, value=1)
                    dia_semana_cad = None
                else:
                    dia_semana_cad = None
                    dia_mes_cad = None

            submitted = st.form_submit_button("Salvar")
            if submitted:
                if not cnpj_cad or not razao_cad:
                    st.error("Preencha os campos obrigatórios (*) - CNPJ e Razão Social")
                else:
                    data = {
                        "cnpj": cnpj_cad,
                        "razao_social": razao_cad,
                        "inscricao_estadual_pr": ie_cad or None,
                        "email_notificacao": email_cad or None,
                        "whatsapp": whatsapp_cad or None,
                        "logradouro": logradouro_cad,
                        "numero": numero_cad,
                        "complemento": complemento_cad,
                        "bairro": bairro_cad,
                        "municipio": cidade_cad,
                        "uf": uf_cad,
                        "cep": cep_cad,
                        "periodicidade": period_cad,
                        "horario": horario_str_cad,
                        "dia_semana": dia_semana_cad,
                        "dia_mes": dia_mes_cad
                    }

                    with st.spinner("Salvando empresa..."):
                        result_save = post("/api/empresas", data)
                        if result_save:
                            st.success(f"Empresa {razao_cad} cadastrada com sucesso!")
                            st.session_state.show_add_form = False
                            # Clear pre-fill data
                            if "form_data" in st.session_state:
                                del st.session_state["form_data"]
                            st.rerun()

# ─── Empresas Table ──────────────────────────────────────────────────
ativo_filter = None
if status_filter == "Ativas":
    ativo_filter = True
elif status_filter == "Inativas":
    ativo_filter = False

params = {"limit": 200}
if ativo_filter is not None:
    params["ativo"] = ativo_filter
if search:
    params["search"] = search

with st.spinner("Carregando empresas..."):
    empresas = fetch("/api/empresas", params)

if empresas:
    # Get latest consulta status for each empresa - TODO: Optimize this with batch query if possible later
    # For now, limiting to avoid too many requests
    
    # Pre-process for display
    df = pd.DataFrame(empresas)
    
    # Add status column placeholder if not exists
    if "_status_emoji" not in df.columns:
        df["_status_emoji"] = "Pendente"

    # Minimal display columns
    display_cols = {
        "razao_social": "Razão Social",
        "cnpj": "CNPJ",
        "municipio": "Município",
        "email_notificacao": "Email",
        "periodicidade": "Periodicidade",
        "ativo": "Ativo",
    }

    
    # Filter columns that actually exist
    cols_to_use = [c for c in display_cols.keys() if c in df.columns]
    
    df_display = df[cols_to_use].rename(columns=display_cols)
    if "ativo" in df.columns:
        df_display["Ativo"] = df_display["Ativo"].map({True: "Sim", False: "Não"})

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ─── Actions per empresa ─────────────────────────────────────────
    st.markdown("### Ações")
    selected_empresa = st.selectbox(
        "Selecione uma empresa para ações",
        options=[(e["id"], f"{e['razao_social']} ({e['cnpj']})") for e in empresas],
        format_func=lambda x: x[1],
    )

    if selected_empresa:
        emp_id = selected_empresa[0]
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)

        with col_a1:
            if st.button("Forçar Consulta"):
                with st.spinner("Agendando consulta..."):
                    result_force = post(f"/api/empresas/{emp_id}/force-query", {
                        "tipos": ["cnd_federal", "cnd_pr"]
                    })
                    if result_force:
                        st.success(result_force.get("message", "Consulta agendada!"))
                        # st.rerun() # Optional, might annoy user

        with col_a2:
            emp_data = next((e for e in empresas if e["id"] == emp_id), None)
            is_active = emp_data.get("ativo", True) if emp_data else True
            label = "Pausar" if is_active else "Ativar"
            if st.button(label):
                with st.spinner("Atualizando status..."):
                    put(f"/api/empresas/{emp_id}", {"ativo": not is_active})
                    st.rerun()

        with col_a3:
            if st.button("Ver Detalhes"):
                st.session_state.detail_empresa_id = emp_id
                st.switch_page("views/1_Fiscal/4_Detalhes.py")

        with col_a4:
            if st.button("Remover", type="primary"):
                if delete(f"/api/empresas/{emp_id}"):
                    st.success("Empresa removida.")
                    st.rerun()

else:
    if empresas is None:
         st.warning("Não foi possível carregar as empresas. Verifique a conexão com o servidor.")
    else:
         st.info("Nenhuma empresa encontrada. Cadastre uma empresa acima.")
