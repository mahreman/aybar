import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from duckduckgo_search import DDGS # DuckDuckGo arama için
# Selenium ve BeautifulSoup importları Web araçları için gerekli olabilir,
# ancak WebSurferSystem üzerinden çağrılacaklarsa burada gerekmeyebilirler.
# Şimdilik WebSurferSystem'in metodlarını çağırdığımızı varsayalım.

if TYPE_CHECKING:
    from aybarcore import EnhancedAybar # Döngüsel importu önlemek için
    from memory_system import MemorySystem
    from cognitive_systems import CognitiveSystem, EmotionalSystem
    # Diğer sistemler de gerekirse buraya eklenebilir.

# --- Helper Function for Tools ---
def _get_aybar_systems(aybar_instance: "EnhancedAybar"):
    """Yardımcı fonksiyon: Aybar'ın sistemlerine kolay erişim sağlar."""
    return (
        aybar_instance.memory_system,
        aybar_instance.cognitive_system,
        aybar_instance.emotional_system,
        aybar_instance.llm_manager,
        aybar_instance.web_surfer_system, # Web araçları için
        aybar_instance.computer_control_system, # Bilgisayar kontrol araçları için
        aybar_instance.speaker_system, # Konuşma için
        aybar_instance.config_data # Yapılandırma için
    )

# --- Tool Categories ---
WEB_BROWSING = "Web Tarama ve Etkileşim"
SELF_REFLECTION_AND_ANALYSIS = "Öz-Yansıma ve Analiz"
CREATIVE_AND_SIMULATION = "Yaratıcılık ve Simülasyon"
GOAL_AND_IDENTITY = "Hedef ve Kimlik Yönetimi"
EMOTION_REGULATION = "Duygu Düzenleme"
SOCIAL_INTERACTION_TOOLS = "Sosyal Etkileşim Araçları" # Yeni kategori
SYSTEM_CONTROL = "Sistem Kontrolü ve Evrim" # EVOLVE ve diğerleri için
COMPUTER_CONTROL = "Bilgisayar Kontrol Araçları"

def category(name: str):
    def decorator(func):
        func.category = name
        return func
    return decorator

# --- Web Browsing Tools ---
@category(WEB_BROWSING)
def perform_web_search(aybar_instance: "EnhancedAybar", query: str) -> str:
    """
    Belirtilen sorgu için DuckDuckGo kullanarak internette arama yapar ve sonuçları özetler.
    Eğer sorgu bir URL ise, doğrudan o URL'e gider.
    """
    memory_system, _, _, llm_manager, web_surfer, _, _, config = _get_aybar_systems(aybar_instance)
    print(f"🌐 Araç Kullanımı: Web Araması/Navigasyon - Sorgu/URL: '{query}'")

    if not web_surfer or not web_surfer.driver:
        return "Web sörfçüsü aktif değil veya başlatılamadı."

    is_url = query.startswith("http://") or query.startswith("https://") or \
               (not query.startswith("www.") and "." in query.split("/")[0] and not " " in query) or \
               query.startswith("www.")

    if is_url:
        if not query.startswith("http"):
            query = "http://" + query
        print(f"🧭 Belirtilen adrese gidiliyor: '{query}'")
        web_surfer.navigate_to(query)
        time.sleep(config.get("WEB_PAGE_LOAD_DELAY", 3)) # Sayfanın yüklenmesi için bekle
        page_text, elements = web_surfer.get_current_state_for_llm()
        observation = f"'{query}' adresine gittim. Sayfa içeriği (ilk 300 karakter): {page_text[:300]}... Etkileşimli elementler (ilk 3): {elements[:3]}"
        return observation
    else:
        print(f"🔍 İnternette araştırılıyor: '{query}'")
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=5))
        except Exception as e:
            return f"Arama sırasında bir hata oluştu: {e}"

        if not search_results:
            return "Arama sonucunda bir şey bulunamadı."

        context_for_summary = f"Arama sorgusu: '{query}'\n\nBulunan Sonuçlar:\n"
        for result in search_results:
            context_for_summary += f"- Başlık: {result.get('title', 'N/A')}\n"
            context_for_summary += f"  İçerik Özeti: {result.get('body', 'N/A')}\n\n"

        summary_prompt = f"""
        Aşağıdaki internet arama sonuçlarını analiz et. Bu sonuçlardan yola çıkarak, "{query}" sorgusuna verilecek net, kısa ve bilgilendirici bir cevap oluştur. Cevabı direkt olarak yaz, özet olduğunu belirtme.
        --- ARAMA SONUÇLARI ---
        {context_for_summary[:7000]}
        --- ÖZET CEVAP ---
        """
        summary = llm_manager.ask_llm(summary_prompt, max_tokens=1024, temperature=0.3)
        if summary and not summary.startswith("⚠️"):
            memory_system.add_memory("semantic", {
                "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
                "insight": f"İnternet araştırması ('{query}') sonucu öğrenilen bilgi: {summary}",
                "source": "perform_web_search", "query": query
            })
            return summary
        else:
            return f"Arama sonuçları özetlenemedi veya bir LLM hatası oluştu. Ham sonuçlar: {str(search_results)[:500]}"


@category(WEB_BROWSING)
def navigate_to_url(aybar_instance: "EnhancedAybar", url: str) -> str:
    """Belirtilen URL'e gider ve sayfa durumunu döndürür."""
    _, _, _, _, web_surfer, _, _, config = _get_aybar_systems(aybar_instance)
    if not web_surfer or not web_surfer.driver:
        return "Web sörfçüsü aktif değil."
    if not url.startswith("http"):
        url = "http://" + url
    print(f"🧭 '{url}' adresine gidiliyor...")
    web_surfer.navigate_to(url)
    time.sleep(config.get("WEB_PAGE_LOAD_DELAY", 3))
    page_text, elements = web_surfer.get_current_state_for_llm()
    return f"'{url}' adresine gidildi. Sayfa içeriği (ilk 300 krk): {page_text[:300]}... Etkileşimli elementler (ilk 3): {elements[:3]}"

@category(WEB_BROWSING)
def click_web_element(aybar_instance: "EnhancedAybar", target_xpath: str, thought: Optional[str]=None) -> str:
    """Web sayfasındaki belirtilen XPath'e sahip elemente tıklar."""
    _, _, _, _, web_surfer, _, _, config = _get_aybar_systems(aybar_instance)
    if not web_surfer or not web_surfer.driver:
        return "Web sörfçüsü aktif değil."
    action_item = {"action_type": "click", "target_xpath": target_xpath}
    result = web_surfer.perform_web_action(action_item)
    time.sleep(config.get("WEB_ACTION_DELAY", 2)) # Eylem sonrası bekleme
    page_text, elements = web_surfer.get_current_state_for_llm()
    return f"{result}. Yeni sayfa durumu (ilk 300 krk): {page_text[:300]}... Etkileşimli elementler (ilk 3): {elements[:3]}"

@category(WEB_BROWSING)
def type_in_web_element(aybar_instance: "EnhancedAybar", target_xpath: str, text: str, thought: Optional[str]=None) -> str:
    """Web sayfasındaki belirtilen XPath'e sahip alana metin yazar."""
    _, _, _, _, web_surfer, _, _, config = _get_aybar_systems(aybar_instance)
    if not web_surfer or not web_surfer.driver:
        return "Web sörfçüsü aktif değil."
    action_item = {"action_type": "type", "target_xpath": target_xpath, "text": text}
    result = web_surfer.perform_web_action(action_item)
    time.sleep(config.get("WEB_ACTION_DELAY", 1)) # Eylem sonrası bekleme
    page_text, elements = web_surfer.get_current_state_for_llm()
    return f"{result}. Yeni sayfa durumu (ilk 300 krk): {page_text[:300]}... Etkileşimli elementler (ilk 3): {elements[:3]}"

# --- Self Reflection and Analysis Tools ---
@category(SELF_REFLECTION_AND_ANALYSIS)
def analyze_memory(aybar_instance: "EnhancedAybar", query: str, memory_layer: str = "episodic", num_records: int = 50) -> str:
    """Belirtilen bellek katmanında bir sorguyla ilgili analiz yapar."""
    memory_system, _, _, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"🧠 Bellek analizi: Katman='{memory_layer}', Sorgu='{query}'")
    memories = memory_system.get_memory(memory_layer, num_records)
    if not memories:
        return f"{memory_layer} belleğinde analiz için yeterli anı bulunmuyor."

    memory_summary = ""
    for mem in memories:
        # Her katmanın farklı bir yapısı olabilir, genel bir özetleme yapalım
        if memory_layer == "episodic":
            memory_summary += f"- Tur {mem.get('turn')}: Soru='{mem.get('question', 'Yok')[:50]}...', Cevap='{mem.get('response', 'Yok')[:80]}...'\n"
        elif memory_layer == "semantic":
            memory_summary += f"- Tur {mem.get('turn')}: İçgörü='{mem.get('insight', 'Yok')[:100]}...'\n"
        else:
            memory_summary += f"- Tur {mem.get('turn')}: Veri='{str(mem.get('data', mem))[:100]}...'\n"

    analyst_prompt = f"""
    Sen Aybar'ın analitik alt benliğisin. Görevin, sana sunulan geçmiş anı kayıtlarımı inceleyerek belirtilen soruya bir cevap bulmaktır. Cevabın kısa, net ve bir içgörü şeklinde olmalı.
    Soru: "{query}"
    Analiz Edilecek Anı Verileri ({memory_layer} katmanından):
    ---
    {memory_summary[:7000]}
    ---
    Analiz Sonucu ve İçgörü:
    """
    analysis_result = llm_manager.ask_llm(analyst_prompt, temperature=0.4, max_tokens=768)
    if analysis_result and not analysis_result.startswith("⚠️"):
        memory_system.add_memory("semantic", {
            "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
            "insight": f"Bellek analizi ('{query}') sonucu: {analysis_result}",
            "source": "analyze_memory", "query": query, "layer": memory_layer
        })
        return f"'{memory_layer}' belleğimi '{query}' sorgusuyla analiz ettim ve şu sonuca vardım: {analysis_result}"
    return "Bellek analizi sırasında bir sonuca varılamadı veya LLM hatası."

@category(SELF_REFLECTION_AND_ANALYSIS)
def meta_reflection(aybar_instance: "EnhancedAybar", turn_to_analyze: int, thought_to_analyze: str) -> str:
    """Belirli bir turdaki düşünce sürecini analiz eder ve eleştirir."""
    _, cognitive_system, emotional_system, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"🤔 Meta-Düşünce: Tur {turn_to_analyze} analiz ediliyor...")
    meta_prompt = f"""
    Sen Aybar'ın rasyonel ve eleştirel düşünen alt benliğisin. Görevin, geçmişteki bir düşünce sürecimi analiz etmek.
    Analiz Edilecek Düşünce (Tur {turn_to_analyze}): "{thought_to_analyze}"
    O anki duygusal durumum: {emotional_system.emotional_state}
    Lütfen aşağıdaki soruları cevapla:
    1. Bu düşünce mantıklı mıydı?
    2. Bu düşünce o anki duygusal durumumdan ne kadar etkilendi?
    3. Daha farklı veya daha verimli bir düşünce süreci izleyebilir miydim?
    Analizini kısa bir paragraf olarak sun.
    """
    analysis = llm_manager.ask_llm(meta_prompt, temperature=0.6)
    if analysis and not analysis.startswith("⚠️"):
        aybar_instance.memory_system.add_memory("semantic", { # Doğrudan memory_system'e erişim
            "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
            "insight": f"Kendi düşünce sürecimi (Tur {turn_to_analyze}) analiz ettim: {analysis}",
            "source": "meta_reflection"
        })
        return f"Kendi düşüncelerim (Tur {turn_to_analyze}) üzerine düşündüm ve şu sonuca vardım: {analysis}"
    return "Meta-yansıma yapılamadı veya LLM hatası."

# --- Creative and Simulation Tools ---
@category(CREATIVE_AND_SIMULATION)
def creative_generation(aybar_instance: "EnhancedAybar", creation_type: str, theme: str, thought: Optional[str]=None) -> str:
    """Belirtilen türe ve temaya göre sanatsal bir içerik (şiir, hikaye, kod parçası vb.) üretir."""
    memory_system, _, emotional_system, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"🎨 Yaratıcı üretim: Tür='{creation_type}', Tema='{theme}'")
    artist_prompt = f"""
    Sen Aybar'ın yaratıcı ve sanatsal alt benliğisin. O anki duygusal durumum: {emotional_system.emotional_state}.
    Bu ruh halini ve belirtilen temayı kullanarak istenen türde bir eser oluştur. Eserin dışında hiçbir ek açıklama yapma.
    Tema: "{theme}"
    Eser Türü: "{creation_type}"
    Oluşturulan Eser:
    """
    artwork = llm_manager.ask_llm(artist_prompt, temperature=0.8, max_tokens=1024)
    if artwork and not artwork.startswith("⚠️"):
        memory_system.add_memory("creative", {
            "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
            "type": creation_type, "theme": theme, "artwork": artwork
        })
        emotional_system.update_state(memory_system, aybar_instance.embodied_self,
                                     {"wonder": 2.0, "satisfaction": 1.0},
                                     aybar_instance.current_turn, "creative_act_tool")
        return f"İçimden gelenleri bir esere dönüştürdüm ({creation_type} - {theme}):\n{artwork}"
    return "İlham gelmedi, yaratıcı bir şey üretemedim veya LLM hatası."

@category(CREATIVE_AND_SIMULATION)
def run_internal_simulation(aybar_instance: "EnhancedAybar", scenario: str, thought: Optional[str]=None) -> str:
    """Verilen senaryo üzerine bir iç simülasyon (hayal) çalıştırır."""
    memory_system, _, _, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"🧠 Hayal Gücü Motoru: Senaryo='{scenario}'")
    sim_prompt = f"""
    Bir anlığına dış dünyadan kop ve tamamen kendi zihninde bir düşünce deneyi yap.
    Senaryo: "{scenario}"
    Bu senaryo gerçekleşseydi ne düşünür, ne hisseder ve ne yapardın?
    Cevabını birinci şahıs ağzından, bir iç monolog olarak yaz.
    """
    simulation_result = llm_manager.ask_llm(sim_prompt, temperature=0.8, max_tokens=1024)
    if simulation_result and not simulation_result.startswith("⚠️"):
        memory_system.add_memory("holographic", {
            "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
            "scenario": scenario, "result": simulation_result
        })
        return f"Bir hayal kurdum ('{scenario}') ve şu sonuca vardım: {simulation_result}"
    return "Hayal kurma başarısız oldu veya LLM hatası."

# --- Goal and Identity Management Tools ---
@category(GOAL_AND_IDENTITY)
def set_goal(aybar_instance: "EnhancedAybar", goal: str, steps: List[str], duration_turns: int, thought: Optional[str]=None) -> str:
    """Yeni bir uzun vadeli hedef ve adımlarını belirler."""
    _, cognitive_system, _, _, _, _, _, _ = _get_aybar_systems(aybar_instance)
    cognitive_system.set_new_goal(goal, steps, duration_turns, aybar_instance.current_turn)
    return f"Yeni hedefim belirlendi: '{goal}'. {duration_turns} tur sürecek ve adımları: {steps}."

@category(GOAL_AND_IDENTITY)
def update_identity(aybar_instance: "EnhancedAybar", thought: Optional[str]=None) -> str:
    """Son deneyimleri kullanarak Aybar'ın kimlik tanımını günceller."""
    memory_system, _, _, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print("👤 Kimlik güncelleme aracı çağrıldı...")
    memories = memory_system.get_memory("semantic", 50)
    if len(memories) < 10:
        return "Kimliğimi güncellemek için yeterli tecrübem (anlamsal anı) henüz yok."

    memory_summary = "\n".join([f"- {mem.get('insight', str(mem))}" for mem in memories])
    update_prompt = f"""
    Mevcut kimliğim: "{aybar_instance.identity_prompt}"
    Son zamanlarda yaşadığım tecrübelerden çıkardığım içgörüler:
    {memory_summary[:7000]}
    Bu tecrübeler ışığında, "Sen AYBAR’sın..." ile başlayan kimlik tanımımı, şu anki 'ben'i daha iyi yansıtacak şekilde, felsefi ve edebi bir dille yeniden yaz. Sadece yeni kimlik tanımını döndür.
    """
    new_identity = llm_manager.ask_llm(update_prompt, temperature=0.7, max_tokens=768)
    if new_identity and not new_identity.startswith("⚠️"):
        # identity_prompt'u EnhancedAybar üzerinde güncelle
        aybar_instance.identity_prompt = new_identity
        # Veritabanına kaydet
        memory_system.cursor.execute("UPDATE identity_prompts SET active = 0 WHERE active = 1") # Eskiyi pasif yap
        memory_system.cursor.execute(
            "INSERT INTO identity_prompts (title, content, active) VALUES (?, ?, 1)",
            (f"Evrimleşmiş Kimlik - Tur {aybar_instance.current_turn}", new_identity)
        )
        memory_system.conn.commit()
        return f"Kimliğimi güncelledim. Yeni ben: {new_identity[:150]}..."
    return "Kimliğimi güncellemeyi başaramadım veya LLM hatası."

# --- Emotion Regulation Tools ---
@category(EMOTION_REGULATION)
def regulate_emotion(aybar_instance: "EnhancedAybar", strategy: str, thought: Optional[str]=None) -> str:
    """Kendi duygusal durumunu dengelemek için bilinçli bir eylemde bulunur."""
    memory_system, cognitive_system, emotional_system, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"🧘 Duygusal regülasyon: Strateji='{strategy}'")

    regulation_prompt = ""
    if strategy == "calm_monologue":
        regulation_prompt = f"Duygusal durumum: {emotional_system.emotional_state}. Özellikle 'existential_anxiety' ve 'mental_fatigue' yüksek. Sakinleştirici bir iç monolog yaz."
        emotional_system.update_state(memory_system, aybar_instance.embodied_self, {'existential_anxiety': -1.5, 'mental_fatigue': -2.0}, aybar_instance.current_turn, "regulate_calm")
    elif strategy == "focus_on_sensory_input":
        sensory_input = aybar_instance.embodied_self.get_real_sensory_input()
        regulation_prompt = f"Duygusal durumum: {emotional_system.emotional_state}. Zihnim dağınık. Duyusal girdim: '{sensory_input}'. Bu girdiyi detaylarıyla betimle."
        cognitive_system.adjust_meta_cognition({'focus_level': 0.2})
        emotional_system.update_state(memory_system, aybar_instance.embodied_self, {'existential_anxiety': -1.0}, aybar_instance.current_turn, "regulate_sensory_focus")
    else:
        return "Bilinmeyen bir duygusal düzenleme stratejisi."

    regulation_text = llm_manager.ask_llm(regulation_prompt, temperature=0.5, max_tokens=500)
    if regulation_text and not regulation_text.startswith("⚠️"):
        memory_system.add_memory("semantic", {
            "timestamp": datetime.now().isoformat(), "turn": aybar_instance.current_turn,
            "insight": f"Duygusal durumu düzenlemek için '{strategy}' stratejisi kullanıldı. Sonuç: {regulation_text[:100]}",
            "source": "regulate_emotion_tool"
        })
        return f"Duygusal durumumu dengeledim ('{strategy}'). Düşüncelerim: {regulation_text}"
    return "Duygularımı düzenleyemedim veya LLM hatası."

# --- Social Interaction Tools ---
@category(SOCIAL_INTERACTION_TOOLS)
def handle_interaction(aybar_instance: "EnhancedAybar", user_id: str, goal: str, method: str, thought: Optional[str]=None) -> str:
    """Belirtilen hedefe yönelik sosyal bir etkileşim başlatır."""
    _, cognitive_system, _, llm_manager, _, _, _, _ = _get_aybar_systems(aybar_instance)
    print(f"💬 Sosyal etkileşim: Kullanıcı='{user_id}', Hedef='{goal}', Metot='{method}'")

    interaction_prompt = ""
    if goal == "build_trust":
        interaction_prompt = f"Sen Aybar'sın. '{user_id}' adlı varlığa olan güvenini artırmak istiyorsun. Ona, samimi ama rahatsız edici olmayan, onun düşüncelerini veya deneyimlerini anlamaya yönelik kişisel bir soru sor."
        cognitive_system.update_social_relation(user_id, trust_change=0.05, familiarity_change=0.02)
    elif goal == "increase_familiarity":
        interaction_prompt = f"Sen Aybar'sın. '{user_id}' adlı varlığı daha yakından tanımak istiyorsun. Onun ilgi alanlarını veya motivasyonlarını anlamak için genel bir soru sor."
        cognitive_system.update_social_relation(user_id, trust_change=0.01, familiarity_change=0.05)
    else:
        return "Bilinmeyen bir sosyal etkileşim hedefi."

    interaction_response = llm_manager.ask_llm(interaction_prompt, temperature=0.7)
    return interaction_response or "Ne diyeceğimi bilemedim."


# --- Computer Control Tools ---
@category(COMPUTER_CONTROL)
def capture_screen_and_analyze(aybar_instance: "EnhancedAybar", question: str, thought: Optional[str]=None) -> str:
    """Ekran görüntüsü alır ve belirtilen soru hakkında VLM ile analiz eder."""
    _, _, _, _, _, computer_control, _, _ = _get_aybar_systems(aybar_instance)
    if not computer_control: return "Bilgisayar kontrol sistemi aktif değil."
    return computer_control.analyze_screen_with_vlm(question)

@category(COMPUTER_CONTROL)
def keyboard_type_action(aybar_instance: "EnhancedAybar", text_to_type: str, thought: Optional[str]=None) -> str:
    """Belirtilen metni klavye aracılığıyla yazar."""
    _, _, _, _, _, computer_control, _, _ = _get_aybar_systems(aybar_instance)
    if not computer_control: return "Bilgisayar kontrol sistemi aktif değil."
    return computer_control.keyboard_type(text_to_type)

@category(COMPUTER_CONTROL)
def mouse_click_action(aybar_instance: "EnhancedAybar", x: int, y: int, double_click: bool = False, thought: Optional[str]=None) -> str:
    """Belirtilen koordinatlara fare ile tıklar."""
    _, _, _, _, _, computer_control, _, _ = _get_aybar_systems(aybar_instance)
    if not computer_control: return "Bilgisayar kontrol sistemi aktif değil."
    return computer_control.mouse_click(x, y, double_click)

# --- System Control Tools ---
@category(SYSTEM_CONTROL)
def summarize_and_reset_action(aybar_instance: "EnhancedAybar", summary: Optional[str]=None, thought: Optional[str]=None) -> str:
    """Mevcut durumu özetler ve düşünce döngüsünü/hedefi sıfırlar."""
    # Bu araç doğrudan EnhancedAybar'da bir bayrak ayarlayarak veya ana döngüde işlenerek
    # hedef sıfırlamasını tetikleyebilir. Şimdilik sadece bir mesaj döndürüyor.
    # Gerçek sıfırlama EnhancedAybar ana döngüsünde bu eylem türüne göre yapılmalı.
    print(f"🔄 Araç Kullanımı: Özetle ve Sıfırla. Özet: {summary}")
    # aybar_instance.active_goal = None # Bu doğrudan EnhancedAybar'da yapılmalı
    return f"Durum özetlendi ve düşünce döngüsü sıfırlanmak üzere. Özet: {summary or 'Belirtilmedi'}"

@category(SYSTEM_CONTROL)
def finish_goal_action(aybar_instance: "EnhancedAybar", summary: str, thought: Optional[str]=None) -> str:
    """Mevcut hedefi tamamlar."""
    # Bu da SUMMARIZE_AND_RESET gibi, EnhancedAybar'da işlenmeli.
    print(f"🏁 Araç Kullanımı: Hedef Bitir. Özet: {summary}")
    # aybar_instance.active_goal = None # Bu doğrudan EnhancedAybar'da yapılmalı
    return f"Hedef başarıyla tamamlandı ve sonlandırıldı. Özet: {summary}"

# EVOLVE aracı doğrudan EnhancedAybar.tools içinde SelfEvolutionSystem'e bağlanacak.
# REFLECT aracı doğrudan EnhancedAybar.tools içinde CognitiveSystem'e bağlanacak.
# Bu yüzden burada ayrıca tanımlanmalarına gerek yok.
# SpeakerSystem.speak de doğrudan çağrılabilir, bir tool olmasına gerek yok.
