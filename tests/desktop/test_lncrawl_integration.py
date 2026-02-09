"""
Comprehensive integration tests for lncrawl workflow.

Tests the complete workflow:
1. Search for novel by name
2. Select from search results
3. Download first 10 chapters
4. Extract and verify chapter content

NOTE: These tests require:
- Active internet connection
- Working novel source websites
- The specific test novel to be available
- May take several minutes to complete

Run with: pytest tests/desktop/test_lncrawl_integration.py -v -s
Skip with: pytest -k "not lncrawl_integration"
"""

import pytest
import random

from sagemtl_desktop.core.lightnovel_crawler_wrapper import (
    LightNovelCrawlerWrapper,
    LIGHTNOVEL_CRAWLER_AVAILABLE
)

# Mark all tests in this module as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not LIGHTNOVEL_CRAWLER_AVAILABLE,
        reason="lightnovel-crawler not installed"
    )
]


@pytest.mark.skipif(
    not LIGHTNOVEL_CRAWLER_AVAILABLE,
    reason="lightnovel-crawler not installed"
)
class TestLightNovelCrawlerIntegration:
    """Integration tests for the complete lncrawl workflow"""

    @pytest.fixture
    def crawler(self):
        """Create a crawler instance"""
        return LightNovelCrawlerWrapper()

    @pytest.fixture
    def test_novel_name(self):
        """Novel name to search for"""
        return "Marvel: I am the leader of the mutant race"

    @pytest.mark.asyncio
    async def test_01_search_novel(self, crawler, test_novel_name):
        """Test searching for a novel by name"""
        print(f"\n[TEST] Searching for: {test_novel_name}")
        
        search_results = []
        progress_messages = []
        
        def progress_callback(current, total, message):
            progress_messages.append(message)
            print(f"  Progress: {message}")
        
        # Perform search
        search_results = await crawler.search_novel_by_name(
            test_novel_name,
            progress_callback
        )
        
        # Verify search returned results
        assert len(search_results) > 0, "Search should return at least one result"
        print(f"  ✓ Found {len(search_results)} results")
        
        # Verify progress messages were received
        assert len(progress_messages) > 0, "Should receive progress updates"
        print(f"  ✓ Received {len(progress_messages)} progress updates")
        
        # Verify result structure
        for result in search_results[:3]:  # Check first 3 results
            assert 'title' in result, "Result should have title"
            assert 'url' in result, "Result should have url"
            assert 'info' in result, "Result should have info"
            print(f"  ✓ {result['title'][:50]}... - {result['info']}")
        
        return search_results

    @pytest.mark.asyncio
    async def test_02_select_random_sites(self, crawler, test_novel_name):
        """Test selecting random sites from search results"""
        print("\n[TEST] Selecting random sites from search results")
        
        # Search first
        search_results = await crawler.search_novel_by_name(test_novel_name)
        assert len(search_results) >= 3, "Need at least 3 results for this test"
        
        # Select 3 random results
        selected_results = random.sample(search_results, min(3, len(search_results)))
        
        print(f"  ✓ Selected {len(selected_results)} random sites:")
        for i, result in enumerate(selected_results, 1):
            print(f"    {i}. {result['title']} - {result['info']}")
            print(f"       URL: {result['url']}")
        
        # Verify each selected result has required fields
        for result in selected_results:
            assert result['url'].startswith('http'), "URL should be valid"
            assert len(result['title']) > 0, "Title should not be empty"
        
        return selected_results

    @pytest.mark.asyncio
    async def test_03_download_first_10_chapters(self, crawler, test_novel_name):
        """Test downloading first 10 chapters from a novel"""
        print("\n[TEST] Downloading first 10 chapters")
        
        # Search and get first result
        search_results = await crawler.search_novel_by_name(test_novel_name)
        assert len(search_results) > 0, "Need at least one result"
        
        # Use first result for download test
        selected = search_results[0]
        print(f"  Selected: {selected['title']}")
        print(f"  URL: {selected['url']}")
        
        progress_messages = []
        
        def progress_callback(current, total, message):
            progress_messages.append(message)
            print(f"  Progress: {message}")
        
        # Download novel (limited to first 10 chapters)
        novel_data = await crawler.fetch_novel(
            selected['url'],
            progress_callback,
            max_chapters=10  # Limit to 10 chapters for testing
        )
        
        # Verify novel data structure
        assert novel_data is not None, "Should return novel data"
        assert hasattr(novel_data, 'title'), "Should have title"
        assert hasattr(novel_data, 'author'), "Should have author"
        assert hasattr(novel_data, 'chapters'), "Should have chapters"
        
        print(f"  ✓ Downloaded novel: {novel_data.title}")
        print(f"  ✓ Author: {novel_data.author}")
        print(f"  ✓ Chapters downloaded: {len(novel_data.chapters)}")
        
        # Verify we got chapters (should be <= 10)
        assert len(novel_data.chapters) > 0, "Should download at least one chapter"
        assert len(novel_data.chapters) <= 10, "Should not exceed 10 chapters"
        
        # Verify progress updates were received
        assert len(progress_messages) > 0, "Should receive progress updates"
        
        return novel_data

    @pytest.mark.asyncio
    async def test_04_extract_first_chapter(self, crawler, test_novel_name):
        """Test extracting and verifying first chapter content"""
        print("\n[TEST] Extracting first chapter")
        
        # Download novel first
        search_results = await crawler.search_novel_by_name(test_novel_name)
        selected = search_results[0]
        
        novel_data = await crawler.fetch_novel(selected['url'], max_chapters=10)
        
        # Get first chapter
        assert len(novel_data.chapters) > 0, "Should have at least one chapter"
        first_chapter = novel_data.chapters[0]
        
        # Verify chapter structure
        assert hasattr(first_chapter, 'title'), "Chapter should have title"
        assert hasattr(first_chapter, 'content'), "Chapter should have content"
        
        print(f"  ✓ First chapter title: {first_chapter.title}")
        print(f"  ✓ Content length: {len(first_chapter.content)} characters")
        
        # Verify content is not empty
        assert len(first_chapter.content) > 0, "Chapter content should not be empty"
        assert len(first_chapter.content) > 100, "Chapter should have substantial content"
        
        # Display first 500 characters as preview
        preview = first_chapter.content[:500].strip()
        print("\n  Preview (first 500 chars):")
        print(f"  {'-' * 60}")
        for line in preview.split('\n')[:10]:  # First 10 lines
            print(f"  {line}")
        if len(first_chapter.content) > 500:
            print(f"  ... ({len(first_chapter.content) - 500} more characters)")
        print(f"  {'-' * 60}")
        
        return first_chapter

    @pytest.mark.asyncio
    async def test_05_verify_all_chapters(self, crawler, test_novel_name):
        """Test that all downloaded chapters have valid content"""
        print("\n[TEST] Verifying all chapter content")
        
        # Download novel
        search_results = await crawler.search_novel_by_name(test_novel_name)
        selected = search_results[0]
        novel_data = await crawler.fetch_novel(selected['url'], max_chapters=10)
        
        print(f"  Total chapters to verify: {len(novel_data.chapters)}")
        
        for i, chapter in enumerate(novel_data.chapters, 1):
            # Verify each chapter has title and content
            assert hasattr(chapter, 'title'), f"Chapter {i} should have title"
            assert hasattr(chapter, 'content'), f"Chapter {i} should have content"
            assert len(chapter.title) > 0, f"Chapter {i} title should not be empty"
            assert len(chapter.content) > 0, f"Chapter {i} content should not be empty"
            
            print(f"  ✓ Chapter {i}: {chapter.title} ({len(chapter.content)} chars)")
        
        print(f"  ✓ All {len(novel_data.chapters)} chapters verified successfully")

    @pytest.mark.asyncio
    async def test_06_full_workflow(self, crawler, test_novel_name):
        """Test complete workflow: search -> select -> download -> extract"""
        print("\n[TEST] Running complete workflow test")
        
        # Step 1: Search
        print("\n  Step 1: Searching for novel...")
        search_results = await crawler.search_novel_by_name(test_novel_name)
        assert len(search_results) > 0, "Search failed"
        print(f"    ✓ Found {len(search_results)} results")
        
        # Step 2: Select random sites
        print("\n  Step 2: Selecting random sites...")
        num_to_select = min(3, len(search_results))
        selected_results = random.sample(search_results, num_to_select)
        print(f"    ✓ Selected {len(selected_results)} sites")
        for i, result in enumerate(selected_results, 1):
            print(f"      {i}. {result['title'][:50]}...")
        
        # Step 3: Pick one to download (first from random selection)
        print("\n  Step 3: Downloading from selected site...")
        chosen = selected_results[0]
        print(f"    Downloading from: {chosen['title']}")
        
        progress_count = {'value': 0}
        
        def progress_callback(current, total, message):
            progress_count['value'] += 1
        
        novel_data = await crawler.fetch_novel(
            chosen['url'],
            progress_callback,
            max_chapters=10
        )
        print(f"    ✓ Downloaded {len(novel_data.chapters)} chapters")
        print(f"    ✓ Received {progress_count['value']} progress updates")
        
        # Step 4: Extract first chapter
        print("\n  Step 4: Extracting first chapter...")
        first_chapter = novel_data.chapters[0]
        print(f"    ✓ Title: {first_chapter.title}")
        print(f"    ✓ Content: {len(first_chapter.content)} characters")
        
        # Step 5: Verify all chapters
        print("\n  Step 5: Verifying all chapters...")
        for i, chapter in enumerate(novel_data.chapters, 1):
            assert len(chapter.content) > 0, f"Chapter {i} has no content"
        print(f"    ✓ All {len(novel_data.chapters)} chapters verified")
        
        print("\n  ✓ COMPLETE WORKFLOW TEST PASSED")
        
        return {
            'search_results_count': len(search_results),
            'selected_sites': len(selected_results),
            'chapters_downloaded': len(novel_data.chapters),
            'novel_title': novel_data.title,
            'novel_author': novel_data.author,
            'first_chapter_title': first_chapter.title,
            'first_chapter_length': len(first_chapter.content)
        }

    def test_07_url_detection(self, crawler):
        """Test URL vs name detection"""
        print("\n[TEST] Testing URL detection")
        
        # Test URLs
        urls = [
            "https://example.com/novel/123",
            "http://site.com/book",
            "https://www.novelsite.org/title"
        ]
        
        for url in urls:
            assert crawler.is_url(url), f"Should detect {url} as URL"
            print(f"  ✓ Correctly identified as URL: {url}")
        
        # Test novel names
        names = [
            "Marvel: I am the leader of the mutant race",
            "My Novel Title",
            "Some Random Name"
        ]
        
        for name in names:
            assert not crawler.is_url(name), f"Should not detect {name} as URL"
            print(f"  ✓ Correctly identified as name: {name}")

    @pytest.mark.asyncio
    async def test_08_progress_callbacks(self, crawler, test_novel_name):
        """Test that progress callbacks are called during operations"""
        print("\n[TEST] Testing progress callbacks")
        
        callback_data = {
            'search_calls': 0,
            'download_calls': 0,
            'messages': []
        }
        
        # Test search callbacks
        def search_progress(current, total, message):
            callback_data['search_calls'] += 1
            callback_data['messages'].append(('search', message))
        
        print("  Testing search progress callbacks...")
        search_results = await crawler.search_novel_by_name(
            test_novel_name,
            search_progress
        )
        
        assert callback_data['search_calls'] > 0, "Search should trigger callbacks"
        print(f"    ✓ Search callbacks: {callback_data['search_calls']}")
        
        # Test download callbacks
        def download_progress(current, total, message):
            callback_data['download_calls'] += 1
            callback_data['messages'].append(('download', message))
        
        print("  Testing download progress callbacks...")
        selected = search_results[0]
        await crawler.fetch_novel(
            selected['url'],
            download_progress,
            max_chapters=10
        )
        
        assert callback_data['download_calls'] > 0, "Download should trigger callbacks"
        print(f"    ✓ Download callbacks: {callback_data['download_calls']}")
        print(f"    ✓ Total progress messages: {len(callback_data['messages'])}")


# Standalone test that can be run directly
if __name__ == "__main__":
    import asyncio
    
    async def run_manual_test():
        """Run a manual test of the workflow"""
        print("=" * 70)
        print("LNCRAWL INTEGRATION TEST")
        print("=" * 70)
        
        crawler = LightNovelCrawlerWrapper()
        test_novel = "Marvel: I am the leader of the mutant race"
        
        # Search
        print(f"\n1. Searching for: {test_novel}")
        results = await crawler.search_novel_by_name(test_novel)
        print(f"   Found {len(results)} results")
        
        # Select 3 random
        selected = random.sample(results, min(3, len(results)))
        print(f"\n2. Selected {len(selected)} random sites:")
        for i, r in enumerate(selected, 1):
            print(f"   {i}. {r['title']} - {r['info']}")
        
        # Download from first
        print(f"\n3. Downloading from: {selected[0]['title']}")
        novel = await crawler.fetch_novel(selected[0]['url'], max_chapters=10)
        print(f"   Title: {novel.title}")
        print(f"   Author: {novel.author}")
        print(f"   Chapters: {len(novel.chapters)}")
        
        # Show first chapter
        print(f"\n4. First chapter: {novel.chapters[0].title}")
        print(f"   Length: {len(novel.chapters[0].content)} characters")
        print("\n   Preview:")
        print("   " + "-" * 60)
        preview = novel.chapters[0].content[:500]
        for line in preview.split('\n')[:10]:
            print(f"   {line}")
        print("   " + "-" * 60)
        
        print("\n✓ Test completed successfully!")
    
    asyncio.run(run_manual_test())
