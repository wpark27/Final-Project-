"""Email digest of new updates, via any SMTP server (env-configured)."""
from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage

DEFAULT_TO = "winstonpark27@gmail.com"


def render(updates: list[dict]) -> tuple[str, str, str]:
    subject = f"[Sponsor Calendar] {len(updates)} new update{'s' if len(updates) != 1 else ''}"
    labels = {"released": "RELEASED", "date_confirmed": "DATE CONFIRMED", "new_report": "NEW REPORT", "appointment": "APPOINTMENT"}
    text, rows = [], []
    for u in updates:
        tag = labels.get(u["type"], u["type"])
        text.append(f"[{tag}] {u['entity']} - {u['headline']}\n  {u.get('summary', '')}\n  {u['url']}\n")
        metrics = "".join(f"<li>{html.escape(m)}</li>" for m in u.get("metrics", []))
        rows.append(
            f"<h3 style='margin:16px 0 4px'>{html.escape(tag)} · {html.escape(u['entity'])}</h3>"
            f"<p style='margin:0'><b>{html.escape(u['headline'])}</b></p>"
            f"<p style='margin:4px 0'>{html.escape(u.get('summary', ''))}</p>"
            + (f"<ul>{metrics}</ul>" if metrics else "")
            + f"<p><a href='{html.escape(u['url'])}'>Official source</a></p>"
        )
    return subject, "\n".join(text), "<div style='font-family:sans-serif'>" + "".join(rows) + "</div>"


def send_email(updates: list[dict]) -> None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST is not set; cannot send email")
    subject, text, body_html = render(updates)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "calendar-bot@localhost"))
    msg["To"] = os.environ.get("NOTIFY_TO", DEFAULT_TO)
    msg.set_content(text)
    msg.add_alternative(body_html, subtype="html")
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)
