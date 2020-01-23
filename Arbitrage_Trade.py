from future_arbitrageur import FutureArbitrageur

# enter your apiKeys, secret and password here. Can enter multiple accounts,
# However, they must be of the same length (e.g. len(apiKeys) == len(secret) == len(password))
# Otherwise, a TypeError is thrown.
apiKeys = ['']
secret = ['']
password = ['']

fa = FutureArbitrageur(apiKeys=apiKeys,
                       secret=secret,
                       password=password,
                       recent_contract='BTC-USD-200124',
                       next_week_contract='BTC-USD-200131',
                       distant_contract='BTC-USD-200327',
                       leverage=50,
                       contract_value=100,
                       midline=1.6,
                       grid_width=1.5,
                       fetch_frequency=0.1)

if __name__ == '__main__':
    fa.start()