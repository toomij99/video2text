# 🪐 Jupiter Notes

Jupiter Notes is a web application that automatically transcribes videos and audio files (both YouTube content and uploaded files) and generates structured notes from the transcription. It uses OpenAI's Whisper model for accurate speech-to-text conversion and provides an easy way to download the generated notes in Markdown format.

## Features

- 🎥 YouTube video transcription support
- 📤 Local video file upload support
- 🤖 Automatic transcription using OpenAI's Whisper model
- 📝 Structured note generation
- ⬇️ Download notes in Markdown format
- 🎨 Clean and intuitive user interface

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.7 or higher
- FFmpeg (required for audio processing)
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd jupiter-notes
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Choose one of two options:
   - Enter a YouTube URL
   - Upload a video file

4. Wait for the transcription process to complete
5. Review the generated transcription and notes
6. Download the notes in Markdown format

## Technical Details

- **Maximum Upload Size**: 650MB
- **Supported Formats**: 
  - Video: MP4, AVI, MOV, MKV
  - Audio: MP3, WAV, M4A
- **Output Format**: Markdown (.md)
- **Transcription Model**: OpenAI Whisper (base model)

## Project Structure

```
jupiter-notes/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── uploads/           # Temporary storage for uploaded files
└── templates/         # HTML templates
    ├── index.html    # Home page template
    └── results.html  # Results page template
```

## Dependencies

- Flask: Web framework
- yt-dlp: YouTube video download
- OpenAI Whisper: Speech-to-text transcription
- FFmpeg: Audio processing

## Error Handling

The application includes error handling for:
- Invalid YouTube URLs
- Failed video downloads
- Unsupported file formats
- File size limits
- Transcription failures

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for the Whisper model
- yt-dlp for YouTube video processing
- Flask team for the web framework 