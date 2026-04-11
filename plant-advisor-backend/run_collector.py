"""
run_collector.py — Temporary standalone runner for data_collector.py
Run from: plant-advisor-backend/
    python run_collector.py
Delete this file after collection is done.
"""

import sys
import os

# ── Fix path so relative imports work ────────────────────────────────────────
# Add the backend root AND the app package root to sys.path
backend_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_root)
sys.path.insert(0, os.path.join(backend_root, "app"))

# ── Monkey-patch relative imports inside data_collector ───────────────────────
# data_collector.py uses: from .language_manager import LanguageManager
# We redirect that to the absolute path instead.
import importlib
import types

# Pre-load language_manager so the relative import resolves
import app.services.language_manager as _lm_module
import app.services.data_collector  # will fail on relative import — handled below

# Actually we load it manually to bypass the relative import issue
loader_path = os.path.join(backend_root, "app", "services", "data_collector.py")

# Create a fake "app.services" package namespace if needed
if "app" not in sys.modules:
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [os.path.join(backend_root, "app")]
    sys.modules["app"] = app_pkg

if "app.services" not in sys.modules:
    svc_pkg = types.ModuleType("app.services")
    svc_pkg.__path__ = [os.path.join(backend_root, "app", "services")]
    sys.modules["app.services"] = svc_pkg

# Load each service the collector depends on
from app.services import language_manager
sys.modules["app.services.language_manager"] = language_manager

# Now import the collector properly
from app.services.data_collector import main, CollectionConfig, UltimateComprehensivePlantDataCollector

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  PLANT DATA COLLECTOR — STANDALONE RUNNER")
    print("  This will populate: data/01_raw_data, 02_cleaned_data,")
    print("                      03_vectorized_data, vector_db")
    print("  It may take 10–60+ minutes depending on network speed.")
    print("=" * 70)
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Collection interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
