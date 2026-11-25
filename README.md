# ShopSphere — Customer, Cart & Orders API (BE-2)

Backend service for the **ShopSphere** e-commerce platform managing customer accounts, authentication, shopping carts, and order processing with strict stock-checking and atomic database transactions.

---

## 1. Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **ORM / Database:** SQLAlchemy 2.0 with SQLite (zero-config, PostgreSQL-ready)
- **Validation:** Pydantic v2 & `pydantic-settings`
- **Security:** JWT (`python-jose`) + `passlib[bcrypt]`
- **Testing:** `pytest` + `httpx` (FastAPI `TestClient`)
- **Package & Environment Manager:** Astral `uv`

---

## 2. Project Architecture & Folder Layout

```text
AndroBuddy_Backend_Task/
├── .env.example              # Environment variable template
├── .env                      # Local configuration secrets (git-ignored)
├── requirements.txt          # Frozen dependency specifications
├── README.md                 # Setup, credentials, and API docs
│
├── app/
│   ├── main.py               # FastAPI application factory, CORS, router mounts
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings configuration
│   │   ├── security.py       # Password hashing & JWT token encoding/decoding
│   │   └── dependencies.py   # Reusable auth & order ownership guards
│   ├── db/
│   │   ├── base.py           # DeclarativeBase with common mixins
│   │   └── session.py        # SQLAlchemy engine and session generator (get_db)
│   ├── models/
│   │   ├── user.py           # User model (roles: customer, admin)
│   │   ├── product.py        # Stand-in catalog product model
│   │   ├── cart.py           # Cart & CartItem models
│   │   └── order.py          # Order & OrderItem models (price snapshots & status state machine)
│   ├── schemas/
│   │   ├── auth.py           # User registration, login, and response schemas
│   │   ├── product.py        # Product response schema
│   │   ├── cart.py           # Cart addition, update, and response schemas
│   │   └── order.py          # Order creation, status updates, and responses
│   ├── services/
│   │   ├── auth_service.py   # Authentication and user registration business logic
│   │   ├── cart_service.py   # Cart operations, quantity addition, and stock checks
│   │   └── order_service.py  # Atomic checkout transaction, status transitions, stock restore
│   └── routers/
│       ├── auth.py           # /auth endpoints
│       ├── cart.py           # /cart endpoints
│       ├── orders.py         # /orders endpoints
│       └── products.py       # /products stand-in catalog exploration
│
├── scripts/
│   └── seed.py               # Database seed script (admin, sample customer, 12 products)
│
└── tests/
    ├── conftest.py           # Test fixtures with isolated in-memory SQLite database
    ├── test_auth.py          # Auth tests (register, 409 duplicate, login JWT, /auth/me)
    ├── test_cart.py          # Cart tests (409 over stock, additive quantity, totals)
    └── test_orders.py        # Order tests (stock reduction, 404 ownership, cancel stock restore, state machine)
```

---

## 3. Getting Started

### Prerequisites
- Python 3.12+ installed
- [Astral `uv`](https://docs.astral.sh/uv/) installed (or standard `python -m venv`)

### Installation & Environment Setup

```powershell
# 1. Create a virtual environment using Python 3.12 via uv
uv venv --python 3.12 .venv

# 2. Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\activate
# On Linux / macOS:
# source .venv/bin/activate

# 3. Install project dependencies
uv pip install -r requirements.txt
```

### Environment Variables
Copy `.env.example` to `.env` (already done by default):
```powershell
copy .env.example .env
```

---

## 4. Database Seeding

Run the seed script to initialize tables and populate sample data:
```powershell
python scripts/seed.py
```

This creates:
1. **Admin account** (from `.env` credentials)
2. **Sample Customer account**
3. **12 Stand-in products** with varying stock levels and pricing

### Test Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@shopsphere.com` | `` |
| **Customer** | `customer@shopsphere.com` | `` |

---

## 5. Running the Application

Start the development server with Uvicorn:
```powershell
uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Docs:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running the Automated Test Suite

All tests run against an **isolated in-memory SQLite database** using `pytest` and FastAPI's `TestClient`:

```powershell
pytest -v
```

### Covered Test Scenarios:
1. **`test_register_and_login_success`**: Customer registration, duplicate email check (409), JWT login, and `/auth/me` security validation (password hash is never leaked).
2. **`test_register_password_too_short`**: Validates password requirement ($\ge 8$ characters).
3. **`test_add_to_cart_over_stock_fails`**: Attempting to add quantity greater than available stock returns 409 with a clear message.
4. **`test_cart_operations_and_calculations`**: Verifies additive quantity logic, line item total calculations, and overall cart total.
5. **`test_checkout_reduces_stock_and_clears_cart`**: Verifies atomic transaction: inventory stock is deducted, snapshots copied into order items, and cart is emptied.
6. **`test_customer_cannot_read_another_customers_order`**: Reusable ownership guard returns **404** when Customer B tries to read Customer A's order.
7. **`test_cancel_order_restores_stock`**: Customer cancelling a pending order successfully restores the inventory stock.
8. **`test_admin_order_status_transitions`**: Validates status flow (`pending` $\rightarrow$ `paid` $\rightarrow$ `shipped` $\rightarrow$ `delivered`), forbids customer status modification (403), and returns 409 on invalid transitions.

---

## 7. Key Business Logic & Design Decisions

### 1. Atomic Order Checkout Transaction
In `app/services/order_service.py`, `checkout()` executes stock verification, inventory decrement, order creation with immutable product name/price snapshots, and cart clearing inside a single database transaction block:
```python
try:
    # 1. Re-check stock for all cart items (409 if any item is short)
    # 2. Deduct product.stock_quantity -= item.quantity
    # 3. Create Order and OrderItems (with price & name snapshot)
    # 4. Clear Cart
    db.commit()
except Exception:
    db.rollback()
    raise
```

### 2. Order Status State Machine
Orders transition strictly according to the assignment requirements:
- `pending` $\rightarrow$ `paid` $\rightarrow$ `shipped` $\rightarrow$ `delivered`
- `pending` or `paid` $\rightarrow$ `cancelled`
- Any other transition returns **409 Conflict**.
- Cancelling an order (via `POST /orders/{id}/cancel` by customer or `PATCH /orders/{id}/status` by admin) automatically restores product inventory stock.

### 3. Reusable Ownership Verification
Ownership validation is centralized in `app/core/dependencies.py` via `check_order_ownership()`. When a customer accesses an order ID belonging to another user, a **404 Not Found** is raised to prevent unauthorized ID enumeration.

