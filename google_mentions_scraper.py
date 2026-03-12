import sys
import re
import urllib.parse
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver

# Target base strings for Fuzzy Fallback
SHAYAK_TARGET = "shayak mazumder"
ADYA_TARGET = "adya ai"

# Regex patterns for spacing/casing/joining rules
shayak_regex = re.compile(r'shayak[\s\-]?mazumd[ea]r|#shayakmazumd[ea]r', re.IGNORECASE)
adya_regex = re.compile(r'adya[\s\-]?ai|#adya[\s\-]?ai', re.IGNORECASE)

FUZZY_THRESHOLD = 85.0

def matches_shayak(text: str) -> bool:
    if shayak_regex.search(text):
        return True
    if fuzz.partial_ratio(SHAYAK_TARGET, text.lower()) >= FUZZY_THRESHOLD:
        return True
    return False

def matches_adya(text: str) -> bool:
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

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip().lower()
    now = datetime.now()
    if 'ago' in date_str:
        try:
            num = int(re.search(r'\d+', date_str).group())
            if 'hour' in date_str or 'hr' in date_str or 'min' in date_str:
                return now
            elif 'day' in date_str:
                return now - timedelta(days=num)
            elif 'week' in date_str:
                return now - timedelta(weeks=num)
            elif 'month' in date_str:
                return now - timedelta(days=num*30)
            elif 'year' in date_str:
                return now - timedelta(days=num*365)
        except:
            return None
    elif 'yesterday' in date_str:
        return now - timedelta(days=1)
    else:
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except:
            pass
    return None

def create_driver():
    driver = Driver(uc=True, headless=False)
    return driver

def scrape_google_search(driver, search_query, max_pages=3, date_filter=None):
    encoded_query = urllib.parse.quote(search_query)
    base_url = f'https://www.google.com/search?q={encoded_query}'
    if date_filter:
        base_url += f'&tbs={date_filter}'

    all_results = []
    
    for page in range(max_pages):
        start_param = page * 10
        search_url = f"{base_url}&start={start_param}"
        print(f"Fetching Google Search (Page {page+1}): {search_query}")
        
        driver.get(search_url)

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#search')))
        except Exception as e:
            print(f"Failed to load search results on page {page+1} or no results found.")
            break

        # Scroll randomly to look human
        for _ in range(3):
            driver.execute_script(f"window.scrollBy(0, {random.randint(200, 700)});")
            time.sleep(random.uniform(0.5, 1.5))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        search_blocks = soup.select('div.g, div.tF2Cxc')
        
        if not search_blocks:
            break

        for block in search_blocks:
            title_elem = block.find('h3')
            link_elem = block.find('a', href=True)
            if not title_elem or not link_elem:
                continue
                
            title = title_elem.text.strip()
            link = link_elem.get('href', '')
            
            snippet_elems = block.select('div[style*="-webkit-line-clamp"], div.VwiC3b')
            snippet = ""
            date_text = ""
            if snippet_elems:
                for snip in snippet_elems:
                    snippet += snip.text.strip() + " "
            else:
                span_elems = block.find_all('span')
                for span in span_elems:
                    if 'ago' in span.text or '202' in span.text or '199' in span.text:
                         date_text = span.text.strip()
                    if len(span.text) > 40:
                        snippet += span.text + " "

            snippet = snippet.strip()
            
            if not date_text and snippet:
                date_match = re.match(r'^((?:\w{3}\s\d{1,2},\s\d{4}|\d+\s+(?:days?|hours?|weeks?|months?|years?)\s+ago|yesterday))\s*(?:—|-|·|\|)\s*', snippet, re.IGNORECASE)
                if date_match:
                    date_text = date_match.group(1).strip()
                    snippet = snippet[len(date_match.group(0)):].strip()

            text_to_evaluate = f"{title} {snippet}"
            category = categorize_mention(text_to_evaluate)
            
            if category != "No Target Mentioned":
                parsed_date = parse_date(date_text)
                all_results.append({
                    'Mention_Type': category,
                    'Date': parsed_date.strftime('%Y-%m-%d') if parsed_date else 'Unknown',
                    'Title': title,
                    'Link': link,
                    'Snippet': snippet.strip()
                })
                    
        sleep_time = random.uniform(3, 6)
        time.sleep(sleep_time)
        
    return all_results

def main():
    print("--- Starting Google Mentions Search (LinkedIn Last 6 Months) ---")
    driver = create_driver()
    
    # 1. Search Joint Mentions
    q1 = 'site:linkedin.com/posts/ OR site:linkedin.com/pulse/ "Shayak Mazumder" "Adya AI"'
    # 2. Search Adya AI only
    q2 = 'site:linkedin.com/posts/ OR site:linkedin.com/pulse/ "Adya AI"'
    # 3. Search Shayak only
    q3 = 'site:linkedin.com/posts/ OR site:linkedin.com/pulse/ "Shayak Mazumder"'
    
    queries = [(q1, 3), (q2, 3), (q3, 3)]
    
    all_combined_results = []
    seen_links = set()
    
    for query, pages in queries:
        results = scrape_google_search(driver, query, max_pages=pages, date_filter='qdr:m6')
        for r in results:
            if r['Link'] not in seen_links:
                seen_links.add(r['Link'])
                all_combined_results.append(r)

    driver.quit()

    print(f"\nScraping Complete! Found {len(all_combined_results)} valid mentions.")
    
    if all_combined_results:
        # Save to CSV
        df = pd.DataFrame(all_combined_results)
        
        # Sort so Joint Mentions are at the top, then Adya, then Shayak
        df['sort_order'] = df['Mention_Type'].map({'Joint Mention': 0, 'Adya AI Only': 1, 'Shayak Mazumder Only': 2})
        df = df.sort_values(by=['sort_order', 'Mention_Type']).drop('sort_order', axis=1)
        
        df.to_csv('google_mentions.csv', index=False)

        # Build nice HTML segregation
        html_output = "<html><head><meta charset='utf-8'><style>"
        html_output += "body{font-family:sans-serif; margin:20px;} "
        html_output += "table{border-collapse:collapse; width:100%; margin-bottom:30px;}"
        html_output += "th,td{border:1px solid #ddd; padding:8px; text-align:left;}"
        html_output += "tr:nth-child(even){background-color:#f9f9f9;}"
        html_output += "th{background-color:#4CAF50; color:white;}"
        html_output += "</style></head><body>"
        html_output += "<h1>Google Mentions: LinkedIn (Last 6 Months)</h1>"
        html_output += "<p>Below are all the scraped mentions successfully categorized by the entities they mention.</p>"
        
        # Segregate into separate tables
        mention_types = ['Joint Mention', 'Adya AI Only', 'Shayak Mazumder Only']
        
        for mtype in mention_types:
            subset = df[df['Mention_Type'] == mtype]
            if not subset.empty:
                html_output += f"<h2>{mtype} ({len(subset)} results)</h2>"
                html_output += subset.drop('Mention_Type', axis=1).to_html(index=False, escape=False, formatters={'Link': lambda x: f'<a href="{x}">{x[:50]}...</a>'})
                
        html_output += "</body></html>"
        
        with open('google_mentions.html', 'w', encoding='utf-8') as f:
            f.write(html_output)
            
        print("Data successfully saved to 'google_mentions.csv' and 'google_mentions.html'.")
    else:
        print("No matches were found.")

if __name__ == "__main__":
    main()
