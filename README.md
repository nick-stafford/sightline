# Sightline

Financial analysis of YETI, built off their SEC filings.

**Live:** https://nick-stafford.github.io/sightline/

I spent two years doing month end close by hand before I wrote production software, so reading a set of financials is the part of this I actually know. I wanted something that did the reading for me. This pulls nine years of YETI's filings straight from the SEC, runs the metrics I'd look at anyway, and tells me what's worth a second look. It also ranks YETI against seven other apparel and outdoor names so the numbers mean something instead of sitting there on their own.

The thing it caught: in FY2021 YETI's inventory grew 127% while revenue grew 29%. That gap is stock piling up ahead of demand, and it almost always ends in discounting. The next year gross margin fell 990 basis points, 57.8% down to 47.9%. The signal was sitting in the balance sheet a full year before it showed up in earnings. That's the whole argument for reading working capital instead of just staring at margins.

Python does the pulling and the cleaning, which is most of the actual work. Companies tag the same line item differently and then change tags on you, so a lot of this is just getting Nike and YETI to agree on what inventory means. SQL does the math, DuckDB because I didn't want to stand up a database for eight companies. React draws it. Groq writes the summary at the end, but only over numbers that were already calculated, because I don't want a model doing arithmetic on financials.

There's no backend. The pipeline runs on my machine, spits out JSON, and the page reads it. Loads instantly and costs nothing to host.

Run it:

```
cd pipeline
pip install -r requirements.txt
python fetch_data.py
python build.py
pytest tests/ -q

cd ../web
npm install
npm run dev
```

Everything comes from public SEC filings, as reported, nothing adjusted for one time items. Altman and Piotroski are published models, not my opinion. None of this is investment advice.
