from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import csv
from io import StringIO
from urllib.parse import quote
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

# Constants
MAX_WORKERS = 8  # Increased workers for parallel processing
SEARCH_DELAY = 0.75  # Slightly reduced delay
BATCH_SIZE = 15  # Increased batch size
REQUEST_TIMEOUT = 10  # Timeout for individual requests

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Company Info Finder</title>
            <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Fira Code', monospace;
                    background-color: #1a1a1a;
                    color: #00ff00;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                textarea {
                    width: 100%;
                    height: 150px;
                    margin: 10px 0;
                    padding: 10px;
                    background-color: #2a2a2a;
                    border: 1px solid #00ff00;
                    color: #00ff00;
                    font-family: 'Fira Code', monospace;
                }
                button {
                    padding: 10px 20px;
                    margin: 5px;
                    cursor: pointer;
                    background-color: #2a2a2a;
                    border: 1px solid #00ff00;
                    color: #00ff00;
                    font-family: 'Fira Code', monospace;
                    transition: all 0.3s ease;
                }
                button:hover {
                    background-color: #00ff00;
                    color: #1a1a1a;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    background-color: #2a2a2a;
                }
                th, td {
                    border: 1px solid #00ff00;
                    padding: 12px;
                    text-align: left;
                }
                th {
                    background-color: #333;
                }
                .category-tag {
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    background-color: #333;
                }
                .category-corporate {
                    border: 1px solid #00ff00;
                    color: #00ff00;
                }
                .category-sme {
                    border: 1px solid #00ffff;
                    color: #00ffff;
                }
                .category-midsizedcompany {
                    border: 1px solid #ff00ff;
                    color: #ff00ff;
                }
                .category-recruitmentcompany {
                    border: 1px solid #ffff00;
                    color: #ffff00;
                }
                .category-unknown {
                    border: 1px solid #888;
                    color: #888;
                }
                .source-count {
                    display: inline-block;
                    margin-right: 10px;
                    color: #888;
                }
                .source-link {
                    display: inline-block;
                    padding: 4px 8px;
                    margin: 2px 4px;
                    border-radius: 4px;
                    text-decoration: none;
                    font-size: 0.9em;
                    background-color: #333;
                    border: 1px solid #00ff00;
                    color: #00ff00;
                }
                .source-link:hover {
                    background-color: #00ff00;
                    color: #1a1a1a;
                }
                #loading {
                    display: none;
                    margin: 20px 0;
                    color: #00ff00;
                    font-size: 1.2em;
                }
                .error {
                    color: #ff0000;
                    margin: 10px 0;
                }
                .trusted-source {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 4px;
                    background-color: #333;
                    border: 1px solid #00ff00;
                    color: #00ff00;
                }
                h1 {
                    text-shadow: 0 0 10px #00ff00;
                    letter-spacing: 2px;
                }
                /* Matrix-style loading animation */
                @keyframes matrix {
                    0% { content: "Searching."; }
                    33% { content: "Searching.."; }
                    66% { content: "Searching..."; }
                    100% { content: "Searching."; }
                }
                #loading::after {
                    content: "Searching.";
                    animation: matrix 1.5s infinite;
                }
            </style>
        </head>
        <body>
            <h1>> Company Info Finder_</h1>
            <div>
                <p>> Enter company names (one per line):</p>
                <textarea id="companies" placeholder="Enter company names here, one per line"></textarea>
            </div>
            <div>
                <button onclick="searchCompanies('json')">[ Search Companies ]</button>
                <button onclick="searchCompanies('csv')">[ Download CSV ]</button>
            </div>
            <div id="loading"></div>
            <div id="error" class="error"></div>
            <div id="results"></div>

            <script>
            async function searchCompanies(format = 'json') {
                const companiesText = document.getElementById('companies').value;
                const companies = companiesText.split('\\n').filter(c => c.trim());
                
                if (companies.length === 0) {
                    document.getElementById('error').textContent = '> Error: Please enter at least one company name';
                    return;
                }
                
                if (companies.length > 50) {
                    document.getElementById('error').textContent = '> Error: Maximum 50 companies allowed at once';
                    return;
                }
                
                document.getElementById('error').textContent = '';
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').innerHTML = '';
                
                try {
                    const response = await fetch('/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            companies: companies,
                            format: format
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    if (format === 'csv') {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'company_results.csv';
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    } else {
                        const data = await response.json();
                        
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        
                        let html = `
                            <h3>> Results for ${data.length} Companies_</h3>
                            <table>
                                <tr>
                                    <th>Company</th>
                                    <th>Category</th>
                                    <th>Employee Count</th>
                                    <th>Trusted Source</th>
                                    <th>Sources & Links</th>
                                </tr>`;
                        
                        data.forEach(result => {
                            const categoryClass = `category-${result.category?.toLowerCase().replace(/\s+/g, '') || 'unknown'}`;
                            
                            html += `
                                <tr>
                                    <td>${result.company}</td>
                                    <td><span class="category-tag ${categoryClass}">${result.category || 'Unknown'}</span></td>
                                    <td>${result.employee_count || 'N/A'}</td>
                                    <td><span class="trusted-source">${result.trusted_source || 'N/A'}</span></td>
                                    <td>`;
                            
                            if (result.sources) {
                                result.sources.forEach(source => {
                                    html += `<span class="source-count">${source.source}: ${source.count}</span>`;
                                    
                                    if (source.url) {
                                        const sourceClass = source.source.toLowerCase();
                                        html += `
                                            <a href="${source.url}" 
                                               target="_blank" 
                                               class="source-link source-${sourceClass}"
                                               title="View on ${source.source}">
                                                [ ${source.source} Source ]
                                            </a>`;
                                    }
                                    html += '<br>';
                                });
                            }
                            
                            html += `</td></tr>`;
                        });
                        
                        html += `</table>`;
                        document.getElementById('results').innerHTML = html;
                    }
                } catch (error) {
                    document.getElementById('error').textContent = `> Error: ${error.message || 'Unable to connect to server'}`;
                    console.error('Error:', error);
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            }
            </script>
        </body>
        </html>
        '''
    except Exception as e:
        print(f"Error serving index page: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/search', methods=['POST'])
def search():
    """Handle search requests"""
    try:
        data = request.get_json()
        companies = data.get('companies', [])
        
        if not companies:
            return jsonify({'error': 'No companies provided'}), 400
            
        if len(companies) > 50:
            return jsonify({'error': 'Maximum 50 companies allowed'}), 400

        results = []
        total_companies = len(companies)
        
        # Process companies in batches with progress tracking
        for i in range(0, total_companies, BATCH_SIZE):
            batch = companies[i:i + BATCH_SIZE]
            print(f"Processing batch {i//BATCH_SIZE + 1} of {(total_companies + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                batch_futures = [executor.submit(process_company, company) for company in batch]
                batch_results = []
                
                for future in as_completed(batch_futures):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        print(f"Batch processing error: {str(e)}")
                        continue
                
                results.extend(batch_results)
            
            # Only sleep between batches if there are more batches to process
            if i + BATCH_SIZE < total_companies:
                time.sleep(0.5)  # Reduced delay between batches
            
        return jsonify({'results': results})
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_company(company_name):
    try:
        time.sleep(SEARCH_DELAY)  # Add delay between requests
        return search_company(company_name)
    except Exception as e:
        print(f"Error processing {company_name}: {str(e)}")
        return {
            'company_name': company_name,
            'employee_count': 'Error',
            'category': 'Error',
            'source': 'Error',
            'error': str(e)
        }

def get_headers():
    """Generate random headers to avoid detection"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def extract_employee_count(text):
    """Extract employee count text from LinkedIn's company size field"""
    if not text:
        return None
        
    # Standard LinkedIn company size ranges
    linkedin_ranges = [
        '0-1',
        '2-10',
        '11-50',
        '51-200',
        '201-500',
        '501-1,000',
        '1,001-5,000',
        '5,001-10,000',
        '10,001+'
    ]
    
    # Clean and standardize the text
    text = text.lower().strip()
    text = re.sub(r'employees|company size|·|\s+', ' ', text).strip()
    
    # Try to find an exact LinkedIn range
    for range_text in linkedin_ranges:
        if range_text.lower() in text:
            return range_text
            
    # If no standard range found, try to extract any number range
    number_patterns = [
        r'([\d,]+\+)',  # Matches "10,001+"
        r'([\d,]+-[\d,]+)',  # Matches "1,001-5,000"
        r'([\d,]+)',  # Matches any number
    ]
    
    for pattern in number_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def extract_number_from_range(text):
    """Extract the number from a range"""
    if not text:
        return None
        
    # Extract the number from a range
    number_patterns = [
        r'([\d,]+)\+',  # Matches "10,001+"
        r'([\d,]+)-([\d,]+)',  # Matches "1,001-5,000"
        r'([\d,]+)',  # Matches any number
    ]
    
    for pattern in number_patterns:
        match = re.search(pattern, text)
        if match:
            if match.group(1):
                return int(match.group(1).replace(',', ''))
            elif match.group(2):
                return int(match.group(2).replace(',', ''))
    
    return None

def is_recruitment_company(company_name, description=""):
    """Check if the company is a recruitment company"""
    recruitment_keywords = [
        'recruitment', 'staffing', 'manpower', 'headhunting', 'talent acquisition',
        'employment agency', 'job agency', 'placement agency', 'hr solutions',
        'personnel', 'workforce', 'recruiting'
    ]
    
    text = (company_name + " " + description).lower()
    return any(keyword in text for keyword in recruitment_keywords)

def get_company_category(size_text, company_name, description=""):
    """Categorize company based on employee count text"""
    if not size_text:
        return "Unknown"
        
    if is_recruitment_company(company_name, description):
        return "Recruitment Company"
        
    # Convert size range to minimum number for categorization
    size_to_min = {
        '0-1': 1,
        '2-10': 2,
        '11-50': 11,
        '51-200': 51,
        '201-500': 201,
        '501-1,000': 501,
        '1,001-5,000': 1001,
        '5,001-10,000': 5001,
        '10,001+': 10001
    }
    
    # Try to get the minimum number from the size range
    try:
        if size_text in size_to_min:
            count = size_to_min[size_text]
        else:
            # Handle other formats
            match = re.search(r'([\d,]+)', size_text)
            if match:
                count = int(match.group(1).replace(',', ''))
            else:
                return "Unknown"
    except:
        return "Unknown"
    
    if count >= 200:
        return "Corporate"
    elif count <= 100:
        return "SME"
    else:
        return "Mid-sized Company"

def get_company_linkedin_handle(company_name):
    """Get standardized LinkedIn handle for known companies"""
    company_handles = {
        # Tech Companies
        'google': 'google-singapore',
        'google singapore': 'google-singapore',
        'meta': 'meta-singapore',
        'facebook': 'meta-singapore',
        'facebook singapore': 'meta-singapore',
        'meta singapore': 'meta-singapore',
        'microsoft': 'microsoft-singapore',
        'microsoft singapore': 'microsoft-singapore',
        'apple': 'apple-singapore',
        'apple singapore': 'apple-singapore',
        'amazon': 'amazon-singapore',
        'amazon singapore': 'amazon-singapore',
        'aws': 'amazon-web-services-singapore',
        'amazon web services': 'amazon-web-services-singapore',
        # Singapore Companies
        'singtel': 'singtel',
        'singapore telecommunications': 'singtel',
        'dbs': 'dbs-bank',
        'dbs bank': 'dbs-bank',
        'ocbc': 'ocbc-bank',
        'ocbc bank': 'ocbc-bank',
        'uob': 'uob-group',
        'united overseas bank': 'uob-group',
    }
    return company_handles.get(company_name.lower())

def validate_employee_count(count, company_name):
    """Validate and adjust employee count based on known company information"""
    if not count:
        return None
        
    # Known minimum employee counts for companies
    company_minimums = {
        # Tech Companies
        'google': 2000,
        'meta': 1000,
        'facebook': 1000,
        'microsoft': 1500,
        'apple': 1500,
        'amazon': 2000,
        'aws': 1000,
        # Singapore Companies
        'singtel': 20000,  # Singtel has over 20,000 employees
        'dbs': 30000,      # DBS has over 30,000 employees
        'ocbc': 25000,     # OCBC has over 25,000 employees
        'uob': 25000,      # UOB has over 25,000 employees
    }
    
    company_key = next((k for k in company_minimums.keys() 
                       if k in company_name.lower()), None)
    
    if company_key and count < company_minimums[company_key]:
        return company_minimums[company_key]
    
    return count

def get_linkedin_count(company_name):
    """Get employee count from LinkedIn"""
    try:
        # Try to get known LinkedIn handle first
        known_handle = get_company_linkedin_handle(company_name)
        variations = ([known_handle] if known_handle else []) + [
            company_name.lower(),
            company_name.lower().replace(' ', '-'),
            company_name.lower().replace(' pte ltd', ''),
            company_name.lower().replace(' limited', ''),
            f"{company_name.lower()}-singapore"
        ]
        
        for variation in variations:
            url = f"https://www.linkedin.com/company/{quote(variation)}"
            response = requests.get(url, headers=get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Look specifically for company size field
                size_selectors = [
                    'div[data-test-id="about-us__size"]',
                    'dd.org-about-company-module__company-size-definition-text',
                    'div.org-about-company-module__company-staff-count-range',
                    'div.basic-info-item:contains("Company size")',
                    '.org-page-details__definition-text',
                    '.org-about-company-module__company-size',
                ]
                
                company_size = None
                for selector in size_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text()
                            if 'size' in text.lower() or 'employees' in text.lower():
                                size_text = extract_employee_count(text)
                                if size_text:
                                    company_size = size_text
                                    break
                        if company_size:
                            break
                    except Exception as e:
                        continue
                
                if company_size:
                    return {'source': 'LinkedIn', 'employee_count': company_size}
            
            time.sleep(1)
                
    except Exception as e:
        print(f"Error in LinkedIn search for {company_name}: {str(e)}")
    
    return None

def get_jobstreet_count(company_name):
    """Get employee count from JobStreet"""
    try:
        search_url = f"https://www.jobstreet.com.sg/en/companies/{quote(company_name.lower())}-jobs"
        response = requests.get(search_url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            company_info = soup.find('div', {'class': 'company-info'})
            if company_info:
                size_text = company_info.find(text=re.compile(r'(?i)company size|employees'))
                if size_text:
                    parent = size_text.parent
                    size_value = parent.find_next(text=re.compile(r'\d+'))
                    if size_value:
                        count = extract_employee_count(size_value)
                        if count:
                            return {'source': 'JobStreet', 'employee_count': count}
    except Exception as e:
        print(f"Error in JobStreet search for {company_name}: {str(e)}")
    return None

def get_indeed_count(company_name):
    """Get employee count from Indeed Singapore"""
    try:
        search_url = f"https://sg.indeed.com/cmp/{quote(company_name.replace(' ', '-'))}"
        response = requests.get(search_url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            size_div = soup.find('div', text=re.compile(r'(?i)employees'))
            if size_div:
                size_text = size_div.find_next(text=re.compile(r'\d+|\d+[,]\d+|\d+[-]\d+'))
                if size_text:
                    count = extract_employee_count(size_text)
                    if count:
                        return {'source': 'Indeed', 'employee_count': count}
    except Exception as e:
        print(f"Error in Indeed search for {company_name}: {str(e)}")
    return None

def get_mycareersfuture_count(company_name):
    """Get employee count from MyCareersFuture Singapore"""
    try:
        search_url = f"https://www.mycareersfuture.gov.sg/company/{quote(company_name.lower())}"
        response = requests.get(search_url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            company_info = soup.find('div', {'class': re.compile(r'(?i)company-info|company-details')})
            if company_info:
                size_text = company_info.find(text=re.compile(r'(?i)company size|employees'))
                if size_text:
                    size_value = size_text.find_next(text=re.compile(r'\d+|\d+[,]\d+|\d+[-]\d+'))
                    if size_value:
                        count = extract_employee_count(size_value)
                        if count:
                            return {'source': 'MyCareersFuture', 'employee_count': count}
    except Exception as e:
        print(f"Error in MyCareersFuture search for {company_name}: {str(e)}")
    return None

def get_google_count(company_name):
    """Get employee count from Google"""
    try:
        # Try different search queries
        queries = [
            f"{company_name} singapore number of employees site:linkedin.com",
            f"{company_name} singapore employee count site:linkedin.com",
            f"{company_name} singapore staff strength site:sgpbusiness.com",
            f"{company_name} singapore company size"
        ]
        
        for query in queries:
            url = f"https://www.google.com/search?q={quote(query)}"
            response = requests.get(url, headers=get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Search in different elements
                for div in soup.find_all(['div', 'span', 'p']):
                    count = extract_employee_count(div.get_text())
                    if count:
                        return {'source': 'Google', 'employee_count': count}
            
            # Add delay between attempts
            time.sleep(1)
                
    except Exception as e:
        print(f"Error in Google search for {company_name}: {str(e)}")
    
    return None

def search_company(company_name):
    """Enhanced company search with multiple sources"""
    try:
        # Add timeout to requests
        session = requests.Session()
        session.timeout = REQUEST_TIMEOUT
        
        sources = [
            ('LinkedIn', get_linkedin_count),
            ('JobStreet', get_jobstreet_count),
            ('Indeed', get_indeed_count),
            ('MyCareersFuture', get_mycareersfuture_count),
            ('Google', get_google_count)
        ]
        
        results = []
        employee_counts = []
        
        for source_name, search_func in sources:
            try:
                result = search_func(company_name)
                if result and result.get('employee_count'):
                    results.append(result)
                    if result['employee_count'].isdigit():
                        employee_counts.append(int(result['employee_count']))
            except Exception as e:
                print(f"Error in {source_name} search for {company_name}: {str(e)}")
                continue
        
        if not results:
            return {
                'company_name': company_name,
                'employee_count': 'Not found',
                'category': 'Unknown',
                'source': 'None',
                'error': 'No data found from any source'
            }
        
        # Use the most common or highest employee count
        if employee_counts:
            employee_count = max(set(employee_counts), key=employee_counts.count)
        else:
            employee_count = results[0]['employee_count']
        
        # Determine company category
        category = get_company_category(str(employee_count), company_name.lower())
        
        return {
            'company_name': company_name,
            'employee_count': str(employee_count),
            'category': category,
            'source': results[0]['source'],
            'sources': [{'source': r['source'], 'count': r['employee_count']} for r in results]
        }
        
    except Exception as e:
        print(f"Error processing {company_name}: {str(e)}")
        return {
            'company_name': company_name,
            'employee_count': 'Error',
            'category': 'Error',
            'source': 'Error',
            'error': str(e)
        }

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 3000))
        print(f"Starting server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting server: {str(e)}")
