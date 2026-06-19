# APKScraper

<p align="center">
  <img src="assets/banner.png" alt="APKScraper Banner" width="100%">
</p>

An enterprise-grade, multi-threaded, and fault-tolerant historical APK extraction pipeline designed for automated vulnerability research, patch diffing, and bug bounty recon.

APKScraper acts as a universal ingestion engine, aggregating historical application versions from multiple CDNs (APKPure, Uptodown) into a unified analysis pipeline.

## 🚀 Features

- **Multi-Source Aggregation**: Concurrently scrapes and dedupes version histories from both APKPure and Uptodown APIs.
- **Zero-RAM Streaming**: Downloads massive `1GB+` `.xapk` files safely using memory-efficient block streaming and atomic `.part` temporary files, eliminating corrupted partial downloads.
- **Exact Package Targeting**: Employs an exact-match override engine, ensuring searches for `com.google.android.youtube` strictly download the target package without hallucinating fuzzy matches.
- **Scope Sanitation**: Automatically strips `.apk` and `.xapk` extensions from queries, allowing you to directly copy-paste targets from HackerOne or Bugcrowd scopes.
- **Apkeep Failsafe**: Integrates natively with `apkeep` as an automated fallback mechanism if regional blocks or Play Store redirection policies hide the target from historical databases.
- **Thread-Safe UI**: Renders beautiful, concurrent ANSI progress bars without relying on external libraries like `tqdm` that struggle in strict externally-managed Linux environments.

## 📦 Requirements

- Python 3.8+
- `requests`
- `beautifulsoup4`
- Optional: [`apkeep`](https://github.com/EFForg/apkeep) (for fallback capabilities)

## 🛠️ Installation & Usage

Because it is built as a native Python module with a CLI entrypoint, you can install it directly to your system path:

```bash
pip install -e .
```

Once installed, you can execute it natively from anywhere on your system:

```bash
apkscraper <query> [options]
```

### 📖 Available Commands & Parameters

```text
usage: apkscraper [-h] [-a] [-v VERSION] [-d DIR] [-s {all,apkpure,uptodown}] [-w WORKERS]
                  query

Universal Historical APK Scraper

positional arguments:
  query                 App name or Exact Package ID to search for (e.g. com.google.android.youtube)

options:
  -h, --help            show this help message and exit
  -a, --all             Download all versions available
  -v, --version VERSION Download specific version
  -d, --dir DIR         Directory to save downloads (default: current directory)
  -s, --source {all,apkpure,uptodown}
                        Sources to scrape from (default: all)
  -w, --workers WORKERS Number of concurrent downloads (default: 4)
```

### Example Use Cases

**1. Download ALL Historical Versions (Default behavior)**
Search for an app by name or package ID and download all available historical versions across all sources.
```bash
apkscraper "youtube" --all
```

**2. Target Exact Package ID from a Bug Bounty Scope**
Directly copy-paste a package ID from a scope. The scraper will automatically strip the `.apk` and lock onto the exact package.
```bash
apkscraper "com.paypal.android.p2pmobile.apk" --all
```

**3. Download a Specific Version**
Only download a single, exact version of an app.
```bash
apkscraper "com.whatsapp" --version "2.24.12.78"
```

**4. Specify an Output Directory**
Route the downloaded APKs directly to your static-analysis pipeline directory.
```bash
apkscraper "youtube" --all --dir "/opt/analysis/jadx-worker/inbound"
```

**5. Adjust Concurrency Limits**
Increase or decrease the number of parallel worker threads fetching the APKs (Default is 4).
```bash
apkscraper "youtube" --all --workers 8
```

**6. Isolate a Specific CDN**
Only poll a specific source for historical versions instead of aggregating all of them.
```bash
apkscraper "youtube" --all --source uptodown
```

## 🧪 Running Tests

The package includes a comprehensive `unittest` TDD suite containing mocks for the network and file I/O operations.

```bash
python3 -m unittest apkscraper/tests/test_scraper.py
```
