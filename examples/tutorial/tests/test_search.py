from html.parser import HTMLParser

import pytest

from flaskr.db import get_db


class SearchPage(HTMLParser):
    """Inspect rendered controls and post titles without extra dependencies."""

    def __init__(self, response):
        super().__init__()
        self.titles = []
        self.inputs = []
        self.links = []
        self.labels = []
        self.forms = []
        self._in_title = False
        self._in_post = False
        self.feed(response.get_data(as_text=True))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "post" in attrs.get("class", "").split():
            self._in_post = True
        if tag == "h1" and self._in_post:
            self._in_title = True
        if tag == "input":
            self.inputs.append(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "label":
            self.labels.append(attrs.get("for"))
        if tag == "form":
            self.forms.append(attrs)

    def handle_endtag(self, tag):
        if tag == "article":
            self._in_post = False
        if tag == "h1":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.titles.append(data)


@pytest.fixture
def search_posts(app):
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM post")
        db.executemany(
            "INSERT INTO post (id, author_id, title, body, created)"
            " VALUES (?, 1, ?, ?, ?)",
            [
                (1, "Purdue Study Tips", "Review notes.", "2026-01-01 12:00:00"),
                (2, "Weekend Plans", "Practice guitar.", "2026-01-02 12:00:00"),
                (3, "Favorite Foods", "Parmesan potatoes.", "2026-01-02 12:00:00"),
            ],
        )
        db.commit()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Purdue", "Purdue Study Tips"),
        ("guitar", "Weekend Plans"),
        ("GuItAr", "Weekend Plans"),
        ("  guitar  ", "Weekend Plans"),
    ],
)
def test_search_matches(client, search_posts, query, expected):
    response = client.get("/", query_string={"q": query})
    assert response.status_code == 200
    page = SearchPage(response)
    assert page.titles == [expected]
    field = next(field for field in page.inputs if field.get("name") == "q")
    assert field["value"] == query.strip()


@pytest.mark.parametrize("query", [None, "", " \t\n "])
def test_empty_query_and_ordering(client, search_posts, query):
    response = client.get("/", query_string={} if query is None else {"q": query})
    assert SearchPage(response).titles == [
        "Favorite Foods", "Weekend Plans", "Purdue Study Tips"
    ]
    field = next(f for f in SearchPage(response).inputs if f.get("name") == "q")
    assert field["value"] == ""


def test_filtered_ordering(client, search_posts):
    # "e" occurs in all three titles or bodies, including two timestamp ties.
    response = client.get("/", query_string={"q": "e"})
    assert SearchPage(response).titles == [
        "Favorite Foods", "Weekend Plans", "Purdue Study Tips"
    ]


def test_no_results(client, search_posts):
    response = client.get("/", query_string={"q": "zzzznonexistent"})
    assert SearchPage(response).titles == []
    assert b"No posts found." in response.data
    assert b"No posts yet." not in response.data


def test_empty_blog(app, client):
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM post")
        db.commit()
    assert b"No posts yet." in client.get("/").data
    assert b"No posts found." in client.get("/", query_string={"q": "guitar"}).data


@pytest.mark.parametrize("query", ["%", "_", "'", '"', "\\", "' OR 1=1 --"])
def test_literal_characters(app, client, search_posts, query):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO post (author_id, title, body) VALUES (1, ?, ?)",
            ("Literal match", f"Before {query} after"),
        )
        db.commit()
    response = client.get("/", query_string={"q": query})
    assert SearchPage(response).titles == ["Literal match"]


def test_query_is_escaped(client):
    query = '\"><script>alert(1)</script>'
    response = client.get("/", query_string={"q": query})
    assert b"<script>" not in response.data
    assert b"&lt;script&gt;" in response.data
    field = next(f for f in SearchPage(response).inputs if f.get("name") == "q")
    assert field["value"] == query


def test_accessible_form_and_clear_link(client, search_posts):
    response = client.get("/", query_string={"q": "guitar"})
    page = SearchPage(response)
    field = next(f for f in page.inputs if f.get("name") == "q")
    assert field["type"] == "search"
    assert field["id"] in page.labels
    assert any(
        f.get("role") == "search" and f.get("method") == "get" and f.get("action") == "/"
        for f in page.forms
    )
    assert "/" in page.links
    assert b">Clear</a>" in response.data
    assert len(SearchPage(client.get("/")).titles) == 3


def test_search_preserves_author_permissions(app, client, auth, search_posts):
    with app.app_context():
        db = get_db()
        db.execute("UPDATE post SET author_id = 2 WHERE id = 2")
        db.commit()
    auth.login()
    response = client.get("/", query_string={"q": "guitar"})
    assert b"Weekend Plans" in response.data
    assert b'href="/2/update"' not in response.data
    assert client.post("/2/update", data={"title": "changed", "body": ""}).status_code == 403
    assert client.post("/2/delete").status_code == 403
