import asyncio
import logging
import os

# Mock environment variables for testing purposes to satisfy Settings validation
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy_key")
os.environ.setdefault("INFOSIMPLES_TOKEN", "dummy_token")

from app.services.notifications import send_boleto_notification
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_notification_flow():
    print("=== Testing Notification Flow ===")
    
    # Test Data
    recipient_email = "test@example.com" # Replace with real email if needed or mock
    recipient_phone = settings.twilio_from_number # Use sender as recipient for loopback test if allowed, or mock
    
    # Mock Boleto Data
    boleto_data = {
        "nomeSacado": "João da Silva",
        "valorNominal": "150.00",
        "dataVencimento": "2023-12-31",
        "linhaDigitavel": "12345.67890 12345.67890 12345.67890 1 1234567890",
        "linkBoleto": "https://example.com/boleto.pdf"
    }
    
    # 1. Test "Emitido" (Issued)
    print("\n[1] Testing 'Emitido' Notification...")
    try:
        await send_boleto_notification(
            "emitido", 
            boleto_data, 
            recipient_email, 
            recipient_phone
        )
        print("[OK] 'Emitido' notification sent successfully.")
    except Exception as e:
        print(f"[FAIL] 'Emitido' notification failed: {e}")

    # 2. Test "Pago" (Paid)
    print("\n[2] Testing 'Pago' Notification...")
    try:
        await send_boleto_notification(
            "pago", 
            boleto_data, 
            recipient_email, 
            recipient_phone
        )
        print("[OK] 'Pago' notification sent successfully.")
    except Exception as e:
        print(f"[FAIL] 'Pago' notification failed: {e}")

    # 3. Test "Atraso" (Overdue)
    print("\n[3] Testing 'Atraso' Notification...")
    try:
        await send_boleto_notification(
            "atraso", 
            boleto_data, 
            recipient_email, 
            recipient_phone
        )
        print("[OK] 'Atraso' notification sent successfully.")
    except Exception as e:
        print(f"[FAIL] 'Atraso' notification failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_notification_flow())
