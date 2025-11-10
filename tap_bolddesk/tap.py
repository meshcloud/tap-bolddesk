"""BoldDesk tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers
# TODO: Import your custom stream types here:
from tap_bolddesk.streams import (
    BoldDeskStream,
    TicketsStream,
    MessagesStream,
)
# TODO: Compile a list of custom stream types here
#       OR rewrite discover_streams() below with your custom logic.
STREAM_TYPES = [
    TicketsStream,
    MessagesStream,
]

class TapBoldDesk(Tap):
    """BoldDesk tap class."""
    name = "tap-bolddesk"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            description="The API Key to authenticate against the BoldDesk API"
        ),
        th.Property(
            "api_url",
            th.StringType,
            default="https://mycompany.bolddesk.com/api/v1.0",
            description="The URL for the API service"
        ),
        th.Property(
            "start_date",
            th.StringType,
            default="2024-01-01",
            description="The earliest creation date of a ticket that shall be collected. You can provide an ISO date or date time, e.g. 2024-01-01 or 2024-01-01T03:00:00Z."
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
