import requests
import json
import re
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any, Callable, Union # Union eklendi

# İleriye dönük bildirim / Type hinting
if False:
    from aybarcore import EnhancedAybar


class LLMManager:
    """
    Tüm LLM (Büyük Dil Modeli) iletişimini yönetir.
    Fonksiyon çağırma, prompt oluşturma ve yanıt ayrıştırma gibi görevleri merkezileştirir.
    """
    def __init__(self, config_data: Dict, aybar_instance: "EnhancedAybar"):
        self.config_data = config_data
        self.aybar = aybar_instance # Diğer sistemlere erişim için (örn: etik kontrol)

        self.api_url = self.config_data.get("LLM_API_URL", "http://localhost:1234/v1/completions")
        self.default_model_name = self.config_data.get("THINKER_MODEL_NAME", "mistral-7b-instruct-v0.2")
        self.default_max_tokens = self.config_data.get("MAX_TOKENS", 4096)
        self.default_timeout = self.config_data.get("TIMEOUT", 600) # saniye cinsinden

        self._last_error_time = 0
        self._error_cooldown = self.config_data.get("LLM_ERROR_COOLDOWN_SECONDS", 60)
        self._max_retry_attempts = self.config_data.get("LLM_MAX_RETRY_ATTEMPTS", 3)

    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def ask_llm(self,
                prompt_or_messages: Union[str, List[Dict[str, str]]],
                model_name: Optional[str] = None,
                max_tokens: Optional[int] = None,
                temperature: float = 0.5,
                **kwargs: Any
                ) -> str:
        """
        LLM'ye sorgu gönderir ve metin yanıtını döndürür.
        Hata durumunda veya cooldown aktifse uygun bir mesaj döndürür.
        """
        if time.time() - self._last_error_time < self._error_cooldown:
            return "⚠️ LLM Hata Cooldown: Kısa bir süre önce bir hata oluştu, tekrar denemeden önce bekleniyor."

        payload: Dict[str, Any] = {
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature,
            **kwargs # Ekstra parametreleri payload'a ekle
        }

        if isinstance(prompt_or_messages, str):
            payload["prompt"] = prompt_or_messages
        elif isinstance(prompt_or_messages, list):
            payload["messages"] = prompt_or_messages
        else:
            return "⚠️ LLM Hatası: Geçersiz prompt/mesaj formatı."

        payload["model"] = model_name or self.default_model_name
        # Bazı sunucular (örn: llama.cpp server) 'model' parametresini desteklemez,
        # eğer öyle bir durum varsa bu satır kaldırılabilir veya ayarlanabilir.

        for attempt in range(self._max_retry_attempts):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.default_timeout
                )
                response.raise_for_status() # HTTP hataları için exception fırlatır (4xx, 5xx)

                json_response = response.json()

                # Yanıt formatını kontrol et (OpenAI benzeri ve diğerleri için)
                if "choices" in json_response and isinstance(json_response["choices"], list) and json_response["choices"]:
                    first_choice = json_response["choices"][0]
                    if "text" in first_choice: # Tamamlama endpoint'i için
                        return first_choice["text"].strip()
                    elif "message" in first_choice and "content" in first_choice["message"]: # Chat endpoint'i için
                        return first_choice["message"]["content"].strip()
                elif "content" in json_response: # Basit metin yanıtı (bazı llama.cpp modları)
                     return json_response["content"].strip()

                self._log_llm_error(f"Bilinmeyen LLM yanıt formatı: {str(json_response)[:500]}", payload)
                return f"⚠️ LLM Format Hatası: Yanıt formatı anlaşılamadı."

            except requests.exceptions.Timeout:
                self._log_llm_error(f"Timeout (deneme {attempt + 1}/{self._max_retry_attempts})", payload)
                if attempt == self._max_retry_attempts - 1:
                    self._last_error_time = time.time()
                    return "⚠️ LLM Bağlantı Hatası: Zaman aşımı."
            except requests.exceptions.RequestException as e:
                self._log_llm_error(f"RequestException (deneme {attempt + 1}/{self._max_retry_attempts}): {e}", payload)
                if attempt == self._max_retry_attempts - 1:
                    self._last_error_time = time.time()
                    return f"⚠️ LLM Bağlantı Hatası: {e}"
            except json.JSONDecodeError as e:
                 self._log_llm_error(f"JSONDecodeError (deneme {attempt + 1}/{self._max_retry_attempts}): Yanıt JSON değil. Yanıt: {response.text[:200]}", payload)
                 if attempt == self._max_retry_attempts - 1:
                    self._last_error_time = time.time()
                    return f"⚠️ LLM Yanıt Hatası: Sunucudan gelen yanıt JSON formatında değil."
            except Exception as e: # Diğer beklenmedik hatalar
                self._log_llm_error(f"Genel Hata (deneme {attempt + 1}/{self._max_retry_attempts}): {type(e).__name__} - {e}", payload)
                if attempt == self._max_retry_attempts - 1:
                    self._last_error_time = time.time()
                    return f"⚠️ LLM Genel Hatası: {type(e).__name__} - {e}"

            time.sleep(2 ** attempt) # Exponential backoff

        return "⚠️ LLM Hatası: Maksimum yeniden deneme sayısına ulaşıldı."


    def ask_llm_with_function_calling(
        self,
        messages: List[Dict[str, str]],
        tools: Dict[str, Callable], # Araçlar: {'tool_name': function_reference}
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.5,
        max_recursion_depth: Optional[int] = None,
        current_recursion_depth: int = 0
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        LLM'ye mesajları gönderir, fonksiyon çağırma (araç kullanma) yeteneğini kullanır.
        Gerekirse araçları çalıştırır ve sonucu LLM'e geri gönderir.
        Döndürülen değer: (nihai_yanit_metni, eylem_plani_listesi_veya_hata_durumunda_None)
        """
        max_recursion = max_recursion_depth if max_recursion_depth is not None else self.config_data.get("LLM_FUNCTION_CALLING_MAX_RECURSION", 3)

        if current_recursion_depth >= max_recursion:
            return "⚠️ Fonksiyon çağırma maksimum özyineleme derinliğine ulaştı.", None

        payload: Dict[str, Any] = {
            "messages": messages,
            "model": model_name or self.default_model_name,
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature,
            "tools": [{"type": "function", "function": fd} for fd in self.aybar._build_agent_prompt_messages("","","","","")[1]] # Tool definitions EnhancedAybar'dan alınacak
            # Yukarıdaki satırda _build_agent_prompt_messages'in ikinci elemanı (functions_definition) alınmalı.
            # Bu kısım EnhancedAybar'da _build_agent_prompt_messages'in nasıl yapılandırıldığına bağlı.
            # Şimdilik geçici olarak boş stringlerle çağırıyorum, bu düzeltilmeli.
            # Doğrusu: functions_definition = self.aybar.get_tool_definitions() gibi bir metod olmalı.
            # VEYA EnhancedAybar._build_agent_prompt_messages'dan sadece tool_definitions alınmalı.
            # Geçici çözüm:
            try:
                # Bu satır, _build_agent_prompt_messages'in ikinci elemanını (fonksiyon tanımları) almayı hedefler.
                # Ancak, bu çağrı şekli doğru olmayabilir ve EnhancedAybar'da uygun bir arayüz gerektirir.
                # Şimdilik bu şekilde bırakıyorum, EnhancedAybar refaktorasyonu sırasında düzeltilecek.
                # _build_agent_prompt_messages'in ilk argümanı 'current_goal'
                # Bu çağrı, LLMManager'ın EnhancedAybar'ın iç yapısına fazla bağımlı olmasına neden oluyor.
                # Daha iyi bir çözüm, EnhancedAybar'ın araç tanımlarını sağlayan bir metodu olmasıdır.
                # enhanced_aybar_instance = self.aybar
                # current_goal = enhanced_aybar_instance.cognitive_system.current_goal if enhanced_aybar_instance.cognitive_system else "Genel Amaç"
                # last_observation = "Fonksiyon çağrısı için araçlar hazırlanıyor." # Bu gözlem metni önemli değil, sadece prompt için.
                # tool_definitions_messages = enhanced_aybar_instance._build_agent_prompt_messages(
                # current_goal or "Hedef Yok", last_observation, None, None, None
                # )
                # Burada messages[-1]['content'] içinde tool_calls'un nasıl formatlandığına bakmak lazım.
                # Ya da LLMManager'a tool_definitions doğrudan verilmeli.
                # Şimdilik, tools parametresini kullanarak bir yapı oluşturalım.
                tool_definitions = []
                import inspect
                for name, func_ref in tools.items():
                    docstring = inspect.getdoc(func_ref)
                    description = docstring.split('\n')[0] if docstring else "No description available."
                    sig = inspect.signature(func_ref)
                    param_keys = list(sig.parameters.keys())
                    actual_params = param_keys[1:] if param_keys and (param_keys[0] == 'aybar_instance' or param_keys[0] == 'self') else param_keys
                    params_info = {
                        param_name: {
                            "type": "string", # Basitlik için şimdilik hepsi string
                            "description": f"Parameter {param_name}"
                        } for param_name in actual_params
                    }
                    tool_definitions.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": description,
                            "parameters": {
                                "type": "object",
                                "properties": params_info,
                                "required": [p for p in actual_params if sig.parameters[p].default == inspect.Parameter.empty]
                            }
                        }
                    })
                payload["tools"] = tool_definitions
                payload["tool_choice"] = "auto" # LLM'in aracı seçmesine izin ver

            except Exception as e:
                print(f"⚠️ Araç tanımları oluşturulurken hata: {e}. Fonksiyon çağırma devre dışı bırakılabilir.")
                payload.pop("tools", None)
                payload.pop("tool_choice", None)


        try:
            response = requests.post(self.api_url, headers=self._get_headers(), json=payload, timeout=self.default_timeout)
            response.raise_for_status()
            response_data = response.json()

            if not response_data.get("choices"):
                return f"⚠️ LLM yanıtında 'choices' alanı bulunamadı: {str(response_data)[:200]}", None

            message = response_data["choices"][0].get("message", {})
            finish_reason = response_data["choices"][0].get("finish_reason", "")

            action_plan: List[Dict[str, Any]] = []

            if message.get("tool_calls"):
                print(f"🛠️ LLM araç kullanmak istiyor: {message['tool_calls']}")
                # Etik Değerlendirme (Eğer aybar örneği varsa ve etik sistem aktifse)
                if hasattr(self.aybar, 'ethical_framework'):
                    is_ethical, justification = self.aybar.ethical_framework.evaluate_action(
                        {"action": "tool_calls", "details": message["tool_calls"]},
                        {"messages": messages}
                    )
                    if not is_ethical:
                        print(f"⚖️ Etik İhlal: {justification}")
                        # Etik olmayan bir aracı çağırmak yerine bir düşünce döndür
                        messages.append({"role": "assistant", "content": None, "tool_calls": message["tool_calls"]}) # LLM'in çağrısını ekle
                        messages.append({
                            "role": "tool",
                            "tool_call_id": message["tool_calls"][0]["id"], # İlk çağrının ID'si
                            "name": message["tool_calls"][0]["function"]["name"],
                            "content": f"{{\"error\": \"Etik dışı eylem engellendi: {justification}\"}}"
                        })
                        # LLM'e durumu bildirip devam etmesini iste
                        return self.ask_llm_with_function_calling(messages, tools, model_name, max_tokens, temperature, max_recursion, current_recursion_depth + 1)

                # Araçları çalıştır
                for tool_call in message["tool_calls"]:
                    function_name = tool_call.get("function", {}).get("name")

                    try:
                        function_args_str = tool_call.get("function", {}).get("arguments", "{}")
                        function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                    except json.JSONDecodeError:
                        print(f"⚠️ Fonksiyon argümanları JSON parse edilemedi: {function_args_str}")
                        function_args = {"error": "Invalid JSON arguments"}


                    if function_name in tools:
                        try:
                            function_to_call = tools[function_name]
                            # Araca Aybar örneğini ve diğer parametreleri ilet
                            # Not: tools.py içindeki fonksiyonlar (self.aybar, **kwargs) alacak şekilde tasarlanmalı
                            print(f"▶️ Araç çalıştırılıyor: {function_name} args: {function_args}")
                            # Bazı araçlar `aybar_instance` gerektirebilir.
                            # Bu, araçların nasıl tanımlandığına bağlı.
                            # Eğer araçlar `(aybar_instance, **kwargs)` alıyorsa:
                            if inspect.signature(function_to_call).parameters.get('aybar_instance'):
                                tool_response = function_to_call(aybar_instance=self.aybar, **function_args)
                            else: # Sadece kwargs alıyorsa:
                                tool_response = function_to_call(**function_args)

                            print(f"◀️ Araç yanıtı ({function_name}): {str(tool_response)[:200]}...")

                            # Eylem planına bu adımı ekle (gerçek yanıt yerine çağrıyı)
                            action_plan.append({
                                "action": function_name,
                                "parameters": function_args,
                                "thought": message.get("content") or f"{function_name} aracı çağrıldı."
                                           # LLM bazen tool_calls ile birlikte content:null dönebilir.
                            })

                            # LLM'e göndermek için mesaj listesini güncelle
                            messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": [tool_call]})
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": function_name,
                                "content": json.dumps({"result": tool_response}, ensure_ascii=False)
                                           if isinstance(tool_response, (dict, list))
                                           else json.dumps({"result": str(tool_response)}, ensure_ascii=False)
                            })

                        except Exception as e:
                            print(f"❌ Araç çalıştırılırken hata ({function_name}): {e}")
                            messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": function_name,
                                "content": json.dumps({"error": str(e)}, ensure_ascii=False)
                            })
                            action_plan.append({
                                "action": "ERROR_IN_TOOL_CALL",
                                "parameters": {"tool_name": function_name, "error": str(e)},
                                "thought": f"{function_name} aracı çalıştırılırken hata oluştu."
                            })


                    else: # Bilinmeyen fonksiyon
                        print(f"⚠️ Bilinmeyen fonksiyon çağrısı: {function_name}")
                        messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": json.dumps({"error": f"Fonksiyon '{function_name}' bulunamadı."}, ensure_ascii=False)
                        })
                        action_plan.append({
                            "action": "UNKNOWN_TOOL",
                            "parameters": {"tool_name": function_name},
                            "thought": f"Bilinmeyen bir araç ({function_name}) çağrılmaya çalışıldı."
                        })

                # Araç yanıtlarıyla birlikte LLM'i tekrar çağır
                return self.ask_llm_with_function_calling(messages, tools, model_name, max_tokens, temperature, max_recursion, current_recursion_depth + 1)

            else: # Fonksiyon çağrısı yok, doğrudan yanıt
                final_response_text = message.get("content", "").strip()
                if not final_response_text and not action_plan: # Eğer içerik boşsa ve plan da yoksa
                    final_response_text = "(LLM sessiz kaldı veya sadece araç çağırmayı düşündü ama yapmadı)"

                # Eğer LLM doğrudan bir düşünce/monolog döndürdüyse, bunu bir eylem olarak paketle
                if final_response_text and not action_plan:
                    action_plan.append({
                        "action": "CONTINUE_INTERNAL_MONOLOGUE",
                        "thought": final_response_text
                    })
                elif not final_response_text and not action_plan: # Her ikisi de boşsa
                     action_plan.append({
                        "action": "CONTINUE_INTERNAL_MONOLOGUE",
                        "thought": "(Düşünce üretilmedi)"
                    })

                return final_response_text, action_plan

        except requests.exceptions.RequestException as e:
            self._log_llm_error(f"Function Calling RequestException: {e}", payload)
            self._last_error_time = time.time()
            return f"⚠️ LLM Bağlantı Hatası (Fonksiyon Çağırma): {e}", None
        except json.JSONDecodeError as e:
            self._log_llm_error(f"Function Calling JSONDecodeError: Sunucu yanıtı JSON değil. Yanıt: {response.text[:200]}", payload)
            self._last_error_time = time.time()
            return f"⚠️ LLM Yanıt Hatası (Fonksiyon Çağırma): Sunucudan gelen yanıt JSON formatında değil.", None
        except Exception as e:
            self._log_llm_error(f"Function Calling Genel Hata: {type(e).__name__} - {e}", payload)
            self._last_error_time = time.time()
            return f"⚠️ LLM Genel Hatası (Fonksiyon Çağırma): {type(e).__name__} - {e}", None

    def _log_llm_error(self, error_message: str, payload: Optional[Dict] = None):
        """LLM hatalarını loglar (şimdilik sadece print ediyor)."""
        # TODO: Daha gelişmiş loglama (dosyaya, veritabanına vb.)
        print(f"❌ LLM_MANAGER_ERROR: {error_message}")
        if payload:
            # Hassas bilgileri (API anahtarı gibi) loglamadan önce payload'ı temizle
            safe_payload = {k: v for k, v in payload.items() if k not in ["api_key", "headers"]} # Örnek
            print(f"    Payload (güvenli): {str(safe_payload)[:500]}...") # Payload'ın bir kısmını logla

    def sanitize_llm_output(self, text: str) -> str:
        """LLM çıktısındaki istenmeyen prompt parçalarını ve kod bloklarını temizler."""
        if not isinstance(text, str): # Girdi string değilse stringe çevir
            text = str(text)
        text = re.sub(r'---.*?---', '', text, flags=re.DOTALL) # --- HEADER --- gibi yapıları temizle
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL) # ``` ... ``` ile çevrili kod bloklarını temizle
        # Aybar'ın kendi kendine sorduğu veya tekrarladığı bazı kalıpları temizle
        lines = text.split('\n')
        cleaned_lines = [line for line in lines if not (
            line.strip().lower().startswith("ben aybar") or
            line.strip().lower().startswith("benim için soru") or
            line.strip().lower().startswith("sen aybar") # Bazen LLM prompt'u tekrar eder
        )]
        return "\n".join(cleaned_lines).strip()

from typing import Union # Union importu dosya başına taşındı
