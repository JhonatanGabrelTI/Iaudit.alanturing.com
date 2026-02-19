"""IAudit - Notification service (Twilio WhatsApp + SMTP/Resend Email)."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import settings
from app.models import CommunicationChannel, CommunicationStatus
from app.services.comunicacao import comm_service
from app.services.settings import dynamic_settings

logger = logging.getLogger(__name__)

# ─── Templates ───────────────────────────────────────────────────────

def _format_currency(value: int | float) -> str:
    """Format cents or float to BRL currency string."""
    try:
        val_float = float(value) / 100 if isinstance(value, int) else float(value)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def _build_boleto_email_html(event: str, data: dict[str, Any]) -> str:
    """
    Build HTML email for boleto events.
    Events: 'emitido', 'pago', 'atraso', 'reativado'
    """
    nome = data.get("nomeSacado", "Cliente")
    valor = _format_currency(data.get("valorNominal", 0))
    vencimento = data.get("dataVencimento", "")
    linha = data.get("linhaDigitavel", "")
    link_pdf = data.get("linkBoleto", "#")
    
    colors = {
        "emitido": "#3b82f6", # Blue
        "pago": "#22c55e",    # Green
        "atraso": "#ef4444",  # Red
        "reativado": "#f59e0b" # Amber
    }
    
    titles = {
        "emitido": "Novo Boleto Disponível",
        "pago": "Pagamento Confirmado",
        "atraso": "Aviso de Vencimento",
        "reativado": "Boleto Reativado"
    }
    
    color = colors.get(event, "#3b82f6")
    title = titles.get(event, "Notificação iAudit")
    
    # Template body
    body_content = ""
    if event == "emitido":
        body_content = f"""
            <p>Olá <b>{nome}</b>,</p>
            <p>Seu boleto iAudit referente aos serviços de monitoramento fiscal já está disponível.</p>
            <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><b>Valor:</b> {valor}</p>
                <p style="margin: 5px 0;"><b>Vencimento:</b> {vencimento}</p>
            </div>
            <p>Para facilitar, aqui está a linha digitável:</p>
            <div style="background: #e2e8f0; padding: 10px; font-family: monospace; text-align: center; border-radius: 4px;">
                {linha}
            </div>
            <p style="text-align: center; margin-top: 25px;">
                <a href="{link_pdf}" style="background-color: {color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Baixar Boleto PDF
                </a>
            </p>
        """
    elif event == "pago":
        body_content = f"""
            <p>Olá <b>{nome}</b>,</p>
            <p>Confirmamos o recebimento do pagamento do seu boleto.</p>
            <div style="background: #dcfce7; padding: 15px; border-radius: 8px; margin: 20px 0; color: #166534;">
                <p style="margin: 5px 0;"><b>Valor Pago:</b> {valor}</p>
                <p style="margin: 5px 0;"><b>Obrigado por manter sua conta em dia!</b></p>
            </div>
        """
    elif event == "atraso":
        body_content = f"""
            <p>Olá <b>{nome}</b>,</p>
            <p>Não identificamos o pagamento do boleto com vencimento em <b>{vencimento}</b>.</p>
            <div style="background: #fee2e2; padding: 15px; border-radius: 8px; margin: 20px 0; color: #991b1b;">
                <p style="margin: 5px 0;"><b>Valor Atualizado:</b> {valor}</p>
                <p style="margin: 5px 0;">Evite suspensão dos serviços regularizando sua pendência.</p>
            </div>
            <p style="text-align: center; margin-top: 25px;">
                <a href="{link_pdf}" style="background-color: {color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Visualizar Boleto
                </a>
            </p>
        """
    else:
        body_content = f"<p>Notificação sobre seu boleto: {title}</p>"

    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 40px 0;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
            <div style="background-color: {color}; padding: 20px; text-align: center;">
                <h2 style="color: white; margin: 0; font-size: 24px;">{title}</h2>
            </div>
            <div style="padding: 30px; color: #334155; line-height: 1.6;">
                {body_content}
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">
                    IAudit - Automação Fiscal Inteligente<br>
                    Este é um email automático, por favor não responda.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

def _build_whatsapp_message(event: str, data: dict[str, Any]) -> str:
    """Build WhatsApp text message."""
    nome = data.get("nomeSacado", "Cliente")
    valor = _format_currency(data.get("valorNominal", 0))
    vencimento = data.get("dataVencimento", "")
    linha = data.get("linhaDigitavel", "")
    link_pdf = data.get("linkBoleto", "")

    if event == "emitido":
        return (
            f"📄 *Boleto Disponível - iAudit*\n\n"
            f"Olá {nome}, seu boleto de *{valor}* com vencimento em *{vencimento}* foi gerado.\n\n"
            f"📎 *Baixar PDF:* {link_pdf}\n\n"
            f"👇 *Linha Digitável:*\n{linha}"
        )
    elif event == "pago":
        return (
            f"✅ *Pagamento Confirmado - iAudit*\n\n"
            f"Olá {nome}, confirmamos o pagamento de *{valor}*.\n"
            f"Obrigado!"
        )
    elif event == "atraso":
        return (
            f"⚠️ *Aviso de Pendência - iAudit*\n\n"
            f"Olá {nome}, o boleto de *{valor}* venceu em *{vencimento}*.\n"
            f"Por favor, regularize para manter os serviços ativos.\n\n"
            f"📎 *2ª Via:* {link_pdf}"
        )
    return f"iAudit: Notificação sobre boleto {valor}."


# ─── Sending Logic ───────────────────────────────────────────────────

async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send email via Resend or SMTP."""
    
    # 1. Try Resend
    if settings.resend_api_key:
        try:
            import resend
            resend.api_key = settings.resend_api_key
            resend.Emails.send({
                "from": settings.email_from,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            })
            logger.info(f"Email sent via Resend to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Resend failed: {e}. Trying SMTP.")

    # 2. Try SMTP
    if settings.smtp_user and settings.smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = settings.email_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            # Gmail requires TLS 1.2+ usually handled by starttls
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent via SMTP to {to_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP failed: {e}")
            return False
            
    logger.warning("No email provider configured.")
    return False


async def send_whatsapp_twilio(to_number: str, message: str) -> bool:
    """Send WhatsApp message via Twilio."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials missing.")
        return False
        
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # Ensure number format (Twilio requires 'whatsapp:+55...')
        if not to_number.startswith("whatsapp:"):
            # Clean number first
            clean_num = "".join(filter(str.isdigit, to_number))
            if not clean_num.startswith("55"): # Add Brazil code if missing
                 clean_num = "55" + clean_num
            to_number = f"whatsapp:+{clean_num}"

        msg = client.messages.create(
            from_=settings.twilio_from_number,
            body=message,
            to=to_number
        )
        logger.info(f"WhatsApp sent via Twilio to {to_number}. SID: {msg.sid}")
        return True
    
    except TwilioRestException as e:
        logger.error(f"Twilio API Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Twilio General Error: {e}")
        return False


# ─── Public Notification Functions ───────────────────────────────────

async def send_boleto_notification(event: str, data: dict[str, Any], recipient_email: str, recipient_phone: str = None):
    """
    Main entry point for billing notifications.
    events: 'emitido', 'pago', 'atraso', 'reativado'
    """
    settings_dict = dynamic_settings.get_settings()
    if not settings_dict.get("mensagens_ativas", True):
        logger.info("Global messaging disabled via dynamic settings.")
        return

    # 1. Email
    if recipient_email:
        subject_map = {
            "emitido": "Fatura Disponível - iAudit",
            "pago": "Confirmação de Pagamento - iAudit",
            "atraso": "ALERTA: Fatura em Atraso - iAudit",
            "reativado": "Fatura Reativada - iAudit"
        }
        subject = subject_map.get(event, "Notificação iAudit")
        html = _build_boleto_email_html(event, data)
        
        success = await send_email(recipient_email, subject, html)
        
        await comm_service.log_message(
            channel=CommunicationChannel.email,
            recipient=recipient_email,
            subject=subject,
            content=f"Template: {event}",
            status=CommunicationStatus.sent if success else CommunicationStatus.failed
        )

    # 2. WhatsApp
    if recipient_phone and settings.twilio_account_sid:
        text_msg = _build_whatsapp_message(event, data)
        success = await send_whatsapp_twilio(recipient_phone, text_msg)
        
        await comm_service.log_message(
            channel=CommunicationChannel.whatsapp,
            recipient=recipient_phone,
            content=text_msg,
            status=CommunicationStatus.sent if success else CommunicationStatus.failed
        )


async def send_alert_email(empresa: dict, consulta: dict) -> bool:
    """Legacy alert implementation using new email logic."""
    return await send_alert_email_legacy(empresa, consulta)

def _build_alert_html_legacy(empresa: dict, consulta: dict) -> str:
    """Build HTML email body for an alert (Legacy)."""
    tipo_labels = {
        "cnd_federal": "CND Federal (Receita Federal / PGFN)",
        "cnd_pr": "CND Paraná (SEFAZ PR)",
        "fgts_regularidade": "FGTS Regularidade (CAIXA)",
    }

    situacao_labels = {
        "negativa": "⚠️ NEGATIVA",
        "irregular": "⚠️ IRREGULAR",
        "erro": "❌ ERRO na Consulta",
    }

    tipo = consulta.get("tipo", "")
    situacao = consulta.get("situacao", "").upper()
    
    # Simple alert html
    return f"""
    <h2>🚨 Alerta Fiscal: {tipo}</h2>
    <p>Empresa: {empresa.get('razao_social')}</p>
    <p>CNPJ: {empresa.get('cnpj')}</p>
    <p>Situação: <b style="color:red">{situacao}</b></p>
    """

async def send_alert_email_legacy(empresa: dict, consulta: dict) -> bool:
    """
    Send an alert email when CND is negative or FGTS is irregular.
    """
    to_email = empresa.get("email_notificacao")
    if not to_email:
        return False

    subject = f"🚨 Alerta: {consulta.get('tipo', '').upper()} - {empresa.get('razao_social')}"
    html = _build_alert_html_legacy(empresa, consulta)
    
    success = await send_email(to_email, subject, html)
    
    await comm_service.log_message(
        channel=CommunicationChannel.email,
        recipient=to_email,
        subject=subject,
        content="Alert Email",
        status=CommunicationStatus.sent if success else CommunicationStatus.failed
    )
    return success

