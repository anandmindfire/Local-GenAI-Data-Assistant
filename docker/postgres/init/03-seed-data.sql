-- Auto-seed for PostgreSQL container
\c genai_db;

-- Customers
INSERT INTO customers (customer_id, first_name, last_name, email, phone, city, country) VALUES
(1, 'Alice', 'Smith', 'alice.smith@example.com', '+1-555-0101', 'New York', 'USA'),
(2, 'Bob', 'Jones', 'bob.jones@example.com', '+1-555-0102', 'San Francisco', 'USA'),
(3, 'Charlie', 'Brown', 'charlie.brown@example.com', '+1-555-0103', 'Chicago', 'USA'),
(4, 'Diana', 'Prince', 'diana.prince@example.com', '+1-555-0104', 'Austin', 'USA'),
(5, 'Evan', 'Wright', 'evan.wright@example.com', '+1-555-0105', 'Seattle', 'USA'),
(6, 'Fiona', 'Gallagher', 'fiona.g@example.com', '+1-555-0106', 'Boston', 'USA'),
(7, 'George', 'Clark', 'george.clark@example.com', '+1-555-0107', 'Denver', 'USA')
ON CONFLICT (customer_id) DO NOTHING;

-- Products
INSERT INTO products (product_id, sku, name, category, price, stock_quantity, description) VALUES
(1, 'PROD-LAPTOP-01', 'Pro Laptop 15-inch', 'Electronics', 1299.99, 25, 'High performance laptop with 32GB RAM'),
(2, 'PROD-PHONE-01', 'Smartphone Pro Max', 'Electronics', 999.00, 8, 'Flagship smartphone with OLED display (Low Stock)'),
(3, 'PROD-HEADPHONE-01', 'Wireless Noise Canceling Headphones', 'Audio', 199.50, 45, 'Premium over-ear wireless headphones'),
(4, 'PROD-MONITOR-01', '4K Ultra-Wide Monitor 34-inch', 'Displays', 649.00, 5, 'Curved 4K productivity monitor (Low Stock)'),
(5, 'PROD-KEYBOARD-01', 'Mechanical Wireless Keyboard', 'Accessories', 129.00, 50, 'Compact wireless mechanical keyboard'),
(6, 'PROD-MOUSE-01', 'Ergonomic Precision Mouse', 'Accessories', 79.99, 4, 'Ergonomic mouse with multi-device pairing (Low Stock)'),
(7, 'PROD-STAND-01', 'Aluminum Laptop Stand', 'Accessories', 49.99, 100, 'Adjustable ergonomic aluminum laptop stand')
ON CONFLICT (product_id) DO NOTHING;

-- Orders
INSERT INTO orders (order_id, customer_id, order_date, status, total_amount) VALUES
(1, 1, NOW() - INTERVAL '45 days', 'completed', 2599.98),
(2, 2, NOW() - INTERVAL '20 days', 'completed', 1998.00),
(3, 3, NOW() - INTERVAL '15 days', 'completed', 1299.99),
(4, 4, NOW() - INTERVAL '10 days', 'completed', 649.00),
(5, 5, NOW() - INTERVAL '5 days',  'completed', 328.50),
(6, 1, NOW() - INTERVAL '3 days',  'completed', 1499.49),
(7, 6, NOW() - INTERVAL '2 days',  'cancelled', 999.00),
(8, 2, NOW() - INTERVAL '25 days', 'refunded',  1299.99),
(9, 7, NOW() - INTERVAL '12 days', 'completed', 399.00)
ON CONFLICT (order_id) DO NOTHING;

-- Order Items
INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 2, 1299.99, 2599.98),
(2, 2, 2, 2, 999.00, 1998.00),
(3, 3, 1, 1, 1299.99, 1299.99),
(4, 4, 4, 1, 649.00, 649.00),
(5, 5, 3, 1, 199.50, 199.50),
(6, 5, 5, 1, 129.00, 129.00),
(7, 6, 1, 1, 1299.99, 1299.99),
(8, 6, 3, 1, 199.50, 199.50),
(9, 7, 2, 1, 999.00, 999.00),
(10, 8, 1, 1, 1299.99, 1299.99),
(11, 9, 3, 2, 199.50, 399.00)
ON CONFLICT (item_id) DO NOTHING;

-- Refunds
INSERT INTO refunds (refund_id, order_id, refund_amount, refund_date, reason, status) VALUES
(1, 8, 1299.99, NOW() - INTERVAL '20 days', 'Customer changed mind within 30-day window', 'processed'),
(2, 5, 50.00,   NOW() - INTERVAL '2 days',  'Price match guarantee adjustment', 'processed')
ON CONFLICT (refund_id) DO NOTHING;

-- Adjust sequence values to prevent duplicate key errors on subsequent inserts
SELECT setval('customers_customer_id_seq', (SELECT MAX(customer_id) FROM customers));
SELECT setval('products_product_id_seq', (SELECT MAX(product_id) FROM products));
SELECT setval('orders_order_id_seq', (SELECT MAX(order_id) FROM orders));
SELECT setval('order_items_item_id_seq', (SELECT MAX(item_id) FROM order_items));
SELECT setval('refunds_refund_id_seq', (SELECT MAX(refund_id) FROM refunds));

-- Ensure genai_readonly has SELECT access to all tables
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'genai_readonly') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO genai_readonly;
    END IF;
END
$$;
