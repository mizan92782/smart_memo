from django.db import models

class CurrencyUnit(models.TextChoices):
    BDT = 'TK', 'Taka'
    USD = 'USD', 'US Dollar'
    EUR = 'EUR', 'Euro'
    GBP = 'GBP', 'British Pound'
    JPY = 'JPY', 'Japanese Yen'
    AUD = 'AUD', 'Australian Dollar'
    CAD = 'CAD', 'Canadian Dollar'
    CHF = 'CHF', 'Swiss Franc'
    CNY = 'CNY', 'Chinese Yuan'
    INR = 'INR', 'Indian Rupee'

