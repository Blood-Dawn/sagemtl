# SageMTL

**Offline Machine Translation Desktop Application for Web Novels**

A native desktop application for translating web novels (Chinese, Japanese, Korean → English) using offline translation models with custom glossary support and web novel crawling capabilities.

---

## 🌟 Features

### Core Translation
- **100% Offline Translation** - Uses Argos Translate with locally installed language models (no internet required after setup)
- **Custom Glossary Support** - CSV-based term replacement for character names, cultivation terms, etc.
  - Supports both `source,target` and `English,Chinese` column formats
  - Applied before translation for consistent terminology
- **Multiple Input Formats** - Import from TXT, EPUB, or crawl directly from URLs
- **Multiple Export Formats** - Save as TXT, EPUB, or Markdown

### Novel Crawling
- **Lightnovel-Crawler Integration** - Primary crawler with support for 460+ websites
- **SageCrawler** - Fallback crawler with automatic chapter pattern detection  
- **Wide Site Support** - Works with popular sites like Royal Road, Scribble Hub, WebNovel, WuxiaWorld, and 450+ more
- **Multiple Languages** - Supports English, Chinese, Japanese, Korean, Spanish, French, Indonesian sites
- **Automatic Chapter Detection** - Recognizes common URL patterns and site-specific structures
- **Smart Crawler Selection** - Automatically uses the best crawler for each site

### Desktop Experience
- **Native Qt Interface** - Built with PySide6 for responsive native performance
- **Side-by-Side Preview** - Original and translated text comparison
- **Real-time Progress** - Live job status with detailed logging
- **Batch Processing** - Queue multiple files or URLs for translation
- **Content Deduplication** - Automatic detection of duplicate imports using content hashing

---

## 📋 Requirements

- **Python 3.11+** (3.13 recommended for latest datetime features)
- **Operating Systems**: Windows, macOS, Linux
- **Disk Space**: ~500MB for base models (Chinese), ~1GB+ for multiple languages

---

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   ```powershell
   git clone https://github.com/Blood-Dawn/sagemtl.git
   cd sagemtl
   ```

2. **Set up Python environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements-desktop.txt
   ```

4. **Install translation models**
   ```python
   python -c "import argostranslate.package; argostranslate.package.update_package_index(); available = argostranslate.package.get_available_packages(); chinese = next((p for p in available if p.from_code == 'zh' and p.to_code == 'en'), None); argostranslate.package.install_from_path(chinese.download())"
   ```
   
   For additional languages (Japanese, Korean):
   ```python
   # Japanese
   python -c "import argostranslate.package; argostranslate.package.update_package_index(); available = argostranslate.package.get_available_packages(); japanese = next((p for p in available if p.from_code == 'ja' and p.to_code == 'en'), None); argostranslate.package.install_from_path(japanese.download())"
   
   # Korean
   python -c "import argostranslate.package; argostranslate.package.update_package_index(); available = argostranslate.package.get_available_packages(); korean = next((p for p in available if p.from_code == 'ko' and p.to_code == 'en'), None); argostranslate.package.install_from_path(korean.download())"
   ```

5. **Launch the application**
   ```powershell
   python -m sagemtl_desktop.main
   ```

---

## 📖 Usage Examples

### Workflow 1: Translate Local Files

1. Launch the app: `python -m sagemtl_desktop.main`
2. Click **"Import Files"** → Select your TXT/EPUB files
3. (Optional) Load glossary: **"Load Glossary"** → Select CSV file
4. Select files from the list → Click **"Translate"**
5. Monitor progress in the logs panel
6. Click **"Export"** → Choose format (TXT/EPUB/Markdown) and save location

### Workflow 2: Crawl and Translate Web Novels

1. Launch the app
2. Click **"Fetch from URL"**
3. Enter novel URL (e.g., `https://example.com/novel/chapter-1`)
4. Wait for automatic chapter detection and download
5. (Optional) Load glossary for consistent terminology
6. Click **"Translate"** on the imported content
7. Export when complete

### Glossary Format

Create a CSV file with one of these formats:

**Format 1: source/target columns**
```csv
source,target
道,Dao
修真,Cultivation
金丹,Golden Core
```

**Format 2: English/Chinese columns**
```csv
English,Chinese
Dao,道
Cultivation,修真
Golden Core,金丹
```

The app automatically detects which format you're using.

---

## 🏗️ Architecture

### Directory Structure

```
sagemtl/
├── sagemtl_desktop/          # Desktop application
│   ├── main.py              # Application entry point
│   ├── core/                # Business logic
│   │   ├── epub_extractor.py    # EPUB text extraction
│   │   ├── glossary.py          # Glossary term replacement
│   │   ├── import_manager.py   # Content deduplication
│   │   ├── job_manager.py       # Background job orchestration
│   │   └── translator.py        # Argos Translate integration
│   ├── ui/                  # PySide6 GUI components
│   │   ├── main_window.py       # Main application window
│   │   └── ...
│   └── resources/           # Icons, stylesheets
│
├── sagemtl/                 # Core library (reusable)
│   ├── crawl/              # Web crawling
│   │   └── novel_crawler.py     # SageCrawler implementation
│   ├── translate/          # Translation pipeline
│   ├── clean/              # Text normalization
│   └── jobs/               # Job state management
│
├── tests/                   # Test suite
├── requirements-desktop.txt # Desktop dependencies
└── pyinstaller-desktop.spec # Build configuration
```

### Tech Stack

- **UI Framework**: PySide6 (Qt6) - Native desktop widgets
- **Translation**: Argos Translate - Offline neural translation models
- **Crawling**: httpx (async HTTP) + BeautifulSoup4 (HTML parsing)
- **EPUB Processing**: zipfile + xml.etree.ElementTree + ebooklib
- **Job Management**: Threading + custom job queue system
- **Testing**: pytest + pytest-asyncio

---

## 🔨 Building Executables

To create standalone executables:

```powershell
# Install PyInstaller
pip install pyinstaller

# Build executable (uses pyinstaller-desktop.spec)
pyinstaller pyinstaller-desktop.spec

# Output: dist/SageMTL-Desktop/SageMTL-Desktop.exe
```

The executable bundles Python runtime and dependencies but **does not include translation models**. Users must still install Argos Translate models on first run.

---

## 🌐 Supported Languages

### Translation Directions
- Chinese (Simplified/Traditional) → English
- Japanese → English  
- Korean → English

### Novel Sources
- Direct URL crawling: Works with any site that has sequential chapter URLs
- Automatic pattern detection for common chapter numbering schemes
- Supports popular sites including NovelUpdates, WuxiaWorld, RoyalRoad, ScribbleHub, and many more

---

## 🧪 Running Tests

```powershell
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test file
pytest tests/test_novel_crawler.py

# Run with verbose output
pytest -v
```

---

## 📚 Documentation

- **[DESKTOP_QUICKSTART.md](DESKTOP_QUICKSTART.md)** - 5-minute setup guide with workflow examples
- **[README_DESKTOP.md](README_DESKTOP.md)** - Complete desktop app documentation
- **[DESKTOP_APP_ARCHITECTURE.md](DESKTOP_APP_ARCHITECTURE.md)** - Technical architecture deep dive

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Support & Contributing

- **Issues**: [GitHub Issues](https://github.com/Blood-Dawn/sagemtl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Blood-Dawn/sagemtl/discussions)
- **Author**: Blood-Dawn

---

## 💡 Inspiration

This project was inspired by and builds upon ideas from:
- **[lightnovel-crawler](https://github.com/lncrawl/lightnovel-crawler)** (GPL v3) - Primary crawler with 460+ supported sites. Developed by the lncrawl team and contributors. Provides robust chapter extraction and wide site compatibility.
- **Argos Translate** - Open-source offline neural machine translation

---

## Crawler Options

SageMTL offers two crawler backends to fetch web novels:

### SageCrawler (Built-in)
Our native crawler uses intelligent pattern detection to work with a wide variety of novel sites. It automatically recognizes common chapter URL patterns and adapts to different site structures.

- **License**: MIT (same as SageMTL)
- **Best for**: General use, sites with standard chapter numbering
- **Setup**: No additional installation needed

### LightNovel-Crawler Integration (Recommended)
For maximum site compatibility, SageMTL integrates with [lightnovel-crawler](https://github.com/lncrawl/lightnovel-crawler), an excellent open-source project that supports **460+ web novel sites** across multiple languages.

- **License**: GPL v3 (separate component)
- **Supported Sites**: 460+ including Royal Road, Scribble Hub, WebNovel, WuxiaWorld, NovelFull, and more
- **Languages**: English, Chinese, Japanese, Korean, Spanish, French, Indonesian, and more
- **Setup**: Already included in `requirements-desktop.txt`
- **Attribution**: This integration uses lightnovel-crawler as a library dependency. lightnovel-crawler is developed by the lncrawl team and contributors. See their [repository](https://github.com/lncrawl/lightnovel-crawler) for full details.

### SageCrawler (Built-in Fallback)
Our native crawler uses intelligent pattern detection to work with sites not supported by lightnovel-crawler.

- **License**: MIT (same as SageMTL)
- **Best for**: General use, sites with standard chapter numbering, fallback option
- **Setup**: No additional installation needed

The integration maintains license compliance by using lightnovel-crawler as a separate library dependency rather than incorporating its code into SageMTL. You can use SageMTL with either crawler or both.

### Choosing a Crawler

The app automatically selects the best crawler for your URL:
- **LightNovel-Crawler** is preferred by default (460+ sites supported)
- **SageCrawler** is used as fallback when needed
- You can change the preference in Settings

Both crawlers work seamlessly within the app - the choice is transparent to you.

## Acknowledgments

This project integrates with or was inspired by:

- **[lightnovel-crawler](https://github.com/lncrawl/lightnovel-crawler)** (GPL v3) - Primary crawler integration for enhanced site support (460+ sites). Developed by the lncrawl team and contributors.
- **Argos Translate** - Open-source offline neural machine translation

## License

1. **First Launch**: Translation models (~500MB+) must be downloaded before first use
2. **Offline Mode**: Once models are installed, the app works 100% offline
3. **Translation Quality**: Argos Translate provides functional translations but may not match commercial services
4. **Glossary**: Custom glossaries significantly improve consistency for domain-specific terms
5. **EPUB Support**: Both import (extraction) and export (creation) are supported
6. **Content Hashing**: Duplicate content is automatically detected to prevent re-importing the same files

---

**Version**: 0.0.1  
**Last Updated**: 2025
