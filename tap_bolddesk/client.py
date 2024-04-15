"""REST client handling, including BoldDeskStream base class."""

import requests
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from memoization import cached

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIKeyAuthenticator


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


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
        return APIKeyAuthenticator.create_for_stream(
            self,
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

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        next_page_token = 2
        if previous_token is None:
            logging.info("Requesting the 2nd page now.")
        else :
            if previous_token < int(response.json().get("count", 0)) / 100:
                next_page_token = int(previous_token) + 1
            else :
                next_page_token = None

        logging.info("Next requesting page: " + str(next_page_token))

        return next_page_token

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = { }
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
