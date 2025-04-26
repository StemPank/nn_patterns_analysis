from flask import Flask, render_template, request, jsonify
from db_pattern_detection_app import MainDatabase

app = Flask(__name__)
db = MainDatabase()

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/get_klines')
def get_klines():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    data = db.get_klines(symbol, interval)
    
    if not data:
        return jsonify([])
    
    # print("Fetched rows:", data)

    return jsonify([
        {
            'time': row[0],
            'open': row[1],
            'high': row[2],
            'low': row[3],
            'close': row[4]
        }
        for row in data
    ])

@app.route('/submit_pattern', methods=['POST'])
def submit_pattern():
    data = request.json
    print(data)
    db.insert_pattern(
        symbol=data['symbol'],
        interval=data['interval'],
        pattern_type=data['pattern_type'],
        start_time=int(data['start_time']),
        end_time=int(data['end_time']),
        label_by='manual'
    )
    return jsonify({'status': 'ok'})

@app.route('/get_patterns')
def get_patterns():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    # Получаем паттерны из базы данных
    patterns = db.get_patterns(symbol, interval)
    # Возвращаем паттерны в формате JSON
    return jsonify(patterns)
