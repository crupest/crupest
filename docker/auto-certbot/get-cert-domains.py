#!/usr/bin/env python3

import sys
import os
from os.path import *
from cryptography.x509 import *
from cryptography.x509.oid import ExtensionOID

# Check only one argument
if len(sys.argv) != 2:
    print("You should only specify one argument, aka, the path of cert.",
          file=sys.stderr)
    exit(1)

cert_path = sys.argv[1]

if not exists(cert_path):
    print("Cert file does not exist.", file=sys.stderr)
    exit(2)

if not isfile(cert_path):
    print("Cert path is not a file.")
    exit(3)

if not 'CRUPEST_DOMAIN' in os.environ:
    print("Please set CRUPEST_DOMAIN environment variable to root domain.", file=sys.stderr)
    exit(4)

root_domain = os.environ['CRUPEST_DOMAIN']

with open(cert_path, 'rb') as f:
    cert = load_pem_x509_certificate(f.read())
    ext = cert.extensions.get_extension_for_oid(
        ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    domains: list = ext.value.get_values_for_type(DNSName)
    domains.remove(root_domain)
    domains = [root_domain, *domains]
    print('\n'.join(domains))
