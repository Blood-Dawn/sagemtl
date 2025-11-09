# SageMTL Desktop - Offline MTL Novel Processor

A Windows desktop application for processing bulk machine-translated (MTL) novel text and rewriting it into fluent English. Runs completely offline with bundled translation models.

## Features

✅ **Fully Offline** - No cloud calls, all processing happens locally
✅ **Argos Translate** - Open-source offline translation engine
✅ **Novel Crawling** - Fetch novels from URLs using SageCrawler
✅ **Custom Glossary** - Apply CSV glossary for consistent terminology
✅ **EPUB Support** - Import and extract EPUB files
✅ **Side-by-Side Preview** - View original and cleaned text
✅ **Batch Processing** - Process multiple files at once
✅ **Error Tracking** - Detailed logs with interactive error viewing
✅ **One-Click Export** - Export cleaned text files

## Installation

### Prerequisites

- Python 3.11 or higher
- Windows 10/11 (primary target, but cross-platform capable)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Blood-Dawn/sagemtl.git
   cd sagemtl
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # source .venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements-desktop.txt
   ```

4. **Install Argos Translate language packs:**
   ```python
   python -c "
   import argostranslate.package
   argostranslate.package.update_package_index()
   available = argostranslate.package.get_available_packages()

   # Install Chinese -> English
   pkg = [p for p in available if p.from_code == 'zh' and p.to_code == 'en'][0]
   argostranslate.package.install_from_path(pkg.download())

   # Install Japanese -> English
   pkg = [p for p in available if p.from_code == 'ja' and p.to_code == 'en'][0]
   argostranslate.package.install_from_path(pkg.download())

   # Install Korean -> English
   pkg = [p for p in available if p.from_code == 'ko' and p.to_code == 'en'][0]
   argostranslate.package.install_from_path(pkg.download())
   "
   ```

## Running the App

### Development Mode

```bash
python -m sagemtl_desktop.main
```

### Building Executable

To create a standalone .exe for distribution:

```bash
# Install language packs first (see step 4 above)
pyinstaller pyinstaller-desktop.spec
```

The built application will be in `dist/SageMTL/`

## Usage Guide

### 1. Import Files

**Option A: Import Local Files**
- Click "📁 Import Files" button
- Select `.txt` or `.epub` files
- Files will appear in the left panel with "⏳" (pending) status

**Option B: Fetch from URL**
- Paste novel URL in the "Fetch Novel from URL" field
- Click "Fetch"
- Configure chapter range in the dialog
- SageCrawler will automatically detect chapters and download them

### 2. Load Glossary (Optional)

Create a CSV file with your custom terminology:

```csv
source,target,case_sensitive,word_boundary,notes
"Sect Master","Patriarch",true,false,"Title"
"dao heart","resolve",true,false,"Cultivation term"
"Junior Sister","Little Sis",false,false,"Relationship"
"Heavenly Dao","World Will",true,true,"Concept"
```

Then:
- Click "📋 Load Glossary"
- Select your CSV file
- Glossary will be applied before AND after translation

### 3. Configure Translation

- **Source Language**: Select source language (Chinese, Japanese, Korean, etc.) or "Auto-detect"
- **Target Language**: Select target language (default: English)

### 4. Process Files

- Click "▶ Start Processing"
- Watch progress in the file list (shows percentage)
- View logs in the bottom panel
- Status indicators:
  - ⏳ Pending
  - ⟳ In Progress
  - ✓ Completed
  - ✗ Failed

### 5. Preview Results

- Click any file in the left panel
- View original text (left) and cleaned text (right) side-by-side
- Double-click failed jobs to view detailed error traceback

### 6. Export Results

- Click "💾 Export Results"
- Select output directory
- All completed files will be saved as `filename_cleaned.txt`

## Glossary System

The glossary system applies replacements in two passes:

### Before Translation
Fixes known MTL fragments and preserves special terms before translation:
- Character names
- Cultivation realms/techniques
- Special terminology

### After Translation
Fixes awkward output from the translation model:
- Standardizes terminology
- Fixes capitalization
- Enforces consistent style

### CSV Format

```csv
source,target,case_sensitive,word_boundary,notes
```

- **source**: Text to find
- **target**: Replacement text
- **case_sensitive**: `true` or `false` (default: `true`)
- **word_boundary**: `true` or `false` (default: `false`)
  - If `true`, only matches whole words (e.g., "Sect" won't match "Section")
- **notes**: Optional description

## Translation Pipeline

For each file, the app follows this pipeline:

```
1. Read original text
   ↓
2. Apply glossary (before) → Fix MTL fragments
   ↓
3. Translate with Argos → Chinese/Japanese/Korean → English
   ↓
4. Apply glossary (after) → Standardize terminology
   ↓
5. Save as cleaned text
```

## Architecture

```
sagemtl_desktop/
├── core/                      # Backend logic
│   ├── models.py              # Data models
│   ├── job_manager.py         # Job queue with threading
│   ├── translator.py          # Argos Translate wrapper
│   ├── glossary.py            # CSV glossary processor
│   ├── crawler.py             # SageCrawler wrapper
│   ├── epub_extractor.py      # EPUB parsing
│   └── exporter.py            # Export cleaned text
│
├── ui/                        # PySide6 UI components
│   ├── main_window.py         # Main application window
│   ├── file_list_panel.py     # Job list with status
│   ├── preview_panel.py       # Side-by-side preview
│   ├── controls_panel.py      # Controls and settings
│   ├── log_panel.py           # Log viewer
│   └── dialogs.py             # Dialogs (error, crawl options, about)
│
├── resources/                 # Icons, styles, bundled models
└── main.py                    # Entry point
```

## Technical Details

### Translation Engine

- **Argos Translate**: Open-source neural machine translation
- **Offline Models**: Pre-bundled language packs (Chinese, Japanese, Korean → English)
- **Chunking**: Splits long text into sentences to avoid token limits
- **Progress Tracking**: Real-time progress updates during translation

### Novel Crawling

- **SageCrawler**: Built-in novel crawler with automatic chapter pattern detection
- **Wide Compatibility**: Works with many popular novel sites through intelligent pattern matching
- **Text Output**: Downloads chapters directly as text
- **Error Handling**: Captures and displays crawler output/errors

### Job System

- **Threading**: Each job runs in a background QThread
- **Qt Signals**: UI updates via signal/slot mechanism (no UI blocking)
- **Status Tracking**: Pending → In Progress → Completed/Failed
- **Error Recovery**: Failed jobs show detailed traceback

### Packaging

- **PyInstaller**: One-folder distribution
- **Bundled Models**: Argos language packs included in .exe
- **No Dependencies**: End users don't need Python installed

## Troubleshooting

### Argos Translate not available

**Error**: `Argos Translate is not installed`

**Solution**:
```bash
pip install argostranslate
```

### No translation model for language pair

**Error**: `No translation model for zh→en`

**Solution**: Install the language pack:
```python
import argostranslate.package
argostranslate.package.update_package_index()
available = argostranslate.package.get_available_packages()
pkg = [p for p in available if p.from_code == 'zh' and p.to_code == 'en'][0]
argostranslate.package.install_from_path(pkg.download())
```

### EPUB extraction failed

**Error**: `Not a valid EPUB: META-INF/container.xml not found`

**Solution**: Ensure the file is a valid EPUB. Try opening it in Calibre or another EPUB reader first.

### Slow translation

**Cause**: Argos Translate runs on CPU by default.

**Solution**: Argos can use GPU if available. Install with CUDA support for faster translation (requires NVIDIA GPU).

## Sample Glossary

Create a file `glossary.csv`:

```csv
source,target,case_sensitive,word_boundary,notes
"修真","Cultivation",true,false,"Core concept"
"师兄","Senior Brother",true,false,"Relationship"
"师姐","Senior Sister",true,false,"Relationship"
"师弟","Junior Brother",true,false,"Relationship"
"师妹","Junior Sister",true,false,"Relationship"
"宗主","Sect Master",true,false,"Title"
"长老","Elder",true,false,"Title"
"掌门","Sect Leader",true,false,"Title"
"道心","Dao Heart",true,false,"Cultivation term"
"天道","Heavenly Dao",true,false,"Concept"
"元神","Primordial Spirit",true,false,"Cultivation term"
"金丹","Golden Core",true,false,"Cultivation stage"
"元婴","Nascent Soul",true,false,"Cultivation stage"
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black sagemtl_desktop/
ruff check sagemtl_desktop/
```

### Building for Release

1. Ensure all language packs are installed
2. Test thoroughly in development mode
3. Build with PyInstaller:
   ```bash
   pyinstaller pyinstaller-desktop.spec
   ```
4. Test the built executable in `dist/SageMTL/`
5. Distribute the entire `SageMTL` folder

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Acknowledgments

- **Argos Translate**: Open-source neural translation
- **PySide6**: Qt for Python

## Support

- **Issues**: https://github.com/Blood-Dawn/sagemtl/issues
- **Discussions**: https://github.com/Blood-Dawn/sagemtl/discussions

---

**Note**: This is a complete rewrite of the sageMTL app as a native Windows desktop application. The previous web-based UI has been replaced with a PySide6 (Qt) desktop interface.
