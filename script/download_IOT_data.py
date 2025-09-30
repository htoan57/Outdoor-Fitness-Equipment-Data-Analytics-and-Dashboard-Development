import time as newtime
import os
import glob
import pandas as pd
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, time

print("Loading the libraries, please wait...")
# === CONFIG ===
ASSET_URL = "https://unisa.telematics.guru/Report?ReportId=21"
TRIP_LIST_URL = "https://unisa.telematics.guru/Report?ReportId=2"
ASSET_LOCATION_URL = "https://unisa.telematics.guru/Report?ReportId=62"
IOT_DATA_URL = "https://unisa.telematics.guru/Report?ReportId=49"

# list of exclude assets by name or code
EXCLUDED_ASSETS = ['1066452', '1070033', '1070100', '981892', 
                  '982178', '982276', '982993', '983084', '983108', '983171',
                    'East P - Oyster', #not attached
                    'ECH - Sit Up P', #duplicated from 'ECH - Sit-Up B'
                    'Le Fev - Walk O', 'LCR - Wobble O' # removed as duplicate of their respective (Barra) versions
]

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
ASSET_LIST = "Asset List"
TRIP_LIST = "Trip List"
IOT_DATA = "IoT Data"
ASSET_LOCATION = "Asset Location"

def get_date_input(prompt, is_start=True):
    while True:
        date_str = input(prompt)
        try:
            # Parse date only (no time yet)
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            
            # Add time based on whether it's start or end date
            if is_start:
                date_obj = datetime.combine(date_obj.date(), time(0, 0))   # 00:00
            else:
                date_obj = datetime.combine(date_obj.date(), time(23, 59)) # 23:59
            
            return date_obj
        except ValueError:
            print("Invalid date format. Please use dd/mm/yyyy.")

def ask_user_login():
    while driver.current_url != ASSET_URL:
        driver.get(ASSET_URL)
        print("Please log in manually in the opened browser...")
        input("🔑 Press press ENTER after you finish logging in... \n")
        driver.get(ASSET_URL) # to make sure it return to the asset page event if user click other tabs

def move_all_files_into_new_location(old_location, new_location, timeout=60):
    os.makedirs(new_location, exist_ok=True)

    files = os.listdir(old_location)

    # first loop to wait for download begin
    seconds = 0
    while not any(f.endswith(".crdownload") or f.endswith(".part") or f.endswith(".tmp") for f in files) and seconds < timeout:
        newtime.sleep(1)
        seconds += 1

    # second loop to wait for all files to finish download, then move files
    seconds = 0
    while seconds < timeout:
        files = os.listdir(old_location)
        if not any(f.endswith(".crdownload") or f.endswith(".part") or f.endswith(".tmp") for f in files):
            for f in files:
                src = os.path.join(old_location, f)
                dst = os.path.join(new_location, f)
                
                if os.path.isfile(src):  # move only files, not folders
                    shutil.move(src, dst)
            newtime.sleep(1)
            return
        newtime.sleep(1)
        seconds += 1
    raise TimeoutError("Download did not complete in time")

def download_and_read_assest_list():
    file_location = os.path.join(DOWNLOAD_DIR, ASSET_LIST)

    # change export type to CSV
    driver.get(ASSET_URL)
    
    csv_button = driver.find_element(By.CSS_SELECTOR, '#reportContainer div.btn-group label.btn.btn-primary.ng-scope')
    csv_button.click()

    # Click download button
    driver.find_element(By.CSS_SELECTOR, "#btnDownloadReport").click()

    # Move file after download to correct location
    move_all_files_into_new_location(DOWNLOAD_DIR, file_location)
    print("✅ Asset List downloaded!")

    # === READ CSV ===
    asset_csv_file = None
    csv_files = glob.glob(os.path.join(file_location, "AssetList*.csv"))
    if not csv_files:
        raise FileNotFoundError("❌ No CSV file found matching 'AssetList*.csv'")
    asset_csv_file = csv_files[0]  # use the first one found

     # Read CSV
    df = pd.read_csv(asset_csv_file)

    # Filter out excluded assets
    df = df[~df['Name'].isin(EXCLUDED_ASSETS) & ~df['Asset Code'].isin(EXCLUDED_ASSETS)]

    # Overwrite CSV with filtered data
    df.to_csv(asset_csv_file, index=False)

    return df

def download_and_merge_asset_location(asset_names):
    file_location = os.path.join(DOWNLOAD_DIR, ASSET_LOCATION, "AssetLocation.csv")
    os.makedirs(os.path.join(DOWNLOAD_DIR, ASSET_LOCATION), exist_ok=True)

    # change export type to CSV
    driver.get(ASSET_LOCATION_URL)
    csv_button = driver.find_element(By.CSS_SELECTOR, '#reportContainer div.btn-group label.btn.btn-primary.ng-scope')
    csv_button.click()

   # loop through devices to download
    for item in asset_names:
        # 1. Select dropdown
        dropdown = driver.find_element(By.CSS_SELECTOR, "#reportContainer div.reportParameterContainer > div:nth-child(2) > span")
        dropdown.click()

        # 2. Select the option
        input_field = driver.find_element(By.CSS_SELECTOR, "body > span > span > span.select2-search.select2-search--dropdown > input") 
        input_field.clear()
        input_field.send_keys(item.strip())
        # Click on it
        dropdown_item = driver.find_element(By.CSS_SELECTOR, "#select2-AssetId-results > li")
        dropdown_item.click()

        # 3. Click download button
        driver.find_element(By.CSS_SELECTOR, "#btnDownloadReport").click()

    # Wait for download
    newtime.sleep(1)

    # === READ CSV ===
    csv_files = glob.glob(os.path.join(DOWNLOAD_DIR, "BasicDeviceDataExport*.csv"))
    if not csv_files:
        raise FileNotFoundError("❌ No CSV file found matching 'BasicDeviceDataExport*.csv'")
    
    # Ensure the number of files matches the asset_names list
    if len(csv_files) != len(asset_names):
        raise ValueError("❌ Number of files and asset_names must be the same")
    
    rows = []
    for file, device in zip(csv_files, asset_names):
        try:
            if device == 'Salisbury Oval - Body Twist':
                columns = [
                    "Date Logged (ACT (+09:30))",
                    "Log Reason",
                    "Latitude",
                    "Longitude",
                    "Speed KmH",
                    "Ignition",
                    "Driver Id Data",
                    "Trip Type Code",
                    "Project Code",
                    "Device Name"
                ]

                df = pd.DataFrame(columns=columns)
                df.loc[0] = [None, None, -34.7682900, 138.6446800, None, None, None, None, None, device]
                rows.append(df)
            else:
                # Read the first *data* row (skip header, take one row)
                df = pd.read_csv(file, skiprows=1, nrows=1, header=None)

                # Read header separately to assign correct column names
                header = pd.read_csv(file, nrows=0).columns
                df.columns = header

                if not df.empty:
                    df["Device Name"] = device
                    rows.append(df)
        except Exception as e:
            # print(f"⚠️ Could not read {file}: {e}")
            pass
    
    if rows:
        final_df = pd.concat(rows, ignore_index=True)
        final_df.to_csv(file_location, index=False)

        # Remove original CSV files
        for file in csv_files:
            try:
                os.remove(file)
            except Exception as e:
                pass

        print("✅ Asset Location downloaded!")
        
    else:
        raise ValueError("❌ No valid rows found in the CSV files")


def download_trip_list():
    file_location = os.path.join(DOWNLOAD_DIR, TRIP_LIST)

    # load page
    driver.get(TRIP_LIST_URL)
    
    # change to csv
    csv_button = driver.find_element(By.CSS_SELECTOR, '#reportContainer div.btn-group label.btn.btn-primary.ng-scope')
    csv_button.click()

    # Set the start date 
    start_date_field = driver.find_element(By.CSS_SELECTOR, "#StartDateUtc > input") 
    start_date_field.clear()
    start_date_field.send_keys(start_date.strftime('%d/%m/%Y %H:%M'))

    # Set the end date
    end_date_field = driver.find_element(By.CSS_SELECTOR, "#EndDateUtc > input") 
    end_date_field.clear()
    end_date_field.send_keys(end_date.strftime('%d/%m/%Y %H:%M'))

    # Click download button
    driver.find_element(By.CSS_SELECTOR, "#btnDownloadReport").click()

    # Move file after download to correct location
    move_all_files_into_new_location(DOWNLOAD_DIR, file_location)
    print("✅ Trip List downloaded!")


def download_IOT_info(asset_names):
    file_location = os.path.join(DOWNLOAD_DIR, IOT_DATA)
    driver.get(IOT_DATA_URL)

    # change export type to CSV
    csv_button = driver.find_element(By.CSS_SELECTOR, '#reportContainer div.btn-group label.btn.btn-primary.ng-scope')
    csv_button.click()

    # Set the start date 
    start_date_field = driver.find_element(By.CSS_SELECTOR, "#StartDateUtc > input") 
    start_date_field.clear()
    start_date_field.send_keys(start_date.strftime('%d/%m/%Y %H:%M'))

    # Set the end date
    end_date_field = driver.find_element(By.CSS_SELECTOR, "#EndDateUtc > input") 
    end_date_field.clear()
    end_date_field.send_keys(end_date.strftime('%d/%m/%Y %H:%M'))


    # loop through devices to download
    for item in asset_names:
        # 1. Select dropdown
        dropdown = driver.find_element(By.CSS_SELECTOR, "#reportContainer div.reportParameterContainer > div:nth-child(2) > span")
        dropdown.click()

        # 2. Select the option
        input_field = driver.find_element(By.CSS_SELECTOR, "body > span > span > span.select2-search.select2-search--dropdown > input") 
        input_field.clear()
        input_field.send_keys(item.strip())
        # Click on it
        dropdown_item = driver.find_element(By.CSS_SELECTOR, "#select2-AssetId-results > li")
        dropdown_item.click()

        # 3. Click download button
        driver.find_element(By.CSS_SELECTOR, "#btnDownloadReport").click()

        # 4. Wait for download
        newtime.sleep(2)

    import os
import time as newtime
import pandas as pd
from selenium.webdriver.common.by import By

def download_IOT_info(asset_names):
    file_location = os.path.join(DOWNLOAD_DIR, IOT_DATA)
    driver.get(IOT_DATA_URL)

    # change export type to CSV
    csv_button = driver.find_element(By.CSS_SELECTOR, '#reportContainer div.btn-group label.btn.btn-primary.ng-scope')
    csv_button.click()

    # Set the start date 
    start_date_field = driver.find_element(By.CSS_SELECTOR, "#StartDateUtc > input") 
    start_date_field.clear()
    start_date_field.send_keys(start_date.strftime('%d/%m/%Y %H:%M'))

    # Set the end date
    end_date_field = driver.find_element(By.CSS_SELECTOR, "#EndDateUtc > input") 
    end_date_field.clear()
    end_date_field.send_keys(end_date.strftime('%d/%m/%Y %H:%M'))

    # loop through devices to download
    for item in asset_names:
        # 1. Select dropdown
        dropdown = driver.find_element(By.CSS_SELECTOR, "#reportContainer div.reportParameterContainer > div:nth-child(2) > span")
        dropdown.click()

        # 2. Select the option
        input_field = driver.find_element(By.CSS_SELECTOR, "body > span > span > span.select2-search.select2-search--dropdown > input") 
        input_field.clear()
        input_field.send_keys(item.strip())
        # Click on it
        dropdown_item = driver.find_element(By.CSS_SELECTOR, "#select2-AssetId-results > li")
        dropdown_item.click()

        # 3. Click download button
        driver.find_element(By.CSS_SELECTOR, "#btnDownloadReport").click()

        # 4. Wait for download
        newtime.sleep(2)

    # Filter downloaded CSVs before moving
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.endswith(".csv"):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            try:
                df = pd.read_csv(filepath)

                if not df.empty and "Log Reason" in df.columns:
                    # Keep only rows where Log Reason == 'Start Of Trip'
                    df = df[df["Log Reason"] == "Start Of Trip"]

                    # Overwrite the file with filtered data
                    df.to_csv(filepath, index=False)
            except Exception as e:
                print(f"⚠️ Could not process {filename}: {e}")

    # Move file after download to correct location
    move_all_files_into_new_location(DOWNLOAD_DIR, file_location)
    print("✅ All IOT Data downloaded!")


# remove old folders and create new one
for folder_name in [ASSET_LIST, TRIP_LIST, IOT_DATA, ASSET_LOCATION, '']:
    old_folder_path = os.path.join(DOWNLOAD_DIR, folder_name)
    if os.path.exists(old_folder_path):
        shutil.rmtree(old_folder_path)
os.makedirs(DOWNLOAD_DIR, exist_ok=True) 

# === SETUP SELENIUM ===
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": DOWNLOAD_DIR,  # where files go
    "download.prompt_for_download": False,       # no popup
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)
options.add_experimental_option("excludeSwitches", ["enable-logging"])  # remove DevTools logs

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# === GET ASSET LIST ===
ask_user_login()
print("✅ Login in successfully! \n")

# Ask for start and end dates
print("Please enter the date range you want to download")
start_date = get_date_input("Enter start date (dd/mm/yyyy): ", is_start=True)
end_date = get_date_input("Enter end date (dd/mm/yyyy): ", is_start=False)

print("\n Automation is running, please wait...")

# download and read asset list into data frame
asset_df = download_and_read_assest_list()

download_and_merge_asset_location(asset_df['Name'].tolist())

# download trip list
download_trip_list()

# === GET IOT INFO ===
asset_with_4G_df = asset_df[asset_df['Device Type'].str.contains('Oyster Edge', na=False)] # only get devices with IOT details = Oyster Edge
download_IOT_info(asset_with_4G_df['Name'].tolist())
print("✅ All downloads complete.")

driver.quit()
