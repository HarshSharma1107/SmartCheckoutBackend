import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import SMTP_EMAIL, SMTP_FROM_NAME, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT
from ..models import Order

logger = logging.getLogger(__name__)


def _build_receipt_email(order: Order) -> tuple[str, str, str]:
    subject = f"Your SmartCheckout receipt — {order.order_number}"

    rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 0'>{item.product.name if item.product else ''} × {item.quantity}</td>"
        f"<td style='padding:6px 0;text-align:right'>₹{float(item.line_total):.2f}</td>"
        f"</tr>"
        for item in order.items
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto">
      <h2 style="margin-bottom:0">SmartCheckout</h2>
      <p style="color:#666;margin-top:4px">Order {order.order_number}</p>
      <p>Hi {order.customer.name if order.customer else ''},</p>
      <p>Thanks for shopping with us! Here's your receipt.</p>
      <table style="width:100%;border-collapse:collapse;margin-top:12px">
        {rows}
      </table>
      <hr style="border:none;border-top:1px solid #ddd;margin:12px 0" />
      <table style="width:100%">
        <tr><td>Subtotal</td><td style="text-align:right">₹{float(order.subtotal):.2f}</td></tr>
        <tr><td>CGST</td><td style="text-align:right">₹{float(order.cgst_total):.2f}</td></tr>
        <tr><td>SGST</td><td style="text-align:right">₹{float(order.sgst_total):.2f}</td></tr>
        <tr><td style="font-weight:bold">Total Paid</td><td style="text-align:right;font-weight:bold">₹{float(order.grand_total):.2f}</td></tr>
        <tr><td>Payment Method</td><td style="text-align:right">{order.payment_method}</td></tr>
      </table>
      <p style="color:#999;font-size:12px;margin-top:20px">This is an automated receipt. Please do not reply.</p>
    </div>
    """

    text = (
        f"SmartCheckout receipt - Order {order.order_number}\n\n"
        + "\n".join(
            f"{item.product.name if item.product else ''} x{item.quantity} - Rs.{float(item.line_total):.2f}"
            for item in order.items
        )
        + f"\n\nSubtotal: Rs.{float(order.subtotal):.2f}"
        f"\nCGST: Rs.{float(order.cgst_total):.2f}"
        f"\nSGST: Rs.{float(order.sgst_total):.2f}"
        f"\nTotal Paid: Rs.{float(order.grand_total):.2f}"
        f"\nPayment Method: {order.payment_method}\n"
    )

    return subject, text, html


def send_receipt_email(to_email: str, order: Order) -> None:
    """Best-effort receipt delivery. Runs as a FastAPI background task after
    checkout has already committed, so a mail failure (bad credentials, SMTP
    outage) must never surface as a checkout error - just log it."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning("SMTP_EMAIL/SMTP_PASSWORD not configured - skipping receipt email to %s", to_email)
        return

    subject, text, html = _build_receipt_email(order)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_EMAIL}>"
    message["To"] = to_email
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, [to_email], message.as_string())
    except Exception:
        logger.exception("Failed to send receipt email for order %s to %s", order.order_number, to_email)
