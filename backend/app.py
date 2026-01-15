from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)

# Global timer state
timer_state = {
    'is_running': False,
    'is_paused': False,
    'current_mode': 'work',  # 'work', 'short_break', 'long_break'
    'remaining_seconds': 25 * 60,  # Default 25 minutes
    'start_time': None,
    'paused_remaining': None,
    'completed_pomodoros': 0,
    'settings': {
        'work_duration': 25 * 60,  # seconds
        'short_break': 5 * 60,  # seconds
        'long_break': 15 * 60,  # seconds
        'short_breaks_until_long': 4,  # number of short breaks before long break
        'auto_switch': False  # automatically start next phase when timer completes
    }
}

timer_lock = threading.Lock()

def update_timer():
    """Background thread to update timer"""
    while True:
        with timer_lock:
            if timer_state['is_running'] and not timer_state['is_paused']:
                if timer_state['remaining_seconds'] > 0:
                    timer_state['remaining_seconds'] -= 1
                else:
                    # Timer completed
                    timer_state['is_running'] = False
                    # Switch to next mode
                    if timer_state['current_mode'] == 'work':
                        timer_state['completed_pomodoros'] += 1
                        # Check if we need a long break
                        if timer_state['completed_pomodoros'] % timer_state['settings']['short_breaks_until_long'] == 0:
                            timer_state['current_mode'] = 'long_break'
                            timer_state['remaining_seconds'] = timer_state['settings']['long_break']
                        else:
                            timer_state['current_mode'] = 'short_break'
                            timer_state['remaining_seconds'] = timer_state['settings']['short_break']
                    elif timer_state['current_mode'] == 'short_break':
                        timer_state['current_mode'] = 'work'
                        timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
                    elif timer_state['current_mode'] == 'long_break':
                        timer_state['current_mode'] = 'work'
                        timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
                    
                    # Auto-switch: automatically start the next phase if enabled
                    if timer_state['settings'].get('auto_switch', False):
                        timer_state['is_running'] = True
                        timer_state['start_time'] = datetime.now().isoformat()
        time.sleep(1)

# Start timer update thread
timer_thread = threading.Thread(target=update_timer, daemon=True)
timer_thread.start()

@app.route('/', methods=['GET'])
def root():
    """Root endpoint - health check"""
    return jsonify({'status': 'ok', 'message': 'Pomodoro Timer API is running'})

@app.route('/api/timer/state', methods=['GET'])
def get_timer_state():
    """Get current timer state"""
    with timer_lock:
        return jsonify(timer_state)

@app.route('/api/timer/start', methods=['POST'])
def start_timer():
    """Start the timer"""
    with timer_lock:
        if timer_state['is_paused']:
            timer_state['is_paused'] = False
            if timer_state['paused_remaining']:
                timer_state['remaining_seconds'] = timer_state['paused_remaining']
                timer_state['paused_remaining'] = None
        else:
            # Set timer to current mode's duration
            if timer_state['current_mode'] == 'work':
                timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
            elif timer_state['current_mode'] == 'short_break':
                timer_state['remaining_seconds'] = timer_state['settings']['short_break']
            else:
                timer_state['remaining_seconds'] = timer_state['settings']['long_break']
        timer_state['is_running'] = True
        timer_state['start_time'] = datetime.now().isoformat()
    return jsonify(timer_state)

@app.route('/api/timer/pause', methods=['POST'])
def pause_timer():
    """Pause the timer"""
    with timer_lock:
        if timer_state['is_running'] and not timer_state['is_paused']:
            timer_state['is_paused'] = True
            timer_state['paused_remaining'] = timer_state['remaining_seconds']
    return jsonify(timer_state)

@app.route('/api/timer/skip', methods=['POST'])
def skip_timer():
    """Skip current timer and move to next"""
    with timer_lock:
        timer_state['is_running'] = False
        timer_state['is_paused'] = False
        
        # Switch to next mode
        if timer_state['current_mode'] == 'work':
            timer_state['completed_pomodoros'] += 1
            if timer_state['completed_pomodoros'] % timer_state['settings']['short_breaks_until_long'] == 0:
                timer_state['current_mode'] = 'long_break'
                timer_state['remaining_seconds'] = timer_state['settings']['long_break']
            else:
                timer_state['current_mode'] = 'short_break'
                timer_state['remaining_seconds'] = timer_state['settings']['short_break']
        elif timer_state['current_mode'] == 'short_break':
            timer_state['current_mode'] = 'work'
            timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
        elif timer_state['current_mode'] == 'long_break':
            timer_state['current_mode'] = 'work'
            timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
    return jsonify(timer_state)

@app.route('/api/timer/reset', methods=['POST'])
def reset_timer():
    """Reset timer to default"""
    with timer_lock:
        timer_state['is_running'] = False
        timer_state['is_paused'] = False
        timer_state['current_mode'] = 'work'
        timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
        timer_state['paused_remaining'] = None
    return jsonify(timer_state)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    with timer_lock:
        return jsonify(timer_state['settings'])

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update timer settings"""
    data = request.json
    with timer_lock:
        # Settings now come in as total seconds, not minutes
        if 'work_duration' in data:
            duration = int(data['work_duration'])
            timer_state['settings']['work_duration'] = duration if duration >= 0 else 1
        if 'short_break' in data:
            duration = int(data['short_break'])
            timer_state['settings']['short_break'] = duration if duration >= 0 else 1
        if 'long_break' in data:
            duration = int(data['long_break'])
            timer_state['settings']['long_break'] = duration if duration >= 0 else 1
        if 'short_breaks_until_long' in data:
            timer_state['settings']['short_breaks_until_long'] = int(data['short_breaks_until_long'])
        if 'auto_switch' in data:
            timer_state['settings']['auto_switch'] = bool(data['auto_switch'])
        if 'work_sound' in data:
            timer_state['settings']['work_sound'] = data['work_sound']
        if 'work_sound_file_name' in data:
            timer_state['settings']['work_sound_file_name'] = data['work_sound_file_name']
        if 'break_sound' in data:
            timer_state['settings']['break_sound'] = data['break_sound']
        if 'break_sound_file_name' in data:
            timer_state['settings']['break_sound_file_name'] = data['break_sound_file_name']
        if 'max_downtime_reminders' in data:
            timer_state['settings']['max_downtime_reminders'] = max(0, int(data['max_downtime_reminders']))
        
        # Update current timer if not running
        if not timer_state['is_running']:
            if timer_state['current_mode'] == 'work':
                timer_state['remaining_seconds'] = timer_state['settings']['work_duration']
            elif timer_state['current_mode'] == 'short_break':
                timer_state['remaining_seconds'] = timer_state['settings']['short_break']
            elif timer_state['current_mode'] == 'long_break':
                timer_state['remaining_seconds'] = timer_state['settings']['long_break']
    
    return jsonify(timer_state['settings'])

if __name__ == '__main__':
    app.run(debug=True, port=5001)

