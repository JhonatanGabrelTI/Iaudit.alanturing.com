
"""
New Independent Modules Utilities.
Contains logic for Bulk Import, Red Flag Management, and Scheduler.
Zero Breaking Changes: This file is additive and does not modify existing logic.
"""

import streamlit as st
import httpx
import pandas as pd
import re
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── MODULE 1: BULK IMPORT LOGIC ─────────────────────────────────────

def clean_cnpj(cnpj: str) -> str:
    """Removes non-digits from CNPJ string."""
    return re.sub(r'\D', '', str(cnpj))

def fetch_company_data_independent(cnpj: str):
    """
    Independent fetcher for Bulk Import to avoid touching core fetch logic.
    Returns: dict or None
    """
    try:
        # Mocking the endpoint call structure used in other pages
        # Assuming there's an endpoint /api/empresas/{cnpj} or similar
        # If not, we fall back to the mock logic or whatever the backend provides.
        # Based on previous context, we might use a direct search endpoint
        
        # NOTE: Using a specific endpoint for data retrieval
        response = httpx.get(f"{BACKEND_URL}/api/query/cnpj/{cnpj}", timeout=30.0)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"cnpj": cnpj, "error": "Not Found", "situacao": "DESCONHECIDA"}
        else:
            return {"cnpj": cnpj, "error": f"HTTP {response.status_code}", "situacao": "ERRO"}
            
    except Exception as e:
        return {"cnpj": cnpj, "error": str(e), "situacao": "ERRO"}

def process_bulk_list(cnpjs: list, progress_bar=None):
    """
    Processes a list of CNPJs sequentially.
    Updates session state 'bulk_results' and 'red_flags'.
    """
    if 'bulk_results' not in st.session_state:
        st.session_state['bulk_results'] = []
    
    total = len(cnpjs)
    
    for i, raw_cnpj in enumerate(cnpjs):
        cnpj = clean_cnpj(raw_cnpj)
        if len(cnpj) != 14:
            # Skip valid length check or mark as invalid
            st.session_state['bulk_results'].append({
                "cnpj": raw_cnpj,
                "razao_social": "CNPJ Inválido",
                "situacao": "ERRO",
                "status_icon": "❌"
            })
            continue
            
        # Fetch Data
        data = fetch_company_data_independent(cnpj)
        
        # Process Result
        # Determine status icon/class similar to main app but independent
        situacao = data.get('situacao', 'DESCONHECIDA')
        is_regular = situacao.upper() == 'ATIVA' or situacao.upper() == 'REGULAR' # Adapting to likely API response
        
        result_entry = {
            "cnpj": cnpj,
            "razao_social": data.get('razao_social', 'Desconhecido'),
            "situacao": situacao,
            "status_icon": "✅" if is_regular else "🚩",
            "data_consulta": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        st.session_state['bulk_results'].insert(0, result_entry) # Add to top
        
        # INTEGRATION WITH RED FLAG MODULE
        if not is_regular:
            add_to_red_flags(result_entry)
            
        # Update Progress
        if progress_bar:
            progress_bar.progress((i + 1) / total, text=f"Processando {i+1}/{total}: {cnpj}")

# ─── MODULE 2: RED FLAG MANAGER ──────────────────────────────────────

def add_to_red_flags(company_data):
    """Adds a company to the Red Flag list if not already present."""
    if 'red_flags' not in st.session_state:
        st.session_state['red_flags'] = []
    
    # Check for duplicates
    exists = any(item['cnpj'] == company_data['cnpj'] for item in st.session_state['red_flags'])
    if not exists:
        st.session_state['red_flags'].append(company_data)

def get_red_flags():
    """Retrieves the list of irregular companies."""
    return st.session_state.get('red_flags', [])

# ─── MODULE 3: SCHEDULER LOGIC ───────────────────────────────────────

def schedule_job(job_data):
    """Adds a job to the schedule list."""
    if 'scheduled_jobs' not in st.session_state:
        st.session_state['scheduled_jobs'] = []
        
    st.session_state['scheduled_jobs'].append(job_data)

def get_scheduled_jobs():
    return st.session_state.get('scheduled_jobs', [])
