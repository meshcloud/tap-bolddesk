"""Stream type classes for tap-bolddesk."""

from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_bolddesk.client import BoldDeskStream

# TODO: Delete this is if not using json files for schema definition
# SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

class TicketsStream(BoldDeskStream):
    """Define custom stream."""
    name = "tickets"
    path = "/tickets"
    primary_keys = ["ticketId"]
    replication_key = None
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
        th.Property("createdOn", th.StringType),
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

