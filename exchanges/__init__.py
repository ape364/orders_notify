from exchanges.bittrex import BittrexApi
from exchanges.kraken import KrakenApi
from exchanges.liqui import LiquiApi

exchange_apis = [LiquiApi, BittrexApi, KrakenApi]


def get_api_by_name(exchange_name):
    for api in exchange_apis:
        if api.name == exchange_name:
            return api


def get_supported_info():
    apis_info = []
    for api in exchange_apis:
        apis_info.append(f'[{api.name}]({api.url})')
    return '\n'.join(apis_info)
