# vision_sensor.py - Nihai ve Düzeltilmiş Kod

import cv2
import time
import json
import numpy as np # <-- EKSİK OLAN SATIR EKLENDİ

def detect_motion(frame1, frame2):
    """İki kare arasındaki farkı analiz ederek hareketi tespit eden basit bir fonksiyon."""
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=3)
    # Hareketin "anlamlı" kabul edilmesi için eşik değeri
    return np.sum(dilated) > 1000 

print("👁️  Görsel Algı Sensörü Başlatılıyor...")
try:
    cap = cv2.VideoCapture(0) # 0, varsayılan web kamerasını temsil eder
    if not cap.isOpened():
        raise IOError("Web kamerası açılamadı.")

    print("✅ Kamera bulundu ve aktif. Hareket algılama döngüsü başlıyor...")
    # İlk kareyi referans olarak al
    ret, frame1 = cap.read()
    if not ret:
        print("❌ Kameradan ilk kare okunamadı.")
        cap.release()
        exit()
    
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    time.sleep(1)

    while True:
        ret, frame2 = cap.read()
        if not ret:
            break

        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Hareketi analiz et
        motion_detected = detect_motion(gray1, gray2)
        
        # Algı sonucunu paylaşılan bir dosyaya yaz
        perception = {
            "timestamp": time.time(),
            "type": "visual",
            "status": "MOTION_DETECTED" if motion_detected else "STATIC_ENVIRONMENT",
            "description": "Kamera görüş alanında bir hareket algılandı." if motion_detected else "Ortam sakin ve hareketsiz."
        }
        try:
            with open("vision_perception.json", "w") as f:
                json.dump(perception, f)
        except Exception as e:
            print(f"HATA: Algı dosyasına yazılamadı: {e}")
            
        # Bir sonraki döngü için referans kareyi güncelle
        gray1 = gray2
        time.sleep(2) # Her 2 saniyede bir kontrol et

except (IOError, ImportError) as e:
    print(f"❌ Görsel sensör hatası: {e}. 'opencv-python' kütüphanesinin kurulu olduğundan emin olun.")
finally:
    if 'cap' in locals() and cap.isOpened():
        cap.release()
