from flask import Flask, request, render_template
import paho.mqtt.publish as publish
import base64
from PIL import Image, ImageOps
import io
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 


MQTT_BROKER = "test.mosquitto.org"
TOPIC_TEXT = "ahwuesp32/string12345"
TOPIC_IMAGE = "ahwuesp32/display/image12345"
MAX_B64_LEN = 7000  # Base64 字串最大長度限制（對應約 5.2~5.5 KB 圖片）

def compress_to_fit_size(img, max_b64_len=MAX_B64_LEN):
    """將圖片儲存為 baseline JPEG，並自動調整 quality 直到符合 base64 長度限制"""
    quality = 90
    while quality >= 20:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True, progressive=False)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode('ascii')
        b64_cleaned = b64.replace('\n', '').replace('\r', '').replace(' ', '')
        if len(b64_cleaned) <= max_b64_len:
            return b64_cleaned, quality
        quality -= 5
    raise ValueError("無法壓縮圖片至符合 base64 限制")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_message():
    msg = request.form.get("msg")
    file = request.files.get("image")

    if msg:
        publish.single(TOPIC_TEXT, msg, hostname=MQTT_BROKER)

    if file and file.filename:
        try:
            img = Image.open(file).convert("RGB")
            img = ImageOps.invert(img)
            img = img.resize((128, 160))

            b64_cleaned, final_quality = compress_to_fit_size(img, MAX_B64_LEN)

            publish.single(TOPIC_IMAGE, b64_cleaned, hostname=MQTT_BROKER)

            return f'''
                <p>✅ 圖片已送出</p>
                <ul>
                    <li>壓縮品質：{final_quality}</li>
                    <li>Base64 長度：{len(b64_cleaned)} bytes</li>
                </ul>
                <a href="/"><button>回到表單</button></a>
            '''
        except Exception as e:
            return f"<p>❌ 圖片處理失敗: {e}</p>"

    return '''
        <p>✅ 訊息已送出（若有）</p>
        <a href="/"><button>回到表單</button></a>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
