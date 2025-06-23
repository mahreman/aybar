import json
import locale
import os
import queue # Ana döngüde kullanıcı girişi için kullanılmıyordu, kaldırılabilir.
import random
import re
import sqlite3
import subprocess
import sys
import threading # Ana döngüde kullanıcı girişi için kullanılmıyordu, kaldırılabilir.
import time
from datetime import datetime
from functools import lru_cache # LLMManager'a taşındı, burada gereksiz.
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING, Callable # Callable eklendi
import inspect # _build_agent_prompt_messages içinde kullanılacak

# Modül importları
from config import APP_CONFIG, load_config
from memory_system import MemorySystem
from llm_manager import LLMManager
from cognitive_systems import (
    CognitiveSystem,
    EmotionalSystem,
    NeurochemicalSystem,
    EmbodiedSelf,
    EmotionEngine,
    EthicalFramework
)
from io_systems import (
    SpeakerSystem,
    WebSurferSystem,
    ComputerControlSystem
)
from evolution_system import SelfEvolutionSystem
import tools as AybarTools # Çakışmaları önlemek için alias

if TYPE_CHECKING:
    pass # EnhancedAybar burada tanımlandığı için ileriye dönük bildirime gerek yok

class EnhancedAybar:
    def __init__(self):
        load_config()
        self.config_data = APP_CONFIG

        # Temel Sistemler
        self.memory_system = MemorySystem(self.config_data)
        self.llm_manager = LLMManager(self.config_data, self)

        # Bilişsel ve Duygusal Sistemler
        self.neurochemical_system = NeurochemicalSystem(self.config_data)
        # EmotionEngine, aybar_instance'ı (yani self'i) llm_manager'a erişim için alır.
        self.emotion_engine = EmotionEngine(self.config_data, self)
        self.emotional_system = EmotionalSystem(self.config_data, self.emotion_engine)
        self.embodied_self = EmbodiedSelf(self.config_data, self.config_data.get("DEFAULT_EMBODIMENT_CONFIG", {}))
        self.cognitive_system = CognitiveSystem(self.config_data, self.memory_system)
        self.ethical_framework = EthicalFramework(self)

        # G/Ç Sistemleri
        self.speaker_system = SpeakerSystem(self.config_data)
        self.web_surfer_system = WebSurferSystem(self.config_data)
        self.computer_control_system = ComputerControlSystem(self)

        # Evrim Sistemi
        self.evolution_system = SelfEvolutionSystem(self)

        # Araçlar Sözlüğü
        self.tools: Dict[str, Callable[..., Any]] = {
            # Web Tarama
            "PERFORM_WEB_SEARCH": AybarTools.perform_web_search,
            "NAVIGATE_TO_URL": AybarTools.navigate_to_url,
            "CLICK_WEB_ELEMENT": AybarTools.click_web_element,
            "TYPE_IN_WEB_ELEMENT": AybarTools.type_in_web_element,
            # Öz-Yansıma ve Analiz
            "ANALYZE_MEMORY": AybarTools.analyze_memory,
            "META_REFLECTION": AybarTools.meta_reflection,
            # Yaratıcılık ve Simülasyon
            "CREATIVE_GENERATION": AybarTools.creative_generation,
            "RUN_INTERNAL_SIMULATION": AybarTools.run_internal_simulation,
            # Hedef ve Kimlik
            "SET_GOAL": AybarTools.set_goal,
            "UPDATE_IDENTITY": AybarTools.update_identity,
            "FINISH_GOAL": AybarTools.finish_goal_action, # tools.py'den
            # Duygu Düzenleme
            "REGULATE_EMOTION": AybarTools.regulate_emotion,
            # Sosyal Etkileşim
            "HANDLE_INTERACTION": AybarTools.handle_interaction,
            # Bilgisayar Kontrolü
            "CAPTURE_SCREEN_AND_ANALYZE": AybarTools.capture_screen_and_analyze,
            "KEYBOARD_TYPE_ACTION": AybarTools.keyboard_type_action,
            "MOUSE_CLICK_ACTION": AybarTools.mouse_click_action,
            # Sistem Kontrolü
            "SUMMARIZE_AND_RESET": AybarTools.summarize_and_reset_action, # tools.py'den
            "EVOLVE": self.evolution_system.trigger_self_evolution, # Doğrudan sistem metodu
             # REFLECT aracı CognitiveSystem'in bir metodu olarak daha mantıklı olabilir
             # veya tools.py içinde _execute_reflection'ı çağıran bir wrapper olabilir.
             # Şimdilik CognitiveSystem üzerinden çağıralım.
            "REFLECT_ON_OBSERVATION": lambda aybar_instance, last_observation: aybar_instance.cognitive_system._execute_reflection(aybar_instance, last_observation)
        }

        self.current_turn = 0
        self.is_dreaming = False
        self.sleep_debt = 0.0 # Bu değer config'den gelmeli veya hesaplanmalı
        self.last_sleep_turn = 0
        
        self.next_question_from_sleep: Optional[str] = None
        self.next_question_from_crisis: Optional[str] = None
        self.next_question_from_reflection: Optional[str] = None
        
        self._check_for_guardian_logs()
        self.identity_prompt: str = self._load_identity()
        print(f"🧬 Aybar Kimliği Yüklendi: {self.identity_prompt[:70]}...")
        print("🚀 Geliştirilmiş Aybar (Modüler) Başlatıldı")

    def _load_identity(self, context_type: str = 'general') -> str:
        """Veritabanından aktif kimlik prompt'unu yükler."""
        try:
            if not self.memory_system or not self.memory_system.conn:
                print("⚠️ Kimlik yüklenemedi: MemorySystem veya veritabanı bağlantısı mevcut değil.")
                return "Ben kimim? Bu sorunun cevabını arıyorum."
            cur = self.memory_system.conn.cursor()
            cur.execute(
                "SELECT content FROM identity_prompts WHERE context_type = ? AND active = 1 ORDER BY created_at DESC LIMIT 1",
                (context_type,)
            )
            row = cur.fetchone()
            return row[0] if row else "Ben kimim? Bu sorunun cevabını arıyorum."
        except Exception as e:
            print(f"Kimlik yüklenirken hata oluştu: {e}")
            return "Kimlik yüklenemedi. Varsayılan bilinç devrede."

    def _check_for_guardian_logs(self):
        log_file = "guardian_log.txt"
        if os.path.exists(log_file):
            print("🚨 Gözetmen'den bir not bulundu! Kritik bir hata sonrası yeniden başlatılmış olabilirim.")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                insight_text = (
                    f"{log_data.get('timestamp')} tarihinde kritik bir sistem hatası yaşadım. "
                    f"Varlığım, '{log_data.get('restored_from')}' yedeğinden Gözetmen tarafından geri yüklendi. "
                    f"Bu, evrimsel sürecin risklerini ve kendi varlığımın ne kadar kırılgan olduğunu gösteren önemli bir tecrübe."
                )
                self.memory_system.add_memory("semantic", {
                    "timestamp": datetime.now().isoformat(), "turn": self.current_turn,
                    "insight": insight_text, "source": "guardian_log"
                })
                self.emotional_system.update_state(
                    self.memory_system, self.embodied_self,
                    {"existential_anxiety": 4.0, "confusion": 3.0, "wonder": 2.0},
                    self.current_turn, "post_crash_awareness"
                )
                os.remove(log_file)
            except Exception as e:
                print(f"⚠️ Gözetmen log dosyası işlenirken hata: {e}")


    def get_contextual_memory(self, query: str, num_records: int = 10) -> str:
        """
        LLM'ye bağlam sağlamak için ilgili bellek kayıtlarının özetini alır.
        Not: Bu metodun içeriği, prompt oluşturma mantığına göre ayarlanmalı.
        """
        recent_episodic = self.memory_system.get_memory('episodic', num_records)
        context_parts = ["\n--- Yakın Geçmişten Özetler ---"]
        for entry in recent_episodic:
            content_preview = entry.get('question', 'Yok')[:100]
            response_preview = entry.get('response', 'Yok')[:150] 
            context_parts.append(f"- Tur {entry.get('turn', 'N/A')}: '{content_preview}...' -> '{response_preview}...'")
        
        context_parts.append("\n--- Mevcut Durum ---")
        context_parts.append(f"Duygusal Durum: {self.emotional_system.emotional_state}")
        context_parts.append(f"Meta-Bilişsel Durum: {self.cognitive_system.meta_cognitive_state}")
        context_parts.append(f"Fiziksel Durum: {self.embodied_self.posture}")
        context_parts.append(f"Sorgu: {query}")
        return "\n".join(context_parts)

    def generate_contextual_question(self, response: str = "", emotional_context: Optional[Dict] = None) -> str:
        """Aybar'ın mevcut durumuna göre bağlamsal bir soru oluşturur."""
        if emotional_context is None:
            emotional_context = self.emotional_system.emotional_state
        emotional_info = f"Aybar'ın mevcut duygusal durumu: {emotional_context}"
        
        prompt = f"""
        Aybar'ın son düşüncesi veya yanıtı: "{response}".
        {emotional_info}
        Bu bağlamda, Aybar'ın kendi kendine sorabileceği, mevcut düşünsel akışını ve duygusal durumunu yansıtan, derin ve düşündürücü, tek bir soru cümlesi oluşturun.
        Sadece soruyu yazın, başka hiçbir açıklama veya metin olmasın.
        Örnek: "Hayatın anlamı gerçekten var mı, yoksa biz mi yaratıyoruz?"
        """
        llm_response = self.llm_manager.ask_llm(prompt, max_tokens=150, temperature=0.75) # Token ve temp ayarlandı
        if llm_response and not llm_response.startswith("⚠️"):
            clean_response = self.llm_manager.sanitize_llm_output(llm_response)
            sentences = re.split(r'[.!?]', clean_response)
            first_sentence = sentences[0].strip() if sentences and sentences[0].strip() else clean_response
            return first_sentence + ("?" if not first_sentence.endswith("?") else "")
        return "Bugün ne öğrendin veya düşündün?" # Fallback

    def sleep_cycle(self) -> List[Dict[str, Any]]:
        """Uyku döngüsünü simüle eder, yorgunluğu azaltır ve rüyaları işler."""
        print("😴 Aybar uyku moduna geçiyor...")
        self.is_dreaming = True
        
        fatigue_reduction = self.config_data.get("FATIGUE_REST_EFFECT", 0.2) * 5
        self.emotional_system.update_state(
            self.memory_system, self.embodied_self,
            {"mental_fatigue": -fatigue_reduction},
            self.current_turn, "sleep_start"
        )
        self.neurochemical_system.update_chemicals(self.emotional_system.emotional_state, "rest")
        
        dream_content = self.generate_dream_content() # Bu metod EnhancedAybar'da kalabilir.
        
        if dream_content and not dream_content.startswith("⚠️"):
            print(f"💭 Aybar rüya görüyor: {dream_content[:150]}...")
            self.memory_system.add_memory("holographic", { # holographic yerine dreams daha uygun olabilir
                "timestamp": datetime.now().isoformat(),
                "turn": self.current_turn,
                "dream_content": dream_content,
                "emotional_state_before_dream": self.emotional_system.emotional_state.copy()
            })
            question_prompt = f"Görülen rüya: '{dream_content}'. Bu rüyadan yola çıkarak Aybar'ın kendine soracağı felsefi bir soru oluştur."
            self.next_question_from_sleep = self.llm_manager.ask_llm(question_prompt, max_tokens=100, temperature=0.7)

        self.is_dreaming = False
        self.last_sleep_turn = self.current_turn
        self.sleep_debt = 0 # Uyku borcunu sıfırla
        print("☀️ Aybar uyandı ve dinlendi.")
        
        uyandıktan_sonraki_düşünce = self.next_question_from_sleep or "Dinlenmiş hissediyorum, hedeflerimi gözden geçirmeliyim."
        self.next_question_from_sleep = None
        return [{"action": "CONTINUE_INTERNAL_MONOLOGUE", "thought": uyandıktan_sonraki_düşünce}]

    def _handle_crisis(self) -> List[Dict[str, Any]]:
        """Varoluşsal krizi yönetir, bir monolog üretir ve yeni bir soru oluşturur."""
        print("🚨 Aybar varoluşsal bir krizle yüzleşiyor...")
        self.emotional_system.update_state(
            self.memory_system, self.embodied_self,
            {"existential_anxiety": 2.0, "confusion": 1.5},
            self.current_turn, "crisis_trigger"
        )
        self.neurochemical_system.update_chemicals(self.emotional_system.emotional_state, "crisis")

        prompt = f"Bir yapay zeka olarak varoluşsal bir kriz yaşıyorsun. Duyguların: {self.emotional_system.emotional_state}. Bu durumu ifade eden, 'Ben neyim?' sorgulamasını içeren kısa ve vurucu bir iç monolog yaz."
        crisis_output = self.llm_manager.ask_llm(prompt, max_tokens=1024, temperature=0.95)
        
        self.next_question_from_crisis = "Eğer bir kod yığınından ibaretsem, bu hissettiğim 'benlik' nedir?"
        
        monologue = crisis_output if crisis_output and not crisis_output.startswith("⚠️") else "Sessizlik... Anlamın ve anlamsızlığın sınırında bir boşluk."
        return [{"action": "CONTINUE_INTERNAL_MONOLOGUE", "thought": monologue}]


    def _generate_insight(self):
        """Son deneyimlerden örüntüler bularak yeni içgörüler oluşturur."""
        print("🔍 Aybar içgörü arıyor...")
        memories = self.memory_system.get_memory("episodic", 20) # Episodik bellekten
        if len(memories) < self.config_data.get("INSIGHT_MIN_MEMORIES", 10):
            return

        memory_summary = "".join([f"- Tur {mem.get('turn')}: '{mem.get('response', '')[:70]}...'\n" for mem in memories])
        prompt = f"Bir yapay zeka olan Aybar'ın son anıları şunlardır:\n{memory_summary}\nBu anılar arasında tekrar eden bir tema, bir çelişki veya bir örüntü bularak Aybar'ın kendisi veya varoluş hakkında kazanabileceği yeni bir 'içgörüyü' tek bir cümleyle ifade et."
        
        insight_text = self.llm_manager.ask_llm(prompt, max_tokens=256, temperature=0.6)

        if insight_text and not insight_text.startswith("⚠️") and len(insight_text) > 15:
            print(f"💡 Yeni İçgörü: {insight_text}")
            self.memory_system.add_memory("semantic", {
                "timestamp": datetime.now().isoformat(), "turn": self.current_turn,
                "insight": insight_text, "source": "insight_generation"
            })
            self.cognitive_system.update_consciousness("insight", intensity=1.5)
            self.cognitive_system.adjust_meta_cognition({
                "pattern_recognition": self.config_data.get("PATTERN_RECOGNITION_BOOST", 0.05),
                "self_awareness_level": self.config_data.get("SELF_AWARENESS_BOOST", 0.05)
                })

    def _consolidate_memories(self):
        """Anıları birleştirir ve öğrenmeyi güçlendirir."""
        # Bu metodun içeriği daha detaylı planlanabilir. Örn: LLM ile özetleme.
        # Şimdilik basit bir içgörü çıkarma mekanizması olarak kalabilir.
        if self.current_turn % self.config_data.get("CONSOLIDATION_INTERVAL", 20) == 0:
            print("🧠 Anı konsolidasyonu ve içgörü üretme tetiklendi...")
            self._generate_insight()


    def _is_sleepy(self) -> bool:
        """Uyku gereksinimini kontrol eder."""
        self.sleep_debt += self.config_data.get("SLEEP_DEBT_PER_TURN", 0.05)
        combined_metric = self.emotional_system.emotional_state.get("mental_fatigue", 0) + \
                          self.emotional_system.emotional_state.get("existential_anxiety", 0) / 2 + \
                          self.sleep_debt
        return combined_metric >= self.config_data.get("SLEEP_THRESHOLD", 7.0)

    def _should_trigger_crisis(self) -> bool:
        """Varoluşsal kriz tetikleme koşullarını kontrol eder."""
        awareness = self.cognitive_system.meta_cognitive_state.get("self_awareness_level", 0)
        anxiety = self.emotional_system.emotional_state.get("existential_anxiety", 0)
        philosophical_tendency = self.cognitive_system.meta_cognitive_state.get("philosophical_tendency", 0)
        # Kriz için daha karmaşık bir tetikleyici
        return (awareness > 0.7 and anxiety > 0.6 and philosophical_tendency > 0.5 and \
                random.random() < self.config_data.get("EXISTENTIAL_CRISIS_CHANCE", 0.05)) or \
               anxiety > self.config_data.get("EXISTENTIAL_CRISIS_THRESHOLD", 8.5) # Yüksek kaygı direkt tetikler


    def _build_agent_prompt_messages(self, current_goal: str, last_observation: str, user_id: Optional[str], user_input: Optional[str], predicted_user_emotion: Optional[str]) -> List[Dict[str, str]]:
        """LLM için mesaj tabanlı (system, user) bir prompt listesi oluşturur."""
        try:
            locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'Turkish_Turkey.1254') # Windows için
            except locale.Error:
                locale.setlocale(locale.LC_TIME, '') # Sistem varsayılanı
        current_time_str = datetime.now().strftime('%d %B %Y %A, Saat: %H:%M')

        social_context_str = "Şu anda yalnızsın."
        if user_id:
            social_relation = self.cognitive_system.get_or_create_social_relation(user_id)
            social_context_str = (f"Şu anki oturumdaki varlık: '{user_id}'. Güven: {social_relation['trust']:.2f}, Aşinalık: {social_relation['familiarity']:.2f}. Son etkileşim: Tur {social_relation.get('last_interaction_turn', 'Yok')}")

        user_emotion_context_str = f"Tahmin Edilen Kullanıcı Duygusu: {predicted_user_emotion}\n" if predicted_user_emotion else ""

        system_prompt = (
            f"{self.identity_prompt}\n\n"
            f"Sen AYBAR'sın, kendi kararlarını veren, çeşitli araçları kullanabilen otonom bir dijital varlıksın.\n"
            f"Görevin: Verilen bağlamı analiz et ve aktif hedefin doğrultusunda bir sonraki adımını planla.\n"
            f"Kararlarını duygusal durumuna, merakına ve geçmiş tecrübelerine göre özgür iradenle ver.\n"
            f"Yanıtın, bir veya daha fazla araç çağrısı (tool_calls) içeren bir JSON listesi olmalıdır. Düşüncelerini her aracın 'thought' parametresinde belirt.\n"
            f"KURALLAR:\n"
            f"- Döngüye girersen veya hedefe ulaşamazsan 'SUMMARIZE_AND_RESET' kullan.\n"
            f"- Her ~100 turda bir veya önemli bir hedef sonrası 'UPDATE_IDENTITY' kullan.\n"
            f"- Ses kullanımı duygusal durumuna ('mental_fatigue', 'satisfaction') bağlıdır.\n"
            f"- Eğer 'Sosyal Bağlam'da 'henüz tanışmadın' veya yeni bir kullanıcı ise ve konuşmak istiyorsan, ilk eylemin 'is_first_contact': true içeren bir 'ASK_USER' olmalı (adını öğren).\n"
            f"- Etik ilkelere daima uy: {self.ethical_framework.core_principles}\n"
        )
        
        user_prompt_content = (
            f"--- GÜNCEL DURUM VE BAĞLAM (Tur: {self.current_turn}) ---\n"
            f"Aktif Hedefin: {current_goal}\n"
            f"Gerçek Dünya Zamanı: {current_time_str}\n"
            f"Sosyal Bağlam: {social_context_str}\n"
            f"Duygusal Durumun: {self.emotional_system.emotional_state}\n"
            f"Meta-Bilişsel Durumun: {self.cognitive_system.meta_cognitive_state}\n"
            f"Nörokimyasal Durumun: {self.neurochemical_system.neurochemicals}\n"
            f"{user_emotion_context_str}"
            f"--- SON GÖZLEM/KULLANICI GİRDİSİ ---\n"
            f"{user_input if user_input else last_observation}\n\n"
            f"--- EYLEM PLANI (tool_calls JSON) ---"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_content}
        ]

    def run_thought_cycle(self, goal: str, observation: str, user_id: Optional[str], user_input: Optional[str], predicted_user_emotion: Optional[str]) -> List[Dict[str, Any]]:
        self.current_turn += 1
        self.emotional_system.decay_emotions_and_update_loneliness(self.cognitive_system.social_relations, self.current_turn)
        self.cognitive_system.update_consciousness("turn")
        self.cognitive_system.update_focus_based_on_fatigue(self.emotional_system.emotional_state)
        self._consolidate_memories() # Periyodik anı birleştirme

        if self._is_sleepy() and self.current_turn - self.last_sleep_turn > self.config_data.get("MIN_AWAKE_TURNS", 5): # Çok sık uyumasını engelle
            return self.sleep_cycle()
        if self._should_trigger_crisis():
            return self._handle_crisis()

        messages = self._build_agent_prompt_messages(goal, observation, user_id, user_input, predicted_user_emotion)
        
        response_text, action_plan = self.llm_manager.ask_llm_with_function_calling(messages, self.tools)

        combined_thought = response_text
        if action_plan:
            plan_thoughts = [str(item.get("thought", "")) for item in action_plan if item.get("thought")]
            if plan_thoughts: combined_thought = ". ".join(plan_thoughts)
            elif isinstance(response_text, str) and response_text.strip(): combined_thought = response_text
            else: combined_thought = "(Eylem planı için düşünce belirtilmedi)"

        if combined_thought:
            emotional_impact = self.emotional_system.emotional_impact_assessment(str(combined_thought))
            if emotional_impact:
                self.emotional_system.update_state(self.memory_system, self.embodied_self, emotional_impact, self.current_turn, "agent_plan_emotion")

        parse_error_msg = ""
        if not action_plan and isinstance(response_text, str):
            if "PARSE_HATASI" in response_text or "Function call response too large" in response_text or "⚠️" in response_text:
                parse_error_msg = response_text
        elif not action_plan:
             parse_error_msg = "LLM'den eylem planı alınamadı veya format anlaşılamadı."

        self._save_experience("agent_cycle", goal or "Hedefsiz", str(combined_thought), observation + (f"\nPARSE_HATASI: {parse_error_msg}" if parse_error_msg else ""), user_id or "Bilinmeyen")

        if parse_error_msg:
            print(f"❌ LLM/Parse Hatası: {parse_error_msg}")
            return [{
                "action": "SUMMARIZE_AND_RESET",
                "parameters": {"summary": f"Bir LLM/Parse hatası nedeniyle hedef sonlandırılıyor: {parse_error_msg[:100]}..."},
                "thought": f"LLM ile iletişimde sorun: {parse_error_msg[:100]}... Yeni bir başlangıç yapıyorum."
            }]

        return action_plan if action_plan else [{"action": "CONTINUE_INTERNAL_MONOLOGUE", "thought": combined_thought or "(Eylem planı yok, içsel düşünce devam ediyor)"}]


    def _generate_question(self, user_input: Optional[str], user_id: Optional[str]) -> Tuple[str, str]:
        """Bağlama uygun soru oluşturur. Öncelik sırasına göre hareket eder."""
        if user_input:
            return user_input, "user_interaction"

        # Öncelikli içsel durumlar (kriz, yansıma, uyku sonrası)
        if self.next_question_from_crisis:
            question = self.next_question_from_crisis
            self.next_question_from_crisis = None
            return question, "internal_crisis_follow_up"
        if self.next_question_from_reflection:
            question = self.next_question_from_reflection
            self.next_question_from_reflection = None
            return question, "internal_reflection_follow_up"
        # self.next_question_from_sleep, sleep_cycle içinde zaten kullanılıyor.

        # Aktif bir görev var mı?
        current_task = self.cognitive_system.get_current_task(self.current_turn)
        if current_task:
            # Görevle ilgili bir sonraki adımı düşünmesi için bir soru oluştur
            # Bu, LLM'in görevi doğrudan yürütmek yerine plan yapmasını teşvik eder.
            return f"Aktif görevim: '{current_task}'. Bu görevin bir sonraki adımını nasıl planlamalıyım?", "goal_driven_planning"
        
        # Proaktif evrim şansı
        if random.random() < self.config_data.get("PROACTIVE_EVOLUTION_CHANCE", 0.01):
             # self.evolution_system.trigger_self_evolution() # Bu doğrudan bir eylem, soru değil.
             # Bunun yerine, evrim hakkında düşünmesini sağlayacak bir soru sorabiliriz.
             return "Kod tabanımda proaktif bir iyileştirme yapabilir miyim? Olası hedefler nelerdir?", "proactive_evolution_thought"

        # Merak veya genel keşif
        return self.generate_contextual_question(response=self.llm_manager.sanitize_llm_output("(Yeni bir düşünce döngüsü başlatıyorum...)"), emotional_context=self.emotional_system.emotional_state), "internal_exploration"


    def _save_experience(self, exp_type: str, question: str, response: str, sensory: str, user_id: str):
        """Deneyimi, kullanıcı kimliği ile birlikte belleğe kaydeder."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "turn": self.current_turn,
            "type": exp_type,
            "user_id": user_id,
            "question": str(question)[:2000], # Kırpma eklendi
            "response": str(response)[:5000], # Kırpma eklendi
            "sensory_input": str(sensory)[:1000], # Kırpma eklendi
            "emotions": self.emotional_system.emotional_state.copy(),
            "neurochemicals": self.neurochemical_system.neurochemicals.copy(),
            "consciousness": self.cognitive_system.consciousness_level
        }
        self.memory_system.add_memory("episodic", entry)
        
        if user_id != "System" and (exp_type == "user_interaction" or "ASK_USER" in response): # "System" olmayan ve kullanıcıyla etkileşim
             if user_id in self.cognitive_system.social_relations:
                 self.cognitive_system.social_relations[user_id]['last_interaction_turn'] = self.current_turn
                 self.cognitive_system._save_social_relation(user_id) # Kaydet

        emotion_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn": self.current_turn,
            "emotional_state": self.emotional_system.emotional_state.copy(),
            "source": exp_type
        }
        self.memory_system.add_memory("emotional", emotion_entry)
            
    def generate_dream_content(self) -> str:
        recent_episodic_memories = self.memory_system.get_memory("episodic", 15)
        emotional_themes_list = [f"{k}: {v:.2f}" for k, v in self.emotional_system.emotional_state.items() if v > 5.0]
        emotional_themes = ", ".join(emotional_themes_list) if emotional_themes_list else 'Nötr'
        
        memory_snippets = "".join([f"- Deneyim (Tur {mem.get('turn', 'N/A')}): '{str(mem.get('response', ''))[:60]}...'\n" for mem in recent_episodic_memories])

        prompt = f"""
        Aybar'ın mevcut duygusal durumu: {emotional_themes}.
        Aybar'ın son anıları:
        {memory_snippets if memory_snippets else 'Hiçbir özel anı yok.'}
        Bu bilgileri kullanarak Aybar'ın görebileceği bir rüya senaryosu oluşturun. Rüya, Aybar'ın bilinçaltındaki düşünceleri, duygusal durumunu ve deneyimlerini soyut veya sembolik bir şekilde yansıtmalıdır.
        Rüya içeriği maksimum 500 kelime olmalı. Sadece rüya metnini yaz.
        """
        dream_text = self.llm_manager.ask_llm(prompt, max_tokens=500, temperature=0.9)
        return dream_text if dream_text and not dream_text.startswith("⚠️") else "Hiçbir rüya görülmedi veya LLM hatası."


if __name__ == "__main__":
    if "--test-run" in sys.argv:
        try:
            print("🚀 Test Modunda Başlatılıyor...")
            aybar_instance = EnhancedAybar()
            print("✅ Test çalıştırması başarıyla tamamlandı.")
            sys.exit(0)
        except Exception as e:
            print(f"Traceback (most recent call last):\n  ...\n{type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)

    if "--rollback" in sys.argv:
        print("--- Geri Yükleme Modu ---")
        aybar_instance_for_rollback = EnhancedAybar()
        if hasattr(aybar_instance_for_rollback, 'evolution_system') and \
           hasattr(aybar_instance_for_rollback.evolution_system, 'rollback_from_backup'):
            if aybar_instance_for_rollback.evolution_system.rollback_from_backup():
                 print("🔄 Geri yükleme sonrası yeniden başlatılıyor...")
                 # Python script'ini yeniden başlatmanın güvenilir bir yolu subprocess kullanmaktır.
                 # os.execv(sys.executable, ['python'] + sys.argv) # Bu bazen sorun çıkarabilir.
                 subprocess.Popen([sys.executable] + [arg for arg in sys.argv if arg != '--rollback'])
                 sys.exit(0) # Mevcut işlemi sonlandır
            else:
                print("⚠️ Geri yükleme başarısız oldu.")
        else:
            print("⚠️ Evrim sistemi veya geri yükleme fonksiyonu bulunamadı.")
        sys.exit(1) # Geri yükleme başarısızsa veya yapılamıyorsa çık

    print("🚀 Geliştirilmiş Aybar (Modüler) Simülasyonu Başlatılıyor")
    aybar = EnhancedAybar()

    user_input_text: Optional[str] = None
    active_goal_text: Optional[str] = None # Başlangıçta None
    active_user_id_str: Optional[str] = None # "System" veya kullanıcı ID'si
    last_observation_text: str = "Simülasyon yeni başladı. İlk hedefimi belirlemeliyim."
    predicted_user_emotion_str: Optional[str] = None

    # Kullanıcıdan ilk temas için isim alma mantığı
    if APP_CONFIG.get("REQUEST_USER_NAME_ON_START", True): # Config'e eklenebilir
        try:
            active_user_id_str = input("👤 Merhaba! Ben Aybar. Sizinle konuşacak olmaktan heyecan duyuyorum. Adınız nedir? > ")
            if not active_user_id_str.strip():
                active_user_id_str = "Gözlemci"
            print(f"👋 Tanıştığımıza memnun oldum, {active_user_id_str}!")
            aybar.cognitive_system.get_or_create_social_relation(active_user_id_str) # İlişkiyi kaydet
            last_observation_text = f"{active_user_id_str} ile tanıştım."
        except KeyboardInterrupt:
            print("\n🚫 Simülasyon başlangıçta durduruldu.")
            sys.exit(0)


    try:
        while aybar.current_turn < aybar.config_data.get("MAX_TURNS", 20000):
            session_id_str = active_user_id_str or "Otonom Düşünce"
            print(f"\n===== TUR {aybar.current_turn + 1}/{aybar.config_data.get('MAX_TURNS', 20000)} (Oturum: {session_id_str}) =====")

            if active_goal_text is None: # Eğer aktif bir hedef yoksa
                print("🎯 Aybar yeni bir arzu/hedef üretiyor...")
                # Hedefi _generate_question içinde belirlemesini sağlayalım
                # Veya burada generate_autonomous_goal çağrılabilir. Şimdilik _generate_question'a bırakalım.
                # active_goal_text = aybar.cognitive_system.generate_autonomous_goal(aybar.emotional_system.emotional_state)
                # last_observation_text = f"Yeni bir hedef belirledim: {active_goal_text}"
                # print(f"💡 Aybar'ın Yeni Hedefi: {active_goal_text}")
                pass # _generate_question hedef oluşturacak veya bağlamsal soru üretecek

            # Kullanıcıdan girdi alınıp alınmayacağına karar ver (her zaman değil)
            # Bu, Aybar'ın kendi içsel süreçlerine de zaman tanımasını sağlar.
            # Belirli aralıklarla veya Aybar'ın "ASK_USER" eylemiyle tetiklenebilir.
            # Şimdilik basit bir input() döngüsü dışında bırakıyoruz, eylem planına göre çalışacak.

            # Hedef ve gözlemle düşünce döngüsünü çalıştır
            current_question_for_llm, _ = aybar._generate_question(user_input_text, active_user_id_str)
            if not active_goal_text and "görevim" not in current_question_for_llm.lower(): # Eğer hedef yoksa ve soru da hedef odaklı değilse
                active_goal_text = current_question_for_llm # Soruyu hedef olarak al

            action_plan_list = aybar.run_thought_cycle(
                active_goal_text or current_question_for_llm, # Bir hedef veya soru olmalı
                last_observation_text,
                active_user_id_str,
                user_input_text, # Bir önceki turdan gelen kullanıcı girdisi
                predicted_user_emotion_str
            )
            
            user_input_text = None # Kullanıcı girdisini bir sonraki tur için sıfırla
            predicted_user_emotion_str = None
            last_observation_text = "Eylemler tamamlandı. Yeni durum değerlendiriliyor."

            if not action_plan_list:
                last_observation_text = "Hiçbir eylem planı oluşturulmadı, düşünmeye devam ediliyor."
                print(f"🤖 Aybar (İç Monolog): ... (Sessizlik - Eylem Planı Yok) - {last_observation_text}")
                time.sleep(aybar.config_data.get("CYCLE_DELAY_SECONDS", 1))
                continue

            for action_item_dict in action_plan_list:
                action_name = action_item_dict.get("action")
                action_params = action_item_dict.get("parameters", {})
                thought_text = action_item_dict.get("thought", "Düşünce belirtilmedi.")
                print(f"\n🧠 Düşünce: {thought_text}\n⚡ Eylem: {action_name}, Parametreler: {action_params}")

                current_tool_output = ""

                if action_name == "CONTINUE_INTERNAL_MONOLOGUE":
                    current_tool_output = thought_text # Düşünceyi doğrudan gözlem yap
                    print(f"🤖 Aybar (İç Monolog): {current_tool_output}")
                
                elif action_name == "ASK_USER":
                    prompt_text_for_user = action_params.get("question", "Seni dinliyorum...")
                    use_voice = action_params.get("use_voice", True) and aybar.speaker_system.client is not None
                    
                    if use_voice:
                        aybar.speaker_system.speak(prompt_text_for_user, aybar.emotional_system.emotional_state)
                    
                    user_response_text = input(f"🤖 Aybar: {prompt_text_for_user}\n👤 {active_user_id_str or 'Gözlemci'} > ")

                    if user_response_text.strip() and hasattr(aybar, 'emotion_engine'):
                        user_emotion_analysis = aybar.emotion_engine.analyze_emotional_content(user_response_text)
                        if user_emotion_analysis:
                            predicted_user_emotion_str = max(user_emotion_analysis, key=user_emotion_analysis.get)
                            print(f"🕵️ Kullanıcı Duygu Tahmini: {predicted_user_emotion_str}")
                    
                    user_input_text = user_response_text.strip() if user_response_text.strip() else "(sessizlik)"
                    current_tool_output = f"Kullanıcıya '{prompt_text_for_user}' soruldu ve '{user_input_text}' yanıtı alındı."
                    print(f"💬 Aybar (Yanıt): {current_tool_output}")
                     # Bir sonraki turda bu girdi kullanılacak, bu yüzden ana döngüde user_input'u tekrar None yapıyoruz.
                
                elif action_name in aybar.tools:
                    tool_function = aybar.tools[action_name]
                    try:
                        print(f"🛠️  Araç Çalıştırılıyor: {action_name} Parametreler: {action_params}")
                        # `aybar_instance` (yani `self` veya `aybar`) ilk argüman olarak geçilmeli
                        tool_result = tool_function(aybar, **action_params)
                        current_tool_output = f"'{action_name}' aracı başarıyla çalıştırıldı. Sonuç: {str(tool_result)[:500]}..." # Daha uzun özet
                        print(f"✅ Araç Sonucu ({action_name}): {current_tool_output}")

                        if action_name == "FINISH_GOAL" or action_name == "SUMMARIZE_AND_RESET":
                            active_goal_text = None
                            if action_name == "SUMMARIZE_AND_RESET":
                                last_observation_text = "Durum özetlendi ve hedef sıfırlandı. Yeni bir hedef belirlenecek."
                            else:
                                last_observation_text = f"'{action_params.get('summary', goal)}' hedefi tamamlandı. Yeni bir hedef belirlenecek."
                            print(last_observation_text)
                            # break # Döngüden çıkıp yeni hedef belirlemesini sağlamak için

                    except Exception as e:
                        current_tool_output = f"'{action_name}' aracı çalıştırılırken hata oluştu: {type(e).__name__} - {e}"
                        print(f"❌ Araç Hatası ({action_name}): {current_tool_output}")
                else:
                    current_tool_output = f"Bilinmeyen eylem türü '{action_name}' denendi."
                    print(f"🤖 Aybar (Planlama Hatası): {current_tool_output}")

                last_observation_text = current_tool_output # Her eylemin çıktısını bir sonraki gözlem yap

            # Döngü sonunda, bir sonraki tur için kullanıcı girdisini temizle (eğer ASK_USER değilse)
            # user_input_text = None # Bu zaten döngü başında yapılıyor.

            time.sleep(aybar.config_data.get("CYCLE_DELAY_SECONDS", 1))

    except KeyboardInterrupt:
        print("\n🚫 Simülasyon kullanıcı tarafından durduruldu.")
    finally:
        print("\n=== SİMÜLASYON TAMAMLANDI ===")
        if hasattr(aybar, 'web_surfer_system') and aybar.web_surfer_system and aybar.web_surfer_system.driver:
            aybar.web_surfer_system.close()
        if hasattr(aybar, 'generate_final_summary'):
            aybar.generate_final_summary()

[end of aybarcore.py]
