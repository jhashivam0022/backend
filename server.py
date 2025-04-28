from flask import Flask, request, jsonify
import subprocess
import os
from werkzeug.utils import secure_filename
import traceback
from waitress import serve
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 
app.config['UPLOAD_FOLDER'] = 'uploads'

# Make sure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/start-verification', methods=['POST'])
def start_verification():
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No file uploaded'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Spawn the selenium script with filepath as argument
        process = subprocess.Popen(
            ['python', 'selenium_script.py', filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        print(f"Python output:\n{stdout}")
        print(f"Python error:\n{stderr}")

        if process.returncode == 0:
            return jsonify({'message': 'PAN verification completed successfully.'})
        else:
            return jsonify({'message': 'Python script failed.', 'error': stderr}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({'message': f'Error occurred: {str(e)}'}), 500



if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

