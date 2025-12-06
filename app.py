import os
import socket
import qrcode
import threading
import time
# Import render_template, NOT render_template_string
from flask import Flask, request, redirect, url_for, send_from_directory, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename

app = Flask(__name__)
auth = HTTPBasicAuth()

# --- CONFIGURATION ---
# (This part is all the same)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'shared_files')
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024
users = {"admin": "admin"}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

def get_local_ip():
    # (This function is the same)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# --- ROUTES ---
@app.route('/')
def index():
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    # --- THIS IS THE KEY CHANGE ---
    # It now reads from 'templates/index.html'
    return render_template("index.html", files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    if file.filename == '': return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('index'))

@app.route('/save_snippet', methods=['POST'])
def save_snippet():
    snippet_name = request.form.get('snippet_name', 'snippet')
    snippet_content = request.form.get('snippet_content', '')
    filename = secure_filename(f"{snippet_name}.txt")
    try:
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w', encoding='utf-8') as f:
            f.write(snippet_content)
    except Exception as e:
        print(f"!!! ERROR SAVING SNIPPET: {e}")
    return redirect(url_for('index'))

@app.route('/get_text/<path:filename>')
def get_text(filename):
    if not filename.endswith('.txt'):
        return jsonify({"error": "Invalid file type"}), 400
    safe_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if not os.path.isfile(safe_path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": f"Error reading file: {e}"}), 500

# --- NEW ROUTE FOR VIEWING MEDIA ---
@app.route('/view_file/<path:filename>')
def view_file(filename):
    """
    Serves a file for inline viewing (not as an attachment).
    The browser will try to display it if it can (image, video, pdf).
    """
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    if not os.path.isfile(file_path):
        return "File not found", 404
        
    # By default, send_from_directory serves files inline.
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename)

@app.route('/download/<path:filename>')
def download_file(filename):
    # This route specifically forces a download prompt.
    return send_from_directory(app.config['UPLOAD_FOLDER'], secure_filename(filename), as_attachment=True)

@app.route('/delete/<path:filename>')
@auth.login_required
def delete_file(filename):
    safe_filename = secure_filename(filename)
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        os.remove(full_path)
    return redirect(url_for('index'))

@app.route('/shutdown')
@auth.login_required
def shutdown():
    def kill():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=kill).start()
    return "Server is shutting down..."


# (The rest of the script: generate_qr and if __name__ == '__main__' remains the same)
def generate_qr(ip, port):
    try:
        url = f"http://{ip}:{port}"
        img = qrcode.make(url)
        qr_path = os.path.join(BASE_DIR, "connect_qr.png")
        img.save(qr_path)
        os.startfile(qr_path)
    except Exception: pass

if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    print(f"\n✅ Server running at: http://{local_ip}:{port}")
    print("🔑 Admin Username: admin")
    print("🔑 Admin Password: admin")
    threading.Thread(target=generate_qr, args=(local_ip, port)).start()
    app.run(host='0.0.0.0', port=port, debug=False)