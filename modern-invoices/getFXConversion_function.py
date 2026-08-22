from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

def calculate_getFXConversion(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute FX conversion rate based on a mock in‑memory UomConversionDated table.
    Returns a dict with the key 'conversionRate' (float) or an error dict.
    """
    # ---------- 1. Determine effective timestamp ----------
    as_of_ts_str: Optional[str] = request.get("asOfTimestamp")
    if as_of_ts_str:
        try:
            # ISO8601 with trailing Z
            as_of_ts = datetime.strptime(as_of_ts_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            # fallback to fromisoformat (handles without Z)
            as_of_ts = datetime.fromisoformat(as_of_ts_str.rstrip("Z"))
    else:
        as_of_ts = datetime.utcnow()

    # ---------- 2. Mock data representing UomConversionDated ----------
    # Each entry mimics a DB row.
    mock_data: List[Dict[str, Any]] = [
        {
            "uomId": "USD",
            "uomIdTo": "EUR",
            "conversionFactor": Decimal("0.847457627118644"),
            "fromDate": datetime(2022, 1, 1),
            "thruDate": None,
            "purposeEnumId": None,
        },
        {
            "uomId": "GBP",
            "uomIdTo": "USD",
            "conversionFactor": Decimal("0.9009009"),
            "fromDate": datetime(2023, 1, 1),
            "thruDate": None,
            "purposeEnumId": "FX_CONVERSION",
        },
        {
            "uomId": "JPY",
            "uomIdTo": "CAD",
            "conversionFactor": Decimal("1.25"),
            "fromDate": datetime(2020, 1, 1),
            "thruDate": None,
            "purposeEnumId": None,
        },
        # Additional rows could be added here for extensibility.
    ]

    # ---------- 3. Build filter conditions ----------
    uom_id = request.get("uomId")
    uom_id_to = request.get("uomIdTo")
    purpose_enum_id = request.get("purposeEnumId")

    def row_is_valid(row: Dict[str, Any]) -> bool:
        if row["uomId"] != uom_id:
            return False
        if row["uomIdTo"] != uom_id_to:
            return False
        # fromDate <= as_of_ts
        if row["fromDate"] > as_of_ts:
            return False
        # (thruDate is None) OR (thruDate >= as_of_ts)
        thru = row["thruDate"]
        if thru is not None and thru < as_of_ts:
            return False
        # optional purpose filter
        if purpose_enum_id is not None:
            if row.get("purposeEnumId") != purpose_enum_id:
                return False
        return True

    # Apply filter
    filtered_rows = [row for row in mock_data if row_is_valid(row)]

    # ---------- 4. Order by fromDate descending ----------
    filtered_rows.sort(key=lambda r: r["fromDate"], reverse=True)

    # ---------- 5. Compute conversionRate ----------
    if not filtered_rows:
        return {"error": "Conversion rate not found"}

    first_row = filtered_rows[0]
    conversion_factor: Decimal = first_row["conversionFactor"]

    # Guard against division by zero
    if conversion_factor == 0:
        return {"error": "Invalid conversion factor (zero)"}

    conversion_rate = (Decimal("1") / conversion_factor).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Return as float to match expected output format
    return {"conversionRate": float(conversion_rate)}