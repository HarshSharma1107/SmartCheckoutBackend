import uuid
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, Inventory, Order, OrderItem, Store
from ..schemas import OrderCreateRequest, OrderResponse, PaymentRequest
from ..utils import generate_order_number, format_order

router = APIRouter(prefix="/api/v1", tags=["orders"])

@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(payload: OrderCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        store_uuid = uuid.UUID(payload.store_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid store_id")

    store_result = await db.execute(select(Store).where(Store.store_id == store_uuid))
    if not store_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Store not found")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    order_items_data = []
    subtotal = Decimal("0")
    cgst_total = Decimal("0")
    sgst_total = Decimal("0")

    for cart_item in payload.items:
        try:
            pid = uuid.UUID(cart_item.product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product_id: {cart_item.product_id}")

        prod_result = await db.execute(select(Product).where(Product.product_id == pid, Product.is_active == True))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {cart_item.product_id} not found or inactive")

        inv_result = await db.execute(
            select(Inventory).where(Inventory.product_id == pid, Inventory.store_id == store_uuid)
        )
        inventory = inv_result.scalar_one_or_none()
        available = inventory.qty_available if inventory else 0
        if available < cart_item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for '{product.name}'. Available: {available}, Requested: {cart_item.quantity}"
            )

        unit_price = product.mrp
        line_base = unit_price * cart_item.quantity
        cgst_amount = (line_base * product.cgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        sgst_amount = (line_base * product.sgst_rate / Decimal("100")).quantize(Decimal("0.01"))
        line_total = (line_base + cgst_amount + sgst_amount).quantize(Decimal("0.01"))

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

    grand_total = (subtotal + cgst_total + sgst_total).quantize(Decimal("0.01"))

    order = Order(
        order_number=generate_order_number(),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        store_id=store_uuid,
        status="COMPLETED",
        subtotal=subtotal.quantize(Decimal("0.01")),
        discount_total=Decimal("0"),
        cgst_total=cgst_total.quantize(Decimal("0.01")),
        sgst_total=sgst_total.quantize(Decimal("0.01")),
        grand_total=grand_total,
        payment_method=payload.payment_method,
        payment_status="PAID",
        completed_at=datetime.utcnow(),
    )
    db.add(order)
    await db.flush()

    for item_data in order_items_data:
        product = item_data["product"]
        oi = OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            mrp=product.mrp,
            discount_amount=Decimal("0"),
            cgst_rate=item_data["cgst_rate"],
            cgst_amount=item_data["cgst_amount"],
            sgst_rate=item_data["sgst_rate"],
            sgst_amount=item_data["sgst_amount"],
            line_total=item_data["line_total"],
        )
        db.add(oi)

        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == product.product_id,
                Inventory.store_id == store_uuid
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv:
            inv.qty_on_hand = max(0, inv.qty_on_hand - item_data["quantity"])

    await db.flush()

    order_result = await db.execute(select(Order).where(Order.order_id == order.order_id))
    fresh_order = order_result.scalar_one()
    items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.order_id))
    fresh_order.items = list(items_result.scalars().all())

    for item in fresh_order.items:
        prod_res = await db.execute(select(Product).where(Product.product_id == item.product_id))
        item.product = prod_res.scalar_one_or_none()

    return format_order(fresh_order)

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order_id")

    result = await db.execute(select(Order).where(Order.order_id == oid))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == oid))
    order.items = list(items_result.scalars().all())
    for item in order.items:
        prod_res = await db.execute(select(Product).where(Product.product_id == item.product_id))
        item.product = prod_res.scalar_one_or_none()

    return format_order(order)