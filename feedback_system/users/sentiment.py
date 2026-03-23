"""
Sentiment analysis utility using TextBlob.
Classifies feedback comments as positive, neutral, or negative.
"""
from textblob import TextBlob


def analyze_sentiment(text):
    """
    Analyze the sentiment of text using TextBlob.
    
    Returns:
        str: 'positive', 'neutral', or 'negative'
    """
    if not text or not text.strip():
        return 'neutral'

    blob = TextBlob(text)
    polarity = blob.sentiment[0]

    if polarity > 0.1:
        return 'positive'
    elif polarity < -0.1:
        return 'negative'
    else:
        return 'neutral'


def get_sentiment_emoji(sentiment):
    """Return emoji for a given sentiment."""
    emojis = {
        'positive': '😊',
        'neutral': '😐',
        'negative': '😞',
    }
    return emojis.get(sentiment, '😐')
