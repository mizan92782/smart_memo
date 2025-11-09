from django.shortcuts import render

from categories.models import Category

# Create your views here.
def homepage(request):
    cat = Category.objects.all()
    return render(request, 'home.html', {'categories': cat})