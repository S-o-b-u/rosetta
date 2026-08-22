def calculate_getTotalDiscountAmount(request):
    """
    Returns the value of the 'totalDiscountAmount' field from the input payload.

    Parameters
    ----------
    request : dict
        Input payload expected to contain the key 'totalDiscountAmount'.

    Returns
    -------
    dict
        A dictionary with a single key 'totalDiscountAmount' mirroring the input value.
        If the key is missing, the value defaults to 0.0.
    """
    # Extract the required field, defaulting to 0.0 if absent.
    total_discount = request.get("totalDiscountAmount", 0.0)

    # Preserve the exact field name and return it in a new dict.
    return {"totalDiscountAmount": total_discount}