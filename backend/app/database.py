"""IAudit - Supabase database client wrapper."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import uuid
from typing import Any, List, Dict, Optional

from supabase import create_client, Client

from app.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None
DEMO_MODE = False  # Will be set to True if Supabase fails

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_FILE = os.path.join(DATA_DIR, "local_db.json")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("empresas", []), data.get("consultas", []), data.get("boletos", []), data.get("billing_plans", [])
        except Exception as e:
            logger.error(f"Failed to load local DB: {e}")
    return [], [], [], []

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "empresas": DEMO_EMPRESAS,
                "consultas": DEMO_CONSULTAS,
                "boletos": DEMO_BOLETOS,
                "billing_plans": DEMO_BILLING_PLANS
            }, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save local DB: {e}")

# Initialize from file
DEMO_EMPRESAS, DEMO_CONSULTAS, DEMO_BOLETOS, DEMO_BILLING_PLANS = load_db()

# If empty, we start fresh (User requested "No More Fake Data")
if not DEMO_EMPRESAS:
    DEMO_EMPRESAS = []
if not DEMO_CONSULTAS:
    DEMO_CONSULTAS = []
if not DEMO_BOLETOS:
    DEMO_BOLETOS = []
if not DEMO_BILLING_PLANS:
    DEMO_BILLING_PLANS = []

def get_supabase() -> Client | None:
    """Get or create the Supabase client singleton."""
    global _client, DEMO_MODE
    if _client is None and not DEMO_MODE:
        try:
            _client = create_client(settings.supabase_url, settings.supabase_key)
            # Test the connection
            _client.table("empresas").select("id", count="exact").limit(1).execute()
        except Exception as e:
            logger.warning(f"⚠️  Supabase connection failed: {e}. Running in DEMO MODE with in-memory data.")
            DEMO_MODE = True
            _client = None
    
    if DEMO_MODE:
        return None
        
    return _client


# ─── Empresas ────────────────────────────────────────────────────────

def get_empresas(
    ativo: bool | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List empresas with optional filters."""
    if DEMO_MODE:
        empresas = DEMO_EMPRESAS
        if ativo is not None:
            empresas = [e for e in empresas if e.get("ativo") == ativo]
        if search:
            search_lower = search.lower()
            empresas = [e for e in empresas if search_lower in str(e.get("cnpj", "")).lower() or search_lower in str(e.get("razao_social", "")).lower()]
        return empresas[offset:offset+limit]
    
    sb = get_supabase()
    if sb is None: # Fallback if get_supabase switched to demo mode mid-execution
        return get_empresas(ativo, search, limit, offset)

    query = sb.table("empresas").select("*")
    if ativo is not None:
        query = query.eq("ativo", ativo)
    if search:
        query = query.or_(f"cnpj.ilike.%{search}%,razao_social.ilike.%{search}%")
    query = query.order("razao_social").range(offset, offset + limit - 1)
    return query.execute().data


def get_empresa_by_id(empresa_id: str) -> dict | None:
    """Get a single empresa by ID."""
    if DEMO_MODE:
        for e in DEMO_EMPRESAS:
            if e.get("id") == empresa_id:
                return e
        return None
        
    sb = get_supabase()
    if sb is None: return get_empresa_by_id(empresa_id)

    result = sb.table("empresas").select("*").eq("id", empresa_id).execute()
    return result.data[0] if result.data else None


def get_empresa_by_cnpj(cnpj: str) -> dict | None:
    """Get an empresa by CNPJ."""
    if DEMO_MODE:
        for emp in DEMO_EMPRESAS:
            if emp.get("cnpj") == cnpj:
                return emp
        return None

    sb = get_supabase()
    if sb is None: return get_empresa_by_cnpj(cnpj)

    result = sb.table("empresas").select("*").eq("cnpj", cnpj).execute()
    return result.data[0] if result.data else None


def create_empresa(data: dict) -> dict:
    """Insert a new empresa."""
    if DEMO_MODE:
        import uuid
        from datetime import datetime, timezone
        
        empresa_mock = {
            "id": str(uuid.uuid4()),
            "cnpj": data.get("cnpj", ""),
            "razao_social": data.get("razao_social", ""),
            "inscricao_estadual_pr": data.get("inscricao_estadual_pr"),
            "email_notificacao": data.get("email_notificacao"),
            "whatsapp": data.get("whatsapp"),
            "periodicidade": data.get("periodicidade", "mensal"),
            "dia_semana": data.get("dia_semana"),
            "dia_mes": data.get("dia_mes"),
            "horario": data.get("horario", "08:00:00"),
            "ativo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        DEMO_EMPRESAS.append(empresa_mock)
        save_db()
        return empresa_mock
    
    sb = get_supabase()
    if sb is None: return create_empresa(data)

    result = sb.table("empresas").insert(data).execute()
    return result.data[0]


def update_empresa(empresa_id: str, data: dict) -> dict:
    """Update an empresa."""
    if DEMO_MODE:
        for i, emp in enumerate(DEMO_EMPRESAS):
            if emp["id"] == empresa_id:
                updated_emp = {**emp, **data, "updated_at": datetime.now(timezone.utc).isoformat()}
                DEMO_EMPRESAS[i] = updated_emp
                save_db()
                return updated_emp
        raise Exception("Empresa not found in demo mode")
    
    sb = get_supabase()
    if sb is None: return update_empresa(empresa_id, data)

    result = sb.table("empresas").update(data).eq("id", empresa_id).execute()
    return result.data[0]


def delete_empresa(empresa_id: str) -> None:
    """Soft-delete (deactivate) an empresa."""
    if DEMO_MODE:
        for i, emp in enumerate(DEMO_EMPRESAS):
            if emp["id"] == empresa_id:
                emp["ativo"] = False
                emp["updated_at"] = datetime.now(timezone.utc).isoformat()
                save_db()
                return
        return
    
    sb = get_supabase()
    if sb is None: return delete_empresa(empresa_id)

    sb.table("empresas").update({"ativo": False}).eq("id", empresa_id).execute()


def clear_all_empresas() -> None:
    """Hard-delete ALL empresas and associated data."""
    if DEMO_MODE:
        global DEMO_EMPRESAS, DEMO_CONSULTAS, DEMO_BOLETOS
        DEMO_EMPRESAS = []
        DEMO_CONSULTAS = []
        DEMO_CONSULTAS = []
        DEMO_BOLETOS = []
        DEMO_BILLING_PLANS = []
        save_db()
        return

    sb = get_supabase()
    if sb is None:
        return clear_all_empresas()

    # Due to 'on delete cascade' in schema, deleting from 'empresas' 
    # will remove associated 'consultas' and 'logs_execucao'.
    sb.table("empresas").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()


def get_empresas_ativas() -> list[dict]:
    """Get all active empresas for scheduling."""
    if DEMO_MODE:
        return [e for e in DEMO_EMPRESAS if e.get("ativo") == True]
        
    sb = get_supabase()
    if sb is None: return get_empresas_ativas()

    return sb.table("empresas").select("*").eq("ativo", True).execute().data


def count_empresas(ativo: bool | None = None) -> int:
    """Count empresas."""
    if DEMO_MODE:
        empresas = DEMO_EMPRESAS
        if ativo is not None:
            empresas = [e for e in empresas if e.get("ativo") == ativo]
        return len(empresas)
        
    sb = get_supabase()
    if sb is None: return count_empresas(ativo)

    query = sb.table("empresas").select("id", count="exact")
    if ativo is not None:
        query = query.eq("ativo", ativo)
    result = query.execute()
    return result.count or 0


# ─── Consultas ───────────────────────────────────────────────────────

def get_consultas_pendentes() -> list[dict]:
    """Get scheduled consultas that are due for execution."""
    if DEMO_MODE:
        return [] # No auto-execution in demo mode yet
        
    sb = get_supabase()
    if sb is None: return []

    now = datetime.now(timezone.utc).isoformat()
    return (
        sb.table("consultas")
        .select("*, empresas(cnpj, razao_social, inscricao_estadual_pr, email_notificacao)")
        .eq("status", "agendada")
        .lte("data_agendada", now)
        .order("data_agendada")
        .execute()
        .data
    )


def get_consultas_retry() -> list[dict]:
    """Get failed consultas that can still be retried."""
    sb = get_supabase()
    if sb is None: return []

    return (
        sb.table("consultas")
        .select("*, empresas(cnpj, razao_social, inscricao_estadual_pr, email_notificacao)")
        .eq("status", "erro")
        .lt("tentativas", settings.max_retries)
        .order("data_agendada")
        .execute()
        .data
    )


def create_consulta(data: dict) -> dict:
    """Insert a new consulta."""
    if DEMO_MODE:
        import uuid
        mock_consulta = {
            "id": str(uuid.uuid4()),
            **data,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        DEMO_CONSULTAS.append(mock_consulta)
        save_db()
        return mock_consulta

    sb = get_supabase()
    if sb is None: return create_consulta(data)

    result = sb.table("consultas").insert(data).execute()
    return result.data[0]


def update_consulta(consulta_id: str, data: dict) -> dict:
    """Update a consulta record."""
    if DEMO_MODE:
        for i, c in enumerate(DEMO_CONSULTAS):
            if c["id"] == consulta_id:
                updated = {**c, **data}
                DEMO_CONSULTAS[i] = updated
                save_db()
                return updated
        return {} # Should raise but keeping simple
        
    sb = get_supabase()
    if sb is None: return update_consulta(consulta_id, data)

    result = sb.table("consultas").update(data).eq("id", consulta_id).execute()
    return result.data[0]


def get_consultas(
    empresa_id: str | None = None,
    tipo: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List consultas with filters."""
    if DEMO_MODE:
        consultas = DEMO_CONSULTAS
        if empresa_id:
            consultas = [c for c in consultas if c.get("empresa_id") == empresa_id]
        # Sort by date desc
        consultas.sort(key=lambda x: x.get("data_agendada", ""), reverse=True)
        return consultas[offset:offset+limit]

    sb = get_supabase()
    if sb is None: return get_consultas(empresa_id, tipo, status, limit, offset)

    query = sb.table("consultas").select("*, empresas(cnpj, razao_social)")
    if empresa_id:
        query = query.eq("empresa_id", empresa_id)
    if tipo:
        query = query.eq("tipo", tipo)
    if status:
        query = query.eq("status", status)
    query = query.order("data_agendada", desc=True).range(offset, offset + limit - 1)
    return query.execute().data


def get_consulta_by_id(consulta_id: str) -> dict | None:
    """Get a single consulta by ID."""
    if DEMO_MODE:
        for c in DEMO_CONSULTAS:
            if c["id"] == consulta_id:
                return c
        return None

    sb = get_supabase()
    if sb is None: return get_consulta_by_id(consulta_id)

    result = (
        sb.table("consultas")
        .select("*, empresas(cnpj, razao_social)")
        .eq("id", consulta_id)
        .execute()
    )
    return result.data[0] if result.data else None


def count_consultas_hoje() -> int:
    """Count consultas executed today."""
    if DEMO_MODE:
        return len([c for c in DEMO_CONSULTAS if c.get("data_execucao") and c["data_execucao"].startswith(datetime.now().strftime("%Y-%m-%d"))])
        
    sb = get_supabase()
    if sb is None: return count_consultas_hoje()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = (
        sb.table("consultas")
        .select("id", count="exact")
        .gte("data_execucao", f"{today}T00:00:00Z")
        .execute()
    )
    return result.count or 0


def count_alertas_ativos() -> int:
    """Count active alerts (negativa / irregular)."""
    if DEMO_MODE:
        return len([c for c in DEMO_CONSULTAS if c.get("status") == "concluida" and c.get("situacao") in ["negativa", "irregular"]])

    sb = get_supabase()
    if sb is None: return count_alertas_ativos()

    result = (
        sb.table("consultas")
        .select("id", count="exact")
        .eq("status", "concluida")
        .in_("situacao", ["negativa", "irregular"])
        .execute()
    )
    return result.count or 0


# ─── Logs ────────────────────────────────────────────────────────────

def create_log(consulta_id: str, nivel: str, mensagem: str, payload: Any = None):
    """Insert an execution log entry."""
    if DEMO_MODE:
        print(f"[DEMO LOG] {nivel}: {mensagem} (payload={payload})")
        return

    sb = get_supabase()
    if sb is None: return create_log(consulta_id, nivel, mensagem, payload)

    data = {
        "consulta_id": consulta_id,
        "nivel": nivel,
        "mensagem": mensagem,
    }
    if payload:
        data["payload"] = payload
    sb.table("logs_execucao").insert(data).execute()


# ─── RPC calls ───────────────────────────────────────────────────────

def rpc_consultas_por_dia(dias: int = 7) -> list[dict]:
    """Call the consultas_por_dia Supabase function."""
    if DEMO_MODE:
        from datetime import timedelta
        result = []
        for i in range(dias):
            dia = datetime.now() - timedelta(days=dias-i-1)
            result.append({
                "data": dia.strftime("%Y-%m-%d"),
                "total": 8 + (i % 5),
                "sucessos": 7 + (i % 4),
                "erros": 1 if i % 3 == 0 else 0
            })
        return result
        
    sb = get_supabase()
    if sb is None: return rpc_consultas_por_dia(dias)

    return sb.rpc("consultas_por_dia", {"dias": dias}).execute().data


def rpc_proximas_consultas(limite: int = 10) -> list[dict]:
    """Call the proximas_consultas Supabase function."""
    if DEMO_MODE:
        from datetime import timedelta
        empresas = DEMO_EMPRESAS
        result = []
        for i, emp in enumerate(empresas[:limite]):
            result.append({
                "consulta_id": f"future_{i}",
                "cnpj": emp["cnpj"],
                "razao_social": emp["razao_social"],
                "tipo": ["cnd_federal", "cnd_pr", "fgts_regularidade"][i % 3],
                "data_agendada": (datetime.now() + timedelta(days=i+1)).isoformat()
            })
        return result
        
    sb = get_supabase()
    if sb is None: return rpc_proximas_consultas(limite)

    return sb.rpc("proximas_consultas", {"limite": limite}).execute().data


def rpc_alertas_ativos(limite: int = 20) -> list[dict]:
    """Call the alertas_ativos Supabase function."""
    if DEMO_MODE:
        from datetime import timedelta
        demos = [
            {
                "consulta_id": "c1", "cnpj": "09.157.307/0001-75", 
                "razao_social": "Empresa Digital Ltda", 
                "tipo": "cnd_federal", "situacao": "negativa",
                "data_execucao": (datetime.now() - timedelta(days=1)).isoformat()
            },
        ]
        return demos[:limite]
        
    sb = get_supabase()
    if sb is None: return rpc_alertas_ativos(limite)

    return sb.rpc("alertas_ativos", {"limite": limite}).execute().data

# ─── Boletos ─────────────────────────────────────────────────────────

def get_boletos_ativos() -> list[dict]:
    """Get all active boletos (emitidos ou atrasados)."""
    if DEMO_MODE:
        return [b for b in DEMO_BOLETOS if b.get("status") in ("emitido", "atraso")]
    
    sb = get_supabase()
    if sb is None: return get_boletos_ativos()
    
    # We need to join with empresa to get email/whatsapp for notifications
    # This assumes a VIEW or foreign key relationship is set up correctly in Supabase
    # If not, we might need two queries or a robust join.
    # Assuming 'boletos' table exists and has 'empresa_id'
    
    return (
        sb.table("boletos")
        .select("*, empresas(razao_social, email_notificacao, whatsapp)")
        .in_("status", ["emitido", "atraso"])
        .execute()
        .data
    )

def update_boleto_status(boleto_id: str, status: str, extra_data: dict = None) -> dict:
    """Update boleto status."""
    update_payload = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if extra_data:
        # Merge extra data into a 'bradesco_metadata' column if it exists, or just specific fields
        # For simple storage, let's assume we update metadata if column exists
        pass 
    if DEMO_MODE:
        for i, b in enumerate(DEMO_BOLETOS):
            if b["id"] == boleto_id:
                updated = {**b, **update_payload}
                DEMO_BOLETOS[i] = updated
                save_db()
                return updated
        return {}

    sb = get_supabase()
    if sb is None: return update_boleto_status(boleto_id, status, extra_data)

    return sb.table("boletos").update(update_payload).eq("id", boleto_id).execute().data[0]


# ─── Billing Plans ───────────────────────────────────────────────────

def get_billing_plans(empresa_id: str = None) -> list[dict]:
    """Get billing plans, optionally filtered by empresa."""
    if DEMO_MODE:
        if empresa_id:
            return [p for p in DEMO_BILLING_PLANS if p["empresa_id"] == empresa_id and p.get("ativo", True)]
        return [p for p in DEMO_BILLING_PLANS if p.get("ativo", True)]
    
    sb = get_supabase()
    if sb is None: return get_billing_plans(empresa_id)

    query = sb.table("billing_plans").select("*").eq("ativo", True)
    if empresa_id:
        query = query.eq("empresa_id", empresa_id)
    return query.execute().data

def create_billing_plan(data: dict) -> dict:
    """Create a new billing plan."""
    if DEMO_MODE:
        import uuid
        plan = {
            "id": str(uuid.uuid4()),
            "ativo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **data
        }
        DEMO_BILLING_PLANS.append(plan)
        save_db()
        return plan
    
    sb = get_supabase()
    if sb is None: return create_billing_plan(data)
    
    return sb.table("billing_plans").insert(data).execute().data[0]

def delete_billing_plan(plan_id: str) -> None:
    """Soft delete a billing plan."""
    if DEMO_MODE:
        for i, p in enumerate(DEMO_BILLING_PLANS):
            if p["id"] == plan_id:
                p["ativo"] = False
                save_db()
                return
        return

    sb = get_supabase()
    if sb is None: return delete_billing_plan(plan_id)
    
    sb.table("billing_plans").update({"ativo": False}).eq("id", plan_id).execute()

def update_billing_plan(plan_id: str, data: dict) -> dict:
    """Update a billing plan."""
    if DEMO_MODE:
        for i, p in enumerate(DEMO_BILLING_PLANS):
            if p["id"] == plan_id:
                updated = {**p, **data}
                DEMO_BILLING_PLANS[i] = updated
                save_db()
                return updated
        return {}

    sb = get_supabase()
    if sb is None: return update_billing_plan(plan_id, data)
    
    return sb.table("billing_plans").update(data).eq("id", plan_id).execute().data[0]

