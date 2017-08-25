import hashlib
import hmac
import re
from time import time
from urllib.parse import urlencode

from exchanges.base import BaseApi, Order, State
from exchanges.exceptions import BaseExchangeException


class BittrexApiException(BaseExchangeException):
    pass


class NullOrderState(BittrexApiException):
    pass


class BittrexApi(BaseApi):
    name = 'bittrex'
    api_id = 2
    url = 'https://bittrex.com/'
    api_regex = re.compile(r'\w{32}')  # a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7
    secret_regex = re.compile(r'\w{32}')  # a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7

    async def active_orders(self) -> list:
        method_url = 'https://bittrex.com/api/v1.1/market/getopenorders'
        headers, url = self.get_headers_url(method_url)
        resp = await self.get(url, headers)
        if not resp['success']:
            raise BittrexApiException(resp['message'])
        api_orders = resp['result']
        orders = []
        for order in api_orders:
            orders.append(
                Order(
                    self.api_id,
                    order['OrderUuid'],
                    'sell' if order['OrderType'] == 'LIMIT_SELL' else 'buy',
                    order['Exchange'],
                    order['PricePerUnit'] or order['Limit'],
                    order['Quantity'],
                    self.order_state(order)
                )
            )
        return orders

    async def order_info(self, order_id: str) -> dict:
        method_url = 'https://bittrex.com/api/v1.1/account/getorder'
        params = {'uuid': order_id}
        headers, url = self.get_headers_url(method_url, **params)
        resp = await self.get(url, headers)
        if not resp['success']:
            raise BittrexApiException(resp['message'])
        order = resp['result']
        return Order(
            self.api_id,
            order['OrderUuid'],
            'sell' if order['Type'] == 'LIMIT_SELL' else 'buy',
            order['Exchange'],
            order['PricePerUnit'] or order['Limit'],
            order['Quantity'],
            self.order_state(order)
        )

    @staticmethod
    def order_state(order: dict) -> State:
        is_open, canceled = order['Closed'] is None, order['CancelInitiated']
        qty, qty_remaining = order['Quantity'], order['QuantityRemaining']

        if is_open and qty == qty_remaining:
            return State.ACTIVE
        if not is_open and not canceled and not qty_remaining:
            return State.EXECUTED
        if not is_open and qty_remaining == qty:
            return State.CANCELED
        if not is_open and qty_remaining != qty:
            return State.CANCELED_PARTIALLY_FILLED

        raise NullOrderState(order)

    def get_ticker_url(self, pair):
        return f'https://bittrex.com/Market/Index?MarketName={pair}'

    def get_headers_url(self, method_url, **params):
        params.update({
            'apikey': self._key,
            'nonce': int(time() * 1000)
        })
        url = f'{method_url}?{urlencode(params)}'
        return {'apisign': hmac.new(self._secret.encode(), url.encode(), hashlib.sha512).hexdigest()}, url
