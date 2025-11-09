from django.db import connection
from categories.models import Category
from products.models import Product


def run():

  pro= Category.objects.prefetch_related('products').all()
  
  for x in pro:
    print(x.name)
    print(x.products.count())

  
  print(len(connection.queries))
  