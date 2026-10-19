# Wedding Invitation Studio

A local FastAPI application for creating personalized PNG wedding cards and matching WhatsApp messages. Includes single/double invitation types, editable clarification numbers, and an RSVP dashboard.

## Windows localhost setup (PowerShell)

```powershell
cd path\to\wedding_card_project
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Use Python 3.11+ with compatible dependencies; 3.12 is a safe choice.

## Customize

Edit `.env` for `COUPLE_NAMES`, `WEDDING_DATE`, `WEDDING_VENUE`, `CONTACT_1`, `CONTACT_2` and `NAME_ANCHOR_Y` (relative position from 0 to 1). To use your own wedding design, place a PNG at `assets/templates/invitation.png`. If none is supplied, a simple ivory-colored card is generated. Restart the app after editing `.env`.

## Workflow

Enter guest name, select Single or Double, and optionally enter a WhatsApp phone number. Generate the PNG and message together. Download the PNG, open WhatsApp with the prefilled text, **attach the PNG**, review and send. Update Yes/No RSVP on the dashboard when the guest replies.

**Important:** WhatsApp is not automatically sent and guest replies are not automatically received. Sending a prefilled message is user-initiated. Automatic outbound messages and webhooks require a separately configured official WhatsApp Business integration and approved templates where required.

## Notes

- The application stores guest names and phone numbers locally in `data/invitations.db`. Protect this file.
- The localhost dashboard has no login; do not expose it directly to the public internet.
- For a Double invitation, RSVP Yes is counted as two *potential* attendees. For accurate headcount, ask the guest how many of the two will attend.
