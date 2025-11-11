"""REST client handling, including BoldDeskStream base class."""

import requests
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable
from datetime import datetime, timezone

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
    
    # Rate limit handling configuration
    # Tolerate 429 responses and retry with exponential backoff
    tolerated_http_errors = [429]
    # Maximum number of retries for rate-limited requests
    max_retries = 5 

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
        if next_page_token:
            params["Page"] = next_page_token
        return params

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        # TODO: Parse response body and return a set of records.
        yield from extract_jsonpath(self.records_jsonpath, input=response.json())

    def post_process(self, row: dict, context: Optional[dict]) -> dict:
        """As needed, append or transform raw data to match expected structure."""
        # TODO: Delete this method if not needed.
        return row
    
    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response and log rate limit information.
        
        This method is called by the SDK for every response and allows us to:
        1. Log rate limit headers for monitoring
        2. Handle 429 responses gracefully (SDK handles retries via tolerated_http_errors)
        """
        # Log rate limit information from response headers
        rate_limit_limit = response.headers.get("x-rate-limit-limit")
        rate_limit_remaining = response.headers.get("x-rate-limit-remaining")
        rate_limit_reset = response.headers.get("x-rate-limit-reset")
        
        # For 429 responses, log the reset time
        if response.status_code == 429:
            self.logger.warning(
                f"Rate limit exceeded (HTTP 429). "
                f"Period: {rate_limit_limit}, "
                f"Remaining: {rate_limit_remaining}, "
                f"Reset time: {rate_limit_reset}. "
                f"Will retry."
            )
            # SDK will automatically retry based on tolerated_http_errors
            # and backoff configuration
        
        # Call parent class validation for standard error handling
        super().validate_response(response)
    
    def backoff_wait_generator(self):
        """Custom backoff strategy that respects x-rate-limit-reset header.
        
        Returns wait time based on the x-rate-limit-reset header when available.
        """
        def _backoff_from_headers(retriable_api_error):
            """Calculate backoff time from rate limit headers."""
            response = retriable_api_error.response
            
            # Check if this is a 429 rate limit error
            if response.status_code == 429:
                reset_time_str = response.headers.get("x-rate-limit-reset")
                
                if reset_time_str:
                    try:
                        # Parse the reset time (format: 2021-03-26T10:27:19.568443Z)
                        reset_time = datetime.fromisoformat(
                            reset_time_str.replace("Z", "+00:00")
                        )
                        current_time = datetime.now(timezone.utc)
                        
                        # Calculate seconds until reset
                        wait_time = (reset_time - current_time).total_seconds()
                        
                        # Add a small buffer (2 seconds) to ensure the limit has reset
                        wait_time = max(wait_time + 2, 0)
                        
                        self.logger.info(
                            f"Rate limit exceeded. Will reset at {reset_time_str}. "
                            f"Waiting {wait_time:.1f} seconds."
                        )
                        
                        return int(wait_time)
                    except (ValueError, TypeError) as e:
                        self.logger.warning(
                            f"Could not parse rate limit reset time: {e}. "
                            "Using exponential backoff."
                        )
            
            # Return 0 to use default exponential backoff
            return 0
        
        return self.backoff_runtime(value=_backoff_from_headers)

