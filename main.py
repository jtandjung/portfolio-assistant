import requests
import config
import finnhub
from datetime import datetime
from datetime import timedelta
import pytz
from twilio.rest import Client
import json
import websocket

# Setting up access to APIS and clients
AV_API_KEY = config.alphavantage_api_key
FH_API_KEY = config.finnhub_api_key

finnhub_client = finnhub.Client(api_key=FH_API_KEY)

account_sid = config.twilio_account_sid
auth_token = config.twilio_auth_token
client = Client(account_sid, auth_token)
TWILIO_MESSAGING_SERVICE_SID = config.twilio_messaging_service_sid
TWILIO_PHONE_NUMBER = config.twilio_phone_number
DEST_PHONE_NUMBER = config.dest_phone_number

# List of tickers to watch
TICKERS = config.ticker_list

# Flags for use in monitoring stock prices and alerting for percent changes
TICKER_FLAGS = {}
for ticker in TICKERS:
    TICKER_FLAGS[f"{ticker}_5"] = False
    TICKER_FLAGS[f"{ticker}_10"] = False

# Access real time stock price info, earnings info, news headlines
def get_news(ticker: str):
    news_params = {
        "function":"NEWS_SENTIMENT",
        "tickers":ticker,
        "apikey":AV_API_KEY
    }
    url = "https://www.alphavantage.co/query"
    r = requests.get(url, params=news_params)
    data = r.json()
    #print(data)

    return data

def get_earnings_calendar(ticker: str):
    cal = finnhub_client.earnings_calendar(_from=datetime.now().date(), to=datetime.now().date() + timedelta(days=28), symbol=ticker, international=False)
    
    if len(cal['earningsCalendar']) >= 1:
        return cal['earningsCalendar']

def get_stock_info(ticker: str):
    data = finnhub_client.quote(ticker)
    #print(finnhub_client.quote(ticker))

    return data

# Send earnings dates, if any exist, within one month of today for each ticker being watched to phone
earnings_content = []

for ticker in TICKERS:
    earnings_date = get_earnings_calendar(ticker)

    if earnings_date != None:
        earnings_content.append(f"{ticker}: {earnings_date[0]['date']}\n")
    
if len(earnings_content) > 1:
    message = client.messages.create(
        messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
        body=f"Earnings Calendar:\n{''.join(earnings_content)}",
        from_=TWILIO_PHONE_NUMBER,
        to=DEST_PHONE_NUMBER,
    )

# Send top 3 latest news articles (title + summary) for each ticker being watched to phone
for ticker in TICKERS:
    news_content = []
    newsfeed = get_news(ticker)
    
    for article in newsfeed['feed']:
        for entry in article['ticker_sentiment']:
            if entry['ticker'] == ticker and float(entry['relevance_score']) > 0.5:
                news_content.append(f"Title: {article['title']}\nSummary: {article['summary']}\n\n")

    if len(news_content) > 0:

        for article in news_content[:3]:
            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=f"{ticker}\n\n{article}",
                from_=TWILIO_PHONE_NUMBER,
                to=DEST_PHONE_NUMBER,
            )
    else:
        message = client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            body=f"Error. No {ticker} stories found.",
            from_=TWILIO_PHONE_NUMBER,
            to=DEST_PHONE_NUMBER,
        )

# Monitor ticker current prices until 10 AM EST and send alerts if price has moved 5% and 10% from previous close price
eastern = pytz.timezone('US/Eastern')
current_est_time = datetime.now(eastern)

prev_close_prices = {}
for ticker in TICKERS:
    prev_close_prices[ticker] = finnhub_client.quote(ticker)['pc']
    
def on_message(ws, message):
    #print("Received data: "+message)
    converted_message = json.loads(message)
    
    for entry in converted_message['data']:
        prev_close_price_sym = prev_close_prices[entry['s']]
        percent_diff = round(((entry['p'] - prev_close_price_sym) / prev_close_price_sym) * 100, 2)
        
        if abs(percent_diff) > 5 and TICKER_FLAGS[f"{entry['s']}_5"] == False:
            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=f"{entry['s']}: {percent_diff}%",
                from_=TWILIO_PHONE_NUMBER,
                to=DEST_PHONE_NUMBER,
            )
            TICKER_FLAGS[f"{entry['s']}_5"] = True
            
        if abs(percent_diff) > 10 and TICKER_FLAGS[f"{entry['s']}_10"] == False:
            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=f"{entry['s']}: {percent_diff}%",
                from_=TWILIO_PHONE_NUMBER,
                to=DEST_PHONE_NUMBER,
            )
            TICKER_FLAGS[f"{entry['s']}_10"] = True
            
    if datetime.now(eastern).time() > datetime.strptime('10:00', '%H:%M').time():
        ws.close()

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    for ticker in TICKERS:
        ws.send(f'{{"type":"subscribe","symbol":"{ticker}"}}')

ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=d1u8ct1r01qp7ee28s6gd1u8ct1r01qp7ee28s70",
                          on_message = on_message,
                          on_error = on_error,
                          on_close = on_close)
ws.on_open = on_open
ws.run_forever()

# Send current price and percent change for all tickers at 10 AM EST
sms_10AM_summary = []

for ticker in TICKERS:
    ticker_info = finnhub_client.quote(ticker)
    sms_10AM_summary.append(f"{ticker}: {ticker_info['c']}, {ticker_info['dp']}%\n")

message = client.messages.create(
    messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
    body=''.join(sms_10AM_summary),
    from_=TWILIO_PHONE_NUMBER,
    to=DEST_PHONE_NUMBER
)