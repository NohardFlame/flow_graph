"""Reserved-word and empty-slug handling after alias rewrite."""

from app.core.errors import NormalizationError


def check_reserved(
    slug: str,
    reserved: set[str],
    *,
    fallback: str | None = None,
    field_name: str = "field",
) -> tuple[str, list[str]]:
    """Validate slug after alias rewrite. Return (final_slug, warnings).

    If slug is empty or reserved and fallback is set, return (fallback, [warning]).
    If slug is empty or reserved and fallback is None, raise NormalizationError.
    """
    warnings: list[str] = []
    if not slug:
        if fallback is not None:
            warnings.append(f"{field_name} was empty; using fallback {fallback!r}")
            return fallback, warnings
        raise NormalizationError(f"{field_name} normalized to empty and no fallback configured")
    if slug in reserved:
        if fallback is not None:
            warnings.append(f"{field_name} {slug!r} is reserved; using fallback {fallback!r}")
            return fallback, warnings
        raise NormalizationError(f"{field_name} {slug!r} is reserved and not allowed")
    return slug, warnings
