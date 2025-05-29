from binance.client import Client
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dateutil import parser

# 設置API密鑰
api_key = 'your_api_key'# type your api key
api_secret = 'your_api_secret'# type your api secret

client = Client(api_key, api_secret)

# 獲取歷史K線數據
def get_klines(symbol, interval, start_str):
    start_date = parser.parse(start_str, fuzzy=True).replace(tzinfo=timezone.utc)
    klines = client.get_historical_klines(symbol, interval, start_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    return df

def calculate_rsi(df, window=14):
    delta = df['close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df['RSI'] = rsi
    return df

# 計算移動平均線
def calculate_ma(df, short_window=5, long_window=15):
    df['MA_short'] = df['close'].rolling(window=short_window).mean()
    df['MA_long'] = df['close'].rolling(window=long_window).mean()
    return df

# 交易策略
def trading_strategy(df):
    df = calculate_rsi(df)
    df = calculate_ma(df)
    df['signal'] = 0
    df['position'] = 0
    df['entry_price'] = 0
    df['stop_loss'] = 0
    df['take_profit'] = 0

    for i in range(1, len(df)):
        average = df['close'].iloc[max(0, i-10):i].mean()
        std_dev = df['close'].iloc[max(0, i-10):i].std()
        
        if df['position'].iloc[i-1] == 0:
            if df['RSI'].iloc[i] < 30 and df['MA_short'].iloc[i] > df['MA_long'].iloc[i]:
                df.at[df.index[i], 'signal'] = 1
                df.at[df.index[i], 'entry_price'] = float(df['close'].iloc[i])
                df.at[df.index[i], 'stop_loss'] = df['low'].iloc[max(0, i-5):i].min()
                df.at[df.index[i], 'take_profit'] = float(df['close'].iloc[i]*1.04)
                df.at[df.index[i], 'position'] = 1
            elif df['RSI'].iloc[i] > 70 and df['MA_short'].iloc[i] < df['MA_long'].iloc[i]:
                df.at[df.index[i], 'signal'] = -1
                df.at[df.index[i], 'entry_price'] = float(df['close'].iloc[i])
                df.at[df.index[i], 'stop_loss'] = df['high'].iloc[max(0, i-5):i].max()
                df.at[df.index[i], 'take_profit'] = float(df['close'].iloc[i]*0.96)
                df.at[df.index[i], 'position'] = -1
        else:
            df.at[df.index[i], 'position'] = df['position'].iloc[i-1]
            df.at[df.index[i], 'entry_price'] = df['entry_price'].iloc[i-1]
            df.at[df.index[i], 'stop_loss'] = df['stop_loss'].iloc[i-1]
            df.at[df.index[i], 'take_profit'] = df['take_profit'].iloc[i-1]

            diff = abs(df['entry_price'].iloc[i] - df['stop_loss'].iloc[i])
            
            if df['position'].iloc[i] == 1:
                if df['MA_short'].iloc[i] < df['MA_long'].iloc[i]:
                    df.at[df.index[i], 'position'] = 0
            elif df['position'].iloc[i] == -1:
                if df['MA_short'].iloc[i] > df['MA_long'].iloc[i]:
                    df.at[df.index[i], 'position'] = 0

    return df

# 回測策略
def backtest_strategy(df):
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['returns'] * df['position'].shift()*3
    #print(df['position'].shift(), df['position'])
    df['cumulative_returns'] = (1 + df['returns']).cumprod()
    df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
    return df

# 獲取數據並應用策略
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_5MINUTE
start_str = '12 months ago UTC'

df = get_klines(symbol, interval, start_str)
df = trading_strategy(df)
df = backtest_strategy(df)

# 繪製績效圖表
import matplotlib.pyplot as plt

plt.figure(figsize=(14, 7))
plt.plot(df.index, df['cumulative_returns'], label='Buy and Hold Returns')
plt.plot(df.index, df['cumulative_strategy_returns'], label='Strategy Returns')
plt.legend()
plt.show()
