import pandas as pd
from ccxt import okex3
import time
from multiprocessing.dummy import Pool as ThreadPool
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

pd.set_option('expand_frame_repr', False)

exchange = okex3()
contracts = exchange.futuresGetInstruments()
depth_size = 10
# frequency in seconds
fetch_frequency = 0.2

futures_contracts = []
length = len(contracts)
for index in range(0, length, 3):
    week_contract_id = contracts[index]['instrument_id']
    next_week_contract_id = contracts[index + 1]['instrument_id']
    season_contract_id = contracts[index + 2]['instrument_id']
    if week_contract_id.split('-')[0] in ('BTC', 'ETH', 'EOS', 'BSV', 'BCH') and week_contract_id.split('-')[1] == season_contract_id.split('-')[1] == 'USD':
        futures_contracts.append((week_contract_id, next_week_contract_id, season_contract_id))
futures_contracts.sort(key=lambda tple: tple[0][:3])


def obtain_futures_ticker(instrument_id, size=depth_size):
    while True:
        try:
            ticker = exchange.futuresGetInstrumentsInstrumentIdBook(
                {
                    'instrument_id': instrument_id,
                    'size': size
                }
            )
            return ticker
        except Exception as err:
            print(err)


def obtain_futures_price_difference(contracts: tuple):
    while True:
        start = time.perf_counter()
        end = time.perf_counter()
        while end - start < fetch_frequency:
            end = time.perf_counter()
            continue
        pool = ThreadPool()
        results = pool.map(obtain_futures_ticker, contracts)
        week_contract_ticker: dict = results[0]
        week_best_bid_price = float(week_contract_ticker['bids'][0][0])
        week_best_ask_price = float(week_contract_ticker['asks'][0][0])
        week_useful_bid_price = float(week_contract_ticker['bids'][depth_size-1][0])
        week_useful_ask_price = float(week_contract_ticker['asks'][depth_size-1][0])
        week_bid_depth = sum([int(week_contract_ticker['bids'][i][1]) for i in range(depth_size)])
        week_ask_depth = sum([int(week_contract_ticker['asks'][i][1]) for i in range(depth_size)])
        next_week_contract_ticker: dict = results[1]
        next_week_best_bid_price = float(next_week_contract_ticker['bids'][0][0])
        next_week_best_ask_price = float(next_week_contract_ticker['asks'][0][0])
        next_week_useful_bid_price = float(next_week_contract_ticker['bids'][depth_size-1][0])
        next_week_useful_ask_price = float(next_week_contract_ticker['asks'][depth_size-1][0])
        next_week_bid_depth = sum([int(next_week_contract_ticker['bids'][i][1]) for i in range(depth_size)])
        next_week_ask_depth = sum([int(next_week_contract_ticker['asks'][i][1]) for i in range(depth_size)])
        season_contract_ticker: dict = results[2]
        season_best_bid_price = float(season_contract_ticker['bids'][0][0])
        season_best_ask_price = float(season_contract_ticker['asks'][0][0])
        season_useful_bid_price = float(season_contract_ticker['bids'][depth_size-1][0])
        season_useful_ask_price = float(season_contract_ticker['asks'][depth_size-1][0])
        season_bid_depth = sum([int(season_contract_ticker['bids'][i][1]) for i in range(depth_size)])
        season_ask_depth = sum([int(season_contract_ticker['asks'][i][1]) for i in range(depth_size)])
        timestamp = season_contract_ticker['timestamp']
        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=11)
        timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if week_best_ask_price <= season_best_bid_price:
            eff_w_s_pd = (season_useful_bid_price / week_useful_ask_price - 1) * 100
            print(f'{contracts[0]}, {contracts[2]} pd is {eff_w_s_pd}')
        elif week_best_bid_price > season_best_ask_price:
            eff_w_s_pd = (season_useful_ask_price / week_useful_bid_price - 1) * 100
            print(f'{contracts[0]}, {contracts[2]} pd is {eff_w_s_pd}')
        if next_week_best_ask_price <= season_best_bid_price:
            eff_nw_s_pd = (season_useful_bid_price / next_week_useful_ask_price - 1) * 100
            print(f'{contracts[1]}, {contracts[2]} pd is {eff_nw_s_pd}')
        elif next_week_best_bid_price > season_best_ask_price:
            eff_nw_s_pd = (season_useful_ask_price / next_week_useful_bid_price - 1) * 100
            print(f'{contracts[1]}, {contracts[2]} pd is {eff_nw_s_pd}')
        df = pd.DataFrame()
        df = df.append([[timestamp, eff_w_s_pd, eff_nw_s_pd, week_bid_depth, week_ask_depth, next_week_bid_depth,
                         next_week_ask_depth, season_bid_depth, season_ask_depth]])
        df.rename(
            {0: 'time', 1: f'{contracts[0]} {contracts[2]}pd pct (%)',
             2: f'{contracts[1]} {contracts[2]} pd pct', 3: 'week_bid_depth',
             4: 'week_ask_depth', 5: 'next_week_bid_depth', 6: 'next_week_ask_depth', 7: 'season_bid_depth',
             8: 'season_ask_depth'}, inplace=True, axis='columns')
        filePath = Path().parent / 'data' / (contracts[0] + '-' + contracts[1] + '-' + contracts[2] + ' price difference.csv')
        fileExists = filePath.exists()
        if fileExists:
            try:
                df.to_csv(filePath, header=False, index=False, mode='a')
            except PermissionError:
                pass
        else:
            df.to_csv(filePath, header=True, index=False, mode='a')
        pool.close()


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=len(futures_contracts)) as executor:
        executor.map(obtain_futures_price_difference, futures_contracts)
