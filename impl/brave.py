from impl.mac.browser import Brave, Origin


PRODUCTS = {product.product_title: product for product in (Brave, Origin)}


def get_all_apps():
    for product in PRODUCTS.values():
        yield from product.get_apps()


def get_apps_with_profiles():
    return [app for app in get_all_apps() if app.has_profile]
