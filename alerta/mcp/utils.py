def filter_params(**kwargs) -> list[tuple[str, str]]:
    """Build query params list, supporting multi-value fields."""
    params: list[tuple[str, str]] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, list):
            for v in value:
                params.append((key, str(v)))
        elif isinstance(value, bool):
            params.append((key, str(value).lower()))
        else:
            params.append((key, str(value)))
    return params
