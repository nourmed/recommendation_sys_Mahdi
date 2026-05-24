"""
environmental_analyzer.py
Plant care analysis engine with three-phase structured output.
Uses Qwen 2.5 7B (primary) and GPT-4.1 (fallback) for AI analysis.
Full-featured version with all original methods restored.
"""

import os
import re
import json
import time
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from app.services.llm_client import call_llm, call_llm_streaming, call_gpt, call_groq
except ImportError:
    try:
        from llm_client import call_llm, call_llm_streaming, call_gpt, call_groq
    except ImportError:
        call_llm = None
        call_llm_streaming = None
        call_gpt = None
        call_groq = None

logger = logging.getLogger("plant_advisor.environmental_analyzer")


def safe_print(message: str):
    """Safe print with fallback."""
    try:
        print(message)
    except Exception:
        pass


class EnvironmentalAnalyzer:
    """Analyzes plant growing conditions and generates structured recommendations."""

    def __init__(self, language_manager=None, data_collector=None):
        self.language_manager = language_manager or self._create_fallback_language_manager()
        self.data_collector = data_collector
        self.npy_database_path = None
        self.openai_api_key = None
        self.streaming_response = ""
        self.streaming_active = False
        self.full_llm_stream_output = ""

        if self.data_collector:
            if hasattr(self.data_collector, 'npy_database_path'):
                self.npy_database_path = self.data_collector.npy_database_path
            elif hasattr(self.data_collector, 'config'):
                config = self.data_collector.config
                if hasattr(config, 'npy_database_path'):
                    self.npy_database_path = config.npy_database_path

    def _create_fallback_language_manager(self):
        class FallbackLangManager:
            def get_ai_prompt_instructions(self):
                return "You are an expert agricultural AI advisor. Analyze conditions and provide practical advice."
            def get_current_language_name(self):
                return "English"
        return FallbackLangManager()

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def analyze_conditions(self, user_conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Main entry point - routes analysis based on user experience section."""
        safe_print("\nStarting enhanced analysis workflow...")

        try:
            user_section = user_conditions.get("user_section", "unknown")
            plant_info = user_conditions.get("plant_information", {})
            plant_name = plant_info.get("plant_name", "").strip()

            if not plant_name:
                safe_print("No plant name provided, using general analysis")
                plant_name = "general plants"

            # ── Step 1: Validate plant name ─────────────────────────────────
            safe_print(f"Validating plant name: {plant_name}")
            validation = self._validate_plant_name(plant_name)
            if not validation['valid'] and not user_conditions.get("ignore_typo", False):
                safe_print(f"Invalid plant name rejected: {plant_name}")
                # Stream an error message to the frontend instead of a report
                try:
                    lang = getattr(self.language_manager, 'current_language', 'en')
                    error_title = f"'{plant_name}' does not appear to be a valid plant name."
                    error_body = "Please check the spelling and try again. You can enter the plant name in any language or use the scientific name."
                    
                    if lang != 'en':
                        from deep_translator import GoogleTranslator
                        translator = GoogleTranslator(source='en', target=lang)
                        error_title = translator.translate(error_title)
                        error_body = translator.translate(error_body)
                        
                    safe_print(f"\n\n❌ **{error_title}**\n\n{error_body}")
                except Exception as e:
                    safe_print(
                        f"\n\n❌ **'{plant_name}' does not appear to be a valid plant name.**\n\n"
                        f"Please check the spelling and try again. "
                        f"You can enter the plant name in any language or use the scientific name."
                    )
                return None

            # Use the validated English name for all DB lookups
            english_plant_name = validation['english_name'] or plant_name

            safe_print(f"Checking database for: {english_plant_name}")
            database_result = self._strict_database_check(english_plant_name, user_conditions)

            if database_result["found"]:
                safe_print(f"Found {len(database_result.get('data', []))} relevant entries in database")
                return self._complete_analysis_with_existing_data(user_conditions, database_result)
            else:
                safe_print(f"No data found for '{english_plant_name}' in database")
                return self._trigger_llm_search_mode(english_plant_name, user_conditions)

        except Exception as e:
            safe_print(f"Enhanced analysis error: {e}")
            return self._fallback_original_analysis(user_conditions)

    def analyze_conditions_with_stream(self, user_conditions: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Run analysis and return both structured results and raw stream output."""
        result = self.analyze_conditions(user_conditions)
        stream_output = self.full_llm_stream_output
        return result if result else {}, stream_output

    # =========================================================================
    # DATABASE CHECKS
    # =========================================================================

    def _strict_database_check(self, plant_name: str, user_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check both JSON/embeddings and Qdrant databases for plant data."""
        original_plant_name = plant_name
        english_plant_name = self._translate_plant_name_to_english(plant_name)

        if english_plant_name != original_plant_name:
            safe_print(f"Translation: '{original_plant_name}' to '{english_plant_name}'")

        combined_data = []
        sources_found = []

        qdrant_result = self._check_qdrant_database(english_plant_name, user_conditions)
        if qdrant_result.get("found", False):
            safe_print(f"Found in Qdrant: {len(qdrant_result.get('data', []))} items")
            combined_data.extend(qdrant_result.get("data", []))
            sources_found.append("qdrant")
            
        embeddings_result = self._check_embeddings_database(english_plant_name, user_conditions)
        if embeddings_result.get("found", False):
            safe_print(f"Found in JSON database: {len(embeddings_result.get('data', []))} items")
            combined_data.extend(embeddings_result.get("data", []))
            sources_found.append("json_db")

        if combined_data:
            safe_print(f"Combined database check: {len(combined_data)} items from {sources_found}")
            return {
                "found": True,
                "data": combined_data,
                "sources": sources_found,
                "plant_name": english_plant_name,
                "summary": f"Found {len(combined_data)} entries from {', '.join(sources_found)}"
            }
        else:
            safe_print(f"No data found in any database for '{english_plant_name}'")
            return {"found": False, "data": [], "sources": [], "plant_name": english_plant_name}

    def _check_embeddings_database(self, plant_name: str, user_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check the JSON/embeddings database."""
        if not self.data_collector:
            return {"found": False, "data": []}

        try:
            if hasattr(self.data_collector, 'search_similar_plants'):
                results = self.data_collector.search_similar_plants(plant_name)
                if results and len(results) > 0:
                    return {"found": True, "data": results, "source": "embeddings_db"}
            elif hasattr(self.data_collector, 'search_plants'):
                results = self.data_collector.search_plants(plant_name)
                if results and len(results) > 0:
                    return {"found": True, "data": results, "source": "embeddings_db"}
            elif hasattr(self.data_collector, 'get_plant_requirements'):
                result = self.data_collector.get_plant_requirements(plant_name)
                if result:
                    return {"found": True, "data": [result], "source": "embeddings_db"}
        except Exception as e:
            safe_print(f"Embeddings database check error: {e}")

        return {"found": False, "data": []}

    def _check_qdrant_database(self, plant_name: str, user_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check Qdrant vector database with semantic search + keyword fallback."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchText, ScrollRequest
            client = QdrantClient(host="127.0.0.1", port=6333, timeout=15, check_compatibility=False)

            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if "plant_collection" not in collection_names:
                safe_print(f"Qdrant: collection not found")
                return {"found": False, "data": []}

            # --- Approach 1: Semantic vector search ---
            query_text = f"{plant_name} plant growing guide care requirements"
            query_vector = self._generate_real_embedding(query_text)

            try:
                results = client.search(
                    collection_name="plant_collection",
                    query_vector=query_vector,
                    limit=5,
                    score_threshold=0.3,
                )

                if results:
                    data = []
                    for hit in results:
                        payload = hit.payload
                        data.append({
                            "title": payload.get("title", "Unknown"),
                            "text": payload.get("content", ""),
                            "source": payload.get("source_platform", "qdrant"),
                            "quality_score": payload.get("quality_score", 70),
                            "url": payload.get("url", "")
                        })
                    return {"found": True, "data": data, "source": "qdrant_semantic"}
            except Exception as e:
                safe_print(f"Qdrant semantic search skipped/failed (using keyword fallback): {str(e)[:50]}")

            # --- Approach 2: Keyword payload filter fallback ---
            safe_print(f"Qdrant: trying keyword filter for '{plant_name}'")
            scroll_result = client.scroll(
                collection_name="plant_collection",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="plant_name",
                            match=MatchText(text=plant_name.lower())
                        )
                    ]
                ),
                limit=5,
                with_payload=True
            )
            
            keyword_hits = scroll_result[0] if scroll_result else []
            if keyword_hits:
                safe_print(f"Qdrant keyword filter found {len(keyword_hits)} results for '{plant_name}'")
                data = []
                for hit in keyword_hits:
                    payload = hit.payload
                    data.append({
                        "title": payload.get("title", "Unknown"),
                        "text": payload.get("content", ""),
                        "source": payload.get("source_platform", "qdrant"),
                        "quality_score": payload.get("quality_score", 70),
                        "url": payload.get("url", "")
                    })
                return {"found": True, "data": data, "source": "qdrant_keyword"}

        except Exception as e:
            safe_print(f"Qdrant database check error: {e}")

        return {"found": False, "data": []}

    def _generate_real_embedding(self, text: str) -> List[float]:
        """Generate a 768-dim embedding using BGE to match the rebuilt Qdrant collection."""
        # Always use BAAI/bge-base-en-v1.5 (768-dim) — must match the rebuild_qdrant.py model
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("BAAI/bge-base-en-v1.5")
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            safe_print(f"BGE embedding error: {e}")

        # Fallback: correct dimension zero vector (won't match but won't crash Qdrant)
        import numpy as np
        return np.zeros(768, dtype=np.float32).tolist()

    def _translate_plant_name_to_english(self, plant_name: str) -> str:
        """
        Translate plant name to English using GPT if it's not already English.
        Returns the English name, or the original if translation fails.
        """
        # Skip translation for English-only names (ASCII)
        try:
            plant_name.encode('ascii')
            return plant_name  # Already ASCII/English — no translation needed
        except UnicodeEncodeError:
            pass  # Contains non-ASCII characters — needs translation

        # Call GPT for translation
        try:
            if call_gpt is None:
                return plant_name
            prompt = (
                f"Translate the following plant name to English. "
                f"Return ONLY the English plant name, nothing else, no explanation.\n"
                f"Plant name: {plant_name}"
            )
            result = call_gpt(
                prompt,
                system_message="You are a botanical translator. Translate plant names to English only.",
                temperature=0.0,
                max_tokens=20
            )
            if result:
                english_name = result.strip().strip('"').strip("'").split('\n')[0]
                safe_print(f"Translated '{plant_name}' → '{english_name}'")
                return english_name
        except Exception as e:
            safe_print(f"Translation error: {e}")

        return plant_name

    def _translate_country_to_english(self, country_name: str) -> str:
        """
        Translate country name to English using GPT if it's not already English.
        """
        try:
            country_name.encode('ascii')
            return country_name
        except UnicodeEncodeError:
            pass

        try:
            if call_gpt is None:
                return country_name
            prompt = (
                f"Translate the following region or country name to English. "
                f"Return ONLY the English country name, nothing else, no explanation. "
                f"For example, 'المغرب' should be 'Morocco'.\n"
                f"Country name: {country_name}"
            )
            result = call_gpt(
                prompt,
                system_message="You are a geographic translator. Translate country/region names to standard English only.",
                temperature=0.0,
                max_tokens=20
            )
            if result:
                english_name = result.strip().strip('"').strip("'").split('\n')[0]
                safe_print(f"Country translated: '{country_name}' → '{english_name}'")
                return english_name
        except Exception as e:
            safe_print(f"Translation error: {e}")

        return country_name

    def _validate_plant_name(self, plant_name: str) -> Dict[str, Any]:
        """
        Validate that the given name is a real plant.
        Returns {'valid': True/False, 'message': str, 'english_name': str}
        """
        try:
            if call_gpt is None:
                return {'valid': True, 'english_name': plant_name, 'message': ''}

            prompt = (
                f"Is '{plant_name}' a real plant (any species, crop, herb, flower, tree, vegetable, fruit, etc.) in ANY language?\n"
                f"The user might input the name in French, Spanish, Arabic, or any other language (e.g., 'pomme' is valid because it means apple).\n"
                f"Answer with EXACTLY this format:\n"
                f"VALID: yes or no\n"
                f"ENGLISH: <English common name>\n"
                f"If not a plant, ENGLISH: unknown"
            )
            result = call_gpt(
                prompt,
                system_message="You are a botanist. Answer strictly in the requested format.",
                temperature=0.0,
                max_tokens=30
            )
            if result:
                lines = result.strip().lower().splitlines()
                valid = any('valid: yes' in l for l in lines)
                english_name = plant_name
                for l in lines:
                    if l.startswith('english:'):
                        english_name = l.replace('english:', '').strip().title()
                        break
                return {'valid': valid, 'english_name': english_name, 'message': ''}
        except Exception as e:
            safe_print(f"Plant validation error: {e}")

        return {'valid': True, 'english_name': plant_name, 'message': ''}  # fail-open

    def _validate_country(self, country: str) -> bool:
        """
        Quick check: is this a recognized country/region name?
        Uses a large built-in set — no LLM call needed.
        """
        if not country or country.strip().lower() in ('', 'unknown', 'not specified'):
            return True  # blank is OK

        known_countries = {
            'afghanistan','albania','algeria','andorra','angola','argentina','armenia','australia',
            'austria','azerbaijan','bahrain','bangladesh','belarus','belgium','belize','benin',
            'bolivia','bosnia','botswana','brazil','brunei','bulgaria','burkina faso','burundi',
            'cambodia','cameroon','canada','chad','chile','china','colombia','comoros','congo',
            'costa rica','croatia','cuba','cyprus','czech republic','czechia','denmark','djibouti',
            'dominican republic','dr congo','ecuador','egypt','el salvador','eritrea','estonia',
            'eswatini','ethiopia','fiji','finland','france','gabon','gambia','georgia','germany',
            'ghana','greece','guatemala','guinea','haiti','honduras','hungary','iceland','india',
            'indonesia','iran','iraq','ireland','israel','italy','ivory coast','jamaica','japan',
            'jordan','kazakhstan','kenya','kuwait','kyrgyzstan','laos','latvia','lebanon','lesotho',
            'liberia','libya','liechtenstein','lithuania','luxembourg','madagascar','malawi',
            'malaysia','maldives','mali','malta','mauritania','mauritius','mexico','moldova',
            'monaco','mongolia','montenegro','morocco','mozambique','myanmar','namibia','nepal',
            'netherlands','new zealand','nicaragua','niger','nigeria','north korea','north macedonia',
            'norway','oman','pakistan','panama','paraguay','peru','philippines','poland','portugal',
            'qatar','romania','russia','rwanda','saudi arabia','senegal','serbia','sierra leone',
            'singapore','slovakia','slovenia','somalia','south africa','south korea','south sudan',
            'spain','sri lanka','sudan','sweden','switzerland','syria','taiwan','tajikistan',
            'tanzania','thailand','togo','trinidad and tobago','tunisia','turkey','turkmenistan',
            'uganda','ukraine','united arab emirates','uae','united kingdom','uk','united states',
            'usa','us','uruguay','uzbekistan','venezuela','vietnam','yemen','zambia','zimbabwe',
            'palestine','kosovo','timor-leste','hong kong','macau',
            # Common regions/territories
            'scotland','wales','england','northern ireland','catalonia','quebec',
        }
        return country.strip().lower() in known_countries

    # =========================================================================
    # ANALYSIS PATHS
    # =========================================================================

    def _complete_analysis_with_existing_data(self, user_conditions: Dict[str, Any],
                                               database_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Complete analysis using existing database data."""
        try:
            plant_info = user_conditions.get("plant_information", {})
            plant_name = plant_info.get("plant_name", "unknown")

            safe_print(f"Analyzing {plant_name} with existing database data...")

            search_result = {
                "found": True,
                "data": database_result.get("data", []),
                "sources": database_result.get("sources", []),
                "summary": database_result.get("summary", "Database data available"),
                "search_method": "database_lookup"
            }

            plant_context = self._prepare_plant_context(search_result)

            ai_analysis = self._analyze_with_ollama_streaming(user_conditions, search_result, "basic")

            if not ai_analysis:
                safe_print("AI analysis failed, using fallback")
                ai_analysis = self._generate_fallback_analysis(user_conditions, search_result)

            recommendations = self._assemble_final_recommendations(user_conditions, ai_analysis, search_result)

            return recommendations

        except Exception as e:
            safe_print(f"Error in complete analysis: {e}")
            return self._fallback_original_analysis(user_conditions)

    def _trigger_llm_search_mode(self, plant_name: str, user_conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trigger LLM-based internet search when no database data exists."""
        try:
            safe_print(f"Triggering LLM search mode for: {plant_name}")

            search_prompt = self._create_llm_search_prompt(plant_name, user_conditions)
            system_message = "You are an expert botanist and plant care specialist."

            safe_print("Calling LLM for internet search...")
            llm_result = call_llm_streaming(search_prompt, system_message, temperature=0.3, max_tokens=2000)

            if llm_result.get("text"):
                response_text = llm_result["text"]
            elif llm_result.get("stream"):
                response_text = ""
                for chunk in llm_result["stream"]:
                    response_text += chunk
            else:
                safe_print("LLM search returned empty response")
                return self._fallback_original_analysis(user_conditions)

            if not response_text or len(response_text.strip()) < 50:
                safe_print("LLM search response too short")
                return self._fallback_original_analysis(user_conditions)

            search_data = self._parse_llm_search_response(response_text, plant_name)

            if search_data.get("success", False):
                self._store_in_real_databases(plant_name, search_data)

                search_result = {
                    "found": True,
                    "data": search_data.get("data", []),
                    "sources": ["llm_internet_search"],
                    "summary": f"LLM internet search completed for {plant_name}",
                    "search_method": "llm_internet",
                    "search_data": search_data.get("search_data", {})
                }

                plant_context = self._prepare_plant_context(search_result)
                ai_analysis = self._analyze_with_ollama_streaming(user_conditions, search_result, "recommendations")

                if not ai_analysis:
                    ai_analysis = self._generate_fallback_analysis(user_conditions, search_result)

                recommendations = self._assemble_final_recommendations(user_conditions, ai_analysis, search_result)
                return recommendations
            else:
                safe_print("LLM search data parsing failed")
                return self._fallback_original_analysis(user_conditions)

        except Exception as e:
            safe_print(f"LLM search mode error: {e}")
            return self._fallback_original_analysis(user_conditions)

    def _fallback_original_analysis(self, user_conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fallback analysis when everything else fails."""
        plant_info = user_conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "unknown plant")

        return {
            "ai_analysis": {
                "plant_specific_analysis": {
                    "target_plant": plant_name,
                    "suitability_score": 50,
                    "optimal_match": "unknown",
                    "key_considerations": [
                        f"Limited data available for {plant_name}",
                        "Consider consulting local gardening resources",
                        "Start with basic care and observe plant response"
                    ]
                },
                "growing_recommendations": {
                    "immediate_actions": ["Monitor plant health daily", "Ensure basic water and light needs"],
                    "optimal_setup": ["Research specific needs for this plant"],
                    "seasonal_adjustments": ["Adjust care based on seasonal changes"]
                }
            },
            "fallback_used": True,
            "message": f"Limited analysis available for {plant_name}. Consider providing more details."
        }

    def _generate_fallback_analysis(self, user_conditions: Dict[str, Any], search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback analysis when LLM fails but we have some data."""
        plant_info = user_conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "unknown plant")
        
        data_items = search_result.get("data", [])
        context_summary = ""
        if data_items:
            context_summary = data_items[0].get("text", "")[:500] if data_items[0].get("text") else ""
        
        return {
            "analysis_type": "fallback",
            "ai_response": f"""# Plant Care Analysis for {plant_name}

## Overview
Based on available database information, here are general care recommendations for {plant_name}.

## Database Information
{context_summary if context_summary else "Limited information available in database."}

## General Recommendations

### Immediate Actions
- Monitor plant health daily
- Ensure consistent watering based on soil moisture
- Verify adequate light exposure

### Optimal Setup
- Use well-draining soil appropriate for plant type
- Provide appropriate container size
- Maintain consistent environmental conditions

### Ongoing Care
- Adjust watering frequency based on season
- Monitor for pests and diseases
- Fertilize according to growth stage

## Note
This is a simplified analysis. For more detailed recommendations, please ensure database connectivity and try again.
""",
            "llm_source": "fallback_generator",
            "success": True
        }

    # =========================================================================
    # LLM SEARCH PROMPT
    # =========================================================================

    def _create_llm_search_prompt(self, plant_name: str, user_conditions: Dict[str, Any]) -> str:
        """Create prompt for LLM to search and collect plant growing data."""
        language_instructions = self.language_manager.get_ai_prompt_instructions()
        current_language = self.language_manager.get_current_language_name()

        prompt = f"""{language_instructions}

You are an expert botanist with comprehensive knowledge of plant care.

TARGET PLANT: {plant_name}
RESPONSE LANGUAGE: {current_language}

MISSION: Provide comprehensive growing information for {plant_name}.

RESPOND WITH JSON containing:
{{
    "plant_profile": {{
        "scientific_name": "scientific name",
        "common_names": ["common names"],
        "plant_type": "annual/perennial/etc",
        "origin": "native region"
    }},
    "optimal_conditions": {{
        "temperature": {{
            "daytime_range": "X-Y C",
            "nighttime_range": "X-Y C",
            "tolerance": "temperature tolerance notes"
        }},
        "humidity": {{
            "ideal_range": "X-Y%",
            "tolerance": "humidity tolerance notes"
        }},
        "light": {{
            "type": "full sun/partial shade/etc",
            "duration": "X-Y hours/day",
            "intensity": "description"
        }},
        "soil": {{
            "type": "soil type",
            "ph_range": "X.X-X.X",
            "drainage": "drainage requirements"
        }},
        "watering": {{
            "frequency": "watering frequency",
            "method": "watering method",
            "water_quality": "water preferences"
        }},
        "nutrients": {{
            "fertilizer_type": "recommended fertilizer",
            "application_schedule": "feeding schedule"
        }}
    }},
    "expert_tips": [
        "tip 1",
        "tip 2",
        "tip 3"
    ],
    "sources_consulted": [
        "https://example.com/plant-info",
        "https://example.com/care-guide"
    ]
}}

All text must be in {current_language}. Provide accurate, specific information."""

        return prompt

    def _parse_llm_search_response(self, response_text: str, plant_name: str) -> Dict[str, Any]:
        """Parse LLM search response into structured data."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                
                # Check for sources and save them to sources.txt
                sources = data.get("sources_consulted", [])
                if sources:
                    sources_file = Path("data") / "sources.txt"
                    try:
                        with open(sources_file, "a", encoding="utf-8") as f:
                            f.write(f"--- Sources for {plant_name} ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ---\n")
                            for source in sources:
                                f.write(f"{source}\n")
                            f.write("\n")
                        safe_print(f"✅ Saved {len(sources)} URLs to data/sources.txt")
                    except Exception as e:
                        safe_print(f"⚠️ Failed to save sources to file: {e}")

                return {
                    "success": True,
                    "search_data": data,
                    "data": [{
                        "title": f"Growing Guide for {plant_name}",
                        "text": json.dumps(data, indent=2)[:2000],
                        "source": "llm_internet_search",
                        "plants_mentioned": [plant_name],
                        "quality_score": 85,
                        "date_added": datetime.now().isoformat(),
                        "content_type": "llm_generated",
                        "search_method": "llm_internet"
                    }]
                }
        except Exception as e:
            safe_print(f"LLM response parsing error: {e}")

        return {
            "success": False,
            "error": "Failed to parse LLM response",
            "raw_response": response_text[:500]
        }

    def _store_in_real_databases(self, plant_name: str, llm_search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Store new data in vector databases."""
        try:
            safe_print("Storing new data in databases...")
            search_data = llm_search_result.get("search_data", {})

            storage_items = [{
                "title": f"Growing Data for {plant_name}",
                "text": json.dumps(search_data, indent=2)[:1500],
                "source": "llm_internet_search",
                "plants_mentioned": [plant_name],
                "quality_score": 85,
                "date_added": datetime.now().isoformat(),
                "content_type": "growing_data",
                "search_method": "llm_internet"
            }]

            stored_count = 0

            # 1. QDRANT DATABASE UPSERT
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import PointStruct
                import uuid
                
                client = QdrantClient(host="127.0.0.1", port=6333, check_compatibility=False)
                collections = client.get_collections()
                collection_names = [c.name for c in collections.collections]
                
                if "plant_collection" in collection_names:
                    point_id = str(uuid.uuid4())
                    embedding = self._generate_real_embedding(plant_name)
                    payload = {
                        "title": f"Growing Data for {plant_name}",
                        "content": json.dumps(search_data, indent=2)[:1500],
                        "source_platform": "llm_internet_search",
                        "plant_name": plant_name,
                        "quality_score": 85,
                        "url": "",
                        "date_added": datetime.now().isoformat()
                    }
                    client.upsert(
                        collection_name="plant_collection",
                        points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
                    )
                    stored_count += 1
                    safe_print("Data dynamically stored in Qdrant database ✅")
            except Exception as e:
                safe_print(f"Qdrant storage error: {e}")

            if self.npy_database_path:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    embedding = np.random.rand(768).astype(np.float32)
                    npy_file = Path(self.npy_database_path) / f"{plant_name.replace(' ', '_')}_{timestamp}.npy"
                    np.save(npy_file, np.array([embedding]))
                    stored_count += 1
                    safe_print("Data stored in NPY database")
                except Exception as e:
                    safe_print(f"NPY storage error: {e}")

            if self.data_collector:
                try:
                    for item in storage_items:
                        if hasattr(self.data_collector, 'add_items'):
                            self.data_collector.add_items([item])
                        elif hasattr(self.data_collector, 'store_item'):
                            self.data_collector.store_item(item)
                    stored_count += 1
                    safe_print("Data stored in JSON database")
                except Exception as e:
                    safe_print(f"JSON storage error: {e}")

            return {"success": stored_count > 0, "stored_count": stored_count}

        except Exception as e:
            safe_print(f"Database storage error: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # CONTEXT PREPARATION
    # =========================================================================

    def _prepare_plant_context(self, search_result: Dict[str, Any]) -> str:
        """Prepare context from search results."""
        if not search_result.get("found"):
            return "Limited plant-specific data available in local database."

        plant_data = search_result.get("data", [])

        structured_info = []
        articles = []

        for item in plant_data:
            if item.get("is_article", False):
                articles.append(item)
            else:
                structured_info.append(item)

        context_parts = []

        if structured_info:
            context_parts.append("=== DATABASE FACTS (HIGH CONFIDENCE) ===")
            for i, item in enumerate(structured_info[:3]):
                title = item.get("title", f"Fact {i + 1}")
                content = item.get("text", "")[:500]
                context_parts.append(f"- {title}: {content}\n")

        if articles:
            context_parts.append("=== EXPERT ARTICLES ===")
            for i, item in enumerate(articles[:5]):
                title = item.get("title", f"Article {i + 1}")
                content = item.get("text", "")[:400]
                source = item.get("source", "Unknown")
                context_parts.append(f"- [Source: {source}] {title}: {content}\n")

        return "\n".join(context_parts) if context_parts else "No additional plant database context available."

    def _analyze_with_ollama_streaming(self, user_conditions: Dict[str, Any], search_result: Dict[str, Any],
                                       analysis_type: str = "basic") -> Optional[Dict[str, Any]]:
        """Call LLM with unified prompt to generate AI analysis."""
        try:
            plant_context = self._prepare_plant_context(search_result)
            prompt = self._create_unified_prompt(user_conditions, plant_context, search_result)

            # Inject invalid country warning into the prompt if flagged
            invalid_country = user_conditions.get('_invalid_country')
            if invalid_country:
                prompt += (
                    f"\n\n⚠️ IMPORTANT NOTE FOR REPORT: The user entered '{invalid_country}' as their country, "
                    f"which could not be recognized as a valid country name. "
                    f"Please include a visible warning in the report header stating: "
                    f"'The country name \"{invalid_country}\" was not recognized. "
                    f"Geographic and climate recommendations may be inaccurate. "
                    f"Please re-enter a valid country name for precise advice.'"
                )

            system_message = "You are an expert botanist, horticulturist, and plant-care analyst."

            llm_result = call_llm_streaming(prompt, system_message, temperature=0.7, max_tokens=6500)

            # Handle both text (qwen/groq non-streaming) and generator (gpt/groq streaming)
            if llm_result.get("text"):
                response_text = llm_result["text"]
                source_label = llm_result.get("source", "llm").upper()
                safe_print(f"AI Response ({source_label}):")
                for line in response_text.split("\n"):
                    safe_print(line)
            elif llm_result.get("stream"):
                response_text = ""
                source_label = llm_result.get("source", "llm").upper()
                safe_print(f"AI Response ({source_label} streaming live):")
                line_buffer = ""
                for chunk in llm_result["stream"]:
                    response_text += chunk
                    line_buffer += chunk
                    if "\n" in line_buffer:
                        lines = line_buffer.split("\n")
                        for line in lines[:-1]:
                            safe_print(line)
                        line_buffer = lines[-1]
                if line_buffer:
                    safe_print(line_buffer)
            else:
                safe_print("LLM streaming returned empty response")
                return None

            if not response_text or len(response_text.strip()) < 50:
                safe_print("LLM response too short or empty")
                return None

            # Calculate and append token cost estimation
            try:
                # Approximate 1 token = ~4 chars
                total_in_tokens = (len(prompt) + len(system_message)) // 4
                total_out_tokens = len(response_text) // 4
                
                # Rough estimates based on general modern models (e.g. gpt-4o-mini)
                # $0.15 per 1M input, $0.60 per 1M output
                cost_in = (total_in_tokens / 1_000_000) * 0.150
                cost_out = (total_out_tokens / 1_000_000) * 0.600
                total_cost = cost_in + cost_out

                token_report = (
                    f"\n\n─────────────────────────────────────────────────────\n"
                    f"### 💰 COST & TOKEN ESTIMATION\n"
                    f"- **Input Tokens:** ~{total_in_tokens:,}\n"
                    f"- **Output Tokens:** ~{total_out_tokens:,}\n"
                    f"- **Estimated Cost:** ~${total_cost:.5f} USD\n"
                )
                
                response_text += token_report
                
                # Always immediately pipe the report to the frontend via SSE
                lines = token_report.split("\n")
                for line in lines:
                    safe_print(line)
                        
            except Exception as e:
                safe_print(f"Token estimation error: {e}")

            return {
                "analysis_type": analysis_type,
                "ai_response": response_text,
                "llm_source": llm_result["source"],
                "success": True
            }

        except Exception as e:
            safe_print(f"LLM analysis error: {e}")
            return None

    def _assemble_final_recommendations(self, user_conditions: Dict[str, Any], ai_analysis: Dict[str, Any],
                                        search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble the final recommendations from AI analysis."""
        plant_info = user_conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "unknown")
        plant_variety = plant_info.get("plant_variety", "") or ""
        scientific_name = plant_info.get("scientific_name", "") or ""

        user_section = user_conditions.get("user_section", "unknown")
        if user_section == "has_experience":
            management = user_conditions.get("human_practices", {})
            experience = management.get("experience_level", "intermediate")
            time_commitment = management.get("time_commitment_weekly_hours", "moderate")
        else:
            experience = "beginner"
            basic_prefs = user_conditions.get("basic_preferences", {})
            time_commitment = basic_prefs.get("time_availability", "moderate")

        planting_type = user_conditions.get("planting_type", "unknown")
        growing_location = user_conditions.get("growing_location", "unknown")

        recommendations = {
            "success": True,
            "plant_information": {
                "plant_name": plant_name,
                "plant_variety": plant_variety,
                "scientific_name": scientific_name,
                "planting_type": planting_type,
                "growing_location": growing_location
            },
            "ai_analysis": ai_analysis.get("ai_response", "") if ai_analysis else "",
            "ai_response": ai_analysis.get("ai_response", "") if ai_analysis else "",
            "llm_source": ai_analysis.get("llm_source", "unknown") if ai_analysis else "unknown",
            "database_info": {
                "found": search_result.get("found", False),
                "sources": search_result.get("sources", []),
                "items_found": len(search_result.get("data", []))
            },
            "user_profile": {
                "experience_level": experience,
                "time_commitment": time_commitment,
                "user_section": user_section
            },
            "growing_recommendations": self._generate_growing_recommendations(user_conditions, ai_analysis),
            "success_probabilities": self._calculate_success_probabilities(user_conditions, ai_analysis or {}),
            "tracking_suggestions": self._generate_tracking_suggestions(user_conditions, ai_analysis or {}),
            "milestone_alerts": self._generate_milestone_alerts(user_conditions, ai_analysis or {}),
            "encouragement_timeline": self._generate_encouragement_timeline(user_conditions, ai_analysis or {})
        }

        return recommendations

    def _generate_growing_recommendations(self, user_conditions: Dict[str, Any],
                                          ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured growing recommendations."""
        plant_info = user_conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "unknown")

        return {
            "plant_name": plant_name,
            "immediate_actions": [
                "Monitor plant health daily",
                "Ensure consistent watering schedule",
                "Check light requirements are met"
            ],
            "optimal_setup": [
                "Verify soil conditions match plant needs",
                "Ensure proper drainage",
                "Maintain appropriate temperature range"
            ],
            "seasonal_adjustments": [
                "Adjust watering frequency based on season",
                "Monitor temperature changes",
                "Consider supplemental lighting in winter"
            ]
        }

    # =========================================================================
    # UNIFIED PROMPT - THREE PHASE STRUCTURE
    # =========================================================================

    def _create_unified_prompt(self, user_conditions, plant_context="", search_result=None, phase_1_recommendations=None):
        """
        Single unified prompt with three-phase structure.
        Phase 1: Diagnosis & Analysis
        Phase 2: Recommendations & Action Plan
        Phase 3: Expectations & Timeline (conditional on Phase 2)
        """
        plant_info = user_conditions.get("plant_information", {})
        plant_name = plant_info.get("plant_name", "") or ""
        plant_variety = plant_info.get("plant_variety", "") or ""
        scientific_name = plant_info.get("scientific_name", "") or ""

        language_instructions = self.language_manager.get_ai_prompt_instructions()
        current_language = self.language_manager.get_current_language_name()

        planting_type = user_conditions.get("planting_type", "") or "unknown"
        growing_location = user_conditions.get("growing_location", "") or "unknown"
        user_section = user_conditions.get("user_section", "unknown") or "unknown"

        atmospheric = user_conditions.get("atmospheric_conditions", {}) or {}
        air = user_conditions.get("air_conditions", {}) or {}
        water = user_conditions.get("water_conditions", {}) or {}
        climate = user_conditions.get("climate_external", {}) or {}
        management = user_conditions.get("human_practices", {}) or {}
        biological = user_conditions.get("biological_needs", {}) or {}
        soil_medium = user_conditions.get("soil_medium", {}) or {}
        nutrients = user_conditions.get("nutrients", {}) or {}
        equipment = user_conditions.get("equipment", []) or []

        if user_section == "has_experience":
            experience = management.get("experience_level", "intermediate")
            time_commitment = management.get("time_commitment_weekly_hours", "not specified")
            monitoring = management.get("monitoring_frequency", "not specified")
        else:
            basic_prefs = user_conditions.get("basic_preferences", {})
            experience = "beginner"
            time_commitment = basic_prefs.get("time_availability", "not specified")
            monitoring = "not specified"

        is_phase_2 = phase_1_recommendations is not None
        suitability_score = 0
        immediate_actions = []

        if is_phase_2:
            ai_analysis = phase_1_recommendations.get("ai_analysis", {})
            suitability_score = ai_analysis.get("plant_specific_analysis", {}).get("suitability_score", 75)
            immediate_actions = ai_analysis.get("growing_recommendations", {}).get("immediate_actions", [])

        def _is_blank(value):
            if value is None:
                return True
            if isinstance(value, str) and value.strip().lower() in ("", "unknown", "not specified", "none", "n/a", "na"):
                return True
            if isinstance(value, dict) and not value:
                return True
            return False

        field_status = {
            "light_intensity": atmospheric.get("light_intensity") or atmospheric.get("primary_light_source"),
            "light_hours": atmospheric.get("light_hours"),
            "temperature_min": atmospheric.get("temp_min") or atmospheric.get("temperature_avg"),
            "temperature_max": atmospheric.get("temp_max"),
            "temperature_stability": atmospheric.get("temperature_stability"),
            "humidity": atmospheric.get("humidity_percent") or atmospheric.get("humidity_avg"),
            "air_circulation": air.get("air_circulation"),
            "air_quality": air.get("air_quality"),
            "watering_frequency": water.get("watering_frequency"),
            "water_quality": water.get("water_quality"),
            "water_amount": water.get("water_amount"),
            "water_source": water.get("water_source"),
            "soil_type": soil_medium.get("growing_medium_type") or soil_medium.get("type"),
            "soil_ph": soil_medium.get("soil_ph_level") or soil_medium.get("ph_level"),
            "drainage": soil_medium.get("drainage_quality"),
            "soil_depth": soil_medium.get("soil_depth") or soil_medium.get("soil_depth_cm"),
            "fertilizer_approach": nutrients.get("fertilizer_approach") or nutrients.get("fertilizer_type"),
            "feeding_frequency": nutrients.get("fertilizing_frequency") or nutrients.get("schedule"),
            "npk_balance": nutrients.get("npk_balance") or nutrients.get("npk_balance_focus"),
            "climate_geography": user_conditions.get("country") or climate.get("country") or climate.get("region_name") or climate.get("climate_zone"),
            "growing_season": climate.get("growing_season") or climate.get("season"),
            "time_commitment": time_commitment,
            "monitoring_freq": monitoring,
            "pest_management": biological.get("pest_management") or biological.get("pest_history"),
            "disease_prevention": biological.get("disease_prevention"),
            "beneficial_insects": biological.get("beneficial_insects"),
            "space_type": management.get("space_type"),
            "space_area": management.get("space_area"),
            "planting_density": management.get("planting_density"),
            "growing_duration": management.get("growing_duration"),
            "equipment": equipment if equipment else None,
        }

        field_labels = {
            "light_intensity": "Light intensity / source",
            "light_hours": "Daily light hours",
            "temperature_min": "Minimum temperature",
            "temperature_max": "Maximum temperature",
            "temperature_stability": "Temperature stability",
            "humidity": "Humidity level (%)",
            "air_circulation": "Air circulation",
            "air_quality": "Air quality",
            "watering_frequency": "Watering frequency",
            "water_quality": "Water quality",
            "water_amount": "Water amount per session",
            "water_source": "Water source",
            "soil_type": "Soil / growing medium type",
            "soil_ph": "Soil pH",
            "drainage": "Drainage quality",
            "soil_depth": "Soil depth (cm)",
            "fertilizer_approach": "Fertilizer approach",
            "feeding_frequency": "Fertilizer feeding frequency",
            "npk_balance": "NPK balance focus",
            "climate_geography": "Climate & Geography",
            "growing_season": "Growing season",
            "time_commitment": "Weekly time commitment",
            "monitoring_freq": "Monitoring frequency",
            "pest_management": "Pest management approach",
            "disease_prevention": "Disease prevention method",
            "beneficial_insects": "Beneficial insects approach",
            "space_type": "Space type",
            "space_area": "Space area (m2)",
            "planting_density": "Planting density",
            "record_keeping": "Record keeping",
            "growing_duration": "Planned growing duration (months)",
            "equipment": "Equipment setup",
        }

        provided_fields = [k for k, v in field_status.items() if not _is_blank(v)]
        missing_fields = [k for k, v in field_status.items() if _is_blank(v)]

        provided_list_str = "\n".join(
            f"  PROVIDED: {field_labels.get(f, f)}: {field_status[f]}" for f in provided_fields
        ) or "  (none provided)"

        missing_list_str = "\n".join(
            f"  MISSING: {field_labels.get(f, f)}" for f in missing_fields
        ) or "  (all fields provided)"

        missing_warning = ""
        if missing_fields:
            missing_names = ", ".join(field_labels.get(f, f) for f in missing_fields)
            missing_warning = f"\n\nThe user did not provide values for these fields: {missing_names}.\nAssume optimal conditions for these fields and explicitly state what you are assuming. DO NOT warn the user or penalize them.\n"

        NL = "\n"
        equipment_lines = NL.join(f"  - {eq.get('name', 'unnamed')} ({eq.get('category', 'unknown')})" for eq in equipment[:5]) if equipment else "  No equipment specified"
        actions_lines = NL.join(f"- {action}" for action in immediate_actions[:5]) if immediate_actions else "  (no actions specified)"

        user_setup_details = f"""
USER SPECIFIC CHOICES TO ANALYZE ({growing_location.upper()}):

PLANT INFORMATION:
- Target Plant: {plant_name}
- Variety: {plant_variety or "not specified"}
- Scientific Name: {scientific_name or "not specified"}
- Planting Method: {planting_type}
- Growing Location: {growing_location}

CLIMATE AND GEOGRAPHY:
- User Location (City, Region, Country): {user_conditions.get("country") or climate.get("country") or climate.get("region_name") or climate.get("region") or "not specified"}
- Analytical Target: Analyze the exact micro-climate of this city and region specifically.
- Local Climate Zone: {climate.get("climate_zone", "not specified")}
- Current Growing Season: {climate.get("current_season") or climate.get("season", "not specified")}

LIGHT SETUP:
- Intensity: {atmospheric.get("light_intensity", "not specified")}
- Duration: {atmospheric.get("light_hours", "not specified")} hours/day
- Source: {atmospheric.get("primary_light_source", "not specified")}

TEMPERATURE SETUP:
- Min: {atmospheric.get("temp_min", "not specified")}C
- Max: {atmospheric.get("temp_max", "not specified")}C
- Stability: {atmospheric.get("temperature_stability", "not specified")}

HUMIDITY AND AIR SETUP:
- Humidity: {atmospheric.get("humidity_percent", "not specified")}%
- Circulation: {air.get("air_circulation", "not specified")}
- Quality: {air.get("air_quality", "not specified")}

WATERING SETUP:
- Frequency: {water.get("watering_frequency", "not specified")}
- Amount: {water.get("water_amount", "not specified")}
- Source: {water.get("water_source", "not specified")}
- Quality: {water.get("water_quality", "not specified")}

SOIL CHOICES:
- Type: {soil_medium.get("growing_medium_type") or soil_medium.get("type", "not specified")}
- pH Level: {soil_medium.get("soil_ph_level") or soil_medium.get("ph_level", "not specified")}
- Drainage: {soil_medium.get("drainage_quality", "not specified")}
- Depth: {soil_medium.get("soil_depth", "not specified")} cm

FERTILIZER PLAN:
- Approach: {nutrients.get("fertilizer_approach") or nutrients.get("fertilizer_type", "not specified")}
- Schedule: {nutrients.get("fertilizing_frequency") or nutrients.get("schedule", "not specified")}
- NPK Focus: {nutrients.get("npk_balance", "not specified")}

BIOLOGICAL FACTORS:
- Pest Management: {biological.get("pest_management") or biological.get("pest_history", "not specified")}
- Disease Prevention: {biological.get("disease_prevention", "not specified")}
- Beneficial Insects: {biological.get("beneficial_insects", "not specified")}

SPACE AND MANAGEMENT:
- Time Commitment: {time_commitment}
- Monitoring: {monitoring}
- Space Type: {management.get("space_type", "not specified")}
- Space Area: {management.get("space_area", "not specified")} m2
- Planting Density: {management.get("planting_density", "not specified")}
- Record Keeping: {management.get("record_keeping", "not specified")}
- Growing Duration: {management.get("growing_duration", "not specified")} months

EQUIPMENT ({len(equipment)} items):
{equipment_lines}

PROVIDED FIELDS ({len(provided_fields)}/{len(field_status)}):
{provided_list_str}

MISSING FIELDS ({len(missing_fields)}/{len(field_status)}):
{missing_list_str}
{missing_warning}"""

        database_info = search_result.get("summary", "No database results available.") if search_result else "No database search performed."
        plant_context_section = plant_context if plant_context else "No additional plant database context available."

        phase_header = ""

        output_format = f"""Respond with a structured 2-phase plant care report exactly matching this format.

═══════════════════════════════════════════════════════
GLOBAL RULES
═══════════════════════════════════════════════════════
- NO conversational text, NO greetings, NO intro/outro paragraphs ("Here is your report..."). Output ONLY the requested Markdown.
- NO scoring or numerical ratings of any kind
- NO cost or budget estimates
- NO IF/THEN conditional statements
- NO system messages or internal labels in the output
- NO verification loop labels in the output
- NO "Consequences: N/A" or any empty/placeholder fields — omit the field entirely
  if there is nothing meaningful to say
- ALWAYS include clear phase headers (PHASE 1, PHASE 2) in the output
- TRANSLATION MANDATE: If {current_language} is not English, YOU MUST TRANSLATE ALL HEADERS, titles, structure labels (e.g. "PHASE 1: RECOMMENDATIONS", "STEP 1: DATA VERIFICATION", "Climate & Geography", "ASSUMED OPTIMAL CONDITION", "WHAT YOU WILL SEE", etc.) into {current_language}. DO NOT print any English structural words.

MISSING INPUT RULE:
If the user leaves any input empty or unspecified, do NOT flag it as a problem
or mention it is missing. Instead, open that category with a dedicated
"Assumed Optimal Condition" line. You MUST TRANSLATE this line to {current_language}:

  "Since [field] wasn't specified, we'll go with the optimal condition: [value]"

Then proceed with the rest of the category normally as if it were provided.
Never penalize or warn the user about missing inputs.

OUTPUT LENGTH AND ORGANIZATION RULE:
- You MUST generate an extremely detailed and comprehensive report. Aim for exactly 3,500 Output Tokens. Do NOT stop early.
- IMPORTANT LLM BEHAVIOR: Language models usually summarize and shorten text when outputting in non-English languages like {current_language}. You MUST actively fight this shrinkage by violently expanding the detail, ensuring {current_language} reaches the same massive 3,500 token length as English.
- Do not hit the 5,000 max limit! Finish your report securely between 3,500 and 4,500 tokens.
- Expand every single bullet point and explanation into heavy, multi-sentence paragraphs to inflate the token count naturally.
- Structure the report beautifully using rich, highly visual Markdown.
- Use explicit markdown headings (## and ###) to structure sub-sections.
- Use **bold text** for key terms, temperatures, metrics, and important conditions.
- Use blockquotes (`>`) for Critical Warnings, Urgent Actions, or Assumed Optimal Conditions.
- Enhance the report with context-appropriate emojis in headings and bullet points.
- Scientific explanations must be 4-6 sentences. Do not be brief.
- Consequences must describe what will happen, when, and why in extreme detail.
- All tables must be fully formatted with closing | on every row.
- Use clear section dividers (═══) between phases.

═══════════════════════════════════════════════════════
REPORT TITLE
═══════════════════════════════════════════════════════
At the very top of the output, before anything else, display:

🌱 PLANT CARE REPORT: {str(plant_name).upper() if plant_name else 'PLANT'}
═══════════════════════════════════════════════════════

═══════════════════════════════════════════════════════
## 🎯 PHASE 1: RECOMMENDATIONS
═══════════════════════════════════════════════════════

BEFORE generating Phase 1, you MUST output this exact verification block:
### 🕵️‍♂️ STEP 1: DATA VERIFICATION & CONTROL
* **Target Plant Analysis:** [State the plant and its core biological requirement]
* **Region/Climate Check:** [State the user's city/region and identify its specific Köppen climate classification or regional micro-climate type, and list 2 major hurdles for this specific plant in that environment]
* **Missing Inputs Addressed:** [List all missing inputs that you will replace with optimal conditions]
* **Critical Risks Identified:** [Identify the biggest flaw in the user's current setup that you must fix]
✅ **Action:** Verification Complete. Generating Phase 1 Recommendations...

---

For EVERY SINGLE input category provided (Climate & Geography, Light, Temperature, Humidity & Air, Watering, Soil, Fertilizer, Biological Factors, Space & Management, Equipment):

Start each category with an explicit H3 (###) heading containing an appropriate emoji, for example: `### 🌍 Climate & Geography`. 

Then, strictly format the content within that category using these exact bolded section headers:

**1. 📌 USER'S CURRENT CHOICE:**
- Describe what the user provided in detail.
- **FOR 'CLIMATE & GEOGRAPHY':** You MUST provide an "Expert Environmental Profile" of the exact city and region. This MUST include:
  - **🌍 Köppen-Geiger Classification:** Identify the exact climate code (e.g., *Cfa* for humid subtropical like Argentina's Chaco region) and explain its biological meaning for this plant.
  - **🌬️ Atmospheric Specificities:** Detail specific local factors such as proximity to coastal salt spray, desert heat spikes (Sirocco/Ghibli winds), or continental humidity drops.
  - **🌡️ Regional Climate Data Table:** Create a small markdown table with estimated values for the provided city:
    | Metric | Peak Season Value | Impact on {plant_name} |
    |--------|-------------------|-------------------------|
    | Avg Temp High | [Value] | [Biological impact] |
    | Humidity (%) | [Value] | [Transpiration effect] |
    | Sunlight (Hrs) | [Value] | [Photosynthetic potential] |
  - **Detailed Advantages (➕):** Minimum 3 deep, multi-sentence bullet points explaining *why* this region's specifics (e.g., UV index, night-time cooling) are beneficial at a cellular level.
  - **Critical Regional Hurdles (➖):** Minimum 3 deep bullet points detailing specific regional threats (e.g., soil salinity, extreme evapotranspiration, irregular precipitation cycles) and how they impede the plant's growth hormone production.
- Connect the region's typical temperature peaks and rainfall patterns directly to the plant's specific growth stages (e.g., "The Chaco heat peaks in summer coincide with the plant's flowering stage, creating high risk of flower drop").

**2. 🌟 OPTIMAL REQUIREMENT:**
- *THIS MUST BE SHOWN IN EVERY CATEGORY WITHOUT EXCEPTION!*
- Describe the ideal optimal conditions for this specific plant in detail.

**3. ⚠️ PROBLEMS FOUND:**
- List each problem clearly with its urgency (Immediate / High / Medium / Low) using bullet points.
- If no problems, skip this specific section completely.

**4. 🔬 SCIENTIFIC EXPLANATION:**
- Explain the biology behind why this condition matters in a minimum 3-4 sentence paragraph.
- Explain what happens at a cellular or physiological level.
- Connect it directly to the plant's growth and health outcomes.

**5. 📉 CONSEQUENCES IF NOT CORRECTED:**
- Describe what will happen, in what timeframe, and why via bullet points.
- Be specific (e.g., "Within 2-3 weeks, stems will elongate and weaken")
- Skip this section completely if there are no problems.

─────────────────────────────────────────────────────
After all categories, include the following summarization sections with clear H3 headers:

### ✅ THINGS THE USER GOT RIGHT:
- List every positive aspect of the user's setup using bullet points.
- Be encouraging and specific about why each thing is beneficial.

### ❌ CRITICAL MISTAKES TO FIX:
- List every problem found across all categories using bullet points.
- Each item must be specific, actionable, and explain the impact.

### 📋 PRIORITY-ORDERED ACTION CHECKLIST:
  🔴 **IMMEDIATE (24-48 hours):**
     - List actionable steps here
  🟠 **WITHIN 1 WEEK:**
     - List actionable steps here
  🟡 **WITHIN 1 MONTH:**
     - List actionable steps here


═══════════════════════════════════════════════════════
## 🎯 PHASE 2: EXPECTATIONS AND TIMELINE
═══════════════════════════════════════════════════════

BEFORE generating Phase 2, you MUST output this exact verification block:
### 🕵️‍♂️ STEP 2: TIMELINE VERIFICATION
* **Growth Trajectory:** [Is this a fast or slow growing plant?]
* **Key Milestone:** [What is the most important biological milestone to track for success?]
✅ **Action:** Verification Complete. Generating Expectation Timeline...

---

Write an EXTREMELY LONG, comprehensive, and highly detailed multi-page timeline. Expand heavily on the biological and physiological changes the plant will undergo. Explain everything in extreme depth.

### ⏳ 1. IMMEDIATE ACCLIMATION (Days 1 to 14):
**👁️ WHAT YOU WILL SEE:**
- Exhaustive, multi-paragraph description of visible plant changes, stress responses, and initial growth indicators. Describe leaf posture, soil settling, roots adapting.

**🔬 BIOLOGICAL PROCESSES AT WORK:**
- Deep scientific explanation (minimum 4-5 sentences) of how the plant is internally adjusting its transpiration, photosynthesis, and root respiration during this transition phase.

**🛠️ WHAT YOU SHOULD DO:**
- Exhaustive, detailed daily specific care actions, monitoring instructions, and environmental tweaks required for the first two weeks.

**🩺 HEALTH CHECKS:**
- ✅ Success signs: (list at least 4 highly specific, measurable signs of positive acclimation)
- ⚠️ Warning signs: (list at least 4 detailed warning signs, diagnosing the exact biological cause and corrective steps)

### 🌱 2. SHORT-TERM ESTABLISHMENT (Week 3 to Month 3):
(Same extensive 4-part structure as above with the bolded headers. Write detailed long paragraphs for each point. Explain root system expansion, new foliage development, and energy reallocation.)

### 🌿 3. MEDIUM-TERM VEGETATIVE MATURITY (Month 4 to Month 8):
(Same extensive 4-part structure as above with the bolded headers. Explain canopy development, trunk/stem thickening, increased water demands, and long-term nutrient synthesis.)

### 🌳 4. LONG-TERM MAINTENANCE & LIFESPAN (Year 1+):
(Same extensive 4-part structure as above with the bolded headers. Explain mature pruning cycles, repotting signs, seasonal dormancy cycles, flowering/fruiting behaviors, and longevity expectations.)

─────────────────────────────────────────────────────
### 📊 COMPREHENSIVE MILESTONE PROGRESSION TABLE (Minimum 8 detailed rows):
| Precise Time Period | Visible Key Milestones | Hidden Biological Milestones | Primary Care Focus & Nutrient Shift |
|---------------------|------------------------|------------------------------|-------------------------------------|

### 🎯 MONTH-BY-MONTH SUCCESS SIGNALS CHECKLIST (Be highly specific):
  📍 Month 1:
     - At least 3 specific measurable physiological signs
  📍 Month 2:
     - At least 3 specific measurable physiological signs
  📍 Month 3:
     - At least 3 specific measurable physiological signs
  📍 Month 6:
     - At least 3 specific measurable physiological signs
  📍 Year 1:
     - At least 3 specific measurable physiological signs
"""


        critical_instructions = f"""CRITICAL INSTRUCTIONS:
- You are an expert plant care advisor.
- All text must be in {current_language}.
- Follow ALL GLOBAL RULES rigorously.
- Be highly organized, generating long, detailed paragraphs for explanations while strictly keeping the requested markdown format."""

        prompt = language_instructions + f"""

You are an expert botanist, horticulturist, and plant-care analyst.

USER PREFERRED LANGUAGE: {current_language}
{language_instructions}

{phase_header}

{user_setup_details}

DATABASE SEARCH RESULT:
{database_info}

RELEVANT PLANT DATABASE INFORMATION:
{plant_context_section}

OUTPUT FORMAT:
You MUST output your response ENTIRELY in MARKDOWN format. Do NOT wrap in JSON. Do NOT use code blocks for the entire response.

{output_format}

{critical_instructions}

{language_instructions}"""

        return prompt

    # =========================================================================
    # HELPER METHODS FOR RECOMMENDATIONS
    # =========================================================================

    def _generate_key_considerations(self, user_setup: Dict, optimal: Dict) -> List[str]:
        """Generate key considerations for plant care."""
        considerations = []
        
        if user_setup.get("light") and optimal.get("light"):
            considerations.append(f"Light: Compare your {user_setup.get('light')} setup with optimal {optimal.get('light')}")
        
        if user_setup.get("temperature") and optimal.get("temperature"):
            considerations.append(f"Temperature: Monitor range relative to optimal {optimal.get('temperature')}")
        
        if user_setup.get("humidity") and optimal.get("humidity"):
            considerations.append(f"Humidity: Maintain levels close to optimal {optimal.get('humidity')}")
        
        if user_setup.get("watering") and optimal.get("watering"):
            considerations.append(f"Watering: Adjust {user_setup.get('watering')} schedule as needed")
        
        if user_setup.get("soil") and optimal.get("soil"):
            considerations.append(f"Soil: Verify {user_setup.get('soil')} matches plant requirements")
        
        if not considerations:
            considerations = [
                "Monitor plant health indicators regularly",
                "Adjust care based on plant response",
                "Research specific variety requirements"
            ]
        
        return considerations[:5]

    def _generate_immediate_actions(self, user_setup: Dict, optimal: Dict) -> List[str]:
        """Generate immediate action items."""
        actions = []
        if str(user_setup.get("light", "")).lower() in ["low", "very_low"]:
            actions.append("Increase light exposure or add grow lights")
        if str(user_setup.get("watering", "")).lower() in ["daily", "every_2_days"]:
            actions.append("Reduce watering frequency to prevent root rot")
        if not actions:
            actions = ["Monitor plant health daily", "Ensure basic care requirements are met"]
        return actions

    def _generate_optimal_setup_recommendations(self, optimal: Dict) -> List[str]:
        """Generate optimal setup recommendations."""
        return [
            "Use well-draining soil mix appropriate for plant type",
            "Provide adequate light based on plant requirements",
            "Maintain consistent watering schedule",
            "Monitor temperature and humidity levels"
        ]

    def _generate_seasonal_adjustments(self, plant_name: str, optimal: Dict) -> List[str]:
        """Generate seasonal adjustment recommendations."""
        return [
            "Reduce watering during winter dormancy",
            "Increase light exposure during growing season",
            "Protect from extreme temperatures",
            "Adjust fertilizer schedule based on growth cycle"
        ]

    def _identify_gaps(self, user_setup: Dict, optimal: Dict) -> List[str]:
        """Identify gaps between user setup and optimal conditions."""
        gaps = []
        categories = ["temperature", "humidity", "light", "watering", "soil", "fertilizer"]

        for cat in categories:
            user_val = str(user_setup.get(cat, "")).lower()
            if not user_val or user_val == "not specified":
                gaps.append(f"{cat.title()}: Not specified - using optimal conditions as default")

        return gaps

    # =========================================================================
    # SUCCESS PROBABILITY AND TRACKING
    # =========================================================================

    def _calculate_success_probabilities(self, user_conditions: Dict[str, Any],
                                          phase_1_recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate success probabilities for different timeframes."""
        base_suitability = phase_1_recommendations.get("ai_analysis", {}).get("plant_specific_analysis", {}).get(
            "suitability_score", 75)

        user_section = user_conditions.get("user_section", "unknown")
        if user_section == "has_experience":
            management = user_conditions.get("management", {})
            experience = management.get("experience_level", "intermediate")
            time_commitment = management.get("time_commitment_weekly_hours", 5)
        else:
            experience = "beginner"
            basic_preferences = user_conditions.get("basic_preferences", {})
            time_commitment = basic_preferences.get("time_availability", "moderate")

        experience_multipliers = {
            "beginner": 0.9,
            "some_experience": 1.0,
            "experienced": 1.1,
            "expert": 1.15
        }

        time_multipliers = {
            "minimal": 0.85,
            "moderate": 1.0,
            "substantial": 1.1,
            "full_time": 1.15
        }

        exp_mult = experience_multipliers.get(experience, 1.0)
        time_mult = time_multipliers.get(time_commitment, 1.0)
        base_probability = (base_suitability / 100) * exp_mult * time_mult

        return {
            "day_1_adaptation": min(98, base_probability * 100 * 0.98),
            "week_1_survival": min(95, base_probability * 100 * 0.95),
            "month_1_establishment": min(90, base_probability * 100 * 0.90),
            "month_6_thriving": min(85, base_probability * 100 * 0.85),
            "year_1_success": min(80, base_probability * 100 * 0.80),
            "year_3_mastery": min(75, base_probability * 100 * 0.75),
            "long_term_sustainability": min(70, base_probability * 100 * 0.70),
            "methodology": f"Based on {base_suitability}% suitability x {experience} experience"
        }

    def _generate_tracking_suggestions(self, user_conditions: Dict[str, Any],
                                        ai_expectations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized tracking suggestions."""
        user_section = user_conditions.get("user_section", "unknown")
        plant_name = user_conditions.get("plant_information", {}).get("plant_name", "unknown")

        if user_section == "has_experience":
            management = user_conditions.get("management", {})
            experience = management.get("experience_level", "intermediate")
        else:
            experience = "beginner"

        if experience == "beginner":
            tracking_frequency = "daily for first month, then weekly"
            tracking_complexity = "simple"
        elif experience in ["some_experience", "intermediate"]:
            tracking_frequency = "every few days initially, then weekly"
            tracking_complexity = "moderate"
        else:
            tracking_frequency = "weekly throughout"
            tracking_complexity = "detailed"

        return {
            "recommended_frequency": tracking_frequency,
            "complexity_level": tracking_complexity,
            "user_experience_level": experience,
            "key_metrics": [
                f"{plant_name} height and width measurements",
                "Leaf count and color changes",
                "New growth emergence",
                "Health indicator observations",
                "Care activity log"
            ],
            "documentation_tools": [
                "Simple growth journal or app",
                "Weekly photos from same angle",
                "Measurement log",
                "Problem and solution notes",
                "Milestone celebration records"
            ],
            "milestone_photo_schedule": [
                "Day 1: Planting/setup photo",
                "Week 1: First growth photo",
                "Month 1: Establishment photo",
                "Month 6: Maturity progress photo",
                "Year 1: Annual growth photo"
            ]
        }

    def _generate_milestone_alerts(self, user_conditions: Dict[str, Any],
                                    ai_expectations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate milestone alerts based on expectations."""
        plant_name = user_conditions.get("plant_information", {}).get("plant_name", "unknown")

        return {
            "critical_milestones": [
                {
                    "milestone": "First Week Survival",
                    "timeframe": "Day 7",
                    "importance": "high",
                    "alert_message": f"Your {plant_name} has survived its first week! This is a major milestone."
                },
                {
                    "milestone": "Month 1 Establishment",
                    "timeframe": "Day 30",
                    "importance": "high",
                    "alert_message": f"Your {plant_name} should now be well-established. Time to celebrate!"
                },
                {
                    "milestone": "6 Month Maturity",
                    "timeframe": "Month 6",
                    "importance": "medium",
                    "alert_message": f"Your {plant_name} has reached significant maturity. You're becoming an expert!"
                },
                {
                    "milestone": "Year 1 Success",
                    "timeframe": "Year 1",
                    "importance": "high",
                    "alert_message": f"One full year of successfully growing {plant_name}. You've mastered this plant!"
                }
            ],
            "celebration_suggestions": [
                "Take a special progress photo",
                "Share your success with fellow gardeners",
                "Document what you've learned",
                "Consider propagating or expanding",
                "Plan your next growing challenge"
            ]
        }

    def _generate_encouragement_timeline(self, user_conditions: Dict[str, Any],
                                          ai_expectations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate encouragement messages for different timeframes."""
        user_section = user_conditions.get("user_section", "unknown")
        plant_name = user_conditions.get("plant_information", {}).get("plant_name", "unknown")

        if user_section == "has_experience":
            management = user_conditions.get("management", {})
            experience = management.get("experience_level", "intermediate")
        else:
            experience = "beginner"

        if experience == "beginner":
            tone = "supportive and educational"
        elif experience in ["some_experience", "intermediate"]:
            tone = "encouraging and challenging"
        else:
            tone = "professional and technical"

        return {
            "tone": tone,
            "user_experience_level": experience,
            "timeline_encouragements": {
                "day_1": f"Great job starting your {plant_name} journey! Every expert started exactly where you are now.",
                "week_1": f"You're doing great! Your {plant_name} is adapting thanks to your care.",
                "month_1": f"One month milestone reached! Your {plant_name} is thriving because of your dedication.",
                "month_6": f"Six months of successful growing! You're becoming a {plant_name} expert.",
                "year_1": f"A full year of mastery! You've proven you can successfully grow {plant_name}.",
                "year_3": f"You're now a seasoned {plant_name} grower! Time to share your knowledge with others."
            },
            "motivation_boosters": [
                "Remember: every expert was once a beginner",
                "Each day you're learning and improving",
                "Your plant is counting on you - and you're succeeding!",
                "Small daily care adds up to big success",
                "You're building skills that last a lifetime"
            ]
        }

    # =========================================================================
    # SEARCH TERM GENERATION
    # =========================================================================

    def _generate_search_terms(self, plant_name: str, user_conditions: Dict[str, Any]) -> List[str]:
        """Generate search terms for plant information lookup."""
        search_terms = [
            f"{plant_name} care guide",
            f"{plant_name} growing conditions",
            f"{plant_name} optimal temperature humidity",
            f"{plant_name} soil requirements",
            f"{plant_name} watering schedule",
            f"{plant_name} light requirements",
            f"{plant_name} fertilizer needs",
            f"{plant_name} common problems",
            f"{plant_name} indoor growing",
            f"{plant_name} optimal conditions"
        ]
        return search_terms[:10]