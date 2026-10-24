from django.contrib import admin
from cards.models.card_mod import Card, CardItem


class CardItemInline(admin.TabularInline):
    model = CardItem
    extra = 1


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    inlines = [CardItemInline]
    list_display = ('id', 'title', 'user', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('title', 'user__email')


@admin.register(CardItem)
class CardItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'card', 'product', 'quantity', 'unit_price')
    list_filter = ('card',)
