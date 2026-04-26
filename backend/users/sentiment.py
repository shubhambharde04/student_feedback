"""
Sentiment analysis utility using TextBlob.
Classifies feedback comments as positive, neutral, or negative.
"""
from textblob import TextBlob


def analyze_sentiment(text):
    """
    Analyze the sentiment of text using TextBlob.
    
    Returns:
        tuple: (polarity, label) where label is 'positive', 'neutral', or 'negative'
    """
    if not text or not text.strip():
        return 0.0, 'neutral'

    blob = TextBlob(text)
    polarity = blob.sentiment[0]

    if polarity > 0.1:
        label = 'positive'
    elif polarity < -0.1:
        label = 'negative'
    else:
        label = 'neutral'
        
    return round(float(polarity), 3), label


def get_sentiment_emoji(sentiment):
    """Return emoji for a given sentiment."""
    emojis = {
        'positive': '😊',
        'neutral': '😐',
        'negative': '😞',
    }
    return emojis.get(sentiment, '😐')
