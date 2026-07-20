import json
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api_response import ok
from ..auth import DevicePrincipal, require_device, require_webhook_key
from ..database import get_db
from ..errors import ErrorCode
from ..schemas_enterprise import (
    CheckoutRequest,
    CheckoutResponse,
    EnterpriseOrderCreateRequest,
    EnterpriseOrderCreateResponse,
    OrderItemCreateRequest,
    OrderItemMutationResponse,
    OrderItemUpdateRequest,
    PaymentConfirmationRequest,
)
from ..services.audit import write_audit_log
from ..services.pricing import calculate_line_total, calculate_order_delta, calculate_release_delta

router = APIRouter(prefix="/api/v1/orders", tags=["enterprise-orders"])


async def _load_order_context(db: AsyncSession, order_id: UUID):
    result = await db.execute(
        text("SELECT * FROM ekart_prod.orders WHERE order_id = :order_id"),
        {"order_id": order_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Order not found"})
    return row


async def _load_order_item_for_update(db: AsyncSession, order_id: UUID, item_id: UUID):
    result = await db.execute(
        text(
            """
            SELECT oi.*, p.name,
                   i.inventory_id, i.qty_on_hand, i.qty_reserved
            FROM ekart_prod.order_items oi
            JOIN ekart_prod.orders o ON o.order_id = oi.order_id
            JOIN ekart_prod.products p ON p.product_id = oi.product_id
            JOIN ekart_prod.inventory i
              ON i.product_id = oi.product_id AND i.store_id = o.store_id
            WHERE oi.order_id = :order_id AND oi.item_id = :item_id
            FOR UPDATE OF i, oi
            """
        ),
        {"order_id": order_id, "item_id": item_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Order item not found"})
    return row


async def _apply_order_delta(db: AsyncSession, order_id: UUID, delta: dict[str, Decimal | int]) -> None:
    await db.execute(
        text(
            """
            UPDATE ekart_prod.orders
            SET subtotal = GREATEST(0, subtotal + :base_delta),
                cgst_total = GREATEST(0, cgst_total + :cgst_delta),
                sgst_total = GREATEST(0, sgst_total + :sgst_delta),
                grand_total = GREATEST(0, grand_total + :line_delta)
            WHERE order_id = :order_id
            """
        ),
        {"order_id": order_id, **delta},
    )


async def _insert_inventory_transaction(
    db: AsyncSession,
    *,
    product_id: UUID,
    store_id: UUID,
    order_id: UUID,
    order_item_id: UUID | None,
    transaction_type: str,
    quantity_delta: int,
    qty_on_hand_after: int | None = None,
    qty_reserved_after: int | None = None,
    reason: str,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO ekart_prod.inventory_transactions (
                product_id, store_id, order_id, order_item_id,
                transaction_type, quantity_delta, qty_on_hand_after,
                qty_reserved_after, reason, actor_type
            )
            VALUES (
                :product_id, :store_id, :order_id, :order_item_id,
                :transaction_type, :quantity_delta, :qty_on_hand_after,
                :qty_reserved_after, :reason, 'device'
            )
            """
        ),
        {
            "product_id": product_id,
            "store_id": store_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
            "transaction_type": transaction_type,
            "quantity_delta": quantity_delta,
            "qty_on_hand_after": qty_on_hand_after,
            "qty_reserved_after": qty_reserved_after,
            "reason": reason,
        },
    )


async def _idempotency_hit(db: AsyncSession, scope: str, key: str | None):
    if not key:
        return None
    result = await db.execute(
        text(
            """
            SELECT response
            FROM ekart_prod.idempotency_keys
            WHERE idempotency_key = :key
              AND scope = :scope
              AND expires_at > now()
            """
        ),
        {"key": key, "scope": scope},
    )
    row = result.mappings().one_or_none()
    return row["response"] if row else None


async def _store_idempotency(db: AsyncSession, scope: str, key: str | None, response: dict) -> None:
    if not key:
        return
    await db.execute(
        text(
            """
            INSERT INTO ekart_prod.idempotency_keys (
                idempotency_key, scope, response, expires_at
            )
            VALUES (:key, :scope, CAST(:response AS jsonb), now() + interval '15 minutes')
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {"key": key, "scope": scope, "response": json.dumps(response)},
    )


@router.post("/cart")
async def create_enterprise_order(
    payload: EnterpriseOrderCreateRequest,
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Create an ACTIVE cart order after validating terminal, store, and device assignment.

    Lives at `/cart` rather than the bare collection path on purpose: the
    legacy one-shot consumer endpoint (`backend/routers/orders.py`,
    `POST /api/v1/orders`, no auth) used to be silently shadowed by this
    route because both routers claimed the exact same path+method and this
    one was registered first - Starlette dispatches to the first match, so
    every legacy checkout request was hitting this device-gated handler
    and failing with "Missing device bearer token". Keep these two create
    endpoints on distinct paths so that can't happen again.
    """
    assignment = await db.execute(
        text(
            """
            SELECT 1
            FROM ekart_prod.device_terminal_assignments a
            JOIN ekart_prod.terminals t ON t.terminal_id = a.terminal_id
            WHERE a.device_id = :device_id
              AND a.terminal_id = :terminal_id
              AND t.store_id = :store_id
              AND a.revoked_at IS NULL
            """
        ),
        payload.model_dump(),
    )
    if not assignment.scalar_one_or_none():
        raise HTTPException(status_code=403, detail={"code": ErrorCode.FORBIDDEN, "message": "Device is not assigned to terminal/store"})

    customer_id = None
    if payload.customer_phone:
        customer = await db.execute(
            text(
                """
                INSERT INTO ekart_prod.customers (brand_id, phone)
                VALUES (:brand_id, :phone)
                ON CONFLICT (brand_id, phone) DO UPDATE SET updated_at = now()
                RETURNING customer_id
                """
            ),
            {"brand_id": payload.brand_id, "phone": payload.customer_phone},
        )
        customer_id = customer.scalar_one()

    order_number = f"ORD-{str(payload.store_id)[:8].upper()}-{uuid4().hex[:8].upper()}"
    result = await db.execute(
        text(
            """
            INSERT INTO ekart_prod.orders (
                order_number, brand_id, store_id, terminal_id, device_id, customer_id, status
            )
            VALUES (
                :order_number, :brand_id, :store_id, :terminal_id, :device_id, :customer_id, 'ACTIVE'
            )
            RETURNING order_id, order_number, status
            """
        ),
        {**payload.model_dump(), "customer_id": customer_id, "order_number": order_number},
    )
    row = result.mappings().one()
    await write_audit_log(
        db,
        event_type="ORDER_CREATED",
        entity_type="order",
        entity_id=row["order_id"],
        brand_id=payload.brand_id,
        store_id=payload.store_id,
        actor_type="device",
        payload={"terminal_id": str(payload.terminal_id), "device_id": str(payload.device_id)},
    )
    response = EnterpriseOrderCreateResponse(order_id=row["order_id"], order_number=row["order_number"], status="ACTIVE")
    return ok(response.model_dump(mode="json"))


@router.post("/{order_id}/items")
async def add_order_item(
    order_id: UUID,
    payload: OrderItemCreateRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Add an item and reserve inventory using a row lock."""
    scope = f"order-item-add:{order_id}"
    cached = await _idempotency_hit(db, scope, x_idempotency_key)
    if cached:
        return cached

    order = await _load_order_context(db, order_id)
    product = await db.execute(
        text(
            """
            SELECT p.product_id, p.sku, p.name, p.mrp, p.cgst_rate, p.sgst_rate,
                   i.inventory_id, i.qty_on_hand, i.qty_reserved
            FROM ekart_prod.product_barcodes pb
            JOIN ekart_prod.products p ON p.product_id = pb.product_id
            JOIN ekart_prod.inventory i
              ON i.product_id = p.product_id AND i.store_id = :store_id
            WHERE pb.barcode_value = :barcode
              AND pb.is_active = true
              AND p.is_active = true
              AND p.is_discontinued = false
            FOR UPDATE OF i
            """
        ),
        {"barcode": payload.barcode, "store_id": order["store_id"]},
    )
    row = product.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOT_FOUND, "message": "Barcode not found"})
    available = int(row["qty_on_hand"] or 0) - int(row["qty_reserved"] or 0)
    if available < payload.quantity:
        raise HTTPException(status_code=409, detail={"code": ErrorCode.INSUFFICIENT_STOCK, "message": f"Available: {available}"})

    totals = calculate_line_total(
        Decimal(row["mrp"]),
        payload.quantity,
        Decimal(row["cgst_rate"]),
        Decimal(row["sgst_rate"]),
    )
    inserted = await db.execute(
        text(
            """
            INSERT INTO ekart_prod.order_items (
                order_id, product_id, barcode_scanned, quantity, unit_price, mrp,
                cgst_rate, cgst_amount, sgst_rate, sgst_amount, line_total
            )
            VALUES (
                :order_id, :product_id, :barcode, :quantity, :unit_price, :mrp,
                :cgst_rate, :cgst_amount, :sgst_rate, :sgst_amount, :line_total
            )
            RETURNING item_id
            """
        ),
        {
            "order_id": order_id,
            "product_id": row["product_id"],
            "barcode": payload.barcode,
            "quantity": payload.quantity,
            "unit_price": row["mrp"],
            "mrp": row["mrp"],
            "cgst_rate": row["cgst_rate"],
            "cgst_amount": totals["cgst_amount"],
            "sgst_rate": row["sgst_rate"],
            "sgst_amount": totals["sgst_amount"],
            "line_total": totals["line_total"],
        },
    )
    item_id = inserted.scalar_one()
    await db.execute(
        text("UPDATE ekart_prod.inventory SET qty_reserved = qty_reserved + :quantity WHERE inventory_id = :inventory_id"),
        {"quantity": payload.quantity, "inventory_id": row["inventory_id"]},
    )
    await _insert_inventory_transaction(
        db,
        product_id=row["product_id"],
        store_id=order["store_id"],
        order_id=order_id,
        order_item_id=item_id,
        transaction_type="RESERVE",
        quantity_delta=payload.quantity,
        qty_on_hand_after=int(row["qty_on_hand"]),
        qty_reserved_after=int(row["qty_reserved"] or 0) + payload.quantity,
        reason="Cart item added",
    )
    await db.execute(
        text(
            """
            UPDATE ekart_prod.orders
            SET subtotal = subtotal + :base,
                cgst_total = cgst_total + :cgst_amount,
                sgst_total = sgst_total + :sgst_amount,
                grand_total = grand_total + :line_total
            WHERE order_id = :order_id
            """
        ),
        {"order_id": order_id, **totals},
    )
    response = OrderItemMutationResponse(
        item_id=item_id,
        product_id=row["product_id"],
        name=row["name"],
        quantity=payload.quantity,
        unit_price=float(row["mrp"]),
        line_total=float(totals["line_total"]),
        order_subtotal=float(Decimal(order["subtotal"]) + totals["base"]),
        order_grand_total=float(Decimal(order["grand_total"]) + totals["line_total"]),
    )
    envelope = ok(response.model_dump(mode="json"))
    await _store_idempotency(db, scope, x_idempotency_key, envelope)
    return envelope


@router.delete("/{order_id}/items/{item_id}")
async def delete_order_item(
    order_id: UUID,
    item_id: UUID,
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Remove an item, release reserved inventory, and recalculate totals."""
    order = await _load_order_context(db, order_id)
    item = await _load_order_item_for_update(db, order_id, item_id)
    delta = calculate_release_delta(
        quantity=int(item["quantity"]),
        unit_price=Decimal(item["unit_price"]),
        cgst_rate=Decimal(item["cgst_rate"]),
        sgst_rate=Decimal(item["sgst_rate"]),
        discount_amount=Decimal(item["discount_amount"] or 0),
    )
    new_reserved = max(0, int(item["qty_reserved"] or 0) - int(item["quantity"]))
    await db.execute(
        text("UPDATE ekart_prod.inventory SET qty_reserved = :qty_reserved WHERE inventory_id = :inventory_id"),
        {"qty_reserved": new_reserved, "inventory_id": item["inventory_id"]},
    )
    await db.execute(
        text("DELETE FROM ekart_prod.order_items WHERE order_id = :order_id AND item_id = :item_id"),
        {"order_id": order_id, "item_id": item_id},
    )
    await _apply_order_delta(db, order_id, delta)
    await _insert_inventory_transaction(
        db,
        product_id=item["product_id"],
        store_id=order["store_id"],
        order_id=order_id,
        order_item_id=item_id,
        transaction_type="RELEASE",
        quantity_delta=-int(item["quantity"]),
        qty_on_hand_after=int(item["qty_on_hand"]),
        qty_reserved_after=new_reserved,
        reason="Cart item removed",
    )
    await write_audit_log(
        db,
        event_type="ORDER_ITEM_REMOVED",
        entity_type="order",
        entity_id=order_id,
        brand_id=order["brand_id"],
        store_id=order["store_id"],
        actor_type="device",
        payload={"item_id": str(item_id), "quantity": int(item["quantity"])},
    )
    return ok({"deleted": True, "item_id": str(item_id)})


@router.patch("/{order_id}/items/{item_id}")
async def update_order_item(
    order_id: UUID,
    item_id: UUID,
    payload: OrderItemUpdateRequest,
    _: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db),
):
    """Adjust an item quantity and inventory reservation delta."""
    order = await _load_order_context(db, order_id)
    item = await _load_order_item_for_update(db, order_id, item_id)
    old_quantity = int(item["quantity"])
    if payload.quantity == old_quantity:
        response = OrderItemMutationResponse(
            item_id=item_id,
            product_id=item["product_id"],
            name=item["name"],
            quantity=old_quantity,
            unit_price=float(item["unit_price"]),
            line_total=float(item["line_total"]),
            order_subtotal=float(order["subtotal"]),
            order_grand_total=float(order["grand_total"]),
        )
        return ok(response.model_dump(mode="json"))

    quantity_delta = payload.quantity - old_quantity
    if quantity_delta > 0:
        available = int(item["qty_on_hand"] or 0) - int(item["qty_reserved"] or 0)
        if available < quantity_delta:
            raise HTTPException(status_code=409, detail={"code": ErrorCode.INSUFFICIENT_STOCK, "message": f"Available: {available}"})

    delta = calculate_order_delta(
        old_quantity=old_quantity,
        new_quantity=payload.quantity,
        unit_price=Decimal(item["unit_price"]),
        cgst_rate=Decimal(item["cgst_rate"]),
        sgst_rate=Decimal(item["sgst_rate"]),
        discount_amount=Decimal(item["discount_amount"] or 0),
    )
    new_reserved = max(0, int(item["qty_reserved"] or 0) + quantity_delta)
    await db.execute(
        text("UPDATE ekart_prod.inventory SET qty_reserved = :qty_reserved WHERE inventory_id = :inventory_id"),
        {"qty_reserved": new_reserved, "inventory_id": item["inventory_id"]},
    )
    await db.execute(
        text(
            """
            UPDATE ekart_prod.order_items
            SET quantity = :quantity,
                cgst_amount = :cgst_amount,
                sgst_amount = :sgst_amount,
                line_total = :line_total
            WHERE order_id = :order_id AND item_id = :item_id
            """
        ),
        {
            "order_id": order_id,
            "item_id": item_id,
            "quantity": payload.quantity,
            "cgst_amount": delta["new_cgst_amount"],
            "sgst_amount": delta["new_sgst_amount"],
            "line_total": delta["new_line_total"],
        },
    )
    await _apply_order_delta(db, order_id, delta)
    await _insert_inventory_transaction(
        db,
        product_id=item["product_id"],
        store_id=order["store_id"],
        order_id=order_id,
        order_item_id=item_id,
        transaction_type="RESERVATION_ADJUSTMENT",
        quantity_delta=quantity_delta,
        qty_on_hand_after=int(item["qty_on_hand"]),
        qty_reserved_after=new_reserved,
        reason="Cart quantity updated",
    )
    response = OrderItemMutationResponse(
        item_id=item_id,
        product_id=item["product_id"],
        name=item["name"],
        quantity=payload.quantity,
        unit_price=float(item["unit_price"]),
        line_total=float(delta["new_line_total"]),
        order_subtotal=float(Decimal(order["subtotal"]) + Decimal(delta["base_delta"])),
        order_grand_total=float(Decimal(order["grand_total"]) + Decimal(delta["line_delta"])),
    )
    return ok(response.model_dump(mode="json"))


@router.post("/{order_id}/checkout")
async def checkout_order(order_id: UUID, payload: CheckoutRequest, _: DevicePrincipal = Depends(require_device), db: AsyncSession = Depends(get_db)):
    """Move order to checkout and return payment instructions."""
    order = await _load_order_context(db, order_id)
    await db.execute(
        text("UPDATE ekart_prod.orders SET status='CHECKOUT', payment_method=:payment_method, payment_status='PENDING' WHERE order_id=:order_id"),
        {"order_id": order_id, "payment_method": payload.payment_method},
    )
    response = CheckoutResponse(grand_total=float(order["grand_total"]), qr_code_data=None, razorpay_order_id=None)
    return ok(response.model_dump(mode="json"))


@router.post("/{order_id}/payment-confirmation")
async def payment_confirmation(
    order_id: UUID,
    payload: PaymentConfirmationRequest,
    _: str = Depends(require_webhook_key),
    db: AsyncSession = Depends(get_db),
):
    """Finalize a paid order after payment gateway signature validation."""
    order = await _load_order_context(db, order_id)
    if order["status"] == "COMPLETED":
        return ok({"payment_status": order["payment_status"]})
    if payload.status != "SUCCESS":
        await db.execute(
            text("UPDATE ekart_prod.orders SET payment_status='FAILED', payment_ref=:payment_ref WHERE order_id=:order_id"),
            {"order_id": order_id, "payment_ref": payload.payment_ref},
        )
        return ok({"payment_status": "FAILED"})
    items = await db.execute(
        text(
            """
            SELECT oi.item_id, oi.product_id, oi.quantity,
                   i.inventory_id, i.qty_on_hand, i.qty_reserved
            FROM ekart_prod.order_items oi
            JOIN ekart_prod.inventory i
              ON i.product_id = oi.product_id AND i.store_id = :store_id
            WHERE oi.order_id = :order_id
            FOR UPDATE OF i
            """
        ),
        {"order_id": order_id, "store_id": order["store_id"]},
    )
    for item in items.mappings().all():
        qty = int(item["quantity"])
        new_on_hand = max(0, int(item["qty_on_hand"] or 0) - qty)
        new_reserved = max(0, int(item["qty_reserved"] or 0) - qty)
        await db.execute(
            text(
                """
                UPDATE ekart_prod.inventory
                SET qty_on_hand = :qty_on_hand, qty_reserved = :qty_reserved
                WHERE inventory_id = :inventory_id
                """
            ),
            {"inventory_id": item["inventory_id"], "qty_on_hand": new_on_hand, "qty_reserved": new_reserved},
        )
        await _insert_inventory_transaction(
            db,
            product_id=item["product_id"],
            store_id=order["store_id"],
            order_id=order_id,
            order_item_id=item["item_id"],
            transaction_type="SALE",
            quantity_delta=-qty,
            qty_on_hand_after=new_on_hand,
            qty_reserved_after=new_reserved,
            reason="Payment captured",
        )

    await db.execute(
        text(
            """
            UPDATE ekart_prod.orders
            SET status='COMPLETED', payment_status='CAPTURED',
                payment_ref=:payment_ref, paid_at=now(), completed_at=now()
            WHERE order_id=:order_id
            """
        ),
        {"order_id": order_id, "payment_ref": payload.payment_ref},
    )
    await write_audit_log(
        db,
        event_type="ORDER_COMPLETED",
        entity_type="order",
        entity_id=order_id,
        brand_id=order["brand_id"],
        store_id=order["store_id"],
        actor_type="webhook",
        payload=payload.model_dump(),
    )
    return ok({"payment_status": "CAPTURED"})


@router.get("/cart/{order_id}")
async def get_enterprise_order(order_id: UUID, _: DevicePrincipal = Depends(require_device), db: AsyncSession = Depends(get_db)):
    """Return full order metadata; nested expansion can be added by the service layer.

    Lives at `/cart/{order_id}` for the same reason `create_enterprise_order`
    lives at `/cart` - see that docstring. A bare `GET /{order_id}` here
    would otherwise shadow `orders.py`'s `GET /api/v1/orders/{order_id}`.
    """
    order = await _load_order_context(db, order_id)
    return ok(dict(order))


@router.get("/{order_id}/invoice")
async def get_invoice(order_id: UUID, _: DevicePrincipal = Depends(require_device), db: AsyncSession = Depends(get_db)):
    """Return invoice delivery metadata for an order."""
    order = await _load_order_context(db, order_id)
    return ok(
        {
            "invoice_number": order["invoice_number"],
            "invoice_pdf_url": order["invoice_pdf_url"],
            "sent_at": order["invoice_sent_at"],
            "whatsapp_status": None,
        }
    )


@router.post("/{order_id}/resend-invoice")
async def resend_invoice(order_id: UUID, _: DevicePrincipal = Depends(require_device)):
    """Queue WhatsApp invoice resend."""
    return ok({"queued": True, "order_id": str(order_id)})
