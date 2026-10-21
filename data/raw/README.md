# Raw data

`Tweets.csv` is the **Twitter US Airline Sentiment** dataset (14,640 tweets about six US airlines, February 2015), originally published by CrowdFlower / Figure Eight in its *Data for Everyone* library and redistributed on Kaggle.

- Source: https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment
- Mirror used for credential-free download: https://huggingface.co/datasets/osanseviero/twitter-airline-sentiment
- Licence: **CC BY-NC-SA 4.0** (attribution, non-commercial, share-alike). It is redistributed here unchanged and with attribution. Derived files produced by this project (`data/processed/`) are under the same licence.
- SHA-256: `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` (verified on every load by `sentiment_ml.data`).

The file is used only for training and evaluation. It is not modified. Known text artifacts are repaired in code (see `AIRLINE_TEXT_ARTIFACTS` in `ml/sentiment_ml/data.py`).
