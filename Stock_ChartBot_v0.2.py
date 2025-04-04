#Stock ChartBot v0.2
#by TorqueDog -- 2025/Apr/04
import os
import time
import pytz
import schedule
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import logging
from datetime import datetime, timedelta, time as dtime
from scipy.signal import argrelextrema
from matplotlib.ticker import MaxNLocator

# Configuration
FUTURES = ['ES=F', 'NQ=F']  # Yahoo Finance symbols for ES and NQ futures
STOCKS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'TSLA', 'GOOGL']
OUTPUT_PATH = 'stock_charts'
TIMEFRAMES = ['1d', '4h', '30m']

# Global variable for logger; it will be configured in main
logger = logging.getLogger('chartbot')
logger.setLevel(logging.DEBUG)

def configure_logger(verbose=False):
    # Create file handler to write to chartbot_debug.log
    file_handler = logging.FileHandler("chartbot_debug.log")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if verbose:
        # Also log to console if verbose is enabled
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

def ensure_output_directory():
    """Ensure the output directory exists"""
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

def fix_data_columns(data):
    """
    Ensure that the DataFrame has the expected columns.
    If columns are a MultiIndex, flatten them.
    Also, if column names are in lowercase, or if 'Adj Close' exists but not 'Close',
    rename them accordingly. If all column names are identical, reset them to expected names.
    """
    expected = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    # Flatten multi-level columns if needed
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(1)
    
    # If all column names are the same, override with expected names.
    if len(set(data.columns)) == 1:
        data.columns = expected
        return data

    # Otherwise, try to fix mismatches.
    for col in expected:
        if col not in data.columns:
            lower = col.lower()
            if lower in data.columns:
                data.rename(columns={lower: col}, inplace=True)
            elif col == 'Close' and 'Adj Close' in data.columns:
                data.rename(columns={'Adj Close': 'Close'}, inplace=True)
    return data

def get_extended_period(now):
    """
    Given the current datetime (assumed to be Eastern Time),
    return the extended market period: from previous day 6:00 PM ET
    to current day 9:00 AM ET.
    """
    today = now.date()
    eastern = pytz.timezone('US/Eastern')
    extended_start = eastern.localize(datetime.combine(today - timedelta(days=1), dtime(18, 0)))
    extended_end = eastern.localize(datetime.combine(today, dtime(9, 0)))
    logger.debug(f"Extended period from {extended_start} to {extended_end}")
    return extended_start, extended_end

def get_extended_data(symbol):
    """
    Download intraday data (30-minute interval) with extended hours,
    fix columns if necessary, and then filter for the extended market period.
    """
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    extended_start, extended_end = get_extended_period(now)
    
    logger.debug(f"Downloading data for {symbol} for period '2d' at 30m interval with prepost=True")
    data = yf.download(symbol, period='2d', interval='30m', prepost=True)
    if data.empty:
        logger.debug(f"Downloaded data for {symbol} is empty.")
        return data, extended_start, extended_end

    # Fix columns on the downloaded data
    data = fix_data_columns(data)
    
    # Ensure index is timezone-aware in US/Eastern
    if data.index.tzinfo is None or data.index.tz is None:
        data.index = data.index.tz_localize('UTC').tz_convert(eastern)
    else:
        data.index = data.index.tz_convert(eastern)
    logger.debug(f"Data for {symbol} after timezone conversion: {data.shape[0]} rows. Columns: {data.columns.tolist()}")
    
    # Filter the data to the extended market period
    extended_data = data[(data.index >= extended_start) & (data.index <= extended_end)]
    logger.debug(f"Extended data for {symbol} filtered: {extended_data.shape[0]} rows. Columns: {extended_data.columns.tolist()}")
    
    # Reapply the column-fixing on the filtered data to ensure expected columns exist
    extended_data = fix_data_columns(extended_data)
    logger.debug(f"Extended data for {symbol} after re-fix: Columns: {extended_data.columns.tolist()}")
    
    return extended_data, extended_start, extended_end

def find_support_resistance(data, order=5):
    """
    Find support and resistance levels using local minima and maxima.
    Returns two lists: supports and resistances.
    """
    if data.empty:
        return [], []
    close_prices = data['Close'].values
    if len(close_prices) < (order * 2 + 1):
        level = float(close_prices[0])
        return [level], [level]
    
    supports_idx = argrelextrema(close_prices, np.less, order=order)[0]
    resistances_idx = argrelextrema(close_prices, np.greater, order=order)[0]
    supports = [close_prices[i] for i in supports_idx]
    resistances = [close_prices[i] for i in resistances_idx]
    return supports, resistances

def resample_data(data, timeframe):
    """
    Resample data to the desired timeframe.
    '1d' -> 1 day, '4h' -> 4 hours, '30m' -> no change.
    """
    if timeframe == '1d':
        rule = '1D'
    elif timeframe == '4h':
        rule = '4h'
    elif timeframe == '30m':
        return data  # Already at 30m resolution
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    resampled = data.resample(rule).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    logger.debug(f"Resampled data to {timeframe} has {resampled.shape[0]} rows.")
    return resampled

def plot_extended_chart(extended_data, display_symbol, extended_start, extended_end, support_res_levels, extended_high, extended_low):
    """
    Plot the extended market price action along with:
      - Extended period high and low lines.
      - Support (solid) and resistance (dashed) levels computed on
        1d (red), 4h (blue), and 30m (orange) intervals.
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot the raw extended market price action (30m data)
    ax.plot(extended_data.index, extended_data['Close'], color='black', linewidth=1.5, label='Price Action')
    ax.axhline(y=extended_high, color='green', linestyle='--', linewidth=2,
               label=f"Extended High: {extended_high:.2f}")
    ax.axhline(y=extended_low, color='purple', linestyle='--', linewidth=2,
               label=f"Extended Low: {extended_low:.2f}")
    
    color_map = {'1d': 'red', '4h': 'blue', '30m': 'orange'}
    order_map = {'1d': 1, '4h': 2, '30m': 3}
    
    for tf in TIMEFRAMES:
        resampled = resample_data(extended_data, tf)
        order = order_map.get(tf, 3)
        supports, resistances = find_support_resistance(resampled, order=order)
        logger.debug(f"{display_symbol} {tf} - Supports: {supports}, Resistances: {resistances}")
        for level in supports:
            ax.axhline(y=level, color=color_map[tf], linestyle='-', alpha=0.7, linewidth=1,
                       label=f"{tf.upper()} Support")
        for level in resistances:
            ax.axhline(y=level, color=color_map[tf], linestyle='--', alpha=0.7, linewidth=1,
                       label=f"{tf.upper()} Resistance")
    
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())
    
    ax.set_title(f"{display_symbol} Extended Market\n({extended_start.strftime('%Y-%m-%d %I:%M %p')} ET to {extended_end.strftime('%Y-%m-%d %I:%M %p')} ET)", fontsize=14)
    ax.set_xlabel('Date/Time', fontsize=12)
    ax.set_ylabel('Price', fontsize=12)
    
    # Set the x-axis to show both date and time in Eastern Time
    ax.xaxis.set_major_locator(MaxNLocator(10))
    eastern = pytz.timezone('US/Eastern')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M', tz=eastern))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    return fig

def generate_chart_for_symbol(symbol, display_symbol):
    """
    Generate and save the extended market chart for the given symbol.
    """
    extended_data, extended_start, extended_end = get_extended_data(symbol)
    if extended_data.empty:
        logger.debug(f"No extended data available for {display_symbol}. Skipping chart generation.")
        return

    try:
        extended_high = float(extended_data['High'].max())
        extended_low = float(extended_data['Low'].min())
    except KeyError as e:
        logger.debug(f"KeyError encountered for {display_symbol}: {e}")
        logger.debug(f"Columns available: {extended_data.columns.tolist()}")
        return

    support_res_levels = {}
    for tf in TIMEFRAMES:
        resampled = resample_data(extended_data, tf)
        order = 1 if tf == '1d' else (2 if tf == '4h' else 3)
        supports, resistances = find_support_resistance(resampled, order=order)
        support_res_levels[tf] = {'supports': supports, 'resistances': resistances}
    
    fig = plot_extended_chart(extended_data, display_symbol, extended_start, extended_end, support_res_levels, extended_high, extended_low)
    
    date_str = datetime.now(pytz.timezone('US/Eastern')).strftime('%m%d%Y')
    filename = f"{date_str} - {display_symbol} Extended Chart.png"
    filepath = os.path.join(OUTPUT_PATH, filename)
    fig.savefig(filepath)
    plt.close(fig)
    logger.debug(f"Generated chart for {display_symbol} saved at: {filepath}")

def generate_charts():
    """Generate charts for all symbols (both futures and stocks) using extended market data."""
    ensure_output_directory()
    
    for symbol in FUTURES:
        display_symbol = 'ES' if symbol == 'ES=F' else 'NQ'
        try:
            generate_chart_for_symbol(symbol, display_symbol)
        except Exception as e:
            logger.error(f"Error generating chart for {display_symbol}: {str(e)}")
    
    for symbol in STOCKS:
        try:
            generate_chart_for_symbol(symbol, symbol)
        except Exception as e:
            logger.error(f"Error generating chart for {symbol}: {str(e)}")

def job():
    """Job to run at scheduled time"""
    logger.debug(f"Starting chart generation at {datetime.now()}")
    try:
        generate_charts()
        logger.debug(f"Chart generation completed at {datetime.now()}")
    except Exception as e:
        logger.error(f"Error generating charts: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def set_output_path(path):
    """Set the output path for chart storage"""
    global OUTPUT_PATH
    if os.path.isdir(path) or not os.path.exists(path):
        OUTPUT_PATH = path
        ensure_output_directory()
        logger.debug(f"Output path set to: {OUTPUT_PATH}")
    else:
        logger.error(f"Invalid directory path: {path}")

def run_scheduler():
    """Run the scheduler indefinitely"""
    schedule.every().day.at("09:00").do(job)
    
    logger.debug(f"Scheduler started. Charts will be generated daily at 9:00 AM Eastern Time.")
    logger.debug(f"Charts will be saved to: {os.path.abspath(OUTPUT_PATH)}")
    
    run_now = input("Do you want to generate charts now? (y/n): ").strip().lower()
    if run_now == 'y':
        job()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.debug("\nApplication stopped by user.")

if __name__ == "__main__":
    print("Stock ChartBot v0.2")
    print("===================")
    
    verbose_input = input("Run in verbose mode? (y/n): ").strip().lower()
    verbose = True if verbose_input == 'y' else False
    configure_logger(verbose)
    
    custom_path = input(f"Enter output path (press Enter for default '{OUTPUT_PATH}'): ").strip()
    if custom_path:
        set_output_path(custom_path)
    else:
        ensure_output_directory()
    
    run_scheduler()
