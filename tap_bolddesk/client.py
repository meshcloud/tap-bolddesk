"""REST client handling, including BoldDeskStream base class."""

import requests
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from memoization import cached

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIKeyAuthenticator
from singer_sdk.pagination import BasePageNumberPaginator


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class BoldDeskPaginator(BasePageNumberPaginator):
    """Custom paginator for BoldDesk API."""
    
    def has_more(self, response: requests.Response) -> bool:
        """Check if there are more pages to fetch."""
        data = response.json()
        count = data.get("count", 0)
        current_page = self.current_value
        per_page = 100
        
        # Calculate if there are more pages
        total_pages = (count + per_page - 1) // per_page  # Ceiling division
        has_more = current_page < total_pages
        
        logging.info(f"Page {current_page}/{total_pages}, has_more: {has_more}")
        return has_more


class BoldDeskStream(RESTStream):
    """BoldDesk stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config.get("api_url")
    
    records_jsonpath = "$.result[*]"  # Or override `parse_response`.
    total_count_path = "$.count" 

    @property
    def authenticator(self) -> APIKeyAuthenticator:
        """Return a new authenticator object."""
        return APIKeyAuthenticator(
            key="x-api-key",
            value=self.config.get("api_key"),
            location="header"
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        # If not using an authenticator, you may also provide inline auth headers:
        # headers["Private-Token"] = self.config.get("auth_token")
        return headers

    def get_new_paginator(self) -> BoldDeskPaginator:
        """Create a new paginator for BoldDesk API."""
        return BoldDeskPaginator(start_value=1)

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        params["PerPage"] = 100
        params["RequiresCounts"] = True
        params["sort"] = "asc"
        params["OrderBy"] = "ticketId"
        if next_page_token:
            params["Page"] = next_page_token
        if self.config.get("start_date"):
            params["Q"] = "createdon:{\"from\":\"" + self.config.get("start_date") + "\"}"
        return params

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        # TODO: Parse response body and return a set of records.
        yield from extract_jsonpath(self.records_jsonpath, input=response.json())

    def post_process(self, row: dict, context: Optional[dict]) -> dict:
        """As needed, append or transform raw data to match expected structure."""
        # TODO: Delete this method if not needed.
        return row
