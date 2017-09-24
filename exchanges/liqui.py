import asyncio
import hashlib
import hmac
import re
from logging import getLogger
from time import time
from urllib.parse import urlencode

import aiohttp

from exchanges.base import BaseApi, Order, State
from exchanges.exceptions import BaseExchangeException


class LiquiApiException(BaseExchangeException):
    pass


class NoOrdersException(BaseExchangeException):
    pass


class LiquiApi(BaseApi):
    name = 'liqui'
    api_id = 1
    url = 'https://liqui.io/'
    api_regex = re.compile(r'\w{8}-\w{8}-\w{8}-\w{8}-\w{8}')  # A1B2C3D4-A1B2C3D4-A1B2C3D4-A1B2C3D4-A1B2C3D4
    secret_regex = re.compile(r'\w{64}')  # a78ab8f2410498e696cc6719134c62d5a852eb26070a31cb6a469b5932bf376b

    async def order_history(self) -> [str, ]:
        history = await self._tapi(method='TradeHistory')
        return {str(info['order_id']) for _, info in history.items()}

    async def order_info(self, order_id: str) -> Order:
        order = (await self._tapi(method='OrderInfo', order_id=order_id))[order_id]
        return Order(
            self.api_id,
            order_id,
            order['type'],
            '-'.join(cur.upper() for cur in order['pair'].split('_')),
            order['rate'],
            order['start_amount'],
            self._order_state(order),
        )

    @staticmethod
    def _order_state(order: dict) -> State:
        return State(order['status'])

    def _get_ticker_url(self, pair):
        cur_from, cur_to = pair.split('-')
        return f'https://liqui.io/#/exchange/{cur_from}_{cur_to}'

    async def _tapi(self, **params):
        attempt, delay = 1, 1
        while True:
            try:
                params['nonce'] = int(time())
                data = await self.post(
                    'https://api.liqui.io/tapi',
                    headers={'Key': self._key, 'Sign': self._sign(params)},
                    data=params
                )
                if 'error' in data:
                    if data['error'] == 'no orders':
                        raise NoOrdersException(data['error'])
                    raise LiquiApiException(data['error'])
                return data.get('return', data)
            except (LiquiApiException, aiohttp.client_exceptions.ClientResponseError) as e:
                getLogger().error(f'attempt {attempt}/{self.attempts_limit}, next attempt in {delay} seconds')
                getLogger().exception(e)
                attempt += 1
                if attempt > self.attempts_limit:
                    return {}
                await asyncio.sleep(delay)
                delay *= 2

    def _sign(self, data):
        if isinstance(data, dict):
            data = urlencode(data)
        return hmac.new(self._secret.encode(), data.encode(), hashlib.sha512).hexdigest()
