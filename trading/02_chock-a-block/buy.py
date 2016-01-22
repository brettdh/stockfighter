#!/usr/bin/env python

import argparse
import requests
import time
import math
import json

BASE_URL = "https://api.stockfighter.io/ob/api"
with open("api_key.json") as f:
    API_KEY = json.load(f)['api-key']

def api_key():
    return {
        'headers': {
            'X-Starfighter-Authorization': API_KEY
        }
    }


def stock_url(venue, stock):
    return "{}/venues/{}/stocks/{}".format(BASE_URL, venue, stock)


def order_url(order):
    return stock_url(order['venue'], order['symbol']) + "/{}".format(order['id'])


def get_average_price(venue, stock, n=5, delay=1):
    url = stock_url(venue, stock) + "/quote"
    prices = []
    for _ in xrange(n):
        r = requests.get(url, **api_key())
        r.raise_for_status()
        quote = r.json()
        price = 1
        for key in ['ask', 'bid', 'last']:
            if key in quote:
                price = quote[key]
                break

        print "Got price quote: {}".format(price)
        prices.append(price)

        time.sleep(delay)

    return int(math.ceil(sum(prices) / float(n)))


def bid(account, venue, stock, price_per_share, shares):
    order = {
        'account': account,
        'venue': venue,
        'stock': stock,
        'price': price_per_share * shares,
        'qty': shares,
        'direction': 'buy',
        'orderType': 'limit'
    }
    url = stock_url(venue, stock) + "/orders"
    r = requests.post(url, data=order, **api_key())
    r.raise_for_status()

    response = r.json()
    if not response['ok']:
        raise Exception(response['error'])
    return response


def order_is_filled(order):
    r = requests.get(order_url(order))
    r.raise_for_status()
    return r.json()['open'], order


def wait_for_fill(order, poll=1, checks=5):
    start = time.time()
    for _ in xrange(checks):
        filled, order = order_is_filled(order)
        if filled:
            return order['originalQty']

        time.sleep(poll)

    r = requests.delete(order_url(order))
    r.raise_for_status()
    return r.json()['totalFilled']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("account")
    parser.add_argument("venue")
    parser.add_argument("stock")
    parser.add_argument("--delay", default=5, type=int,
                        help="Seconds (wall clock time) to wait between bids")
    args = parser.parse_args()

    bought = 0
    target = 100000
    shares_per_bid = 10
    while bought < target:
        price = int(get_average_price(args.venue, args.stock) * 1.1)
        print "Bidding for {} shares at {} apiece".format(shares_per_bid, price)
        order = bid(args.account, args.venue, args.stock, price, shares_per_bid)
        shares = wait_for_fill(order)
        bought += shares


if __name__ == '__main__':
    main()
