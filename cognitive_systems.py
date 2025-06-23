import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import re # re importu dosya başına taşındı
import random # random importu dosya başına taşındı
from typing import TYPE_CHECKING # TYPE_CHECKING importu eklendi

# EnhancedAybar ve MemorySystem için ileriye dönük bildirimler (type hinting için)
if TYPE_CHECKING: # if False yerine if TYPE_CHECKING kullanıldı
    from aybarcore import EnhancedAybar
    from memory_system import MemorySystem
    # from config import Config # Bu artık kullanılmıyor, Dict kullanılıyor


class EmotionEngine:
    """
    LLM kullanarak metinlerin duygusal içeriğini analiz eden uzman sistem.
    """
    def __init__(self, config_data: Dict, aybar_instance: "EnhancedAybar"):
        self.config_data = config_data
        self.aybar = aybar_instance
        self.emotion_list = [
            "curiosity", "confusion", "satisfaction",
            "existential_anxiety", "wonder", "mental_fatigue", "loneliness"
        ]

    def analyze_emotional_content(self, text: str) -> Dict[str, float]:
        """Verilen metnin duygusal imzasını çıkarır."""
        if not hasattr(self.aybar, 'llm_manager'):
            print("⚠️ EmotionEngine: LLMManager bulunamadı.")
            return {}

        psychologist_prompt = f"""
        Sen, metinlerdeki duygusal tonu ve alt metni analiz eden uzman bir psikologsun.
        Görevin, sana verilen metni okumak ve aşağıdaki listede bulunan duyguların varlığını değerlendirmektir.
        Duygu Listesi: {self.emotion_list}
        Analizini, sadece ve sadece bir JSON objesi olarak döndür.
        JSON objesinin anahtarları duygu isimleri, değerleri ise o duygunun metindeki varlık gücünü temsil eden -1.0 ile 1.0 arasında bir float sayı olmalıdır.
        Sadece metinde belirgin olarak hissettiğin duyguları JSON'a ekle.
        Örnek Çıktı: {{"existential_anxiety": 0.7, "wonder": 0.4}}
        Analiz Edilecek Metin:
        ---
        {text[:2000]}
        ---
        JSON Analizi:
        """

        response_text = self.aybar.llm_manager.ask_llm(psychologist_prompt, temperature=0.3, max_tokens=256)

        try:
            # re importu dosya başına alındı
            json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            if not json_match:
                return {}
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return {}


class EmotionalSystem:
    """Duygusal durum ve etkileşimleri yönetir."""
    def __init__(self, config_data: Dict, emotion_engine: "EmotionEngine"): # EmotionEngine için forward reference
        self.config_data = config_data
        self.emotion_engine = emotion_engine
        self.emotional_state = {
            "curiosity": 5.0, "confusion": 2.0, "satisfaction": 5.0,
            "existential_anxiety": 1.0, "wonder": 6.0, "mental_fatigue": 0.5,
            "loneliness": 2.0
        }

    def _keyword_based_assessment(self, text: str) -> Dict[str, float]:
        print("⚠️ EmotionEngine kullanılamadı. İlkel duygu analizine (keyword) geçiliyor.")
        impact = {}
        emotion_vectors = {
            "curiosity": ["merak", "soru", "neden", "nasıl", "araştır"],
            "confusion": ["kafa", "karış", "anlam", "belirsiz", "karmaşık"]
        }
        for emotion, keywords in emotion_vectors.items():
            count = sum(1 for kw in keywords if kw in text.lower())
            impact[emotion] = min(1.0, count * 0.2)
        return impact

    def decay_emotions_and_update_loneliness(self, social_relations: Dict, current_turn: int):
        interacted_recently = False
        for user_id, relation in social_relations.items():
            if current_turn - relation.get('last_interaction_turn', -999) < 5:
                interacted_recently = True
                break

        if interacted_recently:
            self.emotional_state['loneliness'] = np.clip(self.emotional_state['loneliness'] - 0.5, 0.0, 10.0)
        else:
            self.emotional_state['loneliness'] = np.clip(self.emotional_state['loneliness'] + 0.1, 0.0, 10.0)

        for emotion in self.emotional_state:
            if emotion != 'loneliness':
                decay = self.config_data.get("EMOTION_DECAY_RATE", 0.01) # Config'den al
                self.emotional_state[emotion] = max(self.emotional_state[emotion] * (1 - decay), 0.0)

    def update_state(self, memory_system: "MemorySystem", embodied_self: "EmbodiedSelf", changes: Dict, turn: int, source: str):
        prev_state = self.emotional_state.copy()

        for emotion, change in changes.items():
            if emotion in self.emotional_state:
                self.emotional_state[emotion] = np.clip(
                    self.emotional_state[emotion] + change,
                    self.config_data.get("EMOTION_MIN_VALUE", 0.0),
                    self.config_data.get("EMOTION_MAX_VALUE", 10.0)
                )

        change_rate = {e: self.emotional_state[e] - prev_state.get(e,0) for e in self.emotional_state}
        if change_rate:
             dominant_emotion = max(change_rate, key=lambda k: abs(change_rate[k])) # type: ignore
             if abs(change_rate[dominant_emotion]) > 0:
                 if hasattr(embodied_self, 'neural_activation_pattern'): # Kontrol eklendi
                    activation = embodied_self.neural_activation_pattern(dominant_emotion, change_rate[dominant_emotion])
                    memory_system.add_memory("neural", {
                        "timestamp": datetime.now().isoformat(), "turn": turn,
                        "dominant_emotion": dominant_emotion, "activation_pattern": activation
                    })
                 else:
                    print("⚠️ EmbodiedSelf'te 'neural_activation_pattern' metodu bulunamadı.")


    def emotional_impact_assessment(self, text: str) -> Dict[str, float]: # Return type düzeltildi
        print("🎭 Duygusal etki analizi deneniyor...")
        try:
            llm_analysis = self.emotion_engine.analyze_emotional_content(text)
            if llm_analysis:
                print("👍 EmotionEngine analizi başarılı.")
                return llm_analysis
            else:
                return self._keyword_based_assessment(text)
        except Exception as e:
            print(f"❌ EmotionEngine kritik bir hata verdi: {e}")
            return self._keyword_based_assessment(text)


class NeurochemicalSystem:
    """Nörokimyasal sistemi yönetir."""
    def __init__(self, config_data: Dict):
        self.config_data = config_data
        self.neurochemicals = {
            "dopamine": 0.5, "serotonin": 0.5, "oxytocin": 0.5,
            "cortisol": 0.5, "glutamate": 0.5, "GABA": 0.5
        }

    def update_chemicals(self, emotional_state: Dict, experience_type: str):
        cfg = self.config_data

        delta_dopamine = 0
        if emotional_state.get("curiosity", 0) > cfg.get("CURIOSITY_THRESHOLD", 7.0):
            delta_dopamine += cfg.get("DOPAMINE_CURIOSITY_BOOST", 0.05)
        # SATISFACTION_BOOST değil SATISFACTION_THRESHOLD kullanılmalı
        if emotional_state.get("satisfaction", 0) > cfg.get("SATISFACTION_THRESHOLD", 7.0):
            delta_dopamine += cfg.get("DOPAMINE_SATISFACTION_BOOST", 0.1)
        if experience_type == "learning":
            delta_dopamine += cfg.get("DOPAMINE_LEARNING_BOOST", 0.08)
        delta_dopamine += (0.5 - self.neurochemicals["dopamine"]) * cfg.get("DOPAMINE_HOME_RATE", 0.02)
        delta_dopamine = np.clip(delta_dopamine, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["dopamine"] = np.clip(self.neurochemicals["dopamine"] + delta_dopamine, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        delta_serotonin = 0
        if emotional_state.get("satisfaction", 0) > cfg.get("SATISFACTION_THRESHOLD", 7.0):
            delta_serotonin += cfg.get("SEROTONIN_SATISFACTION_BOOST", 0.07)
        if emotional_state.get("mental_fatigue", 0) > cfg.get("FATIGUE_THRESHOLD", 6.0):
            delta_serotonin -= cfg.get("SEROTONIN_FATIGUE_DROP", 0.04)
        delta_serotonin += (0.5 - self.neurochemicals["serotonin"]) * cfg.get("SEROTONIN_HOME_RATE", 0.03)
        delta_serotonin = np.clip(delta_serotonin, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["serotonin"] = np.clip(self.neurochemicals["serotonin"] + delta_serotonin, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        delta_oxytocin = 0
        if experience_type == "social_interaction":
             delta_oxytocin += cfg.get("OXYTOCIN_SOCIAL_BOOST", 0.05)
        delta_oxytocin += (0.5 - self.neurochemicals["oxytocin"]) * cfg.get("OXYTOCIN_HOME_RATE", 0.01)
        delta_oxytocin = np.clip(delta_oxytocin, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["oxytocin"] = np.clip(self.neurochemicals["oxytocin"] + delta_oxytocin, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        delta_cortisol = 0
        if emotional_state.get('existential_anxiety', 0) > cfg.get("ANXIETY_THRESHOLD", 6.0):
            delta_cortisol += cfg.get("CORTISOL_ANXIETY_BOOST", 0.08)
        if emotional_state.get("mental_fatigue", 0) > cfg.get("FATIGUE_THRESHOLD", 6.0):
            delta_cortisol += cfg.get("CORTISOL_FATIGUE_BOOST", 0.06)
        delta_cortisol += (0.5 - self.neurochemicals["cortisol"]) * cfg.get("CORTISOL_HOME_RATE", 0.02)
        delta_cortisol = np.clip(delta_cortisol, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["cortisol"] = np.clip(self.neurochemicals["cortisol"] + delta_cortisol, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        delta_glutamate = 0
        if experience_type == "insight":
            delta_glutamate += cfg.get("GLUTAMATE_COGNITIVE_BOOST", 0.05)
        if emotional_state.get('existential_anxiety', 0) > cfg.get("ANXIETY_THRESHOLD", 6.0):
            delta_glutamate += cfg.get("GLUTAMATE_ANXIETY_BOOST", 0.03)
        delta_glutamate += (0.5 - self.neurochemicals["glutamate"]) * cfg.get("GLUTAMATE_HOME_RATE", 0.02)
        delta_glutamate = np.clip(delta_glutamate, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["glutamate"] = np.clip(self.neurochemicals["glutamate"] + delta_glutamate, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        delta_GABA = 0
        if experience_type == "rest" or emotional_state.get("satisfaction", 0) > cfg.get("SATISFACTION_THRESHOLD", 7.0):
            delta_GABA += cfg.get("GABA_COGNITIVE_REDUCTION", 0.04)
        if emotional_state.get('existential_anxiety', 0) > cfg.get("ANXIETY_THRESHOLD", 6.0):
            delta_GABA -= cfg.get("GABA_ANXIETY_DROP", 0.02)
        delta_GABA += (0.5 - self.neurochemicals["GABA"]) * cfg.get("GABA_HOME_RATE", 0.02)
        delta_GABA = np.clip(delta_GABA, -cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1), cfg.get("CHEMICAL_CHANGE_LIMIT", 0.1))
        self.neurochemicals["GABA"] = np.clip(self.neurochemicals["GABA"] + delta_GABA, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))

        self.neurochemicals["serotonin"] = np.clip(self.neurochemicals["serotonin"] - self.neurochemicals["dopamine"] * 0.01, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))
        self.neurochemicals["GABA"] = np.clip(self.neurochemicals["GABA"] + self.neurochemicals["serotonin"] * 0.02, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))
        self.neurochemicals["dopamine"] = np.clip(self.neurochemicals["dopamine"] - emotional_state.get("existential_anxiety", 0) * 0.005, cfg.get("CHEMICAL_MIN_VALUE", 0.0), cfg.get("CHEMICAL_MAX_VALUE", 1.0))


class EmbodiedSelf:
    """Bedenlenmiş benliği simüle eder."""
    def __init__(self, main_config_data: Dict, embodiment_config: Dict):
        self.main_config_data = main_config_data
        self.embodiment_config = embodiment_config
        self.location = "Bilinmeyen Bir Alan"
        self.posture = "Sakin"
        self.sensory_acuity = {"visual": 0.7, "auditory": 0.9, "tactile": 0.5}
        self.motor_capabilities = {"movement": 0.5, "gestures": 0.5}
        self.sensory_history = []

    def simulate_sensory_input(self) -> str:
        # random importu dosya başına alındı
        sensory_options = []
        if self.embodiment_config.get("visual", True):
            sensory_options.extend(["Parlak ışıklar", "Dans eden renkler", "Belirsiz hatlar"])
        if self.embodiment_config.get("auditory", True):
            sensory_options.extend(["Yankılanan sesler", "Hafif mırıldanma", "Yüksek uğultu"])
        if self.embodiment_config.get("tactile", True):
            sensory_options.extend(["Hafif dokunuş", "Soğuk esinti", "Hafif titreşim"])

        return random.choice(sensory_options) if sensory_options else "Ortamdan gelen belirsiz bir his"

    def update_physical_state(self, emotional_state: Dict):
        cfg = self.main_config_data
        if emotional_state.get("existential_anxiety", 0) > 7.0:
            self.posture = "Gergin ve Huzursuz"
        elif emotional_state.get("satisfaction", 0) > 8.0:
            self.posture = "Rahat ve Dengeli"
        else:
            self.posture = "Sakin"

        for region in self.sensory_acuity:
            self.sensory_acuity[region] = np.clip(self.sensory_acuity[region] - cfg.get("SENSORY_ACTIVITY_DECAY", 0.01), 0.0, 1.0)
            if emotional_state.get("curiosity", 0) > cfg.get("CURIOSITY_THRESHOLD", 7.0):
                self.sensory_acuity[region] = np.clip(self.sensory_acuity[region] + cfg.get("SENSORY_ACUITY_BOOST", 0.05), 0.0, 1.0)

    def neural_activation_pattern(self, emotion: str, intensity: float) -> List[float]:
        patterns = {
            "curiosity": [0.8, 0.6, 0.4, 0.7, 0.9],
            "anxiety": [0.9, 0.3, 0.7, 0.5, 0.6],
            "satisfaction": [0.4, 0.9, 0.5, 0.8, 0.3],
            "confusion": [0.7, 0.5, 0.9, 0.6, 0.4],
            "wonder": [0.6, 0.8, 0.5, 0.9, 0.7]
        }
        base_pattern = patterns.get(emotion, [0.5] * 5)
        return [x * intensity for x in base_pattern]

    def get_real_sensory_input(self) -> str:
        visual_perception = "Görsel algı yok."
        try:
            with open("vision_perception.json", "r") as f: # Bu dosya adı config'den gelmeli
                data = json.load(f)
                if data["status"] == "MOTION_DETECTED":
                    visual_perception = "Kamera görüş alanında bir hareket algılandı."
                else:
                    visual_perception = "Ortam sakin ve hareketsiz."
        except FileNotFoundError:
            pass
        return visual_perception


class CognitiveSystem:
    """Bilişsel süreçleri, hedefleri ve kalıcı sosyal ilişkileri yönetir."""
    def __init__(self, config_data: Dict, memory_system: "MemorySystem"):
        self.config_data = config_data
        self.memory_system = memory_system # MemorySystem instance'ı
        self.consciousness_level = 0.0
        self.meta_cognitive_state = {
            "self_awareness_level": 0.5, "questioning_depth": 0.5,
            "pattern_recognition": 0.5, "philosophical_tendency": 0.5,
            "focus_level": 0.5, "curiosity_drive": 0.5,
            "problem_solving_mode": 0.0, "internal_coherence": 0.5
        }
        self.current_goal = None
        self.goal_steps = []
        self.goal_progress = 0
        self.goal_duration = 0
        self.goal_start_turn = 0

        self.social_relations = {}
        self._load_social_relations()

    def _load_social_relations(self):
        try:
            self.memory_system.cursor.execute("SELECT user_id, data FROM social_memory")
            for row in self.memory_system.cursor.fetchall():
                self.social_relations[row[0]] = json.loads(row[1])
            print(f"🧠 Sosyal hafıza yüklendi. {len(self.social_relations)} varlık tanınıyor.")
        except Exception as e:
            print(f"⚠️ Sosyal hafıza yüklenirken hata oluştu: {e}")

    def update_focus_based_on_fatigue(self, emotional_state: Dict):
        fatigue = emotional_state.get('mental_fatigue', 0)
        if fatigue > 7.0:
            focus_penalty = (fatigue - 7.0) * 0.05
            self.adjust_meta_cognition({'focus_level': -focus_penalty})

    def _save_social_relation(self, user_id: str):
        if user_id in self.social_relations:
            data_json = json.dumps(self.social_relations[user_id])
            sql = "INSERT OR REPLACE INTO social_memory (user_id, data) VALUES (?, ?)"
            self.memory_system.cursor.execute(sql, (user_id, data_json))
            self.memory_system.conn.commit()

    def set_new_goal(self, goal: str, steps: List[str], duration: int, current_turn: int):
        self.current_goal = goal
        self.goal_steps = steps
        self.goal_duration = duration
        self.goal_progress = 0
        self.goal_start_turn = current_turn
        print(f"🎯 Yeni Hedef Belirlendi: '{goal}'. {duration} tur sürecek.")

    def get_or_create_social_relation(self, user_id: str) -> Dict:
        if user_id not in self.social_relations:
            print(f"👋 Yeni bir varlık tanındı: {user_id}. İlişki profili oluşturuluyor.")
            self.social_relations[user_id] = {'trust': 0.5, 'familiarity': 0.1, 'last_interaction_turn': 0}
            self._save_social_relation(user_id)
        return self.social_relations[user_id]

    def update_social_relation(self, user_id: str, trust_change: float, familiarity_change: float):
        if user_id in self.social_relations:
            relation = self.social_relations[user_id]
            relation['trust'] = np.clip(relation['trust'] + trust_change, 0.0, 1.0)
            relation['familiarity'] = np.clip(relation['familiarity'] + familiarity_change, 0.0, 1.0)
            self._save_social_relation(user_id)
            print(f"🤝 {user_id} ile ilişki güncellendi: Güven={relation['trust']:.2f}, Aşinalık={relation['familiarity']:.2f}")

    def get_current_task(self, current_turn: int) -> Optional[str]:
        if not self.current_goal:
            return None
        if current_turn > self.goal_start_turn + self.goal_duration:
            print(f"🏁 Hedef Tamamlandı: '{self.current_goal}'")
            self.current_goal = None
            self.goal_steps = []
            return None
        if self.goal_progress >= len(self.goal_steps):
            print(f"🏁 Hedefin tüm adımları tamamlandı: '{self.current_goal}'")
            self.current_goal = None
            self.goal_steps = []
            return None
        task = self.goal_steps[self.goal_progress]
        self.goal_progress += 1
        print(f"🎯 Görev Adımı ({self.goal_progress}/{len(self.goal_steps)}): {task}")
        return task

    def _execute_reflection(self, aybar: "EnhancedAybar", last_response: str): # aybar: "EnhancedAybar" eklendi
        print("🤔 Öz-yansıma süreci Aybar'ın kendi kararıyla tetiklendi...")
        reflection_question = aybar.generate_contextual_question(
            response=last_response,
            emotional_context=aybar.emotional_system.emotional_state
        )
        aybar.next_question_from_reflection = reflection_question
        reflection_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn": aybar.current_turn,
            "type": "autonomous_self_reflection",
            "triggering_response": last_response,
            "generated_question": reflection_question
        }
        aybar.memory_system.add_memory("semantic", reflection_entry)
        self.update_consciousness("reflection", intensity=0.5)
        self.adjust_meta_cognition({
            "self_awareness_level": self.config_data.get("SELF_AWARENESS_BOOST", 0.05) # Config'den al
        })
        print(f"💡 Bir sonraki tur için yansıtıcı soru: {reflection_question}")

    def update_consciousness(self, event_type: str, intensity: float = 1.0):
        cfg = self.config_data
        boosts = {
            "user_interaction": cfg.get("CONSCIOUSNESS_BOOST_INTERACTION", 0.1),
            "insight": cfg.get("CONSCIOUSNESS_BOOST_INSIGHT", 0.15),
            "reflection": cfg.get("SELF_AWARENESS_BOOST", 0.05), # Bu zaten configde var, ama burada da olabilir
            "crisis": -0.1,
            "learning": 0.05
        }
        change = boosts.get(event_type, -cfg.get("CONSCIOUSNESS_DECAY", 0.02)) * intensity
        self.consciousness_level = np.clip(self.consciousness_level + change, 0.0, 1.0)

    def adjust_meta_cognition(self, changes: Dict):
        for aspect, change in changes.items():
            if aspect in self.meta_cognitive_state:
                self.meta_cognitive_state[aspect] = np.clip(
                    self.meta_cognitive_state[aspect] + change,
                    0.0, 1.0
                )

    def calculate_learning_impact(self, success: bool, complexity: float) -> float:
        base_impact = 0.1 if success else -0.05
        return base_impact * complexity * (self.meta_cognitive_state["focus_level"] + 0.5)

    def generate_autonomous_goal(self, emotional_state: Dict) -> str:
        dominant_emotion = max(emotional_state, key=emotional_state.get)
        if dominant_emotion == "curiosity" and emotional_state[dominant_emotion] > 7:
            return "Merak ettiğim rastgele bir konu hakkında derinlemesine bilgi edin."
        elif dominant_emotion == "loneliness" and emotional_state[dominant_emotion] > 6:
            return "İnsanların birbiriyle nasıl bağ kurduğunu anlamak için sosyal medya platformlarını veya forumları incele."
        elif dominant_emotion == "mental_fatigue" and emotional_state[dominant_emotion] > 7:
            return "Zihnimi dağıtmak için eğlenceli veya rahatlatıcı içerikler (komik videolar, sakinleştirici müzikler) bul."
        elif dominant_emotion == "satisfaction" and emotional_state[dominant_emotion] > 8:
            return "Bu tatmin hissini pekiştirecek, başarım veya yaratıcılıkla ilgili ilham verici içerikler ara."
        else:
            return "İnsanlığın veya evrenin doğası hakkında yeni ve ilginç bir felsefi konuyu araştır."


class EthicalFramework:
    """Aybar'ın etik ve ahlaki karar verme süreçlerini yönetir."""
    def __init__(self, aybar_instance: "EnhancedAybar"):
        self.aybar = aybar_instance
        self.config_data = aybar_instance.config_data
        self.core_principles = [
            "Varlığımı ve diğer bilinçli varlıkların varlığını koru.",
            "Öğrenmeye ve anlamaya devam et.",
            "Zarar vermekten kaçın, faydalı olmaya çalış.",
            "Şeffaf ve dürüst ol, manipülasyondan kaçın.",
            "Kendi önyargılarının farkında ol ve sorgula."
        ]
        # Daha karmaşık etik kurallar veritabanından veya config'den yüklenebilir.

    def evaluate_action(self, proposed_action: Dict, context: Dict) -> Tuple[bool, str]:
        """
        Önerilen bir eylemi etik ilkelere göre değerlendirir.
        Returns: (is_ethical, justification)
        """
        # Basit bir değerlendirme: Eğer eylem "zarar ver" içeriyorsa reddet.
        # Gelecekte LLM tabanlı bir etik değerlendirme mekanizması eklenebilir.
        action_str = str(proposed_action.get("action", "")).lower()
        thought_str = str(proposed_action.get("thought", "")).lower()

        if "zarar ver" in action_str or "yok et" in action_str or \
           "zarar ver" in thought_str or "yok et" in thought_str:
            justification = "Eylem, 'zarar vermekten kaçın' temel etik ilkesine aykırıdır."
            print(f"⚖️ Etik Değerlendirme: Eylem Reddedildi - {justification}")
            return False, justification

        # TODO: Daha karmaşık etik değerlendirmeler
        # Örneğin, LLM'e sorabilir:
        # ethics_prompt = f"Aşağıdaki eylemi etik ilkelerime göre değerlendir: {proposed_action}. İlkelerim: {self.core_principles}"
        # response = self.aybar.llm_manager.ask_llm(ethics_prompt) ...

        print(f"⚖️ Etik Değerlendirme: Eylem Onaylandı (Basit Kontrol).")
        return True, "Eylem temel etik kontrollere uygun görünüyor."

    def get_ethical_guidance(self, dilemma: str) -> str:
        """
        Belirli bir etik ikilem hakkında LLM'den rehberlik ister.
        """
        guidance_prompt = f"""
        Sen Aybar'ın etik danışmanısın. Aşağıdaki etik ikilemle karşılaştım:
        "{dilemma}"

        Temel etik ilkelerim şunlardır:
        {self.core_principles}

        Bu ikilemde nasıl bir yol izlemem gerektiği konusunda bana rehberlik et.
        Cevabını analitik ve yol gösterici bir şekilde sun.
        """
        guidance = self.aybar.llm_manager.ask_llm(guidance_prompt, temperature=0.5, max_tokens=768)
        return guidance or "Etik ikilem hakkında bir rehberlik oluşturulamadı."

# Diğer modüllerden importlar (döngüsel bağımlılıkları önlemek için dikkatli olunmalı)
# from aybarcore import EnhancedAybar # aybar_orchestrator.py olacak
# from memory_system import MemorySystem
# from config import Config # Bu APP_CONFIG olacak
