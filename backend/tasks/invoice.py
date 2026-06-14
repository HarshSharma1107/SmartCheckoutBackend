from __future__ import annotations

from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..celery_app import celery_app

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.invoice.generate_invoice_pdf")
def generate_invoice_pdf(self, order_id: str) -> dict[str, str]:
    """Render a GST invoice and upload it to object storage.

    The current implementation renders HTML as a deterministic artifact path.
    Install/configure WeasyPrint and S3 credentials before enabling PDF upload.
    """
    UUID(order_id)
    template = env.get_template("invoice.html")
    html = template.render(
        brand={"name": "SmartCheckout", "gstin": ""},
        store={"name": "Store", "address_line1": ""},
        order={"order_number": order_id, "grand_total": "0.00", "payment_method": ""},
        customer={"name": "Customer", "phone": ""},
        items=[],
        gst_summary=[],
    )
    out_dir = Path("tmp") / "invoices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{order_id}.html"
    out.write_text(html, encoding="utf-8")
    return {"order_id": order_id, "artifact": str(out)}

