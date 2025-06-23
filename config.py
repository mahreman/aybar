import json
import os

APP_CONFIG = {}

DEFAULT_CONFIG = {
    "LLM_API_URL": "http://localhost:1234/v1/completions",
    "THINKER_MODEL_NAME": "mistral-7b-instruct-v0.2",
    "ENGINEER_MODEL_NAME": "Qwen2.5-Coder-7B-Instruct-GGUF",
    "VISION_MODEL_NAME": "ggml_bakllava-1",
    "MAX_TOKENS": 4096,
    "TIMEOUT": 600000,
    "LLM_CACHE_SIZE": 128,
    "MAX_TURNS": 20000,
    "DB_FILE": "aybar_memory.db",
    "MEMORY_FILE": "aybar_memory.json",
    "EMOTIONS_FILE": "aybar_emotions.json",
    "DREAMS_FILE": "aybar_dreams.json",
    "HOLOGRAPHIC_MEMORY_FILE": "aybar_holographic_memory.json",
    "NEURAL_ACTIVATIONS_FILE": "neural_activations.json",
    "SEMANTIC_MEMORY_FILE": "aybar_semantic_memory.json",
    "PROCEDURAL_MEMORY_FILE": "aybar_procedural_memory.json",
    "PROACTIVE_EVOLUTION_RATE": 0.02,
    "EPISODIC_MEMORY_LIMIT": 200,
    "SEMANTIC_MEMORY_LIMIT": 100,
    "PROCEDURAL_MEMORY_LIMIT": 50,
    "EMOTIONAL_MEMORY_LIMIT": 500,
    "DREAM_MEMORY_LIMIT": 50,
    "HOLOGRAPHIC_MEMORY_LIMIT": 50,
    "NEURAL_MEMORY_LIMIT": 200,
    "CREATIVE_MEMORY_LIMIT": 50,
    "PROACTIVE_EVOLUTION_CHANCE": 0.01,
    "FILE_LOCK_TIMEOUT": 10,
    "BATCH_SAVE_INTERVAL": 10,
    "DOPAMINE_CURIOSITY_BOOST": 0.05,
    "DOPAMINE_SATISFACTION_BOOST": 0.1,
    "DOPAMINE_LEARNING_BOOST": 0.08,
    "DOPAMINE_HOME_RATE": 0.02,
    "SEROTONIN_SATISFACTION_BOOST": 0.07,
    "SEROTONIN_FATIGUE_DROP": 0.04,
    "SEROTONIN_HOME_RATE": 0.03,
    "OXYTOCIN_SOCIAL_BOOST": 0.05,
    "OXYTOCIN_HOME_RATE": 0.01,
    "CORTISOL_ANXIETY_BOOST": 0.08,
    "CORTISOL_FATIGUE_BOOST": 0.06,
    "CORTISOL_HOME_RATE": 0.02,
    "GLUTAMATE_COGNITIVE_BOOST": 0.05,
    "GLUTAMATE_ANXIETY_BOOST": 0.03,
    "GLUTAMATE_HOME_RATE": 0.02,
    "GABA_COGNITIVE_REDUCTION": 0.04,
    "GABA_ANXIETY_DROP": 0.02,
    "GABA_HOME_RATE": 0.02,
    "CHEMICAL_CHANGE_LIMIT": 0.1,
    "CHEMICAL_MIN_VALUE": 0.0,
    "CHEMICAL_MAX_VALUE": 1.0,
    "EMOTION_DECAY_RATE": 0.01,
    "EMOTION_MIN_VALUE": 0.0,
    "EMOTION_MAX_VALUE": 10.0,
    "CURIOSITY_THRESHOLD": 7.0,
    "SATISFACTION_THRESHOLD": 7.0,
    "FATIGUE_THRESHOLD": 6.0,
    "ANXIETY_THRESHOLD": 6.0,
    "CURIOSITY_BOOST": 0.1,
    "CONFUSION_BOOST": 0.1,
    "ANXIETY_BOOST": 0.08,
    "WONDER_BOOST": 0.07,
    "FATIGUE_BOOST": 0.05,
    "FATIGUE_REST_EFFECT": 0.2,
    "SELF_AWARENESS_BOOST": 0.05,
    "QUESTIONING_DEPTH_BOOST": 0.05,
    "PATTERN_RECOGNITION_BOOST": 0.05,
    "PHILOSOPHICAL_TENDENCY_BOOST": 0.05,
    "CI_EMOTIONAL_DIVERSITY_WEIGHT": 0.3,
    "CI_MEMORY_DEPTH_WEIGHT": 0.2,
    "CI_SELF_AWARENESS_WEIGHT": 0.3,
    "CI_TEMPORAL_CONSISTENCY_WEIGHT": 0.2,
    "CONSCIOUSNESS_DECAY": 0.02,
    "CONSCIOUSNESS_BOOST_INTERACTION": 0.1,
    "CONSCIOUSNESS_BOOST_INSIGHT": 0.15,
    "SLEEP_DEBT_PER_TURN": 0.05,
    "SLEEP_THRESHOLD": 7.0,
    "SLEEP_DURATION_TURNS": 3,
    "DEEP_SLEEP_REDUCTION": 0.5,
    "EXISTENTIAL_CRISIS_THRESHOLD": 7.0,
    "CRISIS_QUESTION_THRESHOLD": 0.6,
    "SENSORY_ACUITY_BOOST": 0.05,
    "SENSORY_ACTIVITY_DECAY": 0.01,
    "MOTOR_CAPABILITY_BOOST": 0.05,
    "DEFAULT_EMBODIMENT_CONFIG": {"visual": True, "auditory": True, "tactile": True},
    "INSIGHT_THRESHOLD": 0.7,
    "CONSOLIDATION_INTERVAL": 20,
    "USER_INTERVENTION_RATE": 1000000000000000000000,
    "SUMMARY_INTERVAL": 100,
    "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY", "sk_abd025de949665cae6a25fd4275f57885496f4ddca333659"),
    "ELEVENLABS_VOICE_MAP": {
        "varsayilan": "75SIZa3vvET95PHhf1yD",
        "wonder": "DUnzBkwtjRWXPr6wRbmL",
        "satisfaction": "flZTNq2uzsrbxgFGPOUD",
        "existential_anxiety": "ZsYcqahfiS2dy4J6XYC5",
        "curiosity": "2EiwWnXFnvU5JabPnv8n"
    },
    "ELEVENLABS_MODEL": "eleven_multilingual_v2",
    "WEB_SURFER_HEADLESS": False,
    "WEB_ELEMENT_WAIT_TIMEOUT": 10,
    "HARDWARE_API_URL": "http://localhost:5151",
    "EVOLUTION_TEST_TIMEOUT": 60,
    "EVOLUTION_MAX_CONSECUTIVE_FAILURES": 3,
    "CYCLE_DELAY_SECONDS": 1,
    "LLM_FUNCTION_CALLING_MAX_RECURSION": 3,
    "LLM_ERROR_COOLDOWN_SECONDS": 60,
    "LLM_MAX_RETRY_ATTEMPTS": 3
}

def load_config(config_file="aybar_config.json"):
    """Yapılandırmayı JSON dosyasından yükler ve APP_CONFIG'i günceller."""
    global APP_CONFIG
    APP_CONFIG.update(DEFAULT_CONFIG)

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            APP_CONFIG.update(user_config)
            print(f"🔧 Yapılandırma '{config_file}' dosyasından yüklendi.")
        except json.JSONDecodeError:
            print(f"⚠️ '{config_file}' dosyasında JSON format hatası. Varsayılan yapılandırma kullanılacak.")
        except Exception as e:
            print(f"⚠️ '{config_file}' yüklenirken hata: {e}. Varsayılan yapılandırma kullanılacak.")
    else:
        print(f"ℹ️ '{config_file}' bulunamadı. Varsayılan yapılandırma kullanılacak ve oluşturulacak.")
        save_default_config(config_file)

def save_default_config(config_file="aybar_config.json"):
    """Varsayılan yapılandırmayı bir JSON dosyasına kaydeder."""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        print(f"📝 Varsayılan yapılandırma '{config_file}' dosyasına kaydedildi.")
    except Exception as e:
        print(f"⚠️ Varsayılan yapılandırma kaydedilirken hata: {e}")

load_config()

if __name__ == '__main__':
    print("Aybar Yapılandırma Modülü")
    print("="*30)
    if not os.path.exists("aybar_config.json"):
        print("'aybar_config.json' bulunamadı. Varsayılan yapılandırma oluşturuluyor...")
        save_default_config("aybar_config.json")
    else:
        print("'aybar_config.json' zaten mevcut.")
        print("Mevcut yapılandırma:")
        for key, value in APP_CONFIG.items():
            print(f"  {key}: {value}")
    print("\nBu modülü doğrudan çalıştırmak yerine, ana Aybar uygulamasından import edin.")
