"""
AI-Democracy Anticipatory Signal Scanner
Scenarios: Vahvistuu / Uusi demokratia / Heikentyy / Romahtaa
------------------------------------------------------------------
Install dependencies: pip install anthropic feedparser requests
Run manually:         python scanner.py
"""

import anthropic
import feedparser
import json
import os
from datetime import datetime

# ── API KEY ───────────────────────────────────────────────────────────────────
# Never paste your key here. Set it as an environment variable:
#   Mac/Linux: export ANTHROPIC_API_KEY="sk-ant-..."
#   GitHub:    set as a repository secret (see setup guide)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ── NEWS FEEDS ────────────────────────────────────────────────────────────────
# Add or remove feeds freely. Format: "name": "rss_url"

RSS_FEEDS = {

    # ── FINNISH SOURCES ───────────────────────────────────────────────────────
    "yle_uutiset":      "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET",
    "yle_tekno":        "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837",
    "yle_politiikka":   "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-38033",
    "hs_paakirj":       "https://www.hs.fi/rss/paakirjoitukset.xml",
    "mtv_uutiset":      "https://www.mtvuutiset.fi/rss/uutiset.rss",

    # ── FINNISH GOVERNMENT & INSTITUTIONS ─────────────────────────────────────
    "valtioneuvosto":   "https://valtioneuvosto.fi/rss/tiedotteet.rss",
    "eduskunta":        "https://www.eduskunta.fi/FI/tiedotteet/Sivut/RSS.aspx",
    "oikeusministerio": "https://oikeusministerio.fi/rss/tiedotteet.rss",
    "traficom":         "https://www.traficom.fi/fi/rss/uutiset",

    # ── EU POLICY & GOVERNANCE ────────────────────────────────────────────────
    "politico_eu":      "https://www.politico.eu/feed/",
    "euractiv_digital": "https://www.euractiv.com/sections/digital/feed/",
    "euractiv_ai":      "https://www.euractiv.com/sections/digital/artificial-intelligence/feed/",
    "eu_commission":    "https://ec.europa.eu/newsroom/dae/rss.cfm",
    "europarl":         "https://www.europarl.europa.eu/rss/doc/top-stories/en.xml",
    "edri":             "https://edri.org/feed/",           # European digital rights NGO

    # ── GLOBAL NEWS ───────────────────────────────────────────────────────────
    "reuters_tech":     "https://feeds.reuters.com/reuters/technologyNews",
    "guardian_tech":    "https://www.theguardian.com/technology/rss",
    "guardian_media":   "https://www.theguardian.com/media/rss",
    "bbc_tech":         "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "ap_tech":          "https://feeds.apnews.com/rss/apf-technology",

    # ── AI-SPECIFIC ───────────────────────────────────────────────────────────
    "mit_tech":         "https://www.technologyreview.com/feed/",
    "wired_ai":         "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
    "aisnakeoil":       "https://www.aisnakeoil.com/feed",  # AI policy critique
    "import_ai":        "https://importai.substack.com/feed",

    # ── DEMOCRACY & GOVERNANCE RESEARCH ──────────────────────────────────────
    "freedom_house":    "https://freedomhouse.org/rss.xml",
    "v_dem":            "https://www.v-dem.net/feed/",      # Varieties of Democracy institute
    "carnegie_dem":     "https://carnegieendowment.org/topics/democracy/rss",
    "brookings_gov":    "https://www.brookings.edu/topic/governance-studies/feed/",
    "oxpol":            "https://blog.politics.ox.ac.uk/feed/",  # Oxford Politics blog

    # ── DISINFORMATION & INFORMATION ENVIRONMENT ──────────────────────────────
    "euvsdisinfo":      "https://euvsdisinfo.eu/feed/",     # EU East StratCom task force
    "firstdraft":       "https://firstdraftnews.org/feed/",
    "poynter":          "https://www.poynter.org/feed/",

    # ── GDELT TARGETED QUERIES ────────────────────────────────────────────────
    "gdelt_ai_dem":     "https://api.gdeltproject.org/api/v2/doc/doc?query=AI+democracy&mode=artlist&format=rss",
    "gdelt_ai_elect":   "https://api.gdeltproject.org/api/v2/doc/doc?query=artificial+intelligence+elections&mode=artlist&format=rss",
    "gdelt_disinfo":    "https://api.gdeltproject.org/api/v2/doc/doc?query=disinformation+AI+politics&mode=artlist&format=rss",
}

# ── SETTINGS ──────────────────────────────────────────────────────────────────
ARTICLES_PER_FEED   = 20   # how many articles to pull per feed per run
OUTPUT_FILE         = "signals.json"
MODEL               = "claude-sonnet-4-6"
MAX_TOKENS          = 600

# ── CLASSIFICATION PROMPT ─────────────────────────────────────────────────────
PROMPT = """
You are an anticipatory intelligence analyst specializing in AI's impact on democracy.

Assess whether this news item is a relevant anticipatory signal about how AI is affecting
democratic life, institutions, participation, or the information environment.

If relevant, classify it using these four scenarios:

1. STRENGTHENS — AI reinforces and extends existing democratic institutions, participation,
   rule of law, or civic capacity. Current democratic structures adapt and remain legitimate.
   Examples: AI improving electoral administration, expanding civic participation,
   strengthening oversight of technology, transparent public sector AI deployment.

2. NEW_DEMOCRACY — AI enables genuinely new democratic forms not reducible to existing
   institutions. New modes of collective decision-making, legitimacy, or sovereignty emerge.
   Examples: AI-facilitated deliberative assemblies at scale, algorithmic commons governance,
   post-representative participation models, citizen co-design of public AI infrastructure.

3. WEAKENS — AI gradually narrows civic space, concentrates power, erodes rights, or
   hollows out democratic procedures while maintaining democratic facades.
   Examples: algorithmic political manipulation, surveillance creep, technocratic displacement
   of deliberation, platform monopolization of political discourse, AI-enabled gerrymandering.

4. COLLAPSE — AI contributes to acute, visible breakdown of democratic governance,
   legitimacy, or institutions. Crisis-level events rather than gradual erosion.
   Examples: election infrastructure failure, AI disinformation causing institutional
   delegitimization, authoritarian crackdowns enabled by AI, rapid power concentration
   bypassing constitutional limits.

CLASSIFICATION RULES:
- A signal may point toward multiple scenarios simultaneously.
- Assign a PRIMARY category (the dominant reading).
- Add SECONDARY categories where the signal also has meaningful resonance.
- Use AMBIGUOUS as primary only when no scenario clearly dominates and the item is
  genuinely relevant. Do not use it to avoid a difficult judgment.
- Confidence reflects clarity of mapping, not relevance.

DOMAIN OPTIONS:
- epistemic: truth, information environment, media
- procedural: elections, voting, formal democratic processes
- institutional: governance bodies, regulation, rule of law
- participatory: civic engagement, deliberation, public input
- power: concentration or distribution of political power
- multiple: clearly spans several domains

SIGNAL STRENGTH:
- weak: early or isolated indicator
- moderate: clear but not yet established trend
- strong: documented, recurring, or systemic pattern

SIGNAL TYPE:
- emerging: new and just appearing
- accelerating: growing faster
- plateauing: levelling off
- reversing: previously strong signal now weakening

News item:
TITLE: {title}
SOURCE: {source}
SUMMARY: {summary}

Respond ONLY with valid JSON — no preamble, no markdown backticks:
{{
  "relevant": true or false,
  "primary_category": "STRENGTHENS|NEW_DEMOCRACY|WEAKENS|COLLAPSE|AMBIGUOUS",
  "secondary_categories": [],
  "signal_strength": "weak|moderate|strong",
  "signal_type": "emerging|accelerating|plateauing|reversing",
  "domain": "epistemic|procedural|institutional|participatory|power|multiple",
  "confidence": 0.0 to 1.0,
  "rationale": "2-3 sentences on the primary reading",
  "secondary_rationale": "1-2 sentences on secondary dimensions, or empty string if none",
  "finnish_relevance": true or false
}}
"""

# ── FETCH ARTICLES ────────────────────────────────────────────────────────────
def fetch_articles():
    articles = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:ARTICLES_PER_FEED]:
                articles.append({
                    "source":    source,
                    "title":     entry.get("title", "").strip(),
                    "summary":   entry.get("summary", "")[:800].strip(),
                    "url":       entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
            print(f"  ✓ {source}: {min(len(feed.entries), ARTICLES_PER_FEED)} articles")
        except Exception as e:
            print(f"  ✗ {source}: {e}")
    return articles

# ── CLASSIFY ONE ARTICLE ──────────────────────────────────────────────────────
def classify(client, article):
    prompt = PROMPT.format(
        title=article["title"],
        source=article["source"],
        summary=article["summary"],
    )
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
        return {**article, **result, "scanned_at": datetime.utcnow().isoformat()}
    except json.JSONDecodeError as e:
        print(f"  JSON parse error for '{article['title'][:40]}...': {e}")
        return {**article, "relevant": False, "error": "json_parse_error", "scanned_at": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"  API error for '{article['title'][:40]}...': {e}")
        return {**article, "relevant": False, "error": str(e), "scanned_at": datetime.utcnow().isoformat()}

# ── SAVE RESULTS ──────────────────────────────────────────────────────────────
def save(signals):
    try:
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    existing_urls = {s["url"] for s in existing}
    new_signals = [s for s in signals if s["url"] not in existing_urls]
    combined = existing + new_signals

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(new_signals)} new signals added. Total in database: {len(combined)}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("── Fetching articles ────────────────────────────────")
    articles = fetch_articles()
    print(f"\n{len(articles)} articles fetched total")

    print("\n── Classifying ──────────────────────────────────────")
    classified = []
    for i, article in enumerate(articles, 1):
        print(f"  [{i}/{len(articles)}] {article['title'][:55]}...")
        classified.append(classify(client, article))

    signals = [c for c in classified if c.get("relevant") is True]
    print(f"\n{len(signals)} relevant signals identified out of {len(articles)} articles")

    save(signals)

if __name__ == "__main__":
    main()
