"""
scripts/seeds/seed_demo_orders.py — Seed sample orders across various statuses.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from stores.models.store_mod import Store
from products.models.product_mod import Product
from orders.models.order_mod import Order, OrderItem, OrderStatus, FulfillmentType, PaymentStatus, PaymentMethod

User = get_user_model()


def run():
    print("  Seeding demo orders for Fresh Fields Market...")
    vendor = User.objects.filter(email="vendor_saved@test.com").first()
    customer = User.objects.filter(email="customer_a_saved@test.com").first()
    store = Store.objects.filter(id=1).first()

    if not vendor or not customer or not store:
        print("  ❌ Prerequisite models missing.")
        return

    products = list(Product.objects.filter(store=store)[:4])
    if not products:
        print("  ❌ No products found for store.")
        return

    now = timezone.now()

    # Order 1: Submitted (Current / Incoming pending order)
    p1 = products[0]
    p2 = products[1] if len(products) > 1 else products[0]
    sub1 = (p1.price * 2) + p2.price
    fee1 = Decimal("5.00")
    o1, created1 = Order.objects.get_or_create(
        order_number="SM-2026-1001",
        defaults={
            "customer": customer,
            "vendor": vendor,
            "store": store,
            "status": OrderStatus.SUBMITTED,
            "fulfillment_type": FulfillmentType.DELIVERY,
            "delivery_address": "123 Maple Street, Apt 4B, Springfield",
            "customer_phone_snapshot": "+1 (555) 123-4567",
            "subtotal": sub1,
            "delivery_fee": fee1,
            "total_amount": sub1 + fee1,
            "payment_method": PaymentMethod.COD,
            "payment_status": PaymentStatus.PENDING,
            "notes": "Please leave at front door if no answer.",
        }
    )
    if created1:
        OrderItem.objects.create(order=o1, product=p1, product_name_snapshot=p1.name, unit_price_snapshot=p1.price, quantity=2, line_total=p1.price * 2)
        OrderItem.objects.create(order=o1, product=p2, product_name_snapshot=p2.name, unit_price_snapshot=p2.price, quantity=1, line_total=p2.price)

    # Order 2: Accepted (In preparation)
    p3 = products[2] if len(products) > 2 else products[0]
    sub2 = p3.price * 3
    fee2 = Decimal("5.00")
    o2, created2 = Order.objects.get_or_create(
        order_number="SM-2026-1002",
        defaults={
            "customer": customer,
            "vendor": vendor,
            "store": store,
            "status": OrderStatus.ACCEPTED,
            "fulfillment_type": FulfillmentType.DELIVERY,
            "delivery_address": "742 Evergreen Terrace, Springfield",
            "customer_phone_snapshot": "+1 (555) 999-8877",
            "subtotal": sub2,
            "delivery_fee": fee2,
            "total_amount": sub2 + fee2,
            "payment_method": PaymentMethod.COD,
            "payment_status": PaymentStatus.PENDING,
            "accepted_at": now,
            "notes": "Fragile organic produce, handle with care.",
        }
    )
    if created2:
        OrderItem.objects.create(order=o2, product=p3, product_name_snapshot=p3.name, unit_price_snapshot=p3.price, quantity=3, line_total=p3.price * 3)

    # Order 3: Out for Delivery (Delivery order with driver)
    sub3 = p1.price + p3.price
    fee3 = Decimal("5.00")
    o3, created3 = Order.objects.get_or_create(
        order_number="SM-2026-1003",
        defaults={
            "customer": customer,
            "vendor": vendor,
            "store": store,
            "status": OrderStatus.OUT_FOR_DELIVERY,
            "fulfillment_type": FulfillmentType.DELIVERY,
            "delivery_address": "456 Oak Ave, Springfield",
            "customer_phone_snapshot": "+1 (555) 321-7654",
            "subtotal": sub3,
            "delivery_fee": fee3,
            "total_amount": sub3 + fee3,
            "payment_method": PaymentMethod.COD,
            "payment_status": PaymentStatus.PENDING,
            "accepted_at": now,
            "preparing_at": now,
            "dispatched_at": now,
            "delivery_person_name": "Mike Rider",
            "delivery_person_phone": "+1 (555) 444-3322",
            "delivery_vehicle_type": "Motorcycle",
            "delivery_tracking_notes": "Departed store 10 mins ago.",
        }
    )
    if created3:
        OrderItem.objects.create(order=o3, product=p1, product_name_snapshot=p1.name, unit_price_snapshot=p1.price, quantity=1, line_total=p1.price)
        OrderItem.objects.create(order=o3, product=p3, product_name_snapshot=p3.name, unit_price_snapshot=p3.price, quantity=1, line_total=p3.price)

    # Order 4: Completed (In-Store Walk-In handover with 6-digit code)
    p4 = products[3] if len(products) > 3 else products[0]
    sub4 = (p2.price * 2) + (p4.price * 2)
    o4, created4 = Order.objects.get_or_create(
        order_number="SM-2026-1004",
        defaults={
            "customer": customer,
            "vendor": vendor,
            "store": store,
            "status": OrderStatus.COMPLETED,
            "fulfillment_type": FulfillmentType.WALK_IN,
            "walk_in_code": "847291",
            "customer_phone_snapshot": "+1 (555) 123-4567",
            "subtotal": sub4,
            "delivery_fee": Decimal("0.00"),
            "total_amount": sub4,
            "payment_method": PaymentMethod.COD,
            "payment_status": PaymentStatus.COLLECTED,
            "accepted_at": now,
            "completed_at": now,
            "paid_at": now,
            "payment_collected_by": vendor,
        }
    )
    if created4:
        OrderItem.objects.create(order=o4, product=p2, product_name_snapshot=p2.name, unit_price_snapshot=p2.price, quantity=2, line_total=p2.price * 2)
        OrderItem.objects.create(order=o4, product=p4, product_name_snapshot=p4.name, unit_price_snapshot=p4.price, quantity=2, line_total=p4.price * 2)

    print("✅ Demo orders successfully created!")
