# scripts/notify.py
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Leitura de variáveis de ambiente ─────────────────────────────────────────
SMTP_HOST   = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT   = int(os.environ.get("SMTP_PORT", "1025"))
EMAIL_TO    = os.environ["EMAIL_TO"]          # Obrigatório — erro se ausente
EMAIL_FROM  = os.environ.get("EMAIL_FROM", "jenkins@steamapi.local")

BUILD_STATUS = sys.argv[1] if len(sys.argv) > 1 else "DESCONHECIDO"
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "?")
BUILD_URL    = os.environ.get("BUILD_URL", "#")

# ─── Montagem do e-mail ────────────────────────────────────────────────────────
subject = f"[Steam API Tests] Build #{BUILD_NUMBER} — {BUILD_STATUS}"

body = f"""
Pipeline Jenkins — Steam API Testes Automatizados

Status   : {BUILD_STATUS}
Build    : #{BUILD_NUMBER}
URL      : {BUILD_URL}

Verifique os artefatos no Jenkins para os relatórios HTML completos.
"""

msg = MIMEMultipart()
msg["From"]    = EMAIL_FROM
msg["To"]      = EMAIL_TO
msg["Subject"] = subject
msg.attach(MIMEText(body, "plain"))

# ─── Envio ─────────────────────────────────────────────────────────────────────
try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"E-mail enviado para {EMAIL_TO} via {SMTP_HOST}:{SMTP_PORT}")
except Exception as e:
    print(f"Falha ao enviar e-mail: {e}", file=sys.stderr)
    sys.exit(1)
