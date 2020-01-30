import time
import calendar
from multiprocessing.pool import ThreadPool
from ccxt import okex3
from ccxt import RequestTimeout, ExchangeError, ExchangeNotAvailable, DDoSProtection
import datetime
from multiprocessing import Process
exchange = okex3()
depth_size = 10


def handle_ddos_protection(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except DDoSProtection as err:
                print('DDoS protection{}, retry,,,'.format(err))
                time.sleep(5)
    return inner


def http_exception_logger(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except (ExchangeError, ExchangeNotAvailable) as err:
                with open('./log/exception_log.txt', mode='a') as f:
                    f.write('time: {}, [Error] {}\n'.format(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'), err))
                print('http_exception_logger updated')
    return inner

@handle_ddos_protection
@http_exception_logger # obtain_futures_orderbook = http_exception_logge(obtain_futures_orderbook)
def obtain_futures_orderbook(instrument_id, size=depth_size):
    while True:
        try:
            ticker = exchange.futuresGetInstrumentsInstrumentIdBook(
                {
                    'instrument_id': instrument_id,
                    'size': size
                }
            )
            return ticker
        except RequestTimeout as err:
            print(err)
            continue


def obtain_futures_price_difference(contracts: tuple):
    pool = ThreadPool()
    results = pool.map(obtain_futures_orderbook, contracts)
    print(results)
    week_contract_ticker: dict = results[0]
    week_best_bid_price = float(week_contract_ticker['bids'][0][0])
    week_best_ask_price = float(week_contract_ticker['asks'][0][0])
    week_useful_bid_price = float(week_contract_ticker['bids'][depth_size - 1][0])
    week_useful_ask_price = float(week_contract_ticker['asks'][depth_size - 1][0])
    season_contract_ticker: dict = results[1]
    season_best_bid_price = float(season_contract_ticker['bids'][0][0])
    season_best_ask_price = float(season_contract_ticker['asks'][0][0])
    season_useful_bid_price = float(season_contract_ticker['bids'][depth_size - 1][0])
    season_useful_ask_price = float(season_contract_ticker['asks'][depth_size - 1][0])
    # 做多当周，做空季度
    if week_best_ask_price <= season_best_bid_price:
        effective_price_difference_pct_open_short = (season_useful_bid_price / week_useful_ask_price - 1) * 100
        return effective_price_difference_pct_open_short
    # 做多季度， 做空当周
    elif week_best_bid_price > season_best_ask_price:
        effective_price_difference_pct_open_long = (season_useful_ask_price / week_useful_bid_price - 1) * 100
        return effective_price_difference_pct_open_long


class FutureArbitrageur(okex3):
    def __init__(self, *, apiKeys, secret, password, trade_coin, quote_coin,leverage,
                 contract_value, midline, grid_width, fetch_frequency=1):
        super().__init__()
        if apiKeys.__class__ is not str and secret.__class__ is not str and password is not str:
            if not len(apiKeys) == len(secret) == len(password):
                raise TypeError('传入参数长短不一')
            else:
                pass
            self.apiKeys_lst = list(apiKeys)
            self.secret_lst = list(secret)
            self.password_lst = list(password)
        else:
            self.apiKeys_lst = list((apiKeys,))
            self.secret_lst = list((secret,))
            self.password_lst = list((password,))
        self.trade_coin = trade_coin.upper()
        self.quote_coin = quote_coin.upper()

        self.recent_contract = None
        self.next_week_contract = None
        self.distant_contract = None
        self.synthesize_n_update_contracts()

        self.leverage = leverage
        self.contract_value = contract_value
        self.midline = midline
        self.grid_width = grid_width
        for num_pos, num_neg in zip(range(1, len(self.apiKeys_lst) + 1), range(-len(self.apiKeys_lst), 0)):
            setattr(self, 'grid' + str(num_pos), self.midline + self.grid_width * num_pos)
            setattr(self, 'grid' + str(num_neg), self.midline + self.grid_width * num_neg)
        self.fetch_frequency = fetch_frequency
        self.recent_contract_position_obj = None
        self.distant_contract_position_obj = None
        self.account_equity_obj = None
        self.pool = None

    def start(self):
        # /*
        # 程序入口
        secondary_process = Process(target=self.recent_contract_rollover)
        main_process = Process(target=self.monitor_price_difference)
        main_process.start()
        secondary_process.start()
        # */

    def monitor_price_difference(self):
        price_difference0 = obtain_futures_price_difference((self.recent_contract, self.distant_contract))
        self.pool = ThreadPool()
        while True:
            start = time.perf_counter()
            end = time.perf_counter()
            while end - start <= self.fetch_frequency:
                end = time.perf_counter()
                continue
            price_difference1 = obtain_futures_price_difference((self.recent_contract, self.distant_contract))
            # 程序入口
            self.signal_generator(pd0=price_difference0, pd1=price_difference1)
            print('prvious pd is {:.4f} >>> current pd is {:.4f}\n'.format(price_difference0, price_difference1))
            price_difference0 = price_difference1

    def signal_generator(self, *, pd0, pd1):
        # 由上往下穿过中线，平空价差
        if pd1 < self.midline < pd0:
            account = 0
            self.apiKey = self.apiKeys_lst[account]
            self.secret = self.secret_lst[account]
            self.password = self.password_lst[account]
            self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                'instrument_id': self.recent_contract,
                'direction': 'both'
            })
            self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                'instrument_id': self.distant_contract,
                'direction': 'both'
            })
            self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                'instrument_id': self.recent_contract
            })
            # 平空
            self.execute((-1, 0))
            print(f'account {account}')
        # 由下往上穿过中线， 平多价差
        elif pd1 > self.midline > pd0:
            account = 0
            self.apiKey = self.apiKeys_lst[account]
            self.secret = self.secret_lst[account]
            self.password = self.password_lst[account]
            self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                'instrument_id': self.recent_contract,
                'direction': 'both'
            })
            self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                'instrument_id': self.distant_contract,
                'direction': 'both'
            })
            self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                'instrument_id': self.recent_contract
            })
            # 平多
            self.execute((1, 0))
            print(f'account {account}')

        for i, (num_pos, num_neg) in enumerate(zip(range(1, len(self.apiKeys_lst) + 1),
                                                   range(-len(self.apiKeys_lst), 0))):
            # 由下往上穿过网格， 做空价差
            if pd1 > getattr(self, 'grid' + str(num_pos)) > pd0:
                account = i
                self.apiKey = self.apiKeys_lst[account]
                self.secret = self.secret_lst[account]
                self.password = self.password_lst[account]
                self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                    'instrument_id': self.recent_contract,
                    'direction': 'both'
                })
                self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                    'instrument_id': self.distant_contract,
                    'direction': 'both'
                })
                self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                    'instrument_id': self.recent_contract
                })
                # 开空
                self.execute((-1,))
                print(f'account {account}')
            # 由上往下穿过网格， 做多价差
            elif pd1 < getattr(self, 'grid' + str(num_neg)) < pd0:
                account = i
                self.apiKey = self.apiKeys_lst[account]
                self.secret = self.secret_lst[account]
                self.password = self.password_lst[account]
                self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                    'instrument_id': self.recent_contract,
                    'direction': 'both'
                })
                self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                    'instrument_id': self.distant_contract,
                    'direction': 'both'
                })
                self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                    'instrument_id': self.recent_contract
                })
                # 开多
                self.execute((1,))
                print(f'account {account}')
            # 由上往下穿过网格， 平空价差
            elif pd1 < getattr(self, 'grid' + str(num_pos)) < pd0:
                if i < len(self.apiKeys_lst)-1:
                    account = i + 1
                    self.apiKey = self.apiKeys_lst[account]
                    self.secret = self.secret_lst[account]
                    self.password = self.password_lst[account]
                    self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 'both'
                    })
                    self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 'both'
                    })
                    self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                        'instrument_id': self.recent_contract
                    })
                    # 平空
                    self.execute((-1, 0))
                    print(f'account {account}')
                else:
                    continue
            # 由下往上穿过网格， 平多价差
            elif pd1 > getattr(self, 'grid' + str(num_neg)) > pd0:
                if i < len(self.apiKeys_lst)-1:
                    account = i + 1
                    self.apiKey = self.apiKeys_lst[account]
                    self.secret = self.secret_lst[account]
                    self.password = self.password_lst[account]
                    self.recent_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 'both'
                    })
                    self.distant_contract_position_obj = self.pool.apply_async(func=self._get_contract_holding_number, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 'both'
                    })
                    self.account_equity_obj = self.pool.apply_async(func=self._get_account_equity, kwds={
                        'instrument_id': self.recent_contract
                    })
                    # 平多
                    self.execute((1, 0))
                    print(f'account {account}')
                else:
                    continue
            else:
                continue

    def _fetch_futures_ticker(self, instrument_id: str) -> dict:
        while True:
            try:
                return self.futuresGetInstrumentsInstrumentIdTicker({
                    'instrument_id': instrument_id
                })
            except RequestTimeout as err:
                print(f'Timeout while fetching {instrument_id} ticker, retry.... [Error]: {err}')
                continue

    @http_exception_logger
    def _get_position_info(self, instrument_id: str) -> dict:
        return self.futuresGetInstrumentIdPosition({
            'instrument_id': instrument_id
        })['holding'][0]

    def _get_contract_holding_number(self, *, instrument_id: str, direction: str) -> (int, list):
        ''':arg direction: long or short position (can take long or short)'''
        while True:
            if direction == 'long':
                try:
                    position = self.futuresGetInstrumentIdPosition({
                        'instrument_id': instrument_id
                    })['holding'][0]['long_avail_qty']
                except IndexError:
                    position = 0
                except RequestTimeout as err:
                    print(f'Get position request timeout {err}, retry...')
                    continue
                return int(position)
            elif direction == 'short':
                try:
                    position = self.futuresGetInstrumentIdPosition({
                        'instrument_id': instrument_id
                    })['holding'][0]['short_avail_qty']
                except IndexError:
                    position = 0
                except RequestTimeout as err:
                    print(f'Get position request timeout {err}, retry...')
                    continue
                return int(position)
            elif direction == 'both':
                try:
                    position = self.futuresGetInstrumentIdPosition({
                        'instrument_id': instrument_id
                    })['holding'][0]
                    return list(map(int, (position['long_avail_qty'], position['short_avail_qty'])))
                except IndexError:
                    return [0, 0]
                except RequestTimeout as err:
                    print(f'Get position request timeout {err}, retry...')
                    continue
            else:
                raise TypeError('你特么逗我？输入long或者short!')

    def _get_account_equity(self, *, instrument_id: str) -> float:
        trade_currency = '-'.join(instrument_id.split('-')[0:2])
        while True:
            try:
                account_equity = self.futuresGetAccountsCurrency({
                    'currency': trade_currency
                })['equity']
                return float(account_equity)
            except RequestTimeout as err:
                print(f'get account equity request timeout {err}, retyr...')
                continue

    def _place_order(self, *, instrument_id: str, direction: int, size: int, price: float, order_type: int = 2):
        '''
        :param instrument_id:
        :param direction: 1:开多2:开空3:平多4:平空
        :param size: 合约数量
        :param order_type: 参数填数字，0：普通委托（order type不填或填0都是普通委托） 1：只做Maker（Post only） 2：全部成交或立即取消（FOK） 3：立即成交并取消剩余（IOC）
        :return: order_id
        '''
        while True:
            try:
                order_info = self.futuresPostOrder({
                    'instrument_id': instrument_id,
                    'type': direction,  # 1:开多2:开空3:平多4:平空
                    'order_type': order_type,
                    # 参数填数字，0：普通委托（order type不填或填0都是普通委托） 1：只做Maker（Post only） 2：全部成交或立即取消（FOK） 3：立即成交并取消剩余（IOC）
                    'price': price,
                    'size': size
                })['order_id']
                return order_info
            except RequestTimeout as err:
                print(f'place order request timeout {err}, retry...')
                continue

    def _close_position_FOK(self, *, instrument_id: str, direction: int, size: int, price: float, order_type: int = 2):
        '''
        :param instrument_id:
        :param direction: 1:开多2:开空3:平多4:平空
        :param size:
        :param order_type:
        :return: void
        '''
        if direction not in (3, 4):
            raise TypeError('direction should be either 3 or 4')
        with open('./log/log.txt', mode='a') as logger:
            contract_remaining = size
            while True:
                self._place_order(instrument_id=instrument_id, direction=direction, size=contract_remaining, price=price,
                                  order_type=order_type)
                if direction == 3:
                    logger.write(f'平多{instrument_id}, 数量{contract_remaining}\n')
                    print(f'平多{instrument_id}, 数量{contract_remaining}')
                    contract_remaining = self._get_contract_holding_number(instrument_id=instrument_id, direction='long')
                elif direction == 4:
                    logger.write(f'平空{instrument_id}, 数量{contract_remaining}\n')
                    print(f'平空{instrument_id}, 数量{contract_remaining}')
                    contract_remaining = self._get_contract_holding_number(instrument_id=instrument_id, direction='short')
                if contract_remaining == 0:
                    logger.write(f'平仓完成， {instrument_id}, size:{size}, direction:{direction}, time: {datetime.datetime.now()}\n\n')
                    print(f'平仓完成， {instrument_id}, size:{size}, direction:{direction}')
                    return
                else:
                    if direction == 3:
                        price = float(self._fetch_futures_ticker(instrument_id=instrument_id)['best_bid']) * 0.99
                    elif direction == 4:
                        price = float(self._fetch_futures_ticker(instrument_id=instrument_id)['best_ask']) * 1.01
                    else:
                        raise TypeError('direction should be either 3 or 4')

    def _open_position_FOK(self, *, instrument_id: str, direction: int, size: int, price: float, order_type=2):
        '''
        :param instrument_id:
        :param direction: 1:开多2:开空3:平多4:平空
        :param size:
        :param order_type:
        :return: void
        '''
        if direction not in (1, 2):
            raise TypeError('direction should be either 1 or 2')
        with open(f'./log/log.txt', mode='a') as logger:
            contract_remaining = size
            while True:
                self._place_order(instrument_id=instrument_id, direction=direction, size=contract_remaining, price=price,
                                  order_type=order_type)
                if direction == 1:
                    logger.write(f'做多{instrument_id}, 数量{contract_remaining}\n')
                    print(f'做多{instrument_id}, 数量{contract_remaining}')
                    position_opened = self._get_contract_holding_number(instrument_id=instrument_id, direction='long')
                    contract_remaining = size - position_opened
                elif direction == 2:
                    logger.write(f'做空{instrument_id}, 数量{contract_remaining}\n')
                    print(f'做空{instrument_id}, 数量{contract_remaining}')
                    position_opened = self._get_contract_holding_number(instrument_id=instrument_id, direction='short')
                    contract_remaining = size - position_opened
                if contract_remaining <= 0:
                    logger.write(f'开仓完成, {instrument_id}, size:{size}, direction:{direction}, time: {datetime.datetime.now()}\n\n')
                    print(f'开仓完成, {instrument_id}, size:{size}, direction:{direction}')
                    return
                else:
                    if direction == 1:
                        price = float(self._fetch_futures_ticker(instrument_id=instrument_id)['best_ask']) * 1.01
                    elif direction == 2:
                        price = float(self._fetch_futures_ticker(instrument_id=instrument_id)['best_bid']) * 0.99
                    else:
                        raise TypeError('direction should be either 3 or 4')

    def execute(self, signal: tuple):
        pool = ThreadPool()
        if signal == (-1,):
            # 获取当周合约空单， index 0 表示多头， 1 表示空头
            recent_contract_short_position = self.recent_contract_position_obj.get()[1]
            # 只有没开仓才会执行
            if recent_contract_short_position == 0:
                # 1. 平季度空单
                distant_contract_short_position = self.distant_contract_position_obj.get()[1]
                if distant_contract_short_position != 0:
                    distant_contract_ticker = self._fetch_futures_ticker(instrument_id=self.distant_contract)
                    distant_contract_best_ask = float(distant_contract_ticker['best_ask'])
                    self._close_position_FOK(instrument_id=self.distant_contract,
                                             direction=4,
                                             size=distant_contract_short_position,
                                             price=distant_contract_best_ask * 1.01)
                # 2. 获取账户权益，并设置对冲数量
                hedge_amount = account_equity = self.account_equity_obj.get()
                # 3. 计算开仓量, amount 指的是币， 不是合约数
                short_amount = long_amount = account_equity * (self.leverage - 1 - 1) / 2
                # 4. 算出开仓合约数
                recent_contract_ticker, distant_contract_ticker = pool.map(self._fetch_futures_ticker,
                                                                           (self.recent_contract, self.distant_contract))
                recent_contract_best_bid = float(recent_contract_ticker['best_bid'])
                recent_contract_best_ask = float(recent_contract_ticker['best_ask'])
                long_size: int = round(long_amount * recent_contract_best_ask / self.contract_value)
                hedge_size: int = round(hedge_amount * recent_contract_best_bid / self.contract_value)
                distant_contract_best_bid = float(distant_contract_ticker['best_bid'])
                short_size: int = round(short_amount * distant_contract_best_bid / self.contract_value)
                # 5. 做多当周， 做空季度, 对冲当周
                if long_size != 0 and short_size != 0:
                    # 做多当周
                    pool.apply_async(self._open_position_FOK, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 1,
                        'size': long_size,
                        'price': recent_contract_best_ask * 1.01
                    }, error_callback=self.error_callback)
                    # 对冲当周
                    pool.apply_async(self._open_position_FOK, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 2,
                        'size': hedge_size,
                        'price': recent_contract_best_bid * 0.99
                    }, error_callback=self.error_callback)
                    # 做空季度
                    pool.apply_async(self._open_position_FOK, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 2,
                        'size': short_size,
                        'price': distant_contract_best_bid * 0.99
                    }, error_callback=self.error_callback)
                pool.close()
                pool.join()
                f = open('./log/log.txt', mode='a')
                f.write('\n\n')
                f.close()
                print(f'signal is {signal}')
                print('做空价差完成')
            else:
                print(f'signal is {signal}')
                print('重复信号， 做空不执行')
        elif signal == (1,):
            # 获取当周合约空单， index 0 表示多头， 1 表示空头
            recent_contract_short_position = self.recent_contract_position_obj.get()[1]
            # 只有没开仓才会执行
            if recent_contract_short_position == 0:
                # 1. 平季度空单
                distant_contract_short_position = self.distant_contract_position_obj.get()[1]
                if distant_contract_short_position != 0:
                    distant_contract_ticker = self._fetch_futures_ticker(instrument_id=self.recent_contract)
                    distant_contract_best_ask = float(distant_contract_ticker['best_ask'])
                    self._close_position_FOK(instrument_id=self.distant_contract,
                                             direction=4,
                                             size=distant_contract_short_position,
                                             price=distant_contract_best_ask * 1.01)
                # 2. 获取账户权益，并设置对冲数量
                hedge_amount = account_equity = self.account_equity_obj.get()
                # 3. 计算开仓量, amount 指的是币， 不是合约数
                short_amount = long_amount = account_equity * (self.leverage - 1 - 1) / 2
                # 4. 算出开仓合约数, 做空当周， 对冲当周， 做多季度
                recent_contract_ticker, distant_contract_ticker = pool.map(self._fetch_futures_ticker,
                                                                           (self.recent_contract, self.distant_contract))
                recent_contract_best_bid = float(recent_contract_ticker['best_bid'])
                short_size: int = round(long_amount * recent_contract_best_bid / self.contract_value)
                hedge_size: int = round(hedge_amount * recent_contract_best_bid / self.contract_value)
                distant_contract_best_ask = float(distant_contract_ticker['best_ask'])
                long_size: int = round(short_amount * distant_contract_best_ask / self.contract_value)
                # 5. 做空当周， 做多季度
                # 做空当周和对冲当周
                if long_size != 0 and short_size != 0 and hedge_size != 0:
                    pool.apply_async(self._open_position_FOK, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 2,
                        'size': short_size + hedge_size,
                        'price': recent_contract_best_bid * 0.99
                    }, error_callback=self.error_callback)
                    pool.apply_async(self._open_position_FOK, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 1,
                        'size': long_size,
                        'price': distant_contract_best_ask * 1.01
                    }, error_callback=self.error_callback)
                pool.close()
                pool.join()
                f = open('./log/log.txt', mode='a')
                f.write('\n\n')
                f.close()
                print(f'signal is {signal}')
                print('做多价差完成')
            else:
                print(f'signal is {signal}')
                print('重复信号，做多不执行')
        elif signal == (-1, 0):
            recent_contract_long_position = self.recent_contract_position_obj.get()[0]
            recent_contract_short_position = self.recent_contract_position_obj.get()[1]
            distant_contract_short_position = self.distant_contract_position_obj.get()[1]
            recent_contract_ticker, distant_contract_ticker = pool.map(self._fetch_futures_ticker,
                                                                       (self.recent_contract, self.distant_contract))
            recent_contract_best_ask = float(recent_contract_ticker['best_ask'])
            recent_contract_best_bid = float(recent_contract_ticker['best_bid'])
            # 这个if是为了避免重复信号的，只有在当周有持空仓，才有平仓，以及开套期保值仓位的必要。
            if recent_contract_short_position != 0:
                # 平空当周对冲
                pool.apply_async(self._close_position_FOK, kwds={
                    'instrument_id': self.recent_contract,
                    'direction': 4,
                    'size': recent_contract_short_position,
                    'price': recent_contract_best_ask * 1.01
                }, error_callback=self.error_callback)
                if recent_contract_long_position != 0:
                    # 平多当周
                    pool.apply_async(self._close_position_FOK, kwds={
                        'instrument_id': self.recent_contract,
                        'direction': 3,
                        'size': recent_contract_long_position,
                        'price': recent_contract_best_bid * 0.99
                    }, error_callback=self.error_callback)
                # 平空季度
                distant_contract_best_ask = float(distant_contract_ticker['best_ask'])
                if distant_contract_short_position != 0:
                    pool.apply_async(self._close_position_FOK, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 4,
                        'size': distant_contract_short_position,
                        'price': distant_contract_best_ask * 1.01
                    }, error_callback=self.error_callback)
                pool.close()
                pool.join()
                # 开季度套保
                hedge_amount = self.account_equity_obj.get()
                distant_contract_best_bid = float(
                    self._fetch_futures_ticker(instrument_id=self.distant_contract)['best_bid'])
                hedge_size = round(hedge_amount * distant_contract_best_bid / self.contract_value)
                if hedge_size != 0:
                    self._open_position_FOK(instrument_id=self.distant_contract, direction=2, size=hedge_size,
                                            price=distant_contract_best_bid * 0.99)
                f = open('./log/log.txt', mode='a')
                f.write('\n\n')
                f.close()
                print(f'signal is {signal}')
                print('完成平空')
            # 如果recent_contract_long_position是0， 当周不持仓，那么就不需要平仓，也不需要再重复开套期保值仓位
            else:
                print(f'signal is {signal}')
                print('重复信号，不需要平空')
        elif signal == (1, 0):
            recent_contract_short_position = self.recent_contract_position_obj.get()[1]
            distant_contract_long_position = self.distant_contract_position_obj.get()[0]
            recent_contract_ticker, distant_contract_ticker = pool.map(self._fetch_futures_ticker,
                                                                       (self.recent_contract, self.distant_contract))
            recent_contract_best_ask = float(recent_contract_ticker['best_ask'])
            # 只有在当周持有空仓才会执行平仓和套期保值， 防止重复操作
            if recent_contract_short_position != 0:
                # 平空当周，平空当周对冲
                pool.apply_async(self._close_position_FOK, kwds={
                    'instrument_id': self.recent_contract,
                    'direction': 4,
                    'size': recent_contract_short_position,
                    'price': recent_contract_best_ask * 1.01
                }, error_callback=self.error_callback)
                # 平多季度
                distant_contract_best_bid = float(distant_contract_ticker['best_bid'])
                if distant_contract_long_position != 0:
                    pool.apply_async(self._close_position_FOK, kwds={
                        'instrument_id': self.distant_contract,
                        'direction': 3,
                        'size': distant_contract_long_position,
                        'price': distant_contract_best_bid * 0.99
                    }, error_callback=self.error_callback)
                pool.close()
                pool.join()
                # 开季度套保
                hedge_amount = self.account_equity_obj.get()
                distant_contract_best_bid = float(
                    self._fetch_futures_ticker(instrument_id=self.distant_contract)['best_bid'])
                hedge_size = round(hedge_amount * distant_contract_best_bid / self.contract_value)
                if hedge_size != 0:
                    self._open_position_FOK(instrument_id=self.distant_contract, direction=2, size=hedge_size,
                                            price=distant_contract_best_bid * 0.99)
                f = open('./log/log.txt', mode='a')
                f.write('\n\n')
                f.close()
                print(f'signal is {signal}')
                print('完成平多')
            # 当周不持空单就不执行，防止重复操作
            else:
                print(f'signal is {signal}')
                print('重复信号，不需要平多')

    # 将对象的当周，次周，季度合约全部更新
    def synthesize_n_update_contracts(self):
        # ==生成季度合约
        # 设置根， 例如 BTC-USD- 或 ETH-USD-
        stem = self.trade_coin + '-' + self.quote_coin + '-'
        # 生成一个世界标准时间的datetime对象
        utcnow = datetime.datetime.utcnow()
        c = calendar.Calendar()
        # 季度合约在3月， 6月， 9月， 12月的最后一个周五交割
        distant_contract_months = (3, 6, 9, 12)
        index = 0
        # 找到离现在最近的交割月份
        for i in range(len(distant_contract_months)):
            if utcnow.month > distant_contract_months[i]:
                index += 1
                continue
            else:
                break
        year = utcnow.year
        nearest_delivery_month = distant_contract_months[index]
        monthcal = c.monthdatescalendar(year, nearest_delivery_month)
        # 3月， 6月， 9月， 12月距离现在最近的那个月的周五
        # last_friday_date 是一个datetime.datetime.date对象， 必须将其转化为datetime.datetime对象
        last_friday_delivery_date = [day for week in monthcal for day in week if\
                       day.weekday() == calendar.FRIDAY and \
                       day.month == nearest_delivery_month][-1]
        last_friday_delivery_time = datetime.datetime.combine(last_friday_delivery_date, datetime.time(8, 0))
        distant_contract_date = last_friday_delivery_date
        # 如果计算出来的周五是在距离现在的未来， 那么就完成了
        if last_friday_delivery_time > utcnow:
            pass
        # 如果计算出来的周五已经过了， 那么判断现在是否是12月， 如果是，那就加一年，同时把最近月份设置到三月
        elif utcnow.month == 12 and last_friday_delivery_time < utcnow:
            year += 1
            nearest_delivery_month = distant_contract_months[0]
            monthcal = c.monthdatescalendar(year, nearest_delivery_month)
            last_friday_delivery_time = [day for week in monthcal for day in week if \
                                day.weekday() == calendar.FRIDAY and \
                                day.month == nearest_delivery_month][-1]
            distant_contract_date = last_friday_delivery_time
        # 如果现在不是12月（例如， 现在是3月31日，而离我最近的月份是3月， 最后一个周五是3月27日， 已经过了，那么就在加三个月）
        elif utcnow.month != 12 and last_friday_delivery_time < utcnow:
            nearest_delivery_month = distant_contract_months[index+1]
            monthcal = c.monthdatescalendar(year, nearest_delivery_month)
            last_friday_delivery_time = [day for week in monthcal for day in week if \
                                day.weekday() == calendar.FRIDAY and \
                                day.month == nearest_delivery_month][-1]
            distant_contract_date = last_friday_delivery_time
        self.distant_contract = distant_contract_date.strftime(stem + "%y%m%d")
        # ==生成当周和次周合约
        today = datetime.date.today()
        nearest_friday = today + datetime.timedelta(days=(4 - today.weekday()) % 7)
        nearest_friday_delivery_time = datetime.datetime.combine(nearest_friday, datetime.time(8, 0))
        recent_contract_date = nearest_friday
        if nearest_friday_delivery_time > utcnow:
            pass
        else:
            nearest_friday += datetime.timedelta(days=7)
            recent_contract_date = nearest_friday
        next_week_contract_date = recent_contract_date + datetime.timedelta(days=7)
        self.recent_contract = recent_contract_date.strftime(stem + "%y%m%d")
        self.next_week_contract = next_week_contract_date.strftime(stem + '%y%m%d')
        return

    def recent_contract_rollover(self):
        while True:
            utcnow = datetime.datetime.utcnow()
            # 每周五当周合约交割以前rollover
            if utcnow.weekday() == 4 and utcnow.hour == 7 and 56 <= utcnow.minute <= 59:
                for apiKey, secret, password in zip(self.apiKeys_lst, self.secret_lst, self.password_lst):
                    pool = ThreadPool()
                    self.apiKey = apiKey
                    self.secret = secret
                    self.password = password
                    recent_contract_long_position = self._get_contract_holding_number(instrument_id=self.recent_contract, direction='long')
                    recent_contract_short_position = self._get_contract_holding_number(instrument_id=self.recent_contract, direction='short')
                    # 在做空价差
                    if recent_contract_long_position != 0 and recent_contract_short_position != 0:

                        recent_contract_position_info = self._get_position_info(instrument_id=self.recent_contract)
                        recent_contract_long_avg_cost = float(recent_contract_position_info['long_avg_cost'])
                        recent_contract_short_avg_cost = float(recent_contract_position_info['short_avg_cost'])
                        recent_contract_long_coin_equivalent = self.contract_value * recent_contract_long_position / recent_contract_long_avg_cost
                        recent_contract_hedge_coin_equivalent = self.contract_value * recent_contract_short_position / recent_contract_short_avg_cost
                        recent_contract_ticker = self._fetch_futures_ticker(instrument_id=self.recent_contract)
                        recent_contract_best_bid = float(recent_contract_ticker['best_bid'])
                        recent_contract_best_ask = float(recent_contract_ticker['best_ask'])
                        pool.apply_async(func=self._close_position_FOK, kwds={
                            'instrument_id': self.recent_contract,
                            'direction': 4,
                            'size': recent_contract_short_position,
                            'price': recent_contract_best_ask * 1.01
                        }, error_callback=self.error_callback)
                        pool.apply_async(func=self._close_position_FOK, kwds={
                            'instrument_id': self.recent_contract,
                            'direction': 3,
                            'size': recent_contract_long_position,
                            'price': recent_contract_best_bid * 0.99
                        }, error_callback=self.error_callback)
                        next_contract_ticker = self._fetch_futures_ticker(instrument_id=self.next_week_contract)
                        next_contract_best_bid = float(next_contract_ticker['best_bid'])
                        next_contract_best_ask = float(next_contract_ticker['best_ask'])
                        next_contract_last_price = float(next_contract_ticker['last'])
                        next_week_long_size = round(recent_contract_long_coin_equivalent * next_contract_last_price/ self.contract_value)
                        next_week_hedge_size = round(recent_contract_hedge_coin_equivalent * next_contract_last_price / self.contract_value)
                        pool.apply_async(func=self._open_position_FOK, kwds={
                            'instrument_id': self.next_week_contract,
                            'direction': 1,
                            'size': next_week_long_size,
                            'price': next_contract_best_ask * 1.01
                        }, error_callback=self.error_callback)
                        pool.apply_async(func=self._open_position_FOK, kwds={
                            'instrument_id': self.next_week_contract,
                            'direction': 2,
                            'size': next_week_hedge_size,
                            'price': next_contract_best_bid * 0.99
                        }, error_callback=self.error_callback)
                    # 在做多价差
                    elif recent_contract_long_position == 0 and recent_contract_short_position != 0:
                        recent_contract_position_info = self._get_position_info(instrument_id=self.recent_contract)
                        recent_contract_short_avg_cost = float(recent_contract_position_info['short_avg_cost'])
                        recent_contract_short_coin_equivalent = self.contract_value * recent_contract_short_position / recent_contract_short_avg_cost
                        recent_contract_ticker = self._fetch_futures_ticker(instrument_id=self.recent_contract)
                        recent_contract_best_ask = float(recent_contract_ticker['best_ask'])
                        pool.apply_async(func=self._close_position_FOK, kwds={
                            'instrument_id': self.recent_contract,
                            'direction': 4,
                            'size': recent_contract_short_position,
                            'price': recent_contract_best_ask * 1.01
                        }, error_callback=self.error_callback)
                        next_contract_ticker = self._fetch_futures_ticker(instrument_id=self.next_week_contract)
                        next_contract_best_bid = float(next_contract_ticker['best_bid'])
                        next_contract_last_price = float(next_contract_ticker['last'])
                        next_week_short_size = round(recent_contract_short_coin_equivalent * next_contract_last_price / self.contract_value)
                        pool.apply_async(func=self._open_position_FOK, kwds={
                            'instrument_id': self.next_week_contract,
                            'direction': 2,
                            'size': next_week_short_size,
                            'price': next_contract_best_bid * 0.99
                        }, error_callback=self.error_callback)
                    pool.close()
                    pool.join()
                    print('rollover 完成')
            else:
                print('没到时间')
                time.sleep(60)
                # 每60秒更新一次合约信息
                self.synthesize_n_update_contracts()

    @staticmethod
    def error_callback(error):
        print('[Error callback]', error, '\n')
        with open('./log/multithreading_error.txt', mode='a') as logger:
            logger.write('time: {}, [Error] {}\n'.format(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                                         str(error)))
        return
