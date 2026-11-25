def test_add_to_cart_over_stock_fails(client, auth_headers_customer_a, sample_product):
    """Test 2: Adding quantity exceeding available stock returns 409 with clear message."""
    # sample_product has stock_quantity = 5
    payload = {
        "product_id": sample_product.id,
        "quantity": 10,  # Exceeds available 5
    }
    response = client.post("/cart/items", json=payload, headers=auth_headers_customer_a)
    assert response.status_code == 409
    data = response.json()
    assert "exceeds available stock" in data["detail"].lower()


def test_cart_operations_and_calculations(client, auth_headers_customer_a, sample_product):
    """Test cart additive quantity, line totals, and cart total calculations."""
    # 1. Add valid quantity
    add_payload = {"product_id": sample_product.id, "quantity": 2}
    resp1 = client.post("/cart/items", json=add_payload, headers=auth_headers_customer_a)
    assert resp1.status_code == 200
    cart_data = resp1.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["quantity"] == 2
    assert cart_data["items"][0]["unit_price"] == 25.0
    assert cart_data["items"][0]["line_total"] == 50.0
    assert cart_data["total_amount"] == 50.0

    # 2. Add product again (additive quantity check)
    add_more_payload = {"product_id": sample_product.id, "quantity": 1}
    resp2 = client.post("/cart/items", json=add_more_payload, headers=auth_headers_customer_a)
    assert resp2.status_code == 200
    updated_cart = resp2.json()
    assert updated_cart["items"][0]["quantity"] == 3
    assert updated_cart["total_amount"] == 75.0

    # 3. Exceed remaining stock with additive addition (3 + 3 = 6 > 5)
    resp3 = client.post("/cart/items", json={"product_id": sample_product.id, "quantity": 3}, headers=auth_headers_customer_a)
    assert resp3.status_code == 409

    # 4. Empty cart
    resp_empty = client.delete("/cart", headers=auth_headers_customer_a)
    assert resp_empty.status_code == 200
    get_cart_resp = client.get("/cart", headers=auth_headers_customer_a)
    assert len(get_cart_resp.json()["items"]) == 0
    assert get_cart_resp.json()["total_amount"] == 0.0

