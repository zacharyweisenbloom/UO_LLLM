import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import time
import re

import argparse

base_url = "https://uoregon.edu"
def crawl_uoregon(start_url="https://uoregon.edu", delay=0.0, max_pages=5000000000000000):
    visited = set()
    to_visit = [start_url]
    with open("uoregon_urls_test.txt", "w") as f:
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop()
            if current_url in visited:
                    continue

            try: 
                print(f"Crawling: {current_url}") 
                response = requests.get(current_url, timeout=5)

                if response.status_code != 200:
                    print(f"Failed to retrieve {current_url}: {response.status_code}")
                    continue

                visited.add(current_url)
                f.write(current_url + "\n")  # Save the URL to the file
                f.flush()
                soup = BeautifulSoup(response.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(current_url, href)
                    norm_url = normalize_url(full_url)  # Normalize by removing fragment
                    
                    # Check if the URL is valid and belongs to uoregon.edu
                    if is_valid_url(norm_url) and (norm_url not in visited) and (norm_url not in to_visit):
                        to_visit.append(norm_url)

                #time.sleep(delay)  # Respectful crawling delay 
            except Exception as e:
                print(f"Error crawling {current_url}: {e}")
                continue
    return visited

def is_valid_url(url):
    parsed = urlparse(url)
    REPEATED_SEGMENT = re.compile(r'(?:^|/)([^/]+)/\1(/|$)')
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname  # guards against mailto:, javascript:, etc.
        and parsed.hostname.endswith("uoregon.edu")
        and parsed.hostname != "pages.uoregon.edu"
        and not any(parsed.path.endswith(ext) for ext in [".pdf", ".xml", ".jpg", ".jpeg", ".png", ".gif"])
        and not re.search(REPEATED_SEGMENT, parsed.path)  # Avoid repeated segments like /foo/bar/foo
    )

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


def main():
    parser = argparse.ArgumentParser(description="Crawl University of Oregon website and save URLs.")

    print("Starting crawl...")
    urls = crawl_uoregon()
    print(f"Crawled {len(urls)} pages.")
    
    print("Crawl complete. URLs saved to uoregon_urls.txt.")

if __name__ == "__main__":
    main()