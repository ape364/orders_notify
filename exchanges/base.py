from abc import ABC, abstractmethod
from collections import namedtuple

from aiohttp import ClientSession

Order = namedtuple('Order', 'exchange_id order_id type pair price amount is_closed')


class BaseApi(ABC):
    name = None
    api_id = None
    url = None
    api_regex = None
    secret_regex = None

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

    @staticmethod
    async def post(url: str, headers: dict = None, data: dict = None) -> dict:
        async with ClientSession() as s:
            resp = await s.post(url, data=data, headers=headers)
            return await resp.json()

    @staticmethod
    async def get(self, url: str, headers: dict = None) -> dict:
        async with ClientSession() as s:
            resp = await s.get(url, headers=headers)
            return await resp.json()

    @abstractmethod
    async def active_orders(self) -> [Order, ]:
        '''Returns active orders.'''

    @abstractmethod
    async def order_info(self, order_id: str) -> Order:
        '''Returns order info by order id.'''

    @classmethod
    def check_keys(cls, api: str, secret: str) -> bool:
        return cls.api_regex.match(api) and cls.secret_regex.match(secret)
