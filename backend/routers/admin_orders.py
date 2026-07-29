from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..api_response import ok
from ..auth import AdminPrincipal, require_admin
from ..database import get_db
from ..errors import ErrorCode
from ..models import Order, OrderItem, Store
from ..models import customers as Customer
from ..schemas_catalog import (
    AdminOrderDetailResponse,
    AdminOrderItemResponse,
    AdminOrderListItem,
    OrderRefundRequest,
)
from ..services.audit import write_audit_log
from ._admin_common import require_brand_access

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])


def _order_detail_response(order: Order, store_name: str) -> dict:
    return AdminOrderDetailResponse(
        order_id=order.order_id,
        order_number=order.order_number,
        store_id=order.store_id,
        store_name=store_name,
        customer_name=order.customer.name if order.customer else None,
        customer_phone=order.customer.phone if order.customer else None,
        customer_email=order.customer.email if order.customer else None,
        status=order.status,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        cgst_total=order.cgst_total,
        sgst_total=order.sgst_total,
        grand_total=order.grand_total,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        payment_ref=order.payment_ref,
        ordered_at=order.ordered_at,
        completed_at=order.completed_at,
        items=[
            AdminOrderItemResponse(
                item_id=item.item_id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else "",
                sku=item.product.sku if item.product else "",
                quantity=item.quantity,
                unit_price=item.unit_price,
                mrp=item.mrp,
                discount_amount=item.discount_amount,
                cgst_amount=item.cgst_amount,
                sgst_amount=item.sgst_amount,
                line_total=item.line_total,
            )
            for item in order.items
        ],
    ).model_dump(mode="json")


@router.get("")
async def list_orders(
    store_id: UUID | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Order, Store.name)
        .join(Store, Store.store_id == Order.store_id)
        .outerjoin(Customer, Customer.customer_id == Order.customer_id)
        .options(selectinload(Order.customer))
    )

    # STORE_ADMIN only ever sees orders placed at stores in their own brand -
    # same restriction admin_catalog.py applies to inventory/terminals.
    if admin.role != "SUPER_ADMIN":
        if not admin.brand_id:
            raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Not authorized"})
        stmt = stmt.where(Store.brand_id == UUID(admin.brand_id))

    if store_id is not None:
        stmt = stmt.where(Order.store_id == store_id)
    if status:
        stmt = stmt.where(Order.status == status)
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
    if date_from:
        stmt = stmt.where(Order.ordered_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.ordered_at <= date_to)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Order.order_number.ilike(like), Customer.name.ilike(like), Customer.phone.ilike(like)))

    stmt = stmt.order_by(Order.ordered_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.all()
    return ok(
        [
            AdminOrderListItem(
                order_id=order.order_id,
                order_number=order.order_number,
                store_id=order.store_id,
                store_name=store_name,
                customer_name=order.customer.name if order.customer else None,
                customer_phone=order.customer.phone if order.customer else None,
                status=order.status,
                payment_status=order.payment_status,
                payment_method=order.payment_method,
                grand_total=order.grand_total,
                ordered_at=order.ordered_at,
                completed_at=order.completed_at,
            ).model_dump(mode="json")
            for order, store_name in rows
        ]
    )


@router.get("/{order_id}")
async def get_order_detail(
    order_id: UUID,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order, Store.name)
        .join(Store, Store.store_id == Order.store_id)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .where(Order.order_id == order_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Order not found"})
    order, store_name = row

    store_result = await db.execute(select(Store).where(Store.store_id == order.store_id))
    store = store_result.scalar_one()
    require_brand_access(admin, store.brand_id)

    return ok(_order_detail_response(order, store_name))


@router.post("/{order_id}/refund")
async def refund_order(
    order_id: UUID,
    payload: OrderRefundRequest,
    admin: AdminPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.order_id == order_id).with_for_update())
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Order not found"})

    store_result = await db.execute(select(Store).where(Store.store_id == order.store_id))
    store = store_result.scalar_one()
    require_brand_access(admin, store.brand_id)

    if order.payment_status != "PAID":
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.CONFLICT,
                "message": f"Cannot refund an order with payment status {order.payment_status}",
            },
        )

    order.status = "REFUNDED"
    order.payment_status = "REFUNDED"
    order.updated_at = datetime.utcnow()
    await db.flush()

    await write_audit_log(
        db,
        event_type="ORDER_REFUNDED",
        entity_type="order",
        entity_id=order.order_id,
        actor_type="admin",
        actor_id=UUID(admin.admin_id),
        notes=payload.reason,
    )

    return ok({"order_id": str(order.order_id), "status": order.status, "payment_status": order.payment_status})
