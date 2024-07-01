from flask import Flask, send_from_directory, jsonify, request
import pandas as pd
import datetime
import re
import requests
import praw
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import ssl
from flask_caching import Cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable SSL certificate verification for NLTK downloads
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Ensure the lexicon is downloaded before the app is started
nltk.download('vader_lexicon')

app = Flask(__name__, static_folder='static', static_url_path='')
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

@app.route('/')
def serve_static_index():
    return send_from_directory(app.static_folder, 'index.html')

@cache.cached(timeout=300, query_string=True)
@app.route('/api/tickers', methods=['GET'])
def get_tickers():
    min_sentiment = float(request.args.get('minSentiment', 0))
    max_sentiment = float(request.args.get('maxSentiment', 1))
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    num_posts = int(request.args.get('numPosts', 100))

    if start_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)

    subreddits = ["wallstreetbets", "stocks", "investing", "options", "stockmarket", "pennystocks", "cryptocurrency", "daytrading", "robinhood", "thetagang", "weedstocks"]
    data = []
    now = datetime.datetime.now()
    days_ago = now - datetime.timedelta(days=7)

    for subreddit in subreddits:
        for submission in reddit.subreddit(subreddit).new(limit=num_posts):
            submission_time = datetime.datetime.fromtimestamp(submission.created_utc)
            if start_date and submission_time < start_date:
                continue
            if end_date and submission_time > end_date:
                continue
            if submission_time < days_ago:
                break
            post_data = {
                "subreddit": subreddit,
                "title": submission.title,
                "score": submission.score,
                "id": submission.id,
                "url": submission.permalink,
                "author": str(submission.author),
                "created": submission.created_utc,
                "body": submission.selftext
            }
            data.append(post_data)

    df = pd.DataFrame(data)

    if df.empty or 'title' not in df.columns:
        return jsonify([])

    sia = SentimentIntensityAnalyzer()

    def get_sentiment(text):
        if isinstance(text, str):
            return sia.polarity_scores(text)['compound']
        else:
            return 0

    df['title_sentiment'] = df['title'].apply(get_sentiment)
    df['body_sentiment'] = df['body'].apply(get_sentiment)
    df['average_sentiment'] = (df['title_sentiment'] + df['body_sentiment']) / 2
    df['created_dt'] = pd.to_datetime(df['created'], unit='s')

    url = 'https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt'
    response = requests.get(url)
    tickers = response.text.strip().split('\n')
    valid_tickers = set(tickers)

    def find_potential_tickers(text):
        return re.findall(r'\b[A-Z]{2,4}\b', text)

    def filter_valid_tickers(tickers_list, valid_tickers):
        return [ticker for ticker in tickers_list if ticker in valid_tickers]

    df['title_tickers'] = df['title'].apply(find_potential_tickers)
    df['body_tickers'] = df['body'].apply(find_potential_tickers)
    df['valid_title_tickers'] = df['title_tickers'].apply(lambda x: filter_valid_tickers(x, valid_tickers))
    df['valid_body_tickers'] = df['body_tickers'].apply(lambda x: filter_valid_tickers(x, valid_tickers))

    df['date'] = pd.to_datetime(df['created'], unit='s').dt.date
    df = df.explode('valid_title_tickers').groupby(['date', 'valid_title_tickers']).agg({
        'title_sentiment': 'mean',
        'body_sentiment': 'mean',
        'average_sentiment': 'mean',
        'score': 'sum',
        'title': 'first',
        'body': 'first',
        'author': 'first',
        'url': 'first',
        'subreddit': 'first'
    }).reset_index()
    df.rename(columns={'valid_title_tickers': 'ticker'}, inplace=True)

    sp500_url = 'https://gist.githubusercontent.com/ZeccaLehn/f6a2613b24c393821f81c0c1d23d4192/raw/fe4638cc5561b9b261225fd8d2a9463a04e77d19/SP500.csv'
    sp500_df = pd.read_csv(sp500_url)
    sp500_tickers = set(sp500_df['Symbol'])

    df = df[df['ticker'].isin(sp500_tickers)]

    filtered_df = df[(df['average_sentiment'] >= min_sentiment) & (df['average_sentiment'] <= max_sentiment)]

    return jsonify(filtered_df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
