from decimal import Decimal

from backend.services.pricing import calculate_line_total, calculate_order_delta, calculate_release_delta


def test_calculate_line_total_with_cgst_and_sgst():
    result = calculate_line_total(
        unit_price=Decimal("100.00"),
        quantity=2,
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00"),
    )

    assert result["base"] == Decimal("200.00")
    assert result["cgst_amount"] == Decimal("18.00")
    assert result["sgst_amount"] == Decimal("18.00")
    assert result["line_total"] == Decimal("236.00")


def test_calculate_order_delta_for_quantity_increase():
    result = calculate_order_delta(
        old_quantity=1,
        new_quantity=3,
        unit_price=Decimal("50.00"),
        cgst_rate=Decimal("2.50"),
        sgst_rate=Decimal("2.50"),
    )

    assert result["quantity_delta"] == 2
    assert result["base_delta"] == Decimal("100.00")
    assert result["cgst_delta"] == Decimal("2.50")
    assert result["sgst_delta"] == Decimal("2.50")
    assert result["line_delta"] == Decimal("105.00")


def test_calculate_release_delta_for_delete():
    result = calculate_release_delta(
        quantity=2,
        unit_price=Decimal("25.00"),
        cgst_rate=Decimal("6.00"),
        sgst_rate=Decimal("6.00"),
    )

    assert result["quantity_delta"] == -2
    assert result["base_delta"] == Decimal("-50.00")
    assert result["cgst_delta"] == Decimal("-3.00")
    assert result["sgst_delta"] == Decimal("-3.00")
    assert result["line_delta"] == Decimal("-56.00")
