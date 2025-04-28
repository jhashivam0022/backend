import sys
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert

# Get the CSV file path from command-line arguments
file_path = sys.argv[1]

# Read the CSV with no header
df = pd.read_csv(file_path, header=None)

# Extract credentials from the DataFrame (assumes credentials are in specific columns)
user_id = df.iloc[1, 3]  # D2 (user ID)
password = df.iloc[2, 3]  # D3 (password)
TAN_for_Deductor = df.iloc[3, 3]  # D4 (TAN for Deductor)

# Setup Firefox options
options = Options()
options.headless = False  # Set to True to run headless

# Initialize the Firefox WebDriver
driver = webdriver.Firefox(options=options)

# Navigate to the TRACES login page
driver.get("https://www.tdscpc.gov.in/app/login.xhtml?usr=Ded")

try:
    # Fill in the login form with user credentials
    driver.find_element(By.ID, "userId").send_keys(user_id)
    driver.find_element(By.ID, "psw").send_keys(password)
    driver.find_element(By.ID, "tanpan").send_keys(TAN_for_Deductor)

    print("Credentials filled. Please enter CAPTCHA manually and click Login...")

    WebDriverWait(driver, 300).until(
        EC.presence_of_element_located((By.LINK_TEXT, "PAN Verification"))
    )
    print("Login successful!")

    # Proceed to the PAN Verification page
    driver.get("https://www.tdscpc.gov.in/app/ded/panverify.xhtml")
    print("Navigated to PAN verification page.")
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
            print(f"{pan} => {status}")

        except Exception as e:
            print(f"Error processing {pan}: {e}")
            status = "Error"

        # Add to status list
        status_list.append(status)

    # Add status back to DataFrame (assumes 2nd column is for status, index 1)
    df.loc[1:, 1] = status_list

    # Save to CSV
    df.to_csv("PAN_Status_Only.csv", index=False, header=False)
    print("PAN status saved to PAN_Status_Only.csv")

except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)

finally:
    print("Closing the browser...")
    driver.quit()
