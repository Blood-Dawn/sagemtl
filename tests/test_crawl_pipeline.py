from __future__ import annotations

from sagemtl.crawl.pipeline import CrawlOptions, crawl_html


HTML = """
<html lang="en">
  <body>
    <header>Ignore me</header>
    <article>
      <h1>Main title</h1>
      <p>Paragraph one.</p>
      <p class="ad">Advertisement</p>
      <p>Paragraph two.</p>
    </article>
  </body>
</html>
"""


def test_crawl_blocks_trim_boilerplate():
    result = crawl_html(HTML, source="test")
    texts = [block.text for block in result.blocks]
    assert "Advertisement" not in "\n".join(texts)
    assert texts[0] == "Main title"


def test_crawl_allow_selector_filters():
    options = CrawlOptions(allow_selectors=["article > p"], block_selectors=[".ad"])
    result = crawl_html(HTML, source="test", options=options)
    assert all(block.text.startswith("Paragraph") for block in result.blocks)
    assert len(result.blocks) == 2
