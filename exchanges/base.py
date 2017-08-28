from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum

import asyncio
from aiohttp import ClientSession
from logging import getLogger

from exchanges.exceptions import WrongContentTypeException

Order = namedtuple('Order', 'exchange_id order_id type pair price amount state')


class State(Enum):
    ACTIVE = 0
    EXECUTED = 1
    CANCELED = 2
    CANCELED_PARTIALLY_FILLED = 3


state_text = {
    State.ACTIVE: 'active',
    State.EXECUTED: '✅ executed',
    State.CANCELED: '🚫 canceled',
    State.CANCELED_PARTIALLY_FILLED: '⚠️ canceled, partially filled',
}


class BaseApi(ABC):
    name = None
    api_id = None
    url = None
    api_regex = None
    secret_regex = None

    attempts_limit = 5

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

    @staticmethod
    async def post(url: str, headers: dict = None, data: dict = None) -> dict:
        async with ClientSession() as s:
            resp = await s.post(url, data=data, headers=headers)
            return await resp.json()

    async def get(self, url: str, headers: dict = None) -> dict:
        attempt, delay = 1, 1
        async with ClientSession() as s:
            while True:
                try:
                    resp = await s.get(url, headers=headers)
                    if resp.content_type != 'application/json':
                        raise WrongContentTypeException(
                            f'Unexpected content type {resp.content_type!r}. URL: {url}, headers: {headers}'
                        )
                except WrongContentTypeException as e:
                    getLogger().error(f'attempt {attempt}/{self.attempts_limit}, next attempt in {delay} seconds')
                    getLogger().exception(e)
                    attempt += 1
                    if attempt > self.attempts_limit:
                        return {}
                    await asyncio.sleep(delay)
                    delay *= 2
                return await resp.json()

    @abstractmethod
    async def active_orders(self) -> [Order, ]:
        '''Returns active orders.'''

    @abstractmethod
    async def order_info(self, order_id: str) -> Order:
        '''Returns order info by order id.'''

    @staticmethod
    @abstractmethod
    def order_state(order: dict) -> State:
        '''Returns state of the api order.'''

    @abstractmethod
    def get_ticker_url(self, pair):
        '''Returns exchange's ticker URL for provided pair.'''

    @classmethod
    def check_keys(cls, api: str, secret: str) -> bool:
        return cls.api_regex.match(api) and cls.secret_regex.match(secret)
