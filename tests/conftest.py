import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.models.product import Product
from app.core.security import hash_password, create_access_token

# Use isolated in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_product(db_session) -> Product:
    product = Product(
        name="Test Wireless Mouse",
        price=25.00,
        stock_quantity=5,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def customer_a(db_session) -> User:
    user = User(
        email="customer.a@test.com",
        full_name="Customer Alice",
        password_hash=hash_password("Password123!"),
        role="customer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_b(db_session) -> User:
    user = User(
        email="customer.b@test.com",
        full_name="Customer Bob",
        password_hash=hash_password("Password123!"),
        role="customer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    admin = User(
        email="admin@test.com",
        full_name="Admin User",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_headers_customer_a(customer_a) -> dict:
    token = create_access_token(data={"sub": str(customer_a.id), "role": customer_a.role, "email": customer_a.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_customer_b(customer_b) -> dict:
    token = create_access_token(data={"sub": str(customer_b.id), "role": customer_b.role, "email": customer_b.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(admin_user) -> dict:
    token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role, "email": admin_user.email})
    return {"Authorization": f"Bearer {token}"}

