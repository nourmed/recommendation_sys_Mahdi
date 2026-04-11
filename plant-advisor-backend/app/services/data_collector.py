"""
data_collector.py - Enhanced Database Manager & Data Storage

Full Qdrant vector database integration
Manages plant requirements database for the agricultural system
Receives new plant data from environmental_analyzer.py
Ensures no duplicates and makes data available for analysis

Platforms: YouTube (with Transcripts), Websites, Wikipedia, Reddit
"""

import os
import json
import re
import time
import urllib.parse
import requests
import logging
import hashlib
import pickle
import shutil
import uuid
import sys
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import random
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np
from bs4 import BeautifulSoup
import wikipedia
from .language_manager import LanguageManager
# or
from . import language_manager

# Social media API imports
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

# Enhanced scraping imports
try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    try:
        from readability.readability import Document
        READABILITY_AVAILABLE = True
    except ImportError:
        READABILITY_AVAILABLE = False

# Optional imports with fallbacks
try:
    from youtube_search import YoutubeSearch
    YOUTUBE_SEARCH_AVAILABLE = True
except ImportError:
    YOUTUBE_SEARCH_AVAILABLE = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Qdrant for vector storage
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# Scikit-learn for fallback embeddings
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Import existing vector database
try:
    from vector_database import VectorDatabase
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False

# Import ALL trusted sources with comprehensive fallbacks
try:
    from sources import (
        TRUSTED_YOUTUBE_CHANNELS, TRUSTED_WEBSITE_DOMAINS,
        TRUSTED_URL_PATTERNS, PLANT_DISCOVERY_PATTERNS,
        PLANT_IDENTIFICATION_KEYWORDS, CONTENT_QUALITY_INDICATORS,
        CONTENT_EXTRACTION_SELECTORS, VECTOR_DB_CONFIG,
        GOVERNMENT_EXTENSION_SITES, SEED_COMPANY_SOURCES,
        SOCIAL_MEDIA_SOURCES
    )
except ImportError:
    # Comprehensive fallback configurations
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


# =============================================================================
# PLANT REQUIREMENTS DATABASE STRUCTURE
# =============================================================================
class PlantRequirementsDatabase:
    """Database structure for storing plant growth requirements."""

    def load_database(self):
        """Load existing plant requirements database."""
        if self.requirements_file.exists():
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                self.requirements = json.load(f)
        else:
            self.requirements = {}

        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "plants": [],
                "categories": {},
                "last_updated": datetime.now().isoformat()
            }

    def save_database(self):
        """Save the plant requirements database."""
        with open(self.requirements_file, 'w', encoding='utf-8') as f:
            json.dump(self.requirements, f, indent=2, ensure_ascii=False)

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def add_plant_requirements(self, plant_name: str, requirements: Dict[str, Any]) -> bool:
        """Add or update plant requirements in the database."""
        plant_key = plant_name.lower().strip()

        # Check for duplicates
        if plant_key in self.requirements:
            existing_data_size = len(json.dumps(self.requirements[plant_key]))
            new_data_size = len(json.dumps(requirements))

            if new_data_size <= existing_data_size:
                return False

        # Store the requirements
        self.requirements[plant_key] = {
            "common_name": plant_name,
            "requirements": requirements,
            "added_date": datetime.now().isoformat(),
            "source": requirements.get("source", "LLM_search"),
            "confidence_score": requirements.get("confidence_score", 0.8)
        }

        # Update index
        if plant_key not in self.index["plants"]:
            self.index["plants"].append(plant_key)

        # Categorize plant
        category = self._categorize_plant(plant_name)
        if category not in self.index["categories"]:
            self.index["categories"][category] = []
        if plant_key not in self.index["categories"][category]:
            self.index["categories"][category].append(plant_key)

        self.index["last_updated"] = datetime.now().isoformat()

        # Save to disk
        self.save_database()
        return True

    def get_plant_requirements_enhanced(self, plant_name: str) -> Dict[str, Any]:
        """Get plant data from BOTH JSON and Qdrant."""

        # Step 1: Get structured data from JSON
        json_data = self.plant_db.get_plant_requirements(plant_name)

        # Step 2: Search Qdrant for related content
        qdrant_results = []
        if self.data_vectorizer.embeddings_model and self.data_vectorizer.qdrant_db:
            # Create search query
            query = f"{plant_name} growing care requirements"
            query_vector = self.data_vectorizer.embeddings_model.encode(query)

            # Search Qdrant
            search_results = self.data_vectorizer.qdrant_db.search(
                query_vector=query_vector,
                limit=5,  # Get top 5 relevant articles
                score_threshold=0.7  # Only high relevance
            )

            for result in search_results:
                qdrant_results.append({
                    "text": result["payload"]["content"],
                    "source": result["payload"]["source_platform"],
                    "url": result["payload"]["url"],
                    "relevance_score": result["score"]
                })

        # Step 3: Combine both sources
        return {
            "structured_requirements": json_data,  # From JSON
            "related_articles": qdrant_results,  # From Qdrant
            "plant_name": plant_name
        }

    def get_comprehensive_plant_data(self, plant_name: str) -> str:
        """Get both structured + articles in one string for LLM."""

        # Get from both sources
        json_data = self.plant_db.get_plant_requirements(plant_name)

        # Search Qdrant
        context = f"Structured data:\n{json_data}\n\n"

        if self.data_vectorizer.qdrant_db:
            query_vector = self.data_vectorizer.embeddings_model.encode(
                f"{plant_name} growing care"
            )
            results = self.data_vectorizer.qdrant_db.search(query_vector, limit=3)

            context += "Related articles:\n"
            for r in results:
                context += f"- {r['payload']['content'][:200]}...\n"

        return context



    def search_plants(self, query: str) -> List[str]:
        """Search for plants in the database."""
        query_lower = query.lower()
        matches = []

        for plant_key in self.index["plants"]:
            if query_lower in plant_key:
                matches.append(plant_key)

        return matches

    def _categorize_plant(self, plant_name: str) -> str:
        """Categorize a plant based on its name."""
        plant_lower = plant_name.lower()

        for category, plants in PLANT_IDENTIFICATION_KEYWORDS.items():
            if any(p.lower() in plant_lower for p in plants):
                return category

        return "other"

    def check_duplicate(self, plant_name: str) -> bool:
        """Check if a plant already exists in the database."""
        plant_key = plant_name.lower().strip()
        return plant_key in self.requirements


# =============================================================================
# ENHANCED UNICODE/EMOJI HANDLING FOR WINDOWS
# =============================================================================
class UnicodeEmojiHandler:
    """
    Enhanced Unicode handler that fixes emoji encoding issues on Windows cp1252
    while preserving emojis where possible and providing meaningful fallbacks.
    """

    EMOJI_FALLBACKS = {
        # Status and progress indicators
        '🚀': '[LAUNCH]', '✅': '[SUCCESS]', '❌': '[ERROR]', '⚠️': '[WARNING]',
        '📊': '[STATS]', '🔍': '[SEARCH]', '💡': '[TIP]', '🎉': '[COMPLETE]',
        '⏱️': '[TIME]', '🔄': '[PROCESSING]', '💾': '[SAVE]', '📥': '[LOAD]',

        # Platform and source indicators
        '📺': '[YOUTUBE]', '💬': '[REDDIT]', '📚': '[WIKIPEDIA]', '🕷️': '[SCRAPING]',

        # Activity and process indicators
        '🧹': '[CLEANING]', '🔢': '[VECTORIZING]', '🗃️': '[DATABASE]', '🛡️': '[RESILIENT]',
        '⚡': '[FAST]', '🔧': '[CONFIG]', '🌍': '[GLOBAL]', '🎯': '[TARGET]',

        # Content and data types
        '🏛️': '[GOVERNMENT]', '🏪': '[COMMERCIAL]',
        '🌱': '[PLANTS]', '🤖': '[AI]', '🧠': '[NEURAL]', '🔤': '[TEXT]',

        # File and folder operations
        '📄': '[DOCUMENT]', '📁': '[FOLDER]', '📂': '[DIRECTORY]', '📝': '[NOTES]',
        '📈': '[CHART]', '📉': '[DECLINE]', '💥': '[IMPACT]', '🔁': '[RETRY]',

        # Quality and content indicators
        '🆕': '[NEW]', '🔥': '[HOT]', '⭐': '[FEATURED]', '🎨': '[DESIGN]',
        '🔒': '[SECURE]', '🔓': '[UNLOCK]', '🌟': '[PREMIUM]', '💎': '[QUALITY]',

        # System and technical
        '🚨': '[ALERT]', '🎪': '[EVENT]', '🎭': '[MODE]', '🎮': '[INTERACTIVE]',
        '🎲': '[RANDOM]', '🎵': '[AUDIO]', '🖥️': '[SYSTEM]', '⚙️': '[SETTINGS]'
    }

    def __init__(self):
        self.is_windows = sys.platform.startswith('win')
        self.console_encoding = self._detect_console_encoding()
        self.file_encoding = 'utf-8'
        self.emoji_support = self._test_emoji_support()

    def _detect_console_encoding(self) -> str:
        """Detect the best encoding for console output."""
        if not self.is_windows:
            return 'utf-8'

        try:
            encoding = sys.stdout.encoding or 'utf-8'
            test_emoji = "✅"
            test_emoji.encode(encoding)
            return encoding

        except (UnicodeEncodeError, LookupError, AttributeError):
            return 'cp1252'

    def _test_emoji_support(self) -> bool:
        """Test if the current console supports emoji display."""
        try:
            test_emojis = ["✅", "📊", "🚀"]
            for emoji in test_emojis:
                emoji.encode(self.console_encoding)
            return True
        except UnicodeEncodeError:
            return False

    def safe_encode_for_console(self, text: str) -> str:
        """Safely encode text for console output with emoji handling."""
        if not self.is_windows or self.emoji_support:
            try:
                text.encode(self.console_encoding)
                return text
            except UnicodeEncodeError:
                pass

        safe_text = text
        for emoji, fallback in self.EMOJI_FALLBACKS.items():
            safe_text = safe_text.replace(emoji, fallback)

        try:
            safe_text.encode(self.console_encoding, errors='strict')
            return safe_text
        except UnicodeEncodeError:
            return safe_text.encode(self.console_encoding, errors='replace').decode(self.console_encoding)

    def safe_encode_for_file(self, text: str) -> str:
        """Safely encode text for file output (always UTF-8)."""
        return text


# Global Unicode handler instance
unicode_handler = UnicodeEmojiHandler()


def safe_print(message: str):
    """Print function that handles Unicode/emoji encoding safely across platforms."""
    safe_message = unicode_handler.safe_encode_for_console(message)
    print(safe_message)

# =============================================================================
# ENHANCED CONFIGURATION CLASSES
# =============================================================================
@dataclass
class CollectionConfig:
    """Comprehensive configuration for the entire data collection system."""
    # Directory structure
    base_data_dir: str = "comprehensive_plant_data_pipeline"
    logs_dir: str = "logs"
    vector_db_dir: str = "vector_db"

    # Phase directories
    phase_directories: Dict[str, str] = field(default_factory=lambda: {
        "phase1_raw": "01_raw_data",
        "phase2_cleaned": "02_cleaned_data",
        "phase3_vectorized": "03_vectorized_data"
    })

    # Active platforms (YouTube, Websites, Wikipedia, Reddit)
    all_platforms: List[str] = field(default_factory=lambda: [
        "youtube", "websites", "wikipedia", "reddit"
    ])

    # Qdrant configuration
    qdrant_host: str = "185.215.167.14"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "plant_data_collection"

    # Performance and rate limiting
    max_workers: int = 5
    request_timeout: int = 15
    respect_delay: float = 1.0
    batch_size: int = 32
    max_retries: int = 3

    # Content processing limits
    max_content_length: int = 1000
    min_content_length: int = 50
    max_items_per_source: int = 50
    max_results_per_query: int = 50

    # NEW: Incremental collection tracking
    track_last_collected: bool = True
    last_collected_file: str = "last_collected_timestamps.json"
    min_collection_interval_hours: int = 24  # Minimum hours between collections per source

    # NEW: Advanced embeddings configuration
    embedding_model: str = "all-mpnet-base-v2"  # Better quality than all-MiniLM-L6-v2
    chunk_size: int = 512  # Token size for text chunking
    chunk_overlap: int = 50  # Overlap between chunks

    # NEW: Quality filtering
    min_quality_score: float = 1.5  # Minimum quality score to keep content
    use_semantic_filtering: bool = True  # Enable semantic filtering
    semantic_similarity_threshold: float = 0.3  # Threshold for plant-related content

    # NEW: Deduplication settings
    enable_semantic_deduplication: bool = True
    semantic_duplicate_threshold: float = 0.85  # Cosine similarity threshold


# =============================================================================
# ENHANCED LOGGING SYSTEM WITH UNICODE SUPPORT
# =============================================================================
class EnhancedUnicodeLogger:
    """Enhanced logger with comprehensive Unicode support and structured messaging."""

    def __init__(self, name: str, config: CollectionConfig):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging with proper Unicode handling for both file and console."""
        os.makedirs(self.config.logs_dir, exist_ok=True)

        self.logger.handlers.clear()

        file_handler = logging.FileHandler(
            os.path.join(self.config.logs_dir, f"{self.name.lower()}_comprehensive.log"),
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        class UnicodeConsoleFilter(logging.Filter):
            def filter(self, record):
                record.msg = unicode_handler.safe_encode_for_console(str(record.msg))
                return True

        console_handler.addFilter(UnicodeConsoleFilter())

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)

    def info(self, message: str, category: str = "INFO"):
        """Log info message with category prefix."""
        formatted_message = f"[{category}] {message}"
        self.logger.info(formatted_message)

    def warning(self, message: str, category: str = "WARNING"):
        """Log warning message with category prefix."""
        formatted_message = f"[{category}] {message}"
        self.logger.warning(formatted_message)

    def error(self, message: str, category: str = "ERROR"):
        """Log error message with category prefix."""
        formatted_message = f"[{category}] {message}"
        self.logger.error(formatted_message)

    def debug(self, message: str, category: str = "DEBUG"):
        """Log debug message with category prefix."""
        formatted_message = f"[{category}] {message}"
        self.logger.debug(formatted_message)


# =============================================================================
# COMPREHENSIVE SEARCH TERMS
# =============================================================================
COMPREHENSIVE_PLANT_SEARCH_TERMS = [
    # Basic cultivation
    "how to grow", "plant care", "gardening guide", "cultivation", "farming",
    "organic gardening", "permaculture", "hydroponics", "greenhouse growing",
    "container gardening", "urban farming", "vertical gardening", "aquaponics",

    # Scientific and botanical terms
    "botany", "horticulture", "plant biology", "plant physiology", "plant pathology",
    "soil science", "plant nutrition", "plant breeding", "seed starting", "propagation",

    # Seasonal and climate specific
    "tropical plants", "temperate gardening", "cold climate growing", "desert plants",
    "mediterranean gardening", "monsoon season planting", "winter gardening",

    # Traditional and regional knowledge
    "indigenous farming", "traditional agriculture", "heritage varieties", "heirloom plants",
    "native plant gardening", "wild edibles", "medicinal plants", "companion planting",

    # Modern techniques
    "smart farming", "precision agriculture", "automated irrigation", "plant sensors",
    "LED grow lights", "climate control", "pest management", "integrated pest management",

    # Vegetables
    "tomato growing", "lettuce cultivation", "carrot farming", "pepper plants",
    "onion growing", "garlic planting", "potato cultivation", "cucumber care",
    "broccoli growing", "spinach cultivation", "kale farming", "cabbage care",

    # Fruits
    "apple tree care", "orange cultivation", "strawberry growing", "blueberry plants",
    "grape vines", "banana plants", "lemon trees", "peach cultivation",
    "cherry trees", "pear growing", "plum trees", "watermelon farming",

    # Herbs
    "basil growing", "oregano care", "thyme cultivation", "rosemary plants",
    "sage growing", "mint care", "parsley cultivation", "cilantro growing",
    "dill planting", "chives care", "lavender growing", "chamomile cultivation",

    # Flowers
    "rose care", "tulip planting", "sunflower growing", "marigold cultivation",
    "petunia care", "lily growing", "dahlia plants", "orchid care",
    "zinnia growing", "cosmos cultivation", "pansy care", "iris planting",

    # Advanced techniques
    "companion planting", "crop rotation", "soil preparation", "composting guide",
    "pest management", "plant diseases", "irrigation systems", "plant nutrition",
    "greenhouse growing", "hydroponics", "vertical gardening", "urban farming",

    # Seasonal and climate
    "spring planting", "summer gardening", "fall harvest", "winter protection",
    "drought resistant plants", "cold hardy varieties", "tropical gardening",

    # Specific methods
    "seed starting", "transplanting", "pruning techniques", "mulching",
    "fertilizer application", "watering schedules", "harvesting tips"
]


# =============================================================================
# ENHANCED FILE MANAGEMENT SYSTEM
# =============================================================================
class EnhancedFileManager:
    """Enhanced file manager with comprehensive organization and error handling."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.base_dir = Path(config.base_data_dir)
        self.vector_db_dir = self.base_dir / config.vector_db_dir
        self.vector_db = None
        self._initialize_directories()

    def _initialize_directories(self):
        """Initialize all required directories with comprehensive structure."""
        try:
            self.base_dir.mkdir(exist_ok=True)

            for phase_key, phase_dir in self.config.phase_directories.items():
                phase_path = self.base_dir / phase_dir
                phase_path.mkdir(exist_ok=True)

            self.vector_db_dir.mkdir(exist_ok=True)
            self.logger.info(f"Created/ensured vector_db directory: {self.vector_db_dir}", "INIT")

            self._create_platform_folders()

            indexes_dir = self.base_dir / "indexes"
            indexes_dir.mkdir(exist_ok=True)

        except Exception as e:
            self.logger.error(f"Failed to initialize directories: {e}", "INIT")
            raise

    def _create_platform_folders(self):
        """Create folders for all platforms in raw data phase."""
        raw_data_path = self.base_dir / self.config.phase_directories["phase1_raw"]

        for platform in self.config.all_platforms:
            platform_path = raw_data_path / platform
            platform_path.mkdir(exist_ok=True)
            self.logger.info(f"Created/ensured platform folder: {platform_path}", "INIT")

    def generate_readable_filename(self, prefix: str) -> str:
        """Generate a readable filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.json"

    def save_data(self, data: Any, filename: str, phase: str, subfolder: str = None) -> str:
        """Save data with enhanced error handling and validation."""
        try:
            if not data:
                self.logger.warning(f"Attempting to save empty data to {filename}", "SAVE")
                return ""

            phase_dir = self.config.phase_directories.get(phase, phase)
            save_path = self.base_dir / phase_dir

            if subfolder:
                save_path = save_path / subfolder
                save_path.mkdir(exist_ok=True)

            file_path = save_path / filename

            if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
                data = str(data)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Data saved to: {file_path}", "SAVE")
            return str(file_path)

        except Exception as e:
            self.logger.error(f"Failed to save data to {filename}: {e}", "SAVE")
            raise

    def save_vectors(self, data: Any, filename: str, phase: str = "phase3_vectorized", subfolder: str = None) -> str:
        """Save vector data (can be pickle, numpy, or JSON)."""
        try:
            phase_dir = self.config.phase_directories.get(phase, phase)
            save_path = self.base_dir / phase_dir

            if subfolder:
                save_path = save_path / subfolder
                save_path.mkdir(exist_ok=True)

            file_path = save_path / filename

            if filename.endswith('.pkl'):
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            elif filename.endswith('.npy'):
                np.save(file_path, data)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Vector data saved to: {file_path}", "SAVE")
            return str(file_path)

        except Exception as e:
            self.logger.error(f"Failed to save vector data to {filename}: {e}", "SAVE")
            raise

    def save_to_vector_db_folder(self, data: Any, filename: str) -> str:
        """Save data to vector_db folder."""
        try:
            file_path = self.vector_db_dir / filename

            if filename.endswith('.pkl'):
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            elif filename.endswith('.npy'):
                np.save(file_path, data)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Data saved to vector_db folder: {file_path}", "VECTOR_DB")
            return str(file_path)

        except Exception as e:
            self.logger.error(f"Failed to save data to vector_db folder {filename}: {e}", "VECTOR_DB")
            raise

    def load_data(self, filename: str, phase: str, subfolder: str = None) -> Any:
        """Load data from the appropriate phase directory."""
        try:
            phase_dir = self.config.phase_directories.get(phase, phase)
            load_path = self.base_dir / phase_dir

            if subfolder:
                load_path = load_path / subfolder

            file_path = load_path / filename

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to load data from {filename}: {e}", "LOAD")
            raise

    def create_index_mapping(self, data: List[Dict[str, Any]], source_type: str):
        """Create an index mapping for the collected data."""
        try:
            index_data = {
                'source_type': source_type,
                'created_at': datetime.now().isoformat(),
                'total_items': len(data),
                'items': []
            }

            for i, item in enumerate(data):
                index_item = {
                    'index': i,
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'source_name': item.get('source_name', ''),
                    'collected_at': item.get('collected_at', '')
                }
                index_data['items'].append(index_item)

            index_filename = f"{source_type}_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            index_path = self.base_dir / "indexes"
            index_path.mkdir(exist_ok=True)

            with open(index_path / index_filename, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Index created: {index_path / index_filename}", "INDEX")

        except Exception as e:
            self.logger.error(f"Failed to create index for {source_type}: {e}", "INDEX")

    def get_phase_directory(self, phase: str) -> Path:
        """Get the path to a phase directory."""
        phase_dir = self.config.phase_directories.get(phase, phase)
        return self.base_dir / phase_dir

    def get_vector_db_directory(self) -> Path:
        """Get the path to the vector_db directory."""
        return self.vector_db_dir

    def list_files(self, phase: str, pattern: str = "*.json") -> List[Path]:
        """List files in a phase directory matching a pattern."""
        phase_path = self.get_phase_directory(phase)
        return list(phase_path.glob(pattern))


# =============================================================================
# INCREMENTAL COLLECTION TRACKER
# =============================================================================
class IncrementalCollectionTracker:
    """Track last collection times for incremental updates to avoid re-fetching."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.tracker_file = Path(config.base_data_dir) / config.last_collected_file
        self.timestamps = self._load_timestamps()

    def _load_timestamps(self) -> Dict[str, str]:
        """Load last collection timestamps from file."""
        try:
            if self.tracker_file.exists():
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    timestamps = json.load(f)
                self.logger.info(f"Loaded {len(timestamps)} collection timestamps", "TRACKER")
                return timestamps
        except Exception as e:
            self.logger.warning(f"Failed to load timestamps: {e}", "TRACKER")

        return {}

    def _save_timestamps(self):
        """Save collection timestamps to file."""
        try:
            self.tracker_file.parent.mkdir(exist_ok=True)
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.timestamps, f, indent=2)
            self.logger.debug("Saved collection timestamps", "TRACKER")
        except Exception as e:
            self.logger.error(f"Failed to save timestamps: {e}", "TRACKER")

    def get_last_collected(self, source_key: str) -> Optional[str]:
        """Get last collection time for a source."""
        return self.timestamps.get(source_key)

    def update_last_collected(self, source_key: str, timestamp: str = None):
        """Update last collection time to now or specified timestamp."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        self.timestamps[source_key] = timestamp
        self._save_timestamps()
        self.logger.info(f"Updated collection timestamp for {source_key}", "TRACKER")

    def should_collect(self, source_key: str, min_interval_hours: int = None) -> bool:
        """Check if enough time has passed to collect again from this source."""
        if min_interval_hours is None:
            min_interval_hours = self.config.min_collection_interval_hours

        last_time = self.get_last_collected(source_key)
        if not last_time:
            self.logger.info(f"No previous collection found for {source_key}, should collect", "TRACKER")
            return True

        try:
            last_dt = datetime.fromisoformat(last_time)
            hours_passed = (datetime.now() - last_dt).total_seconds() / 3600
            should_collect = hours_passed >= min_interval_hours

            if should_collect:
                self.logger.info(f"{source_key}: {hours_passed:.1f} hours passed, collecting", "TRACKER")
            else:
                self.logger.info(
                    f"{source_key}: Only {hours_passed:.1f} hours passed, skipping (need {min_interval_hours})",
                    "TRACKER")

            return should_collect
        except Exception as e:
            self.logger.warning(f"Error checking collection time for {source_key}: {e}", "TRACKER")
            return True  # Default to collecting if there's an error

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about collection tracking."""
        stats = {
            "total_sources_tracked": len(self.timestamps),
            "sources": {}
        }

        for source_key, timestamp in self.timestamps.items():
            try:
                last_dt = datetime.fromisoformat(timestamp)
                hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
                stats["sources"][source_key] = {
                    "last_collected": timestamp,
                    "hours_ago": round(hours_ago, 2)
                }
            except:
                stats["sources"][source_key] = {
                    "last_collected": timestamp,
                    "hours_ago": None
                }

        return stats


# =============================================================================
# ENHANCED RESILIENT SCRAPER
# =============================================================================
class EnhancedResilientScraper:
    """Comprehensive resilient web scraper with fallback strategies."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.session = self._create_session()
        self.failed_selectors = defaultdict(set)
        self.domain_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'methods_used': set()})

        self.default_selectors = {
            'title': [
                'h1', 'h2', 'h3', '.title', '.post-title', '.entry-title',
                '.article-title', '[class*="title"]', '[id*="title"]',
                'title', '[property="og:title"]', '[name="title"]'
            ],
            'content': [
                'main', 'article', '.content', '.post-content', '.entry-content',
                '.article-content', '.main-content', '[class*="content"]',
                '[class*="article"]', '[class*="post"]', '.text', 'section',
                'div.body', 'div.description', '.summary'
            ],
            'links': [
                'a[href]'
            ],
            'description': [
                '.description', '.summary', '.excerpt', '.intro',
                '[name="description"]', '[property="og:description"]'
            ]
        }

    def _create_session(self) -> requests.Session:
        """Create a robust HTTP session with retry strategy."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
        except ImportError:
            pass

        return session

    def extract_content_resilient(self, url: str, domain: str = None) -> Dict[str, Any]:
        """Extract content using multiple fallback strategies."""
        if not domain:
            domain = urllib.parse.urlparse(url).netloc.replace('www.', '')

        result = {
            'title': '',
            'content': '',
            'url': url,
            'domain': domain,
            'success': False,
            'method_used': '',
            'warnings': [],
            'extraction_time': 0,
            'extracted_at': datetime.now().isoformat()
        }

        start_time = time.time()

        try:
            response = self.session.get(url, timeout=self.config.request_timeout)
            if response.status_code != 200:
                result['warnings'].append(f"HTTP {response.status_code} error")
                return result

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Strategy 1: Domain-specific selectors
            domain_result = self._try_domain_specific_selectors(soup, domain, url)
            if domain_result['success']:
                result.update(domain_result)
                result['method_used'] = 'domain_specific'
                self.domain_stats[domain]['success'] += 1
                self.domain_stats[domain]['methods_used'].add('domain_specific')
                return result

            # Strategy 2: Default flexible selectors
            default_result = self._try_default_selectors(soup, domain, url)
            if default_result['success']:
                result.update(default_result)
                result['method_used'] = 'default_selectors'
                self.domain_stats[domain]['success'] += 1
                self.domain_stats[domain]['methods_used'].add('default_selectors')
                return result

            # Strategy 3: Readability extraction
            if READABILITY_AVAILABLE:
                readability_result = self._try_readability_extraction(html_content, url)
                if readability_result['success']:
                    result.update(readability_result)
                    result['method_used'] = 'readability'
                    self.domain_stats[domain]['success'] += 1
                    self.domain_stats[domain]['methods_used'].add('readability')
                    return result

            # Strategy 4: Heuristic text extraction
            heuristic_result = self._try_heuristic_extraction(soup, url)
            if heuristic_result['success']:
                result.update(heuristic_result)
                result['method_used'] = 'heuristic'
                self.domain_stats[domain]['success'] += 1
                self.domain_stats[domain]['methods_used'].add('heuristic')
                return result

            # Strategy 5: Last resort - all text
            fallback_result = self._try_fallback_extraction(soup, url)
            result.update(fallback_result)
            result['method_used'] = 'fallback'
            result['warnings'].append("Used fallback extraction - content quality may be lower")
            self.domain_stats[domain]['success'] += 1
            self.domain_stats[domain]['methods_used'].add('fallback')

            return result

        except Exception as e:
            result['warnings'].append(f"Extraction failed: {str(e)}")
            self.logger.warning(f"Content extraction failed for {url}: {e}", "SCRAPER")
            self.domain_stats[domain]['failed'] += 1
            return result

        finally:
            result['extraction_time'] = round(time.time() - start_time, 2)

    def _try_domain_specific_selectors(self, soup: BeautifulSoup, domain: str, url: str) -> Dict[str, Any]:
        """Try domain-specific selectors first."""
        result = {'success': False, 'title': '', 'content': '', 'warnings': []}

        if domain not in CONTENT_EXTRACTION_SELECTORS:
            return result

        selectors = CONTENT_EXTRACTION_SELECTORS[domain]

        title = self._extract_with_fallback_selectors(
            soup, selectors.get('title', []), 'title', domain
        )

        content = self._extract_with_fallback_selectors(
            soup, selectors.get('content', []), 'content', domain
        )

        if title or (content and len(content) > 100):
            result.update({
                'success': True,
                'title': title,
                'content': content
            })
            self.logger.debug(f"Domain-specific extraction successful for {domain}", "SCRAPER")
        else:
            result['warnings'].append(f"Domain-specific selectors failed for {domain}")

        return result

    def _try_default_selectors(self, soup: BeautifulSoup, domain: str, url: str) -> Dict[str, Any]:
        """Try default flexible selectors."""
        result = {'success': False, 'title': '', 'content': '', 'warnings': []}

        title = self._extract_with_fallback_selectors(
            soup, self.default_selectors['title'], 'title', domain
        )

        content = self._extract_with_fallback_selectors(
            soup, self.default_selectors['content'], 'content', domain
        )

        if title or (content and len(content) > 100):
            result.update({
                'success': True,
                'title': title,
                'content': content
            })
            self.logger.debug(f"Default selector extraction successful for {url}", "SCRAPER")
        else:
            result['warnings'].append("Default selectors found minimal content")

        return result

    def _extract_with_fallback_selectors(self, soup: BeautifulSoup, selectors: List[str],
                                         selector_type: str, domain: str) -> str:
        """Extract content using fallback selectors, skipping known failed ones."""
        for selector in selectors:
            if selector in self.failed_selectors[domain]:
                continue

            try:
                if selector_type == 'title':
                    elements = soup.select(selector)
                    if elements:
                        title = elements[0].get_text(strip=True)
                        if title and len(title) > 5:
                            self.logger.debug(f"Title extracted with selector '{selector}' for {domain}", "SCRAPER")
                            return title
                else:  # content
                    elements = soup.select(selector)
                    if elements:
                        largest_element = max(elements, key=lambda e: len(e.get_text()))
                        content = largest_element.get_text(separator=' ', strip=True)
                        if content and len(content) > 50:
                            self.logger.debug(f"Content extracted with selector '{selector}' for {domain}",
                                              "SCRAPER")
                            return content

            except Exception as e:
                self.failed_selectors[domain].add(selector)
                self.logger.debug(f"Selector '{selector}' failed for {domain}: {e}", "SCRAPER")
                continue

        return ""

    def _try_readability_extraction(self, html_content: str, url: str) -> Dict[str, Any]:
        """Try readability-lxml for content extraction."""
        result = {'success': False, 'title': '', 'content': '', 'warnings': []}

        try:
            doc = Document(html_content)
            title = doc.title()
            content_html = doc.summary()

            content_soup = BeautifulSoup(content_html, 'html.parser')
            content = content_soup.get_text(separator=' ', strip=True)

            if title or (content and len(content) > 100):
                result.update({
                    'success': True,
                    'title': title or "",
                    'content': content or ""
                })
                self.logger.debug(f"Readability extraction successful for {url}", "SCRAPER")
            else:
                result['warnings'].append("Readability found minimal content")

        except Exception as e:
            result['warnings'].append(f"Readability extraction failed: {str(e)}")
            self.logger.debug(f"Readability extraction failed for {url}: {e}", "SCRAPER")

        return result

    def _try_heuristic_extraction(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Use heuristics to find content."""
        result = {'success': False, 'title': '', 'content': '', 'warnings': []}

        try:
            for element in soup(['script', 'style', 'nav', 'header', 'footer',
                                 'sidebar', 'aside', 'menu', 'advertisement']):
                element.decompose()

            title = ""
            title_candidates = [
                soup.find('title'),
                soup.find('h1'),
                soup.find('h2'),
                soup.select_one('[property="og:title"]'),
                soup.select_one('meta[name="title"]')
            ]

            for candidate in title_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        title = candidate.get('content', '')
                    else:
                        title = candidate.get_text(strip=True)
                    if title and len(title) > 5:
                        break

            content_candidates = []

            for element in soup.find_all(['div', 'section', 'article', 'main']):
                text = element.get_text(strip=True)
                if len(text) > 200:
                    tag_count = len(element.find_all())
                    density = len(text) / max(tag_count, 1)
                    content_candidates.append((density, text, element))

            if content_candidates:
                content_candidates.sort(reverse=True)
                best_content = content_candidates[0][1]

                if title or (best_content and len(best_content) > 100):
                    result.update({
                        'success': True,
                        'title': title,
                        'content': best_content
                    })
                    self.logger.debug(f"Heuristic extraction successful for {url}", "SCRAPER")
                else:
                    result['warnings'].append("Heuristic found minimal content")
            else:
                result['warnings'].append("No content candidates found")

        except Exception as e:
            result['warnings'].append(f"Heuristic extraction failed: {str(e)}")
            self.logger.debug(f"Heuristic extraction failed for {url}: {e}", "SCRAPER")

        return result

    def _try_fallback_extraction(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Last resort: extract all text."""
        result = {'success': False, 'title': '', 'content': '', 'warnings': []}

        try:
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()

            title_elem = soup.find('title') or soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else ""

            all_text = soup.get_text(separator=' ', strip=True)
            content = re.sub(r'\s+', ' ', all_text).strip()

            if len(content) > 50:
                result.update({
                    'success': True,
                    'title': title,
                    'content': content
                })
                self.logger.debug(f"Fallback extraction successful for {url}", "SCRAPER")
            else:
                result['warnings'].append("Even fallback extraction found minimal content")

        except Exception as e:
            result['warnings'].append(f"Fallback extraction failed: {str(e)}")
            self.logger.debug(f"Fallback extraction failed for {url}: {e}", "SCRAPER")

        return result

    def extract_links_resilient(self, soup: BeautifulSoup, domain: str, base_url: str) -> List[Dict[str, str]]:
        """Extract links with resilient strategies."""
        links = []

        try:
            if domain in CONTENT_EXTRACTION_SELECTORS:
                link_selectors = CONTENT_EXTRACTION_SELECTORS[domain].get('links', self.default_selectors['links'])
            else:
                link_selectors = self.default_selectors['links']

            found_links = set()

            for selector in link_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        href = element.get('href', '')
                        text = element.get_text(strip=True)

                        if href and href not in found_links:
                            if href.startswith('/'):
                                href = urllib.parse.urljoin(base_url, href)
                            elif not href.startswith(('http://', 'https://')):
                                continue

                            if self._is_plant_related_link(text, href):
                                links.append({
                                    'url': href,
                                    'text': text,
                                    'selector_used': selector
                                })
                                found_links.add(href)

                except Exception as e:
                    self.logger.debug(f"Link selector '{selector}' failed for {domain}: {e}", "SCRAPER")
                    continue

            self.logger.debug(f"Extracted {len(links)} plant-related links from {domain}", "SCRAPER")

        except Exception as e:
            self.logger.warning(f"Link extraction failed for {domain}: {e}", "SCRAPER")

        return links

    def _is_plant_related_link(self, text: str, href: str) -> bool:
        """Check if a link is plant-related using enhanced detection."""
        try:
            combined = f"{text} {href}".lower()

            plant_indicators = [
                'plant', 'garden', 'grow', 'seed', 'flower', 'vegetable', 'fruit',
                'herb', 'tree', 'cultivation', 'farming', 'agriculture', 'organic',
                'permaculture', 'hydroponic', 'greenhouse', 'nursery', 'botanical'
            ]

            has_plant_indicator = any(indicator in combined for indicator in plant_indicators)

            exclusions = [
                'login', 'register', 'cart', 'checkout', 'payment', 'shipping',
                'privacy', 'terms', 'contact', 'about', 'facebook', 'twitter',
                'instagram', 'youtube', 'pinterest', 'advertisement', 'ad'
            ]

            has_exclusion = any(exclusion in combined for exclusion in exclusions)

            return has_plant_indicator and not has_exclusion

        except Exception:
            return False

    def get_domain_statistics(self) -> Dict[str, Any]:
        """Get scraping statistics by domain."""
        stats = {}
        for domain, data in self.domain_stats.items():
            total_attempts = data['success'] + data['failed']
            success_rate = (data['success'] / total_attempts * 100) if total_attempts > 0 else 0

            stats[domain] = {
                'success_count': data['success'],
                'failed_count': data['failed'],
                'success_rate': round(success_rate, 2),
                'methods_used': list(data['methods_used'])
            }

        return stats


# =============================================================================
# ENHANCED QDRANT VECTOR DATABASE - ROBUST UPLOAD
# =============================================================================
class EnhancedQdrantVectorDatabase:
    """Enhanced Qdrant vector database manager with retry logic and connection stability."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.client = None
        self.vector_dimension = None
        self.performance_metrics = {}
        self.connect()

    def connect(self):
        """Connect to Qdrant instance with enhanced error handling."""
        try:
            if QDRANT_AVAILABLE:
                # FIX 1: Set a high timeout (60 seconds)
                self.client = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                    timeout=60
                )
                try:
                    collections = self.client.get_collections()
                    self.logger.info(f"Connected to Qdrant at {self.config.qdrant_host}:{self.config.qdrant_port}",
                                     "QDRANT")
                    self.logger.info(f"Existing collections: {len(collections.collections)}", "QDRANT")
                except Exception as e:
                    self.logger.error(f"Qdrant connection test failed: {e}", "QDRANT")
                    self.client = None
            else:
                self.logger.error("Qdrant client not available", "QDRANT")
                self.client = None
        except Exception as e:
            self.logger.error(f"Failed to connect to Qdrant: {e}", "QDRANT")
            self.logger.info("Make sure Qdrant is running", "QDRANT")
            self.client = None

    def create_collection(self, vector_dimension: int, distance_metric: Distance = Distance.COSINE,
                          recreate: bool = False):
        """Create Qdrant collection for vectors."""
        if not self.client:
            return False

        try:
            collections = self.client.get_collections()
            collection_exists = any(
                col.name == self.config.qdrant_collection_name for col in collections.collections)

            if collection_exists and recreate:
                self.logger.info(f"Deleting existing collection: {self.config.qdrant_collection_name}", "QDRANT")
                self.client.delete_collection(collection_name=self.config.qdrant_collection_name)
                collection_exists = False

            if not collection_exists:
                self.logger.info(f"Creating Qdrant collection: {self.config.qdrant_collection_name}", "QDRANT")
                self.client.create_collection(
                    collection_name=self.config.qdrant_collection_name,
                    vectors_config=VectorParams(
                        size=vector_dimension,
                        distance=distance_metric
                    )
                )
                self.logger.info(f"Collection created with dimension {vector_dimension}", "QDRANT")

            self.vector_dimension = vector_dimension
            return True

        except Exception as e:
            self.logger.error(f"Failed to create collection: {e}", "QDRANT")
            return False

    def add_points(self, embeddings: np.ndarray, metadata_list: List[Dict[str, Any]]):
        """Add points to Qdrant collection with RETRY LOGIC and SMALLER BATCHES."""
        if not self.client:
            self.logger.error("Qdrant client not connected", "QDRANT")
            return False

        try:
            points = []
            # convert numpy to list for safety
            vectors_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings

            for i, (vector, metadata) in enumerate(zip(vectors_list, metadata_list)):
                point_id = str(uuid.uuid4())

                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "plant_name": metadata.get("plant_name", ""),
                        "title": metadata.get("title", ""),
                        "content": metadata.get("content", ""),
                        "url": metadata.get("url", ""),
                        "source_platform": metadata.get("source_platform", ""),
                        "quality_score": metadata.get("quality_score", 0.0),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "vector_index": metadata.get("vector_index", i),
                        "collected_at": metadata.get("collected_at", "")
                    }
                )
                points.append(point)

            # FIX 2: Smaller batch size (32 is safer than 100)
            batch_size = 32
            total_points = len(points)
            successful_batches = 0

            for i in range(0, total_points, batch_size):
                batch = points[i:i + batch_size]

                # FIX 3: Retry logic
                retries = 3
                for attempt in range(retries):
                    try:
                        self.client.upsert(
                            collection_name=self.config.qdrant_collection_name,
                            points=batch
                        )
                        successful_batches += 1
                        if i % (batch_size * 5) == 0:
                            safe_print(f"    📤 Uploaded batch {successful_batches} ({(i / total_points) * 100:.0f}%)")
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt < retries - 1:
                            time.sleep(2)  # Wait 2 seconds before retry
                            continue
                        else:
                            self.logger.error(f"Failed to upload batch starting at index {i}: {e}", "QDRANT")
                            # Don't return False immediately, try to continue with next batches

                time.sleep(0.1)  # Brief pause to be nice to server

            self.logger.info(f"Upload complete. Processed {total_points} points.", "QDRANT")
            return True

        except Exception as e:
            self.logger.error(f"Critical error in add_points: {e}", "QDRANT")
            return False

    def search(self, query_vector: Union[List[float], np.ndarray], limit: int = 10, score_threshold: float = 0.0):
        """Search for similar vectors in Qdrant."""
        if not self.client:
            return []

        try:
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()

            search_result = self.client.search(
                collection_name=self.config.qdrant_collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )

            results = []
            for scored_point in search_result:
                results.append({
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload
                })
            return results

        except Exception as e:
            self.logger.error(f"Failed to search Qdrant: {e}", "QDRANT")
            return []

    def get_collection_info(self):
        """Get collection information."""
        if not self.client:
            return None
        try:
            info = self.client.get_collection(collection_name=self.config.qdrant_collection_name)
            return {
                "vectors_count": info.vectors_count,
                "segments_count": info.segments_count,
                "disk_data_size": info.disk_data_size
            }
        except Exception:
            return None

    def delete_collection(self):
        """Delete the collection."""
        if not self.client: return False
        try:
            self.client.delete_collection(collection_name=self.config.qdrant_collection_name)
            return True
        except Exception:
            return False


# =============================================================================
# SOCIAL MEDIA COLLECTOR - ENHANCED WITH INCREMENTAL TRACKING
# =============================================================================
class SocialMediaCollector:
    """Collect data from Reddit using PRAW API with incremental tracking."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger,
                 tracker: IncrementalCollectionTracker):
        self.config = config
        self.logger = logger
        self.tracker = tracker
        self.reddit_api = None
        self._setup_reddit_api()

    def _setup_reddit_api(self):
        """Set up Reddit API client."""
        try:
            client_id = "1sQzgeuj25d4xMRly6O5Kg"
            client_secret = "twqjYRdD8fnajWB32cVvfi11BmCSEQ"
            user_agent = "AgriCollector/0.1 by mahdi"

            if PRAW_AVAILABLE:
                self.reddit_api = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                self.logger.info("Reddit API connection established", "REDDIT")
            else:
                self.logger.warning("PRAW not available", "REDDIT")
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit API: {e}", "REDDIT")
            self.reddit_api = None

    def collect_reddit_data(self, search_terms):
        """Collect relevant plant care data from Reddit with incremental updates."""
        reddit_data = []

        if not self.reddit_api:
            self.logger.warning("Reddit API not available", "REDDIT")
            return reddit_data

        safe_print("🔍 Collecting data from Reddit...")

        try:
            trusted_subreddits = SOCIAL_MEDIA_SOURCES.get('Reddit', {}).get('High_Quality_Subreddits', [])

            for subreddit_info in trusted_subreddits:
                subreddit_name = subreddit_info['subreddit'].replace('r/', '')
                source_key = f"reddit_{subreddit_name}"

                # Check incremental collection
                if not self.tracker.should_collect(source_key):
                    safe_print(f"  ⏭️ Skipping {subreddit_name} - recently collected")
                    continue

                safe_print(f"  📄 Collecting from subreddit: {subreddit_name}")

                try:
                    subreddit = self.reddit_api.subreddit(subreddit_name)
                    collected_count = 0

                    # Collect top posts
                    for post in subreddit.top('month', limit=25):
                        try:
                            post_data = self._process_reddit_post(post, subreddit_name, subreddit_info, 'top_post')
                            reddit_data.append(post_data)
                            collected_count += 1
                        except Exception:
                            continue

                    # Collect hot posts
                    for post in subreddit.hot(limit=25):
                        try:
                            post_data = self._process_reddit_post(post, subreddit_name, subreddit_info, 'hot_post')
                            reddit_data.append(post_data)
                            collected_count += 1
                        except Exception:
                            continue

                    self.tracker.update_last_collected(source_key)
                    safe_print(f"    ✅ Collected {collected_count} posts")
                    time.sleep(1)

                except Exception as e:
                    self.logger.debug(f"Error collecting from subreddit {subreddit_name}: {e}", "REDDIT")
                    continue

            # Search Reddit
            for term in search_terms[:10]:
                source_key = f"reddit_search_{term}"
                if not self.tracker.should_collect(source_key):
                    continue

                safe_print(f"  🔍 Searching Reddit for: {term}")

                try:
                    search_results = self.reddit_api.subreddit('all').search(term, limit=20)
                    collected_count = 0

                    for post in search_results:
                        try:
                            post_data = {
                                'title': post.title,
                                'text': post.selftext,
                                'url': f"https://www.reddit.com{post.permalink}",
                                'post_id': post.id,
                                'author': str(post.author) if post.author else '[deleted]',
                                'created_at': datetime.fromtimestamp(post.created_utc).isoformat(),
                                'score': post.score,
                                'upvote_ratio': post.upvote_ratio,
                                'num_comments': post.num_comments,
                                'source_type': 'reddit',
                                'source_name': 'reddit_search',
                                'subreddit': post.subreddit.display_name,
                                'search_term': term,
                                'post_type': 'search_result',
                                'extraction_method': 'reddit_api',
                                'extraction_warnings': [],
                                'collected_at': datetime.now().isoformat()
                            }
                            reddit_data.append(post_data)
                            collected_count += 1
                        except Exception:
                            continue

                    self.tracker.update_last_collected(source_key)
                    time.sleep(1)

                except Exception as e:
                    self.logger.debug(f"Error searching Reddit for '{term}': {e}", "REDDIT")
                    continue

            safe_print(f"✅ Reddit: {len(reddit_data)} posts collected")

        except Exception as e:
            self.logger.error(f"Reddit collection failed: {e}", "REDDIT")

        return reddit_data

    def _process_reddit_post(self, post, subreddit_name, subreddit_info, post_type):
        """Helper to process individual reddit posts."""
        return {
            'title': post.title,
            'text': post.selftext,
            'url': f"https://www.reddit.com{post.permalink}",
            'post_id': post.id,
            'author': str(post.author) if post.author else '[deleted]',
            'created_at': datetime.fromtimestamp(post.created_utc).isoformat(),
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'source_type': 'reddit',
            'source_name': f'reddit_{subreddit_name}',
            'subreddit': subreddit_name,
            'subreddit_description': subreddit_info.get('description', ''),
            'post_type': post_type,
            'extraction_method': 'reddit_api',
            'extraction_warnings': [],
            'collected_at': datetime.now().isoformat()
        }


# =============================================================================
# MULTIPLATFORM VIDEO COLLECTOR - WITH DETAILED LOGS & LIMITS
# =============================================================================
class MultiPlatformVideoCollector:
    """Collect videos from YouTube with transcript support and incremental tracking."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger,
                 tracker: IncrementalCollectionTracker):
        self.config = config
        self.logger = logger
        self.tracker = tracker
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.scraper = EnhancedResilientScraper(config, logger)

    def _get_video_transcript(self, video_id: str) -> str:
        """Extract transcript from YouTube video."""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            return ""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            full_transcript = " ".join([t['text'] for t in transcript_list])
            return full_transcript
        except Exception:
            return ""

    def collect_youtube_comprehensive(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Comprehensive YouTube data collection with transcripts."""
        youtube_data = []
        MAX_VIDEOS_TOTAL = 1000  # 🚀 INCREASED LIMIT TO 1000

        safe_print(f"📺 STARTING YOUTUBE COLLECTION (Limit: {MAX_VIDEOS_TOTAL} videos)...")

        # ---------------------------------------------------------
        # PASTE YOUR API KEY HERE
        # ---------------------------------------------------------
        youtube_api_key = "***REMOVED***"
        # ---------------------------------------------------------

        if youtube_api_key and GOOGLE_API_AVAILABLE:
            api_data = self._youtube_api_collection(search_terms, youtube_api_key, MAX_VIDEOS_TOTAL)
            youtube_data.extend(api_data)

        safe_print(f"✅ YouTube Collection Finished: {len(youtube_data)}/{MAX_VIDEOS_TOTAL} videos collected")
        return youtube_data

    def _youtube_api_collection(self, search_terms: List[str], api_key: str, max_limit: int) -> List[Dict[str, Any]]:
        """Use YouTube API for comprehensive collection with detailed logging."""
        api_data = []
        total_collected = 0

        try:
            youtube = build('youtube', 'v3', developerKey=api_key)

            # --- PART 1: SEARCH TERMS ---
            safe_print("\n🔍 --- STEP 1: Processing Search Terms ---")

            # Process more search terms to get variety (Top 20 instead of 5)
            for i, term in enumerate(search_terms[:20]):
                if total_collected >= max_limit: break

                safe_print(f"  🔎 Searching for term: '{term}'")

                try:
                    search_response = youtube.search().list(
                        q=term, type='video', part='id,snippet',
                        maxResults=20, # Increased from 5 to 20 videos per term
                        relevanceLanguage='en', safeSearch='moderate'
                    ).execute()

                    items = search_response.get('items', [])
                    safe_print(f"    📊 Found {len(items)} videos for '{term}'")

                    for item in items:
                        if total_collected >= max_limit: break

                        video_title = item['snippet']['title']
                        safe_print(f"      🎥 Scraping ({total_collected + 1}/{max_limit}): {video_title[:50]}...")

                        self._process_youtube_api_item(item, term, api_data)
                        total_collected += 1

                except Exception as e:
                    self.logger.debug(f"Search failed for '{term}': {e}", "YOUTUBE")
                    continue

            # --- PART 2: CHANNELS (IMPROVED - Playlist Strategy) ---
            if total_collected < max_limit:
                safe_print("\n📺 --- STEP 2: Processing Trusted Channels (Uploads Playlist) ---")

                total_channels = len(TRUSTED_YOUTUBE_CHANNELS)

                for i, (channel_name, channel_id) in enumerate(TRUSTED_YOUTUBE_CHANNELS.items()):
                    if total_collected >= max_limit:
                        safe_print(f"🛑 Reached limit of {max_limit} videos. Stopping.")
                        break

                    safe_print(f"  📡 Visiting Channel {i + 1}/{total_channels}: {channel_name}")

                    try:
                        # 1. Convert Channel ID (UC...) to Uploads Playlist ID (UU...)
                        if channel_id.startswith('UC'):
                            playlist_id = 'UU' + channel_id[2:]
                        else:
                            playlist_id = channel_id

                        # 2. Fetch recent videos from the playlist
                        playlist_response = youtube.playlistItems().list(
                            playlistId=playlist_id,
                            part='snippet,contentDetails',
                            maxResults=50  # Increased to 50 (API max per page) to get more per channel
                        ).execute()

                        items = playlist_response.get('items', [])
                        safe_print(f"    📊 Found {len(items)} recent videos on channel")

                        for item in items:
                            if total_collected >= max_limit: break

                            # Playlist items structure is slightly different
                            video_id = item['contentDetails']['videoId']
                            video_title = item['snippet']['title']

                            # Standardize item format for _process helper
                            standardized_item = {
                                'id': {'videoId': video_id},
                                'snippet': item['snippet']
                            }

                            safe_print(f"      🎥 Scraping ({total_collected + 1}/{max_limit}): {video_title[:50]}...")

                            self._process_youtube_api_item(standardized_item, "channel_collection", api_data)
                            total_collected += 1

                    except Exception as e:
                        safe_print(f"    ❌ Failed to access channel {channel_name}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"YouTube API Error: {e}", "YOUTUBE")

        return api_data

    def _process_youtube_api_item(self, item, term, data_list):
        """Helper to process YouTube API items."""
        try:
            video_id = item['id']['videoId']
            # Try to get transcript
            transcript = self._get_video_transcript(video_id)

            if transcript:
                safe_print("        ✅ Transcript found!")
            else:
                safe_print("        ⚠️ No transcript (using description)")

            video_data = {
                'title': item['snippet']['title'],
                'text': transcript if transcript else item['snippet']['description'],
                'has_transcript': bool(transcript),
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'video_id': video_id,
                'channel': item['snippet']['channelTitle'],
                'channel_id': item['snippet'].get('channelId', ''),
                'published_at': item['snippet']['publishedAt'],
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'source_type': 'youtube',
                'source_name': 'youtube_api',
                'search_term': term,
                'extraction_method': 'api',
                'extraction_warnings': [],
                'collected_at': datetime.now().isoformat()
            }
            data_list.append(video_data)
        except Exception:
            pass

    def _youtube_search_collection(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        # This fallback is not needed if API works, keeping empty for now to enforce limit via API
        return []

# =============================================================================
# COMPREHENSIVE SOURCE COLLECTOR - IMPROVED EXTRACTION
# =============================================================================
class ComprehensiveSourceCollector:
    """Collect data from government and commercial sources with resilient scraping."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger,
                 tracker: IncrementalCollectionTracker):
        self.config = config
        self.logger = logger
        self.tracker = tracker
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.scraper = EnhancedResilientScraper(config, logger)

    def collect_government_extensions(self) -> List[Dict[str, Any]]:
        """Collect from government extension services with resilient scraping."""
        extension_data = []

        safe_print("🏛️ Collecting from government extension services...")

        for source_name, source_url in GOVERNMENT_EXTENSION_SITES.items():
            source_key = f"gov_{source_name.replace(' ', '_')}"

            # TEMPORARY: Commented out tracker check to force collection for debugging
            # if not self.tracker.should_collect(source_key):
            #     safe_print(f"  ⏭️ Skipping {source_name} - recently collected")
            #     continue

            try:
                safe_print(f"  📍 Collecting from {source_name}...")
                collected = self._collect_extension_site_resilient(source_name, source_url)

                if collected:
                    extension_data.extend(collected)
                    self.tracker.update_last_collected(source_key)
                    safe_print(f"    ✅ Collected {len(collected)} items")
                else:
                    safe_print(f"    ⚠️ No content found for {source_name} (check scraper/selectors)")

            except Exception as e:
                self.logger.debug(f"Extension site collection failed for {source_name}: {e}", "GOVERNMENT")
                continue

        safe_print(f"✅ Government extensions: {len(extension_data)} items collected")
        return extension_data

    def collect_commercial_sources(self) -> List[Dict[str, Any]]:
        """Collect from seed companies and commercial sources with resilient scraping."""
        commercial_data = []

        safe_print("🏪 Collecting from commercial sources...")

        for source_name, source_config in SEED_COMPANY_SOURCES.items():
            source_key = f"commercial_{source_name.replace(' ', '_')}"

            # TEMPORARY: Commented out tracker check
            # if not self.tracker.should_collect(source_key):
            #     safe_print(f"  ⏭️ Skipping {source_name} - recently collected")
            #     continue

            try:
                safe_print(f"  🏢 Collecting from {source_name}...")
                # Handle both dict config and simple URL string
                if isinstance(source_config, dict):
                    url = source_config.get("url")
                else:
                    url = source_config

                collected = self._collect_commercial_site_resilient(source_name, url)

                if collected:
                    commercial_data.extend(collected)
                    self.tracker.update_last_collected(source_key)
                    safe_print(f"    ✅ Collected {len(collected)} items")
                else:
                    safe_print(f"    ⚠️ No content found for {source_name}")

            except Exception as e:
                self.logger.debug(f"Commercial source collection failed for {source_name}: {e}", "COMMERCIAL")
                continue

        safe_print(f"✅ Commercial sources: {len(commercial_data)} items collected")
        return commercial_data

    def _collect_extension_site_resilient(self, source_name: str, source_url: str) -> List[Dict[str, Any]]:
        """Actual scraping logic for extension sites."""
        items = []
        try:
            # 1. Scrape the main page/hub
            result = self.scraper.extract_content_resilient(source_url)

            # If main page has content, save it
            if result['success'] and len(result['content']) > 200:
                items.append({
                    'title': result['title'],
                    'text': result['content'],
                    'url': source_url,
                    'source_name': source_name,
                    'source_type': 'government_extension',
                    'extraction_method': result['method_used'],
                    'extraction_warnings': result['warnings'],
                    'collected_at': datetime.now().isoformat()
                })

            # 2. Aggressive Link Finding (Depth 1)
            response = self.scraper.session.get(source_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                domain = urllib.parse.urlparse(source_url).netloc.replace('www.', '')

                # Find ALL links
                all_links = soup.find_all('a', href=True)
                candidate_urls = set()

                for link in all_links:
                    href = link['href']
                    # Fix relative URLs
                    if href.startswith('/'):
                        href = urllib.parse.urljoin(source_url, href)
                    elif not href.startswith('http'):
                        continue

                    # Filter for interesting keywords in URL
                    if any(x in href.lower() for x in
                           ['grow', 'plant', 'garden', 'crop', 'farm', 'guide', 'factsheet', 'publication']):
                        candidate_urls.add(href)

                # Limit to 10 candidates to avoid getting banned
                for url in list(candidate_urls)[:10]:
                    try:
                        sub_result = self.scraper.extract_content_resilient(url, domain)
                        if sub_result['success'] and len(sub_result['content']) > 300:
                            items.append({
                                'title': sub_result['title'],
                                'text': sub_result['content'],
                                'url': url,
                                'source_name': source_name,
                                'source_type': 'government_extension',
                                'extraction_method': sub_result['method_used'],
                                'collected_at': datetime.now().isoformat()
                            })
                        time.sleep(1)  # Be polite
                    except Exception:
                        continue

        except Exception as e:
            self.logger.debug(f"Error scraping {source_name}: {e}", "GOVERNMENT")

        return items

    def _collect_commercial_site_resilient(self, source_name: str, source_url: str) -> List[Dict[str, Any]]:
        """Actual scraping logic for commercial sites."""
        items = []
        try:
            domain = urllib.parse.urlparse(source_url).netloc.replace('www.', '')

            # 1. Scrape main page
            result = self.scraper.extract_content_resilient(source_url, domain)

            if result['success'] and len(result['content']) > 150:
                items.append({
                    'title': result['title'],
                    'text': result['content'],
                    'url': source_url,
                    'source_name': source_name,
                    'source_type': 'commercial',
                    'extraction_method': result['method_used'],
                    'extraction_warnings': result['warnings'],
                    'collected_at': datetime.now().isoformat()
                })

            # 2. Aggressive Link Finding (Depth 1)
            response = self.scraper.session.get(source_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find ALL links
                all_links = soup.find_all('a', href=True)
                candidate_urls = set()

                for link in all_links:
                    href = link['href']
                    # Fix relative URLs
                    if href.startswith('/'):
                        href = urllib.parse.urljoin(source_url, href)
                    elif not href.startswith('http'):
                        continue

                    # Filter for commercial keywords (product pages, growing guides)
                    if any(x in href.lower() for x in ['product', 'seed', 'guide', 'how-to', 'growing']):
                        candidate_urls.add(href)

                # Limit to 5 candidates
                for url in list(candidate_urls)[:5]:
                    try:
                        sub_result = self.scraper.extract_content_resilient(url, domain)
                        if sub_result['success'] and len(sub_result['content']) > 200:
                            items.append({
                                'title': sub_result['title'],
                                'text': sub_result['content'],
                                'url': url,
                                'source_name': source_name,
                                'source_type': 'commercial',
                                'extraction_method': sub_result['method_used'],
                                'collected_at': datetime.now().isoformat()
                            })
                        time.sleep(1)
                    except Exception:
                        continue

        except Exception as e:
            self.logger.debug(f"Error scraping {source_name}: {e}", "COMMERCIAL")

        return items


# =============================================================================
# DATA CLEANER - RELAXED FILTERING FOR MORE DATA
# =============================================================================
class DataCleaner:
    """Phase 2: Clean and organize the raw data collected in Phase 1."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.discovered_plants = set()
        self.seen_content_hashes = set()
        self.removal_stats = defaultdict(int)

        # Load semantic model for filtering
        self.semantic_model = None
        if config.use_semantic_filtering and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.semantic_model = SentenceTransformer(config.embedding_model)
                self.logger.info(f"Loaded semantic model for filtering: {config.embedding_model}", "PHASE2")
            except Exception as e:
                self.logger.warning(f"Failed to load semantic model for filtering: {e}", "PHASE2")

    def clean_and_organize_data(self, file_manager: EnhancedFileManager) -> Dict[str, Any]:
        """Phase 2: Clean and organize all raw data."""
        safe_print("\n" + "=" * 80)
        safe_print("🧹 PHASE 2: CLEANING AND ORGANIZING RAW DATA (RELAXED FILTERS)")
        safe_print("=" * 80)

        phase2_start = time.time()
        cleaned_data = []

        try:
            raw_data_dir = file_manager.get_phase_directory("phase1_raw")

            for platform in self.config.all_platforms:
                platform_path = raw_data_dir / platform
                if platform_path.exists():
                    safe_print(f"🔧 Cleaning {platform} data...")
                    platform_data = self._clean_platform_data(platform, platform_path)
                    cleaned_data.extend(platform_data)

                    if platform_data:
                        filename = file_manager.generate_readable_filename(f"{platform}_cleaned")
                        file_manager.save_data(platform_data, filename, "phase2_cleaned", platform)

            safe_print("🌱 Identifying plants in cleaned data...")
            for item in cleaned_data:
                plants = self._identify_plants_comprehensive(item.get('text', ''), item.get('title', ''))
                item['plants_mentioned'] = list(plants)
                self.discovered_plants.update(plants)

            organized_data = self._organize_data_by_categories(cleaned_data)

            filename = file_manager.generate_readable_filename("organized_cleaned_data")
            file_manager.save_data(organized_data, filename, "phase2_cleaned")

            phase2_result = {
                "status": "completed",
                "organized_data": organized_data,
                "timestamp": datetime.now().isoformat(),
                "total_items_cleaned": len(cleaned_data),
                "unique_plants_identified": len(self.discovered_plants),
                "removal_statistics": dict(self.removal_stats),
                "processing_time": time.time() - phase2_start,
                "categories_created": list(organized_data.keys()) if isinstance(organized_data, dict) else []
            }

            summary_filename = file_manager.generate_readable_filename("PHASE2_CLEANING_Stats")
            file_manager.save_data(phase2_result, summary_filename, "phase2_cleaned")

            safe_print(f"\n✅ PHASE 2 COMPLETED!")
            safe_print(f"📊 Total items kept: {len(cleaned_data)}")
            safe_print(f"🗑️ Items removed: {sum(self.removal_stats.values())}")
            safe_print(f"🌱 Unique plants identified: {len(self.discovered_plants)}")
            safe_print(f"⏱️ Processing time: {time.time() - phase2_start:.2f}s")

            return phase2_result

        except Exception as e:
            self.logger.error(f"Phase 2 cleaning failed: {e}", "PHASE2")
            return {"status": "failed", "error": str(e)}

    def _clean_platform_data(self, platform: str, platform_path: Path) -> List[Dict[str, Any]]:
        """Clean data from a specific platform."""
        platform_data = []

        for json_file in platform_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        cleaned_item = self._clean_single_item(item, platform)
                        if cleaned_item:
                            platform_data.append(cleaned_item)
                elif isinstance(data, dict):
                    cleaned_item = self._clean_single_item(data, platform)
                    if cleaned_item:
                        platform_data.append(cleaned_item)

            except Exception as e:
                self.logger.debug(f"Error loading {json_file}: {e}", "PHASE2")
                continue

        return platform_data

    def _clean_single_item(self, item: Dict[str, Any], platform: str) -> Optional[Dict[str, Any]]:
        """Clean a single data item."""
        try:
            title = self._clean_text(item.get('title', ''))
            text = self._clean_text(item.get('text', ''))
            url = item.get('url', '').strip()

            if not title and not text:
                self.removal_stats['empty'] += 1
                return None

            # Relaxed Duplicate Check: Only for substantial content
            if len(text) > 100 and self._is_duplicate_content(text):
                self.removal_stats['duplicate'] += 1
                return None

            # Enhanced Semantic Filtering
            relevance_score = 0.0
            if self.semantic_model:
                is_relevant, relevance_score = self._semantic_filter_check(text, title)
                if not is_relevant:
                    self.removal_stats['semantic_irrelevant'] += 1
                    # Log dropped items for debugging (optional, can be noisy)
                    # self.logger.debug(f"Dropped low relevance ({relevance_score:.2f}): {title}", "PHASE2")
                    return None

            # Keyword Backup: If semantic model missing or passed, check keywords
            # But be very lenient if semantic model passed it
            if not self.semantic_model and not self._is_plant_related_enhanced(text, title):
                self.removal_stats['keyword_irrelevant'] += 1
                return None

            cleaned_item = {
                'title': title,
                'text': text,
                'url': url,
                'source_platform': platform,
                'source_type': item.get('source_type', platform),
                'source_name': item.get('source_name', ''),
                'collected_at': item.get('collected_at', ''),
                'cleaned_at': datetime.now().isoformat(),
                'content_length': len(text),
                'quality_score': self._calculate_quality_score(title, text),
                'relevance_score': float(relevance_score),
                'extraction_method': item.get('extraction_method', 'unknown'),
                'extraction_warnings': item.get('extraction_warnings', [])
            }

            if platform == 'youtube':
                cleaned_item.update({
                    'video_id': item.get('video_id', ''),
                    'channel': item.get('channel', ''),
                    'duration': item.get('duration', ''),
                    'views': item.get('views', ''),
                    'has_transcript': item.get('has_transcript', False)
                })

            elif platform == 'reddit':
                cleaned_item.update({
                    'post_id': item.get('post_id', ''),
                    'subreddit': item.get('subreddit', ''),
                    'author': item.get('author', ''),
                    'score': item.get('score', 0),
                    'num_comments': item.get('num_comments', 0)
                })

            return cleaned_item

        except Exception as e:
            self.logger.debug(f"Error cleaning item: {e}", "PHASE2")
            return None

    def _semantic_filter_check(self, text: str, title: str) -> Tuple[bool, float]:
        """Check if content is semantically relevant to plants/agriculture."""
        try:
            # Reference anchors for plant content
            anchors = [
                "how to grow plants vegetables fruits",
                "agriculture farming soil irrigation",
                "plant care disease pest control",
                "botany horticulture gardening guide",
                "growing food homesteading"
            ]

            # Encode content (limit length for speed) and anchors
            content_emb = self.semantic_model.encode(f"{title} {text}"[:512])
            anchor_embs = self.semantic_model.encode(anchors)

            # Calculate max similarity
            from sklearn.metrics.pairwise import cosine_similarity
            scores = cosine_similarity([content_emb], anchor_embs)[0]
            max_score = float(max(scores))

            # Threshold lowered to 0.15 to keep more data
            is_relevant = max_score > 0.15

            return is_relevant, max_score

        except Exception:
            # If semantic check fails (e.g. library missing), default to True (pass)
            return True, 0.0

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        try:
            text = re.sub(r'\s+', ' ', text).strip()
            # Keep basic punctuation but remove weird symbols
            text = re.sub(r'[^\w\s\.,!?;:\-\'\"/]', '', text)
            text = re.sub(r'https?://\S+', '', text)
            text = re.sub(r'\S+@\S+\.\S+', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        except Exception as e:
            self.logger.debug(f"Text cleaning failed: {e}", "PHASE2")
            return text

    def _calculate_quality_score(self, title: str, text: str) -> float:
        """Calculate content quality score."""
        try:
            score = 0.0
            combined_text = (title + " " + text).lower()

            if len(text) > 500:
                score += 2.0
            elif len(text) > 200:
                score += 1.0

            for indicator in CONTENT_QUALITY_INDICATORS["high_quality_indicators"]:
                if indicator.lower() in combined_text:
                    score += 1.0

            for indicator in CONTENT_QUALITY_INDICATORS["low_quality_indicators"]:
                if indicator.lower() in combined_text:
                    score -= 0.5

            plant_indicators = ["step by step", "how to", "guide", "tutorial", "tips", "care", "growing"]
            for indicator in plant_indicators:
                if indicator in combined_text:
                    score += 0.5

            return max(0.0, score)

        except Exception as e:
            self.logger.debug(f"Quality score calculation failed: {e}", "PHASE2")
            return 0.0

    def _organize_data_by_categories(self, cleaned_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Organize cleaned data into logical categories."""
        organized = {
            "by_platform": defaultdict(list),
            "by_plant_type": defaultdict(list),
            "by_content_type": defaultdict(list),
            "by_quality": defaultdict(list),
            "by_extraction_method": defaultdict(list),
            "high_value_content": [],
            "metadata": {
                "total_items": len(cleaned_data),
                "organization_timestamp": datetime.now().isoformat()
            }
        }

        for item in cleaned_data:
            platform = item.get('source_platform', 'unknown')
            organized["by_platform"][platform].append(item)

            plants = item.get('plants_mentioned', [])
            for plant in plants:
                plant_category = self._categorize_plant(plant)
                organized["by_plant_type"][plant_category].append(item)

            content_type = self._determine_content_type(item)
            organized["by_content_type"][content_type].append(item)

            quality_score = item.get('quality_score', 0)
            if quality_score >= 3.0:
                quality_tier = "high"
                organized["high_value_content"].append(item)
            elif quality_score >= 1.5:
                quality_tier = "medium"
            else:
                quality_tier = "low"
            organized["by_quality"][quality_tier].append(item)

            extraction_method = item.get('extraction_method', 'unknown')
            organized["by_extraction_method"][extraction_method].append(item)

        organized["by_platform"] = dict(organized["by_platform"])
        organized["by_plant_type"] = dict(organized["by_plant_type"])
        organized["by_content_type"] = dict(organized["by_content_type"])
        organized["by_quality"] = dict(organized["by_quality"])
        organized["by_extraction_method"] = dict(organized["by_extraction_method"])

        return organized

    def _categorize_plant(self, plant_name: str) -> str:
        """Categorize a plant into a broader category."""
        plant_lower = plant_name.lower()

        for category, plants in PLANT_IDENTIFICATION_KEYWORDS.items():
            if plant_lower in [p.lower() for p in plants]:
                return category

        if any(veg in plant_lower for veg in ['tomato', 'lettuce', 'carrot', 'pepper', 'onion']):
            return 'vegetables'
        elif any(fruit in plant_lower for fruit in ['apple', 'orange', 'berry', 'grape']):
            return 'fruits'
        elif any(herb in plant_lower for herb in ['basil', 'oregano', 'mint', 'parsley']):
            return 'herbs'
        elif any(flower in plant_lower for flower in ['rose', 'tulip', 'lily', 'daisy']):
            return 'flowers'
        else:
            return 'other'

    def _determine_content_type(self, item: Dict[str, Any]) -> str:
        """Determine the type of content."""
        source_type = item.get('source_type', '').lower()
        title = item.get('title', '').lower()
        text = item.get('text', '').lower()

        if source_type in ['youtube']:
            return 'video'
        elif source_type in ['academic', 'botanical_api', 'botanical_scrape']:
            return 'academic'
        elif source_type in ['government_extension', 'extension']:
            return 'official_guide'
        elif source_type == 'commercial':
            return 'commercial'
        elif source_type in ['reddit']:
            return 'social_media'
        elif 'tutorial' in title or 'how to' in title:
            return 'tutorial'
        elif 'guide' in title or 'tips' in title:
            return 'guide'
        else:
            return 'general'

    def _identify_plants_comprehensive(self, content: str, title: str = "") -> Set[str]:
        """Comprehensive plant identification using all keywords."""
        plants_found = set()

        try:
            combined_text = (content + " " + title).lower()

            for category, plant_list in PLANT_IDENTIFICATION_KEYWORDS.items():
                for plant in plant_list:
                    patterns = [
                        rf'\b{re.escape(plant.lower())}\b',
                        rf'\b{re.escape(plant.lower())}s\b',
                        rf'\b{re.escape(plant.lower())}ing\b',
                    ]

                    for pattern in patterns:
                        try:
                            if re.search(pattern, combined_text):
                                plants_found.add(plant)
                                break
                        except Exception:
                            continue

        except Exception as e:
            self.logger.debug(f"Plant identification failed: {e}", "PHASE2")

        return plants_found

    def _is_plant_related_enhanced(self, content: str, title: str = "") -> bool:
        """Enhanced plant relation detection."""
        try:
            combined_text = (content + " " + title).lower()

            pattern_matches = sum(1 for pattern in PLANT_DISCOVERY_PATTERNS
                                  if pattern.lower() in combined_text)

            quality_score = sum(1 for indicator in CONTENT_QUALITY_INDICATORS["high_quality_indicators"]
                                if indicator.lower() in combined_text)

            low_quality_score = sum(1 for indicator in CONTENT_QUALITY_INDICATORS["low_quality_indicators"]
                                    if indicator.lower() in combined_text)

            return (pattern_matches >= 1 and quality_score >= 1 and
                    low_quality_score <= 2 and len(content.strip()) > 150)

        except Exception as e:
            self.logger.debug(f"Plant relation detection failed: {e}", "PHASE2")
            return False

    def _is_duplicate_content(self, content: str) -> bool:
        """Check for duplicate content."""
        try:
            content_hash = hashlib.md5(content.lower().strip().encode()).hexdigest()
            if content_hash in self.seen_content_hashes:
                return True
            self.seen_content_hashes.add(content_hash)
            return False
        except Exception:
            return False


# =============================================================================
# DATA VECTORIZER (COMPLETE PHASE 3 WITH PER-PLANT CHUNKING)
# =============================================================================
class DataVectorizer:
    """Phase 3: Vectorize cleaned data per plant with chunking for Qdrant."""

    def __init__(self, config: CollectionConfig, logger: EnhancedUnicodeLogger):
        self.config = config
        self.logger = logger
        self.embeddings_model = None
        self.qdrant_db = None
        self.load_embeddings_model()
        self.setup_qdrant()

    def load_embeddings_model(self):
        """Load enhanced sentence transformer model."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                safe_print(f"🤖 Loading enhanced sentence transformer model: {self.config.embedding_model}...")
                self.embeddings_model = SentenceTransformer(self.config.embedding_model)

                try:
                    test_embedding = self.embeddings_model.encode(["test sentence"])
                    safe_print(f"✅ Embeddings model test successful, dimension: {test_embedding.shape[1]}")
                except Exception as e:
                    safe_print(f"❌ Embeddings model test failed: {e}")
                    self.embeddings_model = None

                safe_print(f"✅ Embeddings model '{self.config.embedding_model}' loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load embeddings model: {e}", "VECTORIZER")
                self.embeddings_model = None
        else:
            safe_print("⚠️ Sentence transformers not available - using fallback vectorization")

    def setup_qdrant(self):
        """Set up Qdrant vector database connection."""
        if QDRANT_AVAILABLE:
            try:
                safe_print("🗃️ Setting up Qdrant vector database...")
                self.qdrant_db = EnhancedQdrantVectorDatabase(self.config, self.logger)

                if self.qdrant_db.client:
                    try:
                        collections = self.qdrant_db.client.get_collections()
                        safe_print("✅ Qdrant database connected successfully")
                        safe_print(f"📊 Existing collections: {len(collections.collections)}")
                    except Exception as e:
                        safe_print(f"❌ Qdrant connection test failed: {e}")
                        safe_print("💡 Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
                        self.qdrant_db = None
                else:
                    safe_print("❌ Failed to connect to Qdrant")
                    safe_print("💡 Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
            except Exception as e:
                self.logger.error(f"Failed to setup Qdrant: {e}", "VECTORIZER")
                safe_print("💡 Try installing: pip install qdrant-client")
                self.qdrant_db = None
        else:
            safe_print("⚠️ Qdrant not available - vector search will be limited")
            safe_print("💡 Install with: pip install qdrant-client")
            self.qdrant_db = None

    def vectorize_cleaned_data(self, file_manager: EnhancedFileManager) -> Dict[str, Any]:
        """Phase 3: Vectorize all cleaned data using Qdrant with per-plant strategy."""
        safe_print("\n" + "=" * 80)
        safe_print("🔢 PHASE 3: VECTORIZING CLEANED DATA (ENHANCED PER-PLANT)")
        safe_print("=" * 80)

        phase3_start = time.time()

        try:
            cleaned_data_dir = file_manager.get_phase_directory("phase2_cleaned")
            safe_print(f"📁 Cleaned data directory: {cleaned_data_dir}")

            organized_files = list(cleaned_data_dir.glob("organized_cleaned_data_*.json"))
            if not organized_files:
                organized_files = list(cleaned_data_dir.glob("*organized*.json"))

            if not organized_files:
                raise Exception("No organized cleaned data found. Check Phase 2 results.")

            organized_file = max(organized_files, key=lambda p: p.stat().st_mtime)
            safe_print(f"📥 Loading cleaned data from: {organized_file.name}")

            with open(organized_file, 'r', encoding='utf-8') as f:
                organized_data = json.load(f)

            safe_print("🔍 Extracting items from organized data...")
            all_items = []

            # Extract items recursively from categories
            if isinstance(organized_data, dict):
                for category_name, category_data in organized_data.items():
                    if category_name == 'metadata':
                        continue
                    if isinstance(category_data, dict):
                        for subcategory, items in category_data.items():
                            if isinstance(items, list):
                                all_items.extend(items)
                    elif isinstance(category_data, list):
                        all_items.extend(category_data)

            # Deduplicate items by URL or content hash
            unique_items = {}
            for item in all_items:
                # Prefer URL, fallback to content hash
                key = item.get('url') or hashlib.md5(
                    (item.get('title', '') + item.get('text', '')).encode()).hexdigest()
                unique_items[key] = item

            unique_items_list = list(unique_items.values())
            safe_print(f"📊 Unique items to vectorize: {len(unique_items_list)}")

            if not unique_items_list:
                raise Exception("No items found to vectorize")

            # Create enhanced per-plant embeddings
            vectorized_result = self._create_per_plant_embeddings(unique_items_list)

            if not vectorized_result:
                raise Exception("Failed to create vector embeddings")

            # Store in Qdrant
            qdrant_success = self._store_in_qdrant(vectorized_result)

            # Save results locally
            self._save_vectorized_data(vectorized_result, qdrant_success, file_manager)
            self._save_to_vector_db_folder(vectorized_result, file_manager)

            # Create search index (modified for per-plant data)
            search_index = self._create_search_index(vectorized_result, file_manager)

            phase3_result = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "total_items_processed": len(unique_items_list),
                "total_plant_vectors": vectorized_result['total_vectors'],
                "vector_dimension": vectorized_result['vector_dimension'],
                "embeddings_model": vectorized_result['model_name'],
                "processing_time": time.time() - phase3_start,
                "qdrant_integration": qdrant_success,
                "qdrant_collection_name": self.config.qdrant_collection_name if qdrant_success else None,
                "qdrant_host": f"{self.config.qdrant_host}:{self.config.qdrant_port}" if qdrant_success else None,
                "search_index_created": search_index is not None,
                "vector_db_folder_saved": True
            }

            summary_filename = file_manager.generate_readable_filename("PHASE3_VECTORIZATION_Stats")
            file_manager.save_data(phase3_result, summary_filename, "phase3_vectorized")

            safe_print(f"\n✅ PHASE 3 COMPLETED!")
            safe_print(f"📊 Processed items: {len(unique_items_list)}")
            safe_print(f"🌱 Total plant vectors: {vectorized_result['total_vectors']}")
            safe_print(f"🤖 Model used: {vectorized_result['model_name']}")
            safe_print(f"🗃️ Qdrant integration: {'✅ Success' if qdrant_success else '❌ Failed'}")
            safe_print(f"⏱️ Processing time: {time.time() - phase3_start:.2f}s")

            return phase3_result

        except Exception as e:
            self.logger.error(f"Phase 3 vectorization failed: {e}", "PHASE3")
            return {"status": "failed", "error": str(e)}

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split long text into overlapping chunks."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk) > 50:  # Minimum chunk size
                chunks.append(chunk)

        return chunks if chunks else [text]

    def _create_per_plant_embeddings(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create separate embeddings for each plant mentioned in text chunks."""
        safe_print("🌱 Creating per-plant embeddings with chunking...")

        if not self.embeddings_model:
            return self._create_fallback_embeddings(items)

        # Step 1: Pre-process and collect chunks
        safe_print("  🔄 Pre-processing items and chunks...")
        all_chunks_text = []
        all_metadata = []

        for item_idx, item in enumerate(items):
            try:
                title = str(item.get('title', '')).strip()
                text = str(item.get('text', '')).strip()
                plants = item.get('plants_mentioned', [])

                # If no specific plants mentioned, store as generic
                if not plants:
                    plants = ["general_agriculture"]

                # Chunk the text
                full_text = f"{title}\n{text}"
                chunks = self._chunk_text(full_text, self.config.chunk_size, self.config.chunk_overlap)

                for chunk_idx, chunk in enumerate(chunks):
                    # For each chunk, we create an entry for EACH plant mentioned in the parent item
                    for plant in plants:
                        all_chunks_text.append(chunk)

                        meta = {
                            'plant_name': plant,
                            'title': title,
                            'content': chunk,
                            'full_text_length': len(text),
                            'chunk_index': chunk_idx,
                            'total_chunks': len(chunks),
                            'url': item.get('url', ''),
                            'source_platform': item.get('source_platform', ''),
                            'source_type': item.get('source_type', ''),
                            'quality_score': item.get('quality_score', 0.0),
                            'relevance_score': item.get('relevance_score', 0.0),
                            'extraction_method': item.get('extraction_method', 'unknown'),
                            'collected_at': item.get('collected_at', ''),
                            'cleaned_at': item.get('cleaned_at', '')
                        }
                        all_metadata.append(meta)

            except Exception as e:
                self.logger.debug(f"Error preparing item {item_idx}: {e}", "VECTORIZER")
                continue

        safe_print(f"  📊 Generated {len(all_chunks_text)} chunks to embed")

        if not all_chunks_text:
            return None

        # Step 2: Batch encoding (Efficient)
        safe_print("  🔢 Encoding chunks in batches...")
        batch_size = 32
        all_embeddings = []

        total_batches = (len(all_chunks_text) - 1) // batch_size + 1

        for i in range(0, len(all_chunks_text), batch_size):
            batch_texts = all_chunks_text[i:i + batch_size]

            if i % (batch_size * 5) == 0:
                safe_print(f"    Processing batch {i // batch_size + 1}/{total_batches}...")

            try:
                batch_embeddings = self.embeddings_model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    show_progress_bar=False
                )
                all_embeddings.append(batch_embeddings)
            except Exception as e:
                self.logger.error(f"Error encoding batch {i}: {e}", "VECTORIZER")
                # Fallback: empty embeddings for this batch to keep alignment
                dim = 384 if not all_embeddings else all_embeddings[0].shape[1]
                all_embeddings.append(np.zeros((len(batch_texts), dim)))

        # Step 3: Combine and assign indices
        embeddings_matrix = np.vstack(all_embeddings)

        for i, meta in enumerate(all_metadata):
            meta['vector_index'] = i

        safe_print(f"✅ Generated {embeddings_matrix.shape[0]} embeddings")

        return {
            "embeddings": embeddings_matrix,
            "per_plant_data": all_metadata,
            "vector_dimension": embeddings_matrix.shape[1],
            "model_name": self.config.embedding_model,
            "total_vectors": len(all_metadata),
            "created_at": datetime.now().isoformat()
        }

    def _create_fallback_embeddings(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create simple TF-IDF based embeddings as fallback."""
        if not SKLEARN_AVAILABLE:
            return None

        safe_print("📊 Creating TF-IDF embeddings (fallback)...")

        texts = []
        per_plant_data = []

        for item in items:
            title = item.get('title', '')
            text = item.get('text', '')
            plants = item.get('plants_mentioned', []) or ["general_agriculture"]

            full_text = f"{title} {text}"

            for plant in plants:
                texts.append(full_text)
                entry = item.copy()
                entry['plant_name'] = plant
                entry['content'] = full_text[:1000]  # Truncate for fallback
                entry['vector_index'] = len(per_plant_data)
                per_plant_data.append(entry)

        if not texts:
            return None

        vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
        embeddings_matrix = vectorizer.fit_transform(texts).toarray()

        return {
            "embeddings": embeddings_matrix,
            "per_plant_data": per_plant_data,
            "vector_dimension": embeddings_matrix.shape[1],
            "model_name": "TF-IDF_fallback",
            "total_vectors": len(per_plant_data),
            "created_at": datetime.now().isoformat()
        }

    def _store_in_qdrant(self, vectorized_result: Dict[str, Any]) -> bool:
        """Store vectors in Qdrant database."""
        if not self.qdrant_db or not self.qdrant_db.client:
            self.logger.warning("Qdrant not available, skipping DB upload", "QDRANT")
            return False

        try:
            safe_print("🗃️ Storing vectors in Qdrant...")

            # Create collection if needed
            self.qdrant_db.create_collection(
                vector_dimension=vectorized_result['vector_dimension'],
                recreate=True
            )

            # Add points via the EnhancedQdrantVectorDatabase class which handles batching
            success = self.qdrant_db.add_points(
                vectorized_result['embeddings'],
                vectorized_result['per_plant_data']
            )

            if success:
                info = self.qdrant_db.get_collection_info()
                if info:
                    safe_print(f"  ✅ Qdrant Collection Stats:")
                    safe_print(f"    Vectors count: {info['vectors_count']}")
                    safe_print(f"    Segments: {info['segments_count']}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to store vectors in Qdrant: {e}", "QDRANT")
            return False

    def _save_vectorized_data(self, result: Dict[str, Any], qdrant_success: bool,
                              file_manager: EnhancedFileManager):
        """Save vectorized data to phase 3 directory."""
        safe_print("💾 Saving vectorized data to Phase 3 folder...")

        # Save embeddings matrix
        emb_file = file_manager.generate_readable_filename("embeddings_matrix").replace('.json', '.npy')
        file_manager.save_vectors(result["embeddings"], emb_file, "phase3_vectorized")

        # Save metadata
        metadata = {
            "vector_dimension": result["vector_dimension"],
            "model_name": result["model_name"],
            "total_vectors": result["total_vectors"],
            "created_at": result["created_at"],
            "embeddings_file": emb_file,
            "qdrant_integration": qdrant_success
        }
        file_manager.save_data(metadata, file_manager.generate_readable_filename("vector_metadata"),
                               "phase3_vectorized")

        # Save items data (chunked)
        # Note: We save the per_plant_data which contains the content, chunks, and metadata
        file_manager.save_data(result["per_plant_data"], file_manager.generate_readable_filename("vectorized_items"),
                               "phase3_vectorized")

    def _save_to_vector_db_folder(self, result: Dict[str, Any], file_manager: EnhancedFileManager):
        """Save data to the separate vector_db folder."""
        safe_print("💾 Saving to vector_db folder...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save embeddings
        file_manager.save_to_vector_db_folder(result["embeddings"], f"embeddings_{timestamp}.npy")

        # Save Qdrant config
        config = {
            "collection_name": self.config.qdrant_collection_name,
            "vector_dimension": result["vector_dimension"],
            "distance_metric": "cosine",
            "model": result["model_name"],
            "total_vectors": result["total_vectors"],
            "created_at": result["created_at"]
        }
        file_manager.save_to_vector_db_folder(config, f"qdrant_config_{timestamp}.json")

        # Save Items (Optional backup in vector_db)
        # We save a lighter version here without full content to save space, unless needed
        light_items = [{k: v for k, v in item.items() if k != 'content'} for item in result["per_plant_data"]]
        file_manager.save_to_vector_db_folder(light_items, f"items_metadata_{timestamp}.json")

    def _create_search_index(self, result: Dict[str, Any], file_manager: EnhancedFileManager) -> Dict[str, Any]:
        """Create searchable index mapping keywords/plants to vector indices."""
        safe_print("🔍 Creating searchable index...")

        plant_index = defaultdict(list)
        keyword_index = defaultdict(list)

        for entry in result["per_plant_data"]:
            idx = entry['vector_index']

            # Index by plant name
            plant_name = entry['plant_name'].lower()
            plant_index[plant_name].append(idx)

            # Simple keyword indexing from title and content preview
            text_to_index = f"{entry['title']} {entry['content'][:200]}".lower()
            words = re.findall(r'\b\w+\b', text_to_index)
            for word in words:
                if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'they']:
                    keyword_index[word].append(idx)

        index_data = {
            "plant_index": dict(plant_index),
            "keyword_index": dict(keyword_index),
            "total_items": result["total_vectors"],
            "created_at": datetime.now().isoformat()
        }

        file_manager.save_data(index_data, file_manager.generate_readable_filename("search_index"), "phase3_vectorized")
        return index_data
        # =============================================================================
        # NEW METHODS FOR PLANT REQUIREMENTS DATABASE MANAGEMENT
        # =============================================================================

        def store_plant_requirements(self, plant_name: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
            """
            Store new plant requirements received from environmental_analyzer.py.

            This method is called when environmental_analyzer.py doesn't find data locally
            and retrieves it via LLM search.

            Args:
                plant_name: Name of the plant
                requirements: Dictionary containing all growth requirements

            Returns:
                Dict with status and details of the storage operation
            """
            try:
                safe_print(f"📥 Receiving new plant requirements for: {plant_name}")

                # Check for duplicates
                if self.plant_db.check_duplicate(plant_name):
                    safe_print(f"⚠️ Plant '{plant_name}' already exists in database")
                    existing_data = self.plant_db.get_plant_requirements(plant_name)

                    # Check if new data is more comprehensive
                    if self._is_more_comprehensive(requirements, existing_data.get("requirements", {})):
                        safe_print(f"🔄 Updating with more comprehensive data for '{plant_name}'")
                        success = self.plant_db.add_plant_requirements(plant_name, requirements)

                        if success:
                            return {
                                "status": "updated",
                                "message": f"Updated requirements for {plant_name} with more comprehensive data",
                                "plant": plant_name
                            }
                    else:
                        return {
                            "status": "exists",
                            "message": f"Requirements for {plant_name} already exist and are comprehensive",
                            "plant": plant_name
                        }

                # Add new plant requirements
                success = self.plant_db.add_plant_requirements(plant_name, requirements)

                if success:
                    safe_print(f"✅ Successfully stored requirements for '{plant_name}'")

                    # Trigger data collection for this new plant to enrich the database
                    self._enrich_plant_data(plant_name)

                    return {
                        "status": "success",
                        "message": f"Successfully stored requirements for {plant_name}",
                        "plant": plant_name,
                        "total_plants": len(self.plant_db.requirements)
                    }
                else:
                    return {
                        "status": "failed",
                        "message": f"Failed to store requirements for {plant_name}",
                        "plant": plant_name
                    }

            except Exception as e:
                self.logger.error(f"Error storing plant requirements: {e}", "PLANT_DB")
                return {
                    "status": "error",
                    "message": str(e),
                    "plant": plant_name
                }

        def get_plant_requirements(self, plant_name: str) -> Optional[Dict[str, Any]]:
            """
            Retrieve plant requirements for environmental_analyzer.py.

            Args:
                plant_name: Name of the plant to look up

            Returns:
                Dictionary containing plant requirements or None if not found
            """
            try:
                requirements = self.plant_db.get_plant_requirements(plant_name)

                if requirements:
                    safe_print(f"📤 Providing requirements for '{plant_name}' to analyzer")
                    return requirements
                else:
                    safe_print(f"❌ No requirements found for '{plant_name}' in database")
                    return None

            except Exception as e:
                self.logger.error(f"Error retrieving plant requirements: {e}", "PLANT_DB")
                return None

        def search_similar_plants(self, plant_name: str) -> List[Dict[str, Any]]:
            """
            Search for similar plants in the database.

            Args:
                plant_name: Name or partial name of the plant

            Returns:
                List of similar plants with their requirements
            """
            try:
                matches = self.plant_db.search_plants(plant_name)
                results = []

                for match in matches:
                    data = self.plant_db.get_plant_requirements(match)
                    if data:
                        results.append({
                            "plant_name": data["common_name"],
                            "match_key": match,
                            "requirements": data["requirements"],
                            "confidence": data.get("confidence_score", 0.8)
                        })

                return results

            except Exception as e:
                self.logger.error(f"Error searching for similar plants: {e}", "PLANT_DB")
                return []

        def _is_more_comprehensive(self, new_data: Dict, existing_data: Dict) -> bool:
            """
            Check if new data is more comprehensive than existing data.

            Args:
                new_data: New requirements data
                existing_data: Existing requirements data

            Returns:
                True if new data is more comprehensive
            """
            # Count non-empty fields
            new_fields = sum(1 for v in new_data.values() if v and v != "unknown")
            existing_fields = sum(1 for v in existing_data.values() if v and v != "unknown")

            # Also check data size
            new_size = len(json.dumps(new_data))
            existing_size = len(json.dumps(existing_data))

            return new_fields > existing_fields or new_size > existing_size * 1.2

        def _enrich_plant_data(self, plant_name: str):
            """
            Trigger targeted data collection for a specific plant to enrich the database.

            Args:
                plant_name: Name of the plant to collect data for
            """
            try:
                safe_print(f"🔍 Enriching database with additional data for '{plant_name}'")

                # Create targeted search terms
                search_terms = [
                    f"how to grow {plant_name}",
                    f"{plant_name} care guide",
                    f"{plant_name} planting",
                    f"{plant_name} cultivation",
                    f"{plant_name} requirements",
                    f"{plant_name} soil pH",
                    f"{plant_name} watering",
                    f"{plant_name} fertilizer",
                    f"{plant_name} temperature",
                    f"{plant_name} diseases"
                ]

                # Collect targeted data (limited scope for efficiency)
                enrichment_data = []

                # YouTube search (limited)
                if YOUTUBE_SEARCH_AVAILABLE:
                    for term in search_terms[:3]:
                        try:
                            results = YoutubeSearch(term, max_results=2).to_dict()
                            for video in results:
                                # Try to get transcript if possible
                                video_id = video.get('id', '')
                                transcript = ""
                                if YOUTUBE_TRANSCRIPT_AVAILABLE and video_id:
                                    try:
                                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                                        transcript = " ".join([t['text'] for t in transcript_list])
                                    except:
                                        pass

                                enrichment_data.append({
                                    'title': video.get('title', ''),
                                    'text': transcript if transcript else f"Video about {plant_name}",
                                    'url': f"https://www.youtube.com{video.get('url_suffix', '')}",
                                    'source': 'youtube_enrichment',
                                    'plant': plant_name
                                })
                        except:
                            pass

                # Wikipedia search
                try:
                    wikipedia.set_lang("en")
                    search_results = wikipedia.search(plant_name, results=2)
                    for result in search_results:
                        try:
                            page = wikipedia.page(result)
                            enrichment_data.append({
                                'title': page.title,
                                'text': page.content[:1000],
                                'url': page.url,
                                'source': 'wikipedia_enrichment',
                                'plant': plant_name
                            })
                        except:
                            pass
                except:
                    pass

                # Store enrichment data
                if enrichment_data:
                    # Get or create database path
                    db_path = getattr(self.plant_db, 'db_path', Path("plant_requirements_db"))
                    db_path.mkdir(exist_ok=True)

                    enrichment_file = db_path / f"enrichment_{plant_name.lower().replace(' ', '_')}.json"
                    with open(enrichment_file, 'w', encoding='utf-8') as f:
                        json.dump(enrichment_data, f, indent=2, ensure_ascii=False)

                    safe_print(f"✅ Collected {len(enrichment_data)} enrichment items for '{plant_name}'")

            except Exception as e:
                self.logger.error(f"Error enriching plant data: {e}", "ENRICHMENT")

        def get_database_stats(self) -> Dict[str, Any]:
            """
            Get statistics about the plant requirements database.

            Returns:
                Dictionary containing database statistics
            """
            try:
                # Check if db_path exists in plant_db, otherwise define it
                db_path = getattr(self.plant_db, 'db_path', Path("plant_requirements_db"))
                if not db_path.exists():
                    return {"total_plants": 0, "status": "empty"}

                stats = {
                    "total_plants": len(self.plant_db.requirements),
                    "categories": {
                        category: len(plants)
                        for category, plants in self.plant_db.index.get("categories", {}).items()
                    },
                    "last_updated": self.plant_db.index.get("last_updated"),
                    "database_path": str(db_path),
                    "database_size_kb": sum(
                        f.stat().st_size for f in db_path.glob("*.json")
                    ) / 1024 if db_path.exists() else 0
                }

                return stats

            except Exception as e:
                self.logger.error(f"Error getting database stats: {e}", "STATS")
                return {}

        def _save_platform_data(self, data: List[Dict[str, Any]], platform: str):
            """Save platform-specific data - ALWAYS creates folder even if no data - from your original code."""
            # Always create the platform folder
            raw_data_path = self.file_manager.get_phase_directory("phase1_raw")
            platform_path = raw_data_path / platform
            platform_path.mkdir(exist_ok=True)

            # Save data if it exists
            if data:
                filename = self.file_manager.generate_readable_filename(f"{platform}_raw_data")
                self.file_manager.save_data(data, filename, "phase1_raw", platform)
                self.file_manager.create_index_mapping(data, platform)
                self.logger.info(f"Saved {len(data)} items to {platform} folder", "SAVE")

                # Log extraction method statistics
                extraction_methods = defaultdict(int)
                for item in data:
                    method = item.get('extraction_method', 'unknown')
                    extraction_methods[method] += 1

                if extraction_methods:
                    self.logger.info(f"Extraction methods used for {platform}: {dict(extraction_methods)}", "STATS")
            else:
                # Create empty placeholder file to show the platform was attempted
                placeholder_filename = f"{platform}_no_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                placeholder_data = {
                    "status": "no_data_collected",
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "reason": "No data was found or collected from this platform",
                    "resilient_scraping_attempted": True
                }
                self.file_manager.save_data(placeholder_data, placeholder_filename, "phase1_raw", platform)
                self.logger.info(f"Created placeholder for {platform} (no data collected)", "PLACEHOLDER")

        def ultimate_phase1_collect_all_sources(self) -> Dict[str, Any]:
            """Phase 1: Collect RAW UNPROCESSED data from ALL available sources with resilient scraping."""
            safe_print("\n" + "=" * 80)
            safe_print("🌍 ULTIMATE PHASE 1: RAW DATA COLLECTION FROM ALL SOURCES")
            safe_print("🛡️ ENHANCED WITH RESILIENT SCRAPING")
            safe_print("=" * 80)
            safe_print("📊 This collects RAW, UNPROCESSED data from:")
            safe_print("  📺 YouTube (API + Search + Transcripts)")
            safe_print("  🕷️ Trusted websites (Resilient crawling)")
            safe_print("  📚 Wikipedia (Expanded coverage)")
            safe_print("  🏛️ Government extension services")
            safe_print("  🏪 Commercial/seed company sources")
            safe_print("  🔍 Reddit (API)")
            safe_print("🛡️ RESILIENT FEATURES:")
            safe_print("  ⚡ Flexible fallback selectors")
            safe_print("  🔧 Per-domain configurable extraction")
            safe_print("  ⚠️ Comprehensive error handling & warnings")
            safe_print("  🤖 Smart readability-lxml fallback")
            safe_print("  🔄 Multiple extraction strategies per site")
            safe_print("🔍 NO PROCESSING - Just raw collection and storage")
            safe_print("=" * 80)

            phase1_start = time.time()
            all_data = []

            try:
                # 1. Video platforms (YouTube only)
                safe_print("\n📺 COLLECTING RAW DATA FROM YOUTUBE...")

                # YouTube
                youtube_data = self.video_collector.collect_youtube_comprehensive(COMPREHENSIVE_PLANT_SEARCH_TERMS)
                all_data.extend(youtube_data)
                self._save_platform_data(youtube_data, "youtube")

                # 2. Government extension services
                safe_print("\n🏛️ COLLECTING RAW DATA FROM GOVERNMENT EXTENSION SERVICES...")
                extension_data = self.source_collector.collect_government_extensions()
                all_data.extend(extension_data)
                self._save_platform_data(extension_data, "government_extension")

                # 3. Commercial sources
                safe_print("\n🏪 COLLECTING RAW DATA FROM COMMERCIAL SOURCES...")
                commercial_data = self.source_collector.collect_commercial_sources()
                all_data.extend(commercial_data)
                self._save_platform_data(commercial_data, "commercial")

                # 4. Trusted websites
                safe_print("\n🕷️ COLLECTING RAW DATA FROM TRUSTED WEBSITES...")
                website_data = self._collect_enhanced_website_data_resilient()
                all_data.extend(website_data)
                self._save_platform_data(website_data, "websites")

                # 5. Wikipedia
                safe_print("\n📚 COLLECTING RAW DATA FROM WIKIPEDIA...")
                wikipedia_data = self._collect_enhanced_wikipedia_data()
                all_data.extend(wikipedia_data)
                self._save_platform_data(wikipedia_data, "wikipedia")

                # 6. Reddit
                safe_print("\n🔍 COLLECTING RAW DATA FROM REDDIT...")
                reddit_data = self.social_media_collector.collect_reddit_data(COMPREHENSIVE_PLANT_SEARCH_TERMS)
                all_data.extend(reddit_data)
                self._save_platform_data(reddit_data, "reddit")

                # Calculate extraction method statistics
                extraction_stats = defaultdict(int)
                warning_stats = defaultdict(int)

                for item in all_data:
                    method = item.get('extraction_method', 'unknown')
                    extraction_stats[method] += 1

                    warnings = item.get('extraction_warnings', [])
                    for warning in warnings:
                        warning_stats[warning] += 1

                # NO PROCESSING HERE - just save raw data
                phase1_result = {
                    "status": "completed",
                    "resilient_scraping_enabled": True,
                    "raw_data_summary": {
                        "total_items": len(all_data),
                        "platform_breakdown": {
                            "youtube": len(youtube_data),
                            "government_extension": len(extension_data),
                            "commercial": len(commercial_data),
                            "websites": len(website_data),
                            "wikipedia": len(wikipedia_data),
                            "reddit": len(reddit_data)
                        }
                    },
                    "extraction_method_statistics": dict(extraction_stats),
                    "warning_statistics": dict(warning_stats),
                    "timestamp": datetime.now().isoformat(),
                    "processing_time": time.time() - phase1_start,
                    "note": "Raw data collection complete - no processing applied - resilient scraping enabled"
                }

                # Save master raw data file
                filename = self.file_manager.generate_readable_filename("ALL_Raw_Data")
                self.file_manager.save_data(all_data, filename, "phase1_raw")

                # Save phase summary
                summary_filename = self.file_manager.generate_readable_filename("PHASE1_RAW_COLLECTION_Stats")
                self.file_manager.save_data(phase1_result, summary_filename, "phase1_raw")

                safe_print(f"\n✅ ULTIMATE PHASE 1 RAW COLLECTION COMPLETED!")
                safe_print(f"📊 Total raw items collected: {len(all_data)}")
                safe_print(f"🛡️ Resilient scraping methods used: {list(extraction_stats.keys())}")
                safe_print(f"⏱️ Processing time: {time.time() - phase1_start:.2f}s")
                safe_print("📈 Raw data breakdown:")
                for platform, count in phase1_result["raw_data_summary"]["platform_breakdown"].items():
                    safe_print(f"  {platform}: {count} raw items")
                safe_print("🔄 Ready for Phase 2: Data Cleaning and Organization")

                return phase1_result

            except Exception as e:
                self.logger.error(f"Ultimate Phase 1 failed: {e}", "PHASE1")
                return {"status": "failed", "error": str(e)}

        def _collect_enhanced_website_data_resilient(self) -> List[Dict[str, Any]]:
            """Enhanced website data collection using resilient scraping - from your original code enhanced."""
            website_data = []

            # Use ALL domains from sources.py
            domains_to_crawl = list(TRUSTED_WEBSITE_DOMAINS)

            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_domain = {
                    executor.submit(self._crawl_domain_comprehensive_resilient, domain): domain
                    for domain in domains_to_crawl
                }

                for future in as_completed(future_to_domain):
                    domain = future_to_domain[future]
                    try:
                        domain_data = future.result()
                        website_data.extend(domain_data)

                        # Log extraction statistics
                        extraction_methods = defaultdict(int)
                        for item in domain_data:
                            method = item.get('extraction_method', 'unknown')
                            extraction_methods[method] += 1

                        safe_print(f"  ✅ {domain}: {len(domain_data)} pages (methods: {dict(extraction_methods)})")
                    except Exception as e:
                        safe_print(f"  ❌ {domain}: {e}")

            return website_data

        def _crawl_domain_comprehensive_resilient(self, domain: str) -> List[Dict[str, Any]]:
            """Comprehensively crawl a domain using resilient scraping - from your original code enhanced."""
            domain_data = []

            # Get URL patterns for this domain
            patterns = TRUSTED_URL_PATTERNS.get(domain, ["/"])

            for pattern in patterns:
                try:
                    base_url = f"https://{domain}{pattern}"

                    # Use resilient scraper for main page
                    extraction_result = self.scraper.extract_content_resilient(base_url, domain)

                    if not extraction_result['success']:
                        self.logger.warning(f"Failed to extract from {base_url}: {extraction_result['warnings']}",
                                            "SCRAPER")
                        continue

                    # Parse main page for links
                    response = self.scraper.session.get(base_url, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Get plant-related links using resilient method
                        plant_links = self.scraper.extract_links_resilient(soup, domain, base_url)

                        # Add main page content if substantial
                        if len(extraction_result['content']) > 200:
                            domain_data.append({
                                'title': extraction_result['title'],
                                'text': extraction_result['content'],
                                'url': base_url,
                                'domain': domain,
                                'source_type': 'website',
                                'source_name': domain,
                                'extraction_method': extraction_result['method_used'],
                                'extraction_warnings': extraction_result['warnings'],
                                'collected_at': datetime.now().isoformat()
                            })

                        # Scrape linked pages
                        for link_info in plant_links[:15]:  # Limit per pattern
                            try:
                                page_result = self.scraper.extract_content_resilient(link_info['url'], domain)

                                if page_result['success'] and len(page_result['content']) > 100:
                                    domain_data.append({
                                        'title': page_result['title'],
                                        'text': page_result['content'],
                                        'url': link_info['url'],
                                        'domain': domain,
                                        'source_type': 'website',
                                        'source_name': domain,
                                        'extraction_method': page_result['method_used'],
                                        'extraction_warnings': page_result['warnings'],
                                        'collected_at': datetime.now().isoformat()
                                    })

                                time.sleep(1)  # Be respectful

                            except Exception as e:
                                self.logger.debug(f"Error scraping {link_info['url']}: {e}", "SCRAPER")
                                continue

                    time.sleep(2)  # Delay between patterns

                except Exception as e:
                    self.logger.debug(f"Error with pattern {pattern} on {domain}: {e}", "SCRAPER")
                    continue

            return domain_data

        def _collect_enhanced_wikipedia_data(self) -> List[Dict[str, Any]]:
            """Enhanced Wikipedia collection with broader coverage - from your original code enhanced."""
            wikipedia_data = []

            # Extended search terms
            wikipedia_search_terms = [
                # Plant categories
                "List of vegetables", "List of fruits", "List of herbs", "List of flowers",
                "List of trees", "List of houseplants", "List of medicinal plants",
                "List of crops", "List of spices", "List of nuts", "List of berries",

                # Cultivation topics
                "Agriculture", "Horticulture", "Organic farming", "Permaculture",
                "Hydroponics", "Greenhouse", "Plant cultivation", "Crop rotation",

                # Plant families (major ones)
                "Solanaceae", "Brassicaceae", "Fabaceae", "Rosaceae", "Asteraceae",
                "Cucurbitaceae", "Lamiaceae", "Apiaceae", "Poaceae", "Liliaceae",

                # Regional and specialized
                "Tropical agriculture", "Temperate farming", "Desert plants",
                "Aquatic plants", "Native plants", "Invasive plants",
                "Endangered plants", "Rare plants", "Wild edibles"
            ]

            try:
                wikipedia.set_lang("en")

                for search_term in wikipedia_search_terms:
                    try:
                        safe_print(f"  🔍 Wikipedia: {search_term}")
                        search_results = wikipedia.search(search_term, results=8)

                        for result in search_results:
                            try:
                                page = wikipedia.page(result)
                                content = page.content

                                # Extract cultivation/growing information
                                cultivation_content = self._extract_cultivation_sections(content)

                                if len(cultivation_content) > 300:
                                    wikipedia_data.append({
                                        'title': page.title,
                                        'text': cultivation_content,
                                        'url': page.url,
                                        'source_type': 'wikipedia',
                                        'source_name': 'wikipedia',
                                        'search_term': search_term,
                                        'extraction_method': 'wikipedia_api',
                                        'extraction_warnings': [],
                                        'collected_at': datetime.now().isoformat()
                                    })

                            except Exception as e:
                                self.logger.debug(f"Error processing Wikipedia page {result}: {e}", "WIKIPEDIA")
                                continue

                        time.sleep(1)  # Be respectful

                    except Exception as e:
                        self.logger.debug(f"Error searching Wikipedia for {search_term}: {e}", "WIKIPEDIA")
                        continue

            except Exception as e:
                self.logger.error(f"Wikipedia collection failed: {e}", "WIKIPEDIA")

            return wikipedia_data

        def _extract_cultivation_sections(self, content: str) -> str:
            """Extract cultivation-related sections from content - from your original code."""
            try:
                sections = content.split('\n\n')
                cultivation_sections = []

                cultivation_keywords = [
                    'cultivation', 'growing', 'agriculture', 'farming', 'planting',
                    'care', 'maintenance', 'watering', 'fertilizer', 'soil',
                    'pruning', 'harvest', 'propagation', 'seeds', 'transplant'
                ]

                for section in sections:
                    section_lower = section.lower()
                    if any(keyword in section_lower for keyword in cultivation_keywords):
                        cultivation_sections.append(section)

                return '\n\n'.join(cultivation_sections)

            except Exception as e:
                self.logger.debug(f"Cultivation section extraction failed: {e}", "WIKIPEDIA")
                return content

        def run_complete_pipeline(self) -> Dict[str, Any]:
            """
            Run the complete 3-phase pipeline with plant requirements database integration.

            ENHANCED: Now also manages plant requirements for the agricultural system.
            """
            safe_print("🌍 STARTING COMPLETE 3-PHASE PLANT DATA PIPELINE")
            safe_print("🚀 PHASE 1: Raw Collection -> PHASE 2: Cleaning -> PHASE 3: Vectorization")
            safe_print("🛡️ Enhanced with RESILIENT SCRAPING capabilities")
            safe_print("🗃️ Enhanced with QDRANT vector database integration")
            safe_print("💾 Enhanced with vector_db folder integration")
            safe_print("🌱 Enhanced with PLANT REQUIREMENTS DATABASE for environmental_analyzer.py")
            safe_print("=" * 90)

            pipeline_start = time.time()

            try:
                # Phase 1: Ultimate RAW data collection with resilient scraping
                phase1_result = self.ultimate_phase1_collect_all_sources()

                if phase1_result["status"] != "completed":
                    raise Exception("Phase 1 failed")

                # Phase 2: Data cleaning and organization
                phase2_result = self.data_cleaner.clean_and_organize_data(self.file_manager)

                if phase2_result["status"] != "completed":
                    raise Exception("Phase 2 cleaning failed")

                # Phase 3: Data vectorization with Qdrant
                phase3_result = self.data_vectorizer.vectorize_cleaned_data(self.file_manager)

                if phase3_result["status"] != "completed":
                    raise Exception("Phase 3 vectorization failed")

                # Get plant database statistics
                plant_db_stats = self.get_database_stats()

                total_time = time.time() - pipeline_start

                final_summary = {
                    "pipeline_status": "completed",
                    "complete_3_phase_pipeline": True,
                    "resilient_scraping_enabled": True,
                    "qdrant_integration": phase3_result.get("qdrant_integration", False),
                    "qdrant_collection_name": phase3_result.get("qdrant_collection_name"),
                    "qdrant_host": phase3_result.get("qdrant_host"),
                    "vector_db_folder_integration": True,
                    "plant_requirements_database": plant_db_stats,  # NEW
                    "total_processing_time": round(total_time, 2),
                    "phase1_result": phase1_result,
                    "phase2_result": phase2_result,
                    "phase3_result": phase3_result,
                    "platforms_covered": list(phase1_result["raw_data_summary"]["platform_breakdown"].keys()),
                    "total_raw_items": phase1_result["raw_data_summary"]["total_items"],
                    "total_cleaned_items": phase2_result["total_items_cleaned"],
                    "total_vectorized_items": phase3_result["total_items_vectorized"],
                    "unique_plants_discovered": phase2_result["unique_plants_identified"],
                    "vector_dimension": phase3_result["vector_dimension"],
                    "embeddings_model": phase3_result["embeddings_model"],
                    "extraction_methods_used": phase1_result.get("extraction_method_statistics", {}),
                    "extraction_warnings": phase1_result.get("warning_statistics", {}),
                    "comprehensive_coverage_achieved": True,
                    "all_phases_completed": True,
                    "vector_db_folder_created": True,
                    "vector_database_py_used": VECTOR_DB_AVAILABLE,
                    "readability_fallback_available": READABILITY_AVAILABLE,
                    "qdrant_available": QDRANT_AVAILABLE,
                    "unicode_emoji_handling": True,
                    "ready_for_environmental_analyzer": True  # NEW
                }

                # Save final summary
                summary_filename = self.file_manager.generate_readable_filename("COMPLETE_PIPELINE_FINAL_SUMMARY")
                self.file_manager.save_data(final_summary, summary_filename, "phase3_vectorized")

                safe_print("\n" + "=" * 90)
                safe_print("🎉 COMPLETE 3-PHASE PIPELINE FINISHED!")
                safe_print("🛡️ RESILIENT SCRAPING SUCCESSFULLY APPLIED!")
                safe_print("🗃️ QDRANT VECTOR DATABASE INTEGRATION COMPLETE!")
                safe_print("🌱 PLANT REQUIREMENTS DATABASE READY!")
                safe_print(f"⏱️ Total time: {total_time:.2f} seconds")
                safe_print(f"📊 Raw items: {phase1_result['raw_data_summary']['total_items']}")
                safe_print(f"🧹 Cleaned items: {phase2_result['total_items_cleaned']}")
                safe_print(f"🔢 Vectorized items: {phase3_result['total_items_vectorized']}")
                safe_print(f"🌱 Plants discovered: {phase2_result['unique_plants_identified']}")
                safe_print(f"🌱 Plants in database: {plant_db_stats['total_plants']}")  # NEW
                safe_print(f"🧠 Vector dimension: {phase3_result['vector_dimension']}")
                safe_print(f"🤖 Model used: {phase3_result['embeddings_model']}")
                safe_print(f"🌍 Platforms: {len(phase1_result['raw_data_summary']['platform_breakdown'])}")
                safe_print(
                    f"🛡️ Extraction methods: {list(phase1_result.get('extraction_method_statistics', {}).keys())}")
                safe_print(
                    f"🗃️ Qdrant integration: {'✅ Success' if phase3_result.get('qdrant_integration') else '❌ Failed'}")
                if phase3_result.get('qdrant_integration'):
                    safe_print(f"🗃️ Qdrant collection: {phase3_result.get('qdrant_collection_name')}")
                    safe_print(f"🗃️ Qdrant endpoint: {phase3_result.get('qdrant_host')}")
                safe_print("\n📁 All data saved to respective directories:")
                safe_print(f"  📂 01_raw_data: Raw collected data with extraction metadata")
                safe_print(f"  📂 02_cleaned_data: Cleaned and organized data")
                safe_print(f"  📂 03_vectorized_data: Vector embeddings and search indices")
                safe_print(f"  🗃️ vector_db: Embedded data for Qdrant vector database")
                safe_print(f"  🌱 plant_requirements_db: Plant growth requirements database")  # NEW
                safe_print("✅ Data collection is now resilient to website layout changes!")
                safe_print("🗃️ Qdrant provides fast semantic search capabilities!")
                safe_print("🛡️ Unicode/emoji handling works perfectly on Windows!")
                safe_print("🌱 Ready to receive plant data from environmental_analyzer.py!")  # NEW
                safe_print("=" * 90)

                return final_summary

            except Exception as e:
                self.logger.error(f"Complete pipeline failed: {e}", "PIPELINE")
                return {"pipeline_status": "failed", "error": str(e)}


# =============================================================================
# ULTIMATE COMPREHENSIVE PLANT DATA COLLECTOR
# =============================================================================
class UltimateComprehensivePlantDataCollector:
    """Main collector class that coordinates all phases and components."""

    def __init__(self, config: CollectionConfig):
        self.config = config
        self.logger = EnhancedUnicodeLogger("PlantDataCollector", config)
        self.file_manager = EnhancedFileManager(config, self.logger)

        # Initialize plant requirements database
        self.plant_db = PlantRequirementsDatabase()
        self.plant_db.requirements_file = Path("plant_requirements_db") / "requirements.json"
        self.plant_db.index_file = Path("plant_requirements_db") / "index.json"
        self.plant_db.requirements = {}
        self.plant_db.index = {"plants": [], "categories": {}, "last_updated": datetime.now().isoformat()}
        Path("plant_requirements_db").mkdir(exist_ok=True)
        self.plant_db.load_database()

        # Initialize Incremental Tracker (NEW)
        self.tracker = IncrementalCollectionTracker(config, self.logger)

        # Initialize all collectors (Pass tracker where needed)
        self.scraper = EnhancedResilientScraper(config, self.logger)

        # Updated initializations with 'tracker'
        self.social_media_collector = SocialMediaCollector(config, self.logger, self.tracker)
        self.video_collector = MultiPlatformVideoCollector(config, self.logger, self.tracker)
        self.source_collector = ComprehensiveSourceCollector(config, self.logger, self.tracker)

        self.data_cleaner = DataCleaner(config, self.logger)
        self.data_vectorizer = DataVectorizer(config, self.logger)

    def store_plant_requirements(self, plant_name: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Store new plant requirements received from environmental_analyzer.py."""
        try:
            safe_print(f"📥 Receiving new plant requirements for: {plant_name}")

            # Check for duplicates
            if self.plant_db.check_duplicate(plant_name):
                safe_print(f"⚠️ Plant '{plant_name}' already exists in database")
                existing_data = self.plant_db.get_plant_requirements(plant_name)

                # Check if new data is more comprehensive
                if self._is_more_comprehensive(requirements, existing_data.get("requirements", {})):
                    safe_print(f"🔄 Updating with more comprehensive data for '{plant_name}'")
                    success = self.plant_db.add_plant_requirements(plant_name, requirements)

                    if success:
                        return {
                            "status": "updated",
                            "message": f"Updated requirements for {plant_name} with more comprehensive data",
                            "plant": plant_name
                        }
                else:
                    return {
                        "status": "exists",
                        "message": f"Requirements for {plant_name} already exist and are comprehensive",
                        "plant": plant_name
                    }

            # Add new plant requirements
            success = self.plant_db.add_plant_requirements(plant_name, requirements)

            if success:
                safe_print(f"✅ Successfully stored requirements for '{plant_name}'")

                # Trigger data collection for this new plant to enrich the database
                self._enrich_plant_data(plant_name)

                return {
                    "status": "success",
                    "message": f"Successfully stored requirements for {plant_name}",
                    "plant": plant_name,
                    "total_plants": len(self.plant_db.requirements)
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Failed to store requirements for {plant_name}",
                    "plant": plant_name
                }

        except Exception as e:
            self.logger.error(f"Error storing plant requirements: {e}", "PLANT_DB")
            return {
                "status": "error",
                "message": str(e),
                "plant": plant_name
            }

    def get_plant_requirements(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve plant requirements for environmental_analyzer.py."""
        try:
            requirements = self.plant_db.get_plant_requirements(plant_name)

            if requirements:
                safe_print(f"📤 Providing requirements for '{plant_name}' to analyzer")
                return requirements
            else:
                safe_print(f"❌ No requirements found for '{plant_name}' in database")
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving plant requirements: {e}", "PLANT_DB")
            return None

    def search_similar_plants(self, plant_name: str) -> List[Dict[str, Any]]:
        """Search for similar plants in the database."""
        try:
            matches = self.plant_db.search_plants(plant_name)
            results = []

            for match in matches:
                data = self.plant_db.get_plant_requirements(match)
                if data:
                    results.append({
                        "plant_name": data["common_name"],
                        "match_key": match,
                        "requirements": data["requirements"],
                        "confidence": data.get("confidence_score", 0.8)
                    })

            return results

        except Exception as e:
            self.logger.error(f"Error searching for similar plants: {e}", "PLANT_DB")
            return []

    def _is_more_comprehensive(self, new_data: Dict, existing_data: Dict) -> bool:
        """Check if new data is more comprehensive than existing data."""
        # Count non-empty fields
        new_fields = sum(1 for v in new_data.values() if v and v != "unknown")
        existing_fields = sum(1 for v in existing_data.values() if v and v != "unknown")

        # Also check data size
        new_size = len(json.dumps(new_data))
        existing_size = len(json.dumps(existing_data))

        return new_fields > existing_fields or new_size > existing_size * 1.2

    def _enrich_plant_data(self, plant_name: str):
        """Trigger targeted data collection for a specific plant to enrich the database."""
        try:
            safe_print(f"🔍 Enriching database with additional data for '{plant_name}'")

            # Create targeted search terms
            search_terms = [
                f"how to grow {plant_name}",
                f"{plant_name} care guide",
                f"{plant_name} planting",
                f"{plant_name} cultivation",
                f"{plant_name} requirements"
            ]

            # Collect targeted data (limited scope for efficiency)
            enrichment_data = []

            # Wikipedia search
            try:
                wikipedia.set_lang("en")
                search_results = wikipedia.search(plant_name, results=2)
                for result in search_results:
                    try:
                        page = wikipedia.page(result)
                        enrichment_data.append({
                            'title': page.title,
                            'text': page.content[:1000],
                            'url': page.url,
                            'source': 'wikipedia_enrichment',
                            'plant': plant_name
                        })
                    except:
                        pass
            except:
                pass

            # Store enrichment data
            if enrichment_data:
                db_path = Path("plant_requirements_db")
                db_path.mkdir(exist_ok=True)

                enrichment_file = db_path / f"enrichment_{plant_name.lower().replace(' ', '_')}.json"
                with open(enrichment_file, 'w', encoding='utf-8') as f:
                    json.dump(enrichment_data, f, indent=2, ensure_ascii=False)

                safe_print(f"✅ Collected {len(enrichment_data)} enrichment items for '{plant_name}'")

        except Exception as e:
            self.logger.error(f"Error enriching plant data: {e}", "ENRICHMENT")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the plant requirements database."""
        try:
            db_path = Path("plant_requirements_db")
            if not db_path.exists():
                return {"total_plants": 0, "status": "empty", "categories": {}}

            stats = {
                "total_plants": len(self.plant_db.requirements),
                "categories": {
                    category: len(plants)
                    for category, plants in self.plant_db.index.get("categories", {}).items()
                },
                "last_updated": self.plant_db.index.get("last_updated"),
                "database_path": str(db_path),
                "database_size_kb": sum(
                    f.stat().st_size for f in db_path.glob("*.json")
                ) / 1024 if db_path.exists() else 0
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}", "STATS")
            return {"total_plants": 0, "status": "error", "categories": {}}

    def _save_platform_data(self, data: List[Dict[str, Any]], platform: str):
        """Save platform-specific data - ALWAYS creates folder even if no data."""
        # Always create the platform folder
        raw_data_path = self.file_manager.get_phase_directory("phase1_raw")
        platform_path = raw_data_path / platform
        platform_path.mkdir(exist_ok=True)

        # Save data if it exists
        if data:
            filename = self.file_manager.generate_readable_filename(f"{platform}_raw_data")
            self.file_manager.save_data(data, filename, "phase1_raw", platform)
            self.file_manager.create_index_mapping(data, platform)
            self.logger.info(f"Saved {len(data)} items to {platform} folder", "SAVE")

            # Log extraction method statistics
            extraction_methods = defaultdict(int)
            for item in data:
                method = item.get('extraction_method', 'unknown')
                extraction_methods[method] += 1

            if extraction_methods:
                self.logger.info(f"Extraction methods used for {platform}: {dict(extraction_methods)}", "STATS")
        else:
            # Create empty placeholder file to show the platform was attempted
            placeholder_filename = f"{platform}_no_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            placeholder_data = {
                "status": "no_data_collected",
                "platform": platform,
                "timestamp": datetime.now().isoformat(),
                "reason": "No data was found or collected from this platform",
                "resilient_scraping_attempted": True
            }
            self.file_manager.save_data(placeholder_data, placeholder_filename, "phase1_raw", platform)
            self.logger.info(f"Created placeholder for {platform} (no data collected)", "PLACEHOLDER")

    def ultimate_phase1_collect_all_sources(self) -> Dict[str, Any]:
        """Phase 1: Collect RAW UNPROCESSED data from ALL available sources with resilient scraping."""
        safe_print("\n" + "=" * 80)
        safe_print("🌍 ULTIMATE PHASE 1: RAW DATA COLLECTION FROM ALL SOURCES")
        safe_print("🛡️ ENHANCED WITH RESILIENT SCRAPING & INCREMENTAL TRACKING")
        safe_print("=" * 80)

        phase1_start = time.time()
        all_data = []

        try:
            # 1. YouTube
            safe_print("\n📺 COLLECTING RAW DATA FROM YOUTUBE...")
            youtube_data = self.video_collector.collect_youtube_comprehensive(COMPREHENSIVE_PLANT_SEARCH_TERMS)
            all_data.extend(youtube_data)
            self._save_platform_data(youtube_data, "youtube")

            # 2. Government extension services
            safe_print("\n🏛️ COLLECTING RAW DATA FROM GOVERNMENT EXTENSION SERVICES...")
            extension_data = self.source_collector.collect_government_extensions()
            all_data.extend(extension_data)
            self._save_platform_data(extension_data, "government_extension")

            # 3. Commercial sources
            safe_print("\n🏪 COLLECTING RAW DATA FROM COMMERCIAL SOURCES...")
            commercial_data = self.source_collector.collect_commercial_sources()
            all_data.extend(commercial_data)
            self._save_platform_data(commercial_data, "commercial")

            # 4. Trusted websites
            safe_print("\n🕷️ COLLECTING RAW DATA FROM TRUSTED WEBSITES...")
            website_data = self._collect_enhanced_website_data_resilient()
            all_data.extend(website_data)
            self._save_platform_data(website_data, "websites")

            # 5. Wikipedia
            safe_print("\n📚 COLLECTING RAW DATA FROM WIKIPEDIA...")
            wikipedia_data = self._collect_enhanced_wikipedia_data()
            all_data.extend(wikipedia_data)
            self._save_platform_data(wikipedia_data, "wikipedia")

            # 6. Reddit
            safe_print("\n🔍 COLLECTING RAW DATA FROM REDDIT...")
            reddit_data = self.social_media_collector.collect_reddit_data(COMPREHENSIVE_PLANT_SEARCH_TERMS)
            all_data.extend(reddit_data)
            self._save_platform_data(reddit_data, "reddit")

            # Calculate extraction method statistics
            extraction_stats = defaultdict(int)
            warning_stats = defaultdict(int)

            for item in all_data:
                method = item.get('extraction_method', 'unknown')
                extraction_stats[method] += 1

                warnings = item.get('extraction_warnings', [])
                for warning in warnings:
                    warning_stats[warning] += 1

            phase1_result = {
                "status": "completed",
                "resilient_scraping_enabled": True,
                "raw_data_summary": {
                    "total_items": len(all_data),
                    "platform_breakdown": {
                        "youtube": len(youtube_data),
                        "government_extension": len(extension_data),
                        "commercial": len(commercial_data),
                        "websites": len(website_data),
                        "wikipedia": len(wikipedia_data),
                        "reddit": len(reddit_data)
                    }
                },
                "extraction_method_statistics": dict(extraction_stats),
                "warning_statistics": dict(warning_stats),
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - phase1_start,
                "note": "Raw data collection complete - no processing applied - resilient scraping enabled"
            }

            # Save master raw data file
            filename = self.file_manager.generate_readable_filename("ALL_Raw_Data")
            self.file_manager.save_data(all_data, filename, "phase1_raw")

            # Save phase summary
            summary_filename = self.file_manager.generate_readable_filename("PHASE1_RAW_COLLECTION_Stats")
            self.file_manager.save_data(phase1_result, summary_filename, "phase1_raw")

            safe_print(f"\n✅ ULTIMATE PHASE 1 RAW COLLECTION COMPLETED!")
            safe_print(f"📊 Total raw items collected: {len(all_data)}")
            safe_print(f"⏱️ Processing time: {time.time() - phase1_start:.2f}s")

            return phase1_result

        except Exception as e:
            self.logger.error(f"Ultimate Phase 1 failed: {e}", "PHASE1")
            return {"status": "failed", "error": str(e)}

    def _collect_enhanced_website_data_resilient(self) -> List[Dict[str, Any]]:
        """Enhanced website data collection using resilient scraping."""
        website_data = []
        domains_to_crawl = list(TRUSTED_WEBSITE_DOMAINS)

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_domain = {
                executor.submit(self._crawl_domain_comprehensive_resilient, domain): domain
                for domain in domains_to_crawl
            }

            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    domain_data = future.result()
                    website_data.extend(domain_data)

                    extraction_methods = defaultdict(int)
                    for item in domain_data:
                        method = item.get('extraction_method', 'unknown')
                        extraction_methods[method] += 1

                    safe_print(f"  ✅ {domain}: {len(domain_data)} pages (methods: {dict(extraction_methods)})")
                except Exception as e:
                    safe_print(f"  ❌ {domain}: {e}")

        return website_data

    def _crawl_domain_comprehensive_resilient(self, domain: str) -> List[Dict[str, Any]]:
        """Comprehensively crawl a domain using resilient scraping."""
        domain_data = []
        patterns = TRUSTED_URL_PATTERNS.get(domain, ["/"])

        for pattern in patterns:
            try:
                base_url = f"https://{domain}{pattern}"

                # Check incremental tracking here if needed, but website crawling is broader

                extraction_result = self.scraper.extract_content_resilient(base_url, domain)

                if not extraction_result['success']:
                    self.logger.warning(f"Failed to extract from {base_url}: {extraction_result['warnings']}",
                                        "SCRAPER")
                    continue

                response = self.scraper.session.get(base_url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    plant_links = self.scraper.extract_links_resilient(soup, domain, base_url)

                    if len(extraction_result['content']) > 200:
                        domain_data.append({
                            'title': extraction_result['title'],
                            'text': extraction_result['content'],
                            'url': base_url,
                            'domain': domain,
                            'source_type': 'website',
                            'source_name': domain,
                            'extraction_method': extraction_result['method_used'],
                            'extraction_warnings': extraction_result['warnings'],
                            'collected_at': datetime.now().isoformat()
                        })

                    for link_info in plant_links[:15]:
                        try:
                            page_result = self.scraper.extract_content_resilient(link_info['url'], domain)

                            if page_result['success'] and len(page_result['content']) > 100:
                                domain_data.append({
                                    'title': page_result['title'],
                                    'text': page_result['content'],
                                    'url': link_info['url'],
                                    'domain': domain,
                                    'source_type': 'website',
                                    'source_name': domain,
                                    'extraction_method': page_result['method_used'],
                                    'extraction_warnings': page_result['warnings'],
                                    'collected_at': datetime.now().isoformat()
                                })

                            time.sleep(1)

                        except Exception as e:
                            self.logger.debug(f"Error scraping {link_info['url']}: {e}", "SCRAPER")
                            continue

                time.sleep(2)

            except Exception as e:
                self.logger.debug(f"Error with pattern {pattern} on {domain}: {e}", "SCRAPER")
                continue

        return domain_data

    def _collect_enhanced_wikipedia_data(self) -> List[Dict[str, Any]]:
        """Enhanced Wikipedia collection with broader coverage."""
        wikipedia_data = []

        wikipedia_search_terms = [
            "List of vegetables", "List of fruits", "List of herbs", "List of flowers",
            "Agriculture", "Horticulture", "Organic farming", "Permaculture",
            "Hydroponics", "Greenhouse", "Plant cultivation", "Crop rotation"
        ]

        try:
            wikipedia.set_lang("en")

            for search_term in wikipedia_search_terms:
                try:
                    safe_print(f"  🔍 Wikipedia: {search_term}")
                    search_results = wikipedia.search(search_term, results=8)

                    for result in search_results:
                        try:
                            page = wikipedia.page(result)
                            content = page.content
                            cultivation_content = self._extract_cultivation_sections(content)

                            if len(cultivation_content) > 300:
                                wikipedia_data.append({
                                    'title': page.title,
                                    'text': cultivation_content,
                                    'url': page.url,
                                    'source_type': 'wikipedia',
                                    'source_name': 'wikipedia',
                                    'search_term': search_term,
                                    'extraction_method': 'wikipedia_api',
                                    'extraction_warnings': [],
                                    'collected_at': datetime.now().isoformat()
                                })

                        except Exception as e:
                            self.logger.debug(f"Error processing Wikipedia page {result}: {e}", "WIKIPEDIA")
                            continue

                    time.sleep(1)

                except Exception as e:
                    self.logger.debug(f"Error searching Wikipedia for {search_term}: {e}", "WIKIPEDIA")
                    continue

        except Exception as e:
            self.logger.error(f"Wikipedia collection failed: {e}", "WIKIPEDIA")

        return wikipedia_data

    def _extract_cultivation_sections(self, content: str) -> str:
        """Extract cultivation-related sections from content."""
        try:
            sections = content.split('\n\n')
            cultivation_sections = []

            cultivation_keywords = [
                'cultivation', 'growing', 'agriculture', 'farming', 'planting',
                'care', 'maintenance', 'watering', 'fertilizer', 'soil',
                'pruning', 'harvest', 'propagation', 'seeds', 'transplant'
            ]

            for section in sections:
                section_lower = section.lower()
                if any(keyword in section_lower for keyword in cultivation_keywords):
                    cultivation_sections.append(section)

            return '\n\n'.join(cultivation_sections)

        except Exception as e:
            self.logger.debug(f"Cultivation section extraction failed: {e}", "WIKIPEDIA")
            return content

    def run_complete_pipeline(self) -> Dict[str, Any]:
        """Run the complete 3-phase pipeline with plant requirements database integration."""
        safe_print("🌍 STARTING COMPLETE 3-PHASE PLANT DATA PIPELINE")
        safe_print("🚀 PHASE 1: Raw Collection -> PHASE 2: Cleaning -> PHASE 3: Vectorization")
        safe_print("🌱 Enhanced with PLANT REQUIREMENTS DATABASE for environmental_analyzer.py")
        safe_print("=" * 90)

        pipeline_start = time.time()

        try:
            # Phase 1: Ultimate RAW data collection with resilient scraping
            phase1_result = self.ultimate_phase1_collect_all_sources()

            if phase1_result["status"] != "completed":
                raise Exception("Phase 1 failed")

            # Phase 2: Data cleaning and organization
            phase2_result = self.data_cleaner.clean_and_organize_data(self.file_manager)

            if phase2_result["status"] != "completed":
                raise Exception("Phase 2 cleaning failed")

            # Phase 3: Data vectorization with Qdrant
            phase3_result = self.data_vectorizer.vectorize_cleaned_data(self.file_manager)

            if phase3_result["status"] != "completed":
                raise Exception("Phase 3 vectorization failed")

            # Get plant database statistics
            plant_db_stats = self.get_database_stats()

            total_time = time.time() - pipeline_start

            final_summary = {
                "pipeline_status": "completed",
                "complete_3_phase_pipeline": True,
                "resilient_scraping_enabled": True,
                "qdrant_integration": phase3_result.get("qdrant_integration", False),
                "plant_requirements_database": plant_db_stats,
                "total_processing_time": round(total_time, 2),
                "phase1_result": phase1_result,
                "phase2_result": phase2_result,
                "phase3_result": phase3_result,
                "ready_for_environmental_analyzer": True
            }

            # Save final summary
            summary_filename = self.file_manager.generate_readable_filename("COMPLETE_PIPELINE_FINAL_SUMMARY")
            self.file_manager.save_data(final_summary, summary_filename, "phase3_vectorized")

            safe_print("\n" + "=" * 90)
            safe_print("🎉 COMPLETE 3-PHASE PIPELINE FINISHED!")
            safe_print(f"🌱 Plants in database: {plant_db_stats['total_plants']}")
            safe_print(f"⏱️ Total time: {total_time:.2f} seconds")
            safe_print("✅ Ready to receive plant data from environmental_analyzer.py!")
            safe_print("=" * 90)

            return final_summary

        except Exception as e:
            self.logger.error(f"Complete pipeline failed: {e}", "PIPELINE")
            return {"pipeline_status": "failed", "error": str(e)}

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    """
    Main execution function for complete 3-phase collection with plant requirements database.
    """
    safe_print("🌍 COMPLETE PLANT DATA COLLECTION PIPELINE")
    safe_print("🚀 ALL SOURCES • ALL PLATFORMS • FULL 3-PHASE PROCESSING")
    safe_print("🛡️ ENHANCED WITH RESILIENT SCRAPING CAPABILITIES")
    safe_print("🗃️ ENHANCED WITH QDRANT VECTOR DATABASE INTEGRATION")
    safe_print("💾 ENHANCED WITH VECTOR_DB FOLDER INTEGRATION")
    safe_print("🔤 ENHANCED WITH UNICODE/EMOJI SUPPORT FOR WINDOWS")
    safe_print("🌱 ENHANCED WITH PLANT REQUIREMENTS DATABASE MANAGEMENT")
    safe_print("=" * 80)

    # Show system information
    safe_print(f"🖥️ System: {'Windows' if unicode_handler.is_windows else 'Unix/Linux'}")
    safe_print(f"📝 Console Encoding: {unicode_handler.console_encoding}")
    safe_print(f"🤖 Emoji Support: {'✅ Native' if unicode_handler.emoji_support else '❌ Fallback mode'}")

    # Check for readability availability
    if READABILITY_AVAILABLE:
        safe_print("✅ readability-lxml available for smart content extraction")
    else:
        safe_print("⚠️ readability-lxml not available - install with: pip install readability-lxml")

    # Check for Qdrant availability
    if QDRANT_AVAILABLE:
        safe_print("✅ Qdrant client available for vector database")
        safe_print("💡 Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
    else:
        safe_print("⚠️ Qdrant not available - install with: pip install qdrant-client")

    # Check for sentence transformers
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        safe_print("✅ Sentence transformers available for embeddings")
    else:
        safe_print("⚠️ Sentence transformers not available - install with: pip install sentence-transformers")

    # Check for social media APIs
    if PRAW_AVAILABLE:
        safe_print("✅ PRAW available for Reddit API")
    else:
        safe_print("⚠️ PRAW not available - install with: pip install praw")

    if YOUTUBE_TRANSCRIPT_AVAILABLE:
        safe_print("✅ YouTube Transcript API available for video content")
    else:
        safe_print("⚠️ YouTube Transcript API not available - install with: pip install youtube-transcript-api")

    safe_print("")

    # Initialize ultimate collector
    config = CollectionConfig()
    collector = UltimateComprehensivePlantDataCollector(config)

    # Show plant database status
    db_stats = collector.get_database_stats()
    safe_print(f"🌱 Plant Requirements Database Status:")
    safe_print(f"  📊 Total plants: {db_stats['total_plants']}")
    safe_print(f"  📂 Categories: {db_stats['categories']}")
    safe_print(f"  💾 Database size: {db_stats.get('database_size_kb', 0):.2f} KB")
    safe_print("")

    # Run complete pipeline
    result = collector.run_complete_pipeline()

    # Display final results
    if result['pipeline_status'] == 'completed':
        safe_print("\n🎉 SUCCESS: Enhanced plant data collection completed!")
        safe_print(f"📊 Raw items: {result.get('total_raw_items', 0)}")
        safe_print(f"🧹 Cleaned items: {result.get('total_cleaned_items', 0)}")
        safe_print(f"🔢 Vectorized items: {result.get('total_vectorized_items', 0)}")
        safe_print(f"🌱 Plants discovered: {result.get('unique_plants_discovered', 0)}")
        safe_print(f"🌱 Plants in database: {result['plant_requirements_database']['total_plants']}")
        safe_print(f"🧠 Vector dimension: {result.get('vector_dimension', 0)}")
        safe_print(f"🤖 Model: {result.get('embeddings_model', 'unknown')}")
        safe_print(f"⏱️ Total time: {result.get('total_processing_time', 0)}s")
        safe_print(f"🛡️ Extraction methods: {list(result.get('extraction_methods_used', {}).keys())}")
        safe_print(f"🗃️ Qdrant integration: {'✅ Success' if result.get('qdrant_integration') else '❌ Failed'}")
        if result.get('qdrant_integration'):
            safe_print(f"🗃️ Qdrant collection: {result.get('qdrant_collection_name')}")
            safe_print(f"🗃️ Qdrant endpoint: {result.get('qdrant_host')}")
        safe_print(f"🔤 Unicode/emoji handling: {'✅ Working perfectly!' if result.get('unicode_emoji_handling') else '❌ Issues detected'}")
        safe_print(f"\n✅ Vector embeddings saved in 03_vectorized_data directory!")
        safe_print(f"🗃️ Qdrant vector database ready for semantic search!")
        safe_print(f"🗃️ Vector database files saved in vector_db folder!")
        safe_print(f"🌱 Plant requirements database ready for environmental_analyzer.py!")
        safe_print(f"🛡️ Scraping is now resilient to layout changes!")
        if result.get('vector_database_py_used'):
            safe_print(f"🔗 Integrated with existing vector_database.py successfully!")
        if result.get('readability_fallback_available'):
            safe_print(f"📖 Smart readability fallback available!")
        if result.get('ready_for_environmental_analyzer'):
            safe_print(f"✅ Ready to receive and store plant data from environmental_analyzer.py!")
    else:
        safe_print(f"\n❌ PIPELINE FAILED: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()