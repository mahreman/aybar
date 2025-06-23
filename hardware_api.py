# hardware_api.py

from flask import Flask, request, jsonify
import pyautogui
import base64
from io import BytesIO

app = Flask(__name__)
pyautogui.FAILSAFE = False # Farenin ekran köşelerine giderek hata vermesini engeller

print("🦾 Donanım Kontrol API'si Başlatılıyor...")

@app.route('/mouse/click', methods=['POST'])
def click_mouse():
    data = request.json
    x, y = data.get('x'), data.get('y')
    double = data.get('double', False)
    
    if x is None or y is None:
        return jsonify({"status": "error", "message": "x ve y koordinatları gerekli."}), 400
        
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        if double:
            pyautogui.doubleClick()
        else:
            pyautogui.click()
        message = f"Başarıyla ({x}, {y}) konumuna tıklandı."
        print(f"API: {message}")
        return jsonify({"status": "success", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/keyboard/type', methods=['POST'])
def type_keyboard():
    data = request.json
    text = data.get('text', '')
    try:
        pyautogui.write(text, interval=0.05)
        message = f"'{text}' metni klavyeden yazıldı."
        print(f"API: {message}")
        return jsonify({"status": "success", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/screen/capture', methods=['GET'])
def capture_screen():
    try:
        from PIL import Image
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        print("API: Ekran görüntüsü alındı ve base64 olarak kodlandı.")
        return jsonify({"status": "success", "image_base64": img_str})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("✅ Donanım Kontrol API'si http://localhost:5151 adresinde çalışıyor.")
    app.run(host='0.0.0.0', port=5151)
