from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import yt_dlp
import whisper
import os
import tempfile
import shutil
import uuid
from werkzeug.utils import secure_filename
import threading
import time
from werkzeug.exceptions import RequestTimeout

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 650 * 1024 * 1024  # 650MB max upload
app.config['UPLOAD_TIMEOUT'] = 300  # 5 minutes timeout for uploads
app.secret_key = os.urandom(24)

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Storage for transcriptions and progress
transcription_storage = {}
progress_storage = {}

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 650MB'}), 413

@app.errorhandler(RequestTimeout)
def handle_timeout_error(error):
    return jsonify({'error': 'Request timed out. Please try again with a smaller file or use the YouTube URL option'}), 408

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({'error': str(error)}), 500

def update_progress(task_id, progress, status):
    progress_storage[task_id] = {
        'progress': progress,
        'status': status,
        'error': None
    }

def process_file_with_progress(file_path, task_id, video_title):
    try:
        update_progress(task_id, 10, 'Loading Whisper model...')
        model = whisper.load_model("base")
        
        update_progress(task_id, 30, 'Starting transcription...')
        result = model.transcribe(file_path)
        transcription = result["text"]
        
        update_progress(task_id, 70, 'Formatting notes...')
        # Format as Jupiter Notes
        paragraphs = transcription.split(". ")
        notes = ""
        for i, para in enumerate(paragraphs):
            if para.strip():
                if i < len(paragraphs) - 1:
                    para += "."
                notes += f"• {para.strip()}\n\n"
        
        update_progress(task_id, 90, 'Saving results...')
        # Store results
        transcription_storage[task_id] = {
            'transcription': transcription,
            'notes': notes,
            'video_title': video_title
        }
        
        update_progress(task_id, 100, 'Complete!')
        with app.app_context():
            progress_storage[task_id]['redirect_url'] = url_for('show_results', task_id=task_id)
        
    except Exception as e:
        progress_storage[task_id]['error'] = str(e)
        progress_storage[task_id]['progress'] = 100

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_youtube', methods=['POST'])
def process_youtube():
    youtube_url = request.form['youtube_url']
    if not youtube_url:
        return jsonify({'error': 'Please enter a YouTube URL'})
    
    try:
        task_id = str(uuid.uuid4())
        update_progress(task_id, 0, 'Starting YouTube download...')
        
        def process():
            with app.app_context():
                try:
                    temp_dir = tempfile.mkdtemp()
                    
                    update_progress(task_id, 20, 'Downloading YouTube audio...')
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(youtube_url, download=True)
                        video_title = info.get('title', 'Unknown Title')
                        downloaded_file = ydl.prepare_filename(info)
                    
                    update_progress(task_id, 40, 'Processing audio...')
                    process_file_with_progress(downloaded_file, task_id, video_title)
                    
                    # Clean up
                    shutil.rmtree(temp_dir)
                    
                except Exception as e:
                    progress_storage[task_id]['error'] = str(e)
                    progress_storage[task_id]['progress'] = 100
        
        thread = threading.Thread(target=process)
        thread.start()
        
        return jsonify({'task_id': task_id})
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/process_upload', methods=['POST'])
def process_upload():
    if 'video_file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['video_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    try:
        task_id = str(uuid.uuid4())
        update_progress(task_id, 0, 'Starting upload...')
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        def process():
            with app.app_context():
                try:
                    update_progress(task_id, 20, 'Processing uploaded file...')
                    process_file_with_progress(filepath, task_id, filename)
                    
                    # Clean up
                    os.remove(filepath)
                    
                except Exception as e:
                    progress_storage[task_id]['error'] = str(e)
                    progress_storage[task_id]['progress'] = 100
        
        thread = threading.Thread(target=process)
        thread.start()
        
        return jsonify({'task_id': task_id})
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    if task_id not in progress_storage:
        return jsonify({'error': 'Task not found'})
    return jsonify(progress_storage[task_id])

@app.route('/results/<task_id>')
def show_results(task_id):
    if task_id not in transcription_storage:
        return "Transcription not found", 404
    
    data = transcription_storage[task_id]
    return render_template('results.html',
                         video_title=data['video_title'],
                         transcription=data['transcription'],
                         notes=data['notes'],
                         trans_id=task_id)

@app.route('/download_notes/<trans_id>')
def download_notes(trans_id):
    if trans_id not in transcription_storage:
        return "Transcription not found", 404
    
    data = transcription_storage[trans_id]
    video_title = data['video_title']
    notes = data['notes']
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.md')
    with open(temp_file.name, 'w', encoding='utf-8') as f:
        f.write(f"# Jupiter Notes: {video_title}\n\n{notes}")
    
    return_file = send_file(temp_file.name,
                         as_attachment=True,
                         download_name=f"jupiter_notes_{video_title.replace(' ', '_')}.md")
    
    # Schedule file for deletion after it's sent
    os.unlink(temp_file.name)
    
    # Clean up storage after some time
    def cleanup():
        time.sleep(300)  # Wait 5 minutes
        if trans_id in transcription_storage:
            del transcription_storage[trans_id]
        if trans_id in progress_storage:
            del progress_storage[trans_id]
    
    cleanup_thread = threading.Thread(target=cleanup)
    cleanup_thread.start()
    
    return return_file

if __name__ == "__main__":
    app.run(debug=True)