# Telematics CSV Downloader

This tool automatically downloads, combines and put CSV report files from Telematics into structured folder that can be used by the dashboard.  
The script is packaged as a standalone program, so you can run it without needing to install Python or any extra libraries.

---

## How to Use (For Users)
1. Run the `.exe` file provided on the Sharepoint folder.  
2. Follow the instruction to login and provide date range for the analysis.
3. The program will automatically process the downloaded Telematics CSV files.  
4. Once finished, the "downloads" folder containing all CSV files will appear in the same location as the `.exe` file.  

That’s it — you can now open **PowerBI** dashboard to get the updated analysis!

---

## How to Build the Executable (For Developers Only)
If you need to rebuild the `.exe` file yourself:

1. Install **PyInstaller**:
   ```bash
   pip install pyinstaller
   ```
2. Open a terminal in the same folder as download_IOT_data.py.
3. Run the following command:
    ```bash
    pyinstaller --onefile --console download_IOT_data.py
    ```
4. Once finished, the .exe file will be located inside the dist/ folder.