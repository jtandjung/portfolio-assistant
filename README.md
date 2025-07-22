# Portfolio Assistant Program
Developed a Python program to notify users of real-time price movements and latest news of selected stocks

## General Information
Personal investing is a great way to save and passively grow your money but it is not without effort. To effectively invest, keeping track of your investments and of the broader stock market is an important task that can be both easy to forget and time-consuming. This program helps with that by sending the user a news overview and upcoming earnings dates for selected stocks every day at market open. It also monitors the selected stocks' prices in real-time and notifies the user when price changes cross pre-defined thresholds.

## Technologies Used
- Python
- Alpha Vantage API
- Finnhub API
- Twilio API
- WebSocket
- PythonAnywhere

## Features
- Automated messaging with PythonAnywhere
- Real-time stock price monitoring through WebSocket
- Easy to specify what stocks the user wants to be monitored in config.py file (along with necessary API keys and parameters)

## Usage
- Fill in necessary information for API keys and parameters in config.py file
- Specify which stocks to monitor in ticker_list in config.py file
- (Optional) Change price percentage change thresholds at which to send a message to the user [see main.py line 119]
