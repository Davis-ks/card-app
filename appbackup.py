import json
import mimetypes
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
OUT = ROOT / "assets" / "generated"
OUT.mkdir(parents=True, exist_ok=True)
DB = ROOT / "data" / "invitations.db"
DB.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Wedding Invitation Studio")

CSS = '''
:root{--wine:#713747;--wine-dark:#492532;--gold:#c8a56a;--cream:#f7f1e8;--ink:#30272a;--muted:#796d70;--line:#eadfe0;--white:#fff;--green:#236b4a;--red:#a23a43}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:15px/1.5 Inter,Segoe UI,Arial,sans-serif}
a{color:var(--wine);text-decoration:none}a:hover{text-decoration:underline}.shell{max-width:1200px;margin:auto;padding:28px 22px 50px}
.hero{background:linear-gradient(120deg,var(--wine-dark),var(--wine));color:white;border-radius:22px;padding:28px 30px;display:flex;justify-content:space-between;align-items:center;gap:20px;box-shadow:0 12px 35px #49253220}
.brand{display:flex;align-items:center;gap:15px}.brandmark{width:52px;height:52px;border:1px solid #d8bd8c;border-radius:16px;display:grid;place-items:center;color:#f0d8a9;font-size:26px}.eyebrow{text-transform:uppercase;letter-spacing:2px;font-size:11px;color:#e4cda9;font-weight:700}.hero h1{margin:3px 0 5px;font:600 clamp(24px,3vw,34px)/1.15 Georgia,serif;color:white}.hero p{margin:0;color:#eadde0}.hero-tag{border:1px solid #ffffff42;border-radius:999px;padding:9px 14px;color:#f2dfc1;font-size:12px;white-space:nowrap}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:20px 0}.stat,.panel{background:white;border:1px solid #eee4e2;border-radius:17px;box-shadow:0 4px 18px #49253208}.stat{padding:18px 20px}.stat-label{color:var(--muted);font-size:13px}.stat-value{font:600 30px Georgia,serif;color:var(--wine);margin-top:5px}.stat-note{font-size:12px;color:var(--muted)}.content-grid{display:grid;grid-template-columns:minmax(300px,.86fr) minmax(0,1.4fr);gap:18px;align-items:start}.panel{padding:23px}.panel h2{font:600 22px Georgia,serif;color:var(--wine-dark);margin:0 0 5px}.sub{color:var(--muted);margin:0 0 20px;font-size:13px}.field{margin:15px 0}.field label{display:block;font-weight:650;font-size:13px;margin-bottom:7px}.field input,.field select{width:100%;border:1px solid #d9cbca;background:#fffdfb;padding:12px 13px;border-radius:10px;font:inherit;color:var(--ink);outline:none}.field input:focus,.field select:focus{border-color:var(--gold);box-shadow:0 0 0 3px #c8a56a25}.hint{font-size:12px;color:var(--muted);margin-top:6px}.btn{border:0;background:var(--wine);color:white;padding:12px 17px;border-radius:10px;font:650 14px inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}.btn:hover{background:var(--wine-dark);text-decoration:none}.btn.secondary{background:#f5ecec;color:var(--wine);border:1px solid #e7d8da}.btn.full{width:100%;margin-top:5px}.pill{display:inline-flex;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:700;background:#f2eceb;color:#6b565b;white-space:nowrap}.pill.good{background:#e4f4eb;color:var(--green)}.pill.bad{background:#fae9e9;color:var(--red)}.pill.pending{background:#fff3d9;color:#8a651d}.table-head{display:flex;justify-content:space-between;align-items:start;gap:12px;margin-bottom:15px}.search{max-width:240px;width:100%;border:1px solid #e2d6d5;padding:10px 12px;border-radius:9px;font:inherit}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:570px}th{text-align:left;text-transform:uppercase;letter-spacing:.7px;font-size:10px;color:var(--muted);padding:12px 10px;border-bottom:1px solid var(--line)}td{padding:14px 10px;border-bottom:1px solid #f1e9e8;font-size:13px}tr:last-child td{border-bottom:0}.guest-name{font-weight:700;color:var(--wine-dark)}.empty{text-align:center;padding:35px 12px;color:var(--muted)}.small{font-size:12px;color:var(--muted)}.actions{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0}.preview{display:block;max-width:310px;width:100%;max-height:520px;object-fit:contain;border:1px solid var(--line);border-radius:12px;background:#faf7f3;margin:auto}.message{width:100%;min-height:240px;border:1px solid var(--line);border-radius:12px;padding:13px;font:14px/1.6 inherit;white-space:pre-wrap}.detail-grid{display:grid;grid-template-columns:minmax(220px,.8fr) minmax(0,1.2fr);gap:20px}.notice{border-radius:11px;padding:12px 14px;background:#f8f0e6;color:#6c4b22;font-size:13px;margin:12px 0}.footer{text-align:center;color:#938488;font-size:12px;margin-top:24px}
@media(max-width:850px){.content-grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{align-items:flex-start;flex-direction:column}.detail-grid{grid-template-columns:1fr}.preview{max-height:450px}}
@media(max-width:480px){.shell{padding:14px 12px 30px}.hero,.panel{padding:19px}.stats{gap:9px}.stat{padding:14px}.stat-value{font-size:25px}.table-head{flex-direction:column}.search{max-width:none}}
'''


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS invitations (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
        phone TEXT, message TEXT NOT NULL, image TEXT NOT NULL,
        rsvp TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL,
        delivery_status TEXT NOT NULL DEFAULT 'Not sent',
        delivery_error TEXT NOT NULL DEFAULT '', sent_at TEXT NOT NULL DEFAULT ''
    )''')
    # Migrate existing databases without deleting existing guest records.
    columns = {row[1] for row in con.execute("PRAGMA table_info(invitations)").fetchall()}
    for column, definition in (
        ("delivery_status", "TEXT NOT NULL DEFAULT 'Not sent'"),
        ("delivery_error", "TEXT NOT NULL DEFAULT ''"),
        ("sent_at", "TEXT NOT NULL DEFAULT ''"),
    ):
        if column not in columns:
            con.execute(f"ALTER TABLE invitations ADD COLUMN {column} {definition}")
    con.commit()
    return con


def cfg(key, default=""):
    return os.getenv(key, default).strip()


def font(size, bold=False):
    candidates = (["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold
                  else ["C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/arial.ttf"])
    candidates += (["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"] if bold
                   else ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"])
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def find_template():
    folder = ROOT / "assets" / "templates"
    for filename in ("fanuel wedding card.jpeg", "fanuel wedding card.png",
                     "fanuel invitation.jpeg", "fanuel invitation.jpg",
                     "invitation.png", "invitation.jpeg", "invitation.jpg"):
        candidate = folder / filename
        if candidate.is_file():
            return candidate
    return None


def make_card(name, kind, ident):
    template = find_template()
    if template is None:
        raise FileNotFoundError("No wedding card found in assets/templates/. Check the image filename.")
    with Image.open(template) as source:
        im = source.convert("RGB")
    draw = ImageDraw.Draw(im)
    width, height = im.size
    try:
        anchor = float(cfg("NAME_ANCHOR_Y", "0.32"))
    except ValueError:
        anchor = 0.32
    anchor = max(0.05, min(0.95, anchor))
    center_y = int(height * anchor)
    max_text_width = width * 0.56
    size = max(18, int(width * 0.038))
    selected_font = font(size, bold=True)
    while size > 18:
        bounds = draw.textbbox((0, 0), name, font=selected_font)
        if bounds[2] - bounds[0] <= max_text_width:
            break
        size -= 1
        selected_font = font(size, bold=True)
    bounds = draw.textbbox((0, 0), name, font=selected_font)
    text_width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    pad_x, pad_y = max(10, int(width * .012)), max(4, int(height * .004))
    left = int((width - text_width) / 2) - pad_x
    top = center_y - int(text_height / 2) - pad_y
    right = int((width + text_width) / 2) + pad_x
    bottom = center_y + int(text_height / 2) + pad_y
    draw.rounded_rectangle((left, top, right, bottom), radius=max(3, int(width * .006)), fill="#f8efe2")
    draw.text(((width - text_width) / 2, center_y - text_height / 2 - bounds[1]),
              name, font=selected_font, fill="#70303b")
    output_path = OUT / f"{ident}.png"
    im.save(output_path, format="PNG", optimize=True)
    return output_path


def message_for(name, kind):
    people = "mtu mmoja tu (wewe)" if kind == "Single" else "watu wawili (wewe na mwandamani mmoja)"
    lines = [
        f"Habari {name},", "",
        "Familia ya Bw. na Bi. Johnson Fanuel Mzava inayo furaha kubwa kukualika kushiriki nasi katika sherehe ya ndoa ya mwana wao, Fanuel Johnson.", "",
        f"Tarehe: {cfg('WEDDING_DATE', 'Jumamosi, 24 Oktoba 2026')}",
        f"Saa: {cfg('WEDDING_TIME', '7:00 mchana')}",
        f"Mahali: {cfg('WEDDING_VENUE', 'Ukumbi wa Mbise Lodge')}", "",
        f"Aina ya mwaliko: {kind} — mwaliko huu unamhusu {people}.", "",
        "Kwa mawasiliano zaidi, tafadhali wasiliana na:",
        cfg("CONTACT_1", "Kiangi Mangara — 0755 337 570"),
        cfg("CONTACT_2", "Christina J. Mturi — 0757 447 724"),
        cfg("CONTACT_3", "Beatrice F. Kisimbo — 0715 569 866"), "",
        "Tunatazamia kusherehekea pamoja nawe siku hii ya pekee.",
        "Karibu sana!"
    ]
    return "\n".join(lines)


def normalize_phone(value):
    raw = value.strip()
    digits = re.sub(r"\D", "", raw)
    # Tanzania local mobile format 0XXXXXXXXX becomes country code 255XXXXXXXXX.
    if digits.startswith("0") and len(digits) == 10:
        digits = "255" + digits[1:]
    if not (8 <= len(digits) <= 15):
        raise ValueError("Enter a valid WhatsApp number, preferably with country code, e.g. +255712345678.")
    return digits


def _meta_post_json(url, token, payload, action_label):
    request = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"
    })
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(action_label + ": " + _provider_error(exc)) from exc
    messages = result.get("messages") or []
    if not messages or not messages[0].get("id"):
        raise RuntimeError(action_label + ": WhatsApp did not confirm acceptance: " + json.dumps(result)[:500])
    return messages[0]["id"]


def meta_send_image_then_text(phone, image_path, message):
    """Upload and send the invitation image first, then send the full text as a separate message."""
    token = cfg("META_ACCESS_TOKEN")
    phone_id = cfg("META_PHONE_NUMBER_ID")
    version = cfg("META_API_VERSION", "v23.0")
    if not token or not phone_id:
        raise RuntimeError("Meta WhatsApp credentials are missing. Set META_ACCESS_TOKEN and META_PHONE_NUMBER_ID in .env.")
    base = f"https://graph.facebook.com/{version}/{phone_id}"
    boundary = "----WeddingStudio" + uuid.uuid4().hex
    file_bytes = image_path.read_bytes()
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{image_path.name}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    upload_req = Request(base + "/media", data=b"".join(parts), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"
    })
    try:
        with urlopen(upload_req, timeout=30) as response:
            media_data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Invitation image upload failed: " + _provider_error(exc)) from exc
    media_id = media_data.get("id")
    if not media_id:
        raise RuntimeError("WhatsApp image upload did not return a media ID.")

    # First send the PNG as its own image message, without a caption.
    image_message_id = _meta_post_json(base + "/messages", token, {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "image",
        "image": {"id": media_id},
    }, "Invitation image send failed")

    # Then send the complete Swahili invitation as a separate text message.
    try:
        text_message_id = _meta_post_json(base + "/messages", token, {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }, "Invitation text send failed")
    except Exception as exc:
        raise RuntimeError(
            "The invitation image was accepted by WhatsApp, but the follow-up text failed. " + str(exc)
        ) from exc
    return image_message_id, text_message_id


def _provider_error(exc):
    try:
        if hasattr(exc, "read"):
            body = exc.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            err = data.get("error", {})
            return str(err.get("message") or body)[:600]
    except Exception:
        pass
    return str(exc)[:600]


def page(body, title="Wedding Invitation Studio"):
    return HTMLResponse('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(title)}</title><style>' + CSS + '</style></head><body><main class="shell">'
        + body + '<div class="footer">Wedding Invitation Studio · Guest details are stored locally in your project database.</div></main></body></html>')


def status_pill(status):
    lowered = status.lower()
    klass = "good" if "accepted" in lowered or "sent" == lowered else "bad" if "failed" in lowered else "pending"
    return f'<span class="pill {klass}">{escape(status)}</span>'


@app.get("/", response_class=HTMLResponse)
def home():
    with db() as con:
        rows = con.execute("SELECT * FROM invitations ORDER BY created_at DESC").fetchall()
    total = len(rows)
    yes = sum(row["rsvp"] == "Yes" for row in rows)
    pending_rsvp = sum(row["rsvp"] == "Pending" for row in rows)
    delivery_ok = sum("accepted" in (row["delivery_status"] or "").lower() for row in rows)
    table_rows = "".join(
        f'<tr data-search="{escape((row["name"] + " " + (row["phone"] or "")).lower(), quote=True)}">'
        f'<td><a class="guest-name" href="/invite/{row["id"]}">{escape(row["name"])}</a><div class="small">{escape(row["phone"] or "No phone added")}</div></td>'
        f'<td>{escape(row["kind"])}</td><td>{status_pill(row["rsvp"])}</td>'
        f'<td>{status_pill(row["delivery_status"] or "Not sent")}</td>'
        f'<td>{escape(row["created_at"][:10])}</td></tr>' for row in rows
    ) or '<tr><td colspan="5"><div class="empty">No guests yet. Add your first guest using the form.</div></td></tr>'
    provider = cfg("WHATSAPP_PROVIDER", "mock").lower()
    mode_text = "Meta WhatsApp API" if provider == "meta" else "Test mode · messages are not sent"
    mode_class = "good" if provider == "meta" else "pending"
    return page(f'''
    <header class="hero"><div class="brand"><div class="brandmark">♡</div><div><div class="eyebrow">Celebrating together</div><h1>Wedding Invitation Studio</h1><p>Guest invitations, WhatsApp delivery and RSVP tracking.</p></div></div><div class="hero-tag">✦ Elegant event management</div></header>
    <div class="stats">
      <div class="stat"><div class="stat-label">Total invitations</div><div class="stat-value">{total}</div><div class="stat-note">Guests added to your list</div></div>
      <div class="stat"><div class="stat-label">Confirmed attendance</div><div class="stat-value">{yes}</div><div class="stat-note">Guests who replied YES</div></div>
      <div class="stat"><div class="stat-label">Awaiting RSVP</div><div class="stat-value">{pending_rsvp}</div><div class="stat-note">Responses still pending</div></div>
      <div class="stat"><div class="stat-label">Accepted by WhatsApp</div><div class="stat-value">{delivery_ok}</div><div class="stat-note">Provider accepted send requests</div></div>
    </div>
    <div class="content-grid">
      <section class="panel"><h2>Create an invitation</h2><p class="sub">Enter each guest's details. The card and message are prepared together.</p>
        <div style="margin-bottom:14px">Delivery mode: <span class="pill {mode_class}">{escape(mode_text)}</span></div>
        <form method="post" action="/create">
          <div class="field"><label for="name">Guest's full name</label><input id="name" name="name" maxlength="100" required placeholder="e.g. Asha Mwinyi" autocomplete="name"></div>
          <div class="field"><label for="phone">Guest's WhatsApp number</label><input id="phone" name="phone" type="tel" placeholder="+255712345678" autocomplete="tel" {"required" if provider == "meta" else ""}><div class="hint">Use the international format (+255...). Tanzanian numbers starting with 0 are converted automatically.</div></div>
          <div class="field"><label for="kind">Invitation type</label><select id="kind" name="kind"><option value="Single" selected>Single · 1 guest</option><option value="Double">Double · 2 guests</option></select></div>
          <button class="btn full" type="submit">✦ Create invitation</button>
        </form>
        <div class="notice">WhatsApp sends only when <code>WHATSAPP_PROVIDER=meta</code> and valid Meta credentials are configured. Mock mode never sends a real message.</div>
        <p class="small">Template file is read from <code>assets/templates/</code>. Guest records remain in your existing SQLite database.</p>
      </section>
      <section class="panel"><div class="table-head"><div><h2>Guest list</h2><p class="sub" style="margin:4px 0 0">Manage invitations, delivery and RSVP replies.</p></div><input class="search" id="guestSearch" placeholder="Search guests or phone…" aria-label="Search guests"></div>
        <div class="table-wrap"><table><thead><tr><th>Guest</th><th>Type</th><th>RSVP</th><th>Delivery</th><th>Created</th></tr></thead><tbody id="guestRows">{table_rows}</tbody></table></div>
      </section>
    </div>
    <script>document.getElementById('guestSearch').addEventListener('input',function(){{const q=this.value.toLowerCase();document.querySelectorAll('#guestRows tr[data-search]').forEach(r=>r.style.display=r.dataset.search.includes(q)?'':'none')}});</script>
    ''')


@app.post("/create")
def create(name: str = Form(...), kind: str = Form("Single"), phone: str = Form("")):
    name = " ".join(name.split())
    if not name or len(name) > 100 or kind not in ("Single", "Double"):
        raise HTTPException(400, "Invalid name or invitation type")
    phone = phone.strip()
    provider = cfg("WHATSAPP_PROVIDER", "mock").lower()
    if phone:
        try:
            phone = normalize_phone(phone)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    if provider == "meta" and not phone:
        raise HTTPException(400, "A WhatsApp number is required when Meta sending is enabled.")
    ident = uuid.uuid4().hex
    image_path = make_card(name, kind, ident)
    message = message_for(name, kind)
    delivery_status = "Mock mode — not sent"
    delivery_error = ""
    sent_at = ""
    with db() as con:
        con.execute("INSERT INTO invitations (id,name,kind,phone,message,image,rsvp,created_at,delivery_status,delivery_error,sent_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (ident, name, kind, phone, message, image_path.name, "Pending", datetime.now(timezone.utc).isoformat(), delivery_status, delivery_error, sent_at))
    if provider == "meta":
        try:
            image_message_id, text_message_id = meta_send_image_then_text(phone, image_path, message)
            delivery_status = "Image and text accepted by WhatsApp"
            delivery_error = ""
            sent_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            delivery_status = "Failed to send"
            delivery_error = str(exc)[:1000]
        with db() as con:
            con.execute("UPDATE invitations SET delivery_status=?,delivery_error=?,sent_at=? WHERE id=?",
                        (delivery_status, delivery_error, sent_at, ident))
    elif provider not in ("mock", ""):
        delivery_status = "Failed to send"
        delivery_error = f"Unsupported WHATSAPP_PROVIDER value: {provider}. Use mock or meta."
        with db() as con:
            con.execute("UPDATE invitations SET delivery_status=?,delivery_error=? WHERE id=?",
                        (delivery_status, delivery_error, ident))
    return RedirectResponse("/invite/" + ident, status_code=303)


def get_invite(ident):
    with db() as con:
        row = con.execute("SELECT * FROM invitations WHERE id=?", (ident,)).fetchone()
    if row is None:
        raise HTTPException(404, "Invitation not found")
    return row


@app.get("/invite/{ident}", response_class=HTMLResponse)
def invitation(ident: str):
    row = get_invite(ident)
    message_html = escape(row["message"])
    phone = re.sub(r"\D", "", row["phone"] or "")
    whatsapp_url = f'https://wa.me/{phone}?text={quote(row["message"])}' if phone else f'https://wa.me/?text={quote(row["message"])}'
    status = row["delivery_status"] or "Not sent"
    error_box = f'<div class="notice" style="background:#fae9e9;color:#8d2c34"><strong>Delivery issue:</strong> {escape(row["delivery_error"] or "No provider details available.")}</div>' if "failed" in status.lower() else ''
    if "accepted" in status.lower():
        delivery_note = "WhatsApp accepted both the image and text send requests. Final delivery/read status may arrive later through a configured webhook."
    elif "mock" in status.lower():
        delivery_note = "Test mode is active. No real WhatsApp message or image was sent."
    else:
        delivery_note = "Review the delivery status below. An invitation record being created does not mean it was delivered."
    rsvp_options = "".join(f'<option value="{value}" {"selected" if row["rsvp"] == value else ""}>{label}</option>' for value, label in (("Pending", "Pending"), ("Yes", "Yes — attending"), ("No", "No — not attending")))
    return page(f'''
      <header class="hero"><div class="brand"><div class="brandmark">♡</div><div><div class="eyebrow">Invitation details</div><h1>{escape(row['name'])}</h1><p>{escape(row['kind'])} invitation · {escape(row['phone'] or 'No WhatsApp number')}</p></div></div><a class="hero-tag" href="/">← Back to dashboard</a></header>
      <section class="panel" style="margin-top:18px"><div class="table-head"><div><h2>Delivery status</h2><p class="sub">Current result for this invitation.</p></div>{status_pill(status)}</div><p>{escape(delivery_note)}</p>{error_box}<p class="small">{('Request accepted at ' + escape(row['sent_at'])) if row['sent_at'] else 'No successful send timestamp recorded.'}</p></section>
      <div class="detail-grid" style="margin-top:18px"><section class="panel"><h2>Personalized PNG</h2><p class="sub">Generated from your original invitation design.</p><img class="preview" src="/png/{ident}" alt="Invitation for {escape(row['name'], quote=True)}"><div class="actions"><a class="btn" href="/png/{ident}?download=1">Download PNG</a></div></section>
      <div><section class="panel"><h2>WhatsApp message</h2><p class="sub">The invitation PNG is sent first, followed by this full message as a separate WhatsApp text.</p><textarea class="message" id="msg" readonly>{message_html}</textarea><div class="actions"><button class="btn secondary" onclick="navigator.clipboard.writeText(document.getElementById('msg').value).then(()=>alert('Message copied'))">Copy message</button><a class="btn secondary" href="{escape(whatsapp_url, quote=True)}" target="_blank" rel="noopener">Open WhatsApp manually</a></div></section>
      <section class="panel" style="margin-top:18px"><h2>RSVP tracking</h2><p class="sub">Record a reply received from the guest.</p><form method="post" action="/rsvp/{ident}"><div class="field"><label for="response">Attendance response</label><select id="response" name="response">{rsvp_options}</select></div><button class="btn" type="submit">Save RSVP</button></form></section></div></div>
    ''', title=f"{row['name']} · Invitation")


@app.get("/png/{ident}")
def png(ident: str, download: int = 0):
    row = get_invite(ident)
    path = OUT / row["image"]
    if not path.is_file():
        raise HTTPException(404, "PNG missing")
    return FileResponse(path, media_type="image/png",
        filename=f'invitation-{ident[:8]}.png' if download else None,
        content_disposition_type="attachment" if download else "inline")


@app.post("/rsvp/{ident}")
def rsvp(ident: str, response: str = Form(...)):
    get_invite(ident)
    if response not in ("Pending", "Yes", "No"):
        raise HTTPException(400, "Invalid RSVP")
    with db() as con:
        con.execute("UPDATE invitations SET rsvp=? WHERE id=?", (response, ident))
    return RedirectResponse("/invite/" + ident, status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
