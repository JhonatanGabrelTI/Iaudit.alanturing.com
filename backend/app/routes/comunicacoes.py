from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.services.comunicacao import comm_service
from app.services.settings import dynamic_settings

router = APIRouter(prefix="/api/comunicacao", tags=["Comunicação"])

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_comm_logs(
    channel: str = Query(None, description="Filtrar por canal (email, whatsapp)"),
    status: str = Query(None, description="Filtrar por status (sent, failed, pending)")
):
    """
    Returns the list of communication logs.
    """
    try:
        return await comm_service.get_logs(channel=channel, status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_comm_stats():
    """
    Returns communication success/failure metrics.
    """
    try:
        return await comm_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", response_model=Dict[str, Any])
async def get_system_settings():
    """
    Returns current dynamic system settings.
    """
    return dynamic_settings.get_settings()

@router.post("/settings", response_model=Dict[str, Any])
async def update_system_settings(new_settings: Dict[str, Any]):
    """
    Updates dynamic system settings.
    """
    try:
        return dynamic_settings.update_settings(new_settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/logs")
async def clear_comm_logs():
    """
    Clears all communication logs.
    """
    try:
        await comm_service.clear_logs()
        return {"status": "success", "message": "Logs cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
