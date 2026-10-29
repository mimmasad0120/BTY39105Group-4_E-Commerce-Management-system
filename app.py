
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import Double, Index, case, text, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from twilio.rest import Client
import smtplib
from email.message import EmailMessage
from pathlib import Path
from html import escape
import importlib
import os
import hashlib
import math
import secrets
import time
import json
import hmac

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
UPLOAD_FOLDER = os.path.join(app.instance_path, "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE CONFIGURATION ----------------

# ---------------- DATABASE CONFIGURATION ----------------
from urllib.parse import quote_plus

db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER", "root")
db_password = quote_plus(os.getenv("DB_PASSWORD", ""))
db_name = os.getenv("DB_NAME", "mealzy_main")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{db_user}:{db_password}"
    f"@{db_host}:{db_port}/{db_name}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

OTP_TTL_SECONDS = 10 * 60


class PendingRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    otp_hash = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(Double, nullable=False)


class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    otp_hash = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(Double, nullable=False)


class DeliveryCompletionOtp(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    delivery_user_id = db.Column(db.Integer, nullable=False)
    otp_hash = db.Column(db.String(128), nullable=False)
    otp_code = db.Column(db.String(6), nullable=True)
    expires_at = db.Column(Double, nullable=False)


class AccountCreationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.Float, nullable=False, default=time.time)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return response

# ---------------- CUSTOMER TABLE ----------------
class Customer(db.Model):
    __tablename__ = "customer"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)


def ensure_unique_email_indexes():
    if db.engine.dialect.name == "sqlite":
        return

    inspector = db.inspect(db.engine)
    table_name = Customer.__tablename__
    indexes = inspector.get_indexes(table_name)
    index_names = {idx["name"] for idx in indexes}

    if "ix_customer_email" not in index_names:
        Index("ix_customer_email", Customer.email, unique=True).create(
            bind=db.engine,
            checkfirst=True,
        )


def ensure_otp_expiry_precision():
    if db.engine.dialect.name != "mysql":
        return

    inspector = db.inspect(db.engine)
    for model in (PendingRegistration, PasswordReset):
        column = next(
            column for column in inspector.get_columns(model.__tablename__)
            if column["name"] == "expires_at"
        )
        column_type = column["type"].compile(dialect=db.engine.dialect).upper()
        if column_type != "DOUBLE":
            table_name = model.__tablename__
            db.session.execute(text(
                f'ALTER TABLE `{table_name}` MODIFY `expires_at` DOUBLE NOT NULL'
            ))
            db.session.commit()
            inspector = db.inspect(db.engine)


# ---------------- ADMIN TABLE ----------------
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class DeliveryUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    last_seen_at = db.Column(db.Float, nullable=True)


DELIVERY_ONLINE_TIMEOUT_SECONDS = 60


def create_delivery_token(delivery_user):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="delivery-auth")
    return serializer.dumps({"delivery_user_id": delivery_user.id})


def get_authenticated_delivery_user():
    scheme, separator, token = request.headers.get("Authorization", "").partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None

    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="delivery-auth")
    try:
        payload = serializer.loads(token, max_age=12 * 60 * 60)
    except BadSignature:
        return None
    if not isinstance(payload, dict):
        return None

    try:
        delivery_user_id = int(payload.get("delivery_user_id"))
    except (TypeError, ValueError):
        return None
    return db.session.get(DeliveryUser, delivery_user_id)


def create_customer_token(customer):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="customer-auth")
    return serializer.dumps({"customer_id": customer.id})


def get_authenticated_customer():
    scheme, separator, token = request.headers.get("Authorization", "").partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None

    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="customer-auth")
    try:
        payload = serializer.loads(token, max_age=12 * 60 * 60)
    except BadSignature:
        return None
    if not isinstance(payload, dict):
        return None

    try:
        customer_id = int(payload.get("customer_id"))
    except (TypeError, ValueError):
        return None
    return db.session.get(Customer, customer_id)


class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(40), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)


class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    customer_email = db.Column(db.String(120), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(40), nullable=False, default="Pending")
    address = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    payment_method = db.Column(db.String(40), nullable=True, default="Cash on Delivery")
    payment_status = db.Column(db.String(30), nullable=False, default="Due")
    payment_utr = db.Column(db.String(22), nullable=True)
    delivery_user_id = db.Column(db.Integer, nullable=True)


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)
    customer_email = db.Column(db.String(120), nullable=False, index=True)
    order_ids_json = db.Column(db.Text, nullable=False)
    amount_paise = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    gateway = db.Column(db.String(30), nullable=False, default="razorpay")
    razorpay_order_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="Created")
    created_at = db.Column(db.Float, nullable=False, default=time.time)
    updated_at = db.Column(db.Float, nullable=False, default=time.time)


class OrderFeedback(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    customer_email = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000), nullable=False, default="")
    created_at = db.Column(db.Float, nullable=False, default=time.time)


def ensure_order_delivery_columns():
    inspector = db.inspect(db.engine)
    columns = [column["name"] for column in inspector.get_columns(Order.__tablename__)]
    identifier_preparer = db.engine.dialect.identifier_preparer
    table_name = identifier_preparer.quote(Order.__tablename__)

    if "address" not in columns:
        column_name = identifier_preparer.quote("address")
        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255)"))
    if "location" not in columns:
        column_name = identifier_preparer.quote("location")
        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255)"))
    if "payment_method" not in columns:
        column_name = identifier_preparer.quote("payment_method")
        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(40)"))
    if "delivery_user_id" not in columns:
        column_name = identifier_preparer.quote("delivery_user_id")
        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER NULL"))
    db.session.commit()


def ensure_delivery_user_presence_column():
    inspector = db.inspect(db.engine)
    columns = {
        column["name"]
        for column in inspector.get_columns(DeliveryUser.__tablename__)
    }
    if "last_seen_at" not in columns:
        preparer = db.engine.dialect.identifier_preparer
        table_name = preparer.quote(DeliveryUser.__tablename__)
        column_name = preparer.quote("last_seen_at")
        db.session.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} DOUBLE NULL"
        ))
        db.session.commit()


def ensure_order_payment_status_column():
    columns = {
        column["name"]
        for column in db.inspect(db.engine).get_columns(Order.__tablename__)
    }
    if "payment_status" not in columns:
        preparer = db.engine.dialect.identifier_preparer
        table_name = preparer.quote(Order.__tablename__)
        column_name = preparer.quote("payment_status")
        db.session.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(30) NOT NULL DEFAULT 'Due'"
        ))
        db.session.execute(text(
            f"UPDATE {table_name} SET {column_name} = 'Pending' "
            "WHERE payment_method IN ('UPI', 'Debit Card', 'Credit Card', 'Net Banking')"
        ))
        db.session.execute(text(
            f"UPDATE {table_name} SET status = 'Pending' "
            "WHERE status = 'Paid' AND payment_method IN ('UPI', 'Debit Card', 'Credit Card', 'Net Banking')"
        ))
        db.session.commit()


def ensure_order_payment_utr_column():
    columns = {
        column["name"]
        for column in db.inspect(db.engine).get_columns(Order.__tablename__)
    }
    if "payment_utr" not in columns:
        preparer = db.engine.dialect.identifier_preparer
        table_name = preparer.quote(Order.__tablename__)
        column_name = preparer.quote("payment_utr")
        db.session.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(22) NULL"
        ))
        db.session.commit()


def ensure_delivery_completion_otp_columns():
    inspector = db.inspect(db.engine)
    columns = {
        column["name"]
        for column in inspector.get_columns(DeliveryCompletionOtp.__tablename__)
    }
    if "otp_code" not in columns:
        preparer = db.engine.dialect.identifier_preparer
        table_name = preparer.quote(DeliveryCompletionOtp.__tablename__)
        column_name = preparer.quote("otp_code")
        db.session.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(6) NULL"
        ))
        db.session.commit()


# ---------------- SEND EMAIL ----------------
def build_otp_email(to_email, subject, heading, otp, description):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_ADDRESS"]
    msg["To"] = to_email
    msg.set_content(
        f"{heading}\n\n{description}\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {OTP_TTL_SECONDS // 60} minutes.\n"
        "If you did not request this code, you can ignore this email."
    )

    safe_heading = escape(heading)
    safe_description = escape(description)
    safe_otp = escape(otp)
    expiration_minutes = OTP_TTL_SECONDS // 60
    html_content = f"""\
<!doctype html>
<html lang="en">
<body style="margin:0;padding:32px 12px;background:#f5f3ed;font-family:Arial,sans-serif;color:#17212b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #ece8dd;border-radius:18px;overflow:hidden;">
    <tr>
      <td style="padding:24px 28px 12px;text-align:center;background:#fffdf7;">
        <img src="cid:mealzy-logo" width="180" alt="Mealzy — Good Food, Delivered" style="display:block;width:180px;max-width:100%;height:auto;margin:0 auto;">
      </td>
    </tr>
    <tr>
      <td style="padding:16px 32px 32px;">
        <p style="margin:0 0 10px;color:#ed7d00;font-size:12px;font-weight:bold;letter-spacing:2px;text-align:center;text-transform:uppercase;">Mealzy secure verification</p>
        <h1 style="margin:0 0 14px;color:#17212b;font-size:24px;line-height:1.3;text-align:center;">{safe_heading}</h1>
        <p style="margin:0 0 22px;color:#52606d;font-size:15px;line-height:1.6;text-align:center;">{safe_description}</p>
        <div style="padding:18px 12px;border:1px solid #f2dfc1;border-radius:12px;background:#fff9ed;color:#18212a;font-size:32px;font-weight:bold;letter-spacing:8px;text-align:center;">{safe_otp}</div>
        <p style="margin:18px 0 0;color:#66717c;font-size:13px;line-height:1.6;text-align:center;">This code expires in {expiration_minutes} minutes. If you did not request it, you can ignore this email.</p>
      </td>
    </tr>
    <tr>
      <td style="padding:16px 24px;background:#17212b;color:#dce5e9;font-size:12px;text-align:center;">Good Food, Delivered</td>
    </tr>
  </table>
</body>
</html>
"""
    msg.add_alternative(html_content, subtype="html")
    html_part = msg.get_payload()[-1]
    logo_path = Path(app.root_path) / "static" / "email" / "mealzy-logo.png"
    html_part.add_related(
        logo_path.read_bytes(),
        maintype="image",
        subtype="png",
        cid="<mealzy-logo>",
        filename="mealzy-logo.png",
        disposition="inline",
    )
    return msg


def send_otp_email(to_email, subject, heading, otp, description):
    msg = build_otp_email(to_email, subject, heading, otp, description)
    for attempt in range(2):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_PASSWORD"])
                server.send_message(msg)
            return
        except (smtplib.SMTPServerDisconnected, TimeoutError, ConnectionError) as error:
            if attempt == 1:
                raise
            app.logger.warning("SMTP connection dropped while sending an OTP email; retrying: %s", error)


def send_email_otp(to_email, otp):
    send_otp_email(
        to_email,
        "Your Mealzy verification code",
        "Verify your email",
        otp,
        "Use this code to finish creating your Mealzy account.",
    )


def send_password_reset_otp(to_email, otp):
    send_otp_email(
        to_email,
        "Your Mealzy password reset code",
        "Reset your password",
        otp,
        "Use this code to reset your Mealzy account password.",
    )


def send_delivery_completion_otp(to_email, otp):
    send_otp_email(
        to_email,
        "Your Mealzy delivery confirmation code",
        "Confirm your delivery",
        otp,
        "Share this code with the delivery staff to confirm that your order has arrived.",
    )


# ---------------- SEND SMS ----------------
def send_sms_otp(phone, otp):
    required = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER")
    credentials = {name: os.getenv(name, "").strip() for name in required}
    if not all(credentials.values()) or any(
        "your_" in value.lower() or "placeholder" in value.lower()
        for value in credentials.values()
    ):
        return False

    client = Client(credentials["TWILIO_ACCOUNT_SID"], credentials["TWILIO_AUTH_TOKEN"])
    client.messages.create(
        body=f"Your Smart Marketplace verification code is {otp}. It expires in 10 minutes.",
        from_=credentials["TWILIO_PHONE_NUMBER"],
        to=phone,
    )
    return True


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return send_from_directory(app.root_path, "hi.html")


@app.route("/hi.html")
def hi_html():
    return send_from_directory(app.root_path, "hi.html")


@app.route("/style.css")
def stylesheet():
    return send_from_directory(app.root_path, "style.css")


@app.route("/script.js")
def javascript():
    return send_from_directory(app.root_path, "script.js")


@app.route("/<path:path>")
def catch_all(path):
    if path.startswith("api/"):
        return jsonify(error="API endpoint not found."), 404
    return send_from_directory(app.root_path, "hi.html")


# ---------------- CUSTOMER REGISTRATION ----------------
@app.route("/api/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    required = ("fullName", "email", "phone", "password", "confirmPassword")
    if any(not str(data.get(field, "")).strip() for field in required):
        return jsonify(error="All registration fields are required."), 400
    if data["password"] != data["confirmPassword"]:
        return jsonify(error="Passwords do not match."), 400

    name = data["fullName"].strip()
    email = data["email"].strip().lower()
    phone = data["phone"].strip()
    existing_customer = Customer.query.filter_by(email=email).first()
    if existing_customer:
        return jsonify(error="Email is already registered."), 409

    otp = f"{secrets.randbelow(1_000_000):06d}"
    registration = PendingRegistration(
        email=email,
        name=name,
        phone=phone,
        password=generate_password_hash(data["password"]),
        otp_hash=hashlib.sha256(otp.encode()).hexdigest(),
        expires_at=time.time() + OTP_TTL_SECONDS,
    )

    try:
        send_email_otp(email, otp)
    except (KeyError, OSError, smtplib.SMTPException, ValueError) as error:
        app.logger.error("Email OTP delivery failed: %s", error)
        return jsonify(error="Could not send the email OTP. Check email settings."), 500

    phone_sent = False
    try:
        phone_sent = send_sms_otp(phone, otp)
    except Exception as error:
        app.logger.warning("SMS OTP delivery skipped: %s", error)

    existing = PendingRegistration.query.filter_by(email=email).first()
    if existing:
        existing.name = registration.name
        existing.phone = registration.phone
        existing.password = registration.password
        existing.otp_hash = registration.otp_hash
        existing.expires_at = registration.expires_at
    else:
        db.session.add(registration)
    db.session.commit()

    channels = ["email"]
    if phone_sent:
        channels.append("phone")
    message = "Email OTP sent."
    if not phone_sent:
        message += " Phone OTP is unavailable until Twilio settings are valid."
    return jsonify(email=email, channels=channels, message=message), 201


@app.route("/api/verify-otp", methods=["POST", "OPTIONS"])
def verify_otp():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    if not email or len(otp) != 6 or not otp.isdigit():
        return jsonify(error="Enter the email and a 6-digit OTP."), 400

    registration = PendingRegistration.query.filter_by(email=email).first()
    if not registration or time.time() > registration.expires_at:
        if registration:
            db.session.delete(registration)
            db.session.commit()
        return jsonify(error="Invalid or expired OTP."), 400

    submitted_hash = hashlib.sha256(otp.encode()).hexdigest()
    if not secrets.compare_digest(registration.otp_hash, submitted_hash):
        return jsonify(error="Invalid or expired OTP."), 400

    db.session.delete(registration)
    db.session.commit()

    new_customer = Customer(
        name=registration.name,
        email=registration.email,
        phone=registration.phone,
        password=registration.password,
    )

    if Customer.query.filter_by(email=email).first():
        return jsonify(error="Email is already registered."), 409

    db.session.add(new_customer)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Email is already registered."), 409

    if not AccountCreationLog.query.filter_by(email=email).first():
        db.session.add(AccountCreationLog(email=email, created_at=time.time()))
        db.session.commit()

    return jsonify(email=email, message="Email verified. Account created."), 200


@app.route("/api/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        return jsonify(error="No customer account was found for that email."), 404

    otp = f"{secrets.randbelow(1_000_000):06d}"
    reset = PasswordReset(
        email=email,
        otp_hash=hashlib.sha256(otp.encode()).hexdigest(),
        expires_at=time.time() + OTP_TTL_SECONDS,
    )

    try:
        send_password_reset_otp(email, otp)
    except (KeyError, OSError, smtplib.SMTPException, ValueError) as error:
        app.logger.error("Password reset email failed: %s", error)
        return jsonify(error="Could not send the password reset email."), 500

    existing = PasswordReset.query.filter_by(email=email).first()
    if existing:
        existing.otp_hash = reset.otp_hash
        existing.expires_at = reset.expires_at
    else:
        db.session.add(reset)
    db.session.commit()
    return jsonify(email=email, message="Password reset OTP sent."), 200


@app.route("/api/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirmPassword", ""))
    if not email or len(otp) != 6 or not otp.isdigit():
        return jsonify(error="Enter the email and a 6-digit OTP."), 400
    if len(password) < 8 or password != confirm_password:
        return jsonify(error="Passwords must match and be at least 8 characters."), 400

    reset = PasswordReset.query.filter_by(email=email).first()
    if not reset or time.time() > reset.expires_at:
        return jsonify(error="Invalid or expired password reset OTP."), 400
    submitted_hash = hashlib.sha256(otp.encode()).hexdigest()
    if not secrets.compare_digest(reset.otp_hash, submitted_hash):
        return jsonify(error="Invalid or expired password reset OTP."), 400

    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        return jsonify(error="Customer account was not found."), 404
    customer.password = generate_password_hash(password)
    db.session.delete(reset)
    db.session.commit()
    return jsonify(message="Password reset successfully."), 200


# ---------------- CUSTOMER LOGIN ----------------
@app.route("/customer-login", methods=["POST", "OPTIONS"])
def customer_login():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify(success=False, message="Enter your email and password."), 400

    customer = Customer.query.filter_by(email=email).first()

    if customer and check_password_hash(customer.password, password):
        return jsonify({
            "success": True,
            "message": "Customer login successful",
            "name": customer.name,
            "token": create_customer_token(customer),
        })

    return jsonify({
        "success": False,
        "message": "Invalid email or password"
    }), 401


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin-login", methods=["POST", "OPTIONS"])
def admin_login():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password")
    if not username or not isinstance(password, str) or not password:
        return jsonify(success=False, message="Enter your username and password."), 400

    admin = Admin.query.filter_by(username=username).first()

    if admin and check_password_hash(admin.password, password):
        return jsonify({
            "success": True,
            "message": "Admin login successful",
            "role": "admin",
        })

    delivery_user = DeliveryUser.query.filter_by(username=username).first()
    if delivery_user and check_password_hash(delivery_user.password, password):
        return jsonify(
            success=True,
            message="Delivery login successful",
            role="delivery",
            name=delivery_user.name,
            token=create_delivery_token(delivery_user),
        )

    return jsonify({
        "success": False,
        "message": "Invalid username or password."
    }), 401


@app.route("/delivery-login", methods=["POST", "OPTIONS"])
def delivery_login():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password")
    if not username or not isinstance(password, str) or not password:
        return jsonify(success=False, message="Enter your delivery username and password."), 400

    delivery_user = DeliveryUser.query.filter_by(username=username).first()
    if delivery_user and check_password_hash(delivery_user.password, password):
        return jsonify(
            success=True,
            message="Delivery login successful",
            name=delivery_user.name,
            token=create_delivery_token(delivery_user),
        )

    return jsonify(success=False, message="Invalid delivery username or password."), 401


@app.route("/api/delivery-users", methods=["GET", "POST", "OPTIONS"])
def delivery_users():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        now = time.time()
        return jsonify(deliveryUsers=[
            {
                "id": delivery_user.id,
                "name": delivery_user.name,
                "username": delivery_user.username,
                "online": (
                    delivery_user.last_seen_at is not None
                    and now - delivery_user.last_seen_at <= DELIVERY_ONLINE_TIMEOUT_SECONDS
                ),
            }
            for delivery_user in DeliveryUser.query.order_by(DeliveryUser.name, DeliveryUser.id).all()
        ])

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    username = str(data.get("username", "")).strip()
    password = data.get("password")
    admin_username = str(data.get("adminUsername", "")).strip()
    admin_password = data.get("adminPassword")
    if not name or not username or not isinstance(password, str) or len(password) < 8:
        return jsonify(error="Enter a name and username, and a password of at least 8 characters."), 400
    admin = Admin.query.filter_by(username=admin_username).first()
    if not admin or not isinstance(admin_password, str) or not check_password_hash(admin.password, admin_password):
        return jsonify(error="Confirm your administrator username and password to create this account."), 401

    delivery_user = DeliveryUser(
        name=name,
        username=username,
        password=generate_password_hash(password),
    )
    db.session.add(delivery_user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="That delivery username is already in use."), 409

    return jsonify(message="Delivery account created successfully.", username=username), 201


@app.route("/api/delivery/presence", methods=["POST", "OPTIONS"])
def update_delivery_presence():
    if request.method == "OPTIONS":
        return "", 204

    delivery_user = get_authenticated_delivery_user()
    if not delivery_user:
        return jsonify(error="Log in with a delivery account to update its online status."), 401

    data = request.get_json(silent=True) or {}
    online = data.get("online")
    if not isinstance(online, bool):
        return jsonify(error="Online status must be true or false."), 400

    delivery_user.last_seen_at = time.time() if online else None
    db.session.commit()
    return jsonify(online=online), 200


@app.route("/api/dashboard-summary", methods=["GET", "OPTIONS"])
def dashboard_summary():
    if request.method == "OPTIONS":
        return "", 204

    customer_count = Customer.query.count()
    account_log_count = AccountCreationLog.query.count()
    return jsonify(
        customers=customer_count,
        accountsCreated=max(customer_count, account_log_count),
        products=Product.query.count(),
        orders=Order.query.count(),
    )


@app.route("/api/admin/feedback", methods=["GET", "OPTIONS"])
def admin_feedback():
    if request.method == "OPTIONS":
        return "", 204

    feedback_rows = db.session.query(OrderFeedback, Order).join(
        Order, Order.id == OrderFeedback.order_id
    ).order_by(OrderFeedback.created_at.desc(), OrderFeedback.order_id.desc()).all()
    rating_total = sum(feedback.rating for feedback, _order in feedback_rows)
    feedback_count = len(feedback_rows)
    return jsonify(
        averageRating=rating_total / feedback_count if feedback_count else 0,
        ratingCount=feedback_count,
        feedback=[
            {
                "orderId": order.id,
                "customerEmail": feedback.customer_email,
                "productName": order.product_name,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "createdAt": feedback.created_at,
            }
            for feedback, order in feedback_rows
        ],
    )


@app.route("/api/customers", methods=["GET", "OPTIONS"])
def list_customers():
    if request.method == "OPTIONS":
        return "", 204

    return jsonify(customers=[
        {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
        }
        for customer in Customer.query.order_by(Customer.id.desc()).all()
    ])


@app.route("/api/customers/<int:customer_id>", methods=["DELETE", "OPTIONS"])
def delete_customer(customer_id):
    if request.method == "OPTIONS":
        return "", 204

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return jsonify(error="Customer not found."), 404

    db.session.delete(customer)
    db.session.commit()
    return jsonify(message="Customer deleted successfully."), 200


@app.route("/api/products", methods=["GET", "POST", "OPTIONS"])
def products():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        return jsonify(products=[
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "price": product.price,
                "unit": product.unit,
                "stock": product.stock,
                "imageUrl": product.image_url,
            }
            for product in Product.query.order_by(Product.id.desc()).all()
        ])

    data = request.form if request.form else (request.get_json(silent=True) or {})
    required = ("name", "category", "description", "price", "unit", "stock")
    if any(not str(data.get(field, "")).strip() for field in required):
        return jsonify(error="All product fields are required."), 400
    image_url = str(data.get("imageUrl", "")).strip() or None
    image = request.files.get("image")
    if image and image.filename:
        extension = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify(error="Upload a JPG, PNG, WEBP, or GIF image."), 400
        safe_name = secure_filename(image.filename)
        unique_name = f"{secrets.token_hex(8)}_{safe_name}"
        image.save(os.path.join(UPLOAD_FOLDER, unique_name))
        image_url = f"/uploads/{unique_name}"

    try:
        product = Product(
            name=str(data["name"]).strip(),
            category=str(data["category"]).strip(),
            description=str(data["description"]).strip(),
            price=float(data["price"]),
            unit=str(data["unit"]).strip(),
            stock=int(data["stock"]),
            image_url=image_url,
        )
    except (TypeError, ValueError):
        return jsonify(error="Price and stock must be valid numbers."), 400
    if product.price < 0 or product.stock < 0:
        return jsonify(error="Price and stock cannot be negative."), 400
    db.session.add(product)
    db.session.commit()
    return jsonify(message="Product added successfully.", product_id=product.id), 201


@app.route("/api/products/<int:product_id>/ratings", methods=["GET", "OPTIONS"])
def product_ratings(product_id):
    if request.method == "OPTIONS":
        return "", 204

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify(error="Product not found."), 404

    feedback_rows = db.session.query(OrderFeedback, Order).join(
        Order, Order.id == OrderFeedback.order_id
    ).filter(
        Order.product_name == product.name
    ).order_by(OrderFeedback.created_at.desc(), OrderFeedback.order_id.desc()).all()
    rating_count = len(feedback_rows)
    rating_total = sum(feedback.rating for feedback, _order in feedback_rows)
    return jsonify(
        productId=product.id,
        averageRating=rating_total / rating_count if rating_count else 0,
        ratingCount=rating_count,
        ratings=[
            {
                "rating": feedback.rating,
                "comment": feedback.comment,
                "createdAt": feedback.created_at,
            }
            for feedback, _order in feedback_rows
        ],
    )


@app.route("/api/products/<int:product_id>", methods=["PUT", "OPTIONS"])
def update_product(product_id):
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Product updates must be sent as JSON."), 400

    fields = ("price", "stock")
    if not any(field in data for field in fields):
        return jsonify(error="Provide a price or stock value to update."), 400

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify(error="Product not found."), 404

    price = data.get("price", product.price)
    stock = data.get("stock", product.stock)
    if isinstance(price, bool) or isinstance(stock, bool):
        return jsonify(error="Price and stock must be valid numbers."), 400
    try:
        price = float(price)
        stock_value = float(stock)
    except (TypeError, ValueError):
        return jsonify(error="Price and stock must be valid numbers."), 400
    if (
        not math.isfinite(price)
        or not math.isfinite(stock_value)
        or price < 0
        or stock_value < 0
        or not stock_value.is_integer()
    ):
        return jsonify(error="Price cannot be negative and stock must be a non-negative whole number."), 400

    product.price = price
    product.stock = int(stock_value)
    db.session.commit()
    return jsonify(
        message="Product updated successfully.",
        product={"id": product.id, "price": product.price, "stock": product.stock},
    ), 200


@app.route("/uploads/<path:filename>")
def uploaded_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


def prepare_order_items(data):
    submitted_items = data.get("items")
    if submitted_items is None:
        submitted_items = [{"productId": data.get("productId"), "quantity": data.get("quantity")}]
    if not isinstance(submitted_items, list) or not submitted_items:
        return None, 0, "Add at least one item to your cart."

    quantities = {}
    for item in submitted_items:
        if not isinstance(item, dict):
            return None, 0, "Cart items are invalid."
        try:
            product_id = int(item.get("productId"))
            quantity = int(item.get("quantity"))
        except (TypeError, ValueError):
            return None, 0, "Cart item quantity is invalid."
        if product_id < 1 or quantity < 1:
            return None, 0, "Cart item quantity is invalid."
        quantities[product_id] = quantities.get(product_id, 0) + quantity

    prepared_items = []
    subtotal = 0
    for product_id, quantity in quantities.items():
        product = db.session.get(Product, product_id)
        if not product or quantity > product.stock:
            return None, 0, "A cart item is unavailable or does not have enough stock."
        prepared_items.append((product, quantity))
        subtotal += product.price * quantity
    return prepared_items, round(subtotal, 2), None


def validate_first_order_coupon(email, coupon_code, subtotal):
    normalized_code = str(coupon_code or "").strip().upper()
    if not normalized_code:
        return {"code": "", "discount": 0, "total": round(subtotal, 2)}, None
    if normalized_code != "MEALZY70":
        return None, "That coupon code is not valid."
    if subtotal <= 200:
        return None, "MEALZY70 requires a cart total above ₹200."
    if Order.query.filter_by(customer_email=email).first():
        return None, "MEALZY70 is only available on your first order."

    discount = round(subtotal * 0.7, 2)
    return {"code": normalized_code, "discount": discount, "total": round(subtotal - discount, 2)}, None


@app.route("/api/coupons/validate", methods=["POST", "OPTIONS"])
def validate_coupon():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("customerEmail", "")).strip().lower()
    if not email:
        return jsonify(error="Customer email is required."), 400
    items, subtotal, error = prepare_order_items(data)
    if error:
        return jsonify(error=error), 400
    coupon, error = validate_first_order_coupon(email, data.get("couponCode"), subtotal)
    if error:
        return jsonify(error=error), 400
    return jsonify(subtotal=subtotal, couponCode=coupon["code"], discount=coupon["discount"], total=coupon["total"]), 200


@app.route("/api/orders", methods=["GET", "POST", "OPTIONS"])
def orders():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        return jsonify(orders=[
            {
                "id": order.id,
                "customerEmail": order.customer_email,
                "productName": order.product_name,
                "quantity": order.quantity,
                "total": order.total,
                "status": order.status,
                "address": order.address or "",
                "location": order.location or "",
                "paymentMethod": order.payment_method or "Cash on Delivery",
                "paymentStatus": order.payment_status,
                "deliveryName": delivery_name,
            }
            for order, delivery_name in db.session.query(
                Order, DeliveryUser.name
            ).outerjoin(
                DeliveryUser, DeliveryUser.id == Order.delivery_user_id
            ).order_by(Order.id.desc()).all()
        ])

    data = request.get_json(silent=True) or {}
    email = str(data.get("customerEmail", "")).strip().lower()
    address = str(data.get("address", "")).strip()
    location = str(data.get("location", "")).strip()
    if not email or not address or not location:
        return jsonify(error="Provide a valid email, delivery address, and delivery location."), 400
    items, subtotal, error = prepare_order_items(data)
    if error:
        return jsonify(error=error), 400
    coupon, error = validate_first_order_coupon(email, data.get("couponCode"), subtotal)
    if error:
        return jsonify(error=error), 400

    payment_method = str(data.get("paymentMethod", "Cash on Delivery")).strip() or "Cash on Delivery"
    if payment_method not in {"Cash on Delivery", "UPI"}:
        return jsonify(error="Choose Cash on Delivery or UPI as the payment method."), 400
    payment_status = "Pending" if payment_method == "UPI" else "Due"
    remaining_total = coupon["total"]
    created_orders = []
    for index, (product, quantity) in enumerate(items):
        line_total = round(product.price * quantity, 2)
        if coupon["code"]:
            if index == len(items) - 1:
                line_total = remaining_total
            else:
                line_total = round(line_total * 0.3, 2)
                remaining_total = round(remaining_total - line_total, 2)
        product.stock -= quantity
        created_orders.append(Order(
            customer_email=email,
            product_name=product.name,
            quantity=quantity,
            total=line_total,
            status="Pending",
            address=address,
            location=location,
            payment_method=payment_method,
            payment_status=payment_status,
        ))
    db.session.add_all(created_orders)
    db.session.commit()
    return jsonify(
        message="Order placed successfully.",
        order_id=created_orders[0].id,
        order_ids=[order.id for order in created_orders],
        subtotal=subtotal,
        discount=coupon["discount"],
        total=coupon["total"],
    ), 201


@app.route("/api/customer/orders", methods=["GET", "OPTIONS"])
def customer_orders():
    if request.method == "OPTIONS":
        return "", 204

    customer = get_authenticated_customer()
    if not customer:
        return jsonify(error="Log in as a customer to view your orders."), 401

    orders = Order.query.filter(
        db.func.lower(Order.customer_email) == customer.email.lower()
    ).order_by(Order.id.desc()).all()
    now = time.time()
    feedback_by_order = {
        feedback.order_id: feedback
        for feedback in OrderFeedback.query.filter(
            OrderFeedback.order_id.in_([order.id for order in orders])
        ).all()
    }
    return jsonify(orders=[
        {
            "id": order.id,
            "customerEmail": order.customer_email,
            "productName": order.product_name,
            "quantity": order.quantity,
            "total": order.total,
            "status": order.status,
            "address": order.address or "",
            "location": order.location or "",
            "paymentMethod": order.payment_method or "Cash on Delivery",
            "paymentStatus": order.payment_status,
            "paymentUtr": order.payment_utr,
            "deliveryOtp": (
                challenge.otp_code
                if (challenge := DeliveryCompletionOtp.query.filter_by(order_id=order.id).first())
                and order.payment_method == "UPI"
                and order.status == "Out for Delivery"
                and challenge.delivery_user_id == order.delivery_user_id
                and challenge.expires_at >= now
                else None
            ),
            "feedback": (
                {
                    "rating": feedback.rating,
                    "comment": feedback.comment,
                    "createdAt": feedback.created_at,
                }
                if (feedback := feedback_by_order.get(order.id))
                else None
            ),
        }
        for order in orders
    ])


@app.route("/api/customer/orders/<int:order_id>/feedback", methods=["POST", "OPTIONS"])
def save_customer_order_feedback(order_id):
    if request.method == "OPTIONS":
        return "", 204

    customer = get_authenticated_customer()
    if not customer:
        return jsonify(error="Log in as a customer to leave order feedback."), 401

    order = Order.query.filter(
        Order.id == order_id,
        db.func.lower(Order.customer_email) == customer.email.lower(),
    ).first()
    if not order:
        return jsonify(error="Order not found."), 404
    if order.status != "Delivered":
        return jsonify(error="Feedback is available after an order is delivered."), 409

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Feedback details are required."), 400

    rating = data.get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        return jsonify(error="Choose a rating from 1 to 5 stars."), 400
    comment = data.get("comment", "")
    if not isinstance(comment, str):
        return jsonify(error="Feedback comment must be text."), 400
    comment = comment.strip()
    if len(comment) > 1000:
        return jsonify(error="Feedback comment must be 1000 characters or fewer."), 400

    feedback = db.session.get(OrderFeedback, order.id)
    if feedback is None:
        feedback = OrderFeedback(order_id=order.id, customer_email=customer.email)
        db.session.add(feedback)
    feedback.rating = rating
    feedback.comment = comment
    feedback.created_at = time.time()
    db.session.commit()
    return jsonify(
        message="Your feedback has been saved.",
        feedback={
            "rating": feedback.rating,
            "comment": feedback.comment,
            "createdAt": feedback.created_at,
        },
    ), 200


def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        return None, None, None
    try:
        razorpay = importlib.import_module("razorpay")
    except ImportError:
        return None, key_id, key_secret
    return razorpay.Client(auth=(key_id, key_secret)), key_id, key_secret


def get_customer_orders_for_payment(customer, order_ids):
    if not isinstance(order_ids, list) or not order_ids:
        return None, "Choose at least one order to pay."
    if len(order_ids) > 50 or any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in order_ids
    ):
        return None, "The order details are invalid."
    unique_ids = list(dict.fromkeys(order_ids))
    orders = Order.query.filter(
        Order.id.in_(unique_ids),
        db.func.lower(Order.customer_email) == customer.email.lower(),
    ).all()
    if len(orders) != len(unique_ids):
        return None, "One or more orders could not be found."
    if any(order.payment_method != "UPI" for order in orders):
        return None, "Only UPI orders can be paid through Razorpay."
    if any(order.payment_status == "Confirmed" for order in orders):
        return None, "One or more orders are already paid."
    return sorted(orders, key=lambda order: order.id), None


@app.route("/api/payments/razorpay/create-order", methods=["POST", "OPTIONS"])
def create_razorpay_order():
    if request.method == "OPTIONS":
        return "", 204
    customer = get_authenticated_customer()
    if not customer:
        return jsonify(error="Log in as a customer before paying."), 401
    client, key_id, key_secret = get_razorpay_client()
    if client is None:
        if key_id is None:
            return jsonify(error="Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to your .env file."), 503
        return jsonify(error="Install the Razorpay Python package using: py -m pip install razorpay"), 503

    data = request.get_json(silent=True) or {}
    orders, error = get_customer_orders_for_payment(customer, data.get("orderIds"))
    if error:
        return jsonify(error=error), 400

    # Never trust a total sent by the browser; calculate it from MySQL order rows.
    amount_paise = int(round(sum(float(order.total) for order in orders) * 100))
    if amount_paise <= 0:
        return jsonify(error="The payment amount must be greater than zero."), 400

    try:
        gateway_order = client.order.create(data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"mealzy-{orders[0].id}-{int(time.time())}",
            "notes": {
                "customer_email": customer.email[:255],
                "mealzy_order_ids": ",".join(str(order.id) for order in orders)[:500],
            },
        })
        transaction = PaymentTransaction(
            customer_email=customer.email,
            order_ids_json=json.dumps([order.id for order in orders]),
            amount_paise=amount_paise,
            currency="INR",
            gateway="razorpay",
            razorpay_order_id=gateway_order["id"],
            status="Created",
        )
        db.session.add(transaction)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not create Razorpay order")
        return jsonify(error="Could not start the payment. Please try again."), 502

    return jsonify(
        keyId=key_id,
        razorpayOrderId=gateway_order["id"],
        amount=amount_paise,
        currency="INR",
        customerName=customer.name,
        customerEmail=customer.email,
        message="Payment order created.",
    ), 201


@app.route("/api/payments/razorpay/verify", methods=["POST", "OPTIONS"])
def verify_razorpay_payment():
    if request.method == "OPTIONS":
        return "", 204
    customer = get_authenticated_customer()
    if not customer:
        return jsonify(error="Log in as a customer before verifying payment."), 401

    data = request.get_json(silent=True) or {}
    gateway_order_id = str(data.get("razorpay_order_id", "")).strip()
    payment_id = str(data.get("razorpay_payment_id", "")).strip()
    signature = str(data.get("razorpay_signature", "")).strip()
    if not gateway_order_id or not payment_id or not signature:
        return jsonify(error="The payment response is incomplete."), 400

    transaction = PaymentTransaction.query.filter_by(
        razorpay_order_id=gateway_order_id,
        customer_email=customer.email,
    ).first()
    if not transaction:
        return jsonify(error="Payment order not found for this account."), 404
    if transaction.status == "Paid" and transaction.razorpay_payment_id == payment_id:
        return jsonify(message="Payment already verified.", paymentStatus="Confirmed"), 200

    client, key_id, key_secret = get_razorpay_client()
    if not client or not key_secret:
        return jsonify(error="Razorpay is not configured on the server."), 503
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": gateway_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        payment = client.payment.fetch(payment_id)
        if payment.get("order_id") != gateway_order_id:
            return jsonify(error="The payment does not match this order."), 400
        if int(payment.get("amount", -1)) != transaction.amount_paise:
            return jsonify(error="The payment amount does not match the order total."), 400
        if payment.get("currency") != transaction.currency:
            return jsonify(error="The payment currency does not match."), 400
        # Signature can be returned before capture; only mark paid after captured/authorized
        # payment is captured. Auto-capture should be enabled in the Razorpay account.
        if payment.get("status") != "captured":
            transaction.status = "Authorized" if payment.get("status") == "authorized" else "Pending"
            transaction.updated_at = time.time()
            db.session.commit()
            return jsonify(error="Payment is not captured yet. Please wait and refresh your orders."), 409
    except Exception:
        app.logger.exception("Razorpay payment signature/API verification failed")
        return jsonify(error="Payment verification failed. No order was marked as paid."), 400

    order_ids = json.loads(transaction.order_ids_json)
    orders = Order.query.filter(
        Order.id.in_(order_ids),
        db.func.lower(Order.customer_email) == customer.email.lower(),
    ).all()
    if len(orders) != len(set(order_ids)):
        return jsonify(error="The linked Mealzy order records could not be found."), 409
    transaction.razorpay_payment_id = payment_id
    transaction.status = "Paid"
    transaction.updated_at = time.time()
    for order in orders:
        order.payment_status = "Confirmed"
        order.payment_utr = None
    db.session.commit()
    return jsonify(message="Payment verified successfully.", paymentStatus="Confirmed"), 200


@app.route("/api/payments/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return jsonify(error="Webhook secret is not configured."), 503
    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = request.get_data(cache=True)
    expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        return jsonify(error="Invalid webhook signature."), 400
    try:
        event = request.get_json(force=True)
        event_name = event.get("event")
        payload = event.get("payload", {})
        payment_entity = (payload.get("payment") or {}).get("entity") or {}
        order_entity = (payload.get("order") or {}).get("entity") or {}
        gateway_order_id = payment_entity.get("order_id") or order_entity.get("id")
        payment_id = payment_entity.get("id")
        if event_name in {"payment.captured", "order.paid"} and gateway_order_id:
            transaction = PaymentTransaction.query.filter_by(
                razorpay_order_id=gateway_order_id
            ).first()
            if transaction and transaction.status != "Paid":
                if event_name == "payment.captured":
                    if (
                        payment_entity.get("status") != "captured"
                        or int(payment_entity.get("amount", -1)) != transaction.amount_paise
                        or payment_entity.get("currency") != transaction.currency
                    ):
                        return jsonify(error="Captured payment does not match transaction."), 400
                    transaction.razorpay_payment_id = payment_id
                elif event_name == "order.paid":
                    # Verify the associated payment is captured before applying an order.paid event.
                    if payment_entity and payment_entity.get("status") == "captured":
                        transaction.razorpay_payment_id = payment_id
                    else:
                        return jsonify(message="Order-paid event received; awaiting captured payment event."), 200
                transaction.status = "Paid"
                transaction.updated_at = time.time()
                order_ids = json.loads(transaction.order_ids_json)
                orders = Order.query.filter(Order.id.in_(order_ids)).all()
                for order in orders:
                    if order.customer_email.lower() == transaction.customer_email.lower():
                        order.payment_status = "Confirmed"
                        order.payment_utr = None
                db.session.commit()
        elif event_name == "payment.failed" and gateway_order_id:
            transaction = PaymentTransaction.query.filter_by(
                razorpay_order_id=gateway_order_id
            ).first()
            if transaction and transaction.status != "Paid":
                transaction.status = "Failed"
                transaction.updated_at = time.time()
                db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not process Razorpay webhook")
        return jsonify(error="Webhook processing failed."), 500
    return jsonify(message="Webhook processed."), 200


@app.route("/api/customer/orders/payment", methods=["POST", "OPTIONS"])
def confirm_customer_order_payment():
    if request.method == "OPTIONS":
        return "", 204

    customer = get_authenticated_customer()
    if not customer:
        return jsonify(error="Log in as a customer to confirm UPI payments."), 401

    data = request.get_json(silent=True) or {}
    order_ids = data.get("orderIds")
    if not isinstance(order_ids, list) or not order_ids:
        return jsonify(error="Select at least one order to confirm."), 400
    if len(order_ids) > 50 or any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in order_ids
    ):
        return jsonify(error="The order details are invalid."), 400

    unique_ids = list(dict.fromkeys(order_ids))
    orders = Order.query.filter(
        Order.id.in_(unique_ids),
        db.func.lower(Order.customer_email) == customer.email.lower(),
    ).all()
    if len(orders) != len(unique_ids):
        return jsonify(error="One or more orders could not be found."), 404
    if any(order.payment_method != "UPI" for order in orders):
        return jsonify(error="Only UPI orders can be confirmed with a payment UTR."), 400
    if any(order.payment_status == "Confirmed" for order in orders):
        return jsonify(error="One or more orders are already confirmed as paid."), 409

    utr = str(data.get("utr", "")).strip()
    if not utr or len(utr) < 12 or len(utr) > 22 or not utr.isalnum():
        return jsonify(error="Enter a valid UPI transaction reference (UTR)."), 400

    for order in orders:
        order.payment_status = "Confirmed"
        order.payment_utr = utr

    db.session.commit()
    return jsonify(message="Payment confirmed successfully.", paymentStatus="Confirmed"), 200


@app.route("/api/orders/<int:order_id>/status", methods=["POST", "OPTIONS"])
def update_order_status(order_id):
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip()
    allowed_statuses = ["Pending", "Processing", "Out for Delivery", "Delivered", "Cancelled"]
    if status not in allowed_statuses:
        return jsonify(error="Invalid order status."), 400

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found."), 404

    order.status = status
    db.session.commit()
    return jsonify(message="Order status updated successfully.", status=order.status), 200


@app.route("/api/delivery/orders", methods=["GET", "OPTIONS"])
def delivery_orders():
    if request.method == "OPTIONS":
        return "", 204
    delivery_user = get_authenticated_delivery_user()
    if not delivery_user:
        return jsonify(error="Log in with a delivery account to view delivery orders."), 401

    orders = Order.query.filter(
        db.or_(
            db.and_(
                Order.status.in_(["Pending", "Processing", "Out for Delivery"]),
                db.or_(Order.delivery_user_id.is_(None), Order.delivery_user_id == delivery_user.id),
            ),
            db.and_(
                Order.status == "Delivered",
                Order.delivery_user_id == delivery_user.id,
            ),
        ),
    ).order_by(Order.id.desc()).all()
    return jsonify(orders=[
        {
            "id": order.id,
            "customerEmail": order.customer_email,
            "productName": order.product_name,
            "quantity": order.quantity,
            "total": order.total,
            "status": order.status,
            "address": order.address or "",
            "location": order.location or "",
            "paymentMethod": order.payment_method or "Cash on Delivery",
            "paymentStatus": order.payment_status,
            "paymentReady": order.payment_method != "UPI" or order.payment_status == "Confirmed",
            "accepted": order.delivery_user_id == delivery_user.id,
        }
        for order in orders
    ])


@app.route("/api/delivery/orders/<int:order_id>/accept", methods=["POST", "OPTIONS"])
def accept_delivery_order(order_id):
    if request.method == "OPTIONS":
        return "", 204
    delivery_user = get_authenticated_delivery_user()
    if not delivery_user:
        return jsonify(error="Log in with a delivery account to accept orders."), 401

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found."), 404
    if order.delivery_user_id == delivery_user.id:
        return jsonify(message="You have already accepted this order.", status=order.status), 200
    if order.delivery_user_id is not None:
        return jsonify(error="This order has already been accepted by another delivery user."), 409
    if order.status not in {"Pending", "Processing", "Out for Delivery"}:
        return jsonify(error="This order is no longer available for delivery."), 409
    if order.payment_method == "UPI" and order.payment_status != "Confirmed":
        return jsonify(error="Confirm UPI payment before accepting this order."), 409

    result = db.session.execute(
        update(Order)
        .where(
            Order.id == order_id,
            Order.delivery_user_id.is_(None),
            Order.status.in_(["Pending", "Processing", "Out for Delivery"]),
        )
        .values(
            delivery_user_id=delivery_user.id,
            status=case((Order.status == "Pending", "Processing"), else_=Order.status),
        )
    )
    if result.rowcount != 1:
        db.session.rollback()
        return jsonify(error="This order has already been accepted by another delivery user."), 409
    db.session.commit()
    order = db.session.get(Order, order_id)
    return jsonify(message="Order accepted successfully.", status=order.status), 200


@app.route("/api/delivery/orders/<int:order_id>/delivery-otp", methods=["POST", "OPTIONS"])
def send_delivery_completion_code(order_id):
    if request.method == "OPTIONS":
        return "", 204
    delivery_user = get_authenticated_delivery_user()
    if not delivery_user:
        return jsonify(error="Log in with a delivery account to request a delivery code."), 401

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found."), 404
    if order.delivery_user_id != delivery_user.id:
        return jsonify(error="Accept this order before requesting a delivery code."), 403
    if order.status != "Out for Delivery":
        return jsonify(error="The order must be out for delivery before requesting a completion code."), 409
    if order.payment_method != "UPI":
        challenge = DeliveryCompletionOtp.query.filter_by(order_id=order.id).first()
        if challenge:
            db.session.delete(challenge)
            db.session.commit()
        return jsonify(error="Cash on Delivery orders do not require a delivery confirmation code."), 409
    if not order.customer_email:
        return jsonify(error="This order does not have a customer email for verification."), 400

    otp = f"{secrets.randbelow(1_000_000):06d}"
    challenge = DeliveryCompletionOtp.query.filter_by(order_id=order.id).first()
    if challenge is None:
        challenge = DeliveryCompletionOtp(order_id=order.id, delivery_user_id=delivery_user.id)
        db.session.add(challenge)
    challenge.delivery_user_id = delivery_user.id
    challenge.otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    challenge.otp_code = otp
    challenge.expires_at = time.time() + OTP_TTL_SECONDS
    db.session.commit()

    return jsonify(
        message="Ask the customer for the confirmation code shown in their My Orders section."
    ), 200


@app.route("/api/delivery/orders/<int:order_id>/status", methods=["POST", "OPTIONS"])
def update_delivery_order_status(order_id):
    if request.method == "OPTIONS":
        return "", 204
    delivery_user = get_authenticated_delivery_user()
    if not delivery_user:
        return jsonify(error="Log in with a delivery account to update delivery orders."), 401

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip()
    allowed_transitions = {
        "Processing": {"Out for Delivery", "Cancelled"},
        "Out for Delivery": {"Delivered", "Cancelled"},
    }

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found."), 404
    if order.delivery_user_id != delivery_user.id:
        return jsonify(error="Accept this order before updating its status."), 403
    if status not in allowed_transitions.get(order.status, set()):
        return jsonify(error=f"Cannot change an order from {order.status} to {status or 'an empty status'}."), 400

    if status == "Delivered" and order.payment_method == "UPI":
        otp = str(data.get("otp", "")).strip()
        if len(otp) != 6 or not otp.isdigit():
            return jsonify(error="Enter the 6-digit code shown in the customer's My Orders."), 400
        challenge = DeliveryCompletionOtp.query.filter_by(order_id=order.id).first()
        submitted_hash = hashlib.sha256(otp.encode()).hexdigest()
        if (
            not challenge
            or challenge.delivery_user_id != delivery_user.id
            or time.time() > challenge.expires_at
            or not secrets.compare_digest(challenge.otp_hash, submitted_hash)
        ):
            return jsonify(error="Invalid or expired delivery confirmation code."), 400
        db.session.delete(challenge)
    elif status in {"Delivered", "Cancelled"}:
        challenge = DeliveryCompletionOtp.query.filter_by(order_id=order.id).first()
        if challenge:
            db.session.delete(challenge)

    order.status = status
    db.session.commit()
    return jsonify(message="Order status updated successfully.", status=order.status), 200


# ---------------- CREATE DATABASE ----------------
with app.app_context():
    db.create_all()
    ensure_otp_expiry_precision()
    ensure_unique_email_indexes()
    ensure_order_delivery_columns()
    ensure_delivery_user_presence_column()
    ensure_order_payment_status_column()
    ensure_order_payment_utr_column()
    ensure_delivery_completion_otp_columns()

    sample_products = [
        ("Paneer Paratha", "breakfast", "Stuffed paratha with paneer and a side of fresh curd.", 90.00, "per plate", 30, "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80"),
        ("Masala Omelette", "breakfast", "Fluffy omelette cooked with onions, tomatoes, and spices.", 75.00, "per plate", 28, "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=600&q=80"),
        ("Poha", "breakfast", "Light and savoury flattened rice with peas, peanuts, and curry leaves.", 55.00, "per plate", 32, "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=600&q=80"),
        ("Fruit Bowl", "breakfast", "Fresh seasonal fruits with yogurt and honey drizzle.", 95.00, "per bowl", 24, "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Sandwich", "lunch", "Grilled chicken, lettuce, and creamy sauce in toasted bread.", 120.00, "per sandwich", 26, "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=600&q=80"),
        ("Veg Biryani", "lunch", "Aromatic rice with vegetables, herbs, and rich biryani masala.", 155.00, "per plate", 22, "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80"),
        ("Paneer Butter Masala", "lunch", "Creamy tomato gravy with soft paneer cubes and warm naan.", 180.00, "per plate", 25, "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Burger", "lunch", "Juicy grilled chicken with fresh lettuce and sauce.", 85.00, "per burger", 35, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80"),
        ("Margherita Pizza", "dinner", "Stone-baked pizza with tomato, basil, and mozzarella.", 220.00, "per pizza", 20, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80"),
        ("Farmhouse Pizza", "dinner", "Stone-baked pizza topped with capsicum, onion, sweet corn, and mushrooms.", 260.00, "per pizza", 18, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80"),
        ("Paneer Tikka Pizza", "dinner", "Mozzarella pizza topped with smoky paneer tikka, peppers, and onions.", 280.00, "per pizza", 16, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Tikka Pizza", "dinner", "Baked pizza with spiced chicken tikka, mozzarella, and a tangy sauce.", 295.00, "per pizza", 15, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80"),
        ("Steamed Veg Momos", "lunch", "Soft steamed dumplings filled with seasoned vegetables, served with chutney.", 110.00, "per plate", 24, "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Momos", "lunch", "Juicy chicken-filled dumplings served with a spicy tomato dipping sauce.", 140.00, "per plate", 22, "https://images.unsplash.com/photo-1625220194771-7ebdea0b70b9?auto=format&fit=crop&w=600&q=80"),
        ("Tandoori Paneer Momos", "dinner", "Paneer momos tossed in smoky tandoori spices and finished with fresh herbs.", 155.00, "per plate", 18, "https://plus.unsplash.com/premium_photo-1673769108070-580fe90b8de7?auto=format&fit=crop&w=600&q=80"),
        ("Dada Boudi Chicken Biryani", "dinner", "Kolkata-style chicken biryani with fragrant rice, a tender chicken piece, and potato.", 230.00, "per plate", 18, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"),
        ("D-Bapi Special Biryani", "dinner", "A hearty dum biryani layered with aromatic basmati rice, spices, and your choice of chicken-style seasoning.", 220.00, "per plate", 18, "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80"),
        ("Wow! Momo Veg Momos", "lunch", "Steamed vegetable dumplings served with a bold, spicy tomato chutney.", 120.00, "per plate", 24, "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=600&q=80"),
        ("Wow! Momo Chicken Momos", "lunch", "Juicy chicken-filled dumplings served steamed with a spicy dipping sauce.", 150.00, "per plate", 22, "https://images.unsplash.com/photo-1496116218417-1a781b1c416c?auto=format&fit=crop&w=600&q=80"),
        ("Butter Chicken", "dinner", "Rich tomato gravy with tender chicken and a buttery finish.", 210.00, "per plate", 18, "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80"),
        ("Grilled Salmon", "dinner", "Perfectly grilled salmon fillet with lemon herbs and vegetables.", 260.00, "per plate", 16, "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Biryani", "dinner", "Fragrant basmati rice layered with spiced chicken.", 180.00, "per plate", 30, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"),
        ("Egg Biryani", "lunch", "Fragrant basmati rice layered with boiled eggs, caramelized onions, and biryani spices.", 160.00, "per plate", 22, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"),
        ("Paneer Biryani", "dinner", "Aromatic dum-cooked basmati rice with paneer, herbs, and warming spices.", 175.00, "per plate", 20, "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80"),
        ("Kolkata Chicken Biryani", "dinner", "Kolkata-style biryani with fragrant rice, tender chicken, potato, and subtle spices.", 210.00, "per plate", 18, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80"),
        ("Penne Arrabbiata", "lunch", "Penne pasta tossed in a lively tomato, garlic, and chilli sauce.", 190.00, "per plate", 18, "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=600&q=80"),
        ("Veg Hakka Noodles", "lunch", "Wok-tossed noodles with crunchy vegetables and savoury Indo-Chinese seasoning.", 150.00, "per plate", 20, "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=600&q=80"),
        ("Masala Dosa", "breakfast", "Crisp rice crepe filled with spiced potato and served with chutneys and sambar.", 110.00, "per plate", 24, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80"),
        ("Samosa Chaat", "lunch", "Crisp samosas topped with chickpeas, yogurt, chutneys, and crunchy sev.", 95.00, "per plate", 20, "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80"),
        ("Pani Puri", "lunch", "Crisp puris served with tangy spiced water, potatoes, and chickpeas.", 70.00, "per plate", 30, "https://images.unsplash.com/photo-1601050690117-94f5f6fa8bd7?auto=format&fit=crop&w=600&q=80"),
        ("Paneer Tikka", "dinner", "Char-grilled paneer and peppers marinated in smoky Indian spices.", 190.00, "per portion", 18, "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80"),
        ("Dal Makhani", "dinner", "Slow-cooked black lentils finished with butter, cream, and warming spices.", 170.00, "per plate", 20, "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Kathi Roll", "lunch", "Spiced grilled chicken wrapped in a flaky paratha with onion and chutney.", 145.00, "per roll", 22, "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80"),
        ("Chilli Paneer", "dinner", "Crispy paneer tossed with peppers, onion, and a savoury Indo-Chinese sauce.", 180.00, "per plate", 18, "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Fried Rice", "dinner", "Wok-fried rice with tender chicken, egg, vegetables, and spring onion.", 175.00, "per plate", 20, "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=600&q=80"),
        ("Gulab Jamun", "dinner", "Soft milk dumplings soaked in fragrant cardamom and rose sugar syrup.", 80.00, "2 pieces", 30, "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80"),
        ("Chocolate Brownie", "dinner", "Rich chocolate brownie with a soft centre and crisp, fudgy edges.", 95.00, "per piece", 24, "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80"),
        ("Mango Lassi", "breakfast", "Cool yogurt drink blended with ripe mango and a hint of cardamom.", 85.00, "per glass", 24, "https://images.unsplash.com/photo-1626200419199-391ae4be7a41?auto=format&fit=crop&w=600&q=80"),
        ("Strawberry Milkshake", "breakfast", "Creamy chilled milkshake blended with strawberries.", 100.00, "per glass", 20, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=600&q=80"),
        ("French Fries", "dinner", "Crispy golden fries served hot and fresh.", 40.00, "per plate", 50, "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=600&q=80"),
        ("Loaded Nachos", "dinner", "Crispy nachos topped with cheese, salsa, and spicy flavours.", 95.00, "per plate", 25, "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=600&q=80"),
        ("Chocolate Cake", "dinner", "Rich, soft chocolate cake with creamy frosting.", 120.00, "per slice", 25, "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=600&q=80"),
        ("Chicken Wings", "dinner", "Juicy, crispy chicken wings tossed in a delicious spicy glaze.", 160.00, "per portion", 20, "https://images.unsplash.com/photo-1527477396000-e27163b481c2?auto=format&fit=crop&w=600&q=80"),
        ("Quick Bite Combo", "lunch", "Chicken burger with crispy fries and a refreshing drink.", 99.00, "per combo", 30, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80"),
        ("Mini Margherita Pizza", "lunch", "A personal-size tomato and mozzarella pizza, baked until golden.", 99.00, "per pizza", 20, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80"),
        ("Veg Momo Snack Plate", "lunch", "A snack plate of steamed vegetable momos served with spicy tomato chutney.", 99.00, "per plate", 24, "https://plus.unsplash.com/premium_photo-1673769108568-e2125b011ac6?auto=format&fit=crop&w=600&q=80"),
        ("Paneer Kathi Roll", "lunch", "Spiced paneer wrapped in a flaky paratha with onion and tangy chutney.", 99.00, "per roll", 22, "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80"),
        ("Masala Fries", "dinner", "Crispy golden fries tossed with a punchy house-style masala.", 99.00, "per plate", 30, "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=600&q=80"),
        ("Mini Veg Biryani", "lunch", "A smaller serving of fragrant vegetable biryani with aromatic basmati rice.", 99.00, "per plate", 20, "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80"),
        ("Hearty Meal Combo", "dinner", "Spiced rice, a savoury side, and a refreshing drink.", 199.00, "per combo", 25, "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80"),
    ]
    existing_product_names = {product.name for product in Product.query.all()}
    missing_products = [
        Product(name=name, category=category, description=description,
                price=price, unit=unit, stock=stock, image_url=image_url)
        for name, category, description, price, unit, stock, image_url in sample_products
        if name not in existing_product_names
    ]
    if missing_products:
        db.session.add_all(missing_products)
        db.session.commit()

    momo_image_by_name = {
        name: image_url
        for name, _, _, _, _, _, image_url in sample_products
        if "momo" in name.lower()
    }
    for product in Product.query.filter(Product.name.in_(momo_image_by_name)).all():
        product.image_url = momo_image_by_name[product.name]

    for product in Product.query.filter_by(name="Gulab Jamun").all():
        if product.image_url == "https://images.unsplash.com/photo-1666190092159-84a6c49d35c6?auto=format&fit=crop&w=600&q=80":
            product.image_url = "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80"
    db.session.commit()

    for product in Product.query.filter_by(name="Classic Chicken Wrap", category="99").all():
        db.session.delete(product)
    db.session.commit()

    category_overrides = {
        "Paneer Paratha": "breakfast",
        "Masala Omelette": "breakfast",
        "Poha": "breakfast",
        "Fruit Bowl": "breakfast",
        "Chicken Sandwich": "lunch",
        "Veg Biryani": "lunch",
        "Paneer Butter Masala": "lunch",
        "Chicken Burger": "lunch",
        "Margherita Pizza": "dinner",
        "Butter Chicken": "dinner",
        "Grilled Salmon": "dinner",
        "Chicken Biryani": "dinner",
        "French Fries": "dinner",
        "Loaded Nachos": "dinner",
        "Chocolate Cake": "dinner",
        "Chicken Wings": "dinner",
    }
    for product in Product.query.all():
        if product.name in category_overrides:
            product.category = category_overrides[product.name]
    db.session.commit()

    # Create default admin if not exists
    if not Admin.query.filter_by(username="admin").first():
        default_admin = Admin(
            username="admin",
            password=generate_password_hash("Admin@123")
        )
        db.session.add(default_admin)
        db.session.commit()

        print("Default admin created")

    permanent_admin_username = "mealzy0120@gmail.com"
    if not Admin.query.filter_by(username=permanent_admin_username).first():
        permanent_admin = Admin(
            username=permanent_admin_username,
            password=generate_password_hash("Mealzy@786")
        )
        db.session.add(permanent_admin)
        db.session.commit()
        print("Permanent admin created")

@app.route("/payment")
def payment_page():
    return send_from_directory(app.root_path, "payment.html")
# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

  