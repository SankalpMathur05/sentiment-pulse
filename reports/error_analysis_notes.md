### Reviewed error patterns

The examples above (plus the wider list of test errors) were read by hand and grouped into six patterns. Quotes are shortened; agreement = `airline_sentiment_confidence`.

**1. Sarcasm and ironic thanks (negative → positive).** "thanks", "thank you" and "!" are among the strongest positive words in this data, and a bag-of-words model adds them up without understanding irony.
- *"thank you for the robotic and non helpful assistance."* (agreement 1.00, predicted positive 0.95)
- *"thanks for being so bad you make a two day train trip look appealing!!"*
- *"thanks for having ground crews that are surprised when flights arrive. #beingsuckontarmacsucks!"*
- Outside the test set, the demo example *"Oh great, another 3 hour delay. Thanks @united 🙄"* is also predicted positive.

**2. Label noise: the model is arguably right (any direction).** 53% of all errors are on tweets whose annotators disagreed (agreement < 0.7), and accuracy is about 89% on full-agreement tweets versus about 63% on low-agreement ones (section 8).
- *"oh, ok! all good! looking forward to escaping the cold for a bit! thanks!"*: labelled negative (agreement 0.35), reads positive.
- *"@JetBlue Airways Reveals 'Bluemanity' Livery - TravelPulse <link>"*: a news headline labelled positive (0.65); neutral is defensible.
- *"Flight 4968 (N8325D) departs @MCO enroute to @NO_Airport <link>"*: a flight notice labelled negative (0.66).

**3. Mixed sentiment and "story arc" tweets (positive → negative).** The tweet describes a problem and then praises how it was solved. The problem vocabulary outweighs the happy ending, and there is no "mixed" label.
- *"That made me so mad, but then I called the bag number, and that person was helpful…"*
- *"Thx to customer service rep ALEX for his patient help in rebook a canceled flight…"* (agreement 1.00)
- *"after missing my flight and rebook 2x, I just walked onto another flight and my phone was still on the seat!!"*

**4. Neutral requests that mention problems (neutral → negative, the most common error).** Customer-service requests use words like *rebooked*, *weather*, *left* and *not* without being complaints. Neutral is the hardest class (F1 ≈ 0.65), and humans find this boundary fuzzy too.
- *"we have been rebooked due to weather, but need to change our reservation and fly on the 24th…"*
- *"I left my personal stuff on US4551 from PHL-BOS about an hour ago…"*
- *"this is for a check-in luggage. Employee told me not to include wheels in the dimensions."*

**5. Replies without their conversation (short tweets, any direction).** Many tweets answer an earlier message the model cannot see, and politeness is not the same as a positive opinion.
- *"Thank you for your response!"*: labelled neutral, predicted positive (1.00).
- *"i sure will"*: labelled negative (agreement 1.00), predicted neutral. The negativity lives in the earlier thread.
- *"any solutions?"*: labelled negative. The question implies a problem, but the words are neutral.

**6. Slang and quoted brand text (positive → neutral).** Rare slang and quoted marketing copy carry little learned signal.
- *"LMAO “@JetBlue: Our fleet's on fleek.”"*: "on fleek" and "lmao" are rare in 2015 training data.

**What would help (with more time):** use annotator agreement as a sample weight so noisy labels count less (a cheap experiment), add a *mixed* class or multi-label output, collect more sarcastic and resolved-complaint examples, include the parent tweet as context, and re-label a sample of low-agreement tweets. Contextual language models would help with sarcasm and negation, but pretrained models are excluded by the brief.
