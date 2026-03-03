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
import time
import requests
from datetime import datetime

# ── API KEY ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ── NEWS FEEDS ────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    # Finnish sources
    "yle_uutiset":      "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET",
    "yle_tekno":        "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837",
    "yle_politiikka":   "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-38033",
    "hs_paakirj":       "https://www.hs.fi/rss/paakirjoitukset.xml",
    "mtv_uutiset":      "https://www.mtvuutiset.fi/rss/uutiset.rss",

    # Finnish government & institutions
    "valtioneuvosto":   "https://valtioneuvosto.fi/rss/tiedotteet.rss",
    "eduskunta":        "https://www.eduskunta.fi/FI/tiedotteet/Sivut/RSS.aspx",
    "oikeusministerio": "https://oikeusministerio.fi/rss/tiedotteet.rss",
    "traficom":         "https://www.traficom.fi/fi/rss/uutiset",

    # EU policy & governance
    "politico_eu":      "https://www.politico.eu/feed/",
    "euractiv_digital": "https://www.euractiv.com/sections/digital/feed/",
    "euractiv_ai":      "https://www.euractiv.com/sections/digital/artificial-intelligence/feed/",
    "eu_commission":    "https://ec.europa.eu/newsroom/dae/rss.cfm",
    "europarl":         "https://www.europarl.europa.eu/rss/doc/top-stories/en.xml",
    "edri":             "https://edri.org/feed/",

    # Global news
    "reuters_tech":     "https://feeds.reuters.com/reuters/technologyNews",
    "guardian_tech":    "https://www.theguardian.com/technology/rss",
    "guardian_media":   "https://www.theguardian.com/media/rss",
    "bbc_tech":         "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "ap_tech":          "https://feeds.apnews.com/rss/apf-technology",

    # AI-specific
    "mit_tech":         "https://www.technologyreview.com/feed/",
    "wired_ai":         "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
    "aisnakeoil":       "https://www.aisnakeoil.com/feed",
    "import_ai":        "https://importai.substack.com/feed",

    # Democracy & governance research
    "freedom_house":    "https://freedomhouse.org/rss.xml",
    "v_dem":            "https://www.v-dem.net/feed/",
    "carnegie_dem":     "https://carnegieendowment.org/topics/democracy/rss",
    "brookings_gov":    "https://www.brookings.edu/topic/governance-studies/feed/",
    "oxpol":            "https://blog.politics.ox.ac.uk/feed/",

    # Disinformation & information environment
    "euvsdisinfo":      "https://euvsdisinfo.eu/feed/",
    "firstdraft":       "https://firstdraftnews.org/feed/",
    "poynter":          "https://www.poynter.org/feed/",

    # ── NEW: Radical signal sources ──────────────────────────────────────────

    # Crisis & conflict early warning
    "crisis_group":     "https://www.crisisgroup.org/rss.xml",
    "civicus":          "https://www.civicus.org/index.php/feed",
    "international_idea": "https://www.idea.int/rss.xml",

    # Investigative / backsliding monitoring
    "occrp":            "https://www.occrp.org/en/rss",
    "vsquare":          "https://vsquare.org/feed/",

    # Governance innovation & futures
    "nesta":            "https://www.nesta.org.uk/feed/",
    "govinsider":       "https://govinsider.asia/feed/",
    "apolitical":       "https://apolitical.co/feed",

    # Academic / speculative
    "ssrn_polisci":     "https://papers.ssrn.com/rss/SSRN_GetFile.cfm?abstractid=&ContentType=topTen&network=Political+Science+Network",
    "lawfare":          "https://www.lawfaremedia.org/feed",
    "verfassungsblog":  "https://verfassungsblog.de/feed/",  # Constitutional law & democracy

    # GDELT targeted queries
    "gdelt_ai_dem":     "https://api.gdeltproject.org/api/v2/doc/doc?query=AI+democracy&mode=artlist&format=rss",
    "gdelt_ai_elect":   "https://api.gdeltproject.org/api/v2/doc/doc?query=artificial+intelligence+elections&mode=artlist&format=rss",
    "gdelt_disinfo":    "https://api.gdeltproject.org/api/v2/doc/doc?query=disinformation+AI+politics&mode=artlist&format=rss",
    "gdelt_autocracy":  "https://api.gdeltproject.org/api/v2/doc/doc?query=AI+autocracy+surveillance+democracy&mode=artlist&format=rss",
    "gdelt_new_dem":    "https://api.gdeltproject.org/api/v2/doc/doc?query=AI+deliberative+democracy+participation+new&mode=artlist&format=rss",
}

# ── SETTINGS ──────────────────────────────────────────────────────────────────
ARTICLES_PER_FEED   = 20
OUTPUT_FILE         = "signals.json"
MODEL               = "claude-sonnet-4-6"
MAX_TOKENS          = 700
FEED_TIMEOUT        = 15
API_RETRIES         = 3
RETRY_BACKOFF       = 5

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

DOMAIN OPTIONS:
- epistemic: truth, information environment, media
- procedural: elections, voting, formal democratic processes
- institutional: governance bodies, regulation, rule of law
- participatory: civic engagement, deliberation, public input
- power: concentration or distribution of political power
- multiple: clearly spans several domains

SIGNAL STRENGTH: weak / moderate / strong
SIGNAL TYPE: emerging / accelerating / plateauing / reversing

IMPACT AND LIKELIHOOD ASSESSMENT:
Rate the signal on two independent dimensions using a 1–5 scale:

impact (1–5): How consequential would this signal be for democracy if the trend it
represents fully developed? Score based on systemic significance, not current scale.
  1 = marginal, affects narrow context
  2 = moderate, affects one domain or country
  3 = significant, affects multiple domains or the European level
  4 = major, threatens or transforms core democratic architecture
  5 = civilizational, fundamentally alters democratic governance globally

likelihood (1–5): How probable is this trajectory materializing within 5–10 years,
given current evidence and structural conditions?
  1 = very unlikely, speculative or fringe
  2 = possible but requires unlikely conditions
  3 = plausible given current trajectory
  4 = probable, strong supporting trends
  5 = near-certain, already in motion

structural_break (true/false): Does this signal suggest a DISCONTINUOUS rupture —
something that would NOT be predicted by extrapolating current trends? Mark true for:
  - paradigm shifts in how AI relates to democratic governance
  - sudden collapses or emergences that bypass incremental change
  - signals that would constitute a qualitative break, not just acceleration
  Mark false for signals that represent gradual continuation of existing dynamics.

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
  "impact": 1-5,
  "likelihood": 1-5,
  "structural_break": true or false,
  "confidence": 0.0 to 1.0,
  "rationale": "2-3 sentences on the primary reading",
  "secondary_rationale": "1-2 sentences on secondary dimensions, or empty string if none",
  "finnish_relevance": true or false
}}
"""

# ── LOAD EXISTING SIGNALS ─────────────────────────────────────────────────────
def load_existing():
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print("  ⚠ signals.json is not a list — starting fresh")
            return []
        valid = [s for s in data if isinstance(s, dict) and isinstance(s.get("url"), str) and s["url"]]
        if len(valid) < len(data):
            print(f"  ⚠ Dropped {len(data)-len(valid)} malformed entries")
        return valid
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"  ⚠ signals.json corrupt ({e}) — starting fresh")
        return []

# ── FETCH ARTICLES ────────────────────────────────────────────────────────────
def fetch_articles(existing_urls: set) -> list:
    articles = []
    for source, url in RSS_FEEDS.items():
        try:
            response = requests.get(url, timeout=FEED_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            new_count = 0
            for entry in feed.entries[:ARTICLES_PER_FEED]:
                article_url = entry.get("link", "").strip()
                if not article_url or article_url in existing_urls:
                    continue
                articles.append({
                    "source":    source,
                    "title":     entry.get("title", "").strip()[:300],
                    "summary":   entry.get("summary", "")[:800].strip(),
                    "url":       article_url,
                    "published": entry.get("published", ""),
                })
                new_count += 1
            print(f"  ✓ {source}: {new_count} new articles")
        except requests.Timeout:
            print(f"  ✗ {source}: timed out after {FEED_TIMEOUT}s")
        except Exception as e:
            print(f"  ✗ {source}: {e}")
    return articles

# ── CLASSIFY ONE ARTICLE ──────────────────────────────────────────────────────
def classify(client, article) -> dict:
    prompt = PROMPT.format(
        title=article["title"],
        source=article["source"],
        summary=article["summary"],
    )
    delay = RETRY_BACKOFF
    for attempt in range(1, API_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )
            raw = response.content[0].text.strip()
            result = json.loads(raw)
            result.setdefault("relevant", False)
            result.setdefault("primary_category", "AMBIGUOUS")
            result.setdefault("secondary_categories", [])
            result.setdefault("impact", 1)
            result.setdefault("likelihood", 1)
            result.setdefault("structural_break", False)
            result.setdefault("confidence", 0.0)
            result.setdefault("rationale", "")
            result.setdefault("secondary_rationale", "")
            result.setdefault("finnish_relevance", False)
            # Clamp impact/likelihood to valid range
            result["impact"]     = max(1, min(5, int(result["impact"])))
            result["likelihood"] = max(1, min(5, int(result["likelihood"])))
            return {**article, **result, "scanned_at": datetime.utcnow().isoformat()}
        except json.JSONDecodeError:
            print(f"    JSON parse error (attempt {attempt}/{API_RETRIES})")
        except Exception as e:
            print(f"    API error (attempt {attempt}/{API_RETRIES}): {e}")
        if attempt < API_RETRIES:
            time.sleep(delay)
            delay *= 2
    return {**article, "relevant": False, "error": "failed_after_retries",
            "scanned_at": datetime.utcnow().isoformat()}

# ── SAVE RESULTS ──────────────────────────────────────────────────────────────
def save(existing: list, new_signals: list):
    combined = existing + new_signals
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {len(new_signals)} new signals added. Total in database: {len(combined)}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("── Loading existing signals ─────────────────────────")
    existing = load_existing()
    existing_urls = {s["url"] for s in existing}
    print(f"  {len(existing)} existing signals, {len(existing_urls)} known URLs")

    print("\n── Fetching articles ────────────────────────────────")
    articles = fetch_articles(existing_urls)
    print(f"\n{len(articles)} new articles to classify")

    if not articles:
        print("Nothing new to classify.")
        return

    print("\n── Classifying ──────────────────────────────────────")
    new_signals = []
    for i, article in enumerate(articles, 1):
        print(f"  [{i}/{len(articles)}] {article['title'][:55]}...")
        result = classify(client, article)
        if result.get("relevant") is True:
            new_signals.append(result)

    print(f"\n{len(new_signals)} relevant signals out of {len(articles)} articles")
    save(existing, new_signals)

if __name__ == "__main__":
    main()
