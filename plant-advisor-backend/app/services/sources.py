from typing import Dict, List, Any

TRUSTED_YOUTUBE_CHANNELS = {
    "Epic Gardening": "UC16rqiVCSYOov2-MZ8OLyZQ",
    "Charles Dowding": "UCB1J6siDdmhwah7q0O2WJBg",
    "Roots and Refuge Farm": "UCOMrekmhO52h48G8Q1WN9mg",
    "Self Sufficient Me": "UCJZTjBlrnDHYmf0F-eYXA3Q",
    "Becky's Homestead": "UCfz0O9f_Ysivwz1CzEn4Wdw",
    "MIgardener": "UC1rUbdCnwrCqb5ddh7gz_dg",
    "Swedish Homestead": "UCVhv5O5_pCtHDZGEHR5_xow",
    "Gardening with Leon": "UCnKT8LgNSW5Yt_l4EQZbJxw"
}

TRUSTED_WEBSITE_DOMAINS = [
    "gardeningknowhow.com", "extension.org", "almanac.com",
    "growveg.com", "seedsavers.org", "motherearthnews.com",
    "organicgardening.com", "finegardening.com", "bhg.com",
    "gardenersworld.com", "rhs.org.uk", "sunset.com",
    "burpee.com", "johnnyseeds.com", "southernexposure.com"
]

TRUSTED_URL_PATTERNS = {
    "gardeningknowhow.com": ["/", "/growing/", "/care/", "/problems/"],
    "extension.org": ["/", "/gardening/", "/farming/", "/crops/"],
    "almanac.com": ["/", "/gardening/", "/planting-calendar/"],
    "motherearthnews.com": ["/", "/organic-gardening/", "/sustainable-farming/"]
}

PLANT_DISCOVERY_PATTERNS = [
    "how to grow", "plant care", "gardening", "cultivation",
    "growing tips", "plant guide", "farming", "agriculture",
    "organic gardening", "permaculture", "hydroponics", "greenhouse growing",
    "container gardening", "urban farming", "vertical gardening", "aquaponics",
    "companion planting", "crop rotation", "soil preparation", "composting",
    "pest management", "plant diseases", "irrigation", "plant nutrition"
]

PLANT_IDENTIFICATION_KEYWORDS = {
    "vegetables": [
        "tomato", "lettuce", "carrot", "pepper", "onion", "garlic", "cucumber",
        "potato", "broccoli", "spinach", "kale", "cabbage", "beet", "radish",
        "turnip", "parsnip", "celery", "asparagus", "artichoke", "leek",
        "brussels sprouts", "cauliflower", "chard", "arugula", "endive"
    ],
    "fruits": [
        "apple", "orange", "strawberry", "blueberry", "grape", "banana",
        "lemon", "peach", "cherry", "pear", "plum", "watermelon", "cantaloupe",
        "honeydew", "mango", "pineapple", "avocado", "fig", "pomegranate",
        "kiwi", "passion fruit", "guava", "papaya", "coconut"
    ],
    "herbs": [
        "basil", "oregano", "thyme", "rosemary", "sage", "mint", "parsley",
        "cilantro", "dill", "chives", "lavender", "chamomile", "tarragon",
        "marjoram", "fennel", "coriander", "bay leaves", "chervil"
    ],
    "flowers": [
        "rose", "tulip", "sunflower", "marigold", "petunia", "lily", "dahlia",
        "orchid", "zinnia", "cosmos", "pansy", "iris", "daffodil", "hyacinth",
        "begonia", "impatiens", "geranium", "carnation", "chrysanthemum"
    ],
    "trees": [
        "oak", "maple", "pine", "cedar", "birch", "willow", "elm", "ash",
        "cherry tree", "apple tree", "pear tree", "plum tree", "fig tree",
        "citrus tree", "avocado tree", "olive tree"
    ],
    "houseplants": [
        "pothos", "monstera", "snake plant", "spider plant", "peace lily",
        "rubber plant", "fiddle leaf fig", "philodendron", "succulent",
        "cactus", "aloe vera", "jade plant", "boston fern"
    ]
}

CONTENT_QUALITY_INDICATORS = {
    "high_quality_indicators": [
        "step by step", "detailed guide", "expert advice", "comprehensive",
        "tutorial", "how-to", "tips", "best practices", "organic",
        "sustainable", "proven methods", "professional advice",
        "research-based", "scientific", "university extension"
    ],
    "low_quality_indicators": [
        "click here", "buy now", "limited time", "spam", "advertisement",
        "affiliate link", "sponsored", "promotion", "discount code"
    ]
}

CONTENT_EXTRACTION_SELECTORS = {
    'gardeningknowhow.com': {
        'title': ['h1.entry-title', 'h1'],
        'content': ['.entry-content', 'article', '.post-content']
    },
    'extension.org': {
        'title': ['h1', '.page-title', '.title'],
        'content': ['.field-item', '.content', 'main', '.page-content']
    },
    'almanac.com': {
        'title': ['h1', '.post-title'],
        'content': ['.post-content', '.entry-content', 'article']
    },
    'motherearthnews.com': {
        'title': ['h1.article-title', 'h1'],
        'content': ['.article-body', '.content', 'article']
    },
    'seedsavers.org': {
        'title': ['h1', '.page-title'],
        'content': ['.field-item', '.content-area', 'main']
    },
    'growveg.com': {
        'title': ['h1', '.title'],
        'content': ['.article-content', '.content', 'main']
    },
    'youtube.com': {
        'title': ['h1.title', '.watch-title', 'h1'],
        'content': ['#description', '.content', '#meta-contents']
    },
}

VECTOR_DB_CONFIG = {
    "dimension": 384,
    "metric": "cosine",
    "index_type": "hnsw"
}

GOVERNMENT_EXTENSION_SITES = {
    "USDA Extension": "https://www.usda.gov",
    "Cornell Cooperative Extension": "https://cce.cornell.edu",
    "University of California Extension": "https://ucanr.edu",
    "Texas A&M AgriLife Extension": "https://agrilifeextension.tamu.edu",
    "Penn State Extension": "https://extension.psu.edu"
}

SEED_COMPANY_SOURCES = {
    "Johnny's Seeds": {
        "url": "https://www.johnnyseeds.com",
        "type": "scrape"
    },
    "Burpee": {
        "url": "https://www.burpee.com",
        "type": "scrape"
    },
    "Southern Exposure": {
        "url": "https://www.southernexposure.com",
        "type": "scrape"
    },
    "Seed Savers Exchange": {
        "url": "https://www.seedsavers.org",
        "type": "scrape"
    }
}

SOCIAL_MEDIA_SOURCES = {
    "Reddit": {
        "High_Quality_Subreddits": [
            {"subreddit": "r/gardening", "description": "General gardening discussions and advice"},
            {"subreddit": "r/vegetablegardening", "description": "Vegetable growing community"},
            {"subreddit": "r/OrganicGardening", "description": "Organic gardening methods"},
            {"subreddit": "r/permaculture", "description": "Permaculture design and practices"},
            {"subreddit": "r/Hydroponics", "description": "Hydroponic growing systems"},
            {"subreddit": "r/composting", "description": "Composting techniques and advice"},
            {"subreddit": "r/homestead", "description": "Self-sufficient living and farming"}
        ]
    }
}
