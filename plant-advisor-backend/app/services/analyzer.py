import os
import re
import logging
import asyncio
import sys
import json
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, AsyncGenerator
from io import StringIO

# Setup Logger
logger = logging.getLogger("plant_advisor")

# Import your existing business logic
try:
    from app.services.environmental_analyzer import EnvironmentalAnalyzer
    from app.services.data_collector import UltimateComprehensivePlantDataCollector, CollectionConfig
    from app.services.language_manager import LanguageManager
    from app.services.conditions import PlantConditionsCollector
except ImportError as e:
    logger.error(f"Import Error in analyzer.py: {e}")
    print(f"Import Error in analyzer.py: {e}")

class PlantAnalyzerService:
    def __init__(self):
        self.data_collector = self._initialize_data_system()
        self.api_key = os.getenv("OPENAI_API_KEY") 
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in .env")

    def _is_log_message(self, line: str) -> bool:
        """Filter out internal backend logs, letting LLM output pass through."""
        line_strip = line.strip()
        if not line_strip: 
            return False # Keep empty lines for formatting
        
        # Block lines that start with these specific system phrases output by safe_print
        system_phrases = [
            "Starting enhanced analysis workflow",
            "No plant name provided",
            "Checking database for:",
            "Translation:",
            "Found in JSON database:",
            "Found in Qdrant:",
            "Found ",
            "Combined database check:",
            "No data found",
            "Embeddings database check",
            "Qdrant database check",
            "Analyzing ",
            "AI analysis failed",
            "Triggering LLM search",
            "Calling LLM for internet search",
            "LLM search",
            "LLM response",
            "Storing new data",
            "Data stored in",
            "NPY storage",
            "JSON storage",
            "Database storage",
            "AI Response (",          # catches ALL variants: (GPT streaming live), (GROQ), etc.
            "LLM streaming",
            "LLM analysis",
            "Enhanced analysis error",
            "Error in complete analysis",
            "🤖 Calling GPT",
            "🔄 Falling back",
            "✅ GPT-4o",
            "✅ Groq",
            "❌ Groq",
            "🌐 [llm_client]",
            "DEBUG:",
            "Validating plant name:",
            "Country translated:",
            "Saved ",
            "Data dynamically stored in",
            "⚠️ Unrecognized country",
        ]
        
        for phrase in system_phrases:
            if line_strip.startswith(phrase):
                return True
            
        return False

    def _initialize_data_system(self):
        """Initialize the vector DB connection once at startup"""
        try:
            if 'CollectionConfig' not in globals():
                return None
                
            config = CollectionConfig()
            config.base_data_dir = "data" 
            collector = UltimateComprehensivePlantDataCollector(config)
            return collector
        except Exception as e:
            logger.error(f"Failed to init Data Collector: {e}")
            return None

    def run_analysis(self, raw_request_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Main entry point called by the API (Legacy non-streaming).
        """
        if not self.api_key:
            return {"error": "OpenAI API Key missing"}

        try:
            # Process conditions
            conditions_collector = PlantConditionsCollector()
            processed_conditions = conditions_collector.process_web_data(raw_request_data)
        except Exception as e:
            logger.error(f"Error processing conditions: {e}")
            raise Exception(f"Failed to process plant conditions: {e}")

        # Setup language manager
        selected_lang = raw_request_data.get("language", "en")
        lang_manager = LanguageManager()
        lang_manager.set_language(selected_lang)
        
        # Initialize analyzer
        analyzer = EnvironmentalAnalyzer(lang_manager, self.data_collector)
        analyzer.openai_api_key = self.api_key
        
        # Set openai.api_key for compatibility
        import openai
        openai.api_key = self.api_key

        logger.info(f"Starting analysis for session {session_id}")
        
        # Run analysis
        recommendations, stream_output = analyzer.analyze_conditions_with_stream(processed_conditions)

        if not recommendations:
            raise Exception("AI Analysis returned no results.")

        # Save report
        file_path = self.save_plant_results(
            processed_conditions,
            recommendations, 
            selected_lang, 
            stream_output,
            session_id
        )

        return {
            "session_id": session_id,
            "status": "completed",
            "plant_name": processed_conditions.get("plant_information", {}).get("plant_name"),
            "recommendations": recommendations,
            "file_path": str(file_path)
        }

    async def run_analysis_stream(self, raw_request_data: Dict[str, Any], session_id: str) -> AsyncGenerator[str, None]:
        """
        Stream analysis results using the actual environmental_analyzer running in a thread.
        """
        if not self.api_key:
            yield "❌ Error: OpenAI API Key missing. Please configure your API key."
            return

        try:
            # Process conditions
            conditions_collector = PlantConditionsCollector()
            processed_conditions = conditions_collector.process_web_data(raw_request_data)
            
            plant_info = processed_conditions.get("plant_information", {})
            plant_name = plant_info.get("plant_name", "Unknown Plant")
            
            # Setup language manager
            selected_lang = raw_request_data.get("language", "en")
            lang_manager = LanguageManager()
            lang_manager.set_language(selected_lang)
            
            # Initialize environmental analyzer
            analyzer = EnvironmentalAnalyzer(lang_manager, self.data_collector)
            analyzer.openai_api_key = self.api_key
            
            import openai
            openai.api_key = self.api_key
            
            # --- CRITICAL FIX: Run blocking code in a thread pool ---
            loop = asyncio.get_running_loop()
            
            # We use a mutable container to capture output from the thread
            capture_container = {
                "output_buffer": [], 
                "done": False, 
                "error": None,
                "recommendations": None,
                "stream_output": None
            }
            
            # Lock for thread safety
            buffer_lock = threading.Lock()
            
            # Override safe_print to capture output instead of printing
            module_name = 'app.services.environmental_analyzer'
            original_safe_print = getattr(sys.modules.get(module_name), 'safe_print', print)
            
            def custom_safe_print(msg):
                # Print to console for server debugging
                print(msg)
                # Add to buffer for web stream
                with buffer_lock:
                    capture_container["output_buffer"].append(str(msg))

            # Inject our capture function
            if module_name in sys.modules:
                sys.modules[module_name].safe_print = custom_safe_print
            
            def run_blocking_analysis():
                try:
                    # Run the actual analysis
                    recs, stream = analyzer.analyze_conditions_with_stream(processed_conditions)
                    capture_container["recommendations"] = recs
                    capture_container["stream_output"] = stream
                except Exception as e:
                    capture_container["error"] = str(e)
                    print(f"Error in analysis thread: {e}")
                finally:
                    capture_container["done"] = True

            # Start the heavy analysis in background thread
            loop.run_in_executor(None, run_blocking_analysis)
            
            # Stream the output as it happens
            last_processed_idx = 0
            
            last_line = ""
            seen_paragraphs = set()  # Track full paragraphs outside the loop
            
            while not capture_container["done"]:
                # Check for new output
                new_lines = []
                with buffer_lock:
                    if len(capture_container["output_buffer"]) > last_processed_idx:
                        new_lines = capture_container["output_buffer"][last_processed_idx:]
                        last_processed_idx = len(capture_container["output_buffer"])
                
                # Yield new lines to the stream (with aggressive deduplication)
                for line in new_lines:
                    if not self._is_log_message(line):
                        clean_text = self._format_line_for_web(line)
                        # Skip if identical to last line (exact duplicate)
                        if clean_text.strip() and clean_text.strip() == last_line.strip():
                            continue
                        
                        last_line = clean_text
                        
                        # Track paragraph content (normalize for comparison)
                        if clean_text.strip():
                            para = clean_text.strip().lower()[:80]
                            if para in seen_paragraphs:
                                continue
                            seen_paragraphs.add(para)
                        
                        yield clean_text + "\n"
                
                await asyncio.sleep(0.1)
            
            # Send any remaining output after completion
            new_lines = []
            with buffer_lock:
                if len(capture_container["output_buffer"]) > last_processed_idx:
                    new_lines = capture_container["output_buffer"][last_processed_idx:]
            
            for line in new_lines:
                if not self._is_log_message(line):
                    clean_text = self._format_line_for_web(line)
                    if clean_text.strip() and clean_text.strip() == last_line.strip():
                        continue
                    last_line = clean_text
                    if clean_text.strip():
                        para = clean_text.strip().lower()[:80]
                        if para in seen_paragraphs:
                            continue
                        seen_paragraphs.add(para)
                    yield clean_text + "\n"
                
            # Report errors if any
            if capture_container["error"]:
                yield f"\n\n❌ **Error during analysis:** {capture_container['error']}"

            # If we have recommendations, save results for PDF
            if capture_container["recommendations"]:
                full_text = "\n".join(capture_container["output_buffer"])
                await self._save_streaming_results(
                    session_id, 
                    plant_name, 
                    full_text, 
                    processed_conditions
                )

            # Restore original print function
            if module_name in sys.modules:
                sys.modules[module_name].safe_print = original_safe_print
                    
        except Exception as e:
            logger.error(f"Streaming analysis error: {e}", exc_info=True)
            yield f"\n\n❌ **Error during analysis:** {str(e)}"

    def _format_line_for_web(self, line: str) -> str:
        """Convert console output to web-friendly format"""
        # Remove ANSI color codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        line = ansi_escape.sub('', line)

        # Strip markdown code fences (```markdown, ```python, ``` etc.)
        stripped = line.strip()
        if stripped.startswith("```"):
            return ""  # Drop code fence lines entirely

        # Simple Markdown conversions
        if line.startswith("=" * 20):
            return "---"
        elif line.startswith("🎯 PHASE"):
            return f"## {line}"
        elif line.startswith("🔍") or line.startswith("📊"):
            return ""  # Skip these symbols in web output
            
        # Ignore backend operational logs from web UI stream
        if any(log in line for log in [
            "Validating plant name",
            "Saved", 
            "URLs to data/sources",
            "Data dynamically stored in Qdrant database",
            "Storing new data in databases"
        ]):
            return ""

        return line

    def _create_mock_lang_manager(self, lang_code: str):
        """Create a mock language manager"""
        class MockLangManager:
            def __init__(self, lang_code):
                self.lang_code = lang_code
                self.translations = self._load_translations()

            def _load_translations(self):
                return {
                    'proceed_comprehensive_search': 'Proceed with comprehensive search?',
                    'search_time_estimate': 'This search will take approximately 2 minutes.',
                    # Add dummy keys to prevent key errors
                    'phase_1_header': 'Phase 1', 'phase_2_header': 'Phase 2',
                    'analyzing_conditions': 'Analyzing...', 'searching_optimal_data': 'Searching...',
                    'no_data_found': 'No data found', 'database_contains': 'Database items:',
                    'items': 'items', 'comprehensive_search_available': 'Deep Search Available',
                    'target_plant': 'Target', 'estimated_time': 'Time',
                    'would_search_sources': 'Sources', 'starting_comprehensive': 'Starting...',
                    'ai_analyzing': 'AI Analyzing'
                }

            def get_text(self, key, **kwargs):
                text = self.translations.get(key, key.replace('_', ' ').title())
                if kwargs:
                    try: text = text.format(**kwargs)
                    except: pass
                return text

            def get_current_language(self): return self.lang_code
            
            def get_current_language_name(self):
                langs = {"en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic"}
                return langs.get(self.lang_code, "English")

            def get_ai_prompt_instructions(self):
                return """You are an expert agricultural AI advisor. Analyze conditions and provide practical advice."""

            def _get_text(self, key): return self.get_text(key)
        
        return MockLangManager(lang_code)

    async def _save_streaming_results(self, session_id: str, plant_name: str, content: str, conditions: Dict):
        """Save streaming results for PDF generation"""
        try:
            results_dir = Path("data/streaming_results")
            results_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = results_dir / f"{session_id}.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_id": session_id,
                    "plant_name": plant_name,
                    "content": content,
                    "conditions": conditions,
                    "timestamp": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving streaming results: {e}")

    def save_plant_results(self, conditions: Dict, recommendations: Any, language: str, 
                          stream_output: str, session_id: str) -> str:
        """Generates the .txt file in data/results/"""
        plant_info = conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "unknown_plant")
        
        results_dir = Path("data/results")
        results_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{plant_name.replace(' ', '_')}_{session_id}.txt"
        file_path = results_dir / filename

        content = self._create_report_content(
            plant_name, 
            plant_info.get("plant_variety", ""),
            conditions,
            recommendations,
            language,
            stream_output,
            datetime.now().strftime("%Y%m%d_%H%M%S")
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename

    def _create_report_content(self, plant_name: str, variety: str, conditions: Dict, 
                              recs: Any, lang: str, stream: str, ts: str) -> str:
        """Constructs the string for the text file."""
        report = []
        report.append(f"🌱 PLANT ANALYSIS REPORT: {plant_name} ({variety})")
        report.append(f"Date: {ts} | Language: {lang}")
        report.append("="*50 + "\n")
        report.append("📋 GROWING CONDITIONS: (See PDF for full details)")
        
        # Only dump stream output for text file
        if stream:
            report.append(stream)

        return "\n".join(report)

# Global Instance
analyzer_service = PlantAnalyzerService()