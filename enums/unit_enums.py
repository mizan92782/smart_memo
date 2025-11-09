from django.db import models

class MeasurementUnit(models.TextChoices):
    # Weight
    MILLIGRAM = 'mg', 'Milligram'
    GRAM = 'g', 'Gram'
    KILOGRAM = 'kg', 'Kilogram'
    TONNE = 't', 'Tonne'

    # Volume
    MILLILITER = 'ml', 'Milliliter'
    LITER = 'l', 'Liter'
    CUBIC_METER = 'm3', 'Cubic Meter'

    # Length
    MILLIMETER = 'mm', 'Millimeter'
    CENTIMETER = 'cm', 'Centimeter'
    METER = 'm', 'Meter'
    KILOMETER = 'km', 'Kilometer'
    INCH = 'in', 'Inch'
    FOOT = 'ft', 'Foot'
    YARD = 'yd', 'Yard'

    # Count / Piece
    PIECE = 'pc', 'Piece'
    DOZEN = 'dz', 'Dozen'
    PAIR = 'pr', 'Pair'

