import base64
import ipaddress
import mimetypes
import re
import socket
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    clean = text.replace("\r", "\n")
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    return clean.strip()


def _is_public_ip(ip_text: str) -> bool:
    ip = ipaddress.ip_address(ip_text)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.netloc:
        raise ValueError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("Authenticated URLs are not allowed")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname in BLOCKED_HOSTS:
        raise ValueError("URL hostname is not allowed")

    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)}
    except socket.gaierror as exc:
        raise ValueError("Unable to resolve URL hostname") from exc

    if not resolved or any(not _is_public_ip(ip) for ip in resolved):
        raise ValueError("URL resolves to a non-public address")

    return parsed.geturl()


def extract_web_content(url: str, timeout_seconds: int = 15) -> Dict[str, str]:
    validated_url = validate_public_http_url(url)
    response = requests.get(
        validated_url,
        timeout=timeout_seconds,
        allow_redirects=False,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
        tag.extract()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

    article = soup.find("article")
    if article:
        content = article.get_text("\n", strip=True)
    else:
        blocks = soup.find_all(["h1", "h2", "h3", "p", "li"])
        content = "\n".join(b.get_text(" ", strip=True) for b in blocks)

    return {
        "title": normalize_text(title)[:300],
        "text": normalize_text(content)[:12000],
    }


def image_to_data_url(image_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(image_path))
    mime = mime or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"
