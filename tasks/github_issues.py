import requests

GH_API = "https://api.github.com"
_GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def _headers(token: str) -> dict:
    return {**_GH_HEADERS, "Authorization": f"Bearer {token}"}

def create_issue(repo: str, title: str, body: str, labels: list[str], token: str) -> str:
    """Creates a GitHub Issue. Returns the issue HTML URL."""
    url = f"{GH_API}/repos/{repo}/issues"
    resp = requests.post(url, headers=_headers(token), json={"title": title, "body": body, "labels": labels})
    resp.raise_for_status()
    return resp.json()["html_url"]

def ensure_labels_exist(repo: str, labels: list[str], token: str) -> None:
    """Creates any labels that don't exist in the repo."""
    url = f"{GH_API}/repos/{repo}/labels"
    existing = {l["name"] for l in requests.get(url, headers=_headers(token)).json()}
    label_colors = {
        "marketing-agent": "0075ca",
        "seo":             "e4e669",
        "content":         "d93f0b",
        "social":          "5319e7",
        "conversion":      "0e8a16",
    }
    for label in labels:
        if label not in existing:
            resp = requests.post(
                url,
                headers=_headers(token),
                json={"name": label, "color": label_colors.get(label, "ededed")},
            )
            resp.raise_for_status()
