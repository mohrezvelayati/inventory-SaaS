from catalog.models import Category, Product, ProductVariant



def create_category(*, store, name):
    """
    Create a new category for a store.
    """
    category = Category.objects.create(store=store, name=name)
    return category


def create_product(*, store, name, description, categories):
    """
    Create a new product for a store.
    """
    product = Product.objects.create(store=store, name=name, description=description)
    product.category.set(categories)
    return product



def create_product_variant(*, product, size, purchase_price, sale_price, current_stock):
    """
    Create a new product variant for a product.
    """
    variant = ProductVariant.objects.create(
        product=product,
        size=size,
        purchase_price=purchase_price,
        sale_price=sale_price,
        current_stock=current_stock
    )
    return variant



def create_variant(*, product, size, purchase_price, sale_price):
    return ProductVariant.objects.create(
        product=product,
        size=size,
        purchase_price=purchase_price,
        sale_price=sale_price
    )
