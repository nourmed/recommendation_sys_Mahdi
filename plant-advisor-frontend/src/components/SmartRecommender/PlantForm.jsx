import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, Loader, Plus, Trash2 } from 'lucide-react';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { logUserAction } from '../../services/history';
import { Country, State, City } from 'country-state-city';

// ── Notice banner translations (10 languages) ────────────────────────────
const NOTICE_TRANSLATIONS = {
  en: { bold: "No need to fill everything!", body: "Only complete what you know — leave any field blank if you're unsure. The more detail you provide, the more precise your advice will be." },
  fr: { bold: "Pas besoin de tout remplir !", body: "Complétez uniquement ce que vous savez — laissez vide ce dont vous n'êtes pas sûr. Plus vous donnez de détails, plus les conseils seront précis." },
  es: { bold: "¡No necesitas completar todo!", body: "Solo completa lo que sabes — deja en blanco los campos que desconoces. Cuantos más detalles proporciones, más precisos serán tus consejos." },
  de: { bold: "Nicht alles muss ausgefüllt werden!", body: "Füllen Sie nur aus, was Sie wissen — lassen Sie Felder leer, wenn Sie unsicher sind. Je mehr Details Sie angeben, desto präziser ist Ihr Rat." },
  ar: { bold: "لا داعي لملء كل شيء!", body: "أكمل فقط ما تعرفه — اترك أي حقل فارغًا إذا لم تكن متأكدًا. كلما زادت التفاصيل التي تقدمها، كانت نصيحتك أكثر دقة." },
  zh: { bold: "无需填写所有内容！", body: "只需填写您知道的内容 — 如果不确定，请将任何字段留空。您提供的详细信息越多，建议就越精确。" },
  pt: { bold: "Não precisa preencher tudo!", body: "Preencha apenas o que você sabe — deixe qualquer campo em branco se não tiver certeza. Quanto mais detalhes você fornecer, mais preciso será o conselho." },
  ru: { bold: "Не нужно заполнять всё!", body: "Заполните только то, что вы знаете — оставьте поля пустыми, если не уверены. Чем больше деталей вы укажете, тем точнее будет совет." },
  tr: { bold: "Her şeyi doldurmak zorunda değilsiniz!", body: "Yalnızca bildiklerinizi doldurun — emin olmadığınız alanları boş bırakın. Ne kadar fazla ayrıntı sağlarsanız tavsiyeniz o kadar doğru olur." },
  it: { bold: "Non devi compilare tutto!", body: "Compila solo ciò che sai — lascia vuoto qualsiasi campo di cui non sei sicuro. Più dettagli fornisci, più preciso sarà il consiglio." },
};

const LOCATION_TRANSLATIONS = {
  en: { country: "Country", select_country: "Select Country", region: "Region / State", select_region: "Select Region", city: "City", select_city: "Select City" },
  fr: { country: "Pays", select_country: "Sélectionner un pays", region: "Région / État", select_region: "Sélectionner une région", city: "Ville", select_city: "Sélectionner une ville" },
  es: { country: "País", select_country: "Seleccionar País", region: "Región / Estado", select_region: "Seleccionar Región", city: "Ciudad", select_city: "Seleccionar Ciudad" },
  de: { country: "Land", select_country: "Land auswählen", region: "Region / Bundesland", select_region: "Region auswählen", city: "Stadt", select_city: "Stadt auswählen" },
  ar: { country: "البلد", select_country: "اختر البلد", region: "المنطقة / الولاية", select_region: "اختر المنطقة", city: "المدينة", select_city: "اختر المدينة" },
  zh: { country: "国家", select_country: "选择国家", region: "地区 / 省", select_region: "选择地区", city: "城市", select_city: "选择城市" },
  pt: { country: "País", select_country: "Selecionar País", region: "Região / Estado", select_region: "Selecionar Região", city: "Cidade", select_city: "Selecionar Cidade" },
  ru: { country: "Страна", select_country: "Выберите страну", region: "Регион / Штат", select_region: "Выберите регион", city: "Город", select_city: "Выберите город" },
  tr: { country: "Ülke", select_country: "Ülke Seçin", region: "Bölge / Eyalet", select_region: "Bölge Seçin", city: "Şehir", select_city: "Şehir Seçin" },
  it: { country: "Paese", select_country: "Seleziona Paese", region: "Regione / Stato", select_region: "Seleziona Regione", city: "Città", select_city: "Seleziona Città" }
};

// Default step configs (English fallback)
const defaultSteps = [
  { id: 1, titleKey: 'plant_information', fallback: 'Plant Information', icon: '🌱' },
  { id: 2, titleKey: 'light_conditions', fallback: 'Light Conditions', icon: '☀️' },
  { id: 3, titleKey: 'temperature_conditions', fallback: 'Temperature', icon: '🌡️' },
  { id: 4, titleKey: 'air_conditions', fallback: 'Air Conditions', icon: '💨' },
  { id: 5, titleKey: 'water_conditions', fallback: 'Water Conditions', icon: '💧' },
  { id: 6, titleKey: 'soil_growing_medium', fallback: 'Soil & Medium', icon: '🪴' },
  { id: 7, titleKey: 'nutrient_management', fallback: 'Nutrients', icon: '🧪' },
  { id: 8, titleKey: 'biological_factors', fallback: 'Biological', icon: '🧬' },
  { id: 9, titleKey: 'space_setup', fallback: 'Space & Setup', icon: '🏗️' },
  { id: 10, titleKey: 'management_practices', fallback: 'Management', icon: '👨‍🌾' },
  { id: 11, titleKey: 'equipment_details', fallback: 'Equipment', icon: '⚙️' },
];

function PlantForm() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [labels, setLabels] = useState({});
  const [userLanguage, setUserLanguage] = useState(localStorage.getItem('plant_app_language') || 'en');
  const [translatedRegions, setTranslatedRegions] = useState([]);
  const [translatedCities, setTranslatedCities] = useState([]);
  const [isTranslatingLocation, setIsTranslatingLocation] = useState(false);
  const [equipment, setEquipment] = useState([]);
  const [showEquipmentForm, setShowEquipmentForm] = useState(false);
  const [currentEquipment, setCurrentEquipment] = useState({
    name: '', category: '', power_source: '', automation_level: '', installation_date: ''
  });
  const [typoSuggestion, setTypoSuggestion] = useState(null);
  const [invalidPlant, setInvalidPlant] = useState(false);
  const [errors, setErrors] = useState({});
  
  const [formData, setFormData] = useState({
    country_iso: '', region_iso: '', city_name: '', geographic_zone: '',
    plant_name: '', plant_variety: '', scientific_name: '',
    planting_method: 'seed_planting', growing_location: 'indoor',
    light_intensity: 'medium', light_hours: '', primary_light_source: 'natural_window',
    has_lighting_equipment: false, lighting_equipment_type: '', lighting_power_watts: '',
    has_timer_control: false, timer_control_type: '',
    temp_min: '', temp_max: '', temperature_stability: 'stable',
    has_temp_control: false, temp_control_type: '', temp_power_source: '', temp_automated: false,
    air_circulation: 'moderate', humidity_percent: '', air_quality: 'good',
    has_ventilation: false, ventilation_type: '', ventilation_control: '',
    watering_frequency: 'weekly', water_amount: 'moderate', water_source: 'tap_water', water_quality: 'good',
    has_irrigation: false, irrigation_type: '',
    growing_medium_type: 'potting_mix', soil_ph_level: 'slightly_acidic', drainage_quality: 'good',
    soil_depth: '', has_tested_ph: false, measured_ph: '',
    fertilizer_approach: 'mixed_approach', fertilizing_frequency: 'monthly', npk_balance: 'balanced',
    tests_nutrients: false, testing_method: '',
    pest_management: 'minimal', disease_prevention: 'hygiene', beneficial_insects: 'welcome_natural',
    space_type: 'room_corner', space_area: '', planting_density: 'moderate',
    experience_level: 'some_experience', time_commitment: '', monitoring_frequency: 'every_few_days',
    record_keeping: 'basic_notes', growing_duration: '',
    has_special_equipment: false
  });

  // Translation helper - returns translated text or fallback
  const t = (key, fallback) => labels[key] || fallback || key;

  // Load translated labels on mount
  useEffect(() => {
    const lang = localStorage.getItem('plant_app_language') || 'en';
    setUserLanguage(lang);
    const loadLabels = async () => {
      try {
        const data = await api.getFormLabels(lang);
        if (data.labels) {
          setLabels(data.labels);
        }
      } catch (err) {
        console.error('Failed to load labels:', err);
      }
    };
    loadLabels();
  }, []);

  // Get the notice text in the user's language
  const notice = NOTICE_TRANSLATIONS[userLanguage] || NOTICE_TRANSLATIONS['en'];
  const locT = LOCATION_TRANSLATIONS[userLanguage] || LOCATION_TRANSLATIONS['en'];
  const isRTL = userLanguage === 'ar';

  const isExperienced = true;
  const currentSteps = defaultSteps;
  const totalSteps = currentSteps.length;
  const progress = (step / totalSteps) * 100;

  const getTranslatedCountryName = (isoCode, defaultName) => {
    try {
      if (userLanguage !== 'en') {
        const regionNames = new Intl.DisplayNames([userLanguage], { type: 'region' });
        return regionNames.of(isoCode) || defaultName;
      }
    } catch (e) {}
    return defaultName;
  };

  const countries = Country.getAllCountries().map(c => ({
    ...c,
    displayName: getTranslatedCountryName(c.isoCode, c.name)
  })).sort((a, b) => a.displayName.localeCompare(b.displayName, userLanguage));

  useEffect(() => {
    let mounted = true;
    const fetchTranslatedRegions = async () => {
      const rawRegions = formData.country_iso ? State.getStatesOfCountry(formData.country_iso) : [];
      if (!rawRegions.length) {
         if (mounted) setTranslatedRegions([]);
         return;
      }
      if (userLanguage === 'en') {
         if (mounted) setTranslatedRegions(rawRegions.map(r => ({ ...r, displayName: r.name })));
         return;
      }
      
      if (mounted) setIsTranslatingLocation(true);
      try {
         const resp = await api.translateLocations(rawRegions.map(r => r.name), userLanguage);
         if (mounted) setTranslatedRegions(rawRegions.map((r, i) => ({ ...r, displayName: resp.translated[i] || r.name })));
      } catch (e) {
         if (mounted) setTranslatedRegions(rawRegions.map(r => ({ ...r, displayName: r.name })));
      }
      if (mounted) setIsTranslatingLocation(false);
    };
    fetchTranslatedRegions();
    return () => { mounted = false; };
  }, [formData.country_iso, userLanguage]);

  useEffect(() => {
    let mounted = true;
    const fetchTranslatedCities = async () => {
      const rawCities = formData.region_iso ? City.getCitiesOfState(formData.country_iso, formData.region_iso) : [];
      if (!rawCities.length) {
         if (mounted) setTranslatedCities([]);
         return;
      }
      if (userLanguage === 'en') {
         if (mounted) setTranslatedCities(rawCities.map(c => ({ ...c, displayName: c.name })));
         return;
      }
      
      if (mounted) setIsTranslatingLocation(true);
      try {
         const resp = await api.translateLocations(rawCities.map(c => c.name), userLanguage);
         if (mounted) setTranslatedCities(rawCities.map((c, i) => ({ ...c, displayName: resp.translated[i] || c.name })));
      } catch (e) {
         if (mounted) setTranslatedCities(rawCities.map(c => ({ ...c, displayName: c.name })));
      }
      if (mounted) setIsTranslatingLocation(false);
    };
    fetchTranslatedCities();
    return () => { mounted = false; };
  }, [formData.region_iso, formData.country_iso, userLanguage]);

  // Get translated step title
  const getStepTitle = (stepConfig) => {
    return t(stepConfig.titleKey, stepConfig.fallback);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    // Clear error for the field when user changes it
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }

    if (name === 'plant_name') {
      setTypoSuggestion(null);
      setInvalidPlant(false);
    }
  };

  const handleEquipmentChange = (e) => {
    const { name, value } = e.target;
    setCurrentEquipment(prev => ({ ...prev, [name]: value }));
  };

  const addEquipment = () => {
    if (currentEquipment.name && currentEquipment.category) {
      setEquipment([...equipment, { ...currentEquipment, id: Date.now() }]);
      setCurrentEquipment({ name: '', category: '', power_source: '', automation_level: '', installation_date: '' });
      setShowEquipmentForm(false);
    }
  };

  const removeEquipment = (id) => {
    setEquipment(equipment.filter(item => item.id !== id));
  };

  const validateStep = () => {
    const newErrors = {};

    if (step === 1) {
      if (!formData.plant_name) newErrors.plant_name = true;
      if (!formData.planting_method) newErrors.planting_method = true;
      if (!formData.country_iso) newErrors.country_iso = true;
      if (!formData.region_iso) newErrors.region_iso = true;
      if (!formData.growing_location) newErrors.growing_location = true;
    }

    if (step === 2) {
      if (formData.light_hours !== '') {
        const val = Number(formData.light_hours);
        if (val < 1 || val > 24) newErrors.light_hours = true;
      }
      if (formData.has_lighting_equipment && formData.lighting_power_watts !== '') {
        const val = Number(formData.lighting_power_watts);
        if (val < 1 || val > 5000) newErrors.lighting_power_watts = true;
      }
    }

    if (step === 3) {
      if (formData.temp_min !== '') {
        const val = Number(formData.temp_min);
        if (val < -20 || val > 50) newErrors.temp_min = true;
      }
      if (formData.temp_max !== '') {
        const val = Number(formData.temp_max);
        if (val < -20 || val > 50) newErrors.temp_max = true;
      }
      if (formData.temp_min !== '' && formData.temp_max !== '') {
        if (Number(formData.temp_min) > Number(formData.temp_max)) {
          newErrors.temp_min = true;
          newErrors.temp_max = true;
        }
      }
    }

    if (step === 4) {
      if (formData.humidity_percent !== '') {
        const val = Number(formData.humidity_percent);
        if (val < 0 || val > 100) newErrors.humidity_percent = true;
      }
    }
    
    if (step === 6) {
      if (formData.soil_depth !== '') {
        const val = Number(formData.soil_depth);
        if (val < 5 || val > 200) newErrors.soil_depth = true;
      }
      if (formData.has_tested_ph && formData.measured_ph !== '') {
        const val = Number(formData.measured_ph);
        if (val < 0 || val > 14) newErrors.measured_ph = true;
      }
    }

    if (step === 9) {
      if (formData.space_area !== '') {
        const val = Number(formData.space_area);
        if (val < 0.1 || val > 1000) newErrors.space_area = true;
      }
    }

    if (step === 10) {
      if (formData.time_commitment !== '') {
        const val = Number(formData.time_commitment);
        if (val < 0 || val > 40) newErrors.time_commitment = true;
      }
      if (formData.growing_duration !== '') {
        const val = Number(formData.growing_duration);
        if (val < 1 || val > 120) newErrors.growing_duration = true;
      }
    }

    setErrors(newErrors);
    
    const hasErrors = Object.keys(newErrors).length > 0;
    
    if (hasErrors) {
      setTimeout(() => {
        const firstError = document.querySelector('.error-pulse');
        if (firstError) {
          firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 50);
    }
    
    return !hasErrors;
  };

  const nextStep = () => {
    if (!validateStep()) return;
    
    if (step < totalSteps) setStep(step + 1);
    else submitForm();
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  const submitForm = async (ignoreTypo = false, overridePlantName = null) => {
    setLoading(true);
    setTypoSuggestion(null);
    setInvalidPlant(false);
    try {
      const language = localStorage.getItem('plant_app_language') || 'en';
      
      const selectedCountry = Country.getCountryByCode(formData.country_iso)?.name || '';
      const selectedRegion = State.getStateByCodeAndCountry(formData.region_iso, formData.country_iso)?.name || '';
      const finalGeographicZone = `${formData.city_name}, ${selectedRegion}, ${selectedCountry}`;
      
      const activePlantName = overridePlantName || formData.plant_name;
      const payload = { ...formData, plant_name: activePlantName, geographic_zone: finalGeographicZone, language, equipment: equipment.length > 0 ? equipment : undefined, ignore_typo: ignoreTypo };
      const result = await api.submitAnalysis(payload);
      
      if (result.status === 'invalid') {
        setInvalidPlant(true);
        setStep(1);
        setLoading(false);
        return;
      }
      
      if (result.status === 'typo' && !ignoreTypo && result.suggested_name) {
        setTypoSuggestion(result.suggested_name);
        setLoading(false);
        return;
      }

      localStorage.setItem('current_session_id', result.session_id);
      localStorage.setItem('current_plant_name', activePlantName);
      
      // Log history
      await logUserAction(currentUser, 'Smart Recommender', `Requested a growing guide for ${activePlantName}`, {
        plant: activePlantName,
        experience: formData.experience_level,
        location: formData.growing_location
      });
      
      navigate('/recommender/results');
    } catch (error) {
      alert('Failed to submit analysis. Please try again.');
      console.error(error);
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="form-card">
        {/* Progress Bar */}
        <div className="form-progress">
          <div className="form-progress-bar" style={{ width: `${progress}%` }} />
        </div>

        {typoSuggestion ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} 
            animate={{ opacity: 1, scale: 1 }} 
            className="typo-fullscreen-modal"
            style={{ padding: '2rem', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '400px' }}
          >
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🤔</div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '1rem', color: '#111827' }}>
              {t('did_you_mean', 'Did you mean')} <span style={{ color: '#10b981', fontWeight: 800 }}>{typoSuggestion}</span>?
            </h2>
            <p style={{ color: '#6b7280', marginBottom: '2rem', fontSize: '1.1rem', lineHeight: '1.5' }}>
              {t('typo_explanation', 'We couldn\'t find an exact scientific or common match for your spelling. Would you like to use this corrected name for your report?')}
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '400px', margin: '0 auto', width: '100%' }}>
              <button 
                type="button" 
                onClick={() => {
                  setFormData(prev => ({ ...prev, plant_name: typoSuggestion }));
                  submitForm(true, typoSuggestion);
                }} 
                className="btn btn-primary"
                style={{ padding: '1rem', fontSize: '1.1rem', backgroundColor: '#10b981', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}
              >
                ✅ {t('yes_continue', 'Yes, use the corrected name')}
              </button>
              <button 
                type="button" 
                onClick={() => {
                  setTypoSuggestion(null);
                  setStep(1);
                  setLoading(false);
                }} 
                className="btn btn-secondary"
                style={{ padding: '1rem', fontSize: '1.1rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}
              >
                ✏️ {t('no_modify_name', 'No, let me type a different name')}
              </button>
            </div>
          </motion.div>
        ) : (
          <>
            {/* Header */}
            <div className="form-header">
              <h2>{currentSteps[step - 1]?.icon} {getStepTitle(currentSteps[step - 1])}</h2>
              <p>{t('step', 'Step')} {step} / {totalSteps}</p>
            </div>

            {/* Notice Banner */}
            <div className={`form-notice-banner ${isRTL ? 'rtl' : ''}`}>
              <div className="form-notice-icon-wrap">
                <span className="form-notice-icon">💡</span>
              </div>
              <div className="form-notice-text">
                <span className="form-notice-bold">{notice.bold}</span>
                {' '}
                <span className="form-notice-body">{notice.body}</span>
              </div>
            </div>

        {/* Invalid Plant UI */}
        <AnimatePresence>
          {invalidPlant && step === 1 && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }} 
              animate={{ opacity: 1, height: 'auto' }} 
              exit={{ opacity: 0, height: 0 }}
              style={{ padding: '1rem', background: '#fef2f2', border: '1px solid #ef4444', borderRadius: '0.5rem', marginBottom: '1.5rem', color: '#b91c1c' }}
            >
              <p style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                ❌ {t('invalid_plant_name', `The name '${formData.plant_name}' does not appear to be a valid plant. Please correct it.`)}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form Body */}
        <div className="form-body">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              {/* Step 1: Plant Information */}
              {step === 1 && (
                <div>
                  <div className="form-group">
                    <label className="form-label">{t('plant_name', 'What plant do you want to grow?')} *</label>
                    <input type="text" name="plant_name" value={formData.plant_name} onChange={handleChange} className={`form-input ${errors.plant_name ? 'error-pulse' : ''}`} placeholder={t('plant_name_help', 'e.g. tomato, basil, roses')} required />
                  </div>

                  <div className="form-group">
                    <label className="form-label">{t('plant_variety', 'Plant variety')} ({t('optional', 'optional')})</label>
                    <input type="text" name="plant_variety" value={formData.plant_variety} onChange={handleChange} className="form-input" placeholder={t('plant_variety_help', 'e.g. Cherry tomato, Sweet basil')} />
                  </div>

                  <div className="form-group">
                    <label className="form-label">{t('scientific_name', 'Scientific name')} ({t('optional', 'optional')})</label>
                    <input type="text" name="scientific_name" value={formData.scientific_name} onChange={handleChange} className="form-input" placeholder={t('scientific_name_help', 'e.g. Ocimum basilicum')} />
                  </div>

                  <div className="form-group">
                    <label className="form-label">{t('planting_type_question', 'What type of planting are you doing?')} *</label>
                    <select name="planting_method" value={formData.planting_method} onChange={handleChange} className={`form-select ${errors.planting_method ? 'error-pulse' : ''}`} required>
                      <option value="seed_planting">{t('seed_planting', 'Seed planting - Growing from seeds')}</option>
                      <option value="transplanting">{t('transplanting', 'Transplanting - Moving young plants')}</option>
                      <option value="cuttings">{t('cuttings', 'Cuttings - Growing from stem/leaf/root pieces')}</option>
                      <option value="grafting">{t('grafting', 'Grafting - Joining two plants together')}</option>
                      <option value="layering">{t('layering', 'Layering - Rooting while still attached')}</option>
                      <option value="division">{t('division', 'Division - Splitting mature plants')}</option>
                      <option value="tissue_culture">{t('tissue_culture', 'Tissue culture - Lab-grown from cells')}</option>
                    </select>
                  </div>

                  <div className="form-group" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                    <div className="location-field">
                      <label className="form-label">{locT.country} *</label>
                      <select name="country_iso" value={formData.country_iso} onChange={(e) => { handleChange(e); setFormData(p => ({...p, region_iso: '', city_name: ''})); }} className={`form-select ${errors.country_iso ? 'error-pulse' : ''}`} required>
                        <option value="">{locT.select_country}</option>
                        {countries.map(c => <option key={c.isoCode} value={c.isoCode}>{c.displayName}</option>)}
                      </select>
                    </div>
                    <div className="location-field">
                      <label className="form-label">{locT.region} *</label>
                      <select name="region_iso" value={formData.region_iso} onChange={(e) => { handleChange(e); setFormData(p => ({...p, city_name: ''})); }} className={`form-select ${errors.region_iso ? 'error-pulse' : ''}`} disabled={!formData.country_iso} required>
                        <option value="">{isTranslatingLocation ? '...' : locT.select_region}</option>
                        {translatedRegions.map(r => <option key={r.isoCode} value={r.isoCode}>{r.displayName}</option>)}
                      </select>
                    </div>
                    <div className="location-field">
                      <label className="form-label">{locT.city}</label>
                      <select name="city_name" value={formData.city_name} onChange={handleChange} className={`form-select ${errors.city_name ? 'error-pulse' : ''}`} disabled={!formData.region_iso}>
                        <option value="">{isTranslatingLocation ? '...' : locT.select_city}</option>
                        {translatedCities.map(c => <option key={c.name} value={c.name}>{c.displayName}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('growing_location_question', 'Where will you be growing this plant?')} *</label>
                    <select name="growing_location" value={formData.growing_location} onChange={handleChange} className={`form-select ${errors.growing_location ? 'error-pulse' : ''}`} required>
                      <option value="indoor">{t('indoor', 'Indoor (house, greenhouse, enclosed space)')}</option>
                      <option value="outdoor">{t('outdoor', 'Outdoor (garden, balcony, open air)')}</option>
                      <option value="both_indoor_outdoor">{t('both_indoor_outdoor', 'Both indoor and outdoor (seasonal movement)')}</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Step 2: Light Conditions */}
              {step === 2 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>☀️ {t('light_conditions', 'Light Conditions')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('light_intensity', 'Light intensity')}</label>
                      <select name="light_intensity" value={formData.light_intensity} onChange={handleChange} className={`form-select ${errors.light_intensity ? 'error-pulse' : ''}`}>
                        <option value="very_low">{t('very_low', 'Very low')}</option>
                        <option value="low">{t('low', 'Low')}</option>
                        <option value="medium">{t('medium', 'Medium')}</option>
                        <option value="high">{t('high', 'High')}</option>
                        <option value="very_high">{t('very_high', 'Very high')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('light_duration_hours', 'Hours of light per day')}</label>
                      <input type="number" name="light_hours" value={formData.light_hours} onChange={handleChange} className={`form-input ${errors.light_hours ? 'error-pulse' : ''}`} placeholder="1-24" min="1" max="24" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('primary_light_source', 'Primary light source')}</label>
                      <select name="primary_light_source" value={formData.primary_light_source} onChange={handleChange} className={`form-select ${errors.primary_light_source ? 'error-pulse' : ''}`}>
                        <option value="natural_window">{t('natural_window', 'Natural window light')}</option>
                        <option value="led_grow">{t('led_lights', 'LED grow lights')}</option>
                        <option value="fluorescent">{t('fluorescent', 'Fluorescent lights')}</option>
                        <option value="mixed">{t('mixed', 'Mixed natural and artificial')}</option>
                        <option value="other">{t('other', 'Other')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="has_lighting_equipment" checked={formData.has_lighting_equipment} onChange={handleChange} />
                      <span>{t('provide_lighting_equipment_details', 'I have lighting equipment')}</span>
                    </label>
                  </div>

                  {formData.has_lighting_equipment && (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div className="form-group">
                          <label className="form-label">{t('equipment_type', 'Lighting equipment type')}</label>
                          <select name="lighting_equipment_type" value={formData.lighting_equipment_type} onChange={handleChange} className="form-select">
                            <option value="">{t('select_option', 'Select...')}</option>
                            <option value="led_panel">{t('led_panel', 'LED panel')}</option>
                            <option value="led_strip">{t('led_strip', 'LED strip lights')}</option>
                            <option value="fluorescent_tube">{t('fluorescent_tube', 'Fluorescent tube')}</option>
                            <option value="grow_bulb">{t('grow_bulb', 'Grow bulb')}</option>
                            <option value="multiple">{t('multiple_types', 'Multiple types')}</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label className="form-label">{t('total_power_watts', 'Total power (watts)')}</label>
                          <input type="number" name="lighting_power_watts" value={formData.lighting_power_watts} onChange={handleChange} className="form-input" placeholder="1-5000" min="1" max="5000" />
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="checkbox-label">
                          <input type="checkbox" name="has_timer_control" checked={formData.has_timer_control} onChange={handleChange} />
                          <span>{t('do_you_have_timer_control', 'Timer control for lights')}</span>
                        </label>
                      </div>

                      {formData.has_timer_control && (
                        <div className="form-group">
                          <label className="form-label">{t('timer_type', 'Timer control type')}</label>
                          <select name="timer_control_type" value={formData.timer_control_type} onChange={handleChange} className="form-select">
                            <option value="">{t('select_option', 'Select...')}</option>
                            <option value="basic_timer">{t('basic_timer', 'Basic timer')}</option>
                            <option value="smart_controller">{t('smart_controller', 'Smart controller')}</option>
                            <option value="manual">{t('manual_control', 'Manual control')}</option>
                          </select>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Step 3: Temperature */}
              {step === 3 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>🌡️ {t('temperature_conditions', 'Temperature Conditions')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('average_min_temp', 'Average min temperature')} (°C)</label>
                      <input type="number" name="temp_min" value={formData.temp_min} onChange={handleChange} className={`form-input ${errors.temp_min ? 'error-pulse' : ''}`} placeholder="-20 to 50" min="-20" max="50" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('average_max_temp', 'Average max temperature')} (°C)</label>
                      <input type="number" name="temp_max" value={formData.temp_max} onChange={handleChange} className={`form-input ${errors.temp_max ? 'error-pulse' : ''}`} placeholder="-20 to 50" min="-20" max="50" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('temperature_stability', 'Temperature stability')}</label>
                      <select name="temperature_stability" value={formData.temperature_stability} onChange={handleChange} className={`form-select ${errors.temperature_stability ? 'error-pulse' : ''}`}>
                        <option value="very_stable">{t('very_stable', 'Very stable')}</option>
                        <option value="stable">{t('stable', 'Stable')}</option>
                        <option value="moderate">{t('moderate_fluctuation', 'Moderate fluctuation')}</option>
                        <option value="high">{t('high_fluctuation', 'High fluctuation')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="has_temp_control" checked={formData.has_temp_control} onChange={handleChange} />
                      <span>{t('do_you_use_temperature_control_equipment', 'I use temperature control equipment')}</span>
                    </label>
                  </div>

                  {formData.has_temp_control && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div className="form-group">
                        <label className="form-label">{t('control_type', 'Control type')}</label>
                        <select name="temp_control_type" value={formData.temp_control_type} onChange={handleChange} className="form-select">
                          <option value="">{t('select_option', 'Select...')}</option>
                          <option value="heating_only">{t('heating_only', 'Heating only')}</option>
                          <option value="cooling_only">{t('cooling_only', 'Cooling only')}</option>
                          <option value="both">{t('both_heating_cooling', 'Both heating and cooling')}</option>
                          <option value="passive">{t('passive_control', 'Passive control')}</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label">{t('power_source', 'Power source')}</label>
                        <select name="temp_power_source" value={formData.temp_power_source} onChange={handleChange} className="form-select">
                          <option value="">{t('select_option', 'Select...')}</option>
                          <option value="electric">{t('electric', 'Electric')}</option>
                          <option value="solar">{t('solar', 'Solar')}</option>
                          <option value="diesel">{t('diesel', 'Diesel')}</option>
                          <option value="gas">{t('gas', 'Gas')}</option>
                          <option value="other">{t('other', 'Other')}</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="checkbox-label">
                          <input type="checkbox" name="temp_automated" checked={formData.temp_automated} onChange={handleChange} />
                          <span>{t('is_temperature_control_automated', 'Automated control')}</span>
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Step 4: Air Conditions */}
              {step === 4 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>💨 {t('air_conditions', 'Air Conditions')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('air_circulation', 'Air circulation quality')}</label>
                      <select name="air_circulation" value={formData.air_circulation} onChange={handleChange} className={`form-select ${errors.air_circulation ? 'error-pulse' : ''}`}>
                        <option value="excellent">{t('excellent', 'Excellent')}</option>
                        <option value="good">{t('good', 'Good')}</option>
                        <option value="moderate">{t('moderate', 'Moderate')}</option>
                        <option value="poor">{t('poor', 'Poor')}</option>
                        <option value="stagnant">{t('stagnant', 'Stagnant')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('humidity_level_percent', 'Humidity level')} (%)</label>
                      <input type="number" name="humidity_percent" value={formData.humidity_percent} onChange={handleChange} className={`form-input ${errors.humidity_percent ? 'error-pulse' : ''}`} placeholder="0-100" min="0" max="100" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('air_quality', 'Air quality')}</label>
                      <select name="air_quality" value={formData.air_quality} onChange={handleChange} className={`form-select ${errors.air_quality ? 'error-pulse' : ''}`}>
                        <option value="excellent">{t('excellent', 'Excellent')}</option>
                        <option value="good">{t('good', 'Good')}</option>
                        <option value="moderate">{t('moderate', 'Moderate')}</option>
                        <option value="poor">{t('poor', 'Poor')}</option>
                        <option value="unknown">{t('unknown', 'Unknown')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="has_ventilation" checked={formData.has_ventilation} onChange={handleChange} />
                      <span>{t('do_you_use_ventilation_equipment', 'I use ventilation equipment')}</span>
                    </label>
                  </div>

                  {formData.has_ventilation && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div className="form-group">
                        <label className="form-label">{t('ventilation_type', 'Ventilation type')}</label>
                        <select name="ventilation_type" value={formData.ventilation_type} onChange={handleChange} className="form-select">
                          <option value="">{t('select_option', 'Select...')}</option>
                          <option value="exhaust_fan">{t('exhaust_fan', 'Exhaust fan')}</option>
                          <option value="intake_fan">{t('intake_fan', 'Intake fan')}</option>
                          <option value="both">{t('both_exhaust_intake', 'Both exhaust and intake')}</option>
                          <option value="air_conditioning">{t('air_conditioning', 'Air conditioning')}</option>
                          <option value="natural">{t('natural_only', 'Natural only')}</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label">{t('control_method', 'Control method')}</label>
                        <select name="ventilation_control" value={formData.ventilation_control} onChange={handleChange} className="form-select">
                          <option value="">{t('select_option', 'Select...')}</option>
                          <option value="manual">{t('manual', 'Manual')}</option>
                          <option value="timer">{t('timer_based', 'Timer based')}</option>
                          <option value="humidity">{t('humidity_controlled', 'Humidity controlled')}</option>
                          <option value="temperature">{t('temperature_controlled', 'Temperature controlled')}</option>
                          <option value="smart">{t('smart_system', 'Smart system')}</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Step 5: Water Conditions */}
              {step === 5 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>💧 {t('water_conditions', 'Water Conditions')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('watering_frequency', 'Watering frequency')}</label>
                      <select name="watering_frequency" value={formData.watering_frequency} onChange={handleChange} className={`form-select ${errors.watering_frequency ? 'error-pulse' : ''}`}>
                        <option value="daily">{t('daily', 'Daily')}</option>
                        <option value="every_2_days">{t('every_2_days', 'Every 2 days')}</option>
                        <option value="twice_weekly">{t('twice_weekly', 'Twice weekly')}</option>
                        <option value="weekly">{t('weekly', 'Weekly')}</option>
                        <option value="as_needed">{t('as_needed', 'As needed')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('water_amount', 'Water amount per session')}</label>
                      <select name="water_amount" value={formData.water_amount} onChange={handleChange} className={`form-select ${errors.water_amount ? 'error-pulse' : ''}`}>
                        <option value="light_misting">{t('light_misting', 'Light misting')}</option>
                        <option value="moderate">{t('moderate', 'Moderate')}</option>
                        <option value="thorough">{t('thorough', 'Thorough')}</option>
                        <option value="deep_soaking">{t('deep_soaking', 'Deep soaking')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('water_source', 'Water source')}</label>
                      <select name="water_source" value={formData.water_source} onChange={handleChange} className={`form-select ${errors.water_source ? 'error-pulse' : ''}`}>
                        <option value="tap_water">{t('tap_water', 'Tap water')}</option>
                        <option value="filtered_water">{t('filtered_water', 'Filtered water')}</option>
                        <option value="rainwater">{t('rainwater', 'Rainwater')}</option>
                        <option value="well_water">{t('well_water', 'Well water')}</option>
                        <option value="distilled">{t('distilled_water', 'Distilled water')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('water_quality', 'Water quality')}</label>
                      <select name="water_quality" value={formData.water_quality} onChange={handleChange} className={`form-select ${errors.water_quality ? 'error-pulse' : ''}`}>
                        <option value="excellent">{t('excellent', 'Excellent')}</option>
                        <option value="good">{t('good', 'Good')}</option>
                        <option value="moderate">{t('moderate', 'Moderate')}</option>
                        <option value="poor">{t('poor', 'Poor')}</option>
                        <option value="unknown">{t('unknown', 'Unknown')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="has_irrigation" checked={formData.has_irrigation} onChange={handleChange} />
                      <span>{t('do_you_use_irrigation_equipment', 'I use irrigation equipment')}</span>
                    </label>
                  </div>

                  {formData.has_irrigation && (
                    <div className="form-group">
                      <label className="form-label">{t('system_type', 'Irrigation system type')}</label>
                      <select name="irrigation_type" value={formData.irrigation_type} onChange={handleChange} className="form-select">
                        <option value="">{t('select_option', 'Select...')}</option>
                        <option value="drip">{t('drip_system', 'Drip system')}</option>
                        <option value="sprinkler">{t('sprinkler', 'Sprinkler')}</option>
                        <option value="soaker_hose">{t('soaker_hose', 'Soaker hose')}</option>
                        <option value="hand">{t('hand_watering', 'Hand watering')}</option>
                        <option value="automated">{t('automated_system', 'Automated system')}</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Step 6: Soil & Growing Medium */}
              {step === 6 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>🪴 {t('soil_growing_medium', 'Soil & Growing Medium')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('growing_medium_type', 'Growing medium type')}</label>
                      <select name="growing_medium_type" value={formData.growing_medium_type} onChange={handleChange} className={`form-select ${errors.growing_medium_type ? 'error-pulse' : ''}`}>
                        <option value="natural_soil">{t('natural_soil', 'Natural soil')}</option>
                        <option value="potting_mix">{t('potting_mix', 'Potting mix')}</option>
                        <option value="custom_blend">{t('custom_blend', 'Custom blend')}</option>
                        <option value="hydroponic">{t('hydroponic', 'Hydroponic')}</option>
                        <option value="soilless">{t('soilless_mix', 'Soilless mix')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('soil_ph_level', 'Soil pH level')}</label>
                      <select name="soil_ph_level" value={formData.soil_ph_level} onChange={handleChange} className={`form-select ${errors.soil_ph_level ? 'error-pulse' : ''}`}>
                        <option value="acidic">{t('acidic', 'Acidic')}</option>
                        <option value="slightly_acidic">{t('slightly_acidic', 'Slightly acidic')}</option>
                        <option value="neutral">{t('neutral', 'Neutral')}</option>
                        <option value="slightly_alkaline">{t('slightly_alkaline', 'Slightly alkaline')}</option>
                        <option value="alkaline">{t('alkaline', 'Alkaline')}</option>
                        <option value="unknown">{t('unknown', 'Unknown')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('drainage_quality', 'Drainage quality')}</label>
                      <select name="drainage_quality" value={formData.drainage_quality} onChange={handleChange} className={`form-select ${errors.drainage_quality ? 'error-pulse' : ''}`}>
                        <option value="excellent">{t('excellent', 'Excellent')}</option>
                        <option value="good">{t('good', 'Good')}</option>
                        <option value="moderate">{t('moderate', 'Moderate')}</option>
                        <option value="poor">{t('poor', 'Poor')}</option>
                        <option value="waterlogged">{t('waterlogged', 'Waterlogged')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('soil_depth_cm', 'Soil depth')} (cm)</label>
                      <input type="number" name="soil_depth" value={formData.soil_depth} onChange={handleChange} className={`form-input ${errors.soil_depth ? 'error-pulse' : ''}`} placeholder="5-200" min="5" max="200" />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="has_tested_ph" checked={formData.has_tested_ph} onChange={handleChange} />
                      <span>{t('have_you_tested_soil_ph', 'I have tested soil pH')}</span>
                    </label>
                  </div>

                  {formData.has_tested_ph && (
                    <div className="form-group">
                      <label className="form-label">{t('measured_ph_value', 'Measured pH value')}</label>
                      <input type="number" name="measured_ph" value={formData.measured_ph} onChange={handleChange} className={`form-input ${errors.measured_ph ? 'error-pulse' : ''}`} placeholder="0-14" min="0" max="14" step="0.1" />
                    </div>
                  )}
                </div>
              )}

              {/* Step 7: Nutrient Management */}
              {step === 7 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>🧪 {t('nutrient_management', 'Nutrient Management')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('fertilizer_approach', 'Fertilizer approach')}</label>
                      <select name="fertilizer_approach" value={formData.fertilizer_approach} onChange={handleChange} className={`form-select ${errors.fertilizer_approach ? 'error-pulse' : ''}`}>
                        <option value="organic_only">{t('organic_only', 'Organic only')}</option>
                        <option value="synthetic_only">{t('synthetic_only', 'Synthetic only')}</option>
                        <option value="mixed_approach">{t('mixed_approach', 'Mixed approach')}</option>
                        <option value="minimal_fertilizer">{t('minimal_fertilizer', 'Minimal fertilizer')}</option>
                        <option value="none">{t('none', 'None')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('fertilizing_frequency', 'Fertilizing frequency')}</label>
                      <select name="fertilizing_frequency" value={formData.fertilizing_frequency} onChange={handleChange} className={`form-select ${errors.fertilizing_frequency ? 'error-pulse' : ''}`}>
                        <option value="weekly">{t('weekly', 'Weekly')}</option>
                        <option value="biweekly">{t('biweekly', 'Biweekly')}</option>
                        <option value="monthly">{t('monthly', 'Monthly')}</option>
                        <option value="seasonally">{t('seasonally', 'Seasonally')}</option>
                        <option value="as_needed">{t('as_needed', 'As needed')}</option>
                        <option value="never">{t('never', 'Never')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('npk_balance_focus', 'NPK balance focus')}</label>
                      <select name="npk_balance" value={formData.npk_balance} onChange={handleChange} className="form-select">
                        <option value="">{t('skip', 'Skip')}</option>
                        <option value="high_nitrogen">{t('high_nitrogen', 'High nitrogen')}</option>
                        <option value="balanced">{t('balanced_npk', 'Balanced NPK')}</option>
                        <option value="phosphorus_focus">{t('phosphorus_focus', 'Phosphorus focus')}</option>
                        <option value="potassium_focus">{t('potassium_focus', 'Potassium focus')}</option>
                        <option value="unknown">{t('unknown', 'Unknown')}</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input type="checkbox" name="tests_nutrients" checked={formData.tests_nutrients} onChange={handleChange} />
                      <span>{t('do_you_test_nutrient_levels', 'I test nutrient levels')}</span>
                    </label>
                  </div>

                  {formData.tests_nutrients && (
                    <div className="form-group">
                      <label className="form-label">{t('testing_method', 'Testing method')}</label>
                      <select name="testing_method" value={formData.testing_method} onChange={handleChange} className="form-select">
                        <option value="">{t('select_option', 'Select...')}</option>
                        <option value="soil_kit">{t('soil_test_kit', 'Soil test kit')}</option>
                        <option value="lab">{t('professional_lab', 'Professional lab')}</option>
                        <option value="digital_meter">{t('digital_meter', 'Digital meter')}</option>
                        <option value="appearance">{t('plant_appearance', 'Plant appearance')}</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {/* Step 8: Biological Factors */}
              {step === 8 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>🧬 {t('biological_factors', 'Biological Factors')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('pest_management_approach', 'Pest management approach')}</label>
                      <select name="pest_management" value={formData.pest_management} onChange={handleChange} className={`form-select ${errors.pest_management ? 'error-pulse' : ''}`}>
                        <option value="preventive">{t('preventive_only', 'Preventive only')}</option>
                        <option value="organic">{t('organic_methods', 'Organic methods')}</option>
                        <option value="integrated">{t('integrated_management', 'Integrated management')}</option>
                        <option value="chemical">{t('chemical_when_needed', 'Chemical when needed')}</option>
                        <option value="minimal">{t('minimal_intervention', 'Minimal intervention')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('disease_prevention_method', 'Disease prevention method')}</label>
                      <select name="disease_prevention" value={formData.disease_prevention} onChange={handleChange} className={`form-select ${errors.disease_prevention ? 'error-pulse' : ''}`}>
                        <option value="hygiene">{t('good_hygiene', 'Good hygiene')}</option>
                        <option value="resistant">{t('resistant_varieties', 'Resistant varieties')}</option>
                        <option value="organic_treatments">{t('organic_treatments', 'Organic treatments')}</option>
                        <option value="chemical">{t('chemical_prevention', 'Chemical prevention')}</option>
                        <option value="natural">{t('natural_immunity', 'Natural immunity')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('beneficial_insects_approach', 'Beneficial insects approach')}</label>
                      <select name="beneficial_insects" value={formData.beneficial_insects} onChange={handleChange} className="form-select">
                        <option value="">{t('skip', 'Skip')}</option>
                        <option value="actively_encourage">{t('actively_encourage', 'Actively encourage')}</option>
                        <option value="welcome_natural">{t('welcome_natural', 'Welcome natural')}</option>
                        <option value="neutral">{t('neutral', 'Neutral')}</option>
                        <option value="discourage">{t('discourage', 'Discourage')}</option>
                        <option value="unknown">{t('unknown', 'Unknown')}</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 9: Space & Setup */}
              {step === 9 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>🏗️ {t('space_setup', 'Space & Setup')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('space_type', 'Space type')}</label>
                      <select name="space_type" value={formData.space_type} onChange={handleChange} className={`form-select ${errors.space_type ? 'error-pulse' : ''}`}>
                        <option value="windowsill">{t('windowsill', 'Windowsill')}</option>
                        <option value="room_corner">{t('room_corner', 'Room corner')}</option>
                        <option value="dedicated_room">{t('dedicated_room', 'Dedicated room')}</option>
                        <option value="greenhouse">{t('greenhouse', 'Greenhouse')}</option>
                        <option value="basement">{t('basement', 'Basement')}</option>
                        <option value="other">{t('other', 'Other')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('approximate_area', 'Approximate area')} (m²)</label>
                      <input type="number" name="space_area" value={formData.space_area} onChange={handleChange} className="form-input" placeholder="0.1-1000" min="0.1" max="1000" step="0.1" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('planting_density', 'Planting density')}</label>
                      <select name="planting_density" value={formData.planting_density} onChange={handleChange} className={`form-select ${errors.planting_density ? 'error-pulse' : ''}`}>
                        <option value="high">{t('high_density', 'High density')}</option>
                        <option value="moderate">{t('moderate_density', 'Moderate density')}</option>
                        <option value="low">{t('low_density', 'Low density')}</option>
                        <option value="single">{t('single_plant', 'Single plant')}</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 10: Management Practices */}
              {step === 10 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>👨‍🌾 {t('management_practices', 'Management Practices')}</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label">{t('experience_level', 'Experience level')}</label>
                      <select name="experience_level" value={formData.experience_level} onChange={handleChange} className={`form-select ${errors.experience_level ? 'error-pulse' : ''}`}>
                        <option value="beginner">{t('beginner', 'Beginner')}</option>
                        <option value="some_experience">{t('some_experience', 'Some experience')}</option>
                        <option value="experienced">{t('experienced', 'Experienced')}</option>
                        <option value="expert">{t('expert', 'Expert')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('time_commitment_weekly_hours', 'Time commitment (weekly hours)')}</label>
                      <input type="number" name="time_commitment" value={formData.time_commitment} onChange={handleChange} className={`form-input ${errors.time_commitment ? 'error-pulse' : ''}`} placeholder="0-40" min="0" max="40" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('monitoring_frequency', 'Monitoring frequency')}</label>
                      <select name="monitoring_frequency" value={formData.monitoring_frequency} onChange={handleChange} className={`form-select ${errors.monitoring_frequency ? 'error-pulse' : ''}`}>
                        <option value="daily">{t('daily', 'Daily')}</option>
                        <option value="every_few_days">{t('every_few_days', 'Every few days')}</option>
                        <option value="weekly">{t('weekly', 'Weekly')}</option>
                        <option value="biweekly">{t('biweekly', 'Biweekly')}</option>
                        <option value="monthly">{t('monthly', 'Monthly')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('record_keeping', 'Record keeping')}</label>
                      <select name="record_keeping" value={formData.record_keeping} onChange={handleChange} className="form-select">
                        <option value="">{t('skip', 'Skip')}</option>
                        <option value="detailed">{t('detailed_records', 'Detailed records')}</option>
                        <option value="basic_notes">{t('basic_notes', 'Basic notes')}</option>
                        <option value="mental">{t('mental_notes', 'Mental notes')}</option>
                        <option value="none">{t('no_records', 'No records')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('planned_growing_duration_months', 'Planned growing duration (months)')}</label>
                      <input type="number" name="growing_duration" value={formData.growing_duration} onChange={handleChange} className={`form-input ${errors.growing_duration ? 'error-pulse' : ''}`} placeholder="1-120" min="1" max="120" />
                    </div>
                  </div>

                </div>
              )}

              {/* Step 11: Equipment */}
              {step === 11 && (
                <div>
                  <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>⚙️ {t('equipment_details', 'Equipment Details')}</h4>
                  
                  {equipment.length > 0 && (
                    <div style={{ marginBottom: '1.5rem' }}>
                      <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                        {t('total_equipment_count', 'Equipment added')}: {equipment.length}
                      </p>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {equipment.map(item => (
                          <div key={item.id} style={{ padding: '0.75rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <strong>{item.name}</strong>
                              <span style={{ marginLeft: '0.5rem', color: '#6b7280', fontSize: '0.875rem' }}>({item.category})</span>
                            </div>
                            <button type="button" onClick={() => removeEquipment(item.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}>
                              <Trash2 size={18} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {!showEquipmentForm ? (
                    <button type="button" onClick={() => setShowEquipmentForm(true)} className="btn btn-secondary" style={{ width: '100%' }}>
                      <Plus size={18} /> {t('add_equipment_item', 'Add Equipment')}
                    </button>
                  ) : (
                    <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', marginTop: '1rem' }}>
                      <div className="form-group">
                        <label className="form-label">{t('equipment_name', 'Equipment name')}</label>
                        <input type="text" name="name" value={currentEquipment.name} onChange={handleEquipmentChange} className="form-input" placeholder={t('equipment_name', 'e.g., LED Panel, Water Pump')} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">{t('category', 'Category')}</label>
                        <select name="category" value={currentEquipment.category} onChange={handleEquipmentChange} className="form-select">
                          <option value="">{t('select_option', 'Select category...')}</option>
                          <option value="lighting">{t('lighting', 'Lighting')}</option>
                          <option value="climate_control">{t('climate_control', 'Climate control')}</option>
                          <option value="irrigation">{t('irrigation', 'Irrigation')}</option>
                          <option value="monitoring">{t('monitoring', 'Monitoring')}</option>
                          <option value="support">{t('support_structure', 'Support structure')}</option>
                          <option value="other">{t('other', 'Other')}</option>
                        </select>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div className="form-group">
                          <label className="form-label">{t('power_source', 'Power source')}</label>
                          <select name="power_source" value={currentEquipment.power_source} onChange={handleEquipmentChange} className="form-select">
                            <option value="">{t('skip', 'Skip')}</option>
                            <option value="electric">{t('electric', 'Electric')}</option>
                            <option value="solar">{t('solar', 'Solar')}</option>
                            <option value="battery">{t('battery', 'Battery')}</option>
                            <option value="manual">{t('manual', 'Manual')}</option>
                            <option value="other">{t('other', 'Other')}</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label className="form-label">{t('automation_level', 'Automation level')}</label>
                          <select name="automation_level" value={currentEquipment.automation_level} onChange={handleEquipmentChange} className="form-select">
                            <option value="">{t('skip', 'Skip')}</option>
                            <option value="fully_automatic">{t('fully_automatic', 'Fully automatic')}</option>
                            <option value="semi_automatic">{t('semi_automatic', 'Semi automatic')}</option>
                            <option value="manual">{t('manual_control', 'Manual control')}</option>
                            <option value="timer">{t('basic_timer', 'Basic timer')}</option>
                          </select>
                        </div>
                      </div>
                      <div className="form-group">
                        <label className="form-label">{t('installation_date', 'Installation date')} ({t('optional', 'optional')})</label>
                        <input type="date" name="installation_date" value={currentEquipment.installation_date} onChange={handleEquipmentChange} className="form-input" />
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                        <button type="button" onClick={addEquipment} className="btn btn-primary" disabled={!currentEquipment.name || !currentEquipment.category} style={{ flex: 1 }}>
                          {t('equipment_added', 'Add')}
                        </button>
                        <button type="button" onClick={() => { setShowEquipmentForm(false); setCurrentEquipment({ name: '', category: '', power_source: '', automation_level: '', installation_date: '' }); }} className="btn btn-secondary" style={{ flex: 1 }}>
                          {t('operation_cancelled', 'Cancel')}
                        </button>
                      </div>
                    </div>
                  )}

                  {equipment.length === 0 && !showEquipmentForm && (
                    <p style={{ textAlign: 'center', color: '#6b7280', marginTop: '1rem', fontSize: '0.875rem' }}>
                      {t('equipment_collection_intro', 'No equipment added yet. Add your special equipment to get better recommendations.')}
                    </p>
                  )}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <div className="form-nav">
          {step > 1 ? (
            <button type="button" onClick={prevStep} className="btn btn-secondary">
              <ArrowLeft size={18} />
              {t('back', 'Back')}
            </button>
          ) : (
            <div />
          )}
          
          <button
            type="button"
            onClick={nextStep}
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader className="spinner" size={18} />
                {t('analyzing', 'Analyzing...')}
              </>
            ) : step === totalSteps ? (
              <>
                {t('submit', 'Get Recommendations')}
                <ArrowRight size={18} />
              </>
            ) : (
              <>
                {t('next', 'Next')}
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
        </>
      )}
      </motion.div>

      <style jsx>{`
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
        }
        
        .checkbox-label input[type="checkbox"] {
          width: 1.25rem;
          height: 1.25rem;
          cursor: pointer;
        }
        
        .checkbox-label span {
          font-size: 0.875rem;
        }

        @keyframes pulse-shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }

        .error-pulse {
          border-color: #ef4444 !important;
          animation: pulse-shake 0.4s ease;
          box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
        }
      `}</style>
    </div>
  );
}

export default PlantForm;