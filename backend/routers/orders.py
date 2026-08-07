import logging
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import DevicePrincipal, require_device
from ..database import get_db
from ..errors import ErrorCode
from ..models import Product, Inventory, Order, OrderItem
from ..schemas import OrderCreateRequest, OrderResponse, PaymentRequest
from ..services.email import send_receipt_email
from ..services.terminal import get_active_assignment
from ..utils import generate_order_number, format_order
from ..models import customers as Customer

router = APIRouter(prefix="/api/v1", tags=["orders"])
logger = logging.getLogger(__name__)


def _mask_phone(phone: str) -> str:
    return f"***{phone[-2:]}" if len(phone) >= 2 else "***"


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: OrderCreateRequest,
    background_tasks: BackgroundTasks,
    principal: DevicePrincipal = Depends(require_device),
    db: AsyncSession = Depends(get_db)
):
    order_number = generate_order_number()
    device_id = uuid.UUID(principal.device_id)
    logger.info(
        "checkout.start order_number=%s device_id=%s payment_method=%s item_count=%d product_ids=%s",
        order_number,
        device_id,
        payload.payment_method,
        len(payload.items),
        [i.product_id for i in payload.items],
    )

    try:
        # The authenticated device's own active terminal assignment is the
        # only source of truth for which store this order can act on -
        # `payload.store_id` is never trusted, only logged if it disagrees
        # (see below), so a tampered/stale client value can't move an order
        # onto a different store.
        assignment_row = await get_active_assignment(db, device_id)
        if assignment_row is None:
            raise HTTPException(
                status_code=403,
                detail={"code": ErrorCode.FORBIDDEN, "message": "Device is not assigned to a store"},
            )
        _assignment, terminal, store, _brand = assignment_row
        store_uuid = store.store_id

        if payload.store_id and payload.store_id != str(store_uuid):
            logger.warning(
                "checkout.store_id_mismatch order_number=%s device_id=%s device_store=%s payload_store=%r",
                order_number, device_id, store_uuid, payload.store_id,
            )

        if payload.idempotency_key:
            existing_result = await db.execute(
                select(Order)
                .options(selectinload(Order.customer), selectinload(Order.items).selectinload(OrderItem.product))
                .where(Order.device_id == device_id, Order.idempotency_key == payload.idempotency_key)
            )
            existing_order = existing_result.scalar_one_or_none()
            if existing_order is not None:
                logger.info(
                    "checkout.idempotent_replay order_number=%s existing_order_id=%s idempotency_key=%s",
                    order_number, existing_order.order_id, payload.idempotency_key,
                )
                return format_order(existing_order)

        if not payload.items:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.VALIDATION_ERROR, "message": "Order must have at least one item"},
            )

        logger.info("checkout.store_resolved order_number=%s store_id=%s", order_number, store_uuid)

        cust_result = await db.execute(
            select(Customer).where(
                Customer.phone == payload.customer_phone
            )
        )

        customer = cust_result.scalar_one_or_none()

        if not customer:
            customer = Customer(
                name=payload.customer_name,
                phone=payload.customer_phone,
                email=payload.customer_email,
                loyalty_points=0,
                tier="STANDARD",
                is_active=True,
            )

            db.add(customer)
            await db.flush()
            logger.info(
                "checkout.customer_created order_number=%s customer_id=%s phone=%s",
                order_number, customer.customer_id, _mask_phone(payload.customer_phone),
            )
        else:
            # `customer` can already exist with a NULL/blank `name` or
            # `email` here even though this ORM model marks both
            # non-nullable: the device-gated enterprise flow
            # (routers/enterprise_orders.py create_enterprise_order) creates
            # a customer row via raw SQL from phone alone (`INSERT INTO
            # ekart_prod.customers (brand_id, phone) ...`), and this legacy
            # endpoint used to only patch `email` on an existing match,
            # never `name`. A `None` then flows into OrderResponse.customer_name
            # (declared as plain `str`), and FastAPI's response_model
            # validation rejects it - which surfaces to the client as a bare
            # unhandled 500, not a normal 4xx, and *only* for customers who
            # were first seen through that other flow. Keep both fields in
            # sync from the payload on every order, not just email.
            customer.name = payload.customer_name
            customer.email = payload.customer_email
            logger.info(
                "checkout.customer_matched order_number=%s customer_id=%s phone=%s",
                order_number, customer.customer_id, _mask_phone(payload.customer_phone),
            )

        # ── Process items ──
        order_items_data = []

        subtotal = Decimal("0")
        cgst_total = Decimal("0")
        sgst_total = Decimal("0")

        for cart_item in payload.items:
            try:
                pid = uuid.UUID(cart_item.product_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"code": ErrorCode.VALIDATION_ERROR, "message": f"Invalid product_id: {cart_item.product_id}"},
                )

            prod_result = await db.execute(
                select(Product).where(
                    Product.product_id == pid,
                    Product.is_active == True
                )
            )

            product = prod_result.scalar_one_or_none()

            if not product:
                logger.warning("checkout.product_not_found order_number=%s product_id=%s", order_number, pid)
                raise HTTPException(
                    status_code=404,
                    detail={"code": ErrorCode.NOT_FOUND, "message": f"Product {cart_item.product_id} not found or inactive"},
                )

            # Lock the inventory row for the rest of this transaction so a
            # concurrent checkout for the same product/store can't read a
            # stale `qty_on_hand` between this check and the decrement below
            # - closes the race that let two simultaneous checkouts both
            # pass the availability check against the last unit in stock.
            inv_result = await db.execute(
                select(Inventory)
                .where(Inventory.product_id == pid, Inventory.store_id == store_uuid)
                .with_for_update()
            )

            inventory = inv_result.scalar_one_or_none()

            available = inventory.qty_available if inventory else 0

            if available < cart_item.quantity:
                logger.warning(
                    "checkout.insufficient_stock order_number=%s product_id=%s available=%d requested=%d",
                    order_number, pid, available, cart_item.quantity,
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": ErrorCode.INSUFFICIENT_STOCK,
                        "message": (
                            f"Insufficient stock for '{product.name}'. "
                            f"Available: {available}, "
                            f"Requested: {cart_item.quantity}"
                        ),
                    },
                )

            inventory.qty_on_hand = max(0, inventory.qty_on_hand - cart_item.quantity)

            unit_price = product.mrp

            line_base = unit_price * cart_item.quantity

            cgst_amount = (
                line_base * product.cgst_rate / Decimal("100")
            ).quantize(Decimal("0.01"))

            sgst_amount = (
                line_base * product.sgst_rate / Decimal("100")
            ).quantize(Decimal("0.01"))

            line_total = (
                line_base + cgst_amount + sgst_amount
            ).quantize(Decimal("0.01"))

            subtotal += line_base
            cgst_total += cgst_amount
            sgst_total += sgst_amount

            order_items_data.append({
                "product": product,
                "quantity": cart_item.quantity,
                "unit_price": unit_price,
                "cgst_rate": product.cgst_rate,
                "cgst_amount": cgst_amount,
                "sgst_rate": product.sgst_rate,
                "sgst_amount": sgst_amount,
                "line_total": line_total,
            })

        grand_total = (
            subtotal + cgst_total + sgst_total
        ).quantize(Decimal("0.01"))

        now = datetime.utcnow()

        order = Order(
            order_number=order_number,
            customer_id=customer.customer_id,
            store_id=store_uuid,
            device_id=device_id,
            terminal_id=terminal.terminal_code,
            idempotency_key=payload.idempotency_key,
            status="COMPLETED",
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount_total=Decimal("0"),
            cgst_total=cgst_total.quantize(Decimal("0.01")),
            sgst_total=sgst_total.quantize(Decimal("0.01")),
            grand_total=grand_total,
            payment_method=payload.payment_method,
            payment_status="PAID",
            ordered_at=now,
            completed_at=now,
            updated_at=now
        )

        db.add(order)

        await db.flush()
        logger.info(
            "checkout.order_created order_number=%s order_id=%s customer_id=%s grand_total=%s",
            order_number, order.order_id, customer.customer_id, grand_total,
        )

        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=item_data["product"].product_id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                mrp=item_data["product"].mrp,
                cgst_rate=item_data["cgst_rate"],
                cgst_amount=item_data["cgst_amount"],
                sgst_rate=item_data["sgst_rate"],
                sgst_amount=item_data["sgst_amount"],
                line_total=item_data["line_total"]
            )

            db.add(order_item)

        await db.flush()
        logger.info("checkout.items_and_inventory_persisted order_number=%s order_id=%s item_count=%d",
                    order_number, order.order_id, len(order_items_data))

        await db.commit()
        logger.info("checkout.committed order_number=%s order_id=%s payment_method=%s payment_status=PAID",
                    order_number, order.order_id, payload.payment_method)

        final_result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items)
                .selectinload(OrderItem.product)
            )
            .where(Order.order_id == order.order_id)
        )

        fresh_order = final_result.scalar_one()

        background_tasks.add_task(send_receipt_email, payload.customer_email, fresh_order)
        logger.info("checkout.receipt_email_queued order_number=%s order_id=%s to=%s",
                    order_number, order.order_id, _mask_email(payload.customer_email))

        response = format_order(fresh_order)
        logger.info("checkout.response_returned order_number=%s order_id=%s status=%s",
                    order_number, order.order_id, response.status)
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "checkout.unhandled_exception order_number=%s device_id=%s customer_phone=%s payment_method=%s item_count=%d",
            order_number, device_id, _mask_phone(payload.customer_phone), payload.payment_method, len(payload.items),
        )
        raise


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.VALIDATION_ERROR, "message": "Invalid order_id"},
        )

    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items)
            .selectinload(OrderItem.product)
        )
        .where(Order.order_id == oid)
    )

    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.NOT_FOUND, "message": "Order not found"},
        )

    return format_order(order)