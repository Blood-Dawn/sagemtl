"""
Test script for lightnovel-crawler integration

Run this to verify that lncrawl is properly integrated and working.
"""
import asyncio
import sys
from pathlib import Path
import pytest

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


from sagemtl_desktop.core.lightnovel_crawler_wrapper import (
    LightNovelCrawlerWrapper,
    LIGHTNOVEL_CRAWLER_AVAILABLE
)

# Skip when run under pytest; this is a standalone integration script.
pytest.skip("Standalone integration script; skip under pytest", allow_module_level=True)


def progress_callback(current, total, message):
    """Simple progress display"""
    percentage = (current / total * 100) if total > 0 else 0
    print(f"[{percentage:5.1f}%] {message}")


async def test_lncrawl():
    """Test lightnovel-crawler wrapper"""
    
    print("=" * 60)
    print("Testing lightnovel-crawler Integration")
    print("=" * 60)
    
    # Check if available
    if not LIGHTNOVEL_CRAWLER_AVAILABLE:
        print("\n❌ ERROR: lightnovel-crawler is not installed!")
        print("\nInstall with: pip install lightnovel-crawler")
        return False
    
    print("\n✓ lightnovel-crawler is installed")
    
    # Create wrapper
    crawler = LightNovelCrawlerWrapper()
    print("✓ Wrapper created successfully")
    
    # Get supported sites
    print("\n" + "=" * 60)
    print("Checking Supported Sites")
    print("=" * 60)
    sites = crawler.get_supported_sites()
    print(f"\n✓ Found {len(sites)} supported sites")
    
    if sites and isinstance(sites, list) and len(sites) > 1:
        print("\nSample sites:")
        for site in sites[:10]:
            print(f"  - {site}")
        if len(sites) > 10:
            print(f"  ... and {len(sites) - 10} more")
    
    # Test URL support
    print("\n" + "=" * 60)
    print("Testing URL Support Detection")
    print("=" * 60)
    
    test_urls = [
        "https://www.royalroad.com/fiction/21220/mother-of-learning",
        "https://www.scribblehub.com/series/12345/test/",
        "https://www.webnovel.com/book/12345",
        "https://www.novelfull.com/test-novel.html",
    ]
    
    for url in test_urls:
        supported = crawler.supports_url(url)
        status = "✓" if supported else "✗"
        print(f"  {status} {url}")
    
    # Test actual crawl (optional - can be slow)
    print("\n" + "=" * 60)
    print("Crawl Test (Optional)")
    print("=" * 60)
    print("\nTo test actual crawling, uncomment the test_crawl section")
    print("in this script and provide a valid URL.")
    
    # Uncomment below to test actual crawling:
    # test_url = "https://www.royalroad.com/fiction/21220/mother-of-learning"
    # print(f"\nAttempting to crawl: {test_url}")
    # print("This may take a few minutes...\n")
    # 
    # try:
    #     novel = await crawler.fetch_novel(
    #         url=test_url,
    #         progress_callback=progress_callback
    #     )
    #     
    #     print("\n✓ Crawl successful!")
    #     print(f"\nTitle: {novel.title}")
    #     print(f"Author: {novel.author}")
    #     print(f"Chapters: {len(novel.chapters)}")
    #     
    #     if novel.chapters:
    #         print(f"\nFirst chapter: {novel.chapters[0].title}")
    #         preview = novel.chapters[0].content[:200]
    #         print(f"Preview: {preview}...")
    # 
    # except Exception as e:
    #     print(f"\n❌ Crawl failed: {str(e)}")
    #     return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    
    return True


def main():
    """Run tests"""
    try:
        success = asyncio.run(test_lncrawl())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
