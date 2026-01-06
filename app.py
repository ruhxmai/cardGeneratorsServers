import os
import io
import zipfile
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
CANVAS_WIDTH = 1000 
CANVAS_HEIGHT = 1428

# Новые коэффициенты сдвига (относительно изначального конфига)
OFFSET_GEN = 6  # Общий сдвиг вверх для всех полей (4 + 2)
OFFSET_DT  = 8  # Сдвиг вверх для даты и времени (4 + 4)

CONFIG = {
    'kid': {
        'bg': 'kid.png',
        'invite':    {'x': 670, 'y': 479 - OFFSET_GEN, 'size': 40, 'align': 'center'},
        'address':   {'x': 560, 'y': 725 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':      {'x': 280, 'y': 844 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':      {'x': 480, 'y': 903 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'eventName': {'x': 500, 'y': 1058 - OFFSET_GEN, 'size': 36, 'align': 'center'}
    },
    'adult': {
        'bg': 'adult.png',
        'invite':    {'x':  670, 'y': 483 - OFFSET_GEN, 'size': 40, 'align': 'center'},
        'address':   {'x': 567, 'y': 735 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':      {'x': 282, 'y': 853 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':      {'x': 475, 'y': 912 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'eventName': {'x': 500, 'y': 1076 - OFFSET_GEN, 'size': 36, 'align': 'center'}
    },
    'school': {
        'bg': 'school.png',
        'invite':  {'x': 500, 'y': 530 - OFFSET_GEN, 'size': 35, 'align': 'center'},
        'field1':  {'x': 400, 'y': 595 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'field2':  {'x': 818, 'y': 590 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'address': {'x': 567, 'y': 806 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':    {'x': 280, 'y': 924 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':    {'x': 470, 'y': 983 - OFFSET_DT,  'size': 34, 'align': 'left'}
    },
    'kindergarten': {
        'bg': 'kindergarten.png',
        'invite':  {'x': 500, 'y': 530 - OFFSET_GEN, 'size': 35, 'align': 'center'},
        'field1':  {'x': 765, 'y': 593 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'field2':  {'x': 315, 'y': 655 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'address': {'x': 575, 'y': 825 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':    {'x': 280, 'y': 946 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':    {'x': 470, 'y': 1006 - OFFSET_DT,  'size': 34, 'align': 'left'}
    },
    'trip': {
        'bg': 'trip.png',
        'invite':  {'x': 500, 'y': 529 - OFFSET_GEN, 'size': 35, 'align': 'center'},
        'field1':  {'x': 402, 'y': 595 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'field2':  {'x': 800, 'y': 594 - OFFSET_GEN, 'size': 28, 'align': 'center'},
        'address': {'x': 567, 'y': 830 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':    {'x': 281, 'y': 947 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':    {'x': 471, 'y': 1006 - OFFSET_DT,  'size': 34, 'align': 'left'}
    },
    'corporate': {
        'bg': 'corporate.png',
        'invite':    {'x': 501, 'y': 476 - OFFSET_GEN, 'size': 40, 'align': 'center'},
        'address':   {'x': 570, 'y': 795 - OFFSET_GEN, 'size': 30, 'align': 'left'},
        'date':      {'x': 280, 'y': 914 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'time':      {'x': 472, 'y': 973 - OFFSET_DT,  'size': 34, 'align': 'left'},
        'eventName': {'x': 501, 'y': 606 - OFFSET_GEN, 'size': 38, 'align': 'center'}
    }
}

MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

def format_date_ru(date_str):
    if not date_str: return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year} г."
    except: return date_str

def draw_text(draw, text, cfg, font_path):
    if not text or not cfg: return
    font = ImageFont.truetype(font_path, cfg.get('size', 30))
    x, y = cfg['x'], cfg['y']
    if cfg.get('align') == 'center':
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = x - (w / 2)
    draw.text((x, y), text, font=font, fill=(0, 0, 0))

def draw_text_wrapped(draw, text, cfg, font_path, max_width=800, indent_x=130):
    if not text or not cfg: return
    font = ImageFont.truetype(font_path, 30) 
    line_height = 58 
    words = text.split(' ')
    lines = []
    current_line = ""
    is_first_line = True
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        current_max_width = (max_width - (cfg['x'] - indent_x)) if is_first_line else max_width
        if w > current_max_width and current_line:
            lines.append(current_line.strip())
            current_line = word + " "
            is_first_line = False
        else:
            current_line = test_line
    if current_line: lines.append(current_line.strip())
    y_cursor, x_cursor = cfg['y'], cfg['x']
    for line in lines:
        draw.text((x_cursor, y_cursor), line, font=font, fill=(0, 0, 0))
        y_cursor += line_height
        x_cursor = indent_x

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        t_type = data.get('type', 'kid')
        names = data.get('names', [])
        cfg = CONFIG.get(t_type, CONFIG['kid'])
        bg_path = os.path.join(BASE_DIR, cfg['bg'])
        font_path = os.path.join(BASE_DIR, "font", "Olympia Deco.ttf")

        if not os.path.exists(bg_path):
            return jsonify({"error": "Background file not found"}), 500

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for name in names:
                img = Image.open(bg_path).convert("RGB")
                img = img.resize((CANVAS_WIDTH, CANVAS_HEIGHT))
                draw = ImageDraw.Draw(img)

                draw_text(draw, name, cfg.get('invite'), font_path)
                draw_text_wrapped(draw, data.get('address', ''), cfg.get('address'), font_path)
                draw_text(draw, format_date_ru(data.get('date', '')), cfg.get('date'), font_path)
                draw_text(draw, data.get('time', ''), cfg.get('time'), font_path)
                draw_text(draw, data.get('input1', ''), cfg.get('field1'), font_path)
                draw_text(draw, data.get('input2', ''), cfg.get('field2'), font_path)
                draw_text(draw, data.get('eventName', ''), cfg.get('eventName'), font_path)

                pdf_buf = io.BytesIO()
                img.save(pdf_buf, format='PDF', quality=95)
                safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
                zf.writestr(f"Приглашение_{safe_name}.pdf", pdf_buf.getvalue())

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='invites_fort_boyard.zip')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)