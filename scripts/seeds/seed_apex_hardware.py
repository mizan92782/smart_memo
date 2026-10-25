import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, '/home/mizan/Desktop/smart_memo')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_memo.settings')
django.setup()

from stores.models.store_mod import Store
from categories.models.category_mod import Category
from products.models.product_mod import Product, MeasurementUnit
from products.models.product_image_mod import ProductImage
from inventory.models.inventory_mod import StockBalance
from users.models.user_mod import User

def run():
    print("Seeding Apex Hardware & Tools (apexhardware.com)...")
    vendor = User.objects.filter(role="vendor").first()
    if not vendor:
        print("Vendor user not found.")
        return

    # Update or create Store 2
    store2, _ = Store.objects.get_or_create(
        id=2,
        defaults={
            "vendor": vendor,
            "name": "Apex Hardware & Tools",
            "slug": "apex-hardware-tools",
            "public_url_slug": "apexhardware.com",
        }
    )

    # Set rich branding
    store2.name = "Apex Hardware & Tools"
    store2.slug = "apex-hardware-tools"
    store2.public_url_slug = "apexhardware.com"
    store2.owner_name = "Bob Vendor"
    store2.phone_number = "+1 (555) 876-5432"
    store2.whatsapp_number = "+1 (555) 876-5432"
    store2.email = "apex@example.com"
    store2.website_url = "https://apexhardware.com"
    store2.shop_type = "hybrid"
    store2.address = "742 Evergreen Terrace, Suite 100"
    store2.opening_time = "07:30"
    store2.closing_time = "20:00"
    store2.is_active = True
    store2.is_verified = True
    store2.average_rating = Decimal("4.90")
    store2.total_reviews = 48
    store2.delivery_enabled = True
    store2.pickup_enabled = True
    store2.delivery_fee = Decimal("8.50")
    store2.min_order_amount = Decimal("25.00")
    store2.logo_url = "https://images.unsplash.com/photo-1581783342308-f792dbdd27c5?w=300&auto=format&fit=crop&q=80"
    store2.cover_photo_url = "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=1600&auto=format&fit=crop&q=80"
    store2.save()

    print("  Created/Updated store branding for Apex Hardware.")

    # Categories
    cat_power, _ = Category.objects.get_or_create(store=store2, name="Power Tools")
    cat_hand, _ = Category.objects.get_or_create(store=store2, name="Hand Tools")
    cat_fasteners, _ = Category.objects.get_or_create(store=store2, name="Fasteners & Hardware")
    cat_electrical, _ = Category.objects.get_or_create(store=store2, name="Electrical & Lighting")
    cat_safety, _ = Category.objects.get_or_create(store=store2, name="Safety & Protective Gear")

    print(f"  Created categories for Apex Hardware: Power Tools, Hand Tools, Fasteners, Electrical, Safety.")

    hardware_products = [
        {
            "name": "DeWalt 20V MAX Cordless Drill Kit",
            "second_name": "Brushless Compact Drill / Driver with 2 Batteries",
            "category": cat_power,
            "barcode": "885911497210",
            "sku": "DW-D20V",
            "aisle": "Aisle 4",
            "shelf_location": "Aisle 4 - Power Tools Bay 1",
            "price": Decimal("129.99"),
            "cost_price": Decimal("85.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 25,
            "tags": ["dewalt", "drill", "cordless", "powertools"],
            "image_url": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=600&auto=format&fit=crop&q=80",
            "description": "High-performance brushless motor delivers 340 unit watts out (UWO) for heavy-duty drilling and fastening applications."
        },
        {
            "name": "Stanley 25-Foot PowerLock Tape Measure",
            "second_name": "Classic Chrome Case with BladeArmor Coating",
            "category": cat_hand,
            "barcode": "076174334289",
            "sku": "ST-TM25",
            "aisle": "Aisle 2",
            "shelf_location": "Aisle 2 - Measurement Rack B",
            "price": Decimal("14.99"),
            "cost_price": Decimal("8.50"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 60,
            "tags": ["stanley", "tape measure", "hand tools"],
            "image_url": "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=600&auto=format&fit=crop&q=80",
            "description": "Durable die-cast metal case with 7-foot standout. BladeArmor coating on the first 3 inches maximizes durability."
        },
        {
            "name": "Estwing 16-Ounce Steel Curved Claw Hammer",
            "second_name": "Solid American Steel with Shock Reduction Grip",
            "category": cat_hand,
            "barcode": "034139622119",
            "sku": "ES-H16",
            "aisle": "Aisle 2",
            "shelf_location": "Aisle 2 - Striking Tools Wall",
            "price": Decimal("29.50"),
            "cost_price": Decimal("18.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 40,
            "tags": ["estwing", "hammer", "claw", "hand tools"],
            "image_url": "https://images.unsplash.com/photo-1586864387789-628af9feed72?w=600&auto=format&fit=crop&q=80",
            "description": "Forged in one piece of genuine American steel. Patented nylon vinyl grip reduces impact vibration by up to 70%."
        },
        {
            "name": "Milwaukee Shockwave 40-Piece Impact Bit Set",
            "second_name": "Custom Alloy76 Steel Impact Driver Bits",
            "category": cat_power,
            "barcode": "045242509126",
            "sku": "MW-BS40",
            "aisle": "Aisle 4",
            "shelf_location": "Aisle 4 - Drill Bits Bin C",
            "price": Decimal("19.99"),
            "cost_price": Decimal("11.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 35,
            "tags": ["milwaukee", "bits", "impact", "powertools"],
            "image_url": "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=600&auto=format&fit=crop&q=80",
            "description": "Engineered for extreme durability and up to 50x life. Optimized Shockzone absorbs peak torque and prevents breaking."
        },
        {
            "name": "Heavy-Duty Zinc Drywall Screws & Anchors (200 pcs)",
            "second_name": "Self-Drilling Wall Anchors with Screws Kit",
            "category": cat_fasteners,
            "barcode": "078234123891",
            "sku": "FA-DW200",
            "aisle": "Aisle 5",
            "shelf_location": "Aisle 5 - Fasteners Bin 12",
            "price": Decimal("12.50"),
            "cost_price": Decimal("6.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 100,
            "tags": ["screws", "anchors", "fasteners", "hardware"],
            "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80",
            "description": "Self-drilling hollow wall anchors hang up to 50 lbs without pre-drilling holes in drywall, sheetrock, and gypsum."
        },
        {
            "name": "Klein Tools Digital Multimeter & Voltage Tester",
            "second_name": "Auto-Ranging 600V AC/DC Electrician Meter",
            "category": cat_electrical,
            "barcode": "092644690181",
            "sku": "KT-MM01",
            "aisle": "Aisle 3",
            "shelf_location": "Aisle 3 - Electrical Testing Display",
            "price": Decimal("49.95"),
            "cost_price": Decimal("31.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 20,
            "tags": ["klein", "multimeter", "electrical", "tester"],
            "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
            "description": "Measures up to 600V AC/DC voltage, 10A DC current, and 2M resistance. CAT III 600V safety rating for professional trade use."
        },
        {
            "name": "3M Professional Safety Glasses & Ear Protection Kit",
            "second_name": "Anti-Fog Scratch Resistant Glasses + NRR 29dB Muffs",
            "category": cat_safety,
            "barcode": "051131070243",
            "sku": "3M-SAF01",
            "aisle": "Aisle 1",
            "shelf_location": "Aisle 1 - PPE Safety Station",
            "price": Decimal("16.00"),
            "cost_price": Decimal("9.50"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 50,
            "tags": ["3m", "safety", "glasses", "ppe"],
            "image_url": "https://images.unsplash.com/photo-1584744982491-665216d95f8b?w=600&auto=format&fit=crop&q=80",
            "description": "ANSI Z87.1 certified impact resistant eye protection paired with high-performance acoustic hearing protection."
        },
        {
            "name": "Gorilla Heavy-Duty Waterproof Duct Tape (35 yd)",
            "second_name": "Triple Layer Strength Tough Weatherproof Adhesive",
            "category": cat_fasteners,
            "barcode": "052427600120",
            "sku": "GT-DT35",
            "aisle": "Aisle 5",
            "shelf_location": "Aisle 5 - Adhesives Shelf C",
            "price": Decimal("9.99"),
            "cost_price": Decimal("5.50"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 75,
            "tags": ["gorilla", "tape", "waterproof", "fasteners"],
            "image_url": "https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?w=600&auto=format&fit=crop&q=80",
            "description": "Double-thick adhesive grips smooth, rough, and uneven surfaces including wood, stone, stucco, brick, metal, and vinyl."
        },
        {
            "name": "Channellock 10-Inch Tongue and Groove Pliers",
            "second_name": "Laser-Hardened Right Angle Teeth Plier",
            "category": cat_hand,
            "barcode": "025582310107",
            "sku": "CL-P10",
            "aisle": "Aisle 2",
            "shelf_location": "Aisle 2 - Plumbing & Pliers Rack",
            "price": Decimal("22.00"),
            "cost_price": Decimal("13.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 30,
            "tags": ["channellock", "pliers", "hand tools"],
            "image_url": "https://images.unsplash.com/photo-1581783342308-f792dbdd27c5?w=600&auto=format&fit=crop&q=80",
            "description": "Undercut tongue & groove design won't slip. PermaLock fastener eliminates nut and bolt failure. Iconic blue comfort grips."
        },
        {
            "name": "LED Ultra-Bright 1000lm Jobsite Work Light",
            "second_name": "Rechargeable Magnetic Base Construction Light",
            "category": cat_electrical,
            "barcode": "088712399014",
            "sku": "EL-WL1000",
            "aisle": "Aisle 3",
            "shelf_location": "Aisle 3 - Work Lighting Bay",
            "price": Decimal("34.50"),
            "cost_price": Decimal("19.00"),
            "measure": 1,
            "unit": MeasurementUnit.PIECE,
            "stock": 25,
            "tags": ["led", "worklight", "rechargeable", "electrical"],
            "image_url": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=600&auto=format&fit=crop&q=80",
            "description": "1000 lumens TrueView high-definition lighting output. Heavy-duty magnetic base attaches firmly to metal studs and pipes."
        }
    ]

    for pdata in hardware_products:
        img_url = pdata.pop("image_url")
        prod, created = Product.objects.get_or_create(
            store=store2,
            name=pdata["name"],
            defaults=pdata
        )
        if not created:
            for k, v in pdata.items():
                setattr(prod, k, v)
            prod.save()

        if img_url:
            ProductImage.objects.get_or_create(
                product=prod,
                image_url=img_url,
                defaults={"is_primary": True, "display_order": 0, "alt_text": prod.name}
            )

        # Inventory balance
        StockBalance.objects.get_or_create(
            store=store2,
            product=prod,
            defaults={
                "on_hand": Decimal(str(pdata.get("stock", 20))),
                "reserved": Decimal("0.000"),
                "low_stock_threshold": Decimal("5.000"),
            }
        )

    print(f"✅ Successfully seeded {len(hardware_products)} products for Apex Hardware & Tools!")

if __name__ == '__main__':
    run()
