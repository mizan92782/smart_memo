try:
    import lorem
    def product_default_description():
        return lorem.paragraph()
except ImportError:
    def product_default_description():
        return "Default product description."

