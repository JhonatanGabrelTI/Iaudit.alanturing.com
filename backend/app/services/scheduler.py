"""IAudit - APScheduler jobs for automated query processing."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.database import (
    get_consultas_pendentes,
    get_consultas_retry,
    get_empresas_ativas,
    create_consulta,
    update_consulta,
    create_log,
)
from app.services.infosimples import infosimples_client
from app.services.drive import drive_service
from app.services.notifications import send_alert_email
from app.services.settings import dynamic_settings

logger = logging.getLogger(__name__)


async def process_single_consulta(consulta: dict) -> None:
    """
    Process a single consultation:
    1. Mark as 'processando'
    2. Call InfoSimples API
    3. Upload PDF to Drive
    4. Update result in Supabase
    5. Send alert if negative/irregular
    """
    consulta_id = consulta["id"]
    tipo = consulta["tipo"]
    empresa = consulta.get("empresas", {})
    cnpj = empresa.get("cnpj", "")
    tentativas = consulta.get("tentativas", 0) + 1

    logger.info(f"Processing consulta {consulta_id}: {tipo} for CNPJ {cnpj}")

    # Mark as processing
    update_consulta(consulta_id, {
        "status": "processando",
        "tentativas": tentativas,
    })
    create_log(consulta_id, "info", f"Iniciando consulta {tipo} (tentativa {tentativas})")

    try:
        # Call InfoSimples API based on type
        if tipo == "cnd_federal":
            result = await infosimples_client.consultar_cnd_federal(cnpj)
        elif tipo == "cnd_pr":
            ie = empresa.get("inscricao_estadual_pr")
            result = await infosimples_client.consultar_cnd_pr(cnpj, ie)
        elif tipo == "fgts_regularidade":
            result = await infosimples_client.consultar_fgts(cnpj)
        else:
            raise ValueError(f"Unknown consultation type: {tipo}")

        situacao = result.get("situacao", "erro")
        pdf_url = result.get("pdf_url")
        drive_link = None

        # Upload PDF to Google Drive if available
        if pdf_url:
            try:
                drive_link = await drive_service.upload_pdf(
                    pdf_url=pdf_url,
                    tipo=tipo,
                    cnpj=cnpj,
                    data=datetime.now(timezone.utc),
                )
            except Exception as e:
                logger.error(f"Drive upload failed for {consulta_id}: {e}")
                create_log(consulta_id, "aviso", f"Upload Google Drive falhou: {e}")

        # Update consulta as completed
        update_data = {
            "status": "concluida",
            "situacao": situacao,
            "resultado_json": result.get("resultado_json", {}),
            "pdf_url": drive_link or pdf_url,
            "data_execucao": datetime.now(timezone.utc).isoformat(),
            "mensagem_erro": None,
        }
        if result.get("data_validade"):
            update_data["data_validade"] = result["data_validade"]

        update_consulta(consulta_id, update_data)
        create_log(consulta_id, "info", f"Consulta concluída: {situacao}")

        # Send alert if negative / irregular
        if situacao in ("negativa", "irregular"):
            create_log(consulta_id, "aviso", f"ALERTA: situação {situacao}")
            try:
                await send_alert_email(empresa, {**consulta, **update_data})
            except Exception as e:
                logger.error(f"Alert email failed: {e}")
                create_log(consulta_id, "erro", f"Envio de email de alerta falhou: {e}")

    except Exception as e:
        logger.error(f"Consulta {consulta_id} failed: {e}")
        error_msg = str(e)

        if tentativas >= settings.max_retries:
            # Max retries exhausted
            update_consulta(consulta_id, {
                "status": "erro",
                "situacao": "erro",
                "mensagem_erro": f"Falha após {tentativas} tentativas: {error_msg}",
                "data_execucao": datetime.now(timezone.utc).isoformat(),
            })
            create_log(consulta_id, "erro", f"Erro final após {tentativas} tentativas: {error_msg}")

            # Send alert for persistent errors
            try:
                await send_alert_email(empresa, {
                    **consulta,
                    "situacao": "erro",
                    "tipo": tipo,
                })
            except Exception:
                pass
        else:
            # Mark as error but eligible for retry
            update_consulta(consulta_id, {
                "status": "erro",
                "mensagem_erro": f"Tentativa {tentativas}: {error_msg}",
            })
            create_log(consulta_id, "aviso", f"Erro na tentativa {tentativas}: {error_msg}. Retry pendente.")


async def process_pending_queries():
    """
    Job 1: Process all pending scheduled queries.
    Runs every 5 minutes via APScheduler.
    """
    logger.info("=== Job: Process Pending Queries ===")
    
    if not dynamic_settings.is_robo_ativo():
        logger.info("Robot is INACTIVE. Skipping process_pending_queries.")
        return

    try:
        # Get pending consultas (agendada + due)
        pending = get_consultas_pendentes()
        logger.info(f"Found {len(pending)} pending consultas")

        # Also get retryable failed consultas
        retryable = get_consultas_retry()
        logger.info(f"Found {len(retryable)} retryable consultas")

        all_queries = pending + retryable

        for consulta in all_queries:
            await process_single_consulta(consulta)

    except Exception as e:
        logger.error(f"process_pending_queries failed: {e}")


def create_daily_schedules():
    """
    Job 2: Create new scheduled consultas for all active empresas.
    Runs daily at 00:05 via APScheduler.

    Creates consultas based on each empresa's periodicidade settings.
    """
    logger.info("=== Job: Create Daily Schedules ===")

    if not dynamic_settings.is_robo_ativo():
        logger.info("Robot is INACTIVE. Skipping create_daily_schedules.")
        return

    try:
        empresas = get_empresas_ativas()
        today = datetime.now(timezone.utc).date()
        weekday = today.weekday()  # 0=Monday ... 6=Sunday
        day_of_month = today.day
        count = 0

        for empresa in empresas:
            periodicidade = empresa.get("periodicidade", "mensal")
            dia_semana = empresa.get("dia_semana")
            dia_mes = empresa.get("dia_mes")
            horario_str = empresa.get("horario", "08:00:00")

            should_schedule = False

            if periodicidade == "diario":
                should_schedule = True
            elif periodicidade == "semanal":
                if dia_semana is not None and weekday == dia_semana:
                    should_schedule = True
            elif periodicidade == "quinzenal":
                if dia_mes is not None and day_of_month in (dia_mes, min(dia_mes + 15, 28)):
                    should_schedule = True
            elif periodicidade == "mensal":
                if dia_mes is not None and day_of_month == dia_mes:
                    should_schedule = True

            if not should_schedule:
                continue

            # Parse horario
            try:
                parts = horario_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                hour, minute = 8, 0

            scheduled_time = datetime(
                today.year, today.month, today.day,
                hour, minute, 0,
                tzinfo=timezone.utc,
            )

            # Create consultas for CND Federal and CND PR (Phase 1 MVP)
            for tipo in ["cnd_federal", "cnd_pr"]:
                try:
                    create_consulta({
                        "empresa_id": empresa["id"],
                        "tipo": tipo,
                        "status": "agendada",
                        "data_agendada": scheduled_time.isoformat(),
                        "tentativas": 0,
                    })
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to schedule {tipo} for {empresa.get('cnpj')}: {e}"
                    )

        logger.info(f"Created {count} scheduled consultas for today")

    except Exception as e:
        logger.error(f"create_daily_schedules failed: {e}")
