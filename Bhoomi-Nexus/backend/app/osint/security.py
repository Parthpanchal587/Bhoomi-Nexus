"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence
Security Controls & SSRF Protection

Protects connectors from Server-Side Request Forgery (SSRF), DNS rebinding,
and internal network discovery attacks when polling external OSINT endpoints.
"""

import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional


# Blocked IP ranges: private networks, loopback, link-local, cloud metadata services
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud Metadata (AWS/GCP/Azure)
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "169.254.169.254",
}


def is_ip_allowed(ip_str: str) -> bool:
    """
    Checks whether an IP address belongs to any blocked or private subnet.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        # Check standard flags
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
            return False
        # Check against explicit blocked networks list
        for net in BLOCKED_NETWORKS:
            if ip_obj in net:
                return False
        return True
    except ValueError:
        return False


def validate_osint_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates a URL before any outbound connection is made.
    Returns: (is_safe, error_message, resolved_ip)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string", None

    parsed = urlparse(url)

    # 1. Scheme must be HTTP or HTTPS
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only http and https are allowed.", None

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL: missing hostname", None

    # 2. Block known sensitive hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, f"Access to restricted hostname '{hostname}' is prohibited.", None

    # 3. Resolve hostname and inspect all resolved IPs (DNS rebinding / private IP defense)
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        if not addr_info:
            return False, f"Could not resolve hostname '{hostname}'", None

        # Check every resolved IP address
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if not is_ip_allowed(ip_str):
                return False, f"Resolved IP '{ip_str}' is in a restricted or private subnet. Connection blocked.", ip_str

        # Return first valid resolved IP
        primary_ip = addr_info[0][4][0]
        return True, None, primary_ip

    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname '{hostname}': {str(e)}", None
    except Exception as e:
        return False, f"Validation error: {str(e)}", None
