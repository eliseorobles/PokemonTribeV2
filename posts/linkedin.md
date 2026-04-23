# LinkedIn post

> Paste this directly into the LinkedIn composer. Attach `promo-vertical-1080x1920.mp4` as the media — LinkedIn will autoplay it muted; the captions in the video carry the story.
> Character count: ~1,850 (well under LinkedIn's 3,000-char limit).

---

I bought some Pokémon cards recently. Then I had a stupid idea.

Last month Meta released **TRIBE v2** — a foundation model that predicts what a human brain does when it sees something. Feed it a video, audio, or image → predicted fMRI activation across 20,484 vertices of cortex. A digital twin of the visual system.

So I asked: **does a human brain already "know" which Pokémon cards are valuable, before reading the set or checking the rarity?**

Scraped 213 priced cards from my Collectr portfolio. Wrapped each image as a 2-second silent MP4. Ran them through TRIBE v2 on my M4 Max (~5.5 hours, two parallel workers). Aggregated the output into 14 anatomical brain regions. Ridge regression from those 14 features to log(price), with leave-one-out cross-validation. Then shuffled the price column 200 times as a control.

The result:

→ Real held-out R² = **+0.095**
→ Shuffle control mean R² = **−0.010**
→ Real model beats 100% of 200 shuffled controls
→ Strongest single region: left visual cortex, **r = +0.44** vs. log(price)

Every one of the top 10 brain regions is positively correlated. Cards that fire the visual system harder cost more.

But the most interesting part is the *disagreements.* Ranking every card by brain response and by market price, the brain flagged:

**61 cards as "the market is sleeping on this"** — visually striking, cheap.
Example: *Harpie's Pet Baby Dragon* trades at $1.14. Brain ranks it like a $76 card.

**68 cards as "the market knows something I don't"** — expensive but visually plain.
Example: a $7.72 Fire Energy. The brain ranks it like a $0.12 card. Right — scarcity, not aesthetics, is what makes it worth that.

The visual cortex is good at spotting cards designed to *look* expensive, and completely blind to cards that are expensive *despite* looking plain.

Not financial advice — Pokémon prices are set by scarcity, meta, and hype, not brains. But the visual features that signal rarity (bold art, holo foils, alt framing) are the same ones that drive neural activation. The secondary market and the visual cortex are detecting the same thing.

Full methodology, interactive site with all 213 cards, and code in the Medium post → [LINK]

Open-source pipeline. Runs on one laptop. Built on TRIBE v2 (CC BY-NC).

#MachineLearning #Neuroscience #AI #DataScience #PokemonTCG #TRIBEv2
