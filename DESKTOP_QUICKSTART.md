# SageMTL Desktop - Quick Start Guide

Get up and running with SageMTL Desktop in 5 minutes!

## Step 1: Install Dependencies (2 minutes)

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
# source .venv/bin/activate

# Install requirements
pip install -r requirements-desktop.txt
```

## Step 2: Install Translation Models (2 minutes)

```bash
# Install Chinese → English
python -c "import argostranslate.package; argostranslate.package.update_package_index(); pkg = [p for p in argostranslate.package.get_available_packages() if p.from_code == 'zh' and p.to_code == 'en'][0]; argostranslate.package.install_from_path(pkg.download())"

# Install Japanese → English
python -c "import argostranslate.package; argostranslate.package.update_package_index(); pkg = [p for p in argostranslate.package.get_available_packages() if p.from_code == 'ja' and p.to_code == 'en'][0]; argostranslate.package.install_from_path(pkg.download())"

# Install Korean → English
python -c "import argostranslate.package; argostranslate.package.update_package_index(); pkg = [p for p in argostranslate.package.get_available_packages() if p.from_code == 'ko' and p.to_code == 'en'][0]; argostranslate.package.install_from_path(pkg.download())"
```

## Step 3: Run the App (1 minute)

```bash
python -m sagemtl_desktop.main
```

## Quick Workflow Example

### Import and Process a Text File

1. **Launch the app**
   ```bash
   python -m sagemtl_desktop.main
   ```

2. **Import a file**
   - Click "📁 Import Files"
   - Select a `.txt` file with Chinese/Japanese/Korean text
   - File appears in left panel with ⏳ status

3. **Optional: Load glossary**
   - Click "📋 Load Glossary"
   - Select `sagemtl_desktop/resources/sample_glossary.csv`
   - Status shows "Glossary: sample_glossary.csv"

4. **Configure translation**
   - Source: Chinese (zh)
   - Target: English (en)

5. **Process**
   - Click "▶ Start Processing"
   - Watch progress in file list
   - View logs at bottom

6. **Preview results**
   - Click the file in the list
   - See original (left) and cleaned (right) text

7. **Export**
   - Click "💾 Export Results"
   - Select output folder
   - Get `filename_cleaned.txt`

### Fetch a Novel from URL

1. **Paste URL**
   ```
   https://example.com/novel/chapter-1
   ```

2. **Click "Fetch"**
   - Configure chapter range (e.g., 1-50)
   - Click OK

3. **Wait for download**
   - SageCrawler downloads and imports chapters automatically
   - App extracts chapters
   - Novel appears as ⏳ pending

4. **Process as normal**
   - Click "▶ Start Processing"
   - Translation runs
   - Export results

## Common Commands

```bash
# Run in development mode
python -m sagemtl_desktop.main

# Build standalone .exe
pyinstaller pyinstaller-desktop.spec

# Run built executable (Windows)
dist\SageMTL\SageMTL.exe

# Install additional language pack
python -c "import argostranslate.package; argostranslate.package.update_package_index(); pkg = [p for p in argostranslate.package.get_available_packages() if p.from_code == 'es' and p.to_code == 'en'][0]; argostranslate.package.install_from_path(pkg.download())"
```

## Sample Test File

Create `test.txt` with Chinese text:

```
这是一个测试文件。
修真者的道心非常重要。
宗主说："所有弟子都要努力修炼。"
师兄和师妹一起去了秘境。
```

Then:
1. Import `test.txt`
2. Load `sample_glossary.csv`
3. Process with Chinese → English
4. Export and view result

Expected output (with glossary applied):
```
This is a test file.
The Dao Heart of a Cultivation practitioner is very important.
The Sect Master said: "All disciples must work hard on their Cultivation."
Senior Brother and Junior Sister went to the secret realm together.
```

## Keyboard Shortcuts

- `Ctrl+O` - Import Files
- `Ctrl+E` - Export Results
- `Ctrl+Q` - Quit

## Troubleshooting

### App won't start
```bash
# Check Python version (must be 3.11+)
python --version

# Reinstall dependencies
pip install --force-reinstall -r requirements-desktop.txt
```

### No translation models
```bash
# List installed models
python -c "import argostranslate.package; print([f'{p.from_name} → {p.to_name}' for p in argostranslate.package.get_installed_packages()])"

# If empty, install models (see Step 2)
```

## Next Steps

- Read the full [README_DESKTOP.md](README_DESKTOP.md)
- Check the [DESKTOP_APP_ARCHITECTURE.md](DESKTOP_APP_ARCHITECTURE.md)
- Create your own glossary CSV
- Try fetching a novel from RoyalRoad or Webnovel

---

**Need help?** Open an issue at https://github.com/Blood-Dawn/sagemtl/issues
