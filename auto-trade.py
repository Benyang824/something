import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.enums import *

api_key = 'your_api_key' # type your api key
api_secret = 'your_api_secrey' # type your api secret
client = Client(api_key, api_secret)
bm = BinanceSocketManager(client)

# 初始化或加載DataFrame
try:
    df = pd.read_csv('trading_data.csv', index_col='timestamp', parse_dates=True)
    print("成功加載之前的數據")
except FileNotFoundError:
    df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    print("未找到之前的數據，創建新的DataFrame")

def process_message(msg):
    global df
    kline = msg['k']
    if kline['x']:  # 確保K線已關閉
        new_row = {
            'timestamp': pd.to_datetime(kline['t'], unit='ms'),
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v'])
        }
        df = pd.concat(new_row, ignore_index=True)
        df.set_index('timestamp', inplace=True)
        trading_strategy(df)
        df.to_csv('trading_data.csv')  # 保存數據到文件

def trading_strategy(df):
    df['signal'] = 0
    df['position'] = 0
    df['entry_price'] = 0
    df['stop_loss'] = 0
    df['take_profit'] = 0
    win = 0
    lose = 0
    total = 0
    buyside = 0
    sellside = 0
    for i in range(1, len(df)):
        if i > 7:
            average = df['close'].iloc[i-7:i].mean()
        elif i == 1:
            average = df['close'].iloc[1]
        else:
            average = df['close'].iloc[1:i].mean()
        if df['position'].iloc[i-1] == 0:
            if float(df['close'].iloc[i]) > df['high'].iloc[i-1] and float(df['close'].iloc[i]) > average:
                buyside = buyside + 1
                df.at[df.index[i], 'signal'] = 1
                df.at[df.index[i], 'entry_price'] = float(df['close'].iloc[i])
                df.at[df.index[i], 'stop_loss'] = float(df['low'].iloc[i])
                df.at[df.index[i], 'position'] = 1
                # 設置槓桿
                client.futures_change_leverage(symbol='BTCUSDT', leverage=5)
                available_funds = 27 * 5  # 27 USDT with 5x leverage
                current_price = float(df['close'].iloc[i])
                quantity = available_funds / current_price
                # 下買單
                order = client.futures_create_order(
                    symbol='BTCUSDT',
                    side='BUY',
                    type='MARKET',
                    quantity=quantity)
            elif float(df['close'].iloc[i]) < df['low'].iloc[i-1] and float(df['close'].iloc[i]) < average:
                sellside = sellside + 1
                df.at[df.index[i], 'signal'] = -1
                df.at[df.index[i], 'entry_price'] = float(df['close'].iloc[i])
                df.at[df.index[i], 'stop_loss'] = float(df['high'].iloc[i])
                df.at[df.index[i], 'position'] = -1
                # 設置槓桿
                client.futures_change_leverage(symbol='BTCUSDT', leverage=5)
                available_funds = 27 * 5  # 27 USDT with 5x leverage
                current_price = float(df['close'].iloc[i])
                quantity = available_funds / current_price
                # 下賣單
                order = client.futures_create_order(
                    symbol='BTCUSDT',
                    side='SELL',
                    type='MARKET',
                    quantity=quantity)
        else:
            df.at[df.index[i], 'position'] = df['position'].iloc[i-1]
            df.at[df.index[i], 'entry_price'] = df['entry_price'].iloc[i-1]
            df.at[df.index[i], 'stop_loss'] = df['stop_loss'].iloc[i-1]
            df.at[df.index[i], 'take_profit'] = df['take_profit'].iloc[i-1]

            if df['position'].iloc[i] == 1:
                if df['low'].iloc[i] <= df['stop_loss'].iloc[i] or df['low'].iloc[i] <= df['low'].iloc[i-1]:
                    df.at[df.index[i], 'position'] = 0
                    if df['low'].iloc[i] <= df['stop_loss'].iloc[i]:
                        lose = lose + 1
                        total = total + 1
                        # 執行賣出操作以關閉多頭倉位
                        order = client.futures_create_order(
                            symbol='BTCUSDT',
                            side='SELL',
                            type='MARKET',
                            quantity=0.001)
                    elif float(df['low'].iloc[i]) <= float(df['low'].iloc[i-1]) and df['entry_price'].iloc[i] <= df['low'].iloc[i]:
                        win = win + 1
                        total = total + 1
                        # 執行賣出操作以關閉多頭倉位
                        order = client.futures_create_order(
                            symbol='BTCUSDT',
                            side='SELL',
                            type='MARKET',
                            quantity=0.001)
                    elif float(df['low'].iloc[i]) <= float(df['low'].iloc[i-1]) and df['entry_price'].iloc[i] > df['low'].iloc[i]:
                        lose = lose + 1
                        total = total + 1
                        # 執行賣出操作以關閉多頭倉位
                        order = client.futures_create_order(
                            symbol='BTCUSDT',
                            side='SELL',
                            type='MARKET',
                            quantity=0.001)
            elif df['position'].iloc[i] == -1:
                if df['high'].iloc[i] >= df['stop_loss'].iloc[i] or df['high'].iloc[i] >= df['high'].iloc[i]:
                    df.at[df.index[i], 'position'] = 0
                    if df['high'].iloc[i] >= df['stop_loss'].iloc[i]:
                        lose = lose + 1
                        total = total + 1
                        # 執行買入操作以關閉空頭倉位
                        order = client.futures_create_order(
                            symbol='BTCUSDT',
                            side='BUY',
                            type='MARKET',
                            quantity=0.001)
                    elif float(df['high'].iloc[i]) >= float(df['high'].iloc[i-1]):
                        win = win + 1
                        total = total + 1
                        # 執行買入操作以關閉空頭倉位
                        order = client.futures_create_order(
                            symbol='BTCUSDT',
                            side='BUY',
                            type='MARKET',
                            quantity=0.001)

# 開始WebSocket
conn_key = bm.start_kline_socket('BTCUSDT', process_message, interval=KLINE_INTERVAL_1MINUTE)
bm.start()

# 無限運行
while True:
    try:
        time.sleep(1)  # 保持程式運行
    except KeyboardInterrupt:
        bm.stop_socket(conn_key)
        bm.close()
        print("程式已停止")
        break
    except Exception as e:
        print(f"發生錯誤: {e}")
        bm.stop_socket(conn_key)
        bm.close()
        # 重新啟動WebSocket
        conn_key = bm.start_kline_socket('BTCUSDT', process_message, interval=KLINE_INTERVAL_1MINUTE)
        bm.start()

