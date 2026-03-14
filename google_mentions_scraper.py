import sys
import re
import urllib.parse
import time
import random
import pandas as pd
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver
from selenium_stealth import stealth

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

def extract_datetime_from_linkedin_url(url):
    # LinkedIn post/activity/article IDs are 19 digits long and contain the timestamp
    m = re.search(r'\b(\d{19})\b', str(url))
    if m:
        try:
            activity_id = int(m.group(1))
            # The first 41 bits of the 64-bit ID represent the Unix timestamp in milliseconds
            timestamp_ms = activity_id >> 22
            # Add UTC suffix or format appropriately later
            return datetime.fromtimestamp(timestamp_ms / 1000.0, timezone.utc)
        except Exception:
            pass
    return None

def parse_date(date_str):
    if not date_str:
        return None
    text_lower = str(date_str).strip().lower()
    now = datetime.now()

    # 1. Check for "Published Jan 1, 2026"
    m = re.search(r'published\s+([a-z]{3}\s+\d{1,2},\s+\d{4})', text_lower)
    if m:
        try: return pd.to_datetime(m.group(1)).to_pydatetime()
        except: pass

    # 2. Check for "22 Sept 2025" or "Oct 12, 2024"
    months = r'jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec'
    m = re.search(rf'(\d{{1,2}}\s+(?:{months})\s+\d{{4}})', text_lower)
    if m:
        try: return pd.to_datetime(m.group(1)).to_pydatetime()
        except: pass
            
    m = re.search(rf'((?:{months})\s+\d{{1,2}},\s+\d{{4}})', text_lower)
    if m:
        try: return pd.to_datetime(m.group(1)).to_pydatetime()
        except: pass
        
    m = re.search(r'(\d{4}-\d{2}-\d{2})', text_lower)
    if m:
        try: return pd.to_datetime(m.group(1)).to_pydatetime()
        except: pass

    # 3. Standard "ago"
    m = re.search(r'(\d+)\s+(days?|hours?|weeks?|months?|years?)\s+ago', text_lower)
    if m:
        try:
            num = int(m.group(1))
            unit = m.group(2)
            if 'hour' in unit: return now
            elif 'day' in unit: return now - timedelta(days=num)
            elif 'week' in unit: return now - timedelta(weeks=num)
            elif 'month' in unit: return now - timedelta(days=num*30)
            elif 'year' in unit: return now - timedelta(days=num*365)
        except: pass

    # 4. LinkedIn style short dates: 2mo. / 3w · / 1d —
    m = re.search(r'\b(\d+)(mo|w|d|h|m|yr)s?(?:\s*·|\s*\.|\s*—|\s|-)', text_lower)
    if m:
        try:
            num = int(m.group(1))
            unit = m.group(2)
            if unit == 'h' or unit == 'm': return now
            elif unit == 'd': return now - timedelta(days=num)
            elif unit == 'w': return now - timedelta(weeks=num)
            elif unit == 'mo': return now - timedelta(days=num*30)
            elif unit == 'yr': return now - timedelta(days=num*365)
        except: pass
        
    if 'yesterday' in text_lower:
        return now - timedelta(days=1)
        
    # 5. Last resort normal parsing
    try:
        if len(text_lower) < 30: # Avoid parsing entire long snippets with to_datetime
            return pd.to_datetime(text_lower).to_pydatetime()
    except:
        pass
        
    return None

def create_driver():
    # Use seleniumbase Driver with enhanced stealth settings
    # Removing hardcoded user agent to prevent Cloudflare/Google CAPTCHA triggers due to mismatch
    driver = Driver(
        uc=True, 
        headless=False
    )
    
    # Apply selenium-stealth to further mask the automated browser
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
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
            if "sorry" in driver.current_url or "captcha" in driver.page_source.lower():
                print("CAPTCHA detected! Waiting 30 seconds for you to solve it manually...")
                time.sleep(30)
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#search')))
                except:
                    print(f"Failed to load search results on page {page+1} after CAPTCHA wait.")
                    break
            else:
                print(f"Failed to load search results on page {page+1} or no results found.")
                break

        # Scroll randomly to look human
        for _ in range(random.randint(2, 5)):
            scroll_dist = random.randint(300, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
            time.sleep(random.uniform(0.8, 2.0))
            
        # Occasional micro-pause to simulate reading
        if random.random() > 0.7:
            time.sleep(random.uniform(2, 4))

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
            
            if link.startswith('/url?'):
                parsed_url = urllib.parse.urlparse(link)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'q' in query_params:
                    link = query_params['q'][0]
                elif 'url' in query_params:
                    link = query_params['url'][0]
            
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

            # Random micro-pause during processing
            if random.random() > 0.8:
                time.sleep(random.uniform(0.5, 1.5))

            text_to_evaluate = f"{title} {snippet}"
            category = categorize_mention(text_to_evaluate)
            
            if category == "Joint Mention":
                parsed_date = extract_datetime_from_linkedin_url(link)
                if not parsed_date:
                    parsed_date = parse_date(date_text) or parse_date(snippet)
                    
                all_results.append({
                    'Mention_Type': category,
                    'Date': parsed_date.strftime('%Y-%m-%d %H:%M:%S UTC') if parsed_date else 'Unknown',
                    'Title': title,
                    'Link': link,
                    'Snippet': snippet.strip()
                })
                    
        sleep_time = random.uniform(5, 10) # Increased delay between pages
        time.sleep(sleep_time)
        
    return all_results

def main():
    print("--- Starting Google Mentions Search (LinkedIn Last 6 Months) ---")
    driver = create_driver()
    
    # Strict search for Joint Mentions only (Last 6 months)
    q1 = 'site:linkedin.com/posts/ OR site:linkedin.com/pulse/ "Shayak Mazumder" "Adya AI"'
    
    # 15 pages per query -> 150 results.
    queries = [(q1, 15)]
    
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
        # Sort by Mention_Type first, then by actual parsed datetime descending
        df['sort_order'] = df['Mention_Type'].map({'Joint Mention': 0})
        # We need an actual datetime column to sort by properly. We can temporarily parse the Date string (handling 'Unknown')
        df['datetime_val'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values(by=['sort_order', 'datetime_val'], ascending=[True, False])
        df = df.drop(['sort_order', 'datetime_val'], axis=1)
        
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
        mention_types = ['Joint Mention']
        
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
