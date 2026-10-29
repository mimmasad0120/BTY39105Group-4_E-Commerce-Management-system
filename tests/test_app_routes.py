import app as app_module
from email.message import EmailMessage
import smtplib


def test_root_route_serves_login_page():
    client = app_module.app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'<html' in response.data.lower()


def test_hi_html_route_serves_login_page():
    client = app_module.app.test_client()
    response = client.get('/hi.html')
    assert response.status_code == 200
    assert b'<html' in response.data.lower()


def test_frontend_assets_are_served_with_their_content_types():
    client = app_module.app.test_client()

    stylesheet = client.get('/style.css')
    javascript = client.get('/script.js')

    assert stylesheet.status_code == 200
    assert stylesheet.mimetype == 'text/css'
    assert javascript.status_code == 200
    assert javascript.mimetype == 'text/javascript'
    assert b'async function customerLogin' in javascript.data


def test_customer_and_product_models_use_their_database_tables():
    assert app_module.Customer.__tablename__ == 'customer2'
    assert app_module.Product.__tablename__ == 'product2'
    assert app_module.Order.__tablename__ == 'order2'


def test_database_uses_local_sqlite_regardless_of_external_database_settings():
    with app_module.app.app_context():
        assert app_module.db.engine.dialect.name == 'sqlite'
        assert app_module.app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///mealzy_local.db'


def test_product_catalog_includes_more_pizza_momo_and_biryani_varieties():
    response = app_module.app.test_client().get('/api/products')

    assert response.status_code == 200
    products = {product['name']: product for product in response.get_json()['products']}
    expected_names = {
        'Farmhouse Pizza',
        'Paneer Tikka Pizza',
        'Chicken Tikka Pizza',
        'Steamed Veg Momos',
        'Chicken Momos',
        'Tandoori Paneer Momos',
        'Dada Boudi Chicken Biryani',
        'D-Bapi Special Biryani',
        'Wow! Momo Veg Momos',
        'Wow! Momo Chicken Momos',
        'Egg Biryani',
        'Paneer Biryani',
        'Kolkata Chicken Biryani',
        'Penne Arrabbiata',
        'Veg Hakka Noodles',
        'Masala Dosa',
        'Mini Margherita Pizza',
        'Veg Momo Snack Plate',
        'Paneer Kathi Roll',
        'Masala Fries',
        'Mini Veg Biryani',
        'Samosa Chaat',
        'Pani Puri',
        'Paneer Tikka',
        'Dal Makhani',
        'Chicken Kathi Roll',
        'Chilli Paneer',
        'Chicken Fried Rice',
        'Gulab Jamun',
        'Chocolate Brownie',
        'Mango Lassi',
        'Strawberry Milkshake',
    }

    assert expected_names <= products.keys()
    assert all(products[name]['price'] > 0 for name in expected_names)
    assert all(products[name]['imageUrl'] for name in expected_names)
    momo_names = {
        'Steamed Veg Momos',
        'Chicken Momos',
        'Tandoori Paneer Momos',
        'Wow! Momo Veg Momos',
        'Wow! Momo Chicken Momos',
        'Veg Momo Snack Plate',
    }
    assert len({products[name]['imageUrl'] for name in momo_names}) == len(momo_names)
    assert all(products[name]['price'] == 99 for name in {
        'Mini Margherita Pizza',
        'Veg Momo Snack Plate',
        'Paneer Kathi Roll',
        'Masala Fries',
        'Mini Veg Biryani',
    })


def test_login_routes_accept_cors_preflight():
    client = app_module.app.test_client()

    for path in ('/customer-login', '/admin-login', '/delivery-login', '/api/delivery-users',
                 '/api/delivery/presence',
                 '/api/admin/feedback',
                 '/api/products/1/ratings',
                 '/api/delivery/orders', '/api/delivery/orders/1/status',
                 '/api/delivery/orders/1/accept', '/api/delivery/orders/1/delivery-otp',
                 '/api/customer/orders/1/feedback'):
        response = client.options(path)
        assert response.status_code == 204
        assert response.headers['Access-Control-Allow-Origin'] == '*'
        assert 'POST' in response.headers['Access-Control-Allow-Methods']


def test_otp_emails_include_inline_mealzy_logo_and_plain_text_fallback(monkeypatch):
    monkeypatch.setenv('EMAIL_ADDRESS', 'sender@example.com')
    message = app_module.build_otp_email(
        'customer@example.com',
        'Your Mealzy verification code',
        'Verify your email',
        '123456',
        'Use this code to finish creating your Mealzy account.',
    )

    assert isinstance(message, EmailMessage)
    assert message.get_content_type() == 'multipart/alternative'
    assert '123456' in message.get_body(preferencelist=('plain',)).get_content()
    html_part = message.get_body(preferencelist=('html',))
    assert html_part is not None
    assert 'cid:mealzy-logo' in html_part.get_content()
    logo_part = next(part for part in message.walk() if part.get_content_type() == 'image/png')
    assert logo_part.get_content_type() == 'image/png'
    assert logo_part['Content-ID'] == '<mealzy-logo>'
    assert logo_part.get_content_disposition() == 'inline'


def test_otp_email_retries_after_smtp_disconnect(monkeypatch):
    monkeypatch.setenv('EMAIL_ADDRESS', 'sender@example.com')
    monkeypatch.setenv('EMAIL_PASSWORD', 'test-password')
    smtp_connections = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.send_attempts = 0
            smtp_connections.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, username, password):
            assert username == 'sender@example.com'
            assert password == 'test-password'

        def send_message(self, message):
            self.send_attempts += 1
            if len(smtp_connections) == 1:
                raise smtplib.SMTPServerDisconnected('Connection unexpectedly closed')

    monkeypatch.setattr(app_module.smtplib, 'SMTP', FakeSMTP)

    app_module.send_otp_email(
        'customer@example.com',
        'Your Mealzy verification code',
        'Verify your email',
        '123456',
        'Use this code to finish creating your Mealzy account.',
    )

    assert len(smtp_connections) == 2
    assert [connection.send_attempts for connection in smtp_connections] == [1, 1]


def test_admin_login_also_routes_delivery_credentials_to_delivery_dashboard():
    username = 'delivery-admin-login-test'
    with app_module.app.app_context():
        app_module.DeliveryUser.query.filter_by(username=username).delete()
        delivery_user = app_module.DeliveryUser(
            name='Test Driver',
            username=username,
            password=app_module.generate_password_hash('test-password-123'),
        )
        app_module.db.session.add(delivery_user)
        app_module.db.session.commit()
        try:
            response = app_module.app.test_client().post(
                '/admin-login',
                json={'username': username, 'password': 'test-password-123'},
            )
            assert response.status_code == 200
            payload = response.get_json()
            assert payload['role'] == 'delivery'
            assert payload['name'] == 'Test Driver'
            assert payload['token']
        finally:
            app_module.DeliveryUser.query.filter_by(username=username).delete()
            app_module.db.session.commit()


def test_delivery_presence_requires_authentication_and_expires():
    username = 'delivery-presence-test'
    with app_module.app.app_context():
        app_module.DeliveryUser.query.filter_by(username=username).delete()
        delivery_user = app_module.DeliveryUser(
            name='Presence Test Driver',
            username=username,
            password=app_module.generate_password_hash('test-password-123'),
        )
        app_module.db.session.add(delivery_user)
        app_module.db.session.commit()
        client = app_module.app.test_client()
        try:
            assert client.post(
                '/api/delivery/presence',
                json={'online': True},
            ).status_code == 401

            login = client.post(
                '/delivery-login',
                json={'username': username, 'password': 'test-password-123'},
            )
            headers = {'Authorization': f"Bearer {login.get_json()['token']}"}
            online = client.post(
                '/api/delivery/presence',
                json={'online': True},
                headers=headers,
            )
            assert online.status_code == 200
            accounts = client.get('/api/delivery-users').get_json()['deliveryUsers']
            assert next(account for account in accounts if account['username'] == username)['online'] is True

            delivery_user.last_seen_at = (
                app_module.time.time() - app_module.DELIVERY_ONLINE_TIMEOUT_SECONDS - 1
            )
            app_module.db.session.commit()
            accounts = client.get('/api/delivery-users').get_json()['deliveryUsers']
            assert next(account for account in accounts if account['username'] == username)['online'] is False

            offline = client.post(
                '/api/delivery/presence',
                json={'online': False},
                headers=headers,
            )
            assert offline.status_code == 200
            assert delivery_user.last_seen_at is None
        finally:
            app_module.DeliveryUser.query.filter_by(username=username).delete()
            app_module.db.session.commit()


def test_admin_can_create_delivery_account_and_delivery_user_can_login():
    username = 'delivery-test-account'
    admin_username = 'delivery-account-test-admin'
    with app_module.app.app_context():
        app_module.DeliveryUser.query.filter_by(username=username).delete()
        app_module.Admin.query.filter_by(username=admin_username).delete()
        admin = app_module.Admin(
            username=admin_username,
            password=app_module.generate_password_hash('admin-password-123'),
        )
        app_module.db.session.add(admin)
        app_module.db.session.commit()
        client = app_module.app.test_client()
        try:
            created = client.post(
                '/api/delivery-users',
                json={
                    'name': 'Test Driver',
                    'username': username,
                    'password': 'test-password-123',
                    'adminUsername': admin_username,
                    'adminPassword': 'admin-password-123',
                },
            )
            assert created.status_code == 201
            user = app_module.DeliveryUser.query.filter_by(username=username).first()
            assert user is not None
            assert user.password != 'test-password-123'

            login = client.post(
                '/delivery-login',
                json={'username': username, 'password': 'test-password-123'},
            )
            assert login.status_code == 200
            assert login.get_json()['name'] == 'Test Driver'
            assert login.get_json()['token']

            duplicate = client.post(
                '/api/delivery-users',
                json={
                    'name': 'Another Driver',
                    'username': username,
                    'password': 'another-password',
                    'adminUsername': admin_username,
                    'adminPassword': 'admin-password-123',
                },
            )
            assert duplicate.status_code == 409
        finally:
            app_module.DeliveryUser.query.filter_by(username=username).delete()
            app_module.Admin.query.filter_by(username=admin_username).delete()
            app_module.db.session.commit()


def test_admin_orders_include_assigned_delivery_name():
    with app_module.app.app_context():
        username = 'admin-order-rider-test'
        email = 'admin-order-rider-test@example.com'
        app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
        app_module.DeliveryUser.query.filter_by(username=username).delete()
        delivery_user = app_module.DeliveryUser(
            name='Assigned Test Rider',
            username=username,
        password=app_module.generate_password_hash('rider-password-123'),
        )
        app_module.db.session.add(delivery_user)
        app_module.db.session.flush()
        assigned_order = app_module.Order(
            customer_email=email,
            product_name='Assigned Rider Meal',
            quantity=1,
            total=80,
            status='Processing',
            delivery_user_id=delivery_user.id,
        )
        unassigned_order = app_module.Order(
            customer_email=email,
            product_name='Unassigned Rider Meal',
            quantity=1,
            total=60,
            status='Pending',
        )
        app_module.db.session.add_all([assigned_order, unassigned_order])
        app_module.db.session.commit()
        try:
            response = app_module.app.test_client().get('/api/orders')
            assert response.status_code == 200
            orders = {
                order['id']: order
                for order in response.get_json()['orders']
                if order['id'] in {assigned_order.id, unassigned_order.id}
            }
            assert orders[assigned_order.id]['deliveryName'] == 'Assigned Test Rider'
            assert orders[unassigned_order.id]['deliveryName'] is None
            assert 'password' not in orders[assigned_order.id]
        finally:
            app_module.Order.query.filter(
                app_module.Order.id.in_([assigned_order.id, unassigned_order.id])
            ).delete(synchronize_session=False)
            app_module.DeliveryUser.query.filter_by(username=username).delete()
            app_module.db.session.commit()


def test_delivery_confirmation_code_is_customer_only_and_not_emailed(monkeypatch):
    with app_module.app.app_context():
        customer_email = 'delivery-order-test@example.com'
        app_module.Order.query.filter(
            app_module.Order.customer_email.in_(
                [customer_email, 'another-customer@example.com']
            )
        ).delete(synchronize_session=False)
        app_module.Customer.query.filter_by(email=customer_email).delete()
        customer = app_module.Customer(
            name='Order Test Customer',
            email=customer_email,
            phone='1234567890',
            password=app_module.generate_password_hash('customer-password-123'),
        )
        order = app_module.Order(
            customer_email=customer_email,
            product_name='Delivery Test Meal',
            quantity=1,
            total=120,
            status='Pending',
            address='House 1, Test Road',
            location='Test City',
            payment_method='UPI',
            payment_status='Confirmed',
        )
        other_customer_order = app_module.Order(
            customer_email='another-customer@example.com',
            product_name='Private Meal',
            quantity=1,
            total=75,
            status='Out for Delivery',
        )
        app_module.db.session.add_all([customer, order, other_customer_order])
        app_module.db.session.commit()
        client = app_module.app.test_client()
        email_calls = []
        monkeypatch.setattr(
            app_module,
            'send_delivery_completion_otp',
            lambda email, otp: email_calls.append((email, otp)),
        )
        try:
            assert client.get('/api/customer/orders').status_code == 401
            customer_login = client.post(
                '/customer-login',
                json={'email': customer_email, 'password': 'customer-password-123'},
            )
            assert customer_login.status_code == 200
            customer_headers = {
                'Authorization': f"Bearer {customer_login.get_json()['token']}"
            }
            before_code = client.get(
                '/api/customer/orders',
                headers=customer_headers,
            ).get_json()['orders']
            assert [item['id'] for item in before_code] == [order.id]
            assert before_code[0]['deliveryOtp'] is None

            assert client.get('/api/delivery/orders').status_code == 401
            delivery_user = app_module.DeliveryUser(
                name='Test Driver',
                username='delivery-order-test',
                password=app_module.generate_password_hash('test-password-123'),
            )
            app_module.db.session.add(delivery_user)
            app_module.db.session.commit()
            login = client.post(
                '/delivery-login',
                json={'username': 'delivery-order-test', 'password': 'test-password-123'},
            )
            token = login.get_json()['token']
            headers = {'Authorization': f'Bearer {token}'}

            listing = client.get('/api/delivery/orders', headers=headers)
            assert listing.status_code == 200
            assert order.id in {item['id'] for item in listing.get_json()['orders']}

            before_accept_status = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Out for Delivery'},
                headers=headers,
            )
            assert before_accept_status.status_code == 403

            accepted = client.post(
                f'/api/delivery/orders/{order.id}/accept',
                headers=headers,
            )
            assert accepted.status_code == 200
            assert accepted.get_json()['status'] == 'Processing'
            assert app_module.db.session.get(app_module.Order, order.id).delivery_user_id == delivery_user.id

            another_user = app_module.DeliveryUser(
                name='Another Driver',
                username='delivery-order-test-2',
                password=app_module.generate_password_hash('another-password-123'),
            )
            app_module.db.session.add(another_user)
            app_module.db.session.commit()
            second_login = client.post(
                '/delivery-login',
                json={'username': 'delivery-order-test-2', 'password': 'another-password-123'},
            )
            second_headers = {'Authorization': f"Bearer {second_login.get_json()['token']}"}
            duplicate_accept = client.post(
                f'/api/delivery/orders/{order.id}/accept',
                headers=second_headers,
            )
            assert duplicate_accept.status_code == 409

            out_for_delivery = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Out for Delivery'},
                headers=headers,
            )
            assert out_for_delivery.status_code == 200

            missing_otp = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Delivered'},
                headers=headers,
            )
            assert missing_otp.status_code == 400

            requested_otp = client.post(
                f'/api/delivery/orders/{order.id}/delivery-otp',
                headers=headers,
            )
            assert requested_otp.status_code == 200
            assert email_calls == []
            assert 'customer' in requested_otp.get_json()['message'].lower()
            assert app_module.db.session.get(app_module.Order, order.id).status == 'Out for Delivery'

            customer_orders = client.get(
                '/api/customer/orders',
                headers=customer_headers,
            ).get_json()['orders']
            visible_order = next(item for item in customer_orders if item['id'] == order.id)
            otp = visible_order['deliveryOtp']
            assert len(otp) == 6 and otp.isdigit()
            assert all(item['customerEmail'] == customer_email for item in customer_orders)
            global_orders = client.get('/api/orders').get_json()['orders']
            assert all('deliveryOtp' not in item for item in global_orders)

            invalid_otp = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Delivered', 'otp': '000000' if otp != '000000' else '000001'},
                headers=headers,
            )
            assert invalid_otp.status_code == 400
            assert app_module.db.session.get(app_module.Order, order.id).status == 'Out for Delivery'

            delivered = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Delivered', 'otp': otp},
                headers=headers,
            )
            assert delivered.status_code == 200
            assert app_module.db.session.get(app_module.Order, order.id).status == 'Delivered'
            completed_orders = client.get(
                '/api/delivery/orders',
                headers=headers,
            ).get_json()['orders']
            assert any(
                item['id'] == order.id and item['status'] == 'Delivered'
                for item in completed_orders
            )
            other_driver_orders = client.get(
                '/api/delivery/orders',
                headers=second_headers,
            ).get_json()['orders']
            assert order.id not in {item['id'] for item in other_driver_orders}
            after_delivery = client.get(
                '/api/customer/orders',
                headers=customer_headers,
            ).get_json()['orders']
            assert next(item for item in after_delivery if item['id'] == order.id)['deliveryOtp'] is None
            reused_otp = client.post(
                f'/api/delivery/orders/{order.id}/status',
                json={'status': 'Delivered', 'otp': otp},
                headers=headers,
            )
            assert reused_otp.status_code == 400
        finally:
            app_module.DeliveryCompletionOtp.query.filter_by(order_id=order.id).delete()
            app_module.Order.query.filter(
                app_module.Order.customer_email.in_(
                    [customer_email, 'another-customer@example.com']
                )
            ).delete(synchronize_session=False)
            app_module.Customer.query.filter_by(email=customer_email).delete()
            app_module.DeliveryUser.query.filter(
                app_module.DeliveryUser.username.in_(['delivery-order-test', 'delivery-order-test-2'])
            ).delete(synchronize_session=False)
            app_module.db.session.commit()


def test_cash_on_delivery_can_be_marked_delivered_without_a_code():
    email = 'delivery-cod-test@example.com'
    username = 'delivery-cod-test'
    with app_module.app.app_context():
        app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
        app_module.DeliveryUser.query.filter_by(username=username).delete()
        delivery_user = app_module.DeliveryUser(
            name='COD Test Driver',
            username=username,
            password=app_module.generate_password_hash('cod-driver-password'),
        )
        app_module.db.session.add(delivery_user)
        app_module.db.session.flush()
        order = app_module.Order(
            customer_email=email,
            product_name='COD Test Meal',
            quantity=1,
            total=50,
            status='Out for Delivery',
            payment_method='Cash on Delivery',
            payment_status='Due',
            delivery_user_id=delivery_user.id,
        )
        app_module.db.session.add(order)
        app_module.db.session.commit()
        order_id = order.id
        headers = {'Authorization': f'Bearer {app_module.create_delivery_token(delivery_user)}'}
        client = app_module.app.test_client()
        try:
            code_request = client.post(
                f'/api/delivery/orders/{order_id}/delivery-otp',
                headers=headers,
            )
            assert code_request.status_code == 409
            assert app_module.DeliveryCompletionOtp.query.filter_by(order_id=order_id).first() is None

            delivered = client.post(
                f'/api/delivery/orders/{order_id}/status',
                json={'status': 'Delivered'},
                headers=headers,
            )
            assert delivered.status_code == 200
            assert app_module.db.session.get(app_module.Order, order_id).status == 'Delivered'
        finally:
            app_module.DeliveryCompletionOtp.query.filter_by(order_id=order_id).delete()
            app_module.Order.query.filter_by(id=order_id).delete()
            app_module.DeliveryUser.query.filter_by(username=username).delete()
            app_module.db.session.commit()


def test_upi_orders_start_pending_and_require_customer_confirmation():
    email = 'upi-payment-test@example.com'
    delivery_username = 'upi-payment-test-driver'
    with app_module.app.app_context():
        app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
        app_module.Customer.query.filter_by(email=email).delete()
        app_module.DeliveryUser.query.filter_by(username=delivery_username).delete()
        product = app_module.Product(
            name='UPI Test Meal',
            category='lunch',
            description='Temporary product for UPI payment tests.',
            price=80,
            unit='per meal',
            stock=5,
        )
        customer = app_module.Customer(
            name='UPI Test Customer',
            email=email,
            phone='1234567890',
            password=app_module.generate_password_hash('upi-customer-password'),
        )
        delivery_user = app_module.DeliveryUser(
            name='UPI Test Driver',
            username=delivery_username,
            password=app_module.generate_password_hash('upi-driver-password'),
        )
        app_module.db.session.add_all([product, customer, delivery_user])
        app_module.db.session.commit()
        client = app_module.app.test_client()
        try:
            placed = client.post(
                '/api/orders',
                json={
                    'customerEmail': email,
                    'paymentMethod': 'UPI',
                    'address': 'House 7, UPI Road',
                    'location': 'UPI Test City',
                    'items': [{'productId': product.id, 'quantity': 1}],
                },
            )
            assert placed.status_code == 201
            order_id = placed.get_json()['order_id']
            order = app_module.db.session.get(app_module.Order, order_id)
            assert order.status == 'Pending'
            assert order.payment_status == 'Pending'

            delivery_login = client.post(
                '/delivery-login',
                json={'username': delivery_username, 'password': 'upi-driver-password'},
            )
            delivery_headers = {
                'Authorization': f"Bearer {delivery_login.get_json()['token']}"
            }
            delivery_orders = client.get(
                '/api/delivery/orders',
                headers=delivery_headers,
            )
            assert delivery_orders.status_code == 200
            listed_order = next(
                item for item in delivery_orders.get_json()['orders']
                if item['id'] == order_id
            )
            assert listed_order['paymentReady'] is False
            not_yet_accepted = client.post(
                f'/api/delivery/orders/{order_id}/accept',
                headers=delivery_headers,
            )
            assert not_yet_accepted.status_code == 409

            unauthenticated = client.post(
                '/api/customer/orders/payment',
                json={'orderIds': [order_id]},
            )
            assert unauthenticated.status_code == 401

            login = client.post(
                '/customer-login',
                json={'email': email, 'password': 'upi-customer-password'},
            )
            headers = {'Authorization': f"Bearer {login.get_json()['token']}"}
            missing_utr = client.post(
                '/api/customer/orders/payment',
                json={'orderIds': [order_id]},
                headers=headers,
            )
            assert missing_utr.status_code == 400
            assert app_module.db.session.get(app_module.Order, order_id).payment_status == 'Pending'

            invalid_utr = client.post(
                '/api/customer/orders/payment',
                json={'orderIds': [order_id], 'utr': '12 34'},
                headers=headers,
            )
            assert invalid_utr.status_code == 400
            assert app_module.db.session.get(app_module.Order, order_id).payment_utr is None

            confirmed = client.post(
                '/api/customer/orders/payment',
                json={'orderIds': [order_id], 'utr': '123456789012'},
                headers=headers,
            )
            assert confirmed.status_code == 200
            confirmed_order_record = app_module.db.session.get(app_module.Order, order_id)
            assert confirmed_order_record.payment_status == 'Confirmed'
            assert confirmed_order_record.payment_utr == '123456789012'

            customer_orders = client.get('/api/customer/orders', headers=headers)
            customer_order = next(
                item for item in customer_orders.get_json()['orders']
                if item['id'] == order_id
            )
            assert customer_order['paymentUtr'] == '123456789012'
            admin_orders = client.get('/api/orders').get_json()['orders']
            admin_order = next(item for item in admin_orders if item['id'] == order_id)
            assert 'paymentUtr' not in admin_order

            confirmed_order = next(
                item for item in client.get(
                    '/api/delivery/orders',
                    headers=delivery_headers,
                ).get_json()['orders']
                if item['id'] == order_id
            )
            assert confirmed_order['paymentReady'] is True

            conflicting_utr = client.post(
                '/api/customer/orders/payment',
                json={'orderIds': [order_id], 'utr': '999999999999'},
                headers=headers,
            )
            assert conflicting_utr.status_code == 409
        finally:
            app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
            app_module.Customer.query.filter_by(email=email).delete()
            app_module.DeliveryUser.query.filter_by(username=delivery_username).delete()
            app_module.db.session.delete(product)
            app_module.db.session.commit()


def test_customer_feedback_is_saved_only_for_their_delivered_orders():
    with app_module.app.app_context():
        customer_email = 'feedback-order-test@example.com'
        other_email = 'feedback-other-customer@example.com'
        old_orders = app_module.Order.query.filter(
            app_module.Order.customer_email.in_([customer_email, other_email])
        ).all()
        for order in old_orders:
            app_module.OrderFeedback.query.filter_by(order_id=order.id).delete()
        app_module.Order.query.filter(
            app_module.Order.customer_email.in_([customer_email, other_email])
        ).delete(synchronize_session=False)
        app_module.Customer.query.filter(
            app_module.Customer.email.in_([customer_email, other_email])
        ).delete(synchronize_session=False)
        product_name = 'Delivered Feedback Meal'
        existing_product = app_module.Product.query.filter_by(name=product_name).first()
        if existing_product:
            app_module.db.session.delete(existing_product)
            app_module.db.session.commit()
        product = app_module.Product(
            name=product_name,
            category='test',
            description='Product used for rating tests.',
            price=120,
            unit='per item',
            stock=3,
        )
        customer = app_module.Customer(
            name='Feedback Customer',
            email=customer_email,
            phone='1234567890',
            password=app_module.generate_password_hash('feedback-password-123'),
        )
        delivered_order = app_module.Order(
            customer_email=customer_email,
            product_name='Delivered Feedback Meal',
            quantity=1,
            total=120,
            status='Delivered',
        )
        pending_order = app_module.Order(
            customer_email=customer_email,
            product_name='Pending Feedback Meal',
            quantity=1,
            total=75,
            status='Pending',
        )
        other_customer_order = app_module.Order(
            customer_email=other_email,
            product_name='Private Delivered Meal',
            quantity=1,
            total=60,
            status='Delivered',
        )
        app_module.db.session.add_all(
            [product, customer, delivered_order, pending_order, other_customer_order]
        )
        app_module.db.session.commit()
        client = app_module.app.test_client()
        try:
            assert client.post(
                f'/api/customer/orders/{delivered_order.id}/feedback',
                json={'rating': 5, 'comment': 'Great delivery'},
            ).status_code == 401
            login = client.post(
                '/customer-login',
                json={'email': customer_email, 'password': 'feedback-password-123'},
            )
            assert login.status_code == 200
            headers = {'Authorization': f"Bearer {login.get_json()['token']}"}

            pending_feedback = client.post(
                f'/api/customer/orders/{pending_order.id}/feedback',
                json={'rating': 5},
                headers=headers,
            )
            assert pending_feedback.status_code == 409
            private_feedback = client.post(
                f'/api/customer/orders/{other_customer_order.id}/feedback',
                json={'rating': 5},
                headers=headers,
            )
            assert private_feedback.status_code == 404
            invalid_rating = client.post(
                f'/api/customer/orders/{delivered_order.id}/feedback',
                json={'rating': 6},
                headers=headers,
            )
            assert invalid_rating.status_code == 400

            saved = client.post(
                f'/api/customer/orders/{delivered_order.id}/feedback',
                json={'rating': 4, 'comment': '  Great delivery  '},
                headers=headers,
            )
            assert saved.status_code == 200
            assert saved.get_json()['feedback']['comment'] == 'Great delivery'
            updated = client.post(
                f'/api/customer/orders/{delivered_order.id}/feedback',
                json={'rating': 5, 'comment': 'Excellent'},
                headers=headers,
            )
            assert updated.status_code == 200

            listed_orders = client.get(
                '/api/customer/orders',
                headers=headers,
            ).get_json()['orders']
            saved_order = next(item for item in listed_orders if item['id'] == delivered_order.id)
            assert saved_order['feedback']['rating'] == 5
            assert saved_order['feedback']['comment'] == 'Excellent'
            admin_feedback = client.get('/api/admin/feedback')
            assert admin_feedback.status_code == 200
            feedback_payload = admin_feedback.get_json()
            assert feedback_payload['ratingCount'] >= 1
            assert 1 <= feedback_payload['averageRating'] <= 5
            admin_review = next(
                item for item in feedback_payload['feedback']
                if item['orderId'] == delivered_order.id
            )
            assert admin_review['customerEmail'] == customer_email
            assert admin_review['productName'] == 'Delivered Feedback Meal'
            assert admin_review['rating'] == 5
            assert admin_review['comment'] == 'Excellent'
            product_ratings = client.get(f'/api/products/{product.id}/ratings')
            assert product_ratings.status_code == 200
            product_rating_payload = product_ratings.get_json()
            assert product_rating_payload['averageRating'] == 5
            assert product_rating_payload['ratingCount'] == 1
            assert product_rating_payload['ratings'][0]['comment'] == 'Excellent'
            assert 'customerEmail' not in product_rating_payload['ratings'][0]
            assert client.get('/api/products/999999/ratings').status_code == 404
            assert sum(
                item.order_id == delivered_order.id
                for item in app_module.OrderFeedback.query.all()
            ) == 1
        finally:
            app_module.OrderFeedback.query.filter(
                app_module.OrderFeedback.order_id.in_(
                    [delivered_order.id, pending_order.id, other_customer_order.id]
                )
            ).delete(synchronize_session=False)
            app_module.Order.query.filter(
                app_module.Order.customer_email.in_([customer_email, other_email])
            ).delete(synchronize_session=False)
            app_module.Customer.query.filter_by(email=customer_email).delete()
            app_module.db.session.delete(product)
            app_module.db.session.commit()


def test_99_category_and_seed_item_are_removed():
    client = app_module.app.test_client()
    page = client.get('/')
    response = client.get('/api/products')

    assert b'data-category="99"' not in page.data
    assert response.status_code == 200
    products = response.get_json()['products']
    assert all(product['name'] != 'Classic Chicken Wrap' for product in products)


def test_combo_products_are_seeded_at_99_and_199():
    client = app_module.app.test_client()
    response = client.get('/api/products')

    assert response.status_code == 200
    prices = {product['name']: product['price'] for product in response.get_json()['products']}
    assert prices['Quick Bite Combo'] == 99
    assert prices['Hearty Meal Combo'] == 199


def test_admin_can_update_product_price_and_stock():
    with app_module.app.app_context():
        product = app_module.Product(
            name='Editable Test Meal',
            category='lunch',
            description='Temporary product for edit tests.',
            price=45,
            unit='per meal',
            stock=8,
        )
        app_module.db.session.add(product)
        app_module.db.session.commit()
        product_id = product.id
        client = app_module.app.test_client()
        try:
            updated = client.put(
                f'/api/products/{product_id}',
                json={'price': 52.5, 'stock': 12},
            )
            assert updated.status_code == 200
            assert updated.get_json()['product'] == {
                'id': product_id,
                'price': 52.5,
                'stock': 12,
            }
            invalid_stock = client.put(
                f'/api/products/{product_id}',
                json={'stock': 1.5},
            )
            assert invalid_stock.status_code == 400
            missing = client.put('/api/products/999999999', json={'price': 10})
            assert missing.status_code == 404
        finally:
            app_module.db.session.delete(app_module.db.session.get(app_module.Product, product_id))
            app_module.db.session.commit()


def test_sms_otp_skips_placeholder_twilio_credentials(monkeypatch):
    monkeypatch.setenv('TWILIO_ACCOUNT_SID', 'your_twilio_account_sid')
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'your_twilio_auth_token')
    monkeypatch.setenv('TWILIO_PHONE_NUMBER', '+15555550100')
    monkeypatch.setattr(app_module, 'Client', lambda *_args, **_kwargs: None)

    assert app_module.send_sms_otp('+15555550101', '123456') is False


def test_order_route_accepts_delivery_address_and_location():
    with app_module.app.app_context():
        product = app_module.Product(
            name='Order Route Test Banana',
            category='Fruit',
            description='Temporary product for order route test.',
            price=20,
            unit='per bunch',
            stock=10,
        )
        app_module.db.session.add(product)
        app_module.db.session.commit()

        client = app_module.app.test_client()
        try:
            response = client.post(
                '/api/orders',
                json={
                    'productId': product.id,
                    'quantity': 2,
                    'customerEmail': 'customer@example.com',
                    'address': 'House 12, Green Road',
                    'location': 'Dhaka, Bangladesh',
                },
            )

            assert response.status_code == 201
            payload = response.get_json()
            assert payload['message'] == 'Order placed successfully.'

            order = app_module.Order.query.filter_by(
                customer_email='customer@example.com',
                product_name=product.name,
            ).order_by(app_module.Order.id.desc()).first()
            assert order is not None
            assert order.address == 'House 12, Green Road'
            assert order.location == 'Dhaka, Bangladesh'

            list_response = client.get('/api/orders')
            order_payload = list_response.get_json()
            assert any(item['address'] == 'House 12, Green Road' for item in order_payload['orders'])
        finally:
            app_module.Order.query.filter_by(
                customer_email='customer@example.com',
                product_name=product.name,
            ).delete(synchronize_session=False)
            app_module.db.session.delete(product)
            app_module.db.session.commit()


def test_mealzy70_coupon_requires_over_200_and_first_order():
    email = 'mealzy70-firstorder@example.com'
    with app_module.app.app_context():
        app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
        product = app_module.Product(
            name='Coupon Test Combo',
            category='lunch',
            description='Temporary product for coupon testing.',
            price=100,
            unit='per combo',
            stock=10,
        )
        app_module.db.session.add(product)
        app_module.db.session.commit()
        client = app_module.app.test_client()
        address = 'House 5, Green Road'
        location = 'Dhaka, Bangladesh'

        try:
            exact_minimum = client.post(
                '/api/coupons/validate',
                json={
                    'customerEmail': email,
                    'couponCode': 'MEALZY70',
                    'items': [{'productId': product.id, 'quantity': 2}],
                },
            )
            assert exact_minimum.status_code == 400
            assert 'above ₹200' in exact_minimum.get_json()['error']

            valid_coupon = client.post(
                '/api/coupons/validate',
                json={
                    'customerEmail': email,
                    'couponCode': 'MEALZY70',
                    'items': [{'productId': product.id, 'quantity': 3}],
                },
            )
            assert valid_coupon.status_code == 200
            assert valid_coupon.get_json()['discount'] == 210
            assert valid_coupon.get_json()['total'] == 90
            assert valid_coupon.get_json()['discount'] == round(valid_coupon.get_json()['subtotal'] * 0.7, 2)
            assert valid_coupon.get_json()['total'] == round(valid_coupon.get_json()['subtotal'] * 0.3, 2)

            order_response = client.post(
                '/api/orders',
                json={
                    'customerEmail': email,
                    'couponCode': 'MEALZY70',
                    'items': [{'productId': product.id, 'quantity': 3}],
                    'address': address,
                    'location': location,
                },
            )
            assert order_response.status_code == 201
            assert order_response.get_json()['total'] == 90
            saved_order_total = sum(
                order.total
                for order in app_module.Order.query.filter_by(customer_email=email).all()
            )
            assert saved_order_total == 90

            reused_coupon = client.post(
                '/api/coupons/validate',
                json={
                    'customerEmail': email,
                    'couponCode': 'MEALZY70',
                    'items': [{'productId': product.id, 'quantity': 3}],
                },
            )
            assert reused_coupon.status_code == 400
            assert 'first order' in reused_coupon.get_json()['error']
        finally:
            app_module.Order.query.filter_by(customer_email=email).delete(synchronize_session=False)
            app_module.db.session.delete(product)
            app_module.db.session.commit()


def test_customer_email_is_unique_in_database():
    with app_module.app.app_context():
        app_module.ensure_unique_email_indexes()
        inspector = app_module.db.inspect(app_module.db.engine)
        indexes = inspector.get_indexes('customer')
        unique_email_index = any(
            idx['name'] == 'ix_customer_email' and idx.get('unique')
            for idx in indexes
        )
        assert unique_email_index is True


def test_admin_can_update_order_status():
    with app_module.app.app_context():
        product = app_module.Product(
            name='Order Status Test Smoothie',
            category='breakfast',
            description='Fresh mango smoothie',
            price=80,
            unit='per glass',
            stock=15,
            image_url='https://example.com/mango.jpg',
        )
        app_module.db.session.add(product)
        app_module.db.session.commit()

        try:
            order = app_module.Order(
                customer_email='adminstatus@example.com',
                product_name=product.name,
                quantity=1,
                total=80,
                status='Pending',
                address='House 1, City',
                location='Dhaka, Bangladesh',
                payment_method='Cash on Delivery',
            )
            app_module.db.session.add(order)
            app_module.db.session.commit()

            client = app_module.app.test_client()
            response = client.post(
                f'/api/orders/{order.id}/status',
                json={'status': 'Out for Delivery'},
            )

            assert response.status_code == 200
            payload = response.get_json()
            assert payload['status'] == 'Out for Delivery'

            updated_order = app_module.db.session.get(app_module.Order, order.id)
            assert updated_order.status == 'Out for Delivery'
        finally:
            app_module.Order.query.filter_by(
                customer_email='adminstatus@example.com',
                product_name=product.name,
            ).delete(synchronize_session=False)
            app_module.db.session.delete(product)
            app_module.db.session.commit()
