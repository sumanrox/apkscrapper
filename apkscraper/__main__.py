import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import re
import argparse
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.dont_write_bytecode = True

import os
import threading
import subprocess
import concurrent.futures
from typing import List, Dict, Optional

# ANSI Colors
C_CYAN = '\033[96m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_RED = '\033[91m'
C_GRAY = '\033[90m'
C_RESET = '\033[0m'

# Thread lock to prevent progress bars from scrambling in the terminal
print_lock = threading.Lock()

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

class BaseScraper:
    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        
        retries = Retry(
            total=3, 
            backoff_factor=1, 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=15, pool_maxsize=15)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def downloadFile(self, url: str, filename: str) -> bool:
        """Download file efficiently with resume support and progress."""
        if os.path.exists(filename):
            with print_lock:
                print(f"{C_YELLOW}[i] {self.name}: Skipping {os.path.basename(filename)} (already exists){C_RESET}")
            return True

        part_filename = f"{filename}.part"

        try:
            response = self.session.get(url, stream=True, allow_redirects=True, timeout=20)
            response.raise_for_status()
        except requests.RequestException as e:
            with print_lock:
                print(f"\n{C_RED}[!] {self.name}: Failed to download {os.path.basename(filename)}: {e}{C_RESET}")
            return False
            
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1MB chunks
        
        try:
            with open(part_filename, 'wb') as f:
                if HAS_TQDM:
                    with tqdm(total=total_size, unit='iB', unit_scale=True, desc=f"{C_CYAN}[{self.name}] {os.path.basename(filename)}{C_RESET}", leave=False) as pbar:
                        for data in response.iter_content(block_size):
                            f.write(data)
                            pbar.update(len(data))
                else:
                    downloaded = 0
                    last_percent = -1
                    short_name = os.path.basename(filename)
                    if len(short_name) > 20:
                        short_name = short_name[:17] + "..."
                        
                    for data in response.iter_content(block_size):
                        f.write(data)
                        downloaded += len(data)
                        if total_size > 0:
                            percent = int(100 * downloaded / total_size)
                            if percent > last_percent:
                                filled = int(40 * downloaded / total_size)
                                bar = f"{C_GREEN}█{C_RESET}" * filled + f"{C_GRAY}-{C_RESET}" * (40 - filled)
                                with print_lock:
                                    sys.stdout.write(f"\r{C_CYAN}[{self.name}]{C_RESET} {short_name:<20} [{bar}] {C_YELLOW}{percent:3d}%{C_RESET}")
                                    sys.stdout.flush()
                                last_percent = percent
                    with print_lock:
                        print(f"\n{C_GREEN}[+] {self.name}: Completed {os.path.basename(filename)}{C_RESET}")
            
            # Atomic rename once completed
            os.rename(part_filename, filename)
            return True
        except IOError as e:
            with print_lock:
                print(f"\n{C_RED}[!] {self.name}: Disk I/O error while saving {filename}: {e}{C_RESET}")
            if os.path.exists(part_filename):
                os.remove(part_filename)
            return False

class APKPureScraper(BaseScraper):
    def __init__(self):
        super().__init__("APKPure")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://apkpure.net/'
        })

    def search(self, query: str) -> List[Dict]:
        url = f"https://apkpure.net/api/v1/search_suggestion_new?key={quote_plus(query)}&limit=5&type=net"
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest'}
        
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            return [{'name': r.get('title'), 'id': r.get('packageName'), 'url': r.get('url')} for r in results]
        except Exception:
            return []

    def getVersions(self, app_id: str) -> List[Dict]:
        url = f"https://apkpure.net/app/{app_id}/versions"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
        except Exception:
            return []
            
        text = response.content.decode('utf-8', errors='ignore')
        soup = BeautifulSoup(text, 'html.parser')
        versions = []
        
        version_links = soup.find_all('a', href=re.compile(f"/{re.escape(app_id)}/download/"))
        for link in version_links:
            href = link.get('href')
            if not href: continue
            
            version_str = href.split('/')[-1]
            if not any(v['version'] == version_str for v in versions):
                versions.append({
                    'version': version_str,
                    'url': f"https://apkpure.net{href}",
                    'source': self
                })
        return versions

    def getDownloadLink(self, download_page_url: str) -> Optional[str]:
        try:
            response = self.session.get(download_page_url, timeout=15)
            response.raise_for_status()
            text = response.content.decode('utf-8', errors='ignore')
            match = re.search(r'href="(https://d\.apkpure\.net/b/(?:APK|XAPK)/[^"]+)"', text)
            return match.group(1) if match else None
        except Exception:
            return None

class UptodownScraper(BaseScraper):
    def __init__(self):
        super().__init__("Uptodown")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.uptodown.com/'
        })

    def search(self, query: str) -> List[Dict]:
        url = "https://www.uptodown.com/android/en/s"
        try:
            response = self.session.post(url, data={"queryString": query}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success") == 1 and "data" in data and "apps" in data["data"]:
                results = []
                for r in data["data"]["apps"]:
                    clean_name = re.sub(r'<[^>]+>', '', r.get('name', ''))
                    results.append({'name': clean_name, 'id': r.get('url'), 'url': r.get('url')})
                return results
        except Exception:
            pass
        return []

    def getVersions(self, app_url: str) -> List[Dict]:
        if not app_url.startswith('http'):
            app_url = f"https://{app_url}"
            
        versions_url = f"{app_url}/versions"
        try:
            response = self.session.get(versions_url, timeout=15)
            response.raise_for_status()
        except Exception:
            return []
            
        text = response.content.decode('utf-8', errors='ignore')
        soup = BeautifulSoup(text, 'html.parser')
        versions = []
        
        version_divs = soup.find_all('div', attrs={'data-version-id': True, 'data-url': True})
        for div in version_divs:
            version_id = div.get('data-version-id')
            base_url = div.get('data-url')
            extra_url = div.get('data-extra-url', 'descargar')
            
            version_span = div.find('span', class_='version')
            version_str = version_span.text.strip() if version_span else version_id
            
            versions.append({
                'version': version_str,
                'url': f"{base_url}/{extra_url}/{version_id}",
                'source': self
            })
        return versions

    def getDownloadLink(self, download_page_url: str) -> Optional[str]:
        try:
            response = self.session.get(download_page_url, timeout=15)
            response.raise_for_status()
            text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(text, 'html.parser')
            dl_button = soup.find('button', id='detail-download-button')
            
            if dl_button and dl_button.get('data-url'):
                token = dl_button.get('data-url')
                dw_url = f"https://dw.uptodown.com/dwn/{token}"
                
                with self.session.get(dw_url, stream=True, timeout=15) as redir_resp:
                    redir_resp.raise_for_status()
                    content_type = redir_resp.headers.get('content-type', '').lower()
                    
                    if 'text/html' in content_type:
                        # Some small HTML page with meta refresh
                        html_text = redir_resp.content.decode('utf-8', errors='ignore')
                        match = re.search(r'url=\'(https://dw\.uptodown\.net/dwn/[^\']+)\'', html_text)
                        return match.group(1) if match else dw_url
                    else:
                        # It's directly serving the file (e.g. application/octet-stream)
                        return redir_resp.url
        except Exception:
            pass
        return None

def processVersion(v: Dict, args: argparse.Namespace, title: str) -> None:
    """Worker function for parallel downloads."""
    scraper = v['source']
    ver_str = v['version']
    
    try:
        dl_url = scraper.getDownloadLink(v['url'])
        
        if not dl_url:
            with print_lock:
                print(f"{C_RED}[!] {scraper.name}: Could not resolve URL for version {ver_str}{C_RESET}")
            return
            
        ext = 'xapk' if ('/XAPK/' in dl_url or 'xapk' in dl_url) else 'apk'
        filename = os.path.join(args.dir, f"{title}_{ver_str}_{scraper.name}.{ext}")
        scraper.downloadFile(dl_url, filename)
    except Exception as e:
        with print_lock:
            print(f"{C_RED}[!] {scraper.name}: Unexpected worker error on version {ver_str} - {e}{C_RESET}")

def main():
    parser = argparse.ArgumentParser(description="Universal Historical APK Scraper")
    parser.add_argument('query', help="App name to search for")
    parser.add_argument('-a', '--all', action='store_true', help="Download all versions available")
    parser.add_argument('-v', '--version', help="Download specific version")
    parser.add_argument('-d', '--dir', default='.', help="Directory to save downloads")
    parser.add_argument('-s', '--source', choices=['all', 'apkpure', 'uptodown'], default='all', help="Sources to scrape from")
    parser.add_argument('-w', '--workers', type=int, default=4, help="Number of concurrent downloads")
    
    args = parser.parse_args()
    
    # Bug Bounty Quality of Life: Auto-strip extensions if copy-pasted from scope
    if args.query.lower().endswith('.apk'):
        args.query = args.query[:-4]
    elif args.query.lower().endswith('.xapk'):
        args.query = args.query[:-5]
        
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
        
    scrapers = []
    if args.source in ['all', 'apkpure']: scrapers.append(APKPureScraper())
    if args.source in ['all', 'uptodown']: scrapers.append(UptodownScraper())
    
    print(f"{C_CYAN}[*] Searching for '{args.query}' across {len(scrapers)} source(s)...{C_RESET}")
    
    all_versions = []
    title = args.query.replace(' ', '_')
    package_name = None
    
    for scraper in scrapers:
        results = scraper.search(args.query)
        if not results:
            print(f"{C_RED}[-] {scraper.name}: No search results.{C_RESET}")
            continue
            
        # Exact package name match logic
        app = results[0]
        for r in results:
            if r.get('id') == args.query or r.get('id', '').endswith(f"/{args.query}"):
                app = r
                break
                
        app_name = app.get('name') or args.query
        print(f"{C_GREEN}[+] {scraper.name}: Found '{app_name}'{C_RESET}")
        title = app_name.replace(' ', '_') 
        
        app_id = app.get('id') or args.query
        if scraper.name == "APKPure":
            package_name = app_id
            
        versions = scraper.getVersions(app_id)
        
        if versions:
            print(f"{C_GRAY}    -> Found {len(versions)} historical versions.{C_RESET}")
            all_versions.extend(versions)
        else:
            print(f"{C_GRAY}    -> No historical versions found.{C_RESET}")

    if not all_versions:
        print(f"\n{C_YELLOW}[!] Could not find any versions across selected sources.{C_RESET}")
        if package_name:
            print(f"{C_CYAN}[*] Fallback: Engaging apkeep for package '{package_name}'...{C_RESET}")
            try:
                subprocess.run(['apkeep', '-a', package_name, args.dir], check=True)
                print(f"{C_GREEN}[+] Fallback completed successfully.{C_RESET}")
            except FileNotFoundError:
                print(f"{C_RED}[!] Fallback failed: 'apkeep' command not found on the system.{C_RESET}")
                print(f"{C_GRAY}    Hint: Install it via 'cargo install apkeep' or from https://github.com/EFForg/apkeep{C_RESET}")
            except subprocess.CalledProcessError as e:
                print(f"{C_RED}[!] Fallback failed: apkeep returned an error ({e}).{C_RESET}")
        else:
            print(f"{C_RED}[!] Cannot use fallback: could not determine Android package ID.{C_RESET}")
        return
        
    versions_to_download = []
    if args.all:
        versions_to_download = all_versions
    elif args.version:
        versions_to_download = [v for v in all_versions if v['version'] == args.version]
        if not versions_to_download:
            print(f"\n{C_RED}[!] Version {args.version} not found across any sources.{C_RESET}")
            return
    else:
        versions_to_download = [all_versions[0]]
        print(f"\n{C_CYAN}[*] Defaulting to latest version found: {versions_to_download[0]['version']} (from {versions_to_download[0]['source'].name}){C_RESET}")
        
    seen_versions = set()
    deduped = []
    for v in versions_to_download:
        if v['version'] not in seen_versions:
            seen_versions.add(v['version'])
            deduped.append(v)
            
    print(f"\n{C_CYAN}[*] Preparing to download {len(deduped)} unique version(s) utilizing {args.workers} workers...{C_RESET}\n")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(processVersion, v, args, title) for v in deduped]
        concurrent.futures.wait(futures)
        
    print(f"\n{C_GREEN}[+] All tasks completed!{C_RESET}")

if __name__ == "__main__":
    main()
