"""`_extract_image` — RSS-dən şəkil çıxarma dəlikləri.

Hər test canlı feed-də ölçülmüş REAL bir haldan gəlir (uydurma deyil).
"""
from __future__ import annotations

from app.ingestion.rss_collector import _extract_image

JPG = "https://i-invdn-com.investing.com/news/LYNXMPEM5E15U_M.jpg"


def test_enclosure_mislabeled_as_html_is_accepted():
    """Investing RSS real .jpg-ni `text/html` kimi etiketləyir → əvvəl atılırdı."""
    entry = {
        "links": [
            {"rel": "enclosure", "type": "text/html; charset=utf-8", "href": JPG}
        ]
    }
    assert _extract_image(entry) == JPG


def test_enclosure_non_image_url_still_rejected():
    """MIME səhv olsa da, şəkil OLMAYAN enclosure götürülməməlidir."""
    entry = {
        "links": [
            {
                "rel": "enclosure",
                "type": "text/html",
                "href": "https://example.com/article.html",
            }
        ]
    }
    assert _extract_image(entry) is None


def test_media_thumbnail_used_when_media_content_has_no_url():
    """`or` listə səviyyəsində bağlanırdı → urlsuz media_content thumbnail-i öldürürdü."""
    entry = {
        "media_content": [{"medium": "video"}],  # url yoxdur
        "media_thumbnail": [{"url": "https://cdn.test/thumb.jpg"}],
    }
    assert _extract_image(entry) == "https://cdn.test/thumb.jpg"


def test_content_encoded_scanned_even_when_summary_truthy():
    """Mining.com: summary truthy olduğu üçün content:encoded heç vaxt skan olunmurdu."""
    entry = {
        "summary": "Qısa təsvir, şəkilsiz.",
        "content": [
            {"value": '<p>x</p><img src="https://www.mining.com/wp-content/a.jpg">'}
        ],
    }
    assert _extract_image(entry) == "https://www.mining.com/wp-content/a.jpg"


def test_single_quoted_and_lazy_src():
    entry = {"summary": "<img data-src='https://cdn.test/lazy.jpg' src='x.gif'>"}
    assert _extract_image(entry) == "https://cdn.test/lazy.jpg"


def test_srcset_first_candidate():
    entry = {
        "summary": '<img srcset="https://cdn.test/a.jpg 1x, https://cdn.test/b.jpg 2x">'
    }
    assert _extract_image(entry) == "https://cdn.test/a.jpg"


def test_protocol_relative_url_upgraded():
    entry = {"media_content": [{"url": "//cdn.test/photo.jpg"}]}
    assert _extract_image(entry) == "https://cdn.test/photo.jpg"


def test_data_uri_rejected():
    """OilPrice JSON-LD/lazy-load 1×1 placeholder-i data: URI-dir."""
    entry = {"summary": '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">'}
    assert _extract_image(entry) is None


def test_tracking_beacon_skipped():
    entry = {
        "summary": '<img src="https://www.facebook.com/tr?id=1&ev=PageView">'
        '<img src="https://cdn.test/real.jpg">'
    }
    assert _extract_image(entry) == "https://cdn.test/real.jpg"


def test_empty_entry_returns_none():
    assert _extract_image({}) is None


def test_precedence_media_beats_enclosure_and_body():
    """Bugünkü sıra qorunmalıdır — dəyişsə sınanmamış naşirlərdə regres olar."""
    entry = {
        "media_content": [{"url": "https://cdn.test/media.jpg"}],
        "links": [{"rel": "enclosure", "type": "image/jpeg", "href": JPG}],
        "summary": '<img src="https://cdn.test/body.jpg">',
    }
    assert _extract_image(entry) == "https://cdn.test/media.jpg"
