export const sentimentEmojis = {
  positive: "😊",
  neutral: "😐", 
  negative: "😞"
};

export const getSentimentEmoji = (sentiment) => {
  if (!sentiment || sentiment === 'neutral') return sentimentEmojis.neutral;
  if (sentiment === 'positive') return sentimentEmojis.positive;
  if (sentiment === 'negative') return sentimentEmojis.negative;
  return sentimentEmojis.neutral;
};
