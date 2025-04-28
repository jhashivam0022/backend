from flask import Flask, request, jsonify
import subprocess
import os
from werkzeug.utils import secure_filename
import traceback
from waitress import serve
from flask_cors import CORS
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

        # Call the function to run the selenium verification
        logging.debug("Starting selenium script")
        result = run_selenium_script(filepath)

        if result['success']:
            return jsonify({'message': 'PAN verification completed successfully.'})
        else:
            logging.error(f"Selenium script failed with error: {result['error']}")
            return jsonify({'message': 'Python script failed.', 'error': result['error']}), 500

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        traceback.print_exc()
        return jsonify({'message': f'Error occurred: {str(e)}'}), 500


def run_selenium_script(file_path):
    try:
        # Read the CSV with no header
        df = pd.read_csv(file_path, header=None)

        # Extract credentials from the DataFrame
        user_id = df.iloc[1, 3]  # D2 (user ID)
        password = df.iloc[2, 3]  # D3 (password)
        TAN_for_Deductor = df.iloc[3, 3]  # D4 (TAN for Deductor)

        # Setup Firefox options
        options = Options()
        options.headless = False  # Set to True if you want to run browser invisibly

        # Point to geckodriver
        service = Service(executable_path="./geckodriver.exe")  # Ensure geckodriver is in the same directory

        # Initialize the Firefox WebDriver
        driver = webdriver.Firefox(service=service, options=options)

        # Navigate to the TRACES login page
        driver.get("https://www.tdscpc.gov.in/app/login.xhtml?usr=Ded")

        # Fill in login form
        driver.find_element(By.ID, "userId").send_keys(user_id)
        driver.find_element(By.ID, "psw").send_keys(password)
        driver.find_element(By.ID, "tanpan").send_keys(TAN_for_Deductor)

        logging.debug("Credentials filled. Please enter CAPTCHA manually and click Login...")

        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.LINK_TEXT, "PAN Verification"))
        )
        logging.debug("Login successful!")

        # Navigate to PAN Verification page
        driver.get("https://www.tdscpc.gov.in/app/ded/panverify.xhtml")
        logging.debug("Navigated to PAN verification page.")
        driver.minimize_window()

        # Get PANs from first column (A) starting from second row
        pan_list = df.iloc[1:, 0].tolist()

        # Empty list to store statuses
        status_list = []

        for pan in pan_list:
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "pannumber")))

                # Enter PAN
                pan_input = driver.find_element(By.ID, "pannumber")
                pan_input.clear()
                pan_input.send_keys(pan)

                # Select Form Type = 26Q
                form_select = driver.find_element(By.ID, "frmType1")
                for option in form_select.find_elements(By.TAG_NAME, 'option'):
                    if option.get_attribute("value") == "26Q":
                        option.click()
                        break

                # Click Go
                driver.find_element(By.ID, "clickGo1").click()

                # Wait for Status to load
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "status")))

                status = driver.find_element(By.ID, "status").text.strip()
                logging.debug(f"{pan} => {status}")

            except Exception as e:
                logging.error(f"Error processing {pan}: {e}")
                status = "Error"

            # Add to status list
            status_list.append(status)

        # Add status back to DataFrame
        df.loc[1:, 1] = status_list

        # Save to CSV
        df.to_csv("PAN_Status_Only.csv", index=False, header=False)
        logging.debug("PAN status saved to PAN_Status_Only.csv")

        # Close the browser
        logging.debug("Closing the browser...")
        driver.quit()

        return {'success': True}

    except Exception as e:
        logging.error(f"An error occurred in selenium script: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    logging.debug("Starting the Flask app")
    serve(app, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
