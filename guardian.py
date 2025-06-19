# guardian.py - Nihai Orkestra Şefi Versiyonu

import subprocess
import sys
import time
import os
import shutil
import datetime
import json

# Yönetilecek ana betiğin adı
MAIN_SCRIPT = "aybar_core6.py"
# Arka planda çalışacak servislerin adları
HARDWARE_API_SCRIPT = "hardware_api.py"
VISION_SENSOR_SCRIPT = "vision_sensor.py"

def backup_script(source_path):
    """Ana betiğin yedeğini alır."""
    backup_path = f"{source_path}.bak"
    try:
        shutil.copy(source_path, backup_path)
        print(f"🛡️  Güvenlik yedeği oluşturuldu: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Yedekleme hatası: {e}")
        return None

def rollback_from_backup(source_path, backup_path):
    """Bozuk betiği yedekten geri yükler ve bir log dosyası oluşturur."""
    try:
        print(f"⟲ Geri yükleme başlatıldı... '{backup_path}' dosyası kullanılıyor.")
        shutil.copy(backup_path, source_path)
        print("✅ Geri yükleme başarılı.")
        
        with open("guardian_log.txt", "w", encoding="utf-8") as f:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "event": "CRITICAL_FAILURE_AND_ROLLBACK",
                "restored_from": backup_path
            }
            json.dump(log_data, f)
        print("📝 Geri yükleme logu oluşturuldu: guardian_log.txt")
        
        return True
    except Exception as e:
        print(f"❌ Geri yükleme hatası: {e}")
        return False

def start_process(script_path):
    """Belirtilen betiği bir alt süreç olarak başlatır."""
    process_env = os.environ.copy()
    process_env["PYTHONIOENCODING"] = "utf-8"
    # stderr=subprocess.PIPE, hataları ayrı yakalamak için
    return subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, 
        text=True,
        encoding='utf-8',
        errors='replace', # Hatalı karakterleri değiştir
        env=process_env
    )

def read_output(pipe, prefix):
    """Bir sürecin çıktısını okur ve ekrana basar."""
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line}", end='')
    pipe.close()


if __name__ == "__main__":
    background_processes = []
    
    try:
        # Adım 1: Arka plan servislerini başlat
        if os.path.exists(HARDWARE_API_SCRIPT):
            print(f"🦾 Donanım API'si başlatılıyor...")
            api_process = start_process(HARDWARE_API_SCRIPT)
            background_processes.append(api_process)
        
        if os.path.exists(VISION_SENSOR_SCRIPT):
            print(f"👁️  Görsel Sensör başlatılıyor...")
            vision_process = start_process(VISION_SENSOR_SCRIPT)
            background_processes.append(vision_process)

        time.sleep(4) # Servislerin tam olarak başlaması için kısa bir bekleme
        print("-" * 50)

        # Adım 2: Ana Aybar sürecini izleme döngüsü
        current_script = MAIN_SCRIPT
        while True:
            aybar_process = start_process(current_script)

            while aybar_process.poll() is None:
                line = aybar_process.stdout.readline()
                if not line:
                    break
                print(line, end='')

                if line.strip().startswith("GUARDIAN_REQUEST: EVOLVE_TO"):
                    new_script_path = line.split("GUARDIAN_REQUEST: EVOLVE_TO")[1].strip()
                    print(f"💫 Gözetmen evrim talebi aldı. Yeni versiyon: {new_script_path}")
                    
                    backup = backup_script(current_script)
                    if os.path.exists(new_script_path):
                        # Önce eski betiği sil, sonra yenisini taşı
                        if os.path.exists(current_script):
                            os.remove(current_script)
                        shutil.move(new_script_path, current_script)
                        print(f"✅ Yeni versiyon '{current_script}' olarak atandı. Aybar yeniden başlatılıyor...")
                    
                    aybar_process.kill() 
                    break

            if aybar_process.returncode != 0:
                print(f"❌ Aybar beklenmedik bir şekilde sonlandı (Çıkış Kodu: {aybar_process.returncode}).")
                # Hata çıktısını oku ve göster
                stderr_output = aybar_process.stderr.read()
                print(f"HATA ÇIKTISI:\n{stderr_output}")

                backup_file = f"{current_script}.bak"
                if os.path.exists(backup_file):
                    if rollback_from_backup(current_script, backup_file):
                        print("🔄 Sistem son stabil yedekten yeniden başlatılacak.")
                    else:
                        print("KRİTİK HATA: Geri yükleme başarısız. Manuel müdahale gerekiyor.")
                        sys.exit(1)
                else:
                    print("UYARI: Yedek bulunamadı, son haliyle yeniden başlatılıyor.")

            print("-" * 20 + " YENİDEN BAŞLATILIYOR " + "-" * 20)
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n🚫 Gözetmen ve tüm alt süreçler kullanıcı tarafından durduruluyor...")
    
    finally:
        print("🧹 Arka plan servisleri temizleniyor...")
        for p in background_processes:
            p.terminate() # Nazikçe sonlandırmayı dene
        if 'aybar_process' in locals() and aybar_process.poll() is None:
            aybar_process.terminate()
        
        # Süreçlerin sonlandığından emin ol
        time.sleep(1)
        for p in background_processes:
            if p.poll() is None:
                p.kill() # Gerekirse zorla sonlandır
        
        print("Tüm süreçler sonlandırıldı. Çıkış yapılıyor.")
