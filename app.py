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
import asyncio

app = Flask(__name__)
CORS(app)

# Constants
MAX_WORKERS = 10  # Increased from 5 to 10
SEARCH_DELAY = 0.5  # Reduced from 1 to 0.5

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
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        companies = data.get('companies', [])
        format_type = data.get('format', 'json')
        
        if not companies:
            return jsonify({"error": "No companies provided"}), 400
            
        if len(companies) > 50:
            return jsonify({"error": "Maximum 50 companies allowed"}), 400
            
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(search_company, company.strip()): company for company in companies}
            for future in as_completed(futures):
                company = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    print(f"Error searching company {company}: {str(e)}")
                    result = {
                        "company": company,
                        "error": str(e),
                        "employee_count": "N/A",
                        "category": "Error",
                        "sources": []
                    }
                results.append(result)
                time.sleep(SEARCH_DELAY)
            
        if format_type == 'csv':
            try:
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['Company', 'Category', 'Employee Count', 'Trusted Source', 'LinkedIn URL', 'Google URL', 'Sources'])
                
                for result in results:
                    linkedin_url = next((source['url'] for source in result.get('sources', [])
                                       if source['source'] == 'LinkedIn'), '')
                    google_url = next((source['url'] for source in result.get('sources', [])
                                     if source['source'] == 'Google'), '')
                    sources = ', '.join([f"{source['source']}: {source['count']}" 
                                       for source in result.get('sources', [])])
                    
                    writer.writerow([
                        result['company'],
                        result.get('category', 'Unknown'),
                        result.get('employee_count', 'N/A'),
                        result.get('trusted_source', 'N/A'),
                        linkedin_url,
                        google_url,
                        sources
                    ])
                
                output.seek(0)
                return Response(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=company_results.csv'}
                )
            except Exception as e:
                print(f"Error generating CSV: {str(e)}")
                return jsonify({"error": "Error generating CSV"}), 500
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
                    return company_size
            
            time.sleep(1)
                
    except Exception as e:
        print(f"LinkedIn error for {company_name}: {str(e)}")
    
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
                        return extract_employee_count(size_value)
    except Exception as e:
        print(f"JobStreet error for {company_name}: {str(e)}")
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
                    return extract_employee_count(size_text)
    except Exception as e:
        print(f"Indeed error for {company_name}: {str(e)}")
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
                        return extract_employee_count(size_value)
    except Exception as e:
        print(f"MyCareersFuture error for {company_name}: {str(e)}")
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
                        return count
            
            # Add delay between attempts
            time.sleep(1)
                
    except Exception as e:
        print(f"Google error: {str(e)}")
    
    return None

def search_company(company_name):
    """Enhanced company search with multiple sources"""
    results = {
        'company': company_name,
        'employee_count': None,
        'category': 'Unknown',
        'trusted_source': None,
        'sources': []
    }
    
    # LinkedIn search (primary source)
    linkedin_count = get_linkedin_count(company_name)
    if linkedin_count:
        results['sources'].append({
            'source': 'LinkedIn',
            'count': linkedin_count,
            'url': f"https://www.linkedin.com/company/{quote(company_name.lower())}"
        })
        results['employee_count'] = linkedin_count
        results['trusted_source'] = 'LinkedIn'
    
    # JobStreet search
    jobstreet_count = get_jobstreet_count(company_name)
    if jobstreet_count:
        results['sources'].append({
            'source': 'JobStreet',
            'count': jobstreet_count,
            'url': f"https://www.jobstreet.com.sg/en/companies/{quote(company_name.lower())}-jobs"
        })
        if not results['employee_count']:
            results['employee_count'] = jobstreet_count
            results['trusted_source'] = 'JobStreet'
    
    # Indeed search
    indeed_count = get_indeed_count(company_name)
    if indeed_count:
        results['sources'].append({
            'source': 'Indeed',
            'count': indeed_count,
            'url': f"https://sg.indeed.com/cmp/{quote(company_name.replace(' ', '-'))}"
        })
        if not results['employee_count']:
            results['employee_count'] = indeed_count
            results['trusted_source'] = 'Indeed'
    
    # MyCareersFuture search
    mcf_count = get_mycareersfuture_count(company_name)
    if mcf_count:
        results['sources'].append({
            'source': 'MyCareersFuture',
            'count': mcf_count,
            'url': f"https://www.mycareersfuture.gov.sg/company/{quote(company_name.lower())}"
        })
        if not results['employee_count']:
            results['employee_count'] = mcf_count
            results['trusted_source'] = 'MyCareersFuture'
    
    # Google search as fallback
    if not results['employee_count']:
        google_count = get_google_count(company_name)
        if google_count:
            results['sources'].append({
                'source': 'Google',
                'count': google_count,
                'url': f"https://www.google.com/search?q={quote(company_name)}+singapore+number+of+employees"
            })
            results['employee_count'] = google_count
            results['trusted_source'] = 'Google'

    # Determine company category based on the most trusted source
    if results['employee_count']:
        count = extract_number_from_range(results['employee_count'])
        if count >= 200:
            results['category'] = 'Corporate'
        elif count <= 100:
            results['category'] = 'SME'
        else:
            results['category'] = 'Mid-sized Company'
        
        # Check if it's a recruitment company
        company_lower = company_name.lower()
        recruitment_keywords = ['recruit', 'staffing', 'manpower', 'employment agency', 'job agency', 'talent']
        if any(keyword in company_lower for keyword in recruitment_keywords):
            results['category'] = 'Recruitment Company'
    
    return results

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 3000))
        print(f"Starting server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting server: {str(e)}")
