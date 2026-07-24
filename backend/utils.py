import uuid
from datetime import datetime
from .schemas import OrderResponse, OrderItemResponse
from .models import Order, OrderItem

def generate_order_number() -> str:
    now = datetime.utcnow()
    short_uuid = str(uuid.uuid4()).replace("-", "")[:6].upper()
    return f"ORD-{now.strftime('%Y%m%d')}-{short_uuid}"

def format_order(order: Order) -> OrderResponse:
    return OrderResponse(
        order_id=str(order.order_id),
        order_number=order.order_number,
        customer_name=order.customer.name if order.customer else "",
        customer_phone=order.customer.phone if order.customer else "",
        customer_email=order.customer.email if order.customer else "",
        status=order.status,
        subtotal=float(order.subtotal),
        discount_total=float(order.discount_total),
        cgst_total=float(order.cgst_total),
        sgst_total=float(order.sgst_total),
        grand_total=float(order.grand_total),
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        ordered_at=order.ordered_at.isoformat(),
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
        items=[
            OrderItemResponse(
                item_id=str(item.item_id),
                product_id=str(item.product_id),
                product_name=item.product.name if item.product else "",
                sku=item.product.sku if item.product else "",
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                mrp=float(item.mrp),
                discount_amount=float(item.discount_amount),
                cgst_amount=float(item.cgst_amount),
                sgst_amount=float(item.sgst_amount),
                line_total=float(item.line_total),
            )
            for item in order.items
        ],
    )