from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

class AnalyzeRequest(BaseModel):
    # Language
    language: str = "en"
    user_email: Optional[EmailStr] = None
    
    # User info
    user_section: Optional[str] = "no_experience"
    
    # Plant info - FLAT STRUCTURE matching frontend
    plant_name: str
    plant_variety: Optional[str] = None
    scientific_name: Optional[str] = None
    planting_method: Optional[str] = "seed_planting"
    growing_location: Optional[str] = "indoor"
    
    # Environmental - FLAT
    light_intensity: Optional[str] = "medium"
    light_hours: Optional[str] = None
    primary_light_source: Optional[str] = "natural_window"
    temp_min: Optional[str] = None
    temp_max: Optional[str] = None
    temperature_stability: Optional[str] = "stable"
    air_circulation: Optional[str] = "moderate"
    humidity_percent: Optional[str] = None
    air_quality: Optional[str] = "good"
    
    # Water & Soil - FLAT
    watering_frequency: Optional[str] = "weekly"
    water_amount: Optional[str] = "moderate"
    water_source: Optional[str] = "tap_water"
    water_quality: Optional[str] = "good"
    growing_medium_type: Optional[str] = "potting_mix"
    soil_ph_level: Optional[str] = "slightly_acidic"
    drainage_quality: Optional[str] = "good"
    soil_depth: Optional[str] = None
    
    # Nutrients - FLAT
    fertilizer_approach: Optional[str] = "mixed_approach"
    fertilizing_frequency: Optional[str] = "monthly"
    npk_balance: Optional[str] = "balanced"
    
    # Biological - FLAT
    pest_management: Optional[str] = "minimal"
    disease_prevention: Optional[str] = "hygiene"
    beneficial_insects: Optional[str] = "encourage"
    
    # Space & Management - FLAT
    space_type: Optional[str] = "room_corner"
    space_area: Optional[str] = None
    planting_density: Optional[str] = "moderate"
    experience_level: Optional[str] = "some_experience"
    time_commitment: Optional[str] = None
    monitoring_frequency: Optional[str] = "every_few_days"
    record_keeping: Optional[str] = "basic"
    growing_duration: Optional[str] = None
    
    # Equipment and additional fields
    has_temp_control: Optional[bool] = False
    has_ventilation: Optional[bool] = False
    has_irrigation: Optional[bool] = False
    has_ph_tested: Optional[bool] = False
    has_nutrient_testing: Optional[bool] = False
    has_equipment: Optional[bool] = False
    ignore_typo: Optional[bool] = False

    class Config:
        extra = "allow"  # Allow extra fields

class AnalysisResponse(BaseModel):
    session_id: str
    status: str
    message: str
    suggested_name: Optional[str] = None

class AnalysisResult(BaseModel):
    session_id: str
    status: str
    plant_name: Optional[str] = None
    recommendations: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None