from impl.mac.app import MacApp


class Brave(MacApp):
    brand = 'Brave Browser'
    product_title = 'Brave'
    channels = ('nightly', 'beta', 'release')
    bundle_id_suffix = ''


class Origin(MacApp):
    brand = 'Brave Origin'
    product_title = 'Origin'
    channels = ('nightly', 'beta')
    bundle_id_suffix = '.origin'


PRODUCTS = {product.product_title: product for product in (Brave, Origin)}


def get_all_apps():
    for product in PRODUCTS.values():
        for channel in product.channels:
            yield product(channel)


def get_apps_with_profiles():
    return [app for app in get_all_apps() if app.has_profile]
