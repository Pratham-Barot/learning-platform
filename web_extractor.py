import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ─────────────────────────────────────────────
# HELPER: Parse HTML to clean text
# ─────────────────────────────────────────────

def parse_html(html: str) -> str:
    """
    Shared BeautifulSoup parsing logic.
    Strips noise tags and returns clean readable text.
    Used by all three extraction methods.
    """

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer",
                     "header", "aside", "form", "iframe",
                     "button", "input", "select", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# METHOD 1: requests (fastest, static HTML)
# ─────────────────────────────────────────────

def fetch_with_requests(url: str) -> str | None:
    """
    Attempt 1: Standard requests session with browser-like headers.
    Works for most open-access static sites.
    Returns clean text or None if it fails.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "none",
        "Sec-Fetch-User":            "?1",
        "Cache-Control":             "max-age=0",
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=15, allow_redirects=True)

        if response.status_code == 403:
            return None

        response.raise_for_status()
        text = parse_html(response.text)

        # Return only if we got meaningful content
        if len(text) >= 200:
            return text

        return None

    except Exception:
        return None


# ─────────────────────────────────────────────
# METHOD 2: cloudscraper (Cloudflare bypass)
# ─────────────────────────────────────────────

def fetch_with_cloudscraper(url: str) -> str | None:
    """
    Attempt 2: cloudscraper bypasses Cloudflare bot detection
    and other common anti-scraping measures.
    Returns clean text or None if it fails.
    """

    try:
        import cloudscraper

        scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
            }
        )

        response = scraper.get(url, timeout=15)

        if response.status_code == 403:
            return None

        response.raise_for_status()
        text = parse_html(response.text)

        if len(text) >= 200:
            return text

        return None

    except ImportError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# METHOD 3: Playwright (JavaScript-heavy sites)
# ─────────────────────────────────────────────

def fetch_with_playwright(url: str) -> str | None:
    """
    Attempt 3: Playwright launches a real headless Chromium browser,
    fully renders JavaScript, waits for dynamic content to load,
    then extracts text. Handles React/Vue SPAs, Medium, and any
    site that requires JS to display content.
    Returns clean text or None if it fails.
    """

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )

            page = context.new_page()

            # Block images, fonts, and media to speed up loading
            page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3}",
                lambda route: route.abort()
            )

            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait a moment for JS-rendered content to appear
            page.wait_for_timeout(2000)

            html = page.content()

            browser.close()

        text = parse_html(html)

        if len(text) >= 200:
            return text

        return None

    except ImportError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# STEP 1: Main extractor with 3-method waterfall
# ─────────────────────────────────────────────

def extract_text_from_url(url: str) -> str:
    """
    Tries all three methods in order, stopping at the first success.

    Waterfall:
    1. requests       → fast, works for static HTML sites
    2. cloudscraper   → handles Cloudflare and bot-detection
    3. Playwright     → handles JavaScript-rendered content

    Raises ValueError with a helpful message if all three fail.
    """

    # Attempt 1: requests
    text = fetch_with_requests(url)
    if text:
        return text

    # Attempt 2: cloudscraper
    text = fetch_with_cloudscraper(url)
    if text:
        return text

    # Attempt 3: Playwright
    text = fetch_with_playwright(url)
    if text:
        return text

    # All three failed
    raise ValueError(
        "Could not extract content from this URL after three attempts. "
        "This may happen because:\n"
        "- The site requires a login or subscription\n"
        "- The content is behind a strict paywall\n"
        "- The page is empty or has very little text\n\n"
        "Please try a different URL such as a Wikipedia article, "
        "GeeksforGeeks, official documentation, or any open-access "
        "educational site."
    )


# ─────────────────────────────────────────────
# STEP 2: Educational content check
# ─────────────────────────────────────────────

def is_educational_content(text: str, url: str) -> tuple[bool, str]:
    """
    Summarizes the full page content first, then classifies
    whether it is educational or knowledge-based.
    Returns (is_allowed: bool, reason: str)
    """

    summary_prompt = f"""
Read the following webpage content and write a 4-5 sentence summary
describing what this page is about, what topics it covers,
and what its main purpose is.

Content:
{text[:8000]}

Summary:
"""
    summary_response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=summary_prompt,
    )
    sample_text = summary_response.text.strip()

    classify_prompt = f"""
You are a content classifier for an educational study tool.

Analyze the following summary from this URL: {url}

Determine if this content is EDUCATIONAL or KNOWLEDGE-BASED.

ALLOW:
- Educational articles, tutorials, how-to guides
- Blog posts explaining a concept or topic
- Wikipedia or encyclopedia-style content
- Research papers or academic content
- Technical documentation or explanations
- Science, history, mathematics, programming content
- Any content a student would genuinely study or learn from

DENY:
- Shopping pages or product listings
- Social media posts or profiles
- Celebrity gossip or entertainment news
- Political propaganda or opinion pieces
- Job listings or career pages
- Adult or inappropriate content
- News articles about current events (not educational)
- Login or empty pages

Return ONLY valid JSON, no markdown:
{{"allowed": true, "reason": "This is a technical tutorial explaining machine learning concepts."}}

Summary to classify:
{sample_text}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=classify_prompt,
    )

    raw = response.text.strip()

    if raw.startswith("```json"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    elif raw.startswith("```"):
        raw = raw.replace("```", "").strip()

    result = json.loads(raw)

    return result.get("allowed", False), result.get("reason", "")