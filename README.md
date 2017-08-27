# CryptoNotify

[@orders_notify_bot](http://t.me/orders_notify_bot) sends notifications about closed orders on cryptocurrency exchanges.

## Usage

### Subscribe

Send a command like this to bot to subscribe to notifications:

`/sub exchange_name api_key secret_key`

Example:

`/sub bittrex a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7 a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7`

### Unsubscribe

Send the following command:

`/unsub exchange_name`

Example:

`/unsub bittrex`

### Supported exchanges

* [Bittrex](https://bittrex.com/)
* [Liqui](https://liqui.io/)

## Contributing

Feel free to send PR with new exchanges. You need to implement logic of BaseApi class, described in exchanges/base.py

## Contacts

Telegram [@ape364](http://t.me/ape364)