"""Demo data. All people below are fictional placeholders."""
import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .constants import HUBS

EXPERTS = [
    {
        "slug": "wanjiku-kamau", "name": "Wanjiku Kamau", "hub": "Nairobi",
        "title": "SME finance advisor", "category": "finance",
        "skills": "cash flow, bookkeeping, loan applications, KRA tax",
        "bio": "Spent nine years as a credit officer before switching sides. Helps "
               "small businesses get their books in order and put together loan "
               "applications that banks and SACCOs approve.",
        "languages": "English, Swahili, Kikuyu", "years": 11, "rate": 4500,
        "rating": 4.9, "sessions": 132,
    },
    {
        "slug": "otieno-odhiambo", "name": "Otieno Odhiambo", "hub": "Nairobi",
        "title": "Startup fundraising coach", "category": "finance",
        "skills": "pitch decks, investors, valuation, grants",
        "bio": "Has prepared over 40 founders for angel and seed rounds. Reviews your "
               "pitch, financial model and investor list, and runs practice pitches.",
        "languages": "English, Swahili, Luo", "years": 8, "rate": 6000,
        "rating": 4.8, "sessions": 87,
    },
    {
        "slug": "amina-hassan", "name": "Amina Hassan", "hub": "Nairobi",
        "title": "Business lawyer", "category": "legal",
        "skills": "company registration, contracts, trademarks, compliance",
        "bio": "Advocate of the High Court focused on small companies. Registers "
               "businesses, drafts and reviews contracts, and handles trademark filings.",
        "languages": "English, Swahili", "years": 10, "rate": 7000,
        "rating": 4.9, "sessions": 98,
    },
    {
        "slug": "brian-mutua", "name": "Brian Mutua", "hub": "Nairobi",
        "title": "Digital marketing strategist", "category": "marketing",
        "skills": "social media, Instagram, TikTok, ads, branding",
        "bio": "Grew online sales for retail and food brands in Nairobi. Builds a "
               "simple content plan and ad budget you can run without an agency.",
        "languages": "English, Swahili", "years": 6, "rate": 3500,
        "rating": 4.7, "sessions": 154,
    },
    {
        "slug": "faith-njeri", "name": "Faith Njeri", "hub": "Nairobi",
        "title": "E-commerce and payments engineer", "category": "tech",
        "skills": "websites, e-commerce, M-Pesa integration, automation",
        "bio": "Builds online shops and payment flows for small businesses. Can tell "
               "you in one session what to build, what to buy and what it will cost.",
        "languages": "English, Swahili", "years": 7, "rate": 5000,
        "rating": 4.8, "sessions": 76,
    },
    {
        "slug": "daniel-kiprop", "name": "Daniel Kiprop", "hub": "Nairobi",
        "title": "Operations and supply chain advisor", "category": "operations",
        "skills": "inventory, suppliers, production, quality",
        "bio": "Former plant manager in agro-processing. Fixes stock-outs, supplier "
               "delays and production bottlenecks for growing manufacturers.",
        "languages": "English, Swahili, Kalenjin", "years": 14, "rate": 5500,
        "rating": 4.6, "sessions": 61,
    },
    {
        "slug": "selam-tesfaye", "name": "Selam Tesfaye", "hub": "Addis Ababa",
        "title": "Regional trade specialist", "category": "trade",
        "skills": "AfCFTA, customs, export, East Africa markets",
        "bio": "Advises firms moving goods between Kenya and Ethiopia. Knows the "
               "customs paperwork, AfCFTA rules of origin and local distributors.",
        "languages": "English, Amharic", "years": 9, "rate": 5000,
        "rating": 4.8, "sessions": 54,
    },
    {
        "slug": "yonas-bekele", "name": "Yonas Bekele", "hub": "Addis Ababa",
        "title": "Manufacturing operations consultant", "category": "operations",
        "skills": "manufacturing, processes, hiring, warehouse",
        "bio": "Set up production lines for textile and leather exporters in Addis. "
               "Helps factories scale output without losing quality.",
        "languages": "English, Amharic", "years": 12, "rate": 4500,
        "rating": 4.7, "sessions": 39,
    },
    {
        "slug": "monica-reed", "name": "Monica Reed", "hub": "Atlanta",
        "title": "US market entry advisor", "category": "trade",
        "skills": "export to US, AGOA, distribution, pricing",
        "bio": "Helps African brands get onto US shelves. Covers AGOA eligibility, "
               "finding distributors and pricing for American buyers.",
        "languages": "English", "years": 15, "rate": 9000,
        "rating": 4.9, "sessions": 71,
    },
    {
        "slug": "marcus-hill", "name": "Marcus Hill", "hub": "Atlanta",
        "title": "Investor readiness coach", "category": "finance",
        "skills": "US investors, due diligence, fundraising, capital",
        "bio": "Angel investor and former bank analyst. Prepares founders for "
               "conversations with US investors and diaspora funds.",
        "languages": "English", "years": 13, "rate": 9500,
        "rating": 4.7, "sessions": 45,
    },
    {
        "slug": "lena-hoffmann", "name": "Lena Hoffmann", "hub": "Berlin",
        "title": "EU market and compliance advisor", "category": "legal",
        "skills": "EU compliance, product standards, export to Europe, GDPR",
        "bio": "Guides exporters through EU product rules, labelling and data "
               "protection so shipments clear customs the first time.",
        "languages": "English, German", "years": 10, "rate": 9000,
        "rating": 4.8, "sessions": 50,
    },
    {
        "slug": "jonas-weber", "name": "Jonas Weber", "hub": "Berlin",
        "title": "Product and software lead", "category": "tech",
        "skills": "software, apps, data, product strategy",
        "bio": "Has shipped products at two Berlin startups. Reviews your app idea or "
               "existing system and turns it into a realistic build plan.",
        "languages": "English, German", "years": 9, "rate": 8500,
        "rating": 4.6, "sessions": 33,
    },
]

SLOT_HOURS = (time(10, 0), time(14, 0), time(16, 0))
BUSINESS_DAYS = 10


def upcoming_slots(hub: str, now: datetime, rng: random.Random) -> list[str]:
    """Return UTC ISO timestamps for open slots over the next business days."""
    tz = ZoneInfo(HUBS[hub]["tz"])
    local_today = now.astimezone(tz).date()
    slots, day = [], local_today
    while len(slots) < BUSINESS_DAYS * len(SLOT_HOURS):
        day += timedelta(days=1)
        if day.weekday() >= 5:
            continue
        for hour in SLOT_HOURS:
            slots.append(datetime.combine(day, hour, tzinfo=tz))
    # Not every expert is free every slot.
    chosen = [s for s in slots if rng.random() < 0.55]
    return [s.astimezone(ZoneInfo("UTC")).isoformat() for s in chosen]


def seed(db, now: datetime | None = None) -> int:
    now = now or datetime.now(ZoneInfo("UTC"))
    rng = random.Random(42)
    for e in EXPERTS:
        cur = db.execute(
            """INSERT INTO experts (slug, name, title, hub, category, skills, bio,
                   languages, years_experience, rate, currency, rating, sessions_done)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'KES', ?, ?)""",
            (e["slug"], e["name"], e["title"], e["hub"], e["category"], e["skills"],
             e["bio"], e["languages"], e["years"], e["rate"], e["rating"], e["sessions"]),
        )
        db.executemany(
            "INSERT INTO availability (expert_id, start_at) VALUES (?, ?)",
            [(cur.lastrowid, s) for s in upcoming_slots(e["hub"], now, rng)],
        )
    db.commit()
    return len(EXPERTS)
