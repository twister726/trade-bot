import talib
import numpy as np
import requests
import pandas as pd
import time
import datetime
import math
import sys
from ciso8601 import parse_datetime

from ftx_client import FtxClient


# api_key_test = 'wiYFjNZa8vQZ00HVlvviBZU8KlUk3P9BsOaFNgWQ'
# api_secret_test = 'FV3I-fMloT9dVIO5W1twDUZA385Q06VDjrN2mqeV'
api_key = '4MZCayt-zZKp3QQFOBgPFdwOK5B1zoxJPMeFAGKz'
api_secret = 'cfQxfctS5j7lR0iq-iGsiItt4znrH9P4AkF-IzMH'

# with open('api_keys.txt', 'r') as f:
#     lines = [x.rstrip('\n') for x in f.readlines()]
#     api_key = lines[0]
#     api_secret = lines[1]

curr_pairs = ['BTC', 'USD']
curr_symbol = '{}/{}'.format(curr_pairs[0], curr_pairs[1])
rsi_resolution = 900 # 15 minutes in seconds

logfile = 'ftx_log.log'
with open(logfile, 'w') as f:
    pass

client = FtxClient(api_key=api_key, api_secret=api_secret)


def logTrade(oldBalance, newBalance, branch, enterTime, enterPrice, exitPrice, orderid):
    with open(logfile, 'a') as f:
        f.write(f'oldBalance: {oldBalance}, newBalance: {newBalance}, branch: {branch}, enterTime: {enterTime}, enterPrice: {enterPrice}, exitPrice: {exitPrice}, orderid: {orderid}\n')
        
def Stoch(close,high,low, smoothk, smoothd, n):
    lowestlow = pd.Series.rolling(low,window=n,center=False).min()
    highesthigh = pd.Series.rolling(high, window=n, center=False).max()
    K = pd.Series.rolling(100*((close-lowestlow)/(highesthigh-lowestlow)), window=smoothk).mean()
    D = pd.Series.rolling(K, window=smoothd).mean()

    return K, D

def rsi(prices):
    i = 0
    upPrices=[]
    downPrices=[]
    #  Loop to hold up and down price movements
    while i < len(prices):
        if i == 0:
            upPrices.append(0)
            downPrices.append(0)
        else:
            if (prices[i]-prices[i-1])>0:
                upPrices.append(prices[i]-prices[i-1])
                downPrices.append(0)
            else:
                downPrices.append(prices[i]-prices[i-1])
                upPrices.append(0)
        i += 1
    x = 0
    avg_gain = []
    avg_loss = []
    #  Loop to calculate the average gain and loss
    while x < len(upPrices):
        if x <15:
            avg_gain.append(0)
            avg_loss.append(0)
        else:
            sumGain = 0
            sumLoss = 0
            y = x-14
            while y<=x:
                sumGain += upPrices[y]
                sumLoss += downPrices[y]
                y += 1
            avg_gain.append(sumGain/14)
            avg_loss.append(abs(sumLoss/14))
        x += 1
    p = 0
    RS = []
    RSI = []
    #  Loop to calculate RSI and RS
    while p < len(prices):
        if p <15:
            RS.append(0)
            RSI.append(0)
        else:
            RSvalue = (avg_gain[p]/avg_loss[p])
            RS.append(RSvalue)
            RSI.append(100 - (100/(1+RSvalue)))
        p+=1
        
#     print('RSI: ', RSI)
    
    return RSI

def get_RSI_df():
#     candles = client.get_klines(symbol=curr_symbol, interval=Client.KLINE_INTERVAL_15MINUTE)
    candles = client.get_candles(curr_symbol, rsi_resolution)
    opens = [x['open'] for x in candles]
    closes = [x['close'] for x in candles]
    highs = [x['high'] for x in candles]
    lows = [x['low'] for x in candles]
    startTimes = [x['time'] for x in candles]
    volumes = [x['volume'] for x in candles]
    df = pd.DataFrame(list(zip(opens, closes, highs, lows, startTimes, volumes)), columns=['open', 'close', 'high', 'low', 'startTime', 'volume'])
#     df.columns=['timestart','open','high','low','close','?','timeend','?','?','?','?','?']
#     df.timestart = [datetime.datetime.fromtimestamp(i/1000) for i in df.timestart.values]
#     df.timeend = [datetime.datetime.fromtimestamp(i/1000) for i in df.timeend.values]
    
    float_data = [float(x) for x in df.close.values]
    np_float_data = np.array(float_data)
    all_rsi = talib.RSI(np_float_data, 14)
#     float_data.reverse()
#     all_rsi1 = rsi(float_data)
#     print('diff: ', [all_rsi[i] - all_rsi1[i] for i in range(len(all_rsi))])
#     print('all_rsi: ', all_rsi)
#     print('len all_rsi: ', len(all_rsi))
    df['rsi'] = all_rsi
#     print('rsi: ', df['rsi'].astype(float).iloc[-1])

    stochrsi = Stoch(df.rsi, df.rsi, df.rsi, 3, 3, 14)
    df['StochrsiK'],df['StochrsiD'] = stochrsi
#     print('stochrsiK: ', df['StochrsiK'][-15:])
    
    return df

def get_RSI():
    df = get_RSI_df()
    newestK = df.StochrsiK.astype(float).iloc[-1]
    return newestK

def print_log(s):
    print(s)
    with open(logfile, 'a') as f:
        f.write(s + '\n')
        
        
price = client.get_price(curr_symbol)
print(price)
print(client.get_account_info())
print()
print('hi, ', client.get_balance(curr_pairs[1]))
print('My wallet: ', client.get_balances())
print()
candles = client.get_candles(curr_symbol, rsi_resolution)
print(len(candles))
print(candles[3])
print(parse_datetime(candles[3]['startTime']).timestamp())
# print(get_RSI())
print('#############')
print()
# print(client.get_order_status(7204332489))


def enterLong(price):
    curr_usd = client.get_balance('USD')
#     print('curr_usd: ', curr_usd)
#     usd_per_btc = client.get_price(curr_symbol)
    btc = curr_usd / price
    newprice = price + 10
    newbtc = btc - 0.001
    
#     print('newbtc: ', newbtc)
    
    # Market order
    while True:
        try:
            result = client.place_order(market=curr_symbol, side='buy', price=newprice, size=newbtc, type='limit')
            break
        except Exception as e:
            print_log('Error in enterLong placing order: ' + repr(e))
        
    print('res: ', result)
    orderid = result['id']
    
    # Wait for market order to get filled
    start_time = time.time()
    while True:
        try:
            status = client.get_order_status(orderid)['status'] 
        except Exception as e:
            print_log('Error in enterLong: ' + repr(e))
            
        if status == 'closed':
            # Check if cancelled
            if abs(curr_usd - client.get_balance('USD')) < 1.0:
                orderid = None
            break
            
        if time.time() - start_time > 60 * 60: # 1 hour
            print_log('Waited too long in enterLong')
            sys.exit(0) # Exit the script
            
        time.sleep(3)
        
    return orderid # Can be None if order is cancelled
    
def exitLong():
    curr_btc = client.get_balance('BTC')
#     print('curr_btc: ', curr_btc)
    curr_usdvalue = client.get_usdValue('BTC')
    price = curr_usdvalue / curr_btc
    #print('curr_usdvalue: ', curr_usdvalue)
    #print('curr_btc: ', curr_btc)
    newprice = price - 10
    #print('newprice: ', newprice)
    
    result = client.place_order(market=curr_symbol, side='sell', price=newprice, size=curr_btc, type='limit', ioc=False)
    print('res: ', result)
    
    orderid = result['id']
    
    # Wait for market order to get filled
#     while client.get_order_status(orderid)['status'] != 'closed':
#         time.sleep(3)
        
    start_time = time.time()
    while True:
        try:
            status = client.get_order_status(orderid)['status'] 
        except Exception as e:
            print_log('Error in enterLong: ' + repr(e))
            
        if status == 'closed':
            # Check if order is cancelled
            if abs(curr_btc - client.get_balance('BTC')) < 0.00001:
                orderid = None
            break
            
        if time.time() - start_time > 60 * 60: # 1 hour
            print_log('Waited too long in exitLong')
            sys.exit(0) # Exit script
            
        time.sleep(3)
        
    return orderid


gap = 100.0
rsi_low_thresh = 33.0

activeLong = False
enterPrice = None
exitPrice = None
enterTime = None


while True:
    time.sleep(0.5)
    
    try:
        currPrice = client.get_price(curr_symbol)
    except Exception as e:
        print_log('Error in currPrice: ' + repr(e))
        continue
    nearestMult = (currPrice//gap) * gap
    modPrice = currPrice - nearestMult
    centPrice = currPrice // gap
    
    currTime = int(time.time())
    
    # Get RSI
    rsi = get_RSI()
    print('stochRSI: ', rsi)
#     print(type(newestK))
    
    if not activeLong and rsi < rsi_low_thresh and modPrice <= 0.2*gap:
        oldBalance = client.get_balance('USD')
        orderid = enterLong(currPrice)
        if orderid == None:
            continue

        print('Entering long with {} USD at {}'.format(oldBalance, currPrice))
        activeLong = True
        enterPrice = currPrice + 1
        enterTime = int(time.time())
        humanTime = datetime.datetime.fromtimestamp(enterTime).strftime('%Y-%m-%d %H:%M:%S')
        print_log('Entering long with {} USD at {} at {} orderid = {}'.format(oldBalance, enterPrice, humanTime, orderid))
        
    if activeLong and enterPrice < currPrice and modPrice >= 0.8*gap:
        orderid = exitLong()
        if orderid == None: # Order cancelled
            continue

        exitPrice = currPrice - 10
        print('Exiting long at {}'.format(exitPrice))
        humanTime = datetime.datetime.fromtimestamp(currTime).strftime('%Y-%m-%d %H:%M:%S')
        logTrade(oldBalance, newBalance=client.get_balance('USD'), branch='Success', enterTime=humanTime, enterPrice=enterPrice, exitPrice=exitPrice, orderid=orderid)
        activeLong = False
        
    if activeLong and enterPrice - currPrice > 0.5*gap:
        orderid = exitLong()
        if orderid == None: # Order cancelled
            continue
            
        exitPrice = currPrice - 10
        print('Exiting long at {}'.format(exitPrice))
        activeLong = False
        humanTime = datetime.datetime.fromtimestamp(enterTime).strftime('%Y-%m-%d %H:%M:%S')
        logTrade(oldBalance, newBalance=client.get_balance('USD'), branch='Cut loss', enterTime=humanTime, enterPrice=enterPrice, exitPrice=currPrice, orderid=orderid)
        
        
