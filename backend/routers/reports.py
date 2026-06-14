from fastapi import APIRouter, Depends, Query

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin

router = APIRouter(prefix="/api/v1/reports", tags=["enterprise-reports"])


@router.get("/sales")
async def sales_report(
    store_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str = Query(default="terminal", pattern="^(terminal|product|hour)$"),
    _: AdminPrincipal = Depends(require_admin),
):
    """Return sales aggregates; production implementation should query the reporting replica."""
    return ok({"store_id": store_id, "date_from": date_from, "date_to": date_to, "group_by": group_by, "rows": []})


@router.get("/device-health")
async def device_health_report(brand_id: str | None = None, store_id: str | None = None, _: AdminPrincipal = Depends(require_admin)):
    """Return latest device heartbeat aggregates."""
    return ok({"brand_id": brand_id, "store_id": store_id, "devices": []})


@router.get("/customer/{customer_id}/purchases")
async def customer_purchases(customer_id: str, _: AdminPrincipal = Depends(require_admin)):
    """Return customer purchase history."""
    return ok({"customer_id": customer_id, "orders": []})


@router.get("/terminal/{terminal_id}/summary")
async def terminal_summary(terminal_id: str, _: AdminPrincipal = Depends(require_admin)):
    """Return terminal order and health summary."""
    return ok({"terminal_id": terminal_id, "summary": {}})
