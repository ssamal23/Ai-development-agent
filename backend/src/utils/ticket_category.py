import re

# Recognized ticket-ID prefixes and what they imply.
#
# A BA sets the convention when creating the story, e.g.
# "FRONT_DEV-001" or "ENH_BACK_DEV-042". Parsing this once
# gives every downstream agent (Ticket, Repository, Planning)
# a reliable signal instead of each one re-guessing "is this
# frontend or backend" from free-text every time.
TICKET_CATEGORIES: dict[str, dict] = {
    "front_dev": {
        "area": "frontend",
        "enhancement": False,
        "label": "Frontend Development",
    },
    "back_dev": {
        "area": "backend",
        "enhancement": False,
        "label": "Backend Development",
    },
    "test": {
        "area": None,
        "enhancement": False,
        "label": "Testing",
    },
    "enh_front_dev": {
        "area": "frontend",
        "enhancement": True,
        "label": "Frontend Enhancement",
    },
    "enh_back_dev": {
        "area": "backend",
        "enhancement": True,
        "label": "Backend Enhancement",
    },
}

_UNKNOWN_CATEGORY = {
    "code": "unknown",
    "area": None,
    "enhancement": False,
    "label": "Unclassified",
}

_PREFIX_PATTERN = re.compile(
    r"^([A-Za-z_]+)-\d+"
)


def parse_ticket_category(
    ticket_id: str | None,
) -> dict:
    """
    Parse the category prefix from a ticket ID such as
    "FRONT_DEV-001" or "ENH_BACK_DEV-042".

    Ticket IDs that don't follow the convention (legacy
    IDs, typos, a BA who forgot the prefix) fall back to
    an "unknown" category with no bias, so the rest of the
    pipeline behaves exactly as it did before this feature
    existed - this is a signal booster, not a hard gate.
    """

    if not ticket_id:
        return dict(_UNKNOWN_CATEGORY)

    match = _PREFIX_PATTERN.match(
        ticket_id.strip()
    )

    if not match:
        return dict(_UNKNOWN_CATEGORY)

    prefix = match.group(1).lower()

    metadata = TICKET_CATEGORIES.get(
        prefix
    )

    if metadata is None:
        return dict(_UNKNOWN_CATEGORY)

    return {
        "code": prefix,
        **metadata,
    }
