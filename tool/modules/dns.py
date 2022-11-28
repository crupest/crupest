from os.path import *
from io import StringIO
import re
from .nginx import *


def generate_dns_zone(domain: str, ip: str, /, ttl: str | int = 600, *, enable_mail: bool = True, dkim: str | None = None) -> str:
    result = f"$ORIGIN {domain}.\n\n"
    result += "; A records\n"
    result += f"@ {ttl} IN A {ip}\n"
    subdomains = list_subdomain_names()
    for subdomain in subdomains:
        result += f"{subdomain} {ttl} IN A {ip}\n"

    if enable_mail:
        result += "\n; MX records\n"
        result += f"@ {ttl} IN MX 10 mail.{domain}.\n"
        result += "\n; SPF record\n"
        result += f"@ {ttl} IN TXT \"v=spf1 mx ~all\"\n"
        if dkim is not None:
            result += "\n; DKIM record\n"
            result += f"mail._domainkey {ttl} IN TEXT \"{dkim}\""
            result += "\n; DMARC record\n"
            result += "_dmarc {ttl} IN TXT \"v=DMARC1; p=none; rua=mailto:dmarc.report@{domain}; ruf=mailto:dmarc.report@{domain}; sp=none; ri=86400\"\n"
    return result


def get_dkim_from_mailserver(domain: str) -> str | None:
    dkim_path = join(data_dir, "dms/config/opendkim/keys", domain, "mail.txt")
    if not exists(dkim_path):
        return None

    p = subprocess.run(["sudo", "cat", dkim_path],
                       capture_output=True, check=True)
    value = ""
    for match in re.finditer("\"(.*)\"", p.stdout.decode('utf-8')):
        value += match.groups[1]
    return value


def generate_dns_zone_with_dkim(domain: str, ip: str, /, ttl: str | int = 600) -> str:
    return generate_dns_zone(domain, ip, ttl, enable_mail=True, dkim=get_dkim_from_mailserver(domain))
