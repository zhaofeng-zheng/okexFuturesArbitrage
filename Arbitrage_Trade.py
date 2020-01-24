from future_arbitrageur import FutureArbitrageur

# apiKeys = ['8ec2e0c2-0807-438e-8140-1476387e4aad', 'fd31987e-3adf-4307-a5b8-89fe055a6fe8',  '9d76655a-ee88-4442-842d-610f226a716b']
apiKeys = ['fc8e4be5-542b-44dc-a310-bd6f6cdce618']
# secret = ['8947260FDAA0EC1246D56B4CEB03AC3C', '06485AFEF0C61D7E9F6B4C6626C60652', '3823E2802EF08634DF86417E4170CE8D']
secret = ['8C61BB59A81A8768DD3DB48F9C9B5D03']
password = ['zhengzhaofeng98']

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
