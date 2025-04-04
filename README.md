# Stock ChartBot
**Stock ChartBot** is a Python application used for generating charts every morning pre-market for the Mag7 and market futures based off of their extended market trading periods.

## What is the goal of this bot?
This bot's goal is to aid the user in the gauging of the market sentiment prior to the opening of trading every morning at 9:30 AM Eastern. It does this by creating a series of charts reviewing the extended market trading period from market close the previous day to market open on the day of execution. It does not apply any sort of logic in the process nor does it inform the user what it believes to be the sentiment of the day. The interpretation of market sentiment the trader uses is completely up to them, but these charts can help a trader to make an informed choice.

## What exactly is the bot doing?
The bot fetches data from Yahoo! Finance to pull price action, high, low, resistance, and support levels for each of the futures and stocks that it is programmed to check, and uses 1D, 4h, and 30m intervals to show the levels of support and resistance. It then generates a stock chart in PNG format and saves it to a folder of the user's choosing (default is [run_directory]\stock_charts).

For example, if Stock ChartBot is generating charts at 9 AM ET on March 26, 2025, then each chart will contain a given future or stock's post-market activity starting from 6 PM ET on March 25, 2025 until pre-market at 9 AM ET on March 26, 2025.

The list of futures and stocks that Stock ChartBot will fetch data for is, in order: <br />
&bull; **ES** - E-mini S&P 500 futures <br />
&bull; **NQ** - E-mini Nasdaq 100 futures <br />
&bull; **AAPL** - Apple Inc. <br />
&bull; **MSFT** - Microsoft Corporation <br />
&bull; **NVDA** - Nvidia Corporation <br />
&bull; **AMZN** - Amazon.com, Inc. <br />
&bull; **META** - Meta Platforms, Inc. <br />
&bull; **TSLA** - Tesla, Inc. <br />
&bull; **GOOGL** - Alphabet Inc. <br />


## How do I use it?
Before you begin, you'll want to make sure you have the supporting modules installed using PIP.
```
pip install schedule pytz pandas yfinance matplotlib scipy numpy
```

Simply run the .py file any time. To ensure successful execution, Stock ChartBot will ask if you want to generate stock charts when it is loaded. This can be helpful if you are writing the charts to a location other than the default. It can also be run in a 'verbose' logging mode to aid in troubleshooting, though you will always have a chartbot_debug.log in the directory where the app is executed from.

Once you've started Stock ChartBot, keep it running in the background and it'll do the rest. Stock ChartBot runs on a schedule of 9 AM ET every morning. It typically takes between 3-4 seconds from the time the first chart is generated (ES) to the last chart (GOOGL) is written to disk and ready for viewing.

## Any bugs outstanding?
&bull; I don't think the 1D / 4h / 30m resolutions for the resistance and support lines actually works all that well right now, but you can get some idea. <br />
&bull; Stock ChartBot runs at 9 AM ET on the weekends too, which... yeah, is sort of pointless. But the fix would be to create a chart on Monday morning combining Friday's extended market period with Monday's pre-market activity, so that'll come one day. <br />
&bull; Probably a lot more, but this is very new, so eh.

## Any examples of the output?
Sure! It isn't perfect, but so far it does the job.
![04042025 - ES Extended Chart](https://github.com/user-attachments/assets/511da5d1-6851-46bd-91f1-923631e8a40e)
![04042025 - NVDA Extended Chart](https://github.com/user-attachments/assets/73cea62c-4d92-4104-8cde-415b449572dc)
