#!/usr/bin/env python3

import json
import jsonschema
import os
from os.path import *
import shutil
import subprocess
from rich.prompt import Confirm
from cryptography.x509 import *
from cryptography.x509.oid import ExtensionOID
from .template import Template
from .path import *

with open(join(nginx_template_dir, 'server.json')) as f:
    server = json.load(f)

with open(join(nginx_template_dir, 'server.schema.json')) as f:
    schema = json.load(f)

jsonschema.validate(server, schema)

non_template_files = ['forbid_unknown_domain.conf', "websocket.conf"]

ssl_template = Template(join(nginx_template_dir, 'ssl.conf.template'))
root_template = Template(join(
    nginx_template_dir, 'root.conf.template'))
static_file_template = Template(join(
    nginx_template_dir, 'static-file.conf.template'))
reverse_proxy_template = Template(join(
    nginx_template_dir, 'reverse-proxy.conf.template'))
redirect_template = Template(join(
    nginx_template_dir, 'redirect.conf.template'))
cert_only_template = Template(join(
    nginx_template_dir, 'cert-only.conf.template'))

nginx_var_set = set.union(root_template.var_set,
                          static_file_template.var_set, reverse_proxy_template.var_set)


def list_subdomain_names() -> list:
    return [s["subdomain"] for s in server["sites"]]


def list_subdomains(domain: str) -> list:
    return [f"{s['subdomain']}.{domain}" for s in server["sites"]]


def list_domains(domain: str) -> list:
    return [domain, *list_subdomains(domain)]


def generate_nginx_config(domain: str, dest: str) -> None:
    if not isdir(dest):
        raise ValueError('dest must be a directory')
    # copy ssl.conf and https-redirect.conf which need no variable substitution
    for filename in non_template_files:
        src = join(nginx_template_dir, filename)
        dst = join(dest, filename)
        shutil.copyfile(src, dst)
    config = {"CRUPEST_DOMAIN": domain}
    # generate ssl.conf
    with open(join(dest, 'ssl.conf'), 'w') as f:
        f.write(ssl_template.generate(config))
    # generate root.conf
    with open(join(dest, f'{domain}.conf'), 'w') as f:
        f.write(root_template.generate(config))
    # generate nginx config for each site
    sites: list = server["sites"]
    for site in sites:
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
        elif site["type"] == 'redirect':
            template = redirect_template
            local_config['CRUPEST_NGINX_URL'] = site["url"]
        elif site["type"] == 'cert-only':
            template = cert_only_template
        else:
            raise Exception('Invalid site type')
        with open(join(dest, f'{subdomain}.{domain}.conf'), 'w') as f:
            f.write(template.generate(local_config))


def check_nginx_config_dir(dir_path: str, domain: str) -> list:
    if not exists(dir_path):
        return []
    good_files = [*non_template_files, "ssl.conf", *
                  [f"{full_domain}.conf" for full_domain in list_domains(domain)]]
    bad_files = []
    for path in os.listdir(dir_path):
        file_name = basename(path)
        if file_name not in good_files:
            bad_files.append(file_name)
    return bad_files


def nginx(domain: str, /, console) -> None:
    bad_files = check_nginx_config_dir(nginx_config_dir, domain)
    if len(bad_files) > 0:
        console.print(
            "WARNING: It seems there are some bad conf files in the nginx config directory:", style="yellow")
        for bad_file in bad_files:
            console.print(bad_file, style="cyan")
        to_delete = Confirm.ask(
            "They will affect nginx in a [red]bad[/] way. Do you want to delete them?", default=True, console=console)
        if to_delete:
            for file in bad_files:
                os.remove(join(nginx_config_dir, file))
    console.print(
        "I have found following var in nginx templates:", style="green")
    for var in nginx_var_set:
        console.print(var, style="magenta")
    if not exists(nginx_config_dir):
        os.mkdir(nginx_config_dir)
        console.print(
            f"Nginx config directory created at [magenta]{nginx_config_dir}[/]", style="green")
    generate_nginx_config(domain, dest=nginx_config_dir)
    console.print("Nginx config generated.", style="green")


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


def get_cert_path(root_domain):
    return join(data_dir, "certbot", "certs", "live", root_domain, "fullchain.pem")


def get_cert_domains(cert_path, root_domain):

    if not exists(cert_path):
        return None

    if not isfile(cert_path):
        return None

    with open(cert_path, 'rb') as f:
        cert = load_pem_x509_certificate(f.read())
        ext = cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        domains: list = ext.value.get_values_for_type(DNSName)
        domains.remove(root_domain)
        domains = [root_domain, *domains]
        return domains


def print_create_cert_message(domain, console):
    console.print(
        "Looks like you haven't run certbot to get the init ssl certificates. You may want to run following code to get one:", style="cyan")
    console.print(certbot_command_gen(domain, "create"),
                  soft_wrap=True, highlight=False)


def check_ssl_cert(domain, console):
    cert_path = get_cert_path(domain)
    tmp_cert_path = join(tmp_dir, "fullchain.pem")
    console.print("Temporarily copy cert to tmp...", style="yellow")
    ensure_tmp_dir()
    subprocess.run(
        ["sudo", "cp", cert_path, tmp_cert_path], check=True)
    subprocess.run(["sudo", "chown", str(os.geteuid()),
                   tmp_cert_path], check=True)
    cert_domains = get_cert_domains(tmp_cert_path, domain)
    if cert_domains is None:
        print_create_cert_message(domain, console)
    else:
        cert_domain_set = set(cert_domains)
        domains = set(list_domains(domain))
        if not cert_domain_set == domains:
            console.print(
                "Cert domains are not equal to host domains. Run following command to recreate it with nginx stopped.", style="red")
            console.print(certbot_command_gen(
                domain, "create", standalone=True), soft_wrap=True, highlight=False)
        console.print("Remove tmp cert...", style="yellow")
        os.remove(tmp_cert_path)
