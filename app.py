import os
import shutil
import logging
from flask import Flask, request, jsonify, Response, render_template_string
import urllib.parse

import yt_dlp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

DOWNLOAD_FOLDER = 'temp_downloads'

if os.path.exists(DOWNLOAD_FOLDER):
    logging.info(f"Removing existing download folder: {DOWNLOAD_FOLDER}")
    shutil.rmtree(DOWNLOAD_FOLDER)
logging.info(f"Creating download folder: {DOWNLOAD_FOLDER}")
os.makedirs(DOWNLOAD_FOLDER)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .loader {
            border: 5px solid #4A5568;
            border-top: 5px solid #4299E1;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen p-4">
    <div class="container mx-auto p-6 md:p-8 max-w-2xl bg-gray-800 rounded-2xl shadow-2xl w-full">
        <h1 class="text-3xl md:text-4xl font-bold text-center mb-6 text-white">Video Downloader</h1>
        <p class="text-center text-gray-400 mb-8">Paste a video link to fetch download options.</p>

        <div class="flex flex-col sm:flex-row gap-4 mb-8">
            <input type="text" id="videoUrl" placeholder="Paste video URL here..." class="flex-grow bg-gray-700 text-white border-2 border-gray-600 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
            <button id="fetchBtn" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 flex items-center justify-center">
                Fetch Video
            </button>
        </div>

        <div id="loader" class="hidden flex justify-center items-center my-8">
            <div class="loader"></div>
        </div>

        <div id="results" class="hidden bg-gray-700 p-6 rounded-lg">
            <div class="flex flex-col md:flex-row gap-6">
                <img id="thumbnail" src="" alt="Video Thumbnail" class="w-full md:w-1/3 rounded-lg shadow-md object-cover">
                <div class="flex-grow">
                    <h2 id="videoTitle" class="text-xl font-semibold mb-4 text-white"></h2>
                    <div id="formats" class="space-y-3">
                    </div>
                </div>
            </div>
        </div>
        
        <div id="error" class="hidden text-red-400 text-center mt-4 p-3 bg-red-900/50 rounded-lg"></div>
    </div>

<script>
    const fetchBtn = document.getElementById('fetchBtn');
    const urlInput = document.getElementById('videoUrl');
    const resultsDiv = document.getElementById('results');
    const loader = document.getElementById('loader');
    const errorDiv = document.getElementById('error');
    
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchBtn.click();
        }
    });

    fetchBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showError("Please enter a video URL.");
            return;
        }

        resultsDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        loader.classList.remove('hidden');
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '<div class="loader" style="width: 20px; height: 20px; border-width: 3px;"></div>';

        try {
            const response = await fetch('/get_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch video information.');
            }
            displayResults(data);

        } catch (err) {
            showError(err.message);
        } finally {
            loader.classList.add('hidden');
            fetchBtn.disabled = false;
            fetchBtn.textContent = 'Fetch Video';
        }
    });

    function displayResults(data) {
        document.getElementById('thumbnail').src = data.thumbnail;
        document.getElementById('videoTitle').textContent = data.title;
        
        const formatsDiv = document.getElementById('formats');
        formatsDiv.innerHTML = '';

        if (data.formats.length === 0) {
            formatsDiv.innerHTML = '<p class="text-gray-400">No suitable MP4 download formats (720p or higher) found.</p>';
        } else {
            data.formats.forEach(format => {
                const fileSize = format.filesize ? `(${(format.filesize / 1024 / 1024).toFixed(2)} MB)` : '';
                const link = document.createElement('a');
                link.href = `/download?url=${encodeURIComponent(data.original_url)}&format_id=${format.format_id}`;
                link.className = 'block bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg text-center transition duration-300';
                link.textContent = `Download ${format.resolution} ${fileSize}`;
                formatsDiv.appendChild(link);
            });
        }
        resultsDiv.classList.remove('hidden');
    }

    function showError(message) {
        errorDiv.textContent = 'Error: ' + message;
        errorDiv.classList.remove('hidden');
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    logging.info(f"Fetching info for URL: {url}")
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats_to_send = []
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                    resolution_str = f.get('resolution')

                    if resolution_str == 'none' or not resolution_str:
                        if f.get('height'):
                            resolution_str = f'{f.get("height")}p'
                        else:
                            continue
                    
                    try:
                        # Extract numerical height for filtering
                        height = int(resolution_str.split('x')[-1].replace('p',''))
                    except ValueError:
                        continue # Skip if resolution string cannot be parsed

                    # --- NEW FILTER: Only include resolutions 720p or higher ---
                    if height >= 720: # Filter out anything below 720p
                        formats_to_send.append({
                            'format_id': f['format_id'],
                            'resolution': resolution_str,
                            'filesize': f.get('filesize') or f.get('filesize_approx'),
                        })
                    # --- END NEW FILTER ---

            # Sort formats by height (resolution) in descending order to show HD first
            sorted_formats = sorted(formats_to_send, 
                                    key=lambda x: int(x['resolution'].split('x')[-1].replace('p','')) if x['resolution'] else 0,
                                    reverse=True)
            
            response_data = {
                'title': info.get('title', 'No title'),
                'thumbnail': info.get('thumbnail', ''),
                'formats': sorted_formats,
                'original_url': url,
            }
            logging.info(f"Found {len(sorted_formats)} formats for '{info.get('title')}'.")
            return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error fetching info: {e}")
        return jsonify({'error': 'Could not process this URL. It may be private, geo-restricted, or invalid.'}), 500

@app.route('/download')
def download():
    url = request.args.get('url')
    format_id = request.args.get('format_id')

    if not url or not format_id:
        return "Missing URL or format ID", 400
    
    logging.info(f"Starting download for format '{format_id}' from URL: {url}")

    def progress_hook(d):
        if d['status'] == 'finished':
            logging.info(f"yt-dlp has finished downloading.")
        if d['status'] == 'downloading':
            pass


    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'progress_hooks': [progress_hook],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base, _ = os.path.splitext(ydl.prepare_filename(info))
            downloaded_path = base + '.mp4'

        if not os.path.exists(downloaded_path):
            raise FileNotFoundError(f"File not found after download and merge attempt: {downloaded_path}")
        
        logging.info(f"File successfully prepared at: {downloaded_path}")

        def generate():
            try:
                with open(downloaded_path, 'rb') as f:
                    yield from f
                logging.info(f"Finished streaming {downloaded_path} to client.")
            finally:
                try:
                    os.remove(downloaded_path)
                    logging.info(f"Successfully cleaned up and removed {downloaded_path}.")
                except OSError as e:
                    logging.error(f"Error deleting file {downloaded_path}: {e}")

        res = Response(generate(), mimetype='video/mp4')
        
        original_filename = os.path.basename(downloaded_path)
        encoded_filename = urllib.parse.quote(original_filename.encode('utf-8'))
        
        res.headers.set(
            "Content-Disposition", 
            f"attachment; filename*=UTF-8''{encoded_filename}"
        )

        return res

    except Exception as e:
        logging.error(f"Download process failed: {e}")
        return f"An error occurred during the download process: {str(e)}", 500


if __name__ == '__main__':
   # Use environment variable for PORT, default to 8080 or 5000 for local
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)