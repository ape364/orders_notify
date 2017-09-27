import base64
import hashlib
import hmac
import re
import urllib
from time import time

from exchanges.base import BaseApi, Order, State
from exchanges.exceptions import BaseExchangeException


class KrakenApiException(BaseExchangeException):
    pass


class AmbiguousResultException(KrakenApiException):
    pass


class UnknownPairException(KrakenApiException):
    pass


class KrakenApi(BaseApi):
    name = 'kraken'
    api_id = 3
    url = 'https://www.kraken.com/'
    api_regex = re.compile(r'^[a-zA-Z0-9/+]{56}$')
    secret_regex = re.compile(r'^[a-zA-Z0-9/+]{86}==$')

    BASE_URL = 'https://api.kraken.com'

    @staticmethod
    def _order_state(order: dict) -> State:
        if order['status'] == 'canceled' and float(order['vol_exec']) > 0:
            return State.CANCELED_PARTIALLY_FILLED
        return {
            'open': State.ACTIVE,
            'canceled': State.CANCELED,
            'closed': State.EXECUTED,
            'expired': State.EXPIRED
        }.get(order['status'])

    async def order_history(self) -> [str, ]:
        method_url = '/0/private/ClosedOrders'

        data = {
            'nonce': int(time() * 1000)
        }

        headers = {
            'API-Key': self._key,
            'API-Sign': self._sign(data, method_url)
        }

        resp = await self.post(self.BASE_URL + method_url, headers, data)

        return {order_id for order_id in resp['result']['closed']}

    async def order_info(self, order_id: str) -> Order:
        method_url = '/0/private/QueryOrders'

        data = {
            'nonce': int(time() * 1000),
            'txid': order_id
        }

        headers = {
            'API-Key': self._key,
            'API-Sign': self._sign(data, method_url)
        }

        resp = await self.post(self.BASE_URL + method_url, headers, data)

        order = resp['result'][order_id]
        descr = order['descr']

        return Order(
            self.api_id,
            order_id,
            descr['type'],
            await self.parse_pair(descr['pair']),
            descr['price'],
            order['vol'],
            self._order_state(order),
        )

    def _get_ticker_url(self, pair):
        return 'https://www.kraken.com/charts'

    def get_headers(self, data, urlpath):
        return {
            'API-Key': self._key,
            'API-Sign': self._sign(data, urlpath)
        }

    def _sign(self, data, urlpath):
        postdata = urllib.parse.urlencode(data)

        # Unicode-objects must be encoded before hashing
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        signature = hmac.new(base64.b64decode(self._secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(signature.digest())

        return sigdigest.decode()

    async def parse_pair(self, pair):
        url = f'https://api.kraken.com/0/public/AssetPairs?pair={pair}'
        resp = await self.get(url)
        if resp['error']:
            raise KrakenApiException('\n'.join(resp['error']))
        result = resp['result']
        if len(result) > 1:
            pairs = ','.join(result.keys())
            raise AmbiguousResultException(f'More than 1 result to pair {pair}: {pairs}')
        _, pair_info = result.popitem()
        return f"{pair_info['base']}-{pair_info['quote']}"

    def _raise_if_error(self, response: dict) -> bool:
        if response['error']:
            raise KrakenApiException('\n'.join(response['error']))
