"""Shared reference data: hubs, categories, statuses."""

HUBS = {
    "Nairobi": {"tz": "Africa/Nairobi", "colour": "nairobi"},
    "Addis Ababa": {"tz": "Africa/Addis_Ababa", "colour": "addis"},
    "Atlanta": {"tz": "America/New_York", "colour": "atlanta"},
    "Berlin": {"tz": "Europe/Berlin", "colour": "berlin"},
}

# Time zone most clients book from; every slot is also shown in this zone.
CLIENT_TZ = "Africa/Nairobi"

CATEGORIES = {
    "finance": "Finance & fundraising",
    "legal": "Legal & compliance",
    "marketing": "Marketing & sales",
    "trade": "Export & cross-border trade",
    "tech": "Technology & digital",
    "operations": "Operations & supply chain",
}

# Words a client might use for each category. Used by the matcher to guess a
# category from free text and to score experts.
CATEGORY_KEYWORDS = {
    "finance": {"funding", "investor", "investors", "loan", "loans", "cash", "cashflow",
                "accounts", "bookkeeping", "tax", "pitch", "valuation", "grant", "capital"},
    "legal": {"contract", "contracts", "registration", "register", "license", "licence",
              "compliance", "kra", "trademark", "ip", "lawyer", "legal", "agreement"},
    "marketing": {"customers", "sales", "brand", "branding", "social", "instagram",
                  "tiktok", "marketing", "ads", "pricing", "leads", "growth"},
    "trade": {"export", "exports", "import", "agoa", "afcfta", "customs", "shipping",
              "logistics", "us", "europe", "eu", "market", "abroad", "berlin", "atlanta"},
    "tech": {"website", "app", "software", "digital", "ecommerce", "mpesa", "payments",
             "data", "system", "automation", "online", "tech"},
    "operations": {"inventory", "supply", "suppliers", "production", "hiring", "staff",
                   "processes", "operations", "warehouse", "quality", "manufacturing"},
}

BOOKING_STATUSES = ["pending", "confirmed", "completed", "cancelled"]
REQUEST_STATUSES = ["new", "matched", "closed"]
