

def categories_processor(request):
    from .models import Category
    
    categories = Category.objects.all().order_by('name')
    return {'categories': categories}  # key = variable name
