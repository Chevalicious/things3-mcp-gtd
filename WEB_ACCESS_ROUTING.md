# AI Agent Web Access Routing Template

Based on [@code_rams](https://x.com/code_rams) research — the optimal multi-tool setup for giving AI agents reliable web access.

## The Core Insight

> "This is never a scraping problem. It's a **routing problem**."

No single tool works everywhere. Route based on what you're dealing with.

---

## The 4-Tool Stack

| Priority | Tool | Use Case | Coverage |
|----------|------|----------|----------|
| 1st | **Cloudflare Browser Rendering API** | Articles, docs, landing pages | ~80% |
| 2nd | **Jina Reader** | Fallback when CF fails | ~15% |
| 3rd | **Firecrawl** | Bot-heavy sites, JS-heavy SPAs | ~5% |
| 4th | **OpenClaw/Playwright Browser** | Emergency: click buttons, fill forms | Rare |

---

## Setup Instructions

### 1. Cloudflare Browser Rendering API (Primary)

```bash
# Enable in Cloudflare dashboard → Browser Rendering
# Create API token with BR permissions

# Add to .env:
CLOUDFLARE_BR_TOKEN=your_token_here
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
```

**Endpoint:**
```
POST https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/markdown
```

**Pros:** Fast, clean Markdown, no local browser, free tier  
**Cons:** Some sites block it, JS-heavy SPAs may fail

---

### 2. Jina Reader (Zero-Config Fallback)

```bash
# No setup needed for basic use
# Just prepend r.jina.ai/ to any URL
```

**Usage:**
```
https://r.jina.ai/https://example.com/article
```

**Optional API key for higher limits:**
- Get free key at: https://jina.ai/reader

**Pros:** Zero setup, just prepend URL, free 10M tokens  
**Cons:** Slower than CF, rate limits without API key

---

### 3. Firecrawl (Hard Sites)

```bash
# Sign up at firecrawl.dev (500 free credits, no card)

# Add to .env:
FIRECRAWL_API_KEY=your_key_here
```

**Endpoint:**
```
POST https://api.firecrawl.dev/v1/scrape
```

**Pros:** Handles bot detection, anti-bot measures, JS rendering  
**Cons:** Credits run out, paid for scale, slower for simple pages

---

### 4. OpenClaw/Playwright Browser (Emergency)

```python
# Built into OpenClaw
# Use when you NEED to:
# - Click buttons
# - Fill forms
# - Interact with dynamic elements
```

**Pros:** Handles anything, full browser control  
**Cons:** Slow, needs Chrome running, fills context window, disconnects on sleep

---

## Routing Logic

```python
def fetch_url(url):
    """Smart routing based on site type and previous failures."""
    
    # Try Cloudflare BR first (80% of cases)
    result = try_cloudflare_br(url)
    if result.success:
        return result.content
    
    # Fallback to Jina Reader (15% more)
    result = try_jina_reader(url)
    if result.success:
        return result.content
    
    # Hard sites: Firecrawl (5%)
    if is_bot_heavy_site(url) or result.error == "bot_detected":
        result = try_firecrawl(url)
        if result.success:
            return result.content
    
    # Last resort: OpenClaw browser
    return try_openclaw_browser(url)
```

---

## Decision Tree

```
Is it a normal article/doc/landing page?
├── YES → Cloudflare BR API
│   └── Fails? → Jina Reader
│       └── Fails? → Check if bot-heavy site
│
Is it JS-heavy with bot detection/login walls?
├── YES → Firecrawl
│   └── Fails? → OpenClaw browser (emergency)
│
Need to click/fill/interact?
└── YES → OpenClaw browser (only option)
```

---

## Environment Variables

```bash
# .env file
CLOUDFLARE_BR_TOKEN=xxx
CLOUDFLARE_ACCOUNT_ID=xxx
FIRECRAWL_API_KEY=xxx
# Jina Reader: no key needed for basic use
```

---

## What NOT To Do

❌ Don't rely on a local browser for 24/7 agent access  
❌ Don't use one tool for everything  
❌ Don't dump full HTML into context (extract what you need)  
❌ Don't wait until production to build routing logic  

---

## Credits

Based on research by [Ramya Chinnadurai (@code_rams)](https://x.com/code_rams)  
Original post: https://x.com/code_rams/status/2032120036593193323

---

## Integration with This Project

Add web access routing to your agent:

1. Copy this template to your project
2. Add the 3 API keys to your `.env`
3. Implement the routing logic
4. Test with various site types
5. Monitor which tools succeed/fail and adjust routing

---

*Template version: 1.0*  
*Last updated: 2026-03-12*
