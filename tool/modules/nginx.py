#!/usr/bin/env python3

from .template import Template
from .path import project_abs_path, nginx_template_dir
import json
import jsonschema
import os
import os.path
import shutil

with open(os.path.join(nginx_template_dir, 'server.json')) as f:
    server = json.load(f)

with open(os.path.join(nginx_template_dir, 'server.schema.json')) as f:
    schema = json.load(f)

jsonschema.validate(server, schema)

non_template_files = ['forbid_unknown_domain.conf', "websocket.conf"]

ssl_template = Template(os.path.join(nginx_template_dir, 'ssl.conf.template'))
root_template = Template(os.path.join(
    nginx_template_dir, 'root.conf.template'))
static_file_template = Template(os.path.join(
    nginx_template_dir, 'static-file.conf.template'))
reverse_proxy_template = Template(os.path.join(
    nginx_template_dir, 'reverse-proxy.conf.template'))
cert_only_template = Template(os.path.join(
    nginx_template_dir, 'cert-only.conf.template'))

nginx_var_set = set.union(root_template.var_set,
                          static_file_template.var_set, reverse_proxy_template.var_set)


def nginx_config_gen(domain: str, dest: str) -> None:
    if not os.path.isdir(dest):
        raise ValueError('dest must be a directory')
    # copy ssl.conf and https-redirect.conf which need no variable substitution
    for filename in non_template_files:
        src = os.path.join(nginx_template_dir, filename)
        dst = os.path.join(dest, filename)
        shutil.copyfile(src, dst)
    config = {"CRUPEST_DOMAIN": domain}
    # generate ssl.conf
    with open(os.path.join(dest, 'ssl.conf'), 'w') as f:
        f.write(ssl_template.generate(config))
    # generate root.conf
    with open(os.path.join(dest, f'{domain}.conf'), 'w') as f:
        f.write(root_template.generate(config))
    # generate nginx config for each site
    sites: list = server["sites"]
    for site in sites:
        if site["type"] not in ['static-file', 'reverse-proxy', "cert-only"]:
            continue
        subdomain = site["subdomain"]
        local_config = config.copy()
        local_config['CRUPEST_NGINX_SUBDOMAIN'] = subdomain
        if site["type"] == 'static-file':
            template = static_file_template
            local_config['CRUPEST_NGINX_ROOT'] = site["root"]
        elif site["type"] == 'reverse-proxy':
            template = reverse_proxy_template
            local_config['CRUPEST_NGINX_UPSTREAM_NAME'] = site["upstream"]["name"]
            local_config['CRUPEST_NGINX_UPSTREAM_SERVER'] = site["upstream"]["server"]
        elif site["type"] == 'cert-only':
            template = cert_only_template
        with open(os.path.join(dest, f'{subdomain}.{domain}.conf'), 'w') as f:
            f.write(template.generate(local_config))


def list_subdomains(domain: str) -> list:
    return [f"{s['subdomain']}.{domain}" for s in server["sites"]]


def list_domains(domain: str) -> list:
    return [domain, *list_subdomains(domain)]


def certbot_command_gen(domain: str, action, /, test=False, no_docker=False, *, standalone=None, email=None, agree_tos=False) -> str:
    domains = list_domains(domain)

    add_domain_option = True
    if action == 'create':
        if standalone == None:
            standalone = True
        certbot_action = "certonly"
    elif action == 'expand':
        if standalone == None:
            standalone = False
        certbot_action = "certonly"
    elif action == 'renew':
        if standalone == None:
            standalone = False
        add_domain_option = False
        certbot_action = "renew"
    else:
        raise ValueError('Invalid action')

    if no_docker:
        command = "certbot "
    else:
        expose_segment = ' -p "0.0.0.0:80:80"'
        web_root_segment = ' -v "{project_abs_path}/data/certbot/webroot:/var/www/certbot"'
        command = f'docker run -it --rm --name certbot -v "{project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{project_abs_path}/data/certbot/data:/var/lib/letsencrypt"{ expose_segment if  standalone else web_root_segment} certbot/certbot '

    command += certbot_action

    if standalone:
        command += " --standalone"
    else:
        command += ' --webroot -w /var/www/certbot'

    if add_domain_option:
        command += f' -d {" -d ".join(domains)}'

    if email is not None:
        command += f' --email {email}'

    if agree_tos:
        command += ' --agree-tos'

    if test:
        command += " --test-cert --dry-run"

    return command


def nginx_config_dir_check(dir_path: str, domain: str) -> list:
    if not os.path.exists(dir_path):
        return []
    good_files = [*non_template_files, "ssl.conf", *
                  [f"{full_domain}.conf" for full_domain in list_domains(domain)]]
    bad_files = []
    for path in os.listdir(dir_path):
        basename = os.path.basename(path)
        if basename not in good_files:
            bad_files.append(basename)
    return bad_files
