import asyncio
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum
from logging import getLogger

import aiohttp
from aiohttp import ClientSession

from exchanges.exceptions import WrongContentTypeException, BaseExchangeException, InvalidResponseException
from settings import REQUEST_ATTEMPTS_LIMIT

Order = namedtuple('Order', 'exchange_id order_id type pair price amount state')


class State(Enum):
    ACTIVE = 0
    EXECUTED = 1
    CANCELED = 2
    CANCELED_PARTIALLY_FILLED = 3
    EXPIRED = 4


state_text = {
    State.ACTIVE: 'active',
    State.EXECUTED: '✅ executed',
    State.CANCELED: '🚫 canceled',
    State.CANCELED_PARTIALLY_FILLED: '⚠️ canceled, partially filled',
    State.EXPIRED: '⏱ expired',
}


class BaseApi(ABC):
    name = None
    api_id = None
    url = None
    api_regex = None
    secret_regex = None

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

    @classmethod
    def check_keys(cls, api: str, secret: str) -> bool:
        return cls.api_regex.match(api) and cls.secret_regex.match(secret)

    async def request(self, url, headers, method='get', data=None):
        attempt, delay = 1, 1
        async with ClientSession() as s:
            session_method = s.__getattribute__(method.lower())
            while True:
                try:
                    resp = await session_method(url=url, headers=headers, data=data)
                    if resp.content_type != 'application/json':
                        raise WrongContentTypeException(f'Unexpected content type {resp.content_type!r} at URL {url}.')
                    json_resp = await resp.json()
                    self._raise_if_error(json_resp)
                    return json_resp
                except (aiohttp.client_exceptions.ClientResponseError, BaseExchangeException) as e:
                    getLogger().error(f'attempt {attempt}/{REQUEST_ATTEMPTS_LIMIT}, next in {delay} seconds...')
                    getLogger().exception(e)
                    attempt += 1
                    if attempt > REQUEST_ATTEMPTS_LIMIT:
                        raise InvalidResponseException(e)
                    await asyncio.sleep(delay)
                    delay *= 2

    async def post(self, url: str, headers: dict = None, data: dict = None) -> dict:
        return await self.request(url, headers, 'post', data)

    async def get(self, url: str, headers: dict = None) -> dict:
        return await self.request(url, headers)

    @abstractmethod
    async def order_history(self) -> [str, ]:
        '''Returns user orders ids.'''

    @abstractmethod
    async def order_info(self, order_id: str) -> Order:
        '''Returns order info by order id.'''

    def format_order(self, order: Order):
        ticker_url = f'[{order.pair}]({self._get_ticker_url(order.pair)})'
        return f'*Exchange:* {self.name}\n' \
               f'*Pair:* {ticker_url}\n' \
               f'*Price:* {order.price:.8f}\n' \
               f'*Amount:* {order.amount:.8f}\n' \
               f'*State:* {state_text[order.state]}'

    @abstractmethod
    def _get_ticker_url(self, pair):
        '''Returns exchange's ticker URL for provided pair.'''

    @staticmethod
    @abstractmethod
    def _order_state(order: dict) -> State:
        '''Returns state of the api order.'''

    @abstractmethod
    def _raise_if_error(self, response: dict):
        '''Raises BaseExchangeException if there is an errors in API response.
        :raises BaseExchangeException:
        '''
