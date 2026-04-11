"""
conditions.py (WEB VERSION)
Comprehensive plant growing conditions processor
Processes data received from web frontend API requests
FULLY MULTI-LANGUAGE SUPPORTED
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Setup logging instead of print
logger = logging.getLogger("plant_advisor.conditions")

class PlantConditionsCollector:
    """Comprehensive collector/processor for all plant growing conditions."""

    def __init__(self, language_manager=None):
        """
        Initialize the conditions collector.
        
        Args:
            language_manager: Optional language manager for translations.
                              If None, uses a simple passthrough.
        """
        self.language_manager = language_manager or self._create_fallback_language_manager()
        self.conditions = {}
        self._init_question_categories()

    def _create_fallback_language_manager(self):
        """Create a simple fallback language manager that returns the key as-is."""
        class FallbackLanguageManager:
            def get_text(self, key, **kwargs):
                return key.replace('_', ' ').title()
            def get_current_language(self):
                return "en"
        return FallbackLanguageManager()

    def _init_question_categories(self):
        """Initialize all question categories and structures."""
        self.condition_categories = {
            "plant_information": {
                "title": "plant_information",
                "required": True,
                "questions": [
                    {
                        "key": "plant_name",
                        "type": "text",
                        "required": True,
                        "max_length": 100,
                        "help_key": "plant_name_help"
                    },
                    {
                        "key": "plant_variety",
                        "type": "text",
                        "required": False,
                        "max_length": 100,
                        "help_key": "plant_variety_help"
                    },
                    {
                        "key": "scientific_name",
                        "type": "text",
                        "required": False,
                        "max_length": 100,
                        "help_key": "scientific_name_help"
                    }
                ]
            },
            "planting_type": {
                "title": "planting_type_question",
                "required": True,
                "options": [
                    "seed_planting", "transplanting", "cuttings",
                    "grafting", "layering", "division", "tissue_culture"
                ]
            },
            "growing_location": {
                "title": "growing_location_question",
                "required": True,
                "options": ["indoor", "outdoor", "both_indoor_outdoor"]
            }
        }

        # Valid options for validation
        self.valid_options = {
            "planting_type": ["seed_planting", "transplanting", "cuttings", "grafting", "layering", "division", "tissue_culture", "Soil", "Pot", "Hydroponic", "Greenhouse"],
            "growing_location": ["indoor", "outdoor", "both_indoor_outdoor"],
            "light_intensity": ["very_low", "low", "medium", "high", "very_high"],
            "temperature_stability": ["very_stable", "stable", "moderate_fluctuation", "high_fluctuation"],
            "air_circulation": ["excellent", "good", "moderate", "poor", "stagnant"],
            "air_quality": ["excellent", "good", "moderate", "poor", "unknown"],
            "water_quality": ["excellent", "good", "moderate", "poor", "unknown"],
            "watering_frequency": ["daily", "every_2_days", "twice_weekly", "weekly", "as_needed"],
            "water_amount": ["light_misting", "moderate", "thorough", "deep_soaking"],
            "water_source": ["tap_water", "filtered_water", "rainwater", "well_water", "distilled_water"],
            "growing_medium_type": ["natural_soil", "potting_mix", "custom_blend", "hydroponic", "soilless_mix"],
            "soil_ph_level": ["acidic", "slightly_acidic", "neutral", "slightly_alkaline", "alkaline", "unknown"],
            "drainage_quality": ["excellent", "good", "moderate", "poor", "waterlogged"],
            "fertilizer_approach": ["organic_only", "synthetic_only", "mixed_approach", "minimal_fertilizer", "none"],
            "fertilizing_frequency": ["weekly", "biweekly", "monthly", "seasonally", "as_needed", "never"],
            "climate_zone": ["tropical", "subtropical", "temperate", "continental", "arid", "mediterranean", "unknown"],
            "experience_level": ["beginner", "some_experience", "experienced", "expert", "Beginner", "Intermediate", "Expert"],
            "monitoring_frequency": ["daily", "every_few_days", "weekly", "biweekly", "monthly"],
            "care_frequency": ["Daily", "Weekly", "Bi-weekly", "daily", "weekly", "bi-weekly"],
        }

    def _get_text(self, key: str) -> str:
        """Get translated text with fallback."""
        return self.language_manager.get_text(key)

    # =========================================================================
    # MAIN WEB ENTRY POINT
    # =========================================================================

    def process_web_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for web API.
        Takes the JSON data from frontend and processes it into the internal format.
        
        Args:
            data: Dictionary containing all form data from the web frontend.
                  Expected structure matches the Pydantic AnalyzeRequest model.
        
        Returns:
            Dictionary with processed and structured conditions.
        """
        logger.info("Processing web data for plant conditions")
        
        try:
            # Determine user experience level
            user_section = self._determine_user_section(data)
            
            # Initialize collected conditions
            collected_conditions = {
                "collection_timestamp": datetime.now().isoformat(),
                "language": data.get("language", "en"),
                "user_section": user_section,
                "collection_method": "web_form",
                "ignore_typo": data.get("ignore_typo", False)
            }

            # Process basic information
            basic_info = self._process_basic_information(data)
            if not basic_info.get("plant_information", {}).get("plant_name"):
                logger.error("Plant name is required but not provided")
                raise ValueError("Plant name is required")

            collected_conditions.update(basic_info)


            # Extract country / geographic zone from flat form data
            geographic_zone = data.get("geographic_zone", "") or ""
            if geographic_zone:
                collected_conditions["country"] = geographic_zone
                # Also store in climate_external so the analyzer prompt can find it
                if "climate_external" not in collected_conditions:
                    collected_conditions["climate_external"] = {}
                collected_conditions["climate_external"]["country"] = geographic_zone
                collected_conditions["climate_external"]["region_name"] = geographic_zone
                logger.info(f"Geographic zone/country: {geographic_zone}")

            # Process detailed conditions based on user section
            if user_section == "has_experience":
                detailed_conditions = self._process_experienced_user_conditions(data)
                collected_conditions.update(detailed_conditions)
            else:
                # Basic preferences for beginners
                preferences = self._process_basic_preferences(data)
                if preferences:
                    collected_conditions["basic_preferences"] = preferences


            # Map flat form fields to nested keys that environmental_analyzer expects
            # The frontend sends flat fields (e.g. "watering_frequency") but the analyzer
            # reads from nested dicts (e.g. user_conditions["water_conditions"]["watering_frequency"])
            self._map_flat_fields_for_analyzer(data, collected_conditions)

            # Log summary
            self._log_conditions_summary(collected_conditions)

            return collected_conditions

        except Exception as e:
            logger.error(f"Error processing web data: {e}")
            raise

    def _determine_user_section(self, data: Dict[str, Any]) -> str:
        """
        Determine user experience section from web data.
        
        Args:
            data: Web form data dictionary
            
        Returns:
            'has_experience' or 'no_experience'
        """
        # Check user_section field from frontend
        user_section = data.get("user_section", "")
        
        if user_section in ["has_experience", "no_experience"]:
            return user_section
        
        # Fallback to experience level in human_practices
        human_practices = data.get("human_practices", {})
        exp_level = human_practices.get("experience_level", "")
        
        if exp_level in ["experienced", "expert", "Expert"]:
            return "has_experience"
        
        return "no_experience"

    def _process_basic_information(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process basic plant information from web data.
        
        Args:
            data: Web form data dictionary
            
        Returns:
            Dictionary with plant_information, planting_type, and growing_location
        """
        basic_info = {}

        # Plant Information - Support both flat (frontend) and nested (legacy) formats
        plant_info_data = data.get("plant_information", {})
        
        # If plant_information is empty or doesn't have plant_name, check flat format
        if isinstance(plant_info_data, dict):
            if not plant_info_data.get("plant_name"):
                plant_name = data.get("plant_name", "")
                plant_variety = data.get("plant_variety", "")
                scientific_name = data.get("scientific_name", "")
            else:
                plant_name = plant_info_data.get("plant_name", "")
                plant_variety = plant_info_data.get("plant_variety", "")
                scientific_name = plant_info_data.get("scientific_name", "")
        else:
            # Fallback to flat format
            plant_name = data.get("plant_name", "")
            plant_variety = data.get("plant_variety", "")
            scientific_name = data.get("scientific_name", "")
        
        basic_info["plant_information"] = {
            "plant_name": self._clean_text(plant_name),
            "plant_variety": self._clean_text(plant_variety),
            "scientific_name": self._clean_text(scientific_name)
        }

        logger.info(f"Processing plant: {basic_info['plant_information']['plant_name']}")

        # Planting Type
        planting_type_data = data.get("planting_type", {})
        if isinstance(planting_type_data, dict):
            planting_method = planting_type_data.get("method", "seed_planting")
        else:
            planting_method = str(planting_type_data) if planting_type_data else "seed_planting"
        
        basic_info["planting_type"] = self._validate_option(
            planting_method,
            self.valid_options["planting_type"],
            "seed_planting"
        )

        # Growing Location
        growing_location_data = data.get("growing_location", {})
        if isinstance(growing_location_data, dict):
            location_method = growing_location_data.get("method", "indoor")
            location_type = growing_location_data.get("type", "greenhouse")
        else:
            location_method = str(growing_location_data) if growing_location_data else "indoor"
            location_type = data.get("location_type", "greenhouse")

        basic_info["growing_location"] = self._validate_option(
            location_method,
            self.valid_options["growing_location"],
            "indoor"
        )

        basic_info["location_type"] = self._validate_option(
            location_type,
            self.valid_options.get("location_type", ["greenhouse", "vertical_farm", "outdoor", "container"]),
            "greenhouse"
        )

        return basic_info

    def _process_water_conditions_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process water conditions from new format."""
        water = data.get("water_conditions", {})
        return {
            "watering_frequency": water.get("watering_frequency", "every_2_days"),
            "water_amount": water.get("water_amount", "moderate"),
            "water_source": water.get("water_source", "tap_water"),
            "water_quality": water.get("water_quality", "good")
        }

    def _process_soil_conditions_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process soil conditions from new format."""
        soil = data.get("soil_medium", {})
        return {
            "type": soil.get("type", "potting_mix"),
            "soil_type_detail": soil.get("soil_type_detail", ""),
            "ph_level": soil.get("ph_level", "unknown"),
            "drainage_quality": soil.get("drainage_quality", "good")
        }

    def _process_nutrients_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process nutrients from new format."""
        nutrients = data.get("nutrients", {})
        return {
            "fertilizer_type": nutrients.get("fertilizer_type", "mixed_approach"),
            "schedule": nutrients.get("schedule", "monthly")
        }

    def _process_climate_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process climate from new format."""
        climate = data.get("climate_external", {})
        return {
            "region": climate.get("region", ""),
            "season": climate.get("season", "spring"),
            "climate_zone": climate.get("climate_zone", "temperate")
        }

    def _process_human_practices_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process human practices from new format."""
        human = data.get("human_practices", {})
        return {
            "care_frequency": human.get("care_frequency", "weekly"),
            "monitoring_frequency": human.get("monitoring_frequency", "weekly"),
            "experience_level": human.get("experience_level", "beginner")
        }

    def _process_biological_new(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process biological needs from new format."""
        bio = data.get("biological_needs", {})
        return {
            "water_frequency": bio.get("water_frequency", "every_2_days"),
            "pest_history": bio.get("pest_history", "none")
        }

    def _process_basic_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process basic preferences for beginner users.
        
        Args:
            data: Web form data dictionary
            
        Returns:
            Dictionary with basic preferences
        """
        preferences = {}

        # Time availability from human practices
        human_practices = data.get("human_practices", {})
        care_freq = human_practices.get("care_frequency", "")
        
        if care_freq:
            time_mapping = {
                "Daily": "substantial",
                "daily": "substantial",
                "Weekly": "moderate",
                "weekly": "moderate",
                "Bi-weekly": "minimal",
                "bi-weekly": "minimal"
            }
            preferences["time_availability"] = time_mapping.get(care_freq, "moderate")

        # Space size from planting type
        planting_type = data.get("planting_type", {})
        if isinstance(planting_type, dict):
            space = planting_type.get("space_available", "")
            if space:
                preferences["space_size"] = self._categorize_space(space)

        return preferences

    def _categorize_space(self, space_description: str) -> str:
        """Categorize space description into standard sizes."""
        space_lower = space_description.lower()
        
        if any(word in space_lower for word in ["very small", "tiny", "windowsill"]):
            return "very_small"
        elif any(word in space_lower for word in ["small", "balcony", "pot"]):
            return "small"
        elif any(word in space_lower for word in ["large", "garden", "field"]):
            return "large"
        else:
            return "medium"

    def _process_experienced_user_conditions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process detailed conditions for experienced users.
        
        Args:
            data: Web form data dictionary
            
        Returns:
            Dictionary with all detailed growing conditions
        """
        conditions = {}

        # Determine location types
        growing_location = data.get("growing_location", "outdoor")
        location_types = (["indoor", "outdoor"] if growing_location == "both_indoor_outdoor"
                         else [growing_location])

        # Environmental Conditions
        conditions["environmental"] = self._process_environmental_conditions(data, location_types)

        # Soil/Growing Medium
        conditions["soil_medium"] = self._process_soil_conditions(data)

        # Nutrients
        conditions["nutrients"] = self._process_nutrient_conditions(data)

        # Climate & Geography (always process, not just outdoor)
        conditions["climate_external"] = self._process_climate_conditions(data)

        # Biological factors
        conditions["biological"] = self._process_biological_conditions(data)

        # Space and setup
        conditions["space_setup"] = self._process_space_conditions(data, location_types)

        # Human practices / Management
        conditions["management"] = self._process_management_practices(data)

        # Equipment (if provided)
        equipment = data.get("equipment", [])
        if equipment:
            conditions["equipment"] = equipment

        return conditions

    def _process_environmental_conditions(self, data: Dict[str, Any], location_types: List[str]) -> Dict[str, Any]:
        """
        Process environmental conditions from web data.
        
        Args:
            data: Web form data
            location_types: List of location types (indoor/outdoor)
            
        Returns:
            Dictionary with environmental conditions
        """
        environmental = {}
        
        # Get atmospheric conditions from web data
        atmos = data.get("atmospheric_conditions", {})

        for location in location_types:
            location_key = f"{location}_conditions" if len(location_types) > 1 else "conditions"

            environmental[location_key] = {
                "light": self._process_light_conditions(data, location),
                "temperature": self._process_temperature_conditions(atmos, location),
                "air": self._process_air_conditions(atmos, location),
                "water": self._process_water_conditions(data, location)
            }

        return environmental

    def _process_light_conditions(self, data: Dict[str, Any], location: str) -> Dict[str, Any]:
        """Process light conditions from web data."""
        light_data = {}
        
        atmos = data.get("atmospheric_conditions", {})
        
        # Light hours
        light_hours_str = atmos.get("light_hours", "8")
        light_hours = self._extract_number(light_hours_str, default=8, min_val=0, max_val=24)
        light_data["light_duration_hours"] = light_hours

        # Infer light intensity from hours
        if light_hours >= 10:
            light_data["light_intensity"] = "high"
        elif light_hours >= 6:
            light_data["light_intensity"] = "medium"
        elif light_hours >= 3:
            light_data["light_intensity"] = "low"
        else:
            light_data["light_intensity"] = "very_low"

        # Location-specific
        if location == "indoor":
            planting_type = data.get("planting_type", {})
            method = planting_type.get("method", "") if isinstance(planting_type, dict) else ""
            
            if method.lower() == "hydroponic":
                light_data["primary_light_source"] = "led_lights"
            else:
                light_data["primary_light_source"] = "natural_window"
        else:
            # Outdoor sun exposure based on light hours
            if light_hours >= 8:
                light_data["sun_exposure"] = "full_sun"
            elif light_hours >= 5:
                light_data["sun_exposure"] = "partial_sun"
            elif light_hours >= 3:
                light_data["sun_exposure"] = "partial_shade"
            else:
                light_data["sun_exposure"] = "full_shade"

        return light_data

    def _process_temperature_conditions(self, atmos: Dict[str, Any], location: str) -> Dict[str, Any]:
        """Process temperature conditions from web data."""
        temp_data = {}

        # Parse temperature string (e.g., "25°C" or "20-30")
        temp_str = atmos.get("temperature_avg", "25")
        temp_value = self._extract_number(temp_str, default=25, min_val=-20, max_val=50)
        
        # Estimate min/max from average
        temp_data["average_min_temp"] = temp_value - 5
        temp_data["average_max_temp"] = temp_value + 5
        temp_data["average_temp"] = temp_value
        
        # Default stability
        temp_data["temperature_stability"] = "moderate_fluctuation"

        return temp_data

    def _process_air_conditions(self, atmos: Dict[str, Any], location: str) -> Dict[str, Any]:
        """Process air conditions from web data."""
        air_data = {}

        # Humidity
        humidity_str = atmos.get("humidity_avg", "50")
        
        # Handle text descriptions
        if isinstance(humidity_str, str):
            humidity_lower = humidity_str.lower()
            if "high" in humidity_lower:
                humidity_value = 75
            elif "low" in humidity_lower:
                humidity_value = 30
            elif "normal" in humidity_lower or "moderate" in humidity_lower:
                humidity_value = 50
            else:
                humidity_value = self._extract_number(humidity_str, default=50, min_val=0, max_val=100)
        else:
            humidity_value = humidity_str if isinstance(humidity_str, (int, float)) else 50

        air_data["humidity_level_percent"] = humidity_value

        # Defaults for other air conditions
        air_data["air_circulation"] = "good"
        air_data["air_quality"] = "good"

        return air_data

    def _process_water_conditions(self, data: Dict[str, Any], location: str) -> Dict[str, Any]:
        """Process water conditions from web data."""
        water_data = {}
        
        bio_needs = data.get("biological_needs", {})
        
        # Water frequency
        water_freq = bio_needs.get("water_frequency", "Regular")
        freq_mapping = {
            "Regular": "every_2_days",
            "regular": "every_2_days",
            "Daily": "daily",
            "daily": "daily",
            "Weekly": "weekly",
            "weekly": "weekly"
        }
        water_data["watering_frequency"] = freq_mapping.get(water_freq, "every_2_days")
        
        # Defaults
        water_data["water_amount"] = "moderate"
        water_data["water_source"] = "tap_water"
        water_data["water_quality"] = "good"

        return water_data

    def _process_soil_conditions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process soil and growing medium conditions from web data."""
        soil_data = {}
        
        soil_medium = data.get("soil_medium", {})

        # Growing medium type
        soil_type = soil_medium.get("type", "potting_mix")
        type_mapping = {
            "Clay": "natural_soil",
            "Sandy": "natural_soil",
            "Loam": "natural_soil",
            "Potting Mix": "potting_mix",
            "potting_mix": "potting_mix",
            "Hydroponic": "hydroponic"
        }
        soil_data["growing_medium_type"] = type_mapping.get(soil_type, "potting_mix")
        soil_data["soil_type_detail"] = soil_type

        # pH Level
        ph_level = soil_medium.get("ph_level", "unknown")
        if ph_level and ph_level != "Unknown":
            ph_value = self._extract_number(str(ph_level), default=7.0, min_val=0, max_val=14)
            soil_data["measured_ph_value"] = ph_value
            
            # Categorize pH
            if ph_value < 6.0:
                soil_data["soil_ph_level"] = "acidic"
            elif ph_value < 6.5:
                soil_data["soil_ph_level"] = "slightly_acidic"
            elif ph_value <= 7.5:
                soil_data["soil_ph_level"] = "neutral"
            elif ph_value <= 8.0:
                soil_data["soil_ph_level"] = "slightly_alkaline"
            else:
                soil_data["soil_ph_level"] = "alkaline"
        else:
            soil_data["soil_ph_level"] = "unknown"

        # Defaults
        soil_data["drainage_quality"] = "good"
        soil_data["soil_depth_cm"] = 30

        return soil_data

    def _process_nutrient_conditions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process nutrient management conditions from web data."""
        nutrient_data = {}
        
        nutrients = data.get("nutrients", {})

        # Fertilizer type
        fert_type = nutrients.get("fertilizer_type", "Standard")
        type_mapping = {
            "Standard": "mixed_approach",
            "Organic": "organic_only",
            "Synthetic": "synthetic_only",
            "None": "none"
        }
        nutrient_data["fertilizer_approach"] = type_mapping.get(fert_type, "mixed_approach")

        # Schedule
        schedule = nutrients.get("schedule", "Standard")
        schedule_mapping = {
            "Standard": "monthly",
            "Weekly": "weekly",
            "Biweekly": "biweekly",
            "Monthly": "monthly",
            "None": "never"
        }
        nutrient_data["fertilizing_frequency"] = schedule_mapping.get(schedule, "monthly")

        # Defaults
        nutrient_data["npk_balance_focus"] = "balanced_npk"
        nutrient_data["tests_nutrients"] = False

        return nutrient_data

    def _process_climate_conditions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process outdoor climate conditions from web data."""
        climate_data = {}
        
        climate_ext = data.get("climate_external", {})

        # Region to climate zone mapping
        region = climate_ext.get("region", "").lower()
        
        climate_mapping = {
            "tropical": "tropical",
            "subtropical": "subtropical",
            "temperate": "temperate",
            "continental": "continental",
            "arid": "arid",
            "desert": "arid",
            "mediterranean": "mediterranean",
            "california": "mediterranean",
            "florida": "subtropical",
            "europe": "temperate",
            "northern europe": "temperate"
        }
        
        # Try to match region
        climate_zone = "unknown"
        for key, value in climate_mapping.items():
            if key in region:
                climate_zone = value
                break
        
        climate_data["climate_zone"] = climate_zone
        climate_data["region_name"] = climate_ext.get("region", "Unknown")
        # Also use geographic_zone from flat form data as country
        geographic_zone = data.get("geographic_zone", "")
        if geographic_zone:
            climate_data["country"] = geographic_zone
            if not climate_data["region_name"] or climate_data["region_name"] == "Unknown":
                climate_data["region_name"] = geographic_zone

        # Season
        season = climate_ext.get("season", "Current")
        climate_data["current_season"] = season

        # Defaults
        climate_data["growing_season_length"] = "long_season"
        climate_data["frost_frequency"] = "rare"
        climate_data["wind_exposure_level"] = "moderate_wind"

        return climate_data

    def _process_biological_conditions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process biological and pest management conditions from web data."""
        bio_data = {}
        
        bio_needs = data.get("biological_needs", {})

        # Pest history
        pest_history = bio_needs.get("pest_history", "None")
        
        if pest_history and pest_history.lower() != "none":
            bio_data["has_pest_history"] = True
            bio_data["pest_history_detail"] = pest_history
            bio_data["pest_management_approach"] = "integrated_management"
        else:
            bio_data["has_pest_history"] = False
            bio_data["pest_management_approach"] = "preventive_only"

        # Defaults
        bio_data["disease_prevention_method"] = "good_hygiene"
        bio_data["beneficial_insects_approach"] = "welcome_natural"

        return bio_data

    def _process_space_conditions(self, data: Dict[str, Any], location_types: List[str]) -> Dict[str, Any]:
        """Process space and setup conditions from web data."""
        space_data = {}
        
        planting_type = data.get("planting_type", {})
        space_available = ""
        method = ""
        
        if isinstance(planting_type, dict):
            space_available = planting_type.get("space_available", "")
            method = planting_type.get("method", "")

        for location in location_types:
            location_key = f"{location}_space" if len(location_types) > 1 else "space"

            # Determine space type based on method
            if location == "indoor":
                if method.lower() == "hydroponic":
                    space_type = "dedicated_room"
                elif method.lower() == "greenhouse":
                    space_type = "greenhouse"
                else:
                    space_type = "windowsill"
            else:
                if method.lower() in ["pot", "container"]:
                    space_type = "container_garden"
                else:
                    space_type = "ground_plot"

            space_data[f"{location_key}_type"] = space_type

            # Parse area if provided
            if space_available:
                area = self._parse_area(space_available)
                if area:
                    space_data[f"{location_key}_area"] = area

            # Default density
            space_data[f"{location_key}_density"] = "moderate_density"

        return space_data

    def _parse_area(self, space_str: str) -> Optional[float]:
        """Parse area from string like '2x2 meters' or '10 sqm'."""
        if not space_str:
            return None
            
        space_lower = space_str.lower()
        
        # Try to find dimensions like "2x2"
        dimension_match = re.search(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)', space_str)
        if dimension_match:
            width = float(dimension_match.group(1))
            length = float(dimension_match.group(2))
            return width * length
        
        # Try to find single number
        number_match = re.search(r'(\d+(?:\.\d+)?)', space_str)
        if number_match:
            return float(number_match.group(1))
        
        return None

    def _process_management_practices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process management and maintenance practices from web data."""
        management_data = {}
        
        human_practices = data.get("human_practices", {})

        # Experience level
        exp_level = human_practices.get("experience_level", "beginner")
        exp_mapping = {
            "Beginner": "beginner",
            "beginner": "beginner",
            "Intermediate": "some_experience",
            "intermediate": "some_experience",
            "Expert": "expert",
            "expert": "expert",
            "experienced": "experienced"
        }
        management_data["experience_level"] = exp_mapping.get(exp_level, "beginner")

        # Care frequency to time commitment
        care_freq = human_practices.get("care_frequency", "Weekly")
        time_mapping = {
            "Daily": 7,
            "daily": 7,
            "Bi-weekly": 3,
            "bi-weekly": 3,
            "Weekly": 2,
            "weekly": 2
        }
        management_data["time_commitment_weekly_hours"] = time_mapping.get(care_freq, 3)

        # Monitoring frequency
        monitoring_mapping = {
            "Daily": "daily",
            "daily": "daily",
            "Bi-weekly": "every_few_days",
            "bi-weekly": "every_few_days",
            "Weekly": "weekly",
            "weekly": "weekly"
        }
        management_data["monitoring_frequency"] = monitoring_mapping.get(care_freq, "weekly")

        # Defaults
        management_data["record_keeping"] = "basic_notes"
        management_data["planned_growing_duration_months"] = 6

        return management_data

    # =========================================================================
    # VALIDATION AND UTILITY METHODS
    # =========================================================================

    def _validate_option(self, value: str, valid_options: List[str], default: str) -> str:
        """Validate that value is in valid options, return default if not."""
        if value in valid_options:
            return value
        
        # Try case-insensitive match
        value_lower = value.lower()
        for option in valid_options:
            if option.lower() == value_lower:
                return option
        
        logger.warning(f"Invalid option '{value}', using default '{default}'")
        return default

    def _clean_text(self, text: str) -> str:
        """Clean and sanitize text input."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Limit length
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
        
        return cleaned.strip()

    def _extract_number(self, text: str, default: float = 0, min_val: float = None, max_val: float = None) -> float:
        """Extract a number from text string."""
        if not text:
            return default
            
        if isinstance(text, (int, float)):
            value = float(text)
        else:
            # Try to find a number in the text
            match = re.search(r'-?\d+(?:\.\d+)?', str(text))
            if match:
                value = float(match.group())
            else:
                return default
        
        # Apply bounds
        if min_val is not None:
            value = max(value, min_val)
        if max_val is not None:
            value = min(value, max_val)
        
        return value

    def _map_flat_fields_for_analyzer(self, raw_data: Dict[str, Any], conditions: Dict[str, Any]):
        """
        Map flat form fields directly to the nested structure
        that environmental_analyzer.py reads from.
        This ensures user-provided values show up in the LLM prompt.
        """
        # Atmospheric conditions (light, temperature, humidity)
        conditions["atmospheric_conditions"] = {
            "light_intensity": raw_data.get("light_intensity", ""),
            "light_hours": raw_data.get("light_hours", ""),
            "primary_light_source": raw_data.get("primary_light_source", ""),
            "temp_min": raw_data.get("temp_min", ""),
            "temp_max": raw_data.get("temp_max", ""),
            "temperature_stability": raw_data.get("temperature_stability", ""),
            "humidity_percent": raw_data.get("humidity_percent", ""),
            "temperature_avg": raw_data.get("temp_min", ""),
            "humidity_avg": raw_data.get("humidity_percent", ""),
        }

        # Air conditions
        conditions["air_conditions"] = {
            "air_circulation": raw_data.get("air_circulation", ""),
            "air_quality": raw_data.get("air_quality", ""),
        }

        # Water conditions
        conditions["water_conditions"] = {
            "watering_frequency": raw_data.get("watering_frequency", ""),
            "water_amount": raw_data.get("water_amount", ""),
            "water_source": raw_data.get("water_source", ""),
            "water_quality": raw_data.get("water_quality", ""),
        }

        # Soil / growing medium
        conditions["soil_medium"] = {
            "growing_medium_type": raw_data.get("growing_medium_type", ""),
            "type": raw_data.get("growing_medium_type", ""),
            "soil_ph_level": raw_data.get("soil_ph_level", ""),
            "ph_level": raw_data.get("soil_ph_level", ""),
            "drainage_quality": raw_data.get("drainage_quality", ""),
            "soil_depth": raw_data.get("soil_depth", ""),
            "soil_depth_cm": raw_data.get("soil_depth", ""),
        }

        # Nutrients
        conditions["nutrients"] = {
            "fertilizer_approach": raw_data.get("fertilizer_approach", ""),
            "fertilizer_type": raw_data.get("fertilizer_approach", ""),
            "fertilizing_frequency": raw_data.get("fertilizing_frequency", ""),
            "schedule": raw_data.get("fertilizing_frequency", ""),
            "npk_balance": raw_data.get("npk_balance", ""),
            "npk_balance_focus": raw_data.get("npk_balance", ""),
        }

        # Biological needs
        conditions["biological_needs"] = {
            "pest_management": raw_data.get("pest_management", ""),
            "pest_history": raw_data.get("pest_management", ""),
            "disease_prevention": raw_data.get("disease_prevention", ""),
            "beneficial_insects": raw_data.get("beneficial_insects", ""),
        }

        # Human practices / management
        conditions["human_practices"] = {
            "experience_level": raw_data.get("experience_level", ""),
            "time_commitment_weekly_hours": raw_data.get("time_commitment", ""),
            "monitoring_frequency": raw_data.get("monitoring_frequency", ""),
            "space_type": raw_data.get("space_type", ""),
            "space_area": raw_data.get("space_area", ""),
            "planting_density": raw_data.get("planting_density", ""),
            "record_keeping": raw_data.get("record_keeping", "basic_notes"),
            "growing_duration": raw_data.get("growing_duration", ""),
        }

        logger.info("Flat form fields mapped to analyzer-expected nested structure")

    def _log_conditions_summary(self, conditions: Dict[str, Any]):
        """Log a summary of collected conditions."""
        plant_info = conditions.get("plant_information", {})
        plant_name = plant_info.get('plant_name', 'Unknown')
        user_section = conditions.get("user_section", "unknown")
        
        logger.info(f"Conditions processed for: {plant_name}")
        logger.info(f"User section: {user_section}")
        logger.info(f"Growing location: {conditions.get('growing_location', 'unknown')}")
        logger.info(f"Planting type: {conditions.get('planting_type', 'unknown')}")

    # =========================================================================
    # EXPORT AND ANALYSIS METHODS (Kept from original)
    # =========================================================================

    def export_conditions_for_analysis(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Export conditions in a format optimized for AI analysis."""
        analysis_format = {
            "metadata": {
                "user_section": conditions.get("user_section", ""),
                "collection_timestamp": conditions.get("collection_timestamp", ""),
                "language": conditions.get("language", ""),
                "collection_method": conditions.get("collection_method", "web_form")
            },
            "plant_info": {
                "name": conditions.get("plant_information", {}).get("plant_name", ""),
                "variety": conditions.get("plant_information", {}).get("plant_variety", ""),
                "scientific_name": conditions.get("plant_information", {}).get("scientific_name", ""),
                "planting_method": conditions.get("planting_type", ""),
                "growing_location": conditions.get("growing_location", "")
            }
        }

        # Add detailed conditions for experienced users
        if conditions.get("user_section") == "has_experience":
            for section_name in ["environmental", "soil_medium", "nutrients", "climate", "biological", "space_setup", "management"]:
                section_data = conditions.get(section_name, {})
                if section_data:
                    analysis_format[section_name] = self._flatten_dict(section_data)

            # Equipment summary
            equipment = conditions.get("equipment", [])
            if equipment:
                analysis_format["equipment"] = {
                    "count": len(equipment),
                    "categories": [eq.get("category", "") for eq in equipment],
                    "automation_levels": [eq.get("automation_level", "") for eq in equipment]
                }
        else:
            # Add basic preferences for beginners
            basic_prefs = conditions.get("basic_preferences", {})
            if basic_prefs:
                analysis_format["basic_preferences"] = basic_prefs

        return analysis_format

    def _flatten_dict(self, nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        """Flatten a nested dictionary for analysis."""
        flattened = {}

        for key, value in nested_dict.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, new_key, sep))
            else:
                flattened[new_key] = value

        return flattened

    def get_plant_info(self, conditions: Dict[str, Any]) -> Dict[str, str]:
        """Extract plant information for easy access."""
        plant_info = conditions.get("plant_information", {})

        return {
            "name": plant_info.get("plant_name", ""),
            "variety": plant_info.get("plant_variety", ""),
            "scientific_name": plant_info.get("scientific_name", ""),
            "growing_location": conditions.get("growing_location", ""),
            "user_section": conditions.get("user_section", ""),
            "planting_method": conditions.get("planting_type", ""),
            "display_name": self._create_display_name(conditions)
        }

    def _create_display_name(self, conditions: Dict[str, Any]) -> str:
        """Create a formatted display name for the plant."""
        plant_info = conditions.get("plant_information", {})
        name = plant_info.get("plant_name", "Unknown Plant")
        variety = plant_info.get("plant_variety", "")

        display_name = name.title()

        if variety:
            display_name += f" '{variety}'"

        location = conditions.get("growing_location", "")
        if location:
            location_text = location.replace("_", " ").title()
            display_name += f" - {location_text}"

        return display_name

    def quick_plant_lookup(self, plant_name: str, growing_location: str = "", user_section: str = "no_experience") -> Dict[str, Any]:
        """Quick method to create basic conditions for a plant."""
        return {
            "collection_timestamp": datetime.now().isoformat(),
            "language": self.language_manager.get_current_language() if hasattr(self.language_manager, 'get_current_language') else "en",
            "user_section": user_section,
            "plant_information": {
                "plant_name": plant_name.strip(),
                "plant_variety": "",
                "scientific_name": ""
            },
            "growing_location": growing_location if growing_location in ["indoor", "outdoor", "both_indoor_outdoor"] else "",
            "collection_method": "quick_lookup"
        }

    def save_conditions(self, conditions: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save collected conditions to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plant_name = conditions.get("plant_information", {}).get("plant_name", "unknown_plant")
            user_section = conditions.get("user_section", "unknown")

            # Clean plant name for filename
            clean_plant_name = re.sub(r'[^\w\s-]', '', plant_name).strip()
            clean_plant_name = re.sub(r'[-\s]+', '_', clean_plant_name).lower()
            filename = f"plant_conditions_{user_section}_{clean_plant_name}_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conditions, f, indent=2, ensure_ascii=False)
            logger.info(f"Conditions saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving conditions: {e}")
            return ""

    def load_conditions(self, filename: str) -> Dict[str, Any]:
        """Load conditions from a JSON file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                conditions = json.load(f)
            logger.info(f"Conditions loaded from: {filename}")
            return conditions
        except Exception as e:
            logger.error(f"Error loading conditions: {e}")
            return {}