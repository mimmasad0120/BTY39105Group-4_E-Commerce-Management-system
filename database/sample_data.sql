USE mealzy_main;

-- =========================================
-- 1. ADD 200 SAMPLE CUSTOMERS
-- =========================================

INSERT INTO customer (name, email, phone, password)
SELECT
    CONCAT('Demo Customer ', LPAD(n, 3, '0')),
    CONCAT('demo.customer', LPAD(n, 3, '0'), '@example.com'),
    CONCAT('900', LPAD(n, 7, '0')),
    'SAMPLE_DATA_NOT_A_LOGIN_PASSWORD'
FROM (
    SELECT a.d * 100 + b.d * 10 + c.d + 1 AS n
    FROM
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) a
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) b
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) c
) numbers
WHERE n BETWEEN 1 AND 200
  AND NOT EXISTS (
      SELECT 1
      FROM customer existing
      WHERE existing.email =
          CONCAT('demo.customer', LPAD(n, 3, '0'), '@example.com')
  );

-- =========================================
-- 2. ADD 200 SAMPLE PRODUCTS
-- =========================================

INSERT INTO product
    (name, category, description, price, unit, stock, image_url)
SELECT
    CONCAT('Demo Product ', LPAD(n, 3, '0')),
    CASE MOD(n, 5)
        WHEN 0 THEN 'Fruits'
        WHEN 1 THEN 'Vegetables'
        WHEN 2 THEN 'Dairy'
        WHEN 3 THEN 'Bakery'
        ELSE 'Snacks'
    END,
    CONCAT('Sample product for dashboard testing ', n),
    ROUND(20 + MOD(n, 100) * 2.5, 2),
    'piece',
    100,
    NULL
FROM (
    SELECT a.d * 100 + b.d * 10 + c.d + 1 AS n
    FROM
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) a
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) b
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) c
) numbers
WHERE n BETWEEN 1 AND 200
  AND NOT EXISTS (
      SELECT 1
      FROM product existing
      WHERE existing.name =
          CONCAT('Demo Product ', LPAD(n, 3, '0'))
  );

-- =========================================
-- 3. ADD 200 SAMPLE ORDERS
-- Uses the sample customers and products above.
-- =========================================

INSERT INTO `order`
    (customer_email, product_name, quantity, total, status,
     address, location, payment_method, payment_status,
     payment_utr, delivery_user_id)
SELECT
    c.email,
    p.name,
    1 + MOD(n, 3),
    p.price * (1 + MOD(n, 3)),
    'Pending',
    CONCAT('Demo Address ', LPAD(n, 3, '0')),
    'Kolkata',
    'Cash on Delivery',
    'Due',
    NULL,
    NULL
FROM (
    SELECT a.d * 100 + b.d * 10 + c.d + 1 AS n
    FROM
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) a
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) b
    CROSS JOIN
        (SELECT 0 d UNION ALL SELECT 1 UNION ALL SELECT 2
         UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
         SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
         UNION ALL SELECT 8 UNION ALL SELECT 9) c
) numbers
JOIN customer c
    ON c.email = CONCAT(
        'demo.customer', LPAD(n, 3, '0'), '@example.com'
    )
JOIN product p
    ON p.name = CONCAT('Demo Product ', LPAD(n, 3, '0'))
WHERE n BETWEEN 1 AND 200
  AND NOT EXISTS (
      SELECT 1
      FROM `order` existing
      WHERE existing.customer_email = c.email
        AND existing.product_name = p.name
        AND existing.address =
            CONCAT('Demo Address ', LPAD(n, 3, '0'))
  );

-- =========================================
-- 4. VERIFY THE FINAL COUNTS
-- =========================================

SELECT COUNT(*) AS customers FROM customer;
SELECT COUNT(*) AS products FROM product;
SELECT COUNT(*) AS orders FROM `order`;

SELECT *
FROM customer
ORDER BY id DESC;
