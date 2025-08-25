SOPEM Performance Dashboard 📈

A Streamlit application to monitor employee performance and production metrics in real-time.

Features

✅ Import CSV or Excel production data

✅ Clean and preprocess data automatically

✅ Compute global, monthly, and daily performance scores

✅ Detect performance anomalies (fraud detection using min/max thresholds)

✅ Visualize employee score evolution with interactive charts

✅ Analyze factory-level productivity

✅ Search and analyze individual employee tasks

✅ Download processed datasets and performance reports in Excel format

Table of Contents:

*Installation

*Usage

*Folder Structure

*Deployment

*Dependencies

*Contributing

*License

*Installation:

Clone the repository:

git clone https://github.com/hbibboudabbous/sope-app.git
cd sope-app


Create a virtual environment:

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows


Install dependencies:

pip install -r requirements.txt

*Usage:

Run the Streamlit app locally:

streamlit run app.py


Navigate to the app in your browser (http://localhost:8501)

Upload your CSV or Excel file

Choose the period of interest

Explore scores, trends, and anomalies

Download reports and the full processed dataset

*Folder Structure:
sope-app/
│
├─ app.py                  # Main Streamlit application
├─ cleaning_data.py        # Data cleaning and preprocessing functions
├─ calcul.py               # Functions to calculate performance scores
├─ functions.py            # Helper functions (charts, aggregations, etc.)
├─ requirements.txt        # Python dependencies
├─ outputs/                # Folder for exported Excel files
└─ README.md               # Project documentation

*Deployment:

You can deploy the app using:

Streamlit Community Cloud (recommended):

Push your repository to GitHub

Go to https://share.streamlit.io

Connect your GitHub repo and deploy

The app will be accessible via a public URL

Self-hosted server / cloud VM:

Use streamlit run app.py --server.port 8501 --server.address 0.0.0.0

Configure firewall or reverse proxy (Nginx) if needed

*Dependencies:

Python ≥ 3.11

pandas

numpy

streamlit

altair

xlsxwriter

openpyxl

Make sure all dependencies are listed in requirements.txt.

*Contributing:

Contributions are welcome!
Please submit issues or pull requests with clear explanations of changes.

*License:

MIT License © 2025 Boudabbous Mohamed Habib
