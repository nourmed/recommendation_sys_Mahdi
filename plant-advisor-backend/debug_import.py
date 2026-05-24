import sys
import traceback

with open("debug_output.txt", "w") as f:
    f.write("Starting import chain debug...\n")
    f.flush()

    try:
        f.write("Step 1: importing fastapi...\n"); f.flush()
        from fastapi import FastAPI

        f.write("Step 2: importing dotenv...\n"); f.flush()
        from dotenv import load_dotenv

        f.write("Step 3: importing schemas...\n"); f.flush()
        from app.schemas.models import AnalyzeRequest, AnalysisResponse, AnalysisResult

        f.write("Step 4: importing llm_client...\n"); f.flush()
        from app.services.llm_client import call_gpt

        f.write("Step 5: importing environmental_analyzer...\n"); f.flush()
        from app.services.environmental_analyzer import EnvironmentalAnalyzer

        f.write("Step 6: importing data_collector...\n"); f.flush()
        from app.services.data_collector import UltimateComprehensivePlantDataCollector, CollectionConfig

        f.write("Step 7: importing language_manager...\n"); f.flush()
        from app.services.language_manager import LanguageManager

        f.write("Step 8: importing conditions...\n"); f.flush()
        from app.services.conditions import PlantConditionsCollector

        f.write("Step 9: importing analyzer service...\n"); f.flush()
        from app.services.analyzer import analyzer_service

        f.write("Step 10: importing endpoints...\n"); f.flush()
        from app.api.endpoints import router

        f.write("ALL IMPORTS OK!\n")

    except Exception as e:
        f.write(f"\n\n=== ERROR ===\n{type(e).__name__}: {e}\n\n")
        f.write(traceback.format_exc())

print("Done - check debug_output.txt")
