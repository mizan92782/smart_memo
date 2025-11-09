from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from categories.models import Category

DEFAULT_CATEGORIES = [
    "Beverages",
    "Bakery",
    "Dairy",
    "Produce",
    "Frozen",
    "Meat",
    "Seafood",
    "Pantry",
    "Snacks",
    "Condiments",
    "Spices & Seasonings",
    "Canned Goods",
    "Grains & Pasta",
    "Breakfast & Cereal",
    "Baking Supplies",
    "Oils & Vinegars",
    "Baby Food",
    "Pet Food",
    "Sweets & Candy",

    # --- Household Essentials ---
    "Household",
    "Cleaning Supplies",
    "Laundry",
    "Paper Products",
    "Toiletries",
    "Personal Care",
    "Health & Wellness",
    "Beauty & Skincare",
    "Medicines & First Aid",

    # --- Others ---
    "Electronics",
    "Stationery",
    "Home & Kitchen",
    "Garden & Outdoor",
    "Toys & Games",
    "Automotive",
    "Clothing",
    "Footwear",
    "Sports & Fitness",
    "Books & Magazines",
]


class Command(BaseCommand):
  help = "Add categories to the Category model. Provide names on the command line or with --file."

  def handle(self, *args, **options):
    catogories_to_add = []
    for category_name in DEFAULT_CATEGORIES:
      catogories_to_add.append(Category(name=category_name))
    
    Category.objects.bulk_create(catogories_to_add, ignore_conflicts=True)
    self.stdout.write(self.style.SUCCESS(f"Successfully added default categories."))