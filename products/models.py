from email.policy import default
from django.db import models

from enums.unit_enums import MeasurementUnit
from utilities.product_images_path import ProductImagePath

from enums.currency_unit import CurrencyUnit
from enums.unit_enums import MeasurementUnit
from utilities.products_default_description import product_default_description 
from categories.models import Category
from django.contrib.postgres.fields import ArrayField


# Create your models here.

"""Generate default description for Category model field."""



'''Product model representing an item for sale.'''
class Product(models.Model):
    
    name = models.CharField(max_length=200)
    second_name = models.CharField(max_length=200,default="")
    description = models.TextField( default=product_default_description )
    tags = ArrayField(
        models.CharField(max_length=10),
        size=5,  # Optional: Array length
        blank=True,
        default=list
    )

    category = models.ForeignKey(Category, on_delete=models.SET_DEFAULT,default="Others" ,related_name='products')

    measure  = models.SmallIntegerField(blank=False, null=False, default=1)
    unit = models.CharField(max_length=10, choices=MeasurementUnit.choices,default=MeasurementUnit.KILOGRAM )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=10, choices=CurrencyUnit.choices ,default=CurrencyUnit.BDT)
    stock = models.DecimalField(max_digits=10, decimal_places=2,default=5)
    
    offer = models.BooleanField(default=False)
    offered_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    offered_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    offer_start_date= models.DateTimeField(null=True, blank=True)
    offer_end_date= models.DateTimeField(null=True, blank=True)

    offered_count= models.SmallIntegerField(default=0)
    offered_count_unit= models.CharField(max_length=10, choices=MeasurementUnit.choices) 
    
    image = models.ImageField(upload_to=ProductImagePath,)

    def is_in_stock(self):
        return self.stock > 0
    

    def save(self, *args, **kwargs):
      self.name= self.name.title()

      self.tags.append(self.name)
      self.tags.append(self.second_name)
      self.tags.append(self.category.name)


      self.offered_price = self.price - (self.price * (self.offered_discount / 100))

      super().save(*args, **kwargs)
          
      

    def __str__(self):
        return f'{self.name} - {self.category}'
