import os
import sys
import django
from decimal import Decimal
import uuid
import secrets

sys.path.insert(0, '/home/mizan/Desktop/smart_memo')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_memo.settings')
django.setup()

from django.utils import timezone
from users.models.user_mod import User
from users.models.profile_mod import Profile
from users.models.address_mod import CustomerAddress
from stores.models.store_mod import Store
from stores.models.review_mod import StoreReview
from stores.models.coupon_mod import Coupon, DiscountType
from stores.models.loyalty_mod import StoreLoyaltyProgram
from categories.models.category_mod import Category
from products.models.product_mod import Product, MeasurementUnit
from products.models.product_image_mod import ProductImage
from inventory.models.inventory_mod import StockBalance
from orders.models.order_mod import Order, OrderItem, OrderStatus, PaymentStatus, FulfillmentType, SalesMemo
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseItem, PurchaseStatus
from cards.models.card_mod import Card, CardItem
from cards.models.template_mod import StoreMemoTemplate, StoreMemoTemplateItem

def run():
    print("🚀 Seeding Full High-Density Production Dataset (10+ for EVERY API)...")

    # 1. USERS & ACCOUNTS
    vendor, _ = User.objects.get_or_create(
        email="vendor_saved@test.com",
        defaults={"role": "vendor", "is_active": True}
    )
    vendor.set_password("Password123!")
    vendor.role = "vendor"
    Profile.objects.update_or_create(user=vendor, defaults={"full_name": "Bob Vendor"})
    vendor.save()

    customer, _ = User.objects.get_or_create(
        email="customer_a_saved@test.com",
        defaults={"role": "customer", "is_active": True}
    )
    customer.set_password("Password123!")
    customer.role = "customer"
    Profile.objects.update_or_create(user=customer, defaults={"full_name": "Alice Customer"})
    customer.save()

    extra_customers = []
    customer_names = [
        ("David Miller", "david.m@test.com"),
        ("Sarah Jenkins", "sarah.j@test.com"),
        ("Michael Chang", "michael.c@test.com"),
        ("Emma Watson", "emma.w@test.com"),
        ("Carlos Rodriguez", "carlos.r@test.com"),
        ("Priya Sharma", "priya.s@test.com"),
        ("Liam O'Connor", "liam.oc@test.com"),
        ("Amina Al-Mansoor", "amina.m@test.com"),
        ("Lucas Silva", "lucas.s@test.com"),
        ("Hannah Schmidt", "hannah.s@test.com")
    ]
    for name, email in customer_names:
        u, _ = User.objects.get_or_create(
            email=email,
            defaults={"role": "customer", "is_active": True}
        )
        u.set_password("Password123!")
        u.role = "customer"
        Profile.objects.update_or_create(user=u, defaults={"full_name": name})
        u.save()
        extra_customers.append(u)

    print(f"  ✅ Users verified (Vendor: {vendor.email}, Customers: {len(extra_customers) + 1})")

    # 2. CUSTOMER SAVED ADDRESSES (10+ Items)
    addresses_data = [
        ("Home Apartment", "Alice Customer", "+1 (555) 123-4567", "Apt 4B, 742 Evergreen Terrace", "San Francisco", "94103", 37.7749, -122.4194, "Ring buzzer 4B, leave by door", True),
        ("Tech Office HQ", "Alice Customer", "+1 (555) 123-4567", "Floor 12, 100 Market Street", "San Francisco", "94105", 37.7929, -122.3970, "Deliver to 12th floor reception", False),
        ("Parents Residence", "Robert Customer", "+1 (555) 234-5678", "1250 Oakwood Blvd", "Oakland", "94612", 37.8044, -122.2712, "Leave with security at main gate", False),
        ("Weekend Beach House", "Alice Customer", "+1 (555) 123-4567", "88 Pacific Coast Hwy", "Pacifica", "94044", 37.6138, -122.4869, "Side gate code is 1234", False),
        ("Crossfit Gym Locker", "David Miller", "+1 (555) 345-6789", "540 Brannan St", "San Francisco", "94107", 37.7771, -122.3992, "Deliver to front desk during hours", False),
        ("Design Studio", "Sarah Jenkins", "+1 (555) 456-7890", "220 King St, Unit 3", "San Francisco", "94107", 37.7758, -122.3926, "Call phone upon arrival", False),
        ("University Campus Dorm", "Michael Chang", "+1 (555) 567-8901", "Dorm B, Room 312, 2600 Bancroft Way", "Berkeley", "94720", 37.8688, -122.2570, "Meet outside student lobby", False),
        ("Downtown Co-working", "Emma Watson", "+1 (555) 678-9012", "500 Howard St, WeWork Hub", "San Francisco", "94105", 37.7885, -122.3978, "Leave at Community Desk", False),
        ("Family Townhouse", "Carlos Rodriguez", "+1 (555) 789-0123", "340 Pine St, Apt 2", "San Francisco", "94104", 37.7917, -122.4021, "Direct street entrance", False),
        ("Suburban Garden Home", "Priya Sharma", "+1 (555) 890-1234", "1820 Blossom Hill Rd", "San Jose", "95124", 37.2415, -121.9056, "Place inside porch box", False),
    ]
    for label, recipient, phone, line, city, postal, lat, lng, inst, is_def in addresses_data:
        CustomerAddress.objects.get_or_create(
            customer=customer,
            label=label,
            defaults={
                "recipient_name": recipient,
                "phone_number": phone,
                "address_line": line,
                "city": city,
                "postal_code": postal,
                "latitude": lat,
                "longitude": lng,
                "delivery_instructions": inst,
                "is_default": is_def,
            }
        )
    print(f"  ✅ Customer addresses seeded: {CustomerAddress.objects.count()}")

    # 3. STORES (10 Verified Merchant Stores)
    stores_catalog_data = [
        {
            "id": 1,
            "name": "Fresh Fields Market",
            "slug": "fresh-fields-market",
            "public_url_slug": "freshfields.com",
            "description": "Premium organic grocer, farm-fresh produce, artisanal bakery, gourmet cheeses, and everyday pantry essentials.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 987-6543",
            "whatsapp": "+1 (555) 987-6543",
            "email": "freshfields@example.com",
            "website": "https://freshfields.com",
            "address": "101 Organic Way, Financial District",
            "lat": Decimal("37.794929"),
            "lng": Decimal("-122.399416"),
            "rating": Decimal("4.85"),
            "reviews": 64,
            "open": "08:00",
            "close": "22:00",
            "delivery_fee": Decimal("4.50"),
            "min_order": Decimal("15.00"),
            "logo": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Fresh Produce", [
                    ("Organic Gala Apples (1kg)", "Sweet and crisp orchard fresh gala apples", Decimal("3.99"), "Aisle 1", "Shelf A-1", "FF-APL-01", "123456789012", "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600&auto=format&fit=crop&q=80"),
                    ("California Ripe Avocados (Pack of 3)", "Creamy Hass avocados ready to eat", Decimal("4.99"), "Aisle 1", "Shelf A-2", "FF-AVO-02", "123456789013", "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=600&auto=format&fit=crop&q=80"),
                    ("Organic Baby Spinach (250g)", "Pre-washed tender salad greens", Decimal("2.99"), "Aisle 1", "Shelf B-1", "FF-SPN-03", "123456789014", "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Bakery & Dairy", [
                    ("Farm Fresh Whole Milk (1L)", "Grade A pasteurized vitamin D milk", Decimal("3.49"), "Aisle 2", "Shelf A-1", "FF-MLK-04", "123456789015", "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600&auto=format&fit=crop&q=80"),
                    ("Artisan Sourdough Loaf (800g)", "Naturally leavened crusty bakery loaf", Decimal("4.99"), "Aisle 2", "Shelf B-2", "FF-BRD-05", "123456789016", "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=600&auto=format&fit=crop&q=80"),
                    ("French Butter with Sea Salt (250g)", "Creamy Normandy cultured butter", Decimal("5.75"), "Aisle 2", "Shelf C-1", "FF-BTR-06", "123456789017", "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Pantry Staples", [
                    ("Extra Virgin Olive Oil (750ml)", "Cold-pressed Greek single estate oil", Decimal("11.50"), "Aisle 3", "Shelf A-3", "FF-OIL-07", "123456789018", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&auto=format&fit=crop&q=80"),
                    ("Organic Wildflower Honey (500g)", "Raw unfiltered local apiary honey", Decimal("8.99"), "Aisle 3", "Shelf B-2", "FF-HNY-08", "123456789019", "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Beverages & Snacks", [
                    ("Sparkling Mineral Water (6x500ml)", "Naturally carbonated mineral springs water", Decimal("5.49"), "Aisle 4", "Shelf A-1", "FF-WTR-09", "123456789020", "https://images.unsplash.com/photo-1560023907-5f339617ea30?w=600&auto=format&fit=crop&q=80"),
                    ("Roasted Artisan Almonds (300g)", "Lightly salted slow-roasted California almonds", Decimal("6.20"), "Aisle 4", "Shelf B-3", "FF-ALM-10", "123456789021", "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 2,
            "name": "Apex Hardware & Tools",
            "slug": "apex-hardware-tools",
            "public_url_slug": "apexhardware.com",
            "description": "Heavy-duty power tools, professional hand tools, building hardware, electrical testing, and safety equipment.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 876-5432",
            "whatsapp": "+1 (555) 876-5432",
            "email": "apex@example.com",
            "website": "https://apexhardware.com",
            "address": "742 Evergreen Terrace, Suite 100",
            "lat": Decimal("37.784929"),
            "lng": Decimal("-122.409416"),
            "rating": Decimal("4.92"),
            "reviews": 52,
            "open": "07:30",
            "close": "20:00",
            "delivery_fee": Decimal("8.50"),
            "min_order": Decimal("25.00"),
            "logo": "https://images.unsplash.com/photo-1581783342308-f792dbdd27c5?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Power Tools", [
                    ("DeWalt 20V MAX Cordless Drill Kit", "Brushless compact drill with 2 lithium batteries", Decimal("129.99"), "Aisle 4", "Shelf A-1", "APX-DRL-01", "885911497210", "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=600&auto=format&fit=crop&q=80"),
                    ("Milwaukee Shockwave 40pc Impact Bit Set", "Custom Alloy76 torque-resistant driver bits", Decimal("19.99"), "Aisle 4", "Shelf B-2", "APX-BIT-02", "045242509126", "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Hand Tools", [
                    ("Stanley 25ft PowerLock Tape Measure", "Classic chrome case with BladeArmor coating", Decimal("14.99"), "Aisle 2", "Shelf A-3", "APX-TAP-03", "076174334289", "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=600&auto=format&fit=crop&q=80"),
                    ("Estwing 16oz Solid Steel Claw Hammer", "Forged American steel with shock reduction grip", Decimal("29.50"), "Aisle 2", "Shelf B-1", "APX-HAM-04", "034139622119", "https://images.unsplash.com/photo-1586864387789-628af9feed72?w=600&auto=format&fit=crop&q=80"),
                    ("Channellock 10-Inch Groove Pliers", "Laser-hardened right angle teeth comfort grip", Decimal("22.00"), "Aisle 2", "Shelf C-2", "APX-PLI-05", "025582310107", "https://images.unsplash.com/photo-1581783342308-f792dbdd27c5?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Fasteners & Hardware", [
                    ("Heavy-Duty Drywall Screws Box (200pc)", "Self-drilling zinc plated drywall screws", Decimal("12.50"), "Aisle 5", "Shelf A-4", "APX-SCR-06", "078234123891", "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"),
                    ("Gorilla Waterproof Heavy Duct Tape (35yd)", "Triple layer strength tough weatherproof adhesive", Decimal("9.99"), "Aisle 5", "Shelf B-2", "APX-TAP-07", "052427600120", "https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Electrical & Safety", [
                    ("Klein Tools Auto-Ranging Digital Multimeter", "CAT III 600V safety rated electrician meter", Decimal("49.95"), "Aisle 3", "Shelf A-2", "APX-MLT-08", "092644690181", "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80"),
                    ("3M Professional Safety Glasses & Ear Muffs Kit", "ANSI Z87.1 certified anti-fog impact protection", Decimal("16.00"), "Aisle 1", "Shelf A-1", "APX-SAF-09", "051131070243", "https://images.unsplash.com/photo-1584744982491-665216d95f8b?w=600&auto=format&fit=crop&q=80"),
                    ("LED 1000lm Magnetic Jobsite Work Light", "Rechargeable magnetic base inspection floodlight", Decimal("34.50"), "Aisle 3", "Shelf B-3", "APX-LGT-10", "088712399014", "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 3,
            "name": "Green Valley Organics",
            "slug": "green-valley-organics",
            "public_url_slug": "greenvalley.com",
            "description": "Certified organic produce, cold-pressed raw juices, macrobiotic bowls, and nutrient-dense superfoods.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 345-6789",
            "whatsapp": "+1 (555) 345-6789",
            "email": "contact@greenvalley.com",
            "website": "https://greenvalley.com",
            "address": "45 River Valley Rd, Mission District",
            "lat": Decimal("37.764929"),
            "lng": Decimal("-122.429416"),
            "rating": Decimal("4.78"),
            "reviews": 38,
            "open": "08:00",
            "close": "21:00",
            "delivery_fee": Decimal("4.00"),
            "min_order": Decimal("20.00"),
            "logo": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1506484381205-f7945653044d?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Organic Fruits", [
                    ("Organic Honeycrisp Apples (1kg)", "Crisp juicy sweet organic apples", Decimal("5.49"), "Aisle 1", "Shelf A-1", "GV-APL-01", "701234567891", "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600&auto=format&fit=crop&q=80"),
                    ("Organic Blueberries Clamshell (250g)", "Antioxidant rich plump fresh blueberries", Decimal("4.50"), "Aisle 1", "Shelf A-3", "GV-BER-02", "701234567892", "https://images.unsplash.com/photo-1498557850523-fd3d118b962e?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Organic Greens & Juices", [
                    ("Cold-Pressed Green Detox Juice (500ml)", "Kale, cucumber, green apple, ginger, lemon", Decimal("7.50"), "Aisle 2", "Shelf B-1", "GV-JUC-03", "701234567893", "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=600&auto=format&fit=crop&q=80"),
                    ("Organic Baby Kale Box (200g)", "Tender nutrient-packed baby kale leaves", Decimal("3.80"), "Aisle 2", "Shelf B-2", "GV-KAL-04", "701234567894", "https://images.unsplash.com/photo-1524179091875-bf99a9a6fa57?w=600&auto=format&fit=crop&q=80"),
                    ("Chia Seed Wellness Pudding Cup", "Almond milk vanilla chia pudding with berries", Decimal("4.25"), "Aisle 2", "Shelf C-1", "GV-CHI-05", "701234567895", "https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 4,
            "name": "Artisan Bakery & Roastery",
            "slug": "artisan-bakery-roastery",
            "public_url_slug": "artisanbakery.com",
            "description": "French croissants, wood-fired sourdough loaves, hand-poured single-origin espresso, and delicate patisserie.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 234-5671",
            "whatsapp": "+1 (555) 234-5671",
            "email": "bonjour@artisanbakery.com",
            "website": "https://artisanbakery.com",
            "address": "88 Boulangerie Way, Hayes Valley",
            "lat": Decimal("37.776929"),
            "lng": Decimal("-122.423416"),
            "rating": Decimal("4.96"),
            "reviews": 89,
            "open": "07:00",
            "close": "19:00",
            "delivery_fee": Decimal("3.50"),
            "min_order": Decimal("12.00"),
            "logo": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Viennoiserie & Pastries", [
                    ("Classic Pure Butter French Croissant", "Flaky golden multi-layered butter croissant", Decimal("3.50"), "Aisle 1", "Shelf A-1", "AB-CRO-01", "801234567891", "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&auto=format&fit=crop&q=80"),
                    ("Pain au Chocolat (Dark Belgian)", "Double baton 64% Belgian dark chocolate croissant", Decimal("4.20"), "Aisle 1", "Shelf A-2", "AB-PAC-02", "801234567892", "https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=600&auto=format&fit=crop&q=80"),
                    ("Almond Frangipane Twice-Baked Croissant", "Toasted sliced almonds with rich almond cream", Decimal("4.75"), "Aisle 1", "Shelf B-1", "AB-ALM-03", "801234567893", "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Specialty Coffee Beans", [
                    ("Ethiopian Yirgacheffe Beans (250g)", "Floral jasmine and bergamot light roast beans", Decimal("16.50"), "Aisle 2", "Shelf A-1", "AB-COF-04", "801234567894", "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&auto=format&fit=crop&q=80"),
                    ("House Espresso Blend Dark Roast (500g)", "Notes of dark chocolate, hazelnut, and caramel", Decimal("19.00"), "Aisle 2", "Shelf B-2", "AB-COF-05", "801234567895", "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 5,
            "name": "MediCare Plus Pharmacy",
            "slug": "medicare-plus-pharmacy",
            "public_url_slug": "medicareplus.com",
            "description": "Licensed retail pharmacy, prescription OTC remedies, vitamins, supplements, diagnostics, and personal hygiene.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 345-0987",
            "whatsapp": "+1 (555) 345-0987",
            "email": "rx@medicareplus.com",
            "website": "https://medicareplus.com",
            "address": "250 Hospital Way, Medical Plaza",
            "lat": Decimal("37.769929"),
            "lng": Decimal("-122.449416"),
            "rating": Decimal("4.88"),
            "reviews": 41,
            "open": "08:00",
            "close": "23:00",
            "delivery_fee": Decimal("3.00"),
            "min_order": Decimal("10.00"),
            "logo": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1576602976047-174e57a47881?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Vitamins & Immunity", [
                    ("Vitamin C 1000mg with Rose Hips (100 Tablets)", "High potency immune defense dietary supplement", Decimal("12.99"), "Aisle 1", "Shelf A-1", "MC-VTC-01", "901234567891", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=80"),
                    ("Omega-3 Triple Strength Fish Oil (120 Softgels)", "Purified wild-caught deep ocean omega-3 EPA/DHA", Decimal("21.50"), "Aisle 1", "Shelf B-2", "MC-OMG-02", "901234567892", "https://images.unsplash.com/photo-1577401239170-897942555fb3?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("First Aid & Wellness", [
                    ("Sterile Adhesive Bandages Variety Pack (100ct)", "Flexible fabric breathable protection assorted sizes", Decimal("6.49"), "Aisle 2", "Shelf A-2", "MC-BND-03", "901234567893", "https://images.unsplash.com/photo-1603398938378-e54eab446dde?w=600&auto=format&fit=crop&q=80"),
                    ("Infrared No-Touch Forehead Digital Thermometer", "1-second medical grade rapid fever temperature readout", Decimal("29.99"), "Aisle 2", "Shelf B-1", "MC-THM-04", "901234567894", "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 6,
            "name": "CyberByte Tech & Mobile",
            "slug": "cyberbyte-tech-mobile",
            "public_url_slug": "cyberbyte.com",
            "description": "Smartphone accessories, high-speed GaN chargers, ANC wireless headphones, ergonomic keyboards, and gaming gear.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 456-7892",
            "whatsapp": "+1 (555) 456-7892",
            "email": "sales@cyberbyte.com",
            "website": "https://cyberbyte.com",
            "address": "650 Silicon Plaza, SOMA Tech Hub",
            "lat": Decimal("37.781929"),
            "lng": Decimal("-122.401416"),
            "rating": Decimal("4.72"),
            "reviews": 35,
            "open": "09:00",
            "close": "21:00",
            "delivery_fee": Decimal("5.00"),
            "min_order": Decimal("20.00"),
            "logo": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Cables & Fast Chargers", [
                    ("65W GaN Dual USB-C Fast Wall Charger", "Ultra-compact fast charging for laptops and smartphones", Decimal("32.00"), "Aisle 1", "Shelf A-1", "CB-CHG-01", "911234567891", "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"),
                    ("Braided USB-C to USB-C 100W Cable (2m)", "Durable nylon braided high-speed sync and PD charging", Decimal("14.50"), "Aisle 1", "Shelf B-2", "CB-CBL-02", "911234567892", "https://images.unsplash.com/photo-1608248597359-00918002cf7e?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Audio & Wearables", [
                    ("Active Noise Cancelling Wireless Earbuds", "Bluetooth 5.3 with 36-hour playback case", Decimal("59.99"), "Aisle 2", "Shelf A-3", "CB-EAR-03", "911234567893", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"),
                    ("Magnetic 10,000mAh Wireless Power Bank", "MagSafe compatible snap-on portable battery pack", Decimal("39.99"), "Aisle 2", "Shelf B-1", "CB-PWR-04", "911234567894", "https://images.unsplash.com/photo-1609592424368-e4fc7a93a103?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 7,
            "name": "Paws & Claws Pet Emporium",
            "slug": "paws-claws-pet-emporium",
            "public_url_slug": "pawsandclaws.com",
            "description": "Holistic organic pet nutrition, grain-free dog food, cat treats, indestructible chew toys, and grooming supplies.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 567-8903",
            "whatsapp": "+1 (555) 567-8903",
            "email": "hello@pawsandclaws.com",
            "website": "https://pawsandclaws.com",
            "address": "410 Pet Boulevard, Marina District",
            "lat": Decimal("37.801929"),
            "lng": Decimal("-122.435416"),
            "rating": Decimal("4.94"),
            "reviews": 57,
            "open": "08:30",
            "close": "20:00",
            "delivery_fee": Decimal("4.50"),
            "min_order": Decimal("15.00"),
            "logo": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Dog Food & Treats", [
                    ("Grain-Free Salmon & Sweet Potato Kibble (5kg)", "Omega rich formula for sensitive digestion and shiny coat", Decimal("38.50"), "Aisle 1", "Shelf A-1", "PC-DOG-01", "921234567891", "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=600&auto=format&fit=crop&q=80"),
                    ("Natural Beef Tendon Chew Sticks (10 Pack)", "Long-lasting dental chew sticks promoting healthy gums", Decimal("15.99"), "Aisle 1", "Shelf B-2", "PC-DOG-02", "921234567892", "https://images.unsplash.com/photo-1535294435445-d7249524ef2e?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Cat Care & Accessories", [
                    ("Clumping Natural Odor-Control Cat Litter (10kg)", "Dust-free quick clumping biodegradable cat litter", Decimal("18.00"), "Aisle 2", "Shelf A-2", "PC-CAT-03", "921234567893", "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&auto=format&fit=crop&q=80"),
                    ("Interactive Feather Laser Cat Toy", "Automatic rotating laser pointer with chirping feather", Decimal("14.50"), "Aisle 2", "Shelf B-3", "PC-CAT-04", "921234567894", "https://images.unsplash.com/photo-1545249390-6bdfa286032f?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 8,
            "name": "The Paper Tree Stationery & Books",
            "slug": "the-paper-tree-stationery-books",
            "public_url_slug": "thepapertree.com",
            "description": "Japanese fountain pens, dotted bullet journals, artist sketchbooks, desk organizers, and curated indie papercraft.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 678-9014",
            "whatsapp": "+1 (555) 678-9014",
            "email": "orders@thepapertree.com",
            "website": "https://thepapertree.com",
            "address": "120 Poet Lane, North Beach",
            "lat": Decimal("37.800929"),
            "lng": Decimal("-122.410416"),
            "rating": Decimal("4.82"),
            "reviews": 34,
            "open": "09:30",
            "close": "19:30",
            "delivery_fee": Decimal("3.00"),
            "min_order": Decimal("10.00"),
            "logo": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1507842229450-79949f5984f1?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Notebooks & Journals", [
                    ("Hardcover Dotted Grid Journal (A5 160gsm)", "Bleedproof thick bamboo paper for fountain pen ink", Decimal("18.50"), "Aisle 1", "Shelf A-1", "PT-NBK-01", "931234567891", "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80"),
                    ("Vintage Leather Refillable Travel Diary", "Distressed top-grain leather with brass lock clasp", Decimal("28.00"), "Aisle 1", "Shelf B-2", "PT-NBK-02", "931234567892", "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Pens & Writing Tools", [
                    ("Brass Mechanical Drafting Pencil 0.5mm", "Solid brass hexagonal barrel with knurled grip", Decimal("19.99"), "Aisle 2", "Shelf A-3", "PT-PEN-03", "931234567893", "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"),
                    ("Japanese Fine Nib Calligraphy Fountain Pen", "Smooth iridium nib with vacuum plunger ink filling", Decimal("24.50"), "Aisle 2", "Shelf B-1", "PT-PEN-04", "931234567894", "https://images.unsplash.com/photo-1569683795645-b62e50fbf103?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 9,
            "name": "Urban Thread Essentials",
            "slug": "urban-thread-essentials",
            "public_url_slug": "urbanthread.com",
            "description": "Minimalist premium heavyweight organic cotton tees, french terry hoodies, durable canvas totes, and comfort basics.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 789-0125",
            "whatsapp": "+1 (555) 789-0125",
            "email": "style@urbanthread.com",
            "website": "https://urbanthread.com",
            "address": "330 Fashion Alley, SoMa District",
            "lat": Decimal("37.778929"),
            "lng": Decimal("-122.404416"),
            "rating": Decimal("4.68"),
            "reviews": 29,
            "open": "10:00",
            "close": "20:00",
            "delivery_fee": Decimal("5.00"),
            "min_order": Decimal("25.00"),
            "logo": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Heavyweight Tees & Tops", [
                    ("Heavyweight Organic Cotton Tee (240gsm Black)", "Pre-shrunk boxy cut combed ringspun organic cotton", Decimal("28.00"), "Aisle 1", "Shelf A-1", "UT-TEE-01", "941234567891", "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop&q=80"),
                    ("Minimalist Off-White Crewneck Pullover", "100% French terry cotton with ribbed cuffs", Decimal("48.00"), "Aisle 1", "Shelf B-2", "UT-CRW-02", "941234567892", "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Everyday Accessories", [
                    ("Heavy Canvas Utility Shopper Tote Bag", "Reinforced box-stitched 16oz cotton duck canvas", Decimal("22.00"), "Aisle 2", "Shelf A-2", "UT-TOT-03", "941234567893", "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"),
                    ("Merino Wool Everyday Ribbed Socks (3 Pack)", "Temperature regulating breathable anti-odor socks", Decimal("18.50"), "Aisle 2", "Shelf B-1", "UT-SOX-04", "941234567894", "https://images.unsplash.com/photo-1582966772680-860e372bb558?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        },
        {
            "id": 10,
            "name": "Sunrise Gourmet Dairy & Cheese",
            "slug": "sunrise-gourmet-dairy-cheese",
            "public_url_slug": "sunrisedairy.com",
            "description": "Cave-aged European cheeses, farm-churned artisan butter, Greek yogurts, clotted cream, and goat milk specialties.",
            "owner_name": "Bob Vendor",
            "phone": "+1 (555) 890-1236",
            "whatsapp": "+1 (555) 890-1236",
            "email": "fromage@sunrisedairy.com",
            "website": "https://sunrisedairy.com",
            "address": "512 Pasture Lane, Sunset District",
            "lat": Decimal("37.755929"),
            "lng": Decimal("-122.482416"),
            "rating": Decimal("4.89"),
            "reviews": 46,
            "open": "08:00",
            "close": "20:00",
            "delivery_fee": Decimal("4.00"),
            "min_order": Decimal("15.00"),
            "logo": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=300&auto=format&fit=crop&q=80",
            "cover": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=1600&auto=format&fit=crop&q=80",
            "categories": [
                ("Artisan Aged Cheeses", [
                    ("Aged English Cheddar 18-Month (200g)", "Sharp crystalline savory traditional farmhouse cheddar", Decimal("8.99"), "Aisle 1", "Shelf A-1", "SR-CHD-01", "951234567891", "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=600&auto=format&fit=crop&q=80"),
                    ("Authentic Italian Parmigiano Reggiano DOP (250g)", "24-month aged nutty umami raw cow milk cheese", Decimal("11.50"), "Aisle 1", "Shelf B-2", "SR-PRM-02", "951234567892", "https://images.unsplash.com/photo-1452195100486-9cc805987862?w=600&auto=format&fit=crop&q=80"),
                    ("Triple Cream French Brie Wheel (200g)", "Decadent buttery soft-ripened creamy cheese", Decimal("7.80"), "Aisle 1", "Shelf C-1", "SR-BRI-03", "951234567893", "https://images.unsplash.com/photo-1559561853-08451507cbe7?w=600&auto=format&fit=crop&q=80"),
                ]),
                ("Farmstead Yogurt & Butter", [
                    ("Traditional Greek Strained Yogurt 1kg", "Thick high-protein whole milk unflavored yogurt", Decimal("6.25"), "Aisle 2", "Shelf A-2", "SR-YOG-04", "951234567894", "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&auto=format&fit=crop&q=80"),
                    ("Hand-Churned Fleur de Sel Butter (250g)", "Rich yellow pasture butter sprinkled with sea salt crystals", Decimal("6.75"), "Aisle 2", "Shelf B-3", "SR-BTR-05", "951234567895", "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=600&auto=format&fit=crop&q=80"),
                ])
            ]
        }
    ]

    all_created_stores = []
    all_created_products = []

    for sdata in stores_catalog_data:
        store_obj, _ = Store.objects.get_or_create(
            id=sdata["id"],
            defaults={
                "vendor": vendor,
                "name": sdata["name"],
                "slug": sdata["slug"],
                "public_url_slug": sdata["public_url_slug"],
            }
        )
        store_obj.vendor = vendor
        store_obj.name = sdata["name"]
        store_obj.slug = sdata["slug"]
        store_obj.public_url_slug = sdata["public_url_slug"]
        store_obj.description = sdata["description"]
        store_obj.owner_name = sdata["owner_name"]
        store_obj.phone_number = sdata["phone"]
        store_obj.whatsapp_number = sdata["whatsapp"]
        store_obj.email = sdata["email"]
        store_obj.website_url = sdata["website"]
        store_obj.address = sdata["address"]
        store_obj.latitude = sdata["lat"]
        store_obj.longitude = sdata["lng"]
        store_obj.average_rating = sdata["rating"]
        store_obj.total_reviews = sdata["reviews"]
        store_obj.opening_time = sdata["open"]
        store_obj.closing_time = sdata["close"]
        store_obj.delivery_fee = sdata["delivery_fee"]
        store_obj.min_order_amount = sdata["min_order"]
        store_obj.logo_url = sdata["logo"]
        store_obj.cover_photo_url = sdata["cover"]
        store_obj.is_active = True
        store_obj.is_verified = True
        store_obj.delivery_enabled = True
        store_obj.pickup_enabled = True
        store_obj.shop_type = "hybrid"
        store_obj.save()
        all_created_stores.append(store_obj)

        # Loyalty & Coupons for every store
        StoreLoyaltyProgram.objects.get_or_create(
            store=store_obj,
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
            store=store_obj,
            code=f"WELCOME{store_obj.id}0",
            defaults={
                "discount_type": DiscountType.PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "min_order_amount": Decimal("20.00"),
                "is_active": True,
            }
        )

        # Categories & Products
        for cat_name, prod_list in sdata["categories"]:
            cat_obj, _ = Category.objects.get_or_create(store=store_obj, name=cat_name)
            for pname, pdesc, pprice, aisle, shelf, psku, pbarcode, pimg in prod_list:
                prod_obj, _ = Product.objects.get_or_create(
                    store=store_obj,
                    name=pname,
                    defaults={
                        "category": cat_obj,
                        "description": pdesc,
                        "price": pprice,
                        "cost_price": (pprice * Decimal("0.62")).quantize(Decimal("0.01")),
                        "aisle": aisle,
                        "shelf_location": shelf,
                        "sku": psku,
                        "barcode": pbarcode,
                        "stock": 35,
                        "unit": MeasurementUnit.PIECE,
                        "measure": 1,
                        "is_active": True,
                    }
                )
                prod_obj.category = cat_obj
                prod_obj.description = pdesc
                prod_obj.price = pprice
                prod_obj.aisle = aisle
                prod_obj.shelf_location = shelf
                prod_obj.sku = psku
                prod_obj.barcode = pbarcode
                prod_obj.stock = 35
                prod_obj.is_active = True
                prod_obj.save()

                if pimg:
                    ProductImage.objects.get_or_create(
                        product=prod_obj,
                        image_url=pimg,
                        defaults={"is_primary": True, "display_order": 0, "alt_text": prod_obj.name}
                    )

                StockBalance.objects.get_or_create(
                    store=store_obj,
                    product=prod_obj,
                    defaults={
                        "on_hand": Decimal("35.000"),
                        "reserved": Decimal("0.000"),
                        "low_stock_threshold": Decimal("5.000"),
                    }
                )
                all_created_products.append(prod_obj)

    print(f"  ✅ 10 Stores seeded. Total Categories: {Category.objects.count()}, Total Products: {Product.objects.count()}")

    # 4. STORE REVIEWS (15+ Verified Reviews)
    review_comments = [
        ("The digital walk-in code is brilliant! Scanned everything in aisle order and counter checkout took literally 10 seconds.", 5, "Thank you so much! We aim to make shopping effortless."),
        ("Super fresh produce and friendly cashier. Love being able to track my budget in real-time.", 5, "Glad you enjoyed your visit! Look forward to seeing you again."),
        ("Very neat store layout. Items match the shelf tags and barcodes scanned without a hitch.", 4, "Thanks for the feedback! We keep our catalog and shelf tags strictly synced."),
        ("Doorstep delivery was on time and carefully packaged with zero broken items.", 5, "Awesome to hear! Our delivery partners take great pride in handling every order."),
        ("Excellent tool selection and knowledgeable staff when I picked up my drill.", 5, "Happy to help with your project! Let us know if you need any other accessories."),
        ("Best sourdough in town. Crispy crust and soft airy crumb. Ordering weekly now.", 5, "Baked fresh every morning with 100% natural sourdough starter!"),
        ("Found hard-to-find vitamins easily. Fast in-store pickup with the 6-digit code.", 5, "Health and wellness is our priority. Stay healthy!"),
        ("Fast cable and charger delivery when my laptop charger broke during work.", 4, "Glad we could save your work day!"),
        ("My dog loves the grain-free salmon kibble. Shiny coat and healthy energy.", 5, "Woof! Give your pup a treat from us!"),
        ("Beautiful dotted journals and smooth fountain pen ink. A stationery lover's dream.", 5, "We handpick every indie journal and papercraft tool."),
        ("Great heavyweight t-shirts that hold their shape after washing. Quality cotton.", 4, "Thank you! We only use 240gsm combed organic cotton."),
        ("The 18-month aged cheddar and French brie were the stars of our dinner party.", 5, "Fromage perfection! Come back to try our truffle gouda next."),
        ("Super clean app and seamless checkout. Digital memo receipt sent to my wallet instantly.", 5, "Thank you! Digital receipts help keep our operations eco-friendly."),
        ("Great customer service when I needed to substitute an out of stock item.", 4, "Customer satisfaction is always our top priority."),
        ("Consistently reliable. Fresh produce, fair prices, and zero waiting in queue.", 5, "Always our pleasure to serve our local community!"),
    ]

    for idx, (comment, rating, reply) in enumerate(review_comments):
        target_store = all_created_stores[idx % len(all_created_stores)]
        reviewer = extra_customers[idx % len(extra_customers)]
        StoreReview.objects.get_or_create(
            store=target_store,
            customer=reviewer,
            defaults={
                "rating": rating,
                "comment": comment,
                "vendor_reply": reply,
                "is_visible": True,
            }
        )
    print(f"  ✅ Store reviews seeded: {StoreReview.objects.count()}")

    # 5. ORDERS ACROSS MULTIPLE STATUSES (15+ Realistic Orders)
    order_specs = [
        (OrderStatus.SUBMITTED, PaymentStatus.PENDING, FulfillmentType.DELIVERY, 1, 0, "742 Evergreen Terrace, Apt 4B"),
        (OrderStatus.SUBMITTED, PaymentStatus.PENDING, FulfillmentType.WALK_IN, 2, 1, None),
        (OrderStatus.ACCEPTED, PaymentStatus.PENDING, FulfillmentType.DELIVERY, 3, 2, "100 Market Street, Floor 12"),
        (OrderStatus.ACCEPTED, PaymentStatus.PENDING, FulfillmentType.WALK_IN, 4, 3, None),
        (OrderStatus.PREPARING, PaymentStatus.PENDING, FulfillmentType.DELIVERY, 1, 4, "1250 Oakwood Blvd"),
        (OrderStatus.PREPARING, PaymentStatus.PENDING, FulfillmentType.WALK_IN, 2, 5, None),
        (OrderStatus.OUT_FOR_DELIVERY, PaymentStatus.PENDING, FulfillmentType.DELIVERY, 5, 6, "540 Brannan St"),
        (OrderStatus.READY_FOR_PICKUP, PaymentStatus.PENDING, FulfillmentType.WALK_IN, 6, 7, None),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.DELIVERY, 1, 0, "Apt 4B, 742 Evergreen Terrace"),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.WALK_IN, 2, 1, None),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.DELIVERY, 3, 2, "220 King St, Unit 3"),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.WALK_IN, 4, 3, None),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.DELIVERY, 7, 4, "500 Howard St"),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.WALK_IN, 8, 5, None),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.DELIVERY, 9, 6, "340 Pine St, Apt 2"),
        (OrderStatus.COMPLETED, PaymentStatus.COLLECTED, FulfillmentType.WALK_IN, 10, 7, None),
        (OrderStatus.CANCELLED, PaymentStatus.FAILED, FulfillmentType.DELIVERY, 1, 8, "1820 Blossom Hill Rd"),
    ]

    for idx, (ostatus, pstatus, ftype, store_idx, cust_idx, addr) in enumerate(order_specs):
        st = all_created_stores[store_idx % len(all_created_stores)]
        cust = extra_customers[cust_idx % len(extra_customers)]
        store_prods = list(Product.objects.filter(store=st))
        if not store_prods:
            continue

        p1 = store_prods[0]
        p2 = store_prods[1] if len(store_prods) > 1 else store_prods[0]

        subtot = p1.price * Decimal("2") + p2.price * Decimal("1")
        dfee = st.delivery_fee if ftype == FulfillmentType.DELIVERY else Decimal("0.00")
        tot = subtot + dfee

        ord_num = f"SM-2026-20{idx+1:02d}"
        w_code = f"{secrets.randbelow(900000) + 100000}"

        order_obj, created = Order.objects.get_or_create(
            order_number=ord_num,
            defaults={
                "customer": cust,
                "vendor": vendor,
                "store": st,
                "status": ostatus,
                "payment_status": pstatus,
                "fulfillment_type": ftype,
                "subtotal": subtot,
                "delivery_fee": dfee,
                "total_amount": tot,
                "walk_in_code": w_code,
                "delivery_address": addr or "",
            }
        )

        if created:
            # Order items
            OrderItem.objects.create(
                order=order_obj,
                product=p1,
                product_name_snapshot=p1.name,
                unit_price_snapshot=p1.price,
                quantity=Decimal("2.000"),
                line_total=(p1.price * Decimal("2")).quantize(Decimal("0.01"))
            )
            OrderItem.objects.create(
                order=order_obj,
                product=p2,
                product_name_snapshot=p2.name,
                unit_price_snapshot=p2.price,
                quantity=Decimal("1.000"),
                line_total=p2.price
            )

            # Sales memo for completed orders
            if ostatus == OrderStatus.COMPLETED:
                SalesMemo.objects.get_or_create(
                    order=order_obj,
                    defaults={
                        "memo_number": f"MEMO-2026-20{idx+1:02d}",
                        "customer": cust,
                        "vendor": vendor,
                        "store_name_snapshot": st.name,
                        "customer_email_snapshot": cust.email,
                        "subtotal": subtot,
                        "delivery_fee": dfee,
                        "total_amount": tot,
                        "amount_paid": tot,
                        "walk_in_code_snapshot": w_code,
                        "items_snapshot": [
                            {"name": p1.name, "qty": "2", "price": str(p1.price), "total": str(p1.price * Decimal("2"))},
                            {"name": p2.name, "qty": "1", "price": str(p2.price), "total": str(p2.price)}
                        ]
                    }
                )

    print(f"  ✅ Orders seeded across all pipelines: {Order.objects.count()} (Sales Memos: {SalesMemo.objects.count()})")

    # 6. SUPPLIERS & PURCHASES (10+ Items)
    suppliers_data = [
        ("Golden Harvest Organic Farms", "contact@goldenharvest.com", "+1 (555) 111-2233", "Salinas Valley, CA"),
        ("Stanley Black & Decker Dist.", "orders@stanleybd.com", "+1 (555) 222-3344", "New Britain, CT"),
        ("California Dairy Co-op", "supply@caldairy.com", "+1 (555) 333-4455", "Modesto, CA"),
        ("French Mill Flour Imports", "import@frenchmill.com", "+1 (555) 444-5566", "Montreal, QC"),
        ("Pfizer Consumer Health Direct", "rxsupply@pfizer.com", "+1 (555) 555-6677", "New York, NY"),
        ("Anker Innovations Logistics", "b2b@anker.com", "+1 (555) 666-7788", "Seattle, WA"),
        ("Purina Pet Nutrition Hub", "wholesale@purina.com", "+1 (555) 777-8899", "St. Louis, MO"),
        ("Midori Japanese Paper Imports", "dist@midoripaper.com", "+1 (555) 888-9900", "Tokyo / San Francisco"),
        ("Organic Mills Cotton Co.", "fabric@organicmills.com", "+1 (555) 999-0011", "Austin, TX"),
        ("Dutch Artisan Cheese Exporters", "cheese@dutchdairy.com", "+1 (555) 000-1122", "Amsterdam / NY"),
    ]

    for idx, (sname, semail, sphone, saddr) in enumerate(suppliers_data):
        st = all_created_stores[idx % len(all_created_stores)]
        sup_obj, _ = Supplier.objects.get_or_create(
            store=st,
            name=sname,
            defaults={"email": semail, "phone": sphone, "address": saddr}
        )

        # Create receiving purchase record
        p_cost = Decimal("450.00") + Decimal(str(idx * 45))
        purch_obj, _ = Purchase.objects.get_or_create(
            store=st,
            purchase_number=f"PO-2026-10{idx+1:02d}",
            defaults={
                "supplier": sup_obj,
                "status": PurchaseStatus.RECEIVED,
                "subtotal": p_cost,
                "additional_charges": Decimal("25.00"),
                "total_cost": p_cost + Decimal("25.00"),
                "received_date": timezone.now(),
                "notes": f"Full procurement batch #{idx+1} received in sound warehouse condition."
            }
        )

    print(f"  ✅ Suppliers & Purchases seeded: {Supplier.objects.count()} suppliers, {Purchase.objects.count()} purchases.")

    # 7. ROUTINE SHOPPING TEMPLATES (10+ Items)
    templates_data = [
        ("Weekly Family Groceries", "Routine weekly fruits, dairy, whole wheat bread and farm eggs", 1),
        ("Home DIY Wall Repair Kit", "Screws, drywall anchors, hammer, and tape measure essentials", 2),
        ("Weekend Organic Detox Cleanse", "Fresh avocados, cold-pressed raw green juice, and baby kale", 3),
        ("Sunday Morning French Breakfast", "Fresh butter croissants, pain au chocolat, and dark roast beans", 4),
        ("First Aid & Immune Essentials", "Vitamin C, omega-3 softgels, adhesive bandages, and thermometer", 5),
        ("Work From Home Tech Setup", "65W fast charger, braided USB-C cable, and ANC wireless earbuds", 6),
        ("Monthly Dog Nutrition Pack", "Grain-free salmon kibble and natural beef tendon dental chews", 7),
        ("Creative Bullet Journal Starter", "Dotted grid journal, mechanical pencil, and fine calligraphy pen", 8),
        ("Minimalist Weekend Wardrobe", "Heavyweight black tee and durable utility canvas tote bag", 9),
        ("Wine & Gourmet Cheese Night", "18-month aged cheddar, parmigiano reggiano, and French brie wheel", 10),
    ]

    for tname, tdesc, store_idx in templates_data:
        st = all_created_stores[(store_idx - 1) % len(all_created_stores)]
        tmpl, created = StoreMemoTemplate.objects.get_or_create(
            user=customer,
            store=st,
            name=tname,
            defaults={"description": tdesc}
        )
        if created:
            for p in Product.objects.filter(store=st)[:3]:
                StoreMemoTemplateItem.objects.create(
                    template=tmpl,
                    product=p,
                    quantity=Decimal("2.000"),
                    notes="Store routine item"
                )

    print(f"  ✅ Routine basket templates seeded: {StoreMemoTemplate.objects.count()}")

    print("\n🎉 MASTER PRODUCTION DATA SEED COMPLETED SUCCESSFULLY!")
    print(f"  • Stores: {Store.objects.count()}")
    print(f"  • Categories: {Category.objects.count()}")
    print(f"  • Products: {Product.objects.count()}")
    print(f"  • Orders: {Order.objects.count()}")
    print(f"  • Customer Addresses: {CustomerAddress.objects.count()}")
    print(f"  • Reviews: {StoreReview.objects.count()}")
    print(f"  • Suppliers: {Supplier.objects.count()}")
    print(f"  • Purchases: {Purchase.objects.count()}")
    print(f"  • Basket Templates: {StoreMemoTemplate.objects.count()}")

if __name__ == '__main__':
    run()
