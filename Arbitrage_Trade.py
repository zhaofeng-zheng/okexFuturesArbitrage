from future_arbitrageur import FutureArbitrageur

apiKeys = []
secret = []
password = []

fa = FutureArbitrageur(apiKeys=apiKeys,
                       secret=secret,
                       password=password,
                       recent_contract='BTC-USD-200131',
                       next_week_contract='BTC-USD-200207',
                       distant_contract='BTC-USD-200327',
                       leverage=50,
                       contract_value=100,
                       midline=1.6,
                       grid_width=1.5,
                       fetch_frequency=0.1)

if __name__ == '__main__':
    fa.start()
# fa.apiKey = fa.apiKeys_lst[0]
# fa.secret = fa.secret_lst[0]
# fa.password = fa.password_lst[0]
# fa.recent_contract_position_obj = fa.pool.apply_async(func=fa._get_position, kwds={
#     'instrument_id': fa.recent_contract,
#     'direction': 'both'
# })
# fa.distant_contract_position_obj = fa.pool.apply_async(func=fa._get_position, kwds={
#     'instrument_id': fa.distant_contract,
#     'direction': 'both'
# })
# fa.account_equity_obj = fa.pool.apply_async(func=fa._get_account_equity, kwds={
#     'instrument_id': fa.recent_contract
# })
# fa.execute((-1,))
