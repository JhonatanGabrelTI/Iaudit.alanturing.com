"""IAudit - CNPJ Query routes (BrasilAPI + InfoSimples)."""

import logging
import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

BRASIL_API_URL = "https://brasilapi.com.br/api/cnpj/v1"
INFOSIMPLES_BASE = "https://api.infosimples.com/api/v2/consultas"


async def _fetch_brasil_api(cnpj: str) -> dict:
    """Fetch company data from BrasilAPI."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BRASIL_API_URL}/{cnpj}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="CNPJ não encontrado na Receita Federal")
        resp.raise_for_status()
        return resp.json()


async def _fetch_infosimples(endpoint: str, params: dict) -> dict:
    """Generic InfoSimples API call."""
    params["token"] = settings.infosimples_token
    params["timeout"] = 600

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{INFOSIMPLES_BASE}/{endpoint}", data=params)
        resp.raise_for_status()
        data = resp.json()
        return data


def _extract_cert_url(data: dict, item: dict = None) -> str:
    """Extract certificate URL from InfoSimples API response."""
    # Try multiple fields where InfoSimples might return the URL
    url = data.get("site_receipt") or ""
    if not url:
        site_receipts = data.get("site_receipts", [])
        if site_receipts and isinstance(site_receipts[0], str):
            url = site_receipts[0]
    if not url and item:
        url = (
            item.get("site_receipt", "") or
            item.get("certificado_url", "") or
            item.get("url", "") or
            item.get("link", "") or
            ""
        )
    return url


async def _get_cnd_federal(cnpj: str) -> dict:
    """Get CND Federal status from InfoSimples."""
    try:
        data = await _fetch_infosimples("receita-federal/pgfn/nova", {
            "cnpj": cnpj,
        })
        code = data.get("code")

        if code == 200:
            result_data = data.get("data", [{}])
            if result_data and len(result_data) > 0:
                item = result_data[0]
                cert_url = _extract_cert_url(data, item)
                situacao = (item.get("situacao", "") or item.get("certidao_tipo", "") or "").lower()
                result = {"status": "regular", "detalhes": item, "certificado_url": cert_url}
                if "negativa" in situacao and "positiva" not in situacao:
                    result["status"] = "regular"
                elif "positiva" in situacao:
                    result["status"] = "irregular"
                return result
        
        # Detect block/insufficient info even on non-200 or 200 with error messages
        full_content = str(data).lower()
        if any(kw in full_content for kw in ["insuficiente", "incompleto", "intervenção", "internet"]):
            return {"status": "pendente", "detalhes": data, "certificado_url": ""}
            
        return {"status": "indisponivel", "detalhes": data, "certificado_url": _extract_cert_url(data)}
    except Exception as e:
        logger.warning(f"CND Federal lookup failed for {cnpj}: {e}")
        return {"status": "indisponivel", "erro": str(e), "certificado_url": ""}


async def _get_cnd_estadual_pr(cnpj: str) -> dict:
    """Get CND Estadual PR status from InfoSimples."""
    try:
        data = await _fetch_infosimples("sefaz/pr/certidao-debitos", {
            "cnpj_base": cnpj,
        })
        code = data.get("code")

        if code == 200:
            result_data = data.get("data", [{}])
            if result_data and len(result_data) > 0:
                item = result_data[0]
                cert_url = _extract_cert_url(data, item)
                situacao = item.get("situacao", "").lower()
                result = {"status": "regular", "detalhes": item, "certificado_url": cert_url}
                if "irregular" in situacao or "positiva" in situacao:
                    result["status"] = "irregular"
                return result
        return {"status": "indisponivel", "detalhes": data, "certificado_url": _extract_cert_url(data)}
    except Exception as e:
        logger.warning(f"CND Estadual PR lookup failed for {cnpj}: {e}")
        return {"status": "indisponivel", "erro": str(e), "certificado_url": ""}


async def _get_fgts(cnpj: str) -> dict:
    """Get FGTS regularity status from InfoSimples."""
    try:
        data = await _fetch_infosimples("caixa/regularidade", {
            "cnpj": cnpj,
        })
        code = data.get("code")

        if code == 200:
            result_data = data.get("data", [{}])
            if result_data and len(result_data) > 0:
                item = result_data[0]
                cert_url = _extract_cert_url(data, item)
                situacao = item.get("situacao", "").lower()
                result = {"status": "regular", "detalhes": item, "certificado_url": cert_url}
                if "irregular" in situacao:
                    result["status"] = "irregular"
                return result
        return {"status": "indisponivel", "detalhes": data, "certificado_url": _extract_cert_url(data)}
    except Exception as e:
        logger.warning(f"FGTS lookup failed for {cnpj}: {e}")
        return {"status": "indisponivel", "erro": str(e), "certificado_url": ""}


async def query_cnpj(cnpj: str) -> dict:
    """
    Full CNPJ query: fetches company data from BrasilAPI 
    and certification statuses from InfoSimples.
    
    Returns a combined dict with company details + certidoes.
    """
    # 1. Fetch basic company data from BrasilAPI
    brasil_data = await _fetch_brasil_api(cnpj)

    # 2. Fetch certifications in parallel
    import asyncio
    cnd_federal, cnd_estadual, fgts = await asyncio.gather(
        _get_cnd_federal(cnpj),
        _get_cnd_estadual_pr(cnpj),
        _get_fgts(cnpj),
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(cnd_federal, Exception):
        cnd_federal = {"status": "indisponivel", "erro": str(cnd_federal)}
    if isinstance(cnd_estadual, Exception):
        cnd_estadual = {"status": "indisponivel", "erro": str(cnd_estadual)}
    if isinstance(fgts, Exception):
        fgts = {"status": "indisponivel", "erro": str(fgts)}

    # 3. Build response
    return {
        "cnpj": brasil_data.get("cnpj", cnpj),
        "razao_social": brasil_data.get("razao_social", ""),
        "nome_fantasia": brasil_data.get("nome_fantasia", ""),
        "situacao_cadastral": brasil_data.get("descricao_situacao_cadastral", ""),
        "data_situacao_cadastral": brasil_data.get("data_situacao_cadastral", ""),
        "porte": brasil_data.get("porte", ""),
        "natureza_juridica": brasil_data.get("natureza_juridica", ""),
        "capital_social": brasil_data.get("capital_social", 0),
        "municipio": brasil_data.get("municipio", ""),
        "uf": brasil_data.get("uf", ""),
        "cep": brasil_data.get("cep", ""),
        "descricao_tipo_de_logradouro": brasil_data.get("descricao_tipo_de_logradouro", ""),
        "logradouro": brasil_data.get("logradouro", ""),
        "numero": brasil_data.get("numero", ""),
        "complemento": brasil_data.get("complemento", ""),
        "bairro": brasil_data.get("bairro", ""),
        "telefone": brasil_data.get("ddd_telefone_1", ""),
        "email": brasil_data.get("email", ""),
        "data_inicio_atividade": brasil_data.get("data_inicio_atividade", ""),
        "cnae_fiscal": brasil_data.get("cnae_fiscal", ""),
        "cnae_fiscal_descricao": brasil_data.get("cnae_fiscal_descricao", ""),
        "cnaes_secundarios": brasil_data.get("cnaes_secundarios", []),
        "qsa": brasil_data.get("qsa", []),
        "opcao_pelo_simples": brasil_data.get("opcao_pelo_simples", None),
        "opcao_pelo_mei": brasil_data.get("opcao_pelo_mei", None),
        "regime_tributario": brasil_data.get("regime_tributario", ""),
        "identificador_matriz_filial": brasil_data.get("descricao_identificador_matriz_filial", ""),
        "certidoes": {
            "cnd_federal": cnd_federal,
            "cnd_estadual": cnd_estadual,
            "fgts": fgts,
        },
        "message": "Dados obtidos com sucesso via BrasilAPI e InfoSimples",
    }


from app.services.history import load_history, save_to_history

@router.get("/history")
async def get_history():
    """Retrieve search history."""
    return load_history()

@router.post("/history")
async def add_history(data: dict):
    """Manually add to history."""
    save_to_history(data)
    return {"status": "ok"}

@router.get("/cnpj/{cnpj}")
async def get_cnpj(cnpj: str):
    """Query CNPJ endpoint - returns company data + certification statuses."""
    # Clean CNPJ
    cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()

    if len(cnpj_clean) != 14 or not cnpj_clean.isdigit():
        raise HTTPException(status_code=400, detail="CNPJ inválido. Insira 14 dígitos.")

    try:
        result = await query_cnpj(cnpj_clean)
        # Save to history automatically
        save_to_history(result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CNPJ query failed for {cnpj_clean}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar CNPJ: {str(e)}")
