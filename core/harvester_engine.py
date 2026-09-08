"""
VASTUDA SaaS Core - Layer 5: Data Harvesters & Web Ingestion Engine
High-throughput, resilient web content harvester with OpenGraph metadata extraction,
content-integrity hashing, and Layer 4 streaming bus integration.
"""

import re
import time
import hashlib
import urllib.request
import urllib.parse
from typing import Dict, Any, List

class SovereignDataHarvester:
    """
    Layer 5 Resilient Ingestion Engine:
    Parses public web endpoints, extracts semantic metadata, calculates
    cryptographic content digests, and streams results into Layer 4 bus.
    """
    def __init__(self, max_bytes: int = 500_000, timeout_sec: float = 6.0):
        self.max_bytes = max_bytes
        self.timeout_sec = timeout_sec
        self.harvest_history: List[Dict[str, Any]] = []
        self.total_pages_harvested = 0
        self.total_bytes_ingested = 0
        self.domains_indexed = set()
        self.total_latency_ms = 0.0

    def harvest(self, url: str) -> Dict[str, Any]:
        """
        Ingests a public target URL, extracts metadata, links, and content hash.
        """
        # Validate URL schema
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc or "unknown-domain"
        start_time = time.perf_counter()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (VASTUDA-Harvester/5.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                status_code = response.status
                content_type = response.headers.get("Content-Type", "text/html")
                raw_bytes = response.read(self.max_bytes)

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            html_text = raw_bytes.decode("utf-8", errors="ignore")

            # Extract Title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else domain

            # Extract Meta Description
            desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', html_text, re.IGNORECASE)
            if not desc_match:
                desc_match = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']', html_text, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else "No meta description provided."

            # Extract OpenGraph title if available
            og_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']', html_text, re.IGNORECASE)
            og_title = og_match.group(1).strip() if og_match else title

            # Discover Outbound Links
            link_matches = re.findall(r'href=["\'](https?://[^"\'\s>]+)["\']', html_text, re.IGNORECASE)
            unique_links = list(dict.fromkeys(link_matches))[:10]

            # Content Integrity Digest
            sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
            word_count = len(re.findall(r'\b\w+\b', html_text))

            record = {
                "status": "success",
                "url": url,
                "domain": domain,
                "http_status": status_code,
                "content_type": content_type,
                "title": title[:100],
                "og_title": og_title[:100],
                "description": description[:180],
                "byte_size": len(raw_bytes),
                "word_count": word_count,
                "links_discovered_count": len(link_matches),
                "sample_links": unique_links[:3],
                "content_hash": sha256_hash,
                "latency_ms": latency_ms,
                "timestamp": time.time(),
                "timestamp_str": time.strftime("%H:%M:%S")
            }

            # Update engine telemetry
            self.total_pages_harvested += 1
            self.total_bytes_ingested += len(raw_bytes)
            self.domains_indexed.add(domain)
            self.total_latency_ms += latency_ms

            # Append to history
            self.harvest_history.insert(0, record)
            if len(self.harvest_history) > 50:
                self.harvest_history = self.harvest_history[:50]

            # Emit to Layer 4 Streaming Bus if available
            try:
                from core.storage_engine import storage_engine
                if storage_engine:
                    storage_engine.publish_event(
                        topic="harvester.page_ingested",
                        payload={"url": url, "title": title, "bytes": len(raw_bytes), "hash": sha256_hash[:16]}
                    )
            except Exception:
                pass

            return record

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_record = {
                "status": "error",
                "url": url,
                "domain": domain,
                "error": str(exc),
                "latency_ms": latency_ms,
                "timestamp": time.time()
            }
            return error_record

    def get_status(self) -> Dict[str, Any]:
        """
        Returns full Level 5 Harvester Fleet Telemetry.
        """
        avg_lat = round(self.total_latency_ms / self.total_pages_harvested, 2) if self.total_pages_harvested > 0 else 0.0
        return {
            "status": "operational",
            "layer": 5,
            "name": "Data Harvesters & Web Ingestion Engine",
            "telemetry": {
                "total_pages_harvested": self.total_pages_harvested,
                "total_bytes_ingested": self.total_bytes_ingested,
                "total_kb_ingested": round(self.total_bytes_ingested / 1024, 2),
                "domains_indexed_count": len(self.domains_indexed),
                "average_latency_ms": avg_lat,
                "max_document_size_kb": round(self.max_bytes / 1024, 2),
                "timeout_sec": self.timeout_sec
            },
            "recent_harvests_count": len(self.harvest_history),
            "timestamp": time.time()
        }

    def get_recent_harvests(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.harvest_history[:limit]


# Global Harvester Singleton
data_harvester = SovereignDataHarvester()
