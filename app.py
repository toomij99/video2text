from flask import Flask, render_template, request, redirect, url_for, send_file, session
import yt_dlp
import whisper
import os
import tempfile
import shutil
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 650 * 1024 * 1024  # 500MB max upload
app.secret_key = os.urandom(24)  # Required for session

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Temporary storage for transcriptions
transcription_storage = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_youtube', methods=['POST'])
def process_youtube():
    youtube_url = request.form['youtube_url']
    if not youtube_url:
        return render_template('index.html', error="Please enter a YouTube URL")
    
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Download the YouTube video audio using yt-dlp
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
        
        # Transcribe the video
        transcription, notes = transcribe_video(downloaded_file, video_title)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        # Store transcription data with a unique ID
        trans_id = str(uuid.uuid4())
        transcription_storage[trans_id] = {
            'transcription': transcription,
            'notes': notes,
            'video_title': video_title
        }
        
        return render_template('results.html', 
                             video_title=video_title,
                             transcription=transcription,
                             notes=notes,
                             trans_id=trans_id)
    
    except Exception as e:
        return render_template('index.html', error=f"Error processing YouTube video: {str(e)}")

@app.route('/process_upload', methods=['POST'])
def process_upload():
    if 'video_file' not in request.files:
        return render_template('index.html', error="No file part")
    
    file = request.files['video_file']
    
    if file.filename == '':
        return render_template('index.html', error="No selected file")
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Transcribe the video
        transcription, notes = transcribe_video(filepath, filename)
        
        # Clean up
        os.remove(filepath)
        
        # Store transcription data with a unique ID
        trans_id = str(uuid.uuid4())
        transcription_storage[trans_id] = {
            'transcription': transcription,
            'notes': notes,
            'video_title': filename
        }
        
        return render_template('results.html', 
                             video_title=filename,
                             transcription=transcription,
                             notes=notes,
                             trans_id=trans_id)
    
    except Exception as e:
        return render_template('index.html', error=f"Error processing uploaded video: {str(e)}")

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
    
    # Clean up storage
    del transcription_storage[trans_id]
    
    return return_file

def transcribe_video(video_path, video_title):
    """Transcribe the video and format notes"""
    # Load Whisper model
    model = whisper.load_model("base")
    
    # Transcribe
    result = model.transcribe(video_path)
    transcription = result["text"]
    
    # Format as Jupiter Notes
    paragraphs = transcription.split(". ")
    notes = ""
    
    for i, para in enumerate(paragraphs):
        if para.strip():
            # Add period back if it's not the last paragraph
            if i < len(paragraphs) - 1:
                para += "."
            notes += f"• {para.strip()}\n\n"
    
    return transcription, notes

if __name__ == "__main__":
    app.run(debug=True)