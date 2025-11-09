from django.db import models

# Create your models here.


class Category(models.Model):
  name = models.CharField(max_length=100,unique=True)

  def save(self, *args, **kwargs):
    self.name= self.name.title()
    super().save(*args, **kwargs)