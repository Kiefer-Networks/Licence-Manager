"""Domain checking utilities."""


def is_company_email(email: str, company_domains: list[str]) -> bool:
    """Check if an email belongs to the company domains.

    Supports both exact domain matches and subdomain matches.
    E.g., for company_domain "firma.de", matches both:
    - user@firma.de (exact)
    - user@sub.firma.de (subdomain)

    Args:
        email: Email address to check
        company_domains: List of company domain names (e.g., ["firma.de", "firma.com"])

    Returns:
        True if the email domain matches one of the company domains
    """
    if not email or "@" not in email:
        return False

    domain = email.split("@")[-1].lower()

    for company_domain in company_domains:
        cd = company_domain.lower()
        # Exact match or subdomain match
        if domain == cd or domain.endswith("." + cd):
            return True

    return False
