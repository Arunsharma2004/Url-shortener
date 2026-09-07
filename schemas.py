import ipaddress
from urllib.parse import urlsplit

from pydantic import BaseModel, HttpUrl, field_validator

_BLOCKED_HOSTNAMES = {"localhost"}


def _points_at_internal_ip(host: str) -> bool:
    """True if `host` is an IP literal in a loopback / private / link-local /
    reserved / multicast / unspecified range (incl. IPv4-mapped IPv6). The
    169.254.0.0/16 link-local range covers the cloud metadata endpoint
    (169.254.169.254).
    """
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


class ShortenRequest(BaseModel):
    original_url: str

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Reject anything that isn't a public http/https URL: non-http(s)
        schemes, URLs carrying userinfo (the ``trusted.com@evil.com`` trick,
        where the visible host looks trusted but the client actually connects
        to ``evil.com``), and URLs whose host is a loopback / private /
        link-local / otherwise internal address (incl. the 169.254.169.254
        cloud-metadata endpoint). Returns the original string unchanged (not
        the parsed URL) so the redirect target is stored exactly as
        submitted.

        Note: hostnames are not resolved, so a public name whose DNS record
        points at an internal address (DNS rebinding) is not caught here.
        """
        try:
            url = HttpUrl(v)
        except Exception as exc:
            raise ValueError("original_url must be a valid http or https URL") from exc

        if urlsplit(v).username is not None:
            raise ValueError("original_url must not contain userinfo (user@host)")

        host = (url.host or "").rstrip(".").lower()
        if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost"):
            raise ValueError("original_url must not point to an internal host")
        if _points_at_internal_ip(host):
            raise ValueError("original_url must not point to an internal address")

        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class StatsResponse(BaseModel):
    original_url: str
    click_count: int
