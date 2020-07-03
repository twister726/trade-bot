from binance.client import Client
from binance.enums import *
import talib
import numpy as np
import requests
import pandas as pd
import time
import datetime

base_url = 'https://api.binance.com/'
curr_symbol = 'BTCUSDT'

def get_price(symbol):
	url = base_url + 'api/v3/ticker/price'
	params = {'symbol': symbol}
	r = requests.get(url=url, params=params)
	data = r.json()
	return data

def Stoch(close,high,low, smoothk, smoothd, n):
	lowestlow = pd.Series.rolling(low,window=n,center=False).min()
	highesthigh = pd.Series.rolling(high, window=n, center=False).max()
	K = pd.Series.rolling(100*((close-lowestlow)/(highesthigh-lowestlow)), window=smoothk).mean()
	D = pd.Series.rolling(K, window=smoothd).mean()

	return K, D

api_key = 'WBixVoVnprvnof5dm1gQnfSQzm4XgwRn5kDM0N2xwiWeXyHqLwBeztqiCbrrF6To'
api_secret = '0aKKxmjdIa8e6QzgdhXESkqEpPyS4U8hpnxIRv9Z2y3RXChxywx5LOxZlIs3m7uZ'

client = Client(api_key, api_secret)

#candles = client.get_klines(symbol='BNBBTC', interval=Client.KLINE_INTERVAL_30MINUTE)
candles = client.get_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_30MINUTE)
print(len(candles))
print('candle0: ', candles[0])

closes = np.array([float(x[4]) for x in candles])

#print('stochrsi: ', talib.STOCHRSI(closes))

print('price: ', get_price('BTCUSDT'))

# TODO
#order = client.create_test_order(
#			symbol='BNBBTC',
#			side=SIDE_BUY,
#			type=ORDER_TYPE_LIMIT,
#			timeInForce=TIME_IN_FORCE_GTC,
#			quantity=1,
#			price=str('0.00001'))
#
#print(order)


# MAIN LOOP

def cancel_order(orderId):
	result = client.cancel_order(symbol=curr_symbol, orderId=orderId)
	print('Order cancelled, result = ', result)

activeTrade = False

purchaseQuantity = 0.00001
orderId = None
enterPrice = None

while True:
	time.sleep(5)

	currPrice = get_price(curr_symbol)
	modPrice = int(currPrice) % 100
	centPrice = int(currPrice) // 100

	# RSI based on 5 MINUTE DATA TODO change?
	candles = client.get_klines(symbol=curr_symbol, interval=Client.KLINE_INTERVAL_5MINUTE)
	df = pd.DataFrame(candles)
	df.columns=['timestart','open','high','low','close','?','timeend','?','?','?','?','?']
	df.timestart = [datetime.datetime.fromtimestamp(i/1000) for i in df.timestart.values]
	df.timeend = [datetime.datetime.fromtimestamp(i/1000) for i in df.timeend.values]

	float_data = [float(x) for x in df.close.values]
	np_float_data = np.array(float_data)
	rsi = talib.RSI(np_float_data, 14)
	df['rsi'] = rsi

	stochrsi = Stoch(df.rsi, df.rsi, df.rsi, 3, 3, 14)
	df['StochrsiK'],df['StochrsiD'] = stochrsi
	print('stochrsiK: ', df['StochrsiK'])

	newestK = df.StochrsiK.astype(str).iloc[-1]
	print('newestK: ', newestK)

	# Check order status. If completed, set activeTrade = False
	# TODO
	if activeTrade:
		order = client.get_order(symbol=curr_symbol, orderId=orderId)
		if order['status'] == 'Complete': # TODO ??
			activeTrade = False

	if not activeTrade and newestK < 33.0 and modPrice <= 20:
		# Place limit order
		order = client.create_test_order(
						symbol=curr_symbol,
						side=SIDE_BUY,
						type=ORDER_TYPE_LIMIT,
						timeInForce=TIME_IN_FORCE_GTC,
						quantity=purchaseQuantity,
						price=str(centPrice * 100.0 + 80))

		orderId = order['orderId']
		enterPrice = centPrice * 100.0 + 80

		activeTrade = True

	if activeTrade and enterPrice < currPrice and modPrice > 80:
		# Cancel Order
		cancel_order(orderId)
		activeTrade = False

	if activeTrade and enterPrice - currPrice > 50:
		cancel_order(orderId)
		activeTrade = False

	break
