# LinkedIn Mentions Scraper - Limitations & Setup Guide

This tool automates searching Google for LinkedIn references mentioning specific target keywords (e.g., "Shayak Mazumder" and "Adya AI") occurring within a 6-month timeframe. Because it acts as an automated browser parsing Google Search results, it comes with several inherent limitations due to Google's strict anti-bot mechanisms.

## Tool Limitations

### 1. Google CAPTCHA & IP Blocking
- **Triggering Bot Detection:** Google aggressively monitors traffic for automated behavior. Even with advanced stealth tools (`seleniumbase`, `uc=True`, and `selenium-stealth`), rapid or repeated searches will eventually trigger Google's "I am not a robot" CAPTCHA, or temporarily soft-ban the IP address.
- **Manual Intervention Requirement:** If a CAPTCHA appears, the script pauses for 30 seconds to allow the user to solve it manually in the visible browser window. If it is not solved, the script will abort the current page and move on.
- **Rate Limiting:** It is highly recommended to run this script sparingly (e.g., once or twice a day) rather than back-to-back to prevent IP blacklisting.

### 2. Search Result Accuracy & Structure
- **Fuzzy Fallback:** Google doesn't always perform exact string matches, even when passing keywords in quotes. The scraper introduces a `rapidfuzz` fallback mechanism to catch minor spelling differences or omitted spaces, ensuring accurate categorization.
- **Incomplete Snippets:** The tool scrapes the visible text snippet provided by the Google search result card to determine keyword presence. If Google truncates the text in the snippet before mentioning the target, the script might misclassify or drop the result. 
- **Redirect Links:** Google wraps destination URLs in their own redirection format (`/url?q=...`). The script parses these to extract the true URL, but any changes by Google to this routing structure could break the link extraction process.

### 3. Date Parsing Reliability
- **Vague Publishing Dates:** LinkedIn and Google rarely provide exact timestamps in the search snippet (e.g., "3 days ago", "1mo"). The script intelligently estimates the actual timestamp based on when the script executes, but this is an approximation and will not be down to the minute.
- **Date Filtering:** The `&tbs=qdr:m6` parameter restricts Google to results indexed within the last 6 months. However, Google's indexing timeline does not always perfectly align with LinkedIn's actual publishing date.

### 4. DOM Changes
- **Fragile Selectors:** The HTML structure of Google Search results ('div.g', 'div.tF2Cxc', '#search') frequently changes as Google A/B tests new layouts. If Google pushes an update to their CSS class names, the BeautifulSoup parsers in this script will need to be updated accordingly.

## Best Practices for Usage
1. Keep the browser window minimized or untouched while it runs to avoid interrupting the automated scrolling.
2. Ensure you have a stable internet connection so the explicit waits (`WebDriverWait`) do not time out prematurely.
3. If you repeatedly encounter CAPTCHAs, wait an hour or connect to a completely different network (like a Mobile Hotspot) to obtain a fresh IP address before retrying.
