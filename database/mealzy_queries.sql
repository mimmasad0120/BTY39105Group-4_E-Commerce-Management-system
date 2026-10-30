USE mealzy_main;

-- =========================================
-- 1. DATABASE INFORMATION
-- =========================================

SELECT DATABASE() AS current_database;
SHOW TABLES;

SELECT
    TABLE_NAME,
    ENGINE,
    TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mealzy_main'
ORDER BY TABLE_NAME;


-- =========================================
-- 2. CUSTOMER QUERIES
-- =========================================

SELECT * FROM customer;

SELECT *
FROM customer
ORDER BY id DESC
LIMIT 20;

SELECT COUNT(*) AS total_customers
FROM customer;

SELECT id, name, email, phone
FROM customer
ORDER BY id DESC;

SELECT email, COUNT(*) AS occurrences
FROM customer
GROUP BY email
HAVING COUNT(*) > 1;

DESCRIBE customer;


-- =========================================
-- 3. PRODUCT QUERIES
-- =========================================

SELECT * FROM product;

SELECT *
FROM product
ORDER BY id DESC
LIMIT 20;

SELECT COUNT(*) AS total_products
FROM product;

SELECT *
FROM product
WHERE price BETWEEN 100 AND 300
ORDER BY price ASC;

SELECT *
FROM product
WHERE name LIKE '%pizza%';

SELECT *
FROM product
WHERE stock <= 5
ORDER BY stock ASC;

SELECT category, COUNT(*) AS product_count
FROM product
GROUP BY category
ORDER BY product_count DESC;

SELECT ROUND(AVG(price), 2) AS average_product_price
FROM product;

DESCRIBE product;


-- =========================================
-- 4. ORDER QUERIES
-- =========================================

SELECT *
FROM `order`
ORDER BY id DESC;

SELECT *
FROM `order`
ORDER BY id DESC
LIMIT 20;

SELECT COUNT(*) AS total_orders
FROM `order`;

SELECT *
FROM `order`
WHERE customer_id = 1;

SELECT status, COUNT(*) AS total_orders
FROM `order`
GROUP BY status;

SELECT ROUND(SUM(total_amount), 2) AS total_order_value
FROM `order`;

SELECT ROUND(AVG(total_amount), 2) AS average_order_amount
FROM `order`;

SELECT *
FROM `order`
ORDER BY total_amount DESC
LIMIT 10;

DESCRIBE `order`;


-- =========================================
-- 5. CUSTOMER AND ORDER RELATIONSHIPS
-- =========================================

SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    o.id AS order_id,
    o.order_date,
    o.total_amount,
    o.status
FROM customer AS c
INNER JOIN `order` AS o
    ON c.id = o.customer_id
ORDER BY o.id DESC;

SELECT
    c.id,
    c.name,
    COUNT(o.id) AS total_orders
FROM customer AS c
LEFT JOIN `order` AS o
    ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_orders DESC;

SELECT
    c.id,
    c.name,
    c.email
FROM customer AS c
LEFT JOIN `order` AS o
    ON c.id = o.customer_id
WHERE o.id IS NULL;

SELECT
    c.id,
    c.name,
    COALESCE(SUM(o.total_amount), 0) AS total_order_value
FROM customer AS c
LEFT JOIN `order` AS o
    ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_order_value DESC;


-- =========================================
-- 6. PAYMENT TRANSACTIONS
-- =========================================

SELECT *
FROM payment_transactions
ORDER BY id DESC;

SELECT COUNT(*) AS total_payment_transactions
FROM payment_transactions;

DESCRIBE payment_transactions;


-- =========================================
-- 7. ADMIN QUERIES
-- Run if the admin table exists
-- =========================================

SELECT COUNT(*) AS total_admins
FROM admin;

DESCRIBE admin;


-- =========================================
-- 8. DELIVERY USER QUERIES
-- Run if the delivery_user table exists
-- =========================================

SELECT COUNT(*) AS total_delivery_users
FROM delivery_user;

DESCRIBE delivery_user;


-- =========================================
-- 9. ORDER FEEDBACK
-- Run if the order_feedback table exists
-- =========================================

SELECT *
FROM order_feedback
ORDER BY id DESC;

SELECT COUNT(*) AS total_feedback
FROM order_feedback;

SELECT ROUND(AVG(rating), 2) AS average_rating
FROM order_feedback;

SELECT rating, COUNT(*) AS rating_count
FROM order_feedback
GROUP BY rating
ORDER BY rating DESC;

DESCRIBE order_feedback;


-- =========================================
-- 10. ORDER ITEMS
-- Run if order_item exists
-- =========================================

SELECT *
FROM order_item;

SELECT
    oi.order_id,
    p.name AS product_name,
    oi.quantity,
    oi.price
FROM order_item AS oi
INNER JOIN product AS p
    ON oi.product_id = p.id
ORDER BY oi.order_id DESC;

SELECT
    p.id,
    p.name,
    SUM(oi.quantity) AS quantity_ordered
FROM order_item AS oi
INNER JOIN product AS p
    ON oi.product_id = p.id
GROUP BY p.id, p.name
ORDER BY quantity_ordered DESC
LIMIT 10;


-- =========================================
-- 11. ADMIN DASHBOARD STATISTICS
-- =========================================

SELECT
    (SELECT COUNT(*) FROM customer) AS total_customers,
    (SELECT COUNT(*) FROM product) AS total_products,
    (SELECT COUNT(*) FROM `order`) AS total_orders,
    (SELECT COUNT(*) FROM payment_transactions)
        AS total_payment_transactions;


-- =========================================
-- 12. DATABASE TABLE STRUCTURES
-- =========================================

SHOW CREATE TABLE customer;
SHOW CREATE TABLE product;
SHOW CREATE TABLE `order`;
SHOW CREATE TABLE payment_transactions;


-- =========================================
-- 13. FOREIGN KEY RELATIONSHIPS FOR ER DIAGRAM
-- =========================================

SELECT
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'mealzy_main'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;


-- =========================================
-- 14. PRIMARY KEY INFORMATION
-- =========================================

SELECT
    TABLE_NAME,
    COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'mealzy_main'
  AND CONSTRAINT_NAME = 'PRIMARY'
ORDER BY TABLE_NAME, ORDINAL_POSITION;


-- =========================================
-- 15. INDEX INFORMATION
-- =========================================

SHOW INDEX FROM customer;
SHOW INDEX FROM product;
SHOW INDEX FROM `order`;


-- =========================================
-- 16. EXACT COUNTS FOR MAIN TABLES
-- =========================================

SELECT 'Customers' AS table_name, COUNT(*) AS total
FROM customer

UNION ALL

SELECT 'Products', COUNT(*)
FROM product

UNION ALL

SELECT 'Orders', COUNT(*)
FROM `order`

UNION ALL

SELECT 'Payment Transactions', COUNT(*)
FROM payment_transactions;


-- =========================================
-- END OF MEALZY INSPECTION QUERIES
-- =========================================
