def test_checkout_reduces_stock_and_clears_cart(client, auth_headers_customer_a, sample_product, db_session):
    """Test 3: Successful checkout reduces inventory stock and clears customer's cart."""
    initial_stock = sample_product.stock_quantity  # 5

    # 1. Add 3 items to cart
    client.post("/cart/items", json={"product_id": sample_product.id, "quantity": 3}, headers=auth_headers_customer_a)

    # 2. Checkout
    order_payload = {"shipping_address": "123 Main Street, Suite 400, Tech City"}
    order_resp = client.post("/orders", json=order_payload, headers=auth_headers_customer_a)
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert order_data["status"] == "pending"
    assert order_data["total_amount"] == 75.00
    assert len(order_data["items"]) == 1
    assert order_data["items"][0]["product_name"] == "Test Wireless Mouse"
    assert order_data["items"][0]["unit_price"] == 25.00
    assert order_data["items"][0]["quantity"] == 3

    # 3. Verify stock was reduced in DB (5 - 3 = 2)
    db_session.refresh(sample_product)
    assert sample_product.stock_quantity == initial_stock - 3

    # 4. Verify cart is now empty
    cart_resp = client.get("/cart", headers=auth_headers_customer_a)
    assert len(cart_resp.json()["items"]) == 0
    assert cart_resp.json()["total_amount"] == 0.0


def test_customer_cannot_read_another_customers_order(client, auth_headers_customer_a, auth_headers_customer_b, sample_product):
    """Test 4: Customer B cannot read Customer A's order, returns 404."""
    # Customer A adds item and creates order
    client.post("/cart/items", json={"product_id": sample_product.id, "quantity": 1}, headers=auth_headers_customer_a)
    order_resp = client.post("/orders", json={"shipping_address": "Customer A Address, NY"}, headers=auth_headers_customer_a)
    order_id = order_resp.json()["id"]

    # Customer A can read their order
    own_order = client.get(f"/orders/{order_id}", headers=auth_headers_customer_a)
    assert own_order.status_code == 200

    # Customer B attempts to read Customer A's order -> 404 Not Found
    other_order = client.get(f"/orders/{order_id}", headers=auth_headers_customer_b)
    assert other_order.status_code == 404


def test_cancel_order_restores_stock(client, auth_headers_customer_a, sample_product, db_session):
    """Test 5: Cancelling an order restores the inventory stock."""
    initial_stock = sample_product.stock_quantity  # 5

    # 1. Customer creates order with 2 items
    client.post("/cart/items", json={"product_id": sample_product.id, "quantity": 2}, headers=auth_headers_customer_a)
    order_resp = client.post("/orders", json={"shipping_address": "456 Market St, San Francisco"}, headers=auth_headers_customer_a)
    order_id = order_resp.json()["id"]

    # Stock is now 3
    db_session.refresh(sample_product)
    assert sample_product.stock_quantity == initial_stock - 2

    # 2. Customer cancels order while pending
    cancel_resp = client.post(f"/orders/{order_id}/cancel", headers=auth_headers_customer_a)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 3. Stock is restored back to 5
    db_session.refresh(sample_product)
    assert sample_product.stock_quantity == initial_stock

    # 4. Cancelling again returns 409
    second_cancel = client.post(f"/orders/{order_id}/cancel", headers=auth_headers_customer_a)
    assert second_cancel.status_code == 409


def test_admin_order_status_transitions(client, auth_headers_customer_a, auth_headers_admin, sample_product):
    """Test order state machine: pending -> paid -> shipped -> delivered and 409 on invalid transition."""
    # 1. Create order
    client.post("/cart/items", json={"product_id": sample_product.id, "quantity": 1}, headers=auth_headers_customer_a)
    order_resp = client.post("/orders", json={"shipping_address": "789 Pine Ave"}, headers=auth_headers_customer_a)
    order_id = order_resp.json()["id"]

    # 2. Customer cannot update status (requires admin)
    forbidden_resp = client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=auth_headers_customer_a)
    assert forbidden_resp.status_code == 403

    # 3. Admin advances pending -> paid
    resp_paid = client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=auth_headers_admin)
    assert resp_paid.status_code == 200
    assert resp_paid.json()["status"] == "paid"

    # 4. Admin advances paid -> shipped
    resp_shipped = client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=auth_headers_admin)
    assert resp_shipped.status_code == 200
    assert resp_shipped.json()["status"] == "shipped"

    # 5. Invalid transition: shipped -> pending returns 409
    invalid_resp = client.patch(f"/orders/{order_id}/status", json={"status": "pending"}, headers=auth_headers_admin)
    assert invalid_resp.status_code == 409

    # 6. Admin advances shipped -> delivered
    resp_delivered = client.patch(f"/orders/{order_id}/status", json={"status": "delivered"}, headers=auth_headers_admin)
    assert resp_delivered.status_code == 200
    assert resp_delivered.json()["status"] == "delivered"

