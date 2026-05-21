import warnings

# macOS uses LibreSSL. Suppress the spurious associated warning.
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL')
