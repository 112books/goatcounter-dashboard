import pytest
from unittest.mock import patch, MagicMock
from tasks.github_issues import create_issue, ensure_labels_exist

def test_create_issue_returns_url():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
    mock_resp.raise_for_status.return_value = None
    with patch("tasks.github_issues.requests.post", return_value=mock_resp) as mock_post:
        url = create_issue("owner/repo", "Test title", "Test body", ["seo"], "gh_token_xxx")
    assert url == "https://github.com/owner/repo/issues/1"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["title"] == "Test title"
    assert "seo" in call_kwargs.kwargs["json"]["labels"]

def test_create_issue_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    with patch("tasks.github_issues.requests.post", return_value=mock_resp):
        with pytest.raises(Exception, match="403"):
            create_issue("owner/repo", "Title", "Body", [], "bad_token")

def test_ensure_labels_exist_creates_missing_label():
    list_resp = MagicMock()
    list_resp.json.return_value = [{"name": "seo"}]
    list_resp.raise_for_status.return_value = None
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    with patch("tasks.github_issues.requests.get", return_value=list_resp):
        with patch("tasks.github_issues.requests.post", return_value=create_resp) as mock_post:
            ensure_labels_exist("owner/repo", ["seo", "marketing-agent"], "token")
    assert mock_post.call_count == 1  # only "marketing-agent" is missing
    assert mock_post.call_args.kwargs["json"]["name"] == "marketing-agent"
