from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from datetime import datetime, timedelta
from collections import deque

app = Flask(__name__)
CORS(app)

# Rate limiting setup
class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  # in seconds
        self.requests = deque()
    
    def can_make_request(self):
        now = datetime.now()
        # Remove old requests
        while self.requests and self.requests[0] < now - timedelta(seconds=self.time_window):
            self.requests.popleft()
        
        # Check if we can make a new request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def time_until_next(self):
        if not self.requests:
            return 0
        
        oldest_request = self.requests[0]
        time_passed = (datetime.now() - oldest_request).total_seconds()
        if time_passed < self.time_window:
            return self.time_window - time_passed
        return 0

# Create rate limiters for different sources
linkedin_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 requests per minute
google_limiter = RateLimiter(max_requests=5, time_window=60)    # 5 requests per minute

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

def get_employee_range(count):
    if count is None:
        return "Unknown"
    if count < 50:
        return "<50"
    elif count < 100:
        return "50-100"
    elif count < 200:
        return "100-200"
    else:
        return ">200"

def categorize_company(employee_count):
    if employee_count is None:
        return "Unknown"
    if employee_count < 200:
        return "SME"
    return "Corporate"

def search_linkedin(company_name):
    if not linkedin_limiter.can_make_request():
        wait_time = linkedin_limiter.time_until_next()
        time.sleep(wait_time)
        if not linkedin_limiter.can_make_request():
            return {'error': 'Rate limit exceeded for LinkedIn, please try again later'}
    
    try:
        company_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}"
        response = requests.get(company_url, headers=HEADERS, timeout=10)
        
        if response.status_code == 429:  # Too Many Requests
            return {'error': 'LinkedIn rate limit reached, please try again later'}
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            for tag in soup.find_all(['p', 'div', 'span']):
                if 'employees' in tag.text.lower():
                    count = extract_employee_count(tag.text)
                    if count:
                        is_recruitment = any(keyword in tag.text.lower() for keyword in ['recruitment', 'staffing', 'manpower', 'hr solutions'])
                        category = "Recruitment Agency" if is_recruitment else categorize_company(count)
                        return {
                            'source': 'LinkedIn',
                            'count': count,
                            'range': get_employee_range(count),
                            'url': company_url,
                            'category': category
                        }
    except requests.exceptions.Timeout:
        return {'error': 'LinkedIn request timed out'}
    except Exception as e:
        return {'error': f'LinkedIn error: {str(e)}'}
    return None

def search_google(company_name):
    if not google_limiter.can_make_request():
        wait_time = google_limiter.time_until_next()
        time.sleep(wait_time)
        if not google_limiter.can_make_request():
            return {'error': 'Rate limit exceeded for Google, please try again later'}
    
    try:
        query = f"{company_name} singapore number of employees site:linkedin.com OR site:glassdoor.com"
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code == 429:  # Too Many Requests
            return {'error': 'Google rate limit reached, please try again later'}
            
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            for result in soup.find_all('div', class_='g'):
                link = result.find('a')
                if link and ('linkedin.com' in link['href'] or 'glassdoor.com' in link['href']):
                    result_url = link['href']
                    text_content = result.get_text()
                    count = extract_employee_count(text_content)
                    if count:
                        is_recruitment = any(keyword in text_content.lower() for keyword in ['recruitment', 'staffing', 'manpower', 'hr solutions'])
                        category = "Recruitment Agency" if is_recruitment else categorize_company(count)
                        return {
                            'source': 'Google',
                            'count': count,
                            'range': get_employee_range(count),
                            'url': result_url,
                            'category': category
                        }
    except requests.exceptions.Timeout:
        return {'error': 'Google request timed out'}
    except Exception as e:
        return {'error': f'Google error: {str(e)}'}
    return None

def search_company(company_name):
    results = []
    errors = []
    
    # Try LinkedIn first
    linkedin_result = search_linkedin(company_name)
    if linkedin_result:
        if 'error' in linkedin_result:
            errors.append(linkedin_result['error'])
        else:
            results.append(linkedin_result)
    
    # Add delay between requests
    time.sleep(random.uniform(1, 2))
    
    # Try Google if LinkedIn failed or had no results
    if not results:
        google_result = search_google(company_name)
        if google_result:
            if 'error' in google_result:
                errors.append(google_result['error'])
            else:
                results.append(google_result)
    
    if not results:
        return {
            'company_name': company_name,
            'employee_range': 'Unknown',
            'sources': [],
            'error': '; '.join(errors) if errors else 'No data found'
        }
    
    # Use the most reliable source
    best_result = results[0]
    
    return {
        'company_name': company_name,
        'employee_range': get_employee_range(best_result['count']),
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
            
            # Add delay between companies
            time.sleep(random.uniform(2, 3))
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
