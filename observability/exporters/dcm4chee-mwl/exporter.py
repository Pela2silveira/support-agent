#!/usr/bin/env python3
"""Prometheus exporter: Keycloak auth + dcm4chee MWL and studies per PACS* AET."""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import requests
from prometheus_client import Gauge, start_http_server

logger = logging.getLogger("dcm4chee_mwl_exporter")

AUTH_HOST = os.environ.get("SSS_DCM4CHEE_AUTH_HOST", "")
AUTH_REALM = os.environ.get("SSS_DCM4CHEE_AUTH_REALM", "dcm4che")
AUTH_CLIENT = os.environ.get("SSS_AUTH_CLIENT", "")
AUTH_TOKEN = os.environ.get("SSS_AUTH_TOKEN", "")
DCM4CHEE_HOST = os.environ.get("SSS_DCM4CHEE_HOST", "")
MULTI_PACS = os.environ.get("SSS_DCM4CHEE_MULTI_PACS", "true").lower() in {
    "1",
    "true",
    "yes",
}
AET_PREFIX = os.environ.get("SSS_DCM4CHEE_AET_PREFIX", "PACS")
SINGLE_AET = os.environ.get("SSS_DCM4CHEE_AET", "")
COLLECT_INTERVAL = int(os.environ.get("SSS_DCM4CHEE_MWL_INTERVAL_SECONDS", str(20 * 60)))
EXPORTER_PORT = int(os.environ.get("SSS_DCM4CHEE_MWL_EXPORTER_PORT", "9100"))
TLS_VERIFY = os.environ.get("SSS_DCM4CHEE_TLS_VERIFY", "true").lower() not in {
    "0",
    "false",
    "no",
}
TZ_NAME = os.environ.get("SSS_DCM4CHEE_TZ", "America/Argentina/Buenos_Aires")
PAGE_SIZE = int(os.environ.get("SSS_DCM4CHEE_MWL_PAGE_SIZE", "200"))
STUDIES_RS_AET = os.environ.get("SSS_STUDIES_RS_AET", "AS_RECEIVED")
STUDY_UID_PREFIX = os.environ.get("SSS_STUDY_INSTANCE_UID_PREFIX", "").strip()
# (connect, read) — keep connect short so a dead host fails the cycle fast
HTTP_TIMEOUT = (
    int(os.environ.get("SSS_HTTP_CONNECT_TIMEOUT", "15")),
    int(os.environ.get("SSS_HTTP_READ_TIMEOUT", "60")),
)
# Stop hammering the host after this many consecutive connect/read failures
MAX_CONSECUTIVE_TRANSPORT_ERRORS = int(
    os.environ.get("SSS_MAX_CONSECUTIVE_TRANSPORT_ERRORS", "3")
)
# Re-auth before token expiry (client_credentials tokens are often ~5m)
TOKEN_REFRESH_SECONDS = int(os.environ.get("SSS_TOKEN_REFRESH_SECONDS", "240"))

MWL_COUNT_DAY = Gauge(
    "sss_pacs_mwl_count_day",
    "MWL items with SPS date 00400002 = today",
    ["aet"],
)
MWL_QUERY_UP = Gauge(
    "sss_pacs_mwl_query_up",
    "1 if MWL list/count succeeded for AET",
    ["aet"],
)
AETS_DISCOVERED = Gauge(
    "sss_pacs_aets_discovered",
    "Number of archive AETs matching the configured prefix",
)
AUTH_UP = Gauge("sss_pacs_auth_up", "1 if Keycloak token was obtained")
REST_UP = Gauge(
    "sss_pacs_rest_up",
    "1 if any dcm4chee-arc REST query succeeded in the last collect",
)
EXPORTER_UP = Gauge("sss_pacs_mwl_exporter_up", "1 while exporter loop is healthy")
LAST_SUCCESS = Gauge(
    "sss_pacs_mwl_last_success_unixtime",
    "Unix time of last successful full collection",
)
STUDIES_TOTAL = Gauge(
    "sss_pacs_studies_total",
    "Studies received today (StudyDate) for ReceivingApplicationEntityTitleOfSeries",
    ["aet"],
)
STUDIES_WORKLIST_UID = Gauge(
    "sss_pacs_studies_worklist_uid",
    "Studies today whose StudyInstanceUID matches the configured prefix (from MWL)",
    ["aet"],
)
STUDIES_QUERY_UP = Gauge(
    "sss_pacs_studies_query_up",
    "1 if studies count succeeded for AET (today)",
    ["aet"],
)


class TransportAbort(Exception):
    """Too many consecutive transport errors; abort the rest of the collect."""


class ApiClient:
    """Keycloak client_credentials + archive REST, with proactive/401 refresh."""

    def __init__(self) -> None:
        self.token: str | None = None
        self.token_at: float = 0.0
        self.consecutive_transport_errors = 0

    def login(self) -> bool:
        token_url = (
            f"{AUTH_HOST.rstrip('/')}/auth/realms/{AUTH_REALM}"
            "/protocol/openid-connect/token"
        )
        payload = {
            "grant_type": "client_credentials",
            "client_id": AUTH_CLIENT,
            "client_secret": AUTH_TOKEN,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(
                token_url,
                data=payload,
                headers=headers,
                timeout=HTTP_TIMEOUT,
                verify=TLS_VERIFY,
            )
            response.raise_for_status()
            access_token = response.json().get("access_token")
            if not access_token:
                logger.error("No access_token in Keycloak response")
                self.token = None
                return False
            self.token = access_token
            self.token_at = time.time()
            logger.info("Keycloak token obtained")
            return True
        except requests.RequestException as exc:
            logger.error("Keycloak auth failed: %s", exc)
            self.token = None
            return False

    def ensure_token(self, force: bool = False) -> None:
        aged = time.time() - self.token_at
        if force or not self.token or aged >= TOKEN_REFRESH_SECONDS:
            if not self.login():
                raise RuntimeError("Keycloak authentication failed")

    def get(self, url: str, *, accept: str, timeout=HTTP_TIMEOUT) -> requests.Response:
        self.ensure_token()
        assert self.token
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
        }
        try:
            response = requests.get(
                url, headers=headers, timeout=timeout, verify=TLS_VERIFY
            )
        except requests.RequestException as exc:
            self.consecutive_transport_errors += 1
            if self.consecutive_transport_errors >= MAX_CONSECUTIVE_TRANSPORT_ERRORS:
                raise TransportAbort(
                    f"{self.consecutive_transport_errors} consecutive transport "
                    f"errors; aborting collect: {exc}"
                ) from exc
            raise

        if response.status_code == 401:
            logger.warning("REST 401 — refreshing Keycloak token and retrying once")
            self.ensure_token(force=True)
            assert self.token
            headers["Authorization"] = f"Bearer {self.token}"
            response = requests.get(
                url, headers=headers, timeout=timeout, verify=TLS_VERIFY
            )

        self.consecutive_transport_errors = 0
        return response


def _require_config() -> None:
    missing = [
        name
        for name, value in (
            ("SSS_DCM4CHEE_AUTH_HOST", AUTH_HOST),
            ("SSS_AUTH_CLIENT", AUTH_CLIENT),
            ("SSS_AUTH_TOKEN", AUTH_TOKEN),
            ("SSS_DCM4CHEE_HOST", DCM4CHEE_HOST),
        )
        if not value
    ]
    if not MULTI_PACS and not SINGLE_AET:
        missing.append("SSS_DCM4CHEE_AET")
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")


def list_archive_aets(client: ApiClient) -> list[str]:
    url = f"{DCM4CHEE_HOST.rstrip('/')}/dcm4chee-arc/aets"
    response = client.get(url, accept="application/json")
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected /aets response (expected list)")

    aets: list[str] = []
    for item in data:
        if isinstance(item, str):
            aet = item
        elif isinstance(item, dict):
            aet = item.get("dicomAETitle") or item.get("aet") or ""
        else:
            continue
        if aet:
            aets.append(aet)
    return sorted(set(aets))


def resolve_aets(client: ApiClient) -> list[str]:
    if not MULTI_PACS:
        return [SINGLE_AET]
    return [aet for aet in list_archive_aets(client) if aet.startswith(AET_PREFIX)]


def _tag_value(obj: dict, tag: str):
    field = obj.get(tag) or {}
    value = field.get("Value")
    if isinstance(value, list) and value:
        return value[0]
    return None


def _parse_sps_date(date_str: str) -> date | None:
    if not date_str or len(date_str) < 8:
        return None
    day = date_str[:8]
    try:
        return date(int(day[0:4]), int(day[4:6]), int(day[6:8]))
    except ValueError:
        return None


def fetch_mwlitems(client: ApiClient, aet: str) -> list[dict]:
    """
    List MWL items for an AET.

    Note: this archive ignores ScheduledProcedureStepStartDate/Time on /count,
    so we pull items and filter client-side by SPS tags.
    """
    items: list[dict] = []
    offset = 0
    while True:
        query = urlencode(
            {
                "offset": str(offset),
                "limit": str(PAGE_SIZE),
                "includefield": "all",
            }
        )
        url = (
            f"{DCM4CHEE_HOST.rstrip('/')}/dcm4chee-arc/aets/{aet}/rs/mwlitems"
            f"?{query}"
        )
        response = client.get(url, accept="application/dicom+json")
        if response.status_code == 204:
            break
        response.raise_for_status()
        if not response.text.strip():
            break
        page = response.json()
        if not isinstance(page, list) or not page:
            break
        items.extend(item for item in page if isinstance(item, dict))
        if len(page) < PAGE_SIZE:
            break
        offset += len(page)
    return items


def _parse_count_response(response: requests.Response) -> int:
    response.raise_for_status()
    text = response.text.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        data = response.json()
        if isinstance(data, dict) and "count" in data:
            return int(data["count"])
        raise ValueError(f"Unexpected studies count response: {text[:200]}")


def count_studies(
    client: ApiClient,
    study_date: str,
    receiving_aet: str,
    study_uid_prefix: str | None = None,
) -> int:
    """QIDO-RS studies/count on AS_RECEIVED (or configured RS AET)."""
    params: dict[str, str] = {
        "StudyDate": study_date,
        "ReceivingApplicationEntityTitleOfSeries": receiving_aet,
    }
    if study_uid_prefix:
        wildcard = (
            study_uid_prefix
            if study_uid_prefix.endswith("*")
            else f"{study_uid_prefix}*"
        )
        params["StudyInstanceUID"] = wildcard

    query = urlencode(params)
    url = (
        f"{DCM4CHEE_HOST.rstrip('/')}/dcm4chee-arc/aets/{STUDIES_RS_AET}/rs/studies/count"
        f"?{query}"
    )
    response = client.get(url, accept="application/json, text/plain, */*")
    return _parse_count_response(response)



def count_mwl_today(items: list[dict], today: date) -> int:
    """Count MWL items with any SPS whose 00400002 equals today."""
    count = 0
    for item in items:
        seq_field = item.get("00400100") or {}
        seq = seq_field.get("Value")
        if not isinstance(seq, list):
            continue
        for sps in seq:
            if not isinstance(sps, dict):
                continue
            date_str = _tag_value(sps, "00400002")
            if isinstance(date_str, str) and _parse_sps_date(date_str) == today:
                count += 1
                break
    return count


def collect_once() -> None:
    client = ApiClient()
    if not client.login():
        AUTH_UP.set(0)
        REST_UP.set(0)
        return
    AUTH_UP.set(1)

    tz = ZoneInfo(TZ_NAME)
    now = datetime.now(tz)
    today = now.date()
    day = today.strftime("%Y%m%d")

    try:
        aets = resolve_aets(client)
    except Exception as exc:
        logger.error("Failed to resolve AETs: %s", exc)
        AETS_DISCOVERED.set(0)
        REST_UP.set(0)
        return

    # Any successful archive REST call marks REST API as up (set early;
    # studies/MWL loops can take longer than the scrape interval).
    REST_UP.set(1)
    AETS_DISCOVERED.set(len(aets))
    logger.info("Collecting MWL for %d AETs (day=%s)", len(aets), day)

    for aet in aets:
        try:
            items = fetch_mwlitems(client, aet)
            count_day = count_mwl_today(items, today)
            MWL_COUNT_DAY.labels(aet=aet).set(count_day)
            MWL_QUERY_UP.labels(aet=aet).set(1)
            logger.info("MWL aet=%s day=%s", aet, count_day)
        except TransportAbort as exc:
            logger.error("%s", exc)
            MWL_QUERY_UP.labels(aet=aet).set(0)
            EXPORTER_UP.set(0)
            return
        except Exception as exc:
            logger.error("MWL count failed aet=%s: %s", aet, exc)
            MWL_QUERY_UP.labels(aet=aet).set(0)

    if STUDY_UID_PREFIX:
        # One absolute count per AET for today; Prometheus stores samples each
        # collect interval for historical queries via the Grafana time picker.
        for aet in aets:
            try:
                total = count_studies(client, day, aet)
                worklist = count_studies(client, day, aet, STUDY_UID_PREFIX)
                STUDIES_TOTAL.labels(aet=aet).set(total)
                STUDIES_WORKLIST_UID.labels(aet=aet).set(worklist)
                STUDIES_QUERY_UP.labels(aet=aet).set(1)
                logger.info(
                    "Studies aet=%s day=%s total=%s worklist_uid=%s outside=%s",
                    aet,
                    day,
                    total,
                    worklist,
                    max(total - worklist, 0),
                )
            except TransportAbort as exc:
                logger.error("%s", exc)
                STUDIES_QUERY_UP.labels(aet=aet).set(0)
                EXPORTER_UP.set(0)
                return
            except Exception as exc:
                logger.error("Studies count failed aet=%s day=%s: %s", aet, day, exc)
                STUDIES_QUERY_UP.labels(aet=aet).set(0)
    else:
        logger.warning(
            "SSS_STUDY_INSTANCE_UID_PREFIX unset; skipping studies metrics"
        )

    LAST_SUCCESS.set(time.time())
    EXPORTER_UP.set(1)


def collector_loop() -> None:
    while True:
        try:
            collect_once()
        except Exception as exc:
            logger.exception("Collection cycle failed: %s", exc)
            EXPORTER_UP.set(0)
        time.sleep(COLLECT_INTERVAL)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    _require_config()
    start_http_server(EXPORTER_PORT)
    logger.info(
        "Exporter listening on :%s (interval=%ss, multi_pacs=%s, prefix=%r, tz=%s, "
        "token_refresh=%ss, http_timeout=%s)",
        EXPORTER_PORT,
        COLLECT_INTERVAL,
        MULTI_PACS,
        AET_PREFIX,
        TZ_NAME,
        TOKEN_REFRESH_SECONDS,
        HTTP_TIMEOUT,
    )
    collector_loop()


if __name__ == "__main__":
    main()
