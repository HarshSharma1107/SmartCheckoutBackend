from decimal import Decimal, ROUND_HALF_UP


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_line_total(
    unit_price: Decimal,
    quantity: int,
    cgst_rate: Decimal,
    sgst_rate: Decimal,
    discount_amount: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    base = unit_price * quantity
    taxable = max(Decimal("0"), base - discount_amount)
    cgst_amount = money(taxable * cgst_rate / Decimal("100"))
    sgst_amount = money(taxable * sgst_rate / Decimal("100"))
    return {
        "base": money(base),
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "line_total": money(taxable + cgst_amount + sgst_amount),
    }


def calculate_order_delta(
    *,
    old_quantity: int,
    new_quantity: int,
    unit_price: Decimal,
    cgst_rate: Decimal,
    sgst_rate: Decimal,
    discount_amount: Decimal = Decimal("0"),
) -> dict[str, Decimal | int]:
    old_totals = calculate_line_total(unit_price, old_quantity, cgst_rate, sgst_rate, discount_amount)
    new_totals = calculate_line_total(unit_price, new_quantity, cgst_rate, sgst_rate, discount_amount)
    return {
        "quantity_delta": new_quantity - old_quantity,
        "base_delta": money(new_totals["base"] - old_totals["base"]),
        "cgst_delta": money(new_totals["cgst_amount"] - old_totals["cgst_amount"]),
        "sgst_delta": money(new_totals["sgst_amount"] - old_totals["sgst_amount"]),
        "line_delta": money(new_totals["line_total"] - old_totals["line_total"]),
        "new_base": new_totals["base"],
        "new_cgst_amount": new_totals["cgst_amount"],
        "new_sgst_amount": new_totals["sgst_amount"],
        "new_line_total": new_totals["line_total"],
    }


def calculate_release_delta(
    *,
    quantity: int,
    unit_price: Decimal,
    cgst_rate: Decimal,
    sgst_rate: Decimal,
    discount_amount: Decimal = Decimal("0"),
) -> dict[str, Decimal | int]:
    totals = calculate_line_total(unit_price, quantity, cgst_rate, sgst_rate, discount_amount)
    return {
        "quantity_delta": -quantity,
        "base_delta": -totals["base"],
        "cgst_delta": -totals["cgst_amount"],
        "sgst_delta": -totals["sgst_amount"],
        "line_delta": -totals["line_total"],
    }
