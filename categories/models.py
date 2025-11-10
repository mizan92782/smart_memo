from django.db import models
from django.urls import reverse
# Create your models here.


class Category(models.Model):
  name = models.CharField(max_length=100,unique=True)

  def save(self, *args, **kwargs):
    self.name= self.name.title()
    super().save(*args, **kwargs)

  def __str__(self):
      return self.name
  

  #! its take a instance of category (by self) and return the url name with wtih neccessry data: in kwgs 
  #! "url-name" defines templated will get this data: such that self.pk,self.name

  def get_category_products_url(self):  # will take a instance
     return reverse('category_products', kwargs={'pk': self.pk })