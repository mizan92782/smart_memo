

def ProductImagePath(instance, filename):
    from products.models import Product
    return f'products/{instance.category}/{instance.id}/{filename}'