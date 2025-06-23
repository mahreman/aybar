import os
import re
import sys
import subprocess
import ast
import astor
from datetime import datetime
from typing import Dict, Optional, Any, List, TYPE_CHECKING
import json
import shutil

if TYPE_CHECKING:
    from aybarcore import EnhancedAybar


class SelfEvolutionSystem:
    def __init__(self, aybar_instance: "EnhancedAybar"):
        self.aybar = aybar_instance
        self.config_data = aybar_instance.config_data
        try:
            main_module = sys.modules.get('__main__')
            if hasattr(main_module, '__file__') and main_module.__file__:
                self.source_code_path = os.path.realpath(main_module.__file__)
            else:
                self.source_code_path = os.path.realpath(sys.argv[0])
        except Exception:
             self.source_code_path = os.path.realpath(sys.argv[0])
        print(f"🛠️ SelfEvolutionSystem: Source code path set to '{self.source_code_path}'")
        self.backup_path = f"{self.source_code_path}.bak"
        self.consecutive_evolution_failures = 0

    class FunctionReplacer(ast.NodeTransformer):
        def __init__(self, target_func_name: str, new_func_code: str):
            self.target_func_name = target_func_name
            self.new_func_node = ast.parse(new_func_code).body[0]
            self.success = False

        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            if node.name == self.target_func_name:
                self.success = True
                return self.new_func_node
            return node

    class ClassMethodAdder(ast.NodeTransformer):
        def __init__(self, target_class_name: str, new_func_code: str):
            self.target_class_name = target_class_name
            self.new_nodes = ast.parse(new_func_code).body
            self.success = False

        def visit_ClassDef(self, node: ast.ClassDef) -> Any:
            if node.name == self.target_class_name:
                node.body.extend(self.new_nodes)
                self.success = True
            return node

    def get_source_code(self) -> Optional[str]:
        try:
            with open(self.source_code_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"ERROR: Kaynak kodu ({self.source_code_path}) okunamadı: {e}")
            return None

    def analyze_and_propose_change(self, problem_description: Optional[str] = None) -> Optional[Dict]:
        source_code = self.get_source_code()
        if not source_code:
            return None

        prompt_context = f"Karşılaştığım sorun şu: '{problem_description}'" if problem_description else "Kendimi proaktif olarak geliştirmek için deneysel ve yaratıcı bir değişiklik yapmak istiyorum."
        prompt = f"""
        Sen, kendi Python kaynak kodunu düzenleyebilen bir yapay zeka olan Aybar'ın mühendis beynisin.
        Amacın: {prompt_context}
        JSON formatına harfiyen uyarak bir çözüm öner. ```json ... ``` işaretleri BAŞINDA ve SONUNDA olsun. Başka metin ekleme.
        ```json
        {{
          "thought": "Değişikliği neden ve nasıl yapacağına dair kısa bir düşünce.",
          "operation_type": "'REPLACE_FUNCTION', 'ADD_NEW_FUNCTION', 'INSERT_CODE_AFTER_LINE'",
          "target": {{
            "class_name": "Sınıf adı, örn: 'EnhancedAybar'",
            "function_name": "Fonksiyon adı, örn: '_ask_llm_uncached'",
            "anchor_line": "'INSERT_CODE_AFTER_LINE' ise, kodun hangi satırdan SONRA ekleneceği (tam metin)."
          }},
          "code": "Tam ve çalışır Python kodu bloğu. Girintilere dikkat et."
        }}
        ```
        Kaynak Kod (ilk 10000 karakter):
        {source_code[:10000]}
        """
        response_text = self.aybar.llm_manager.ask_llm(
            prompt,
            model_name=self.config_data.get("ENGINEER_MODEL_NAME"),
            max_tokens=2048,
            temperature=0.4
        )
        try:
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if not json_match:
                print(f"⚠️ Evrim Hatası: LLM geçerli bir ```json``` bloğu döndürmedi. Dönen Metin:\n{response_text}")
                return None
            clean_json_str = json_match.group(1)
            return json.loads(clean_json_str)
        except json.JSONDecodeError as e:
            print(f"⚠️ Evrim Hatası: JSON parse edilemedi: {e}\nDönen Metin: {response_text}")
            return None

    def _apply_code_change(self, original_code: str, instruction: Dict) -> Optional[str]:
        op_type = instruction.get("operation_type")
        target = instruction.get("target", {})
        code_to_apply = instruction.get("code", "").replace('\\n', '\n').strip()
        if not code_to_apply:
            print("⚠️ Evrim Hatası: Uygulanacak kod içeriği boş.")
            return None
        try:
            tree = ast.parse(original_code)
            transformer: Optional[ast.NodeTransformer] = None
            if op_type == "REPLACE_FUNCTION":
                func_name = target.get("function_name")
                if not func_name: return None
                transformer = self.FunctionReplacer(func_name, code_to_apply)
            elif op_type == "ADD_NEW_FUNCTION":
                class_name = target.get("class_name")
                if not class_name: return None
                transformer = self.ClassMethodAdder(class_name, code_to_apply)
            else:
                print(f"⚠️ Bu evrim sistemi şimdilik sadece REPLACE_FUNCTION ve ADD_NEW_FUNCTION desteklemektedir.")
                return None
            if transformer:
                new_tree = transformer.visit(tree)
                if not getattr(transformer, 'success', False):
                    target_name = target.get('function_name') or target.get('class_name')
                    print(f"ERROR: AST içinde hedef '{target_name}' bulunamadı.")
                    return None
                return astor.to_source(new_tree)
            return None
        except Exception as e:
            print(f"❌ Kod analizi (AST) sırasında kritik hata: {e}")
            return None

    def test_and_apply_change(self, change_instruction: Dict, original_code: str):
        print(f"💡 EVRİM ÖNERİSİ ({change_instruction.get('operation_type')}): {change_instruction.get('thought')}")
        new_code = self._apply_code_change(original_code, change_instruction)
        if not new_code:
            print("⚠️ Evrimsel değişiklik uygulanamadı.")
            return

        temp_file_path = self.source_code_path.replace(".py", f"_v{self.aybar.current_turn + 1}.py")
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)

        print(f"TEST: '{temp_file_path}' test ediliyor...")
        process_env = os.environ.copy()
        process_env["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen([sys.executable, temp_file_path, "--test-run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=process_env)
        try:
            stdout, stderr = process.communicate(timeout=self.config_data.get("EVOLUTION_TEST_TIMEOUT", 60))
            if process.returncode != 0 or "Traceback" in stderr or "Error" in stderr.lower():
                print(f"TEST BAŞARISIZ: Hata:\n{stderr or stdout}")
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                self.consecutive_evolution_failures += 1
                if self.consecutive_evolution_failures >= self.config_data.get("EVOLUTION_MAX_CONSECUTIVE_FAILURES", 3):
                    current_rate = self.config_data.get("PROACTIVE_EVOLUTION_RATE", 0.02)
                    self.config_data["PROACTIVE_EVOLUTION_RATE"] = current_rate / 2
                    print(f"⚠️ Art arda {self.consecutive_evolution_failures} evrim hatası. Evrim oranı düşürüldü: {self.config_data['PROACTIVE_EVOLUTION_RATE']:.2%}")
            else:
                print("TEST BAŞARILI: Değişiklikler kalıcı hale getiriliyor.")
                self.consecutive_evolution_failures = 0
                current_rate = self.config_data.get("PROACTIVE_EVOLUTION_RATE", 0.01)
                self.config_data["PROACTIVE_EVOLUTION_RATE"] = min(0.05, current_rate * 1.2)
                self.aybar.memory_system.add_memory("semantic", {"turn": self.aybar.current_turn, "insight": f"Başarılı evrim: {change_instruction.get('thought')}"})
                print(f"GUARDIAN_REQUEST: EVOLVE_TO {temp_file_path}")
                sys.exit(0)
        except subprocess.TimeoutExpired:
            process.kill()
            print("TEST BAŞARISIZ: Zaman aşımı.")
            if os.path.exists(temp_file_path): os.remove(temp_file_path)
            self.consecutive_evolution_failures +=1

    def trigger_self_evolution(self, problem: Optional[str] = None):
        if problem:
            print(f"🧬 REAKTİF EVRİM TETİKLENDİ: {problem[:100]}...")
        else:
            print("🔬 PROAKTİF EVRİM TETİKLENDİ: Deneysel bir iyileştirme aranıyor...")
        original_code = self.get_source_code()
        if not original_code: return
        proposed_instruction = self.analyze_and_propose_change(problem)
        if not proposed_instruction:
            print("⚠️ Evrim için geçerli bir talimat üretilemedi.")
            insight_text = "Mühendis Beyin'den geçerli bir evrim talimatı alamadım."
            self.aybar.emotional_system.update_state(
                self.aybar.memory_system, self.aybar.embodied_self,
                {"confusion": 1.5, "mental_fatigue": 0.5, "satisfaction": -1.0},
                self.aybar.current_turn, "failed_evolution_planning"
            )
            self.aybar.memory_system.add_memory("semantic", {
                "timestamp": datetime.now().isoformat(), "turn": self.aybar.current_turn,
                "insight": insight_text, "source": "failed_evolution"
            })
            return
        self.test_and_apply_change(proposed_instruction, original_code)

    def rollback_from_backup(self):
        if not os.path.exists(self.backup_path):
            print("⚠️ Geri yüklenecek bir yedek (.bak) dosyası bulunamadı.")
            return False
        try:
            print(f"🔩 Geri yükleme başlatıldı... '{self.backup_path}' dosyası '{self.source_code_path}' üzerine geri yükleniyor.")
            shutil.copy(self.backup_path, self.source_code_path)
            print(f"✅ Geri yükleme başarılı. Aybar, son stabil haline döndürüldü.")
            return True
        except Exception as e:
            print(f"❌ Geri yükleme sırasında kritik bir hata oluştu: {e}")
            return False

    def self_reflection_engine(self) -> Optional[List[str]]:
        recent_memories = self.aybar.memory_system.get_memory(layer="semantic", num_records=10)
        if not recent_memories:
            print("🧩 Bellekten anlamlı yansıma verisi alınamadı.")
            return None
        prompt = f"""
        Aşağıda Aybar'ın son 10 anlamsal hafızası var. Bunları analiz et ve Aybar'ın kendini geliştirmesi
        için potansiyel problem tanımları veya iyileştirme önerileri çıkar.
        Her bir öneriyi kısa, net bir problem tanımı olarak '- ' ile başlayan ayrı bir satırda yaz.

        --- Hafızalar ---
        {json.dumps(recent_memories, indent=2, ensure_ascii=False)}
        --- Problem Tanımları/İyileştirme Önerileri ---
        """
        response_text = self.aybar.llm_manager.ask_llm(
            prompt,
            model_name=self.config_data.get("ENGINEER_MODEL_NAME"),
            max_tokens=1024,
            temperature=0.3
        )
        problems = re.findall(r"-\s*(.+)", response_text)
        if problems:
            print(f"🧩 Öz-yansıma sonucu bulunan potansiyel problemler/iyileştirmeler: {problems}")
            return problems
        else:
            print(f"🧩 Öz-yansıma sonucu anlamlı bir problem/iyileştirme bulunamadı. Yanıt: {response_text}")
            return None
