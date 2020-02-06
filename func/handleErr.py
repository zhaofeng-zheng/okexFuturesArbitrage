from ccxt import RequestTimeout, ExchangeError, ExchangeNotAvailable, DDoSProtection, NetworkError
import time


def handle_ddos_protection(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except DDoSProtection:
                print('DDoS protection from {}, retry,,,'.format(func.__name__))
                time.sleep(5)
    return inner


def http_exception_logger(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except (ExchangeError, ExchangeNotAvailable, RequestTimeout, NetworkError) as err:
                print(f"error message from {func.__name__}, {err}")
                continue
    inner.__name__ = func.__name__
    return inner

