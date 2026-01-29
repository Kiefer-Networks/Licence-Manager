"""Domain checking utilities."""


def is_company_email(email: str, company_domains: list[str]) -> bool:
    """Check if an email belongs to the company domains.

    Args:
        email: Email address to check
        company_domains: List of company domain names (e.g., ["firma.de", "firma.com"])

    Returns:
        True if the email domain matches one of the company domains
    """
    if not email or "@" not in email:
        return False

    domain = email.split("@")[-1].lower()
    return domain in [d.lower() for d in company_domains]
