from flask import Flask, request, jsonify
import subprocess
import os
from werkzeug.utils import secure_filename
import traceback
from waitress import serve
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Enable logging
logging.basicConfig(level=logging.DEBUG)

app.config['UPLOAD_FOLDER'] = 'uploads'

# Make sure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/start-verification', methods=['POST'])
def start_verification():
    try:
        logging.debug("Request received for /start-verification")

        if 'file' not in request.files:
            logging.error('No file part in request')
            return jsonify({'message': 'No file uploaded'}), 400

        file = request.files['file']

        if file.filename == '':
            logging.error('No file selected')
            return jsonify({'message': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logging.debug(f"File saved to {filepath}")

        # Spawn the selenium script with filepath as argument
        logging.debug("Starting selenium script")
        process = subprocess.Popen(
            ['python', 'selenium_script.py', filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        logging.debug(f"Python output:\n{stdout}")
        logging.error(f"Python error:\n{stderr}")

        if process.returncode == 0:
            return jsonify({'message': 'PAN verification completed successfully.'})
        else:
            logging.error(f"Selenium script failed with error: {stderr}")
            return jsonify({'message': 'Python script failed.', 'error': stderr}), 500

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        traceback.print_exc()
        return jsonify({'message': f'Error occurred: {str(e)}'}), 500


if __name__ == "__main__":
    logging.debug("Starting the Flask app")
    serve(app, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
