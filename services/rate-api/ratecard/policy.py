"""Single source of truth for Harbor commercial rules.

The services policy, the eval set, and the rate API all read these values.
"""

APPROVAL_THRESHOLD_USD = 5000
NORTHLINE_DISCOVERY_HOURS = 80
BRIGHTWATER_MONTHLY_HOURS = 40
AFTER_HOURS_MULTIPLIER = 1.25
MINIMUM_HOURS = 4

HOURLY_USD = {
    "consultant": 180,
    "senior": 240,
    "principal": 320,
}

ACCOUNT_DISCOUNT = {
    "NORTH": 0.0,
    "BRIGHT": 0.10,
}

ACCOUNT_NAMES = {
    "NORTH": "Northline",
    "BRIGHT": "Brightwater",
}

ACCOUNT_GROUPS = {
    "NORTH": "hf-acct-north",
    "BRIGHT": "hf-acct-bright",
}

FINANCE_GROUP = "hf-finance"
STAFF_GROUPS = frozenset(
    {
        FINANCE_GROUP,
        "hf-coordinators",
        "hf-makers",
        *ACCOUNT_GROUPS.values(),
    }
)
