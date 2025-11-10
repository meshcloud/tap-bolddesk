"""Stream type classes for tap-bolddesk."""

from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from singer_sdk import typing as th  # JSON Schema typing helpers
from bs4 import BeautifulSoup

from tap_bolddesk.client import BoldDeskStream

# TODO: Delete this is if not using json files for schema definition
# SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

class TicketsStream(BoldDeskStream):
    """Define custom stream."""
    name = "tickets"
    path = "/tickets"
    primary_keys = ["ticketId"]
    replication_key = "lastUpdatedOn"
    replication_method = "INCREMENTAL"
    
    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        return {
            "ticketId": record["ticketId"],
        }
    
    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return URL params for tickets with incremental support."""
        params = super().get_url_params(context, next_page_token)
        
        # Order by lastUpdatedOn descending for incremental sync
        params["OrderBy"] = "lastUpdatedOn"
        params["sort"] = "desc"
        
        # Build the Q parameter for filtering by updatedon
        starting_timestamp = self.get_starting_timestamp(context)
        if starting_timestamp:
            # Format: updatedon:{"from":"2020-11-30T18:30:00.000Z"}
            from_date = starting_timestamp.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            params["Q"] = f'updatedon:{{"from":"{from_date}"}}'
        
        return params
    
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property(
            "title", 
            th.StringType,
            "The title of the ticket"
        ),
        th.Property(
            "ticketId",
            th.IntegerType,
            description="The ticket's system ID"
        ),
        th.Property(
            "cf_issue_type",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType,
                    description="The issue type id"
                ),
                th.Property(
                    "value",
                    th.StringType,
                    description="The display name of the issue type"
                ),
            )
        ),
        
        th.Property(
            "slaBreachedCount",
            th.IntegerType,
            description="Count of how often an SLA was breached for this ticket"
        ),
        th.Property(
            "slaAchievedCount",
            th.IntegerType,
            description="Count of how often an SLA was achieved for this ticket"
        ),
        th.Property("createdOn", th.DateTimeType),
        th.Property("lastUpdatedOn", th.DateTimeType),
        th.Property("closedOn", th.DateTimeType),
        th.Property(
            "group",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "name",
                    th.StringType
                )
            )
        ),
        th.Property(
            "status",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "description",
                    th.StringType
                )
            )
        ),
        th.Property(
            "priority",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "description",
                    th.StringType
                )
            )
        ),
        th.Property(
            "category",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "name",
                    th.StringType
                )
            )
        ),
        th.Property(
            "contactGroup",
            th.ObjectType(
                th.Property(
                    "id",
                    th.IntegerType
                ),
                th.Property(
                    "name", 
                    th.StringType
                )
            )
        )
    ).to_dict()


class MessagesStream(BoldDeskStream):
    """Stream for ticket messages/conversations."""
    name = "messages"
    
    # Set parent relationship
    parent_stream_type = TicketsStream
    
    # Path with placeholder for ticketId from parent context
    # API endpoint: https://{yourdomain}/api/v1/{ticketid}/messages
    path = "/{ticketId}/messages"
    
    primary_keys = ["id"]
    replication_key = None
    
    # Ticket updates don't necessarily mean message updates
    ignore_parent_replication_keys = True
    
    # Don't partition state by ticketId to avoid storing state for each parent ticket.
    # With a high number of tickets, partitioned state would grow excessively large.
    # Messages are synced via parent ticket relationship using incremental lastUpdatedOn.
    state_partitioning_keys = []
    
    def __init__(self, *args, **kwargs):
        """Initialize the stream with a reusable HTML parser."""
        super().__init__(*args, **kwargs)
        self._html_parser = BeautifulSoup("", "html.parser")
    
    # Define schema based on BoldDesk API response structure
    schema = th.PropertiesList(
        th.Property(
            "id",
            th.IntegerType,
            description="The message's system ID"
        ),
        th.Property(
            "ticketId",
            th.IntegerType,
            description="The parent ticket ID"
        ),
        th.Property(
            "description",
            th.StringType,
            description="The message content/description"
        ),
        th.Property(
            "description_plaintext",
            th.StringType,
            description="Plaintext version of the message description (HTML stripped)"
        ),
        th.Property(
            "hasAttachment",
            th.BooleanType,
            description="Whether this message has attachments"
        ),
        th.Property(
            "createdOn",
            th.DateTimeType,
            description="Message creation timestamp"
        ),
        th.Property(
            "updatedOn",
            th.DateTimeType,
            description="Message last update timestamp"
        ),
        th.Property(
            "updatedBy",
            th.ObjectType(
                th.Property("agentShiftId", th.IntegerType),
                th.Property("agentShiftName", th.StringType),
                th.Property("ticketLimit", th.IntegerType),
                th.Property("chatLimit", th.IntegerType),
                th.Property("emailId", th.StringType),
                th.Property("shortCode", th.StringType),
                th.Property("colorCode", th.StringType),
                th.Property("status", th.StringType),
                th.Property("isVerified", th.BooleanType),
                th.Property("profileImageUrl", th.StringType),
                th.Property("userId", th.IntegerType),
                th.Property("name", th.StringType),
                th.Property("displayName", th.StringType),
                th.Property("isAgent", th.BooleanType)
            ),
            description="User who last updated the message"
        ),
        th.Property(
            "source",
            th.StringType,
            description="Source of the message (e.g., 'Agent Portal')"
        ),
        th.Property(
            "isUpdatedByCustomer",
            th.BooleanType,
            description="Whether the message was updated by a customer"
        ),
        th.Property(
            "isFirstUpdate",
            th.BooleanType,
            description="Whether this is the first update"
        ),
        th.Property(
            "updateFlagId",
            th.IntegerType,
            description="ID of the update flag"
        ),
        th.Property(
            "updateFlagName",
            th.StringType,
            description="Name of the update flag"
        ),
        th.Property(
            "attachments",
            th.ArrayType(th.ObjectType()),
            description="Message attachments array"
        ),
        th.Property(
            "messageTypeId",
            th.IntegerType,
            description="Type ID of the message"
        ),
        th.Property(
            "messageTag",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("tagName", th.StringType)
                )
            ),
            description="Tags associated with the message"
        ),
        th.Property(
            "modifiedOrDeletedBy",
            th.ObjectType(
                th.Property("agentShiftId", th.IntegerType),
                th.Property("agentShiftName", th.StringType),
                th.Property("ticketLimit", th.IntegerType),
                th.Property("chatLimit", th.IntegerType),
                th.Property("emailId", th.StringType),
                th.Property("shortCode", th.StringType),
                th.Property("colorCode", th.StringType),
                th.Property("status", th.StringType),
                th.Property("isVerified", th.BooleanType),
                th.Property("profileImageUrl", th.StringType),
                th.Property("userId", th.IntegerType),
                th.Property("name", th.StringType),
                th.Property("displayName", th.StringType),
                th.Property("isAgent", th.BooleanType)
            ),
            description="User who modified or deleted the message"
        ),
        th.Property(
            "modifiedEmailSubject",
            th.StringType,
            description="Modified email subject if applicable"
        ),
        th.Property(
            "isAnyEmailDeliveryFailed",
            th.BooleanType,
            description="Whether any email delivery failed"
        ),
        th.Property(
            "sourceId",
            th.IntegerType,
            description="Source ID of the message"
        ),
        th.Property(
            "activityCount",
            th.IntegerType,
            description="Count of activities related to this message"
        ),
        th.Property(
            "additionalDetails",
            th.ObjectType(
                th.Property("ipAddress", th.StringType),
                th.Property("userAgent", th.StringType)
            ),
            description="Additional details like IP address and user agent"
        ),
        th.Property(
            "skipEmailNotification",
            th.BooleanType,
            description="Whether to skip email notification"
        ),
        th.Property(
            "chatConversationId",
            th.StringType,
            description="Chat conversation ID if from chat"
        )
    ).to_dict()
    
    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return URL params for messages."""
        # Messages might not need pagination params, but include if needed
        params: dict = {}
        # Add any specific parameters for messages endpoint if required
        return params
    
    def post_process(self, row: dict, context: Optional[dict]) -> dict:
        """Process the row to add plaintext description."""
        # Extract HTML description and convert to plaintext
        description_html = row.get("description", "")
        
        if description_html:
            # Reuse the parser instance by resetting its content
            self._html_parser.reset()
            self._html_parser.append(BeautifulSoup(description_html, "html.parser"))
            # Get text content, stripping extra whitespace
            plaintext = self._html_parser.get_text(separator=" ", strip=True)
            row["description_plaintext"] = plaintext
        else:
            row["description_plaintext"] = ""
        
        return row

