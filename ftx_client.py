import time
import urllib.parse
from typing import Optional, Dict, Any, List

from requests import Request, Session, Response
import hmac
from ciso8601 import parse_datetime


class FtxClient:
    _ENDPOINT = 'https://ftx.com/api/'

    def __init__(self, api_key=None, api_secret=None, subaccount_name=None):
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._subaccount_name = subaccount_name

    def _get(self, path, params = None):
        return self._request('GET', path, params=params)

    def _post(self, path, params = None):
        return self._request('POST', path, json=params)

    def _delete(self, path, params = None):
        return self._request('DELETE', path, json=params)

    def _request(self, method, path, **kwargs):
        request = Request(method, self._ENDPOINT + path, **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request):
        ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self._api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self._subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self._subaccount_name)

    def _process_response(self, response):
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                raise Exception(data['error'])
            return data['result']

    def list_futures(self):
        return self._get('futures')

    def list_markets(self):
        return self._get('markets')
    
    def get_price(self, market):
        return float(self._get(f'markets/{market}')['last'])
    
    def get_candles(self, market, resolution):
#         print(market, resolution)
        return self._get(f'markets/{market}/candles?resolution={resolution}')

    def get_orderbook(self, market, depth = None):
        return self._get(f'markets/{market}/orderbook', {'depth': depth})

    def get_trades(self, market):
        return self._get(f'markets/{market}/trades')

    def get_account_info(self):
        return self._get(f'account')
    
    def get_balance(curr):
        balance = self.get_balances()
        if len(balance) == 1 and balance[0]['coin'] != curr:
            return 0.0
        item = [x for x in balance if x['coin'] == curr][0]
        return item['free']

    def get_open_orders(self, market = None):
        return self._get(f'orders', {'market': market})
    
    def get_order_history(self, market = None, side = None, order_type = None, start_time: float = None, end_time: float = None):
        return self._get(f'orders/history', {'market': market, 'side': side, 'orderType': order_type, 'start_time': start_time, 'end_time': end_time})
        
    def get_conditional_order_history(self, market = None, side = None, type = None, order_type = None, start_time = None, end_time = None):
        return self._get(f'conditional_orders/history', {'market': market, 'side': side, 'type': type, 'orderType': order_type, 'start_time': start_time, 'end_time': end_time})

    def modify_order(
        self, existing_order_id: Optional[str] = None,
        existing_client_order_id: Optional[str] = None, price: Optional[float] = None,
        size: Optional[float] = None, client_order_id: Optional[str] = None,
    ):
        assert (existing_order_id is None) ^ (existing_client_order_id is None), \
            'Must supply exactly one ID for the order to modify'
        assert (price is None) or (size is None), 'Must modify price or size of order'
        path = f'orders/{existing_order_id}/modify' if existing_order_id is not None else \
            f'orders/by_client_id/{existing_client_order_id}/modify'
        return self._post(path, {
            **({'size': size} if size is not None else {}),
            **({'price': price} if price is not None else {}),
            ** ({'clientId': client_order_id} if client_order_id is not None else {}),
        })

    def get_conditional_orders(self, market = None):
        return self._get(f'conditional_orders', {'market': market})

    def place_order(self, market, side, price, size, type = 'limit',
                    reduce_only = False, ioc = False, post_only = False,
                    client_id = None):
        return self._post('orders', {'market': market,
                                     'side': side,
                                     'price': price,
                                     'size': size,
                                     'type': type,
                                     'reduceOnly': reduce_only,
                                     'ioc': ioc,
                                     'postOnly': post_only,
                                     'clientId': client_id,
                                     })

    def place_conditional_order(
        self, market, side, size, type = 'stop',
        limit_price = None, reduce_only = False, cancel = True,
        trigger_price = None, trail_value = None
    ):
        """
        To send a Stop Market order, set type='stop' and supply a trigger_price
        To send a Stop Limit order, also supply a limit_price
        To send a Take Profit Market order, set type='trailing_stop' and supply a trigger_price
        To send a Trailing Stop order, set type='trailing_stop' and supply a trail_value
        """
        assert type in ('stop', 'take_profit', 'trailing_stop')
        assert type not in ('stop', 'take_profit') or trigger_price is not None, \
            'Need trigger prices for stop losses and take profits'
        assert type not in ('trailing_stop',) or (trigger_price is None and trail_value is not None), \
            'Trailing stops need a trail value and cannot take a trigger price'

        return self._post('conditional_orders',
                          {'market': market, 'side': side, 'triggerPrice': trigger_price,
                           'size': size, 'reduceOnly': reduce_only, 'type': 'stop',
                           'cancelLimitOnTrigger': cancel, 'orderPrice': limit_price})

    def cancel_order(self, order_id):
        return self._delete(f'orders/{order_id}')
    
    def get_order_status(self, order_id):
        return self._get(f'orders/{order_id}')

    def cancel_orders(self, market_name = None, conditional_orders = False,
                      limit_orders = False):
        return self._delete(f'orders', {'market': market_name,
                                        'conditionalOrdersOnly': conditional_orders,
                                        'limitOrdersOnly': limit_orders,
                                        })

    def get_fills(self):
        return self._get(f'fills')

    def get_balances(self):
        return self._get('wallet/balances')
    
    def get_balance(self, curr):
        balance = self.get_balances()
        temp = [x for x in balance if x['coin'] == curr]
        if len(temp) == 0:
            return 0.0
        
        return temp[0]['free']
    
    def get_usdValue(self, curr):
        balance = self.get_balances()
        temp = [x for x in balance if x['coin'] == curr]
        if len(temp) == 0:
            return 0.0
        
        return temp[0]['usdValue']

    def get_deposit_address(self, ticker):
        return self._get(f'wallet/deposit_address/{ticker}')

    def get_positions(self, show_avg_price = False):
        return self._get('positions', {'showAvgPrice': show_avg_price})

    def get_position(self, name, show_avg_price = False):
        return next(filter(lambda x: x['future'] == name, self.get_positions(show_avg_price)), None)

    def get_all_trades(self, market, start_time = None, end_time = None):
        ids = set()
        limit = 100
        results = []
        while True:
            response = self._get(f'markets/{market}/trades', {
                'end_time': end_time,
                'start_time': start_time,
            })
            deduped_trades = [r for r in response if r['id'] not in ids]
            results.extend(deduped_trades)
            ids |= {r['id'] for r in deduped_trades}
            print(f'Adding {len(response)} trades with end time {end_time}')
            if len(response) == 0:
                break
            end_time = min(parse_datetime(t['time']) for t in response).timestamp()
            if len(response) < limit:
                break
        return results
