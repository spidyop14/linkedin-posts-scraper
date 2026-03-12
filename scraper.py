import requests
import json
import re
import urllib.parse
import pandas as pd
from datetime import datetime
import os
import sys
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

# Target base strings for Fuzzy Fallback
SHAYAK_TARGET = "shayak mazumder"
ADYA_TARGET = "adya ai"

# Regex patterns for spacing/casing/joining rules
shayak_regex = re.compile(r'shayak[\s\-]?mazumd[ea]r|#shayakmazumd[ea]r', re.IGNORECASE)
adya_regex = re.compile(r'adya[\s\-]?ai|#adya[\s\-]?ai', re.IGNORECASE)

FUZZY_THRESHOLD = 85.0

def matches_shayak(text: str) -> bool:
    if not text: return False
    if shayak_regex.search(text):
        return True
    if fuzz.partial_ratio(SHAYAK_TARGET, text.lower()) >= FUZZY_THRESHOLD:
        return True
    return False

def matches_adya(text: str) -> bool:
    if not text: return False
    if adya_regex.search(text):
        return True
    if fuzz.partial_ratio(ADYA_TARGET, text.lower()) >= FUZZY_THRESHOLD:
        return True
    return False

def categorize_mention(text: str) -> str:
    has_shayak = matches_shayak(text)
    has_adya = matches_adya(text)
    
    if has_shayak and has_adya:
        return "Joint Mention"
    elif has_shayak:
        return "Shayak Mazumder Only"
    elif has_adya:
        return "Adya AI Only"
    else:
        return "No Target Mentioned"

def extract_posts_from_html(html_source):
    soup = BeautifulSoup(html_source, 'html.parser')
    code_blocks = soup.find_all('code', id=re.compile('^bpr-guid-'))
    
    seen_urns = set()
    found_posts = []

    for block in code_blocks:
        try:
            data = json.loads(block.get_text().strip())
        except json.JSONDecodeError:
            continue
            
        def traverse(obj):
            if isinstance(obj, dict):
                urn = obj.get('entityUrn', '') or obj.get('urn', '')
                
                text = ""
                if 'commentary' in obj:
                    comm = obj['commentary']
                    if isinstance(comm, dict) and 'text' in comm and isinstance(comm['text'], dict):
                        text = comm['text'].get('text', '')
                elif 'text' in obj and isinstance(obj['text'], dict):
                     text = obj['text'].get('text', '')
                elif 'value' in obj and isinstance(obj['value'], str):
                     text = obj['value']

                if text and urn and 'activity:' in str(urn):
                    activity_id = str(urn).split(':activity:')[-1].split(',')[0]
                    link = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
                    
                    if urn not in seen_urns:
                        category = categorize_mention(text)
                        if category != "No Target Mentioned":
                            seen_urns.add(urn)
                            found_posts.append({
                                'Mention_Type': category,
                                'Date': 'Past 6 Months',
                                'Title': 'LinkedIn Post',
                                'Link': link,
                                'Content': text.strip().replace('\n', ' ')
                            })
                
                for value in obj.values():
                    traverse(value)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)
                    
        traverse(data)
        
    return found_posts

def main():
    print("--- LinkedIn High-Speed API Scraper (Regex + Fuzzy Segregation) ---")
    
    li_at = os.environ.get('LI_AT')
    jsessionid = os.environ.get('JSESSIONID')
    
    if not li_at or not jsessionid:
        print("\n[!] Missing LinkedIn Session Cookies (LI_AT / JSESSIONID).")
        print("Please log in to LinkedIn in your browser, open Developer Tools (F12) -> Application -> Cookies.")
        print("Find 'li_at' and 'JSESSIONID' and enter them below:\n")
        
        try:
            li_at = input("Enter 'li_at' cookie: ").strip()
            jsessionid = input("Enter 'JSESSIONID' cookie: ").strip()
        except:
             pass
        
    if not li_at or not jsessionid:
        print("Cookies are required to use the internal API. Exiting.")
        sys.exit(1)

    jsessionid = jsessionid.replace('"', '')

    session = requests.Session()
    session.cookies.set('li_at', li_at, domain='.linkedin.com')
    session.cookies.set('JSESSIONID', f'"{jsessionid}"', domain='.linkedin.com')
    
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'csrf-token': jsessionid,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    session.headers.update(headers)

    query = '"Shayak Mazumder" OR "Adya AI"'
    encoded_query = urllib.parse.quote(query)
    
    search_url = f"https://www.linkedin.com/search/results/content/?datePosted=%22past-6-months%22&keywords={encoded_query}"
    
    print(f"\n[1/3] Fetching data directly from LinkedIn backend...")
    start_time = datetime.now()
    
    try:
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to LinkedIn: {e}")
        sys.exit(1)
        
    print(f"[2/3] Parsing embedded JSON payloads and evaluating matches...")
    html_source = response.text
    
    if "sign in" in html_source.lower() and "join linkedin" in html_source.lower():
        print("Warning: LinkedIn might have redirected to the login page. Your cookies might be expired.")
        
    results = extract_posts_from_html(html_source)
    
    exec_time = (datetime.now() - start_time).total_seconds()
    print(f"[3/3] Found {len(results)} relevant posts in {exec_time:.2f} seconds.")
    
    if results:
        df = pd.DataFrame(results)
        
        # Sort Mentions Priority
        df['sort_order'] = df['Mention_Type'].map({'Joint Mention': 0, 'Adya AI Only': 1, 'Shayak Mazumder Only': 2})
        df = df.sort_values(by=['sort_order', 'Mention_Type']).drop('sort_order', axis=1)
        
        df.to_csv('linkedin_posts.csv', index=False)
        
        # Build HTML Segregation
        html = "<html><head><meta charset='utf-8'><style>"
        html += "body{font-family:sans-serif; margin:20px;} "
        html += "table{border-collapse:collapse; width:100%; margin-bottom:30px;}"
        html += "th,td{border:1px solid #ddd; padding:8px; text-align:left;}"
        html += "tr:nth-child(even){background-color:#f9f9f9;}"
        html += "th{background-color:#0077B5; color:white;}"
        html += "</style></head><body>"
        html += "<h1>LinkedIn Mentions (Past 6 Months)</h1>"
        
        mention_types = ['Joint Mention', 'Adya AI Only', 'Shayak Mazumder Only']
        for mtype in mention_types:
            subset = df[df['Mention_Type'] == mtype]
            if not subset.empty:
                html += f"<h2>{mtype} ({len(subset)} posts)</h2>"
                html += subset.drop('Mention_Type', axis=1).to_html(index=False, escape=False, formatters={'Link': lambda x: f'<a href="{x}">{x[:50]}...</a>'})
        
        html += "</body></html>"
        
        with open('linkedin_mentions.html', 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"\nData successfully saved to 'linkedin_posts.csv' and 'linkedin_mentions.html'.")
    else:
        print("\nNo matching posts found in the last 6 months using the API.")

if __name__ == "__main__":
    main()