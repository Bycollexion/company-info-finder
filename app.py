from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from fake_useragent import UserAgent
import random
import time
import concurrent.futures

app = Flask(__name__)
CORS(app)

def get_random_headers():
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def extract_employee_count(text):
    if not text:
        return None
    
    # Common patterns for employee counts
    patterns = [
        r'(\d+(?:,\d+)?(?:\+)?)\s*employees',
        r'(\d+(?:,\d+)?(?:\+)?)\s*workers',
        r'(\d+(?:,\d+)?(?:\-\d+(?:,\d+)?)?)\s*employees',
        r'size:\s*(\d+(?:,\d+)?(?:\+)?)',
        r'team size:\s*(\d+(?:,\d+)?(?:\+)?)',
        r'company size:\s*(\d+(?:,\d+)?(?:\+)?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            count = match.group(1).replace(',', '').replace('+', '')
            if '-' in count:
                # Take average of range
                low, high = map(int, count.split('-'))
                return (low + high) // 2
            return int(count)
    return None

def search_linkedin(company_name):
    try:
        url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            company_size = soup.find('dd', {'class': 'org-about-company-module__company-size-definition-text'})
            if company_size:
                return extract_employee_count(company_size.text)
    except Exception as e:
        print(f"LinkedIn error for {company_name}: {str(e)}")
    return None

def search_google(company_name):
    try:
        query = f"{company_name} singapore number of employees site:linkedin.com OR site:glassdoor.com OR site:indeed.com"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            snippets = soup.find_all('div', {'class': ['VwiC3b', 'yXK7lf']})
            
            for snippet in snippets:
                count = extract_employee_count(snippet.text)
                if count:
                    return count
    except Exception as e:
        print(f"Google error for {company_name}: {str(e)}")
    return None

def search_indeed(company_name):
    try:
        url = f"https://sg.indeed.com/cmp/{company_name.replace(' ', '-')}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            size_element = soup.find('div', string=re.compile(r'employees', re.I))
            if size_element:
                return extract_employee_count(size_element.text)
    except Exception as e:
        print(f"Indeed error for {company_name}: {str(e)}")
    return None

def search_glassdoor(company_name):
    try:
        url = f"https://www.glassdoor.sg/Overview/Working-at-{company_name.replace(' ', '-')}-EI_IE.htm"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            size_element = soup.find('div', string=re.compile(r'Size', re.I))
            if size_element:
                return extract_employee_count(size_element.parent.text)
    except Exception as e:
        print(f"Glassdoor error for {company_name}: {str(e)}")
    return None

def search_company(company_name):
    sources = {
        'LinkedIn': search_linkedin,
        'Google': search_google,
        'Indeed': search_indeed,
        'Glassdoor': search_glassdoor
    }
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_source = {
            executor.submit(func, company_name): source_name
            for source_name, func in sources.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                count = future.result()
                if count:
                    results.append({
                        'source': source,
                        'count': count
                    })
            except Exception as e:
                print(f"Error from {source}: {str(e)}")
    
    if not results:
        return None
    
    # Use the most common count or the highest if there's a tie
    counts = {}
    for result in results:
        count = result['count']
        counts[count] = counts.get(count, 0) + 1
    
    most_common = max(counts.items(), key=lambda x: (x[1], x[0]))
    return {
        'employee_count': most_common[0],
        'sources': results
    }

@app.route('/search', methods=['POST'])
def search():
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
        time.sleep(random.uniform(1, 2))  # Rate limiting
        result = {
            'company_name': company,
            'error': None
        }
        
        try:
            search_result = search_company(company)
            if search_result:
                result.update(search_result)
            else:
                result['error'] = 'No data found'
        except Exception as e:
            result['error'] = str(e)
        
        results.append(result)
    
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
