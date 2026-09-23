import sys

if sys.platform == 'win32':
    from impl.win.browser import Brave, Origin
else:
    from impl.mac.browser import Brave, Origin


PRODUCTS = {product.product_title: product for product in (Brave, Origin)}


def get_all_apps():
    for product in PRODUCTS.values():
        yield from product.get_apps()


def get_apps_with_profiles():
    # All architectures and levels of a channel share one profile. Only return
    # one app per profile:
    result = {}
    for app in get_all_apps():
        if app.has_profile:
            result[tuple(app.profile_paths)] = app
    return list(result.values())
