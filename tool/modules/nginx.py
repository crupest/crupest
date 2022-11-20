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

non_template_files = ['forbid_unknown_domain.conf']

ssl_template = Template(os.path.join(nginx_template_dir, 'ssl.conf.template'))
root_template = Template(os.path.join(
    nginx_template_dir, 'root.conf.template'))
static_file_template = Template(os.path.join(
    nginx_template_dir, 'static-file.conf.template'))
reverse_proxy_template = Template(os.path.join(
    nginx_template_dir, 'reverse-proxy.conf.template'))

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
        if site["type"] not in ['static-file', 'reverse-proxy']:
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
        with open(os.path.join(dest, f'{subdomain}.{domain}.conf'), 'w') as f:
            f.write(template.generate(local_config))


def list_subdomains(domain: str) -> list:
    return [f"{s['subdomain']}.{domain}" for s in server["sites"]]


def list_domains(domain: str) -> list:
    return [domain, *list_subdomains(domain)]


def certbot_command_gen(domain: str, action, test=False) -> str:
    domains = list_domains(domain)
    if action == 'create':
        # create with standalone mode
        return f'docker run -it --rm --name certbot -v "{project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{project_abs_path}/data/certbot/data:/var/lib/letsencrypt" -p "0.0.0.0:80:80" certbot/certbot certonly --standalone -d {" -d ".join(domains)}{ " --test-cert --dry-run" if test else "" }'
    elif action == 'expand':
        # expand with webroot mode
        return f'docker run -it --rm --name certbot -v "{project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{project_abs_path}/data/certbot/data:/var/lib/letsencrypt" -v "{project_abs_path}/data/certbot/webroot:/var/www/certbot" certbot/certbot certonly --webroot -w /var/www/certbot -d {" -d ".join(domains)}{ " --test-cert --dry-run" if test else "" }'
    elif action == 'renew':
        # renew with webroot mode
        return f'docker run -it --rm --name certbot -v "{project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{project_abs_path}/data/certbot/data:/var/lib/letsencrypt" -v "{project_abs_path}/data/certbot/webroot:/var/www/certbot" certbot/certbot renew --webroot -w /var/www/certbot{ " --test-cert --dry-run" if test else "" }'
    raise ValueError('Invalid action')


def nginx_config_dir_check(dir_path: str, domain: str) -> list:
    good_files = [*non_template_files, "ssl.conf", *
                  [f"{full_domain}.conf" for full_domain in list_domains(domain)]]
    bad_files = []
    for path in os.listdir(dir_path):
        basename = os.path.basename(path)
        if basename not in good_files:
            bad_files.append(basename)
    return bad_files
