#!/usr/bin/env python

import argparse
import requests
import time
import math
import json
import pprint

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
    return stock_url(order['venue'], order['symbol']) + "/orders/{}".format(order['id'])


def get_average_price(venue, stock, n=5, delay=1):
    url = stock_url(venue, stock) + "/quote"
    prices = []
    for i in xrange(n):
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

        if i + 1 < n:
            time.sleep(delay)

    return int(math.ceil(sum(prices) / float(n)))


def order(account, venue, stock, price_per_share, shares, direction):
    order = {
        'account': account,
        'venue': venue,
        'stock': stock,
        'price': price_per_share,
        'qty': shares,
        'direction': direction,
        'orderType': 'limit'
    }
    url = stock_url(venue, stock) + "/orders"
    r = requests.post(url, json=order, **api_key())
    r.raise_for_status()

    response = r.json()
    if not response['ok']:
        raise Exception(response['error'])
    return response


def bid(account, venue, stock, price_per_share, shares):
    return order(account, venue, stock, price_per_share, shares, 'buy')


def ask(account, venue, stock, price_per_share, shares):
    return order(account, venue, stock, price_per_share, shares, 'sell')


def order_is_filled(order):
    r = requests.get(order_url(order), **api_key())
    r.raise_for_status()
    return not r.json()['open'], order


def wait_for_fill(order, poll=1, checks=5):
    start = time.time()
    for i in xrange(checks):
        filled, order = order_is_filled(order)
        if filled:
            print "Order filled"
            pprint.pprint(order, indent=2)
            return order['originalQty']
        print "Order not yet filled"

        if i + 1 < checks:
            time.sleep(poll)

    r = requests.delete(order_url(order), **api_key())
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
    shares_per_bid = 200
    shares_per_sell = 50
    buys_per_sell = 3  # every N buys, sell some
    price = None
    time_between_bids = 5.0 / 24
    buys = 0

    price = int(get_average_price(args.venue, args.stock, n=1) * 1.1)
    while bought < target:
        print "Bidding for {} shares at {} apiece".format(shares_per_bid, price)
        bid_time = time.time()
        order = bid(args.account, args.venue, args.stock, price, shares_per_bid)
        shares = wait_for_fill(order)
        fill_time = time.time()

        sleep_time = max(0, time_between_bids - (fill_time - bid_time))
        if sleep_time > 0:
            print "Sleeping for {} seconds".format(sleep_time)
            time.sleep(sleep_time)
        bought += shares

        if shares > 0:
            buys += 1

            if buys % buys_per_sell == 0:
                print "Asking for {} per share for {} shares".format(price, shares_per_sell)
                order = ask(args.account, args.venue, args.stock, int(price * 0.7), shares_per_sell)
                shares = wait_for_fill(order)
                bought -= shares

if __name__ == '__main__':
    main()
