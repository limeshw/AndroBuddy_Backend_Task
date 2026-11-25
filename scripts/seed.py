"""
ShopSphere Database Seeding Script
Seeds:
1. One Admin user (credentials from .env)
2. One Sample Customer user
3. 12 Stand-in Products across varied categories
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.user import User
from app.models.product import Product
from app.core.config import settings
from app.core.security import hash_password


SAMPLE_PRODUCTS = [
    {"name": "Wireless Noise-Canceling Headphones", "price": 149.99, "stock_quantity": 25, "is_active": True},
    {"name": "Mechanical Gaming Keyboard RGB", "price": 89.50, "stock_quantity": 18, "is_active": True},
    {"name": "Ultra-Wide Gaming Monitor 34-inch", "price": 399.00, "stock_quantity": 8, "is_active": True},
    {"name": "Ergonomic Office Chair", "price": 199.99, "stock_quantity": 12, "is_active": True},
    {"name": "Stainless Steel Thermal Coffee Mug", "price": 24.95, "stock_quantity": 50, "is_active": True},
    {"name": "USB-C Multiport Docking Station", "price": 59.99, "stock_quantity": 30, "is_active": True},
    {"name": "Smartphone Wireless Fast Charger", "price": 29.99, "stock_quantity": 40, "is_active": True},
    {"name": "Leather Laptop Backpack 15.6-inch", "price": 79.00, "stock_quantity": 15, "is_active": True},
    {"name": "Bluetooth Portable Speaker Waterproof", "price": 45.00, "stock_quantity": 35, "is_active": True},
    {"name": "Smart Fitness Tracker Band", "price": 49.99, "stock_quantity": 20, "is_active": True},
    {"name": "4K Webcam with Privacy Shutter", "price": 69.50, "stock_quantity": 22, "is_active": True},
    {"name": "Discontinued Legacy Gadget", "price": 15.00, "stock_quantity": 0, "is_active": False},
]


def seed_database():
    print("--- ShopSphere Seeding Started ---")
    # 1. Ensure all tables are created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Seed Admin User
        admin_email = settings.ADMIN_EMAIL.lower()
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                full_name=settings.ADMIN_FULL_NAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            print(f"[+] Admin created: {admin_email} (role: admin)")
        else:
            print(f"[*] Admin already exists: {admin_email}")

        # 3. Seed Sample Customer
        sample_customer_email = "customer@shopsphere.com"
        customer = db.query(User).filter(User.email == sample_customer_email).first()
        if not customer:
            customer = User(
                email=sample_customer_email,
                full_name="John Doe",
                password_hash=hash_password("Customer123!"),
                role="customer",
            )
            db.add(customer)
            print(f"[+] Sample customer created: {sample_customer_email} (role: customer)")
        else:
            print(f"[*] Customer already exists: {sample_customer_email}")

        # 4. Seed Products
        products_added = 0
        for p_data in SAMPLE_PRODUCTS:
            existing = db.query(Product).filter(Product.name == p_data["name"]).first()
            if not existing:
                product = Product(
                    name=p_data["name"],
                    price=p_data["price"],
                    stock_quantity=p_data["stock_quantity"],
                    is_active=p_data["is_active"],
                )
                db.add(product)
                products_added += 1

        db.commit()
        print(f"[+] Seeded {products_added} new products (Total catalog size: {db.query(Product).count()})")
        print("--- ShopSphere Seeding Completed Successfully ---")

    except Exception as e:
        db.rollback()
        print(f"[!] Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

