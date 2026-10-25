"""
scripts/seeds/seed_demo_data.py — Seed demo accounts, stores, categories, and products.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from users.models.profile_mod import Profile
from stores.models.store_mod import Store
from stores.models.loyalty_mod import StoreLoyaltyProgram
from stores.models.coupon_mod import Coupon, DiscountType
from categories.models.category_mod import Category
from products.models.product_mod import Product
from products.models.product_image_mod import ProductImage
from shared.enums.enums import UserRoleEnum
from shared.enums.unit_enums import MeasurementUnit

User = get_user_model()


def run():
    print("  Creating demo accounts...")

    # 1. Customer: customer_a_saved@test.com
    customer, _ = User.objects.get_or_create(
        email="customer_a_saved@test.com",
        defaults={
            "role": UserRoleEnum.CUSTOMER,
            "is_active": True,
        }
    )
    customer.set_password("Password123!")
    customer.save()
    p_cust, _ = Profile.objects.get_or_create(user=customer)
    p_cust.full_name = "Alice Shopper"
    p_cust.phone_number = "+1 (555) 123-4567"
    p_cust.address = "123 Maple Street, Apt 4B, Springfield"
    p_cust.save()

    # 2. Vendor: vendor_saved@test.com
    vendor, _ = User.objects.get_or_create(
        email="vendor_saved@test.com",
        defaults={
            "role": UserRoleEnum.VENDOR,
            "is_active": True,
        }
    )
    vendor.set_password("Password123!")
    vendor.save()
    p_vend, _ = Profile.objects.get_or_create(user=vendor)
    p_vend.full_name = "Bob Vendor"
    p_vend.phone_number = "+1 (555) 987-6543"
    p_vend.save()

    # 3. Admin: admin@test.com
    admin, _ = User.objects.get_or_create(
        email="admin@test.com",
        defaults={
            "role": UserRoleEnum.SUPERUSER,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
    )
    admin.set_password("Password123!")
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    p_adm, _ = Profile.objects.get_or_create(user=admin)
    p_adm.full_name = "Chief Administrator"
    p_adm.phone_number = "+1 (555) 000-0001"
    p_adm.save()

    print("  Creating turnkey merchant stores...")

    # Store 1: Fresh Fields Market
    store1, _ = Store.objects.get_or_create(
        id=1,
        defaults={
            "vendor": vendor,
            "name": "Fresh Fields Market",
            "slug": "fresh-fields-market",
            "public_url_slug": "freshfields.com",
            "description": "Your premier neighborhood destination for farm-fresh organic produce, artisanal bakery goods, and pantry essentials.",
            "owner_name": "Bob Vendor",
            "phone_number": "+1 (555) 234-5678",
            "whatsapp_number": "+1 (555) 234-5678",
            "email": "freshfields@example.com",
            "website_url": "https://freshfields.com",
            "shop_type": "hybrid",
            "address": "100 Market St, Downtown",
            "latitude": Decimal("37.774929"),
            "longitude": Decimal("-122.419416"),
            "is_active": True,
            "is_verified": True,
            "average_rating": Decimal("4.80"),
            "total_reviews": 32,
            "delivery_fee": Decimal("5.00"),
            "min_order_amount": Decimal("15.00"),
            "delivery_enabled": True,
            "pickup_enabled": True,
        }
    )
    if store1.vendor != vendor:
        store1.vendor = vendor
        store1.save()

    # Store 2: Apex Hardware & Tools
    store2, _ = Store.objects.get_or_create(
        id=2,
        defaults={
            "vendor": vendor,
            "name": "Apex Hardware & Tools",
            "slug": "apex-hardware-tools",
            "public_url_slug": "apexhardware.com",
            "description": "Heavy-duty tools, hardware, and home improvement supplies for contractors and DIY masters.",
            "owner_name": "Bob Vendor",
            "phone_number": "+1 (555) 876-5432",
            "email": "apex@example.com",
            "shop_type": "hybrid",
            "address": "742 Evergreen Terrace",
            "latitude": Decimal("37.784929"),
            "longitude": Decimal("-122.409416"),
            "is_active": True,
            "is_verified": True,
            "average_rating": Decimal("4.90"),
            "total_reviews": 48,
            "delivery_fee": Decimal("8.50"),
            "min_order_amount": Decimal("25.00"),
            "delivery_enabled": True,
            "pickup_enabled": True,
        }
    )

    # Store 3: Green Valley Organics
    store3, _ = Store.objects.get_or_create(
        id=3,
        defaults={
            "vendor": vendor,
            "name": "Green Valley Organics",
            "slug": "green-valley-organics",
            "public_url_slug": "greenvalley.com",
            "description": "Certified organic produce, cold-pressed juices, and healthy superfoods directly sourced from local farms.",
            "owner_name": "Bob Vendor",
            "phone_number": "+1 (555) 345-6789",
            "email": "contact@greenvalley.com",
            "shop_type": "hybrid",
            "address": "45 River Valley Rd",
            "latitude": Decimal("37.764929"),
            "longitude": Decimal("-122.429416"),
            "is_active": True,
            "is_verified": True,
            "average_rating": Decimal("4.70"),
            "total_reviews": 19,
            "delivery_fee": Decimal("4.00"),
            "min_order_amount": Decimal("20.00"),
            "delivery_enabled": True,
            "pickup_enabled": True,
        }
    )

    print("  Creating categories for Fresh Fields Market...")
    cat_produce, _ = Category.objects.get_or_create(store=store1, name="Fresh Produce")
    cat_bakery, _ = Category.objects.get_or_create(store=store1, name="Bakery & Dairy")
    cat_pantry, _ = Category.objects.get_or_create(store=store1, name="Pantry Staples")
    cat_beverage, _ = Category.objects.get_or_create(store=store1, name="Beverages & Snacks")

    print("  Creating catalog products with barcodes...")
    demo_products = [
        {
            "name": "Organic Whole Milk (1L)",
            "category": cat_bakery,
            "barcode": "123456789012",
            "sku": "FF-MILK-001",
            "aisle": "Aisle 1",
            "shelf_location": "Aisle 1 - Dairy Shelf B",
            "price": Decimal("3.49"),
            "cost_price": Decimal("2.10"),
            "measure": 1,
            "unit": MeasurementUnit.LITER,
            "tags": ["organic", "dairy", "milk"],
            "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Artisan Sourdough Loaf (800g)",
            "category": cat_bakery,
            "barcode": "890123456789",
            "sku": "FF-BREAD-002",
            "aisle": "Aisle 1",
            "shelf_location": "Aisle 1 - Bakery Rack 2",
            "price": Decimal("4.99"),
            "cost_price": Decimal("2.80"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "tags": ["bakery", "sourdough", "artisan"],
            "image_url": "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Farm Fresh Brown Eggs (Dozen)",
            "category": cat_bakery,
            "barcode": "978020137962",
            "sku": "FF-EGGS-003",
            "aisle": "Aisle 1",
            "shelf_location": "Aisle 1 - Dairy Top Shelf",
            "price": Decimal("4.29"),
            "cost_price": Decimal("2.50"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "tags": ["eggs", "organic", "farm"],
            "image_url": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Fresh Hass Avocados (Pack of 3)",
            "category": cat_produce,
            "barcode": "400638133393",
            "sku": "FF-AVOC-004",
            "aisle": "Aisle 2",
            "shelf_location": "Aisle 2 - Produce Bin 4",
            "price": Decimal("3.99"),
            "cost_price": Decimal("2.20"),
            "measure": 3,
            "unit": MeasurementUnit.PIECE,
            "tags": ["produce", "avocado", "fresh"],
            "image_url": "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Crisp Fuji Apples (1kg)",
            "category": cat_produce,
            "barcode": "735005385001",
            "sku": "FF-APPL-005",
            "aisle": "Aisle 2",
            "shelf_location": "Aisle 2 - Produce Stand 1",
            "price": Decimal("2.99"),
            "cost_price": Decimal("1.70"),
            "measure": 1,
            "unit": MeasurementUnit.KILOGRAM,
            "tags": ["fruit", "apples", "organic"],
            "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Colombian Dark Roast Coffee Beans (500g)",
            "category": cat_pantry,
            "barcode": "012345678905",
            "sku": "FF-COFF-006",
            "aisle": "Aisle 3",
            "shelf_location": "Aisle 3 - Coffee & Tea",
            "price": Decimal("8.99"),
            "cost_price": Decimal("5.20"),
            "measure": 500,
            "unit": MeasurementUnit.GRAM,
            "tags": ["coffee", "roast", "beans"],
            "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Extra Virgin Olive Oil (750ml)",
            "category": cat_pantry,
            "barcode": "501234567890",
            "sku": "FF-OIL-007",
            "aisle": "Aisle 3",
            "shelf_location": "Aisle 3 - Oils & Vinegars",
            "price": Decimal("11.50"),
            "cost_price": Decimal("7.00"),
            "measure": 750,
            "unit": MeasurementUnit.MILLILITER,
            "tags": ["oil", "pantry", "olive"],
            "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&auto=format&fit=crop&q=80",
        },
        {
            "name": "Sparkling Mineral Water (6x500ml)",
            "category": cat_beverage,
            "barcode": "601234567891",
            "sku": "FF-WATER-008",
            "aisle": "Aisle 4",
            "shelf_location": "Aisle 4 - Cold Drinks",
            "price": Decimal("5.49"),
            "cost_price": Decimal("3.00"),
            "measure": 6,
            "unit": MeasurementUnit.PIECE,
            "tags": ["beverage", "water", "sparkling"],
            "image_url": "https://images.unsplash.com/photo-1560023907-5f339617ea30?w=600&auto=format&fit=crop&q=80",
        },
    ]

    for pdata in demo_products:
        img_url = pdata.pop("image_url")
        prod, _ = Product.objects.get_or_create(
            store=store1,
            name=pdata["name"],
            defaults={**pdata, "description": f"Premium quality {pdata['name']} stocked fresh daily."}
        )
        if img_url:
            ProductImage.objects.get_or_create(
                product=prod,
                image_url=img_url,
                defaults={"is_primary": True, "display_order": 0, "alt_text": prod.name}
            )

    print("  Setting up Store Loyalty Program & Coupons...")
    StoreLoyaltyProgram.objects.get_or_create(
        store=store1,
        defaults={
            "vendor": vendor,
            "is_active": True,
            "points_per_currency_unit": Decimal("1.00"),
            "currency_per_point_redemption": Decimal("0.0500"),
            "stamps_for_reward": 10,
            "stamp_reward_discount_amount": Decimal("10.00"),
            "min_order_for_stamp": Decimal("20.00"),
        }
    )

    Coupon.objects.get_or_create(
        store=store1,
        code="WELCOME10",
        defaults={
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": Decimal("10.00"),
            "min_order_amount": Decimal("20.00"),
            "is_active": True,
        }
    )

    Coupon.objects.get_or_create(
        store=store1,
        code="SAVE5",
        defaults={
            "discount_type": DiscountType.FIXED,
            "discount_value": Decimal("5.00"),
            "min_order_amount": Decimal("25.00"),
            "is_active": True,
        }
    )

    print("✅ Demo accounts and seed catalog successfully created!")
