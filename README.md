# Company Info Finder

A powerful web application that retrieves company information and employee counts from multiple sources including LinkedIn, JobStreet, Indeed, and MyCareersFuture.

## Features

- Multi-source company data retrieval
- Parallel processing for fast results
- Bulk company search (up to 50 companies)
- CSV export functionality
- Modern hacker-style UI
- Real-time results

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/company-info-finder.git
cd company-info-finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

## Usage

1. Open http://localhost:3000 in your browser
2. Enter company names (one per line)
3. Click "Search Companies" or "Download CSV"

## Data Sources

- LinkedIn
- JobStreet
- Indeed
- MyCareersFuture
- Google (fallback)

## Company Categories

- Corporate: ≥ 200 employees
- SME: ≤ 100 employees
- Mid-sized Company: 101-199 employees
- Recruitment Company: Detected via keywords

## Tech Stack

- Python 3.9
- Flask
- BeautifulSoup4
- Concurrent Processing
- Modern UI with Matrix theme
