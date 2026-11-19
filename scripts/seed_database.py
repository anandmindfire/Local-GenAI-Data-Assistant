"""Database seeding script populating realistic business tables."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import db_context, init_tables
from app.infrastructure.database.models.business import (
    Customer,
    Order,
    OrderItem,
    Product,
    Refund,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_data(session: AsyncSession) -> None:
    """Insert seed data into business tables if not already populated."""
    # Check if customers already exist
    check_stmt = select(Customer).limit(1)
    res = await session.execute(check_stmt)
    if res.scalar_one_or_none():
        logger.info("Database already contains customer data. Skipping seed.")
        return

    now = datetime.now(UTC)

    # 1. Customers
    customers = [
        Customer(
            customer_id=1,
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@example.com",
            phone="+1-555-0101",
            city="New York",
            country="USA",
        ),
        Customer(
            customer_id=2,
            first_name="Bob",
            last_name="Jones",
            email="bob.jones@example.com",
            phone="+1-555-0102",
            city="San Francisco",
            country="USA",
        ),
        Customer(
            customer_id=3,
            first_name="Charlie",
            last_name="Brown",
            email="charlie.brown@example.com",
            phone="+1-555-0103",
            city="Chicago",
            country="USA",
        ),
        Customer(
            customer_id=4,
            first_name="Diana",
            last_name="Prince",
            email="diana.prince@example.com",
            phone="+1-555-0104",
            city="Austin",
            country="USA",
        ),
        Customer(
            customer_id=5,
            first_name="Evan",
            last_name="Wright",
            email="evan.wright@example.com",
            phone="+1-555-0105",
            city="Seattle",
            country="USA",
        ),
        Customer(
            customer_id=6,
            first_name="Fiona",
            last_name="Gallagher",
            email="fiona.g@example.com",
            phone="+1-555-0106",
            city="Boston",
            country="USA",
        ),
        Customer(
            customer_id=7,
            first_name="George",
            last_name="Clark",
            email="george.clark@example.com",
            phone="+1-555-0107",
            city="Denver",
            country="USA",
        ),
    ]
    session.add_all(customers)
    await session.flush()

    # 2. Products
    products = [
        Product(
            product_id=1,
            sku="PROD-LAPTOP-01",
            name="Pro Laptop 15-inch",
            category="Electronics",
            price=1299.99,
            stock_quantity=25,
            description="High performance laptop with 32GB RAM",
        ),
        Product(
            product_id=2,
            sku="PROD-PHONE-01",
            name="Smartphone Pro Max",
            category="Electronics",
            price=999.00,
            stock_quantity=8,
            description="Flagship smartphone with OLED display (Low Stock)",
        ),
        Product(
            product_id=3,
            sku="PROD-HEADPHONE-01",
            name="Wireless Noise Canceling Headphones",
            category="Audio",
            price=199.50,
            stock_quantity=45,
            description="Premium over-ear wireless headphones",
        ),
        Product(
            product_id=4,
            sku="PROD-MONITOR-01",
            name="4K Ultra-Wide Monitor 34-inch",
            category="Displays",
            price=649.00,
            stock_quantity=5,
            description="Curved 4K productivity monitor (Low Stock)",
        ),
        Product(
            product_id=5,
            sku="PROD-KEYBOARD-01",
            name="Mechanical Wireless Keyboard",
            category="Accessories",
            price=129.00,
            stock_quantity=50,
            description="Compact wireless mechanical keyboard",
        ),
        Product(
            product_id=6,
            sku="PROD-MOUSE-01",
            name="Ergonomic Precision Mouse",
            category="Accessories",
            price=79.99,
            stock_quantity=4,
            description="Ergonomic mouse with multi-device pairing (Low Stock)",
        ),
        Product(
            product_id=7,
            sku="PROD-STAND-01",
            name="Aluminum Laptop Stand",
            category="Accessories",
            price=49.99,
            stock_quantity=100,
            description="Adjustable ergonomic aluminum laptop stand",
        ),
    ]
    session.add_all(products)
    await session.flush()

    # 3. Orders
    orders = [
        Order(
            order_id=1,
            customer_id=1,
            order_date=now - timedelta(days=45),
            status="completed",
            total_amount=2599.98,
        ),
        Order(
            order_id=2,
            customer_id=2,
            order_date=now - timedelta(days=20),
            status="completed",
            total_amount=1998.00,
        ),
        Order(
            order_id=3,
            customer_id=3,
            order_date=now - timedelta(days=15),
            status="completed",
            total_amount=1299.99,
        ),
        Order(
            order_id=4,
            customer_id=4,
            order_date=now - timedelta(days=10),
            status="completed",
            total_amount=649.00,
        ),
        Order(
            order_id=5,
            customer_id=5,
            order_date=now - timedelta(days=5),
            status="completed",
            total_amount=328.50,
        ),
        Order(
            order_id=6,
            customer_id=1,
            order_date=now - timedelta(days=3),
            status="completed",
            total_amount=1499.49,
        ),
        Order(
            order_id=7,
            customer_id=6,
            order_date=now - timedelta(days=2),
            status="cancelled",
            total_amount=999.00,
        ),
        Order(
            order_id=8,
            customer_id=2,
            order_date=now - timedelta(days=25),
            status="refunded",
            total_amount=1299.99,
        ),
        Order(
            order_id=9,
            customer_id=7,
            order_date=now - timedelta(days=12),
            status="completed",
            total_amount=399.00,
        ),
    ]
    session.add_all(orders)
    await session.flush()

    # 4. Order Items
    order_items = [
        OrderItem(
            item_id=1, order_id=1, product_id=1, quantity=2, unit_price=1299.99, subtotal=2599.98
        ),
        OrderItem(
            item_id=2, order_id=2, product_id=2, quantity=2, unit_price=999.00, subtotal=1998.00
        ),
        OrderItem(
            item_id=3, order_id=3, product_id=1, quantity=1, unit_price=1299.99, subtotal=1299.99
        ),
        OrderItem(
            item_id=4, order_id=4, product_id=4, quantity=1, unit_price=649.00, subtotal=649.00
        ),
        OrderItem(
            item_id=5, order_id=5, product_id=3, quantity=1, unit_price=199.50, subtotal=199.50
        ),
        OrderItem(
            item_id=6, order_id=5, product_id=5, quantity=1, unit_price=129.00, subtotal=129.00
        ),
        OrderItem(
            item_id=7, order_id=6, product_id=1, quantity=1, unit_price=1299.99, subtotal=1299.99
        ),
        OrderItem(
            item_id=8, order_id=6, product_id=3, quantity=1, unit_price=199.50, subtotal=199.50
        ),
        OrderItem(
            item_id=9, order_id=7, product_id=2, quantity=1, unit_price=999.00, subtotal=999.00
        ),
        OrderItem(
            item_id=10, order_id=8, product_id=1, quantity=1, unit_price=1299.99, subtotal=1299.99
        ),
        OrderItem(
            item_id=11, order_id=9, product_id=3, quantity=2, unit_price=199.50, subtotal=399.00
        ),
    ]
    session.add_all(order_items)
    await session.flush()

    # 5. Refunds
    refunds = [
        Refund(
            refund_id=1,
            order_id=8,
            refund_amount=1299.99,
            refund_date=now - timedelta(days=20),
            reason="Customer changed mind within 30-day window",
            status="processed",
        ),
        Refund(
            refund_id=2,
            order_id=5,
            refund_amount=50.00,
            refund_date=now - timedelta(days=2),
            reason="Price match guarantee adjustment",
            status="processed",
        ),
    ]
    session.add_all(refunds)
    await session.flush()

    logger.info("Database successfully seeded with realistic business data.")


async def main() -> None:
    """CLI entrypoint for seeding database."""
    logger.info("Initializing database schema...")
    await init_tables()
    async with db_context() as session:
        await seed_data(session)
    logger.info("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
