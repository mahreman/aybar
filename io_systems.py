import base64
import requests
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import os # os importları dosya başına taşındı
import subprocess
from typing import TYPE_CHECKING # TYPE_CHECKING importu eklendi

# İleriye dönük bildirim / Type hinting
if TYPE_CHECKING: # if False yerine if TYPE_CHECKING kullanıldı
    from aybarcore import EnhancedAybar
    # from config import Config # Bu artık kullanılmıyor


class SpeakerSystem:
    """Metni, duygusal duruma göre farklı seslerle sese dönüştürür."""
    def __init__(self, config_data: Dict):
        self.config_data = config_data
        self.client = None
        self.voice_map = {}
        self.play_function = None # Oynatma fonksiyonunu saklamak için
        try:
            from elevenlabs import play, ElevenLabs
            self.play_function = play # play fonksiyonunu sakla
            api_key = self.config_data.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                 api_key = "sk_abd025de949665cae6a25fd4275f57885496f4ddca333659"

            if not api_key:
                raise ValueError("ElevenLabs API anahtarı yapılandırmada veya ortam değişkenlerinde bulunamadı.")

            self.client = ElevenLabs(api_key=api_key)

            self.voice_map = self.config_data.get("ELEVENLABS_VOICE_MAP", {
                "varsayilan": "75SIZa3vvET95PHhf1yD",
                "wonder": "DUnzBkwtjRWXPr6wRbmL",
                "satisfaction": "flZTNq2uzsrbxgFGPOUD",
                "existential_anxiety": "ZsYcqahfiS2dy4J6XYC5",
                "curiosity": "2EiwWnXFnvU5JabPnv8n"
            })
            print("🔊 Duygusal Konuşma Motoru (ElevenLabs) başarıyla yüklendi.")

        except ImportError:
            print("⚠️ ElevenLabs kütüphanesi bulunamadı. `pip install elevenlabs` ile kurun. Sesli özellikler devre dışı.")
            self.play_function = self._fallback_play # Fallback play fonksiyonu
        except Exception as e:
            print(f"⚠️ Konuşma motoru (ElevenLabs) başlatılamadı: {e}. Sesli özellikler devre dışı.")
            self.client = None
            self.play_function = self._fallback_play # Fallback play fonksiyonu

    def _fallback_play(self, audio_content: bytes, filename: str = "temp_audio_fallback.mp3"):
        """
        ElevenLabs play fonksiyonu olmadığında ses dosyasını kaydedip
        işletim sistemi varsayılan oynatıcısı ile açmayı dener.
        """
        try:
            with open(filename, "wb") as f:
                f.write(audio_content)

            print(f"🎧 Fallback: Ses '{filename}' olarak kaydedildi. Manuel oynatma gerekebilir.")
            if os.name == 'nt': # Windows
                os.startfile(filename)
            elif os.name == 'posix': # macOS, Linux
                # mpg123 veya aplay gibi bir komut satırı oynatıcısı denenir
                if filename.endswith(".mp3") and subprocess.run(['which', 'mpg123'], capture_output=True, text=True).returncode == 0:
                    subprocess.call(['mpg123', '-q', filename])
                elif subprocess.run(['which', 'aplay'], capture_output=True, text=True).returncode == 0: # .wav için daha uygun olabilir
                    subprocess.call(['aplay', filename])
                else:
                    print("Uygun bir komut satırı oynatıcısı (mpg123, aplay) bulunamadı.")
            # Geçici dosyayı silmek için bir mekanizma eklenebilir, ancak oynatıcının bitmesini beklemek gerekir.
        except Exception as e:
            print(f"⚠️ Fallback ses oynatma sırasında hata: {e}")


    def speak(self, text: str, emotional_state: Dict):
        if not text.strip(): return

        if not self.client: # Eğer ElevenLabs client başlatılamadıysa
            print("⚠️ ElevenLabs client mevcut değil. Seslendirme yapılamıyor.")
            # İsteğe bağlı olarak burada pyttsx3 gibi bir fallback eklenebilir.
            # self._pyttsx3_speak(text)
            return

        try:
            dominant_emotion = max(emotional_state, key=emotional_state.get)
            voice_id = self.voice_map.get(dominant_emotion, self.voice_map.get("varsayilan"))
            print(f"🎤 Aybar konuşuyor... (Duygu: {dominant_emotion}, Ses: {voice_id})")

            audio = self.client.generate(
                text=text,
                voice=voice_id, # type: ignore
                model=self.config_data.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
            )
            if audio:
                if self.play_function:
                    self.play_function(audio) # Saklanan play fonksiyonunu çağır
                else: # Eğer play_function None ise (bir hata oluşmuşsa)
                    print("⚠️ Oynatma fonksiyonu bulunamadı. Ses dosyası oynatılamıyor.")
                    self._fallback_play(audio) # Fallback'i burada da dene
            else:
                print("⚠️ ElevenLabs'ten ses verisi alınamadı.")

        except Exception as e:
            print(f"⚠️ Seslendirme sırasında hata: {e}")


class WebSurferSystem:
    """Selenium kullanarak web tarayıcısını yönetir, sayfaları analiz eder."""
    def __init__(self, config_data: Optional[Dict] = None): # config_data eklendi, opsiyonel
        self.driver = None
        self.config_data = config_data if config_data else {}
        try:
            options = webdriver.ChromeOptions()
            if self.config_data.get("WEB_SURFER_HEADLESS", False): # Headless ayarı config'den
                 options.add_argument('--headless')
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            print("🌐 Web Sörfçüsü motoru (Selenium) başarıyla başlatıldı.")
        except Exception as e:
            print(f"❌ Web Sörfçüsü motoru başlatılamadı: {e}")

    def navigate_to(self, url: str):
        if self.driver:
            print(f"🧭 Sayfaya gidiliyor: {url}")
            self.driver.get(url)

    @staticmethod
    def get_element_xpath(driver, element) -> str:
        script = """
        var getPathTo = function(element) {
            if (element.id !== '') return 'id(\"' + element.id + '\")';
            if (element === document.body) return element.tagName.toLowerCase();
            var ix = 0;
            var siblings = element.parentNode.childNodes;
            for (var i = 0; i < siblings.length; i++) {
                var sibling = siblings[i];
                if (sibling === element)
                    return getPathTo(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                    ix++;
            }
        };
        return getPathTo(arguments[0]);
        """
        try:
            return driver.execute_script(script, element)
        except Exception:
            return "xpath_bulunamadi"

    def get_current_state_for_llm(self) -> Tuple[str, List[Dict]]:
        if not self.driver: return "Tarayıcıya erişilemiyor.", []

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        for script_or_style in soup(["script", "style"]): # Düzeltildi: script_or_style
            script_or_style.extract()
        page_text = soup.get_text(separator=' ', strip=True)[:6000]

        interactive_elements = []
        element_id_counter = 0

        clickable_selectors = "//a[@href] | //button | //input[@type='submit'] | //input[@type='button'] | //*[(@role='button') or (@role='link')]"
        input_selectors = "//textarea | //input[not(@type)] | //input[@type='text' or @type='search' or @type='email' or @type='password' or @type='number']"

        clickable_elements_selenium = self.driver.find_elements(By.XPATH, clickable_selectors)
        input_elements_selenium = self.driver.find_elements(By.XPATH, input_selectors)

        for element in clickable_elements_selenium:
            try:
                text = ' '.join(element.text.strip().split()) or element.get_attribute('aria-label') or "İsimsiz Link/Buton"
                if text and element.is_displayed() and element.is_enabled(): # Görünür ve etkin elementler
                    xpath = self.get_element_xpath(self.driver, element)
                    interactive_elements.append({"id": element_id_counter, "type": "click", "text": text[:100], "xpath": xpath})
                    element_id_counter += 1
            except Exception: continue # Stale element gibi hataları atla

        for element in input_elements_selenium:
            try:
                if element.is_displayed() and element.is_enabled(): # Görünür ve etkin elementler
                    label = element.get_attribute('aria-label') or element.get_attribute('name') or element.get_attribute('placeholder') or f'yazı_girişi_{element_id_counter}'
                    xpath = self.get_element_xpath(self.driver, element)
                    interactive_elements.append({"id": element_id_counter, "type": "type", "label": label, "xpath": xpath})
                    element_id_counter += 1
            except Exception: continue

        return page_text, interactive_elements

    def perform_web_action(self, action_item: Dict) -> str:
        if not self.driver: return "Tarayıcıya erişilemiyor."

        action_type = action_item.get("action_type", "").lower()
        target_xpath = action_item.get("target_xpath")
        wait_timeout = self.config_data.get("WEB_ELEMENT_WAIT_TIMEOUT", 10)

        if not target_xpath:
            return "Hata: Eylem için bir hedef XPath belirtilmedi."

        try:
            wait = WebDriverWait(self.driver, wait_timeout)

            if action_type == 'click':
                target_element = wait.until(EC.element_to_be_clickable((By.XPATH, target_xpath)))
                print(f"🖱️ Element'e XPath ile tıklanıyor: '{target_xpath}'")
                target_element.click()
                return f"Başarıyla '{target_xpath}' adresindeki elemente tıklandı."

            elif action_type == 'type':
                target_element = wait.until(EC.visibility_of_element_located((By.XPATH, target_xpath)))
                text_to_type = action_item.get("text", "")
                print(f"⌨️ Element'e XPath ile yazılıyor: '{target_xpath}', Metin: '{text_to_type}'")
                target_element.clear()
                target_element.send_keys(text_to_type)
                try:
                    target_element.send_keys(Keys.RETURN)
                except Exception: pass
                return f"Başarıyla '{target_xpath}' adresindeki alana '{text_to_type}' yazıldı."

            else:
                return f"Hata: Bilinmeyen eylem türü '{action_type}'"

        except TimeoutException:
            return f"Hata: Hedef element (XPath: {target_xpath}) {wait_timeout} saniye içinde bulunamadı veya etkileşime hazır hale gelmedi."
        except Exception as e:
            return f"Web eylemi sırasında hata: {e.__class__.__name__} - {str(e)}"

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None # Sürücüyü None olarak ayarla


class ComputerControlSystem:
    """Aybar'ın bilgisayarın masaüstünü görmesini ve kontrol etmesini sağlar."""
    def __init__(self, aybar_instance: "EnhancedAybar"):
        self.aybar = aybar_instance
        self.config_data = aybar_instance.config_data
        self.api_url = self.config_data.get("HARDWARE_API_URL", "http://localhost:5151")

    def capture_screen(self, filename="screenshot.png") -> Optional[str]:
        try:
            response = requests.get(f"{self.api_url}/screen/capture", timeout=self.config_data.get("API_TIMEOUT_SECONDS", 10))
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                img_data = base64.b64decode(data["image_base64"])
                with open(filename, "wb") as f:
                    f.write(img_data)
                print(f"🖥️ Ekran görüntüsü API'den alındı ve '{filename}' olarak kaydedildi.")
                return filename
            else:
                print(f"⚠️ Ekran görüntüsü alınamadı: {data.get('message')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Donanım API'sine bağlanılamadı: {e}")
            return None

    def analyze_screen_with_vlm(self, question: str) -> str:
        print(f"👀 Ekran analiz ediliyor: '{question}'")
        screenshot_file = self.capture_screen()
        if not screenshot_file:
            return "Ekranı göremiyorum, bir hata oluştu."

        vision_prompt = f"Görüntüdeki '{question}' sorusunu cevapla. Cevabını sadece JSON formatında ver. Örnek: {{'found': true, 'x': 150, 'y': 320}}"

        if not hasattr(self.aybar, 'llm_manager'):
            return "⚠️ LLMManager bulunamadı, ekran analizi yapılamıyor."

        vision_response = self.aybar.llm_manager.ask_llm(
            vision_prompt,
            model_name=self.config_data.get("VISION_MODEL_NAME"),
            max_tokens=512
        )

        print(f"👁️ Görsel analiz sonucu: {vision_response}")
        return vision_response

    def keyboard_type(self, text: str) -> str:
        try:
            response = requests.post(f"{self.api_url}/keyboard/type", json={"text": text}, timeout=10)
            response.raise_for_status()
            return response.json().get("message", "Yazı yazma eylemi gönderildi.")
        except requests.exceptions.RequestException as e:
            return f"⚠️ Klavye kontrol hatası: Donanım API'sine bağlanılamadı: {e}"

    def mouse_click(self, x: int, y: int, double_click: bool = False) -> str:
        try:
            response = requests.post(f"{self.api_url}/mouse/click", json={"x": x, "y": y, "double": double_click}, timeout=5)
            response.raise_for_status()
            return response.json().get("message", "Tıklama eylemi gönderildi.")
        except requests.exceptions.RequestException as e:
            return f"⚠️ Fare kontrol hatası: Donanım API'sine bağlanılamadı: {e}"

# os ve subprocess importları dosya başına taşındı.
# time importu kaldırıldı, artık kullanılmıyor.
