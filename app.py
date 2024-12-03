from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import random

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def extract_employee_count(text):
    if not text:
        return None
    
    patterns = [
        r'(\d+(?:,\d+)?(?:\+)?)\s*employees',
        r'(\d+(?:,\d+)?(?:\+)?)\s*workers',
        r'(\d+(?:,\d+)?(?:\-\d+(?:,\d+)?)?)\s*employees',
        r'size:\s*(\d+(?:,\d+)?(?:\+)?)',
        r'company size:\s*(\d+(?:,\d+)?(?:\+)?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            count = match.group(1).replace(',', '').replace('+', '')
            if '-' in count:
                low, high = map(int, count.split('-'))
                return (low + high) // 2
            return int(count)
    return None

def search_linkedin(company_name):
    try:
        url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            for tag in soup.find_all(['p', 'div', 'span']):
                if 'employees' in tag.text.lower():
                    count = extract_employee_count(tag.text)
                    if count:
                        return {'source': 'LinkedIn', 'count': count}
    except Exception as e:
        print(f"LinkedIn error for {company_name}: {str(e)}")
    return None

def search_google(company_name):
    try:
        query = f"{company_name} singapore number of employees"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            for tag in soup.find_all(['div', 'span', 'p']):
                if 'employees' in tag.text.lower():
                    count = extract_employee_count(tag.text)
                    if count:
                        return {'source': 'Google', 'count': count}
    except Exception as e:
        print(f"Google error for {company_name}: {str(e)}")
    return None

def search_company(company_name):
    sources = [search_linkedin, search_google]
    results = []
    
    for source_func in sources:
        try:
            result = source_func(company_name)
            if result:
                results.append(result)
            time.sleep(random.uniform(1, 2))  # Random delay between requests
        except Exception as e:
            print(f"Error in {source_func.__name__} for {company_name}: {str(e)}")
    
    if not results:
        return {
            'company_name': company_name,
            'employee_count': None,
            'sources': [],
            'error': 'No data found'
        }
    
    # Use the most common count or the highest if there's a tie
    counts = {}
    for result in results:
        count = result['count']
        counts[count] = counts.get(count, 0) + 1
    
    most_common = max(counts.items(), key=lambda x: (x[1], x[0]))
    
    return {
        'company_name': company_name,
        'employee_count': most_common[0],
        'sources': results,
        'error': None
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        if not data or 'companies' not in data:
            return jsonify({'error': 'No companies provided'}), 400
        
        companies = data['companies']
        if not isinstance(companies, list):
            return jsonify({'error': 'Companies must be provided as a list'}), 400
        
        if len(companies) > 50:
            return jsonify({'error': 'Maximum 50 companies allowed'}), 400
        
        results = []
        for company in companies:
            if not company.strip():
                continue
            result = search_company(company.strip())
            results.append(result)
            time.sleep(random.uniform(1, 2))  # Rate limiting between companies
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
