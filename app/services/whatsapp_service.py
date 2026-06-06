"""
WhatsApp Service using Twilio.
Sends messages to team members via WhatsApp.
"""

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


def _get_twilio_client() -> Client:
    """Create and return Twilio client."""
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


async def send_whatsapp_message(phone: str, message: str) -> dict:
  

    # ── Mock mode if credentials not set ──────────────────────────────────────
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("PHONE:", phone)
        print("TO:", to_number)
        print("FROM:", from_number)
        print(f"[WhatsApp MOCK] To: {phone}\n{message}\n")
        return {"status": "mock_sent"}

    to_number = f"whatsapp:{phone}"
    from_number = settings.TWILIO_WHATSAPP_FROM

    # ── Run Twilio (sync) in thread so it doesn't block FastAPI (async) ───────
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            _send_sync,
            to_number,
            from_number,
            message
        )
        return result
    except Exception as e:
        logger.error(f"[Twilio ERROR] {e}")
        return {"status": "error", "detail": str(e)}


def _send_sync(to: str, from_: str, body: str) -> dict:
    """
    Actual Twilio API call — runs in thread executor.
    Separated so async code stays clean.
    """
    try:
        client = _get_twilio_client()
        msg = client.messages.create(
            body=body,
            from_=from_,
            to=to
        )
        logger.info(f"[Twilio] Message sent: SID={msg.sid} | To={to} | Status={msg.status}")
        return {
            "status": "sent",
            "sid": msg.sid,
            "to": to,
            "twilio_status": msg.status
        }
    except TwilioRestException as e:
        logger.error(f"[Twilio REST ERROR] Code={e.code} | {e.msg}")
        return {
            "status": "error",
            "code": e.code,
            "detail": e.msg
        }
    except Exception as e:
        logger.error(f"[Twilio UNKNOWN ERROR] {e}")
        return {"status": "error", "detail": str(e)}


# ─── Message Templates (Same as before — no changes needed) ──────────────────

def task_assigned_message(
    name: str, project: str, task: str, deadline: str, priority: str
) -> str:
    return f"""Hello {name},

Aapko ek naya task assign kiya gaya hai Prakhar Bagora ki taraf se.

📋 Project: {project}
✅ Task: {task}
📅 Deadline: {deadline}
🔴 Priority: {priority}

Kripya deadline se pehle apna progress update karein.

– AI-PS | Prakhar Bagora"""


def task_reminder_message(name: str, task: str, project: str, deadline: str) -> str:
    return f"""Hello {name},

⏰ Reminder: Aapka task jaldi due hone wala hai.

Task: {task}
Project: {project}
Deadline: {deadline}

Kripya complete karein ya current status update karein.

– AI-PS | Prakhar Bagora"""


def task_delay_alert_message(
    name: str, task: str, project: str, original_deadline: str
) -> str:
    return f"""Hello {name},

🚨 Alert: Aapka assigned task ab delay ho gaya hai.

Task: {task}
Project: {project}
Original Deadline: {original_deadline}

Kripya delay ka reason turant update karein.

– AI-PS | Prakhar Bagora"""


def escalation_to_admin_message(
    task: str, project: str, assigned_to: str, deadline: str,
    delay_reason: str = "Not provided"
) -> str:
    return f"""Prakhar Sir,

🔴 Yeh task delay ho gaya hai:

Project: {project}
Task: {task}
Assigned To: {assigned_to}
Deadline: {deadline}
Current Status: Delayed
Delay Reason: {delay_reason}

Aapki taraf se action required hai.

– AI-PS System"""


def eod_reminder_message(name: str, deadline: str) -> str:
    return f"""Hello {name},

📝 Aaj ka EOD report submit karna baaki hai.

Format:
1. Aaj ka completed work
2. Pending work
3. Delay reason (agar ho)
4. Kal ka plan
5. Support required

Deadline: {deadline}

– AI-PS | Prakhar Bagora"""


def new_account_message(name: str, phone: str, password: str, platform_url: str) -> str:
    return f"""Hello {name},

🎉 Aapka AI-PS account create ho gaya hai!

Login Details:
🌐 Platform: {platform_url}
📱 Mobile: {phone}
🔑 Password: {password}

Pehli baar login karke password zaroor change karein.

– AI-PS | Prakhar Bagora"""


def daily_summary_message(
    total: int, submitted: int, not_submitted: int,
    completed_tasks: int, pending_tasks: int, delayed_tasks: int,
    not_submitted_names: str
) -> str:
    return f"""Prakhar Sir,

📊 Aaj ka EOD Summary:

👥 Total Team Members: {total}
✅ EOD Submitted: {submitted}
❌ EOD Not Submitted: {not_submitted}
✔️ Completed Tasks: {completed_tasks}
⏳ Pending Tasks: {pending_tasks}
🔴 Delayed Tasks: {delayed_tasks}

Non-Submitted Members:
{not_submitted_names}

– AI-PS System"""


def meeting_invite_message(
    name:          str,
    meeting_title: str,
    project:       str,
    meeting_date:  str,
    meeting_time:  str,
    organized_by:  str,
    meeting_link:  str = "Link not provided"   # ← Yeh add karo
) -> str:
    return f"""Hello {name},

📅 Aapko ek meeting mein invite kiya gaya hai.

🏷️ Meeting: {meeting_title}
📋 Project: {project}
📆 Date: {meeting_date}
⏰ Time: {meeting_time}
👤 Organized By: {organized_by}
🔗 Meeting Link: {meeting_link}

Kripya samay par available rahein.

– AI-PS | Prakhar Bagora"""