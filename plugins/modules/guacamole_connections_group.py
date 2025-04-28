#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Pablo Escobar <pablo.escobarlopez@unibas.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible_collections.scicore.guacamole.plugins.module_utils.guacamole import (
    GuacamoleError,
    guacamole_get_token,
    guacamole_get_connections,
    guacamole_get_connections_group_id,
)

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: guacamole_connection

short_description: Administer Guacamole connections using the REST API

version_added: "2.9"

description:
  - Add, update or remove Guacamole connections (RDP, VNC, SSH, Telnet).

options:
  base_url:
    description:
      - URL of the Guacamole instance (without trailing slash or I(/api)).
    type: str
    aliases: [url]
    required: true
  auth_username:
    description: Guacamole administrator user.
    type: str
    required: true
  auth_password:
    description: Password for the Guacamole administrator.
    type: str
    required: true
  validate_certs:
    description: Validate TLS certificates.
    type: bool
    default: true
  connection_name:
    description: Name of the connection to create / update / delete.
    type: str
    aliases: [name]
    required: true
  group_name:
    description:
      - Parent connection-group identifier (name or I(ROOT)).
      - If a string different from I(ROOT) is given, it will be resolved to the
        numeric identifier automatically.
    type: str
    aliases: [parentIdentifier]
    default: ROOT
  protocol:
    description: Protocol of the connection.
    type: str
    choices: [rdp, vnc, ssh, telnet]
  hostname:
    description: Host or IP to connect to.
    type: str
  port:
    description: Port of the remote service.
    type: int
  username:
    description: Username used inside the protocol (when applicable).
    type: str
  password:
    description: Password used inside the protocol (when applicable).
    type: str
  # ───────────────────────────────────────────
  # RDP-specific parameters
  rdp_color_depth:
    description: Colour depth in bits.
    type: int
    choices: [8, 16, 24, 32]
  rdp_domain:
    description: Windows domain.
    type: str
  rdp_enable_drive:
    description: Enable network drive mapping.
    type: bool
  rdp_drive_name:
    description: Network drive name.
    type: str
  rdp_drive_path:
    description: Path to network drive.
    type: str
  rdp_enable_full_window_drag:
    description: Show whole window while dragging.
    type: bool
  rdp_ignore_server_certs:
    description: Ignore server certificates.
    type: bool
  rdp_resize_method:
    description: Resize behaviour when client display changes.
    type: str
    choices: [display-update, reconnect]
  rdp_security:
    description: Security mode for RDP.
    type: str
    choices: [any, nla, nla-ext, tls, rdp]
  rdp_server_layout:
    description: Keyboard layout.
    type: str
    choices:
      - en-us-qwerty
      - en-gb-qwerty
      - de-ch-qwertz
      - de-de-qwertz
      - fr-be-azerty
      - fr-fr-azerty
      - fr-ch-qwertz
      - hu-hu-qwertz
      - it-it-qwerty
      - ja-jp-qwerty
      - pt-br-qwerty
      - es-es-qwerty
      - es-latam-qwerty
      - sv-se-qwerty
      - tr-tr-qwerty
      - failsafe
  rdp_width:
    description: Display width.
    type: int
  rdp_height:
    description: Display height.
    type: int
  rdp_console:
    description: Start an administrative session.
    type: bool
  # ───────────────────────────────────────────
  # SSH-specific parameters
  ssh_passphrase:
    description: Passphrase for the supplied private key.
    type: str
  ssh_private_key:
    description: Private key (PEM) as string.
    type: str
  # ───────────────────────────────────────────
  # Recording
  recording_path:
    description: Path on the Guacamole server where recordings are stored.
    type: str
  recording_name:
    description: Pattern for recording file name.
    type: str
  recording_include_keys:
    description: Include keyboard events in recording.
    type: bool
  create_recording_path:
    description:
      - Automatically create the directory given in C(recording_path) if it
        does not exist.
    type: bool
    default: false
  # ───────────────────────────────────────────
  # SFTP
  sftp_enable:
    description: Enable SFTP subsystem.
    type: bool
    default: false
  sftp_port:
    type: int
  sftp_server_alive_interval:
    type: int
  sftp_hostname:
    type: str
  sftp_username:
    type: str
  sftp_password:
    type: str
  sftp_passphrase:
    type: str
  sftp_private_key:
    type: str
  sftp_root_directory:
    type: str
  sftp_default_upload_directory:
    type: str
  # ───────────────────────────────────────────
  state:
    description: Desired state.
    type: str
    choices: [present, absent]
    default: present
  max_connections:
    description: Maximum simultaneous connections for this connection.
    type: int
  max_connections_per_user:
    description: Maximum simultaneous connections per user.
    type: int
  read_only:
    description: Make connection read-only (VNC).
    type: bool
  cursor:
    description: Cursor handling (remote / local).
    type: str
  disable_copy:
    description: Disable clipboard copy.
    type: bool
  disable_paste:
    description: Disable clipboard paste.
    type: bool
  guacd_hostname:
    description: Override guacd hostname.
    type: str
  guacd_port:
    description: Override guacd port.
    type: int
  guacd_encryption:
    description: Encryption for guacd tunnel.
    type: str
    choices: ["", ssl]

author:
  - Pablo Escobar Lopez (@pescobar)
"""

EXAMPLES = r"""
- name: Simple RDP connection
  scicore.guacamole.guacamole_connection:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    connection_name: rdp_example
    protocol: rdp
    hostname: 192.168.33.44
    port: 3389
    username: rdp_user
    password: rdp_pass
    create_recording_path: true
"""

RETURN = r"""
connection_info:
  description: Information about the created / updated connection
  type: dict
  returned: always
message:
  description: Informational message
  type: str
  returned: always
"""

URL_ADD_CONNECTION = "{url}/api/session/data/{datasource}/connections?token={token}"
URL_UPDATE_CONNECTION = (
    "{url}/api/session/data/{datasource}/connections/{connection_id}?token={token}"
)
URL_DELETE_CONNECTION = URL_UPDATE_CONNECTION
URL_CONNECTION_DETAILS = (
    "{url}/api/session/data/{datasource}/connections/{connection_id}/parameters?token={token}"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────
def guacamole_get_connection_details(base_url, validate_certs, datasource, connection_id, auth_token):
    url = URL_CONNECTION_DETAILS.format(
        url=base_url, datasource=datasource, connection_id=connection_id, token=auth_token
    )
    try:
        return json.load(open_url(url, method="GET", validate_certs=validate_certs))
    except ValueError as exc:
        raise GuacamoleError(f"Invalid JSON from {url}: {exc}")
    except Exception as exc:
        raise GuacamoleError(f"Could not get connection details from {url}: {exc}")


def guacamole_add_parameter(payload, module_params, parameters, protocol=None):
    for parameter in parameters:
        ansible_param = f"{protocol}_{parameter}" if protocol else parameter
        api_param = parameter.replace("_", "-")
        if module_params.get(ansible_param) is not None:
            payload["parameters"][api_param] = module_params[ansible_param]


def guacamole_populate_connection_payload(params):
    payload = {
        "parentIdentifier": params["group_name"],
        "name": params["connection_name"],
        "protocol": params["protocol"],
        "parameters": {
            "enable-sftp": params["sftp_enable"],
            "sftp-directory": params["sftp_default_upload_directory"],
            "read-only": params["read_only"],
        },
        "attributes": {
            "guacd-encryption": params["guacd_encryption"],
            "failover-only": "",
            "weight": "",
            "max-connections": params["max_connections"],
            "guacd-hostname": params["guacd_hostname"],
            "guacd-port": params["guacd_port"],
            "max-connections-per-user": params["max_connections_per_user"],
        },
    }

    common_params = (
        "hostname",
        "port",
        "username",
        "password",
        "recording_path",
        "recording_include_keys",
        "recording_name",
        "create_recording_path",          # ← new
        "sftp_port",
        "sftp_server_alive_interval",
        "sftp_hostname",
        "sftp_username",
        "sftp_passphrase",
        "sftp_password",
        "sftp_private_key",
        "sftp_root_directory",
        "disable_copy",
        "disable_paste",
        "cursor",
        "read_only",
    )
    guacamole_add_parameter(payload, params, common_params)

    if params["protocol"] == "rdp":
        rdp_params = (
            "color_depth",
            "domain",
            "enable_drive",
            "drive_name",
            "drive_path",
            "enable_full_window_drag",
            "security",
            "server_layout",
            "width",
            "height",
            "resize_method",
            "console",
        )
        guacamole_add_parameter(payload, params, rdp_params, "rdp")
        if params.get("rdp_ignore_server_certs") is not None:
            payload["parameters"]["ignore-cert"] = params["rdp_ignore_server_certs"]

    elif params["protocol"] == "ssh":
        ssh_params = ("private_key", "passphrase")
        guacamole_add_parameter(payload, params, ssh_params, "ssh")

    return payload


def guacamole_add_connection(base_url, validate_certs, datasource, auth_token, payload):
    url = URL_ADD_CONNECTION.format(url=base_url, datasource=datasource, token=auth_token)
    headers = {"Content-Type": "application/json"}
    open_url(url, method="POST", validate_certs=validate_certs, headers=headers, data=json.dumps(payload))


def guacamole_update_connection(base_url, validate_certs, datasource, connection_id, auth_token, payload):
    url = URL_UPDATE_CONNECTION.format(
        url=base_url, datasource=datasource, connection_id=connection_id, token=auth_token
    )
    headers = {"Content-Type": "application/json"}
    open_url(url, method="PUT", validate_certs=validate_certs, headers=headers, data=json.dumps(payload))


def guacamole_delete_connection(base_url, validate_certs, datasource, connection_id, auth_token):
    url = URL_DELETE_CONNECTION.format(
        url=base_url, datasource=datasource, connection_id=connection_id, token=auth_token
    )
    open_url(url, method="DELETE", validate_certs=validate_certs)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    module_args = dict(
        base_url=dict(type="str", aliases=["url"], required=True),
        auth_username=dict(type="str", required=True),
        auth_password=dict(type="str", required=True, no_log=True),
        validate_certs=dict(type="bool", default=True),
        group_name=dict(type="str", aliases=["parentIdentifier"], default="ROOT"),
        connection_name=dict(type="str", aliases=["name"], required=True),
        protocol=dict(type="str", choices=["rdp", "vnc", "ssh", "telnet"]),
        hostname=dict(type="str"),
        port=dict(type="int"),
        username=dict(type="str"),
        password=dict(type="str", no_log=True),
        # RDP
        rdp_color_depth=dict(type="int", choices=(8, 16, 24, 32)),
        rdp_domain=dict(type="str"),
        rdp_enable_drive=dict(type="bool", default=False),
        rdp_drive_name=dict(type="str"),
        rdp_drive_path=dict(type="str"),
        rdp_enable_full_window_drag=dict(type="bool", default=True),
        rdp_ignore_server_certs=dict(type="bool"),
        rdp_resize_method=dict(type="str", choices=["display-update", "reconnect"]),
        rdp_security=dict(type="str", choices=["any", "nla", "nla-ext", "tls", "rdp"]),
        rdp_server_layout=dict(
            type="str",
            choices=(
                "en-us-qwerty",
                "en-gb-qwerty",
                "de-ch-qwertz",
                "de-de-qwertz",
                "fr-be-azerty",
                "fr-fr-azerty",
                "fr-ch-qwertz",
                "hu-hu-qwertz",
                "it-it-qwerty",
                "ja-jp-qwerty",
                "pt-br-qwerty",
                "es-es-qwerty",
                "es-latam-qwerty",
                "sv-se-qwerty",
                "tr-tr-qwerty",
                "failsafe",
            ),
        ),
        rdp_width=dict(type="int"),
        rdp_height=dict(type="int"),
        rdp_console=dict(type="bool", default=False),
        # Generic
        state=dict(type="str", choices=["absent", "present"], default="present"),
        max_connections=dict(type="int"),
        max_connections_per_user=dict(type="int"),
        recording_path=dict(type="str"),
        recording_include_keys=dict(type="bool"),
        recording_name=dict(type="str"),
        create_recording_path=dict(type="bool", default=False),  # ← new
        sftp_enable=dict(type="bool", default=False),
        sftp_port=dict(type="int"),
        sftp_server_alive_interval=dict(type="int"),
        sftp_hostname=dict(type="str"),
        sftp_username=dict(type="str"),
        sftp_password=dict(type="str", no_log=True),
        sftp_passphrase=dict(type="str", no_log=True),
        sftp_private_key=dict(type="str", no_log=True),
        sftp_root_directory=dict(type="str"),
        sftp_default_upload_directory=dict(type="str"),
        ssh_passphrase=dict(type="str", no_log=True),
        ssh_private_key=dict(type="str", no_log=True),
        disable_copy=dict(type="bool", default=False),
        disable_paste=dict(type="bool", default=False),
        cursor=dict(type="str"),
        guacd_hostname=dict(type="str"),
        guacd_port=dict(type="int"),
        guacd_encryption=dict(type="str", choices=["", "ssl"]),
        read_only=dict(type="bool", default=False),
    )

    result = dict(changed=False, msg="", connection_info={})

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    # ── Access token ────────────────────────────────────────────────────────
    try:
        token = guacamole_get_token(
            base_url=module.params["base_url"],
            auth_username=module.params["auth_username"],
            auth_password=module.params["auth_password"],
            validate_certs=module.params["validate_certs"],
        )
    except GuacamoleError as exc:
        module.fail_json(msg=str(exc))

    datasource = token["dataSource"]
    auth_token = token["authToken"]

    # Resolve parent group numeric id
    if module.params["group_name"] != "ROOT":
        try:
            module.params["group_name"] = guacamole_get_connections_group_id(
                base_url=module.params["base_url"],
                validate_certs=module.params["validate_certs"],
                datasource=datasource,
                group=module.params["group_name"],
                auth_token=auth_token,
            )
        except GuacamoleError as exc:
            module.fail_json(msg=str(exc))

    # Existing connections
    try:
        connections_before = guacamole_get_connections(
            base_url=module.params["base_url"],
            validate_certs=module.params["validate_certs"],
            datasource=datasource,
            group=module.params["group_name"],
            auth_token=auth_token,
        )
    except GuacamoleError as exc:
        module.fail_json(msg=str(exc))

    connection_exists = False
    connection_id = None
    for conn in connections_before:
        if conn.get("name") == module.params["connection_name"]:
            connection_exists = True
            connection_id = conn["identifier"]
            break

    # ── PRESENT ─────────────────────────────────────────────────────────────
    if module.params["state"] == "present":
        payload = guacamole_populate_connection_payload(module.params)
        try:
            if connection_exists:
                # Detect changes
                before = guacamole_get_connection_details(
                    base_url=module.params["base_url"],
                    validate_certs=module.params["validate_certs"],
                    datasource=datasource,
                    auth_token=auth_token,
                    connection_id=connection_id,
                )
                guacamole_update_connection(
                    base_url=module.params["base_url"],
                    validate_certs=module.params["validate_certs"],
                    datasource=datasource,
                    auth_token=auth_token,
                    connection_id=connection_id,
                    payload=payload,
                )
                after = guacamole_get_connection_details(
                    base_url=module.params["base_url"],
                    validate_certs=module.params["validate_certs"],
                    datasource=datasource,
                    auth_token=auth_token,
                    connection_id=connection_id,
                )
                if before != after:
                    result["changed"] = True
                    result["msg"] = "Connection updated"
            else:
                guacamole_add_connection(
                    base_url=module.params["base_url"],
                    validate_certs=module.params["validate_certs"],
                    datasource=datasource,
                    auth_token=auth_token,
                    payload=payload,
                )
                result["changed"] = True
                result["msg"] = "Connection created"
        except GuacamoleError as exc:
            module.fail_json(msg=str(exc))

    # ── ABSENT ──────────────────────────────────────────────────────────────
    if module.params["state"] == "absent":
        if connection_exists:
            try:
                guacamole_delete_connection(
                    base_url=module.params["base_url"],
                    validate_certs=module.params["validate_certs"],
                    datasource=datasource,
                    auth_token=auth_token,
                    connection_id=connection_id,
                )
                result["changed"] = True
                result["msg"] = "Connection deleted"
            except GuacamoleError as exc:
                module.fail_json(msg=str(exc))
        else:
            result["msg"] = f"No connection named {module.params['connection_name']}"

    # Collect final connection list
    try:
        connections_after = guacamole_get_connections(
            base_url=module.params["base_url"],
            validate_certs=module.params["validate_certs"],
            datasource=datasource,
            group=module.params["group_name"],
            auth_token=auth_token,
        )
    except GuacamoleError as exc:
        module.fail_json(msg=str(exc))

    if connections_before != connections_after:
        result["changed"] = True

    # Populate connection_info when it exists
    for conn in connections_after:
        if conn.get("name") == module.params["connection_name"]:
            result["connection_info"] = conn
            break

    module.exit_json(**result)


if __name__ == "__main__":
    main()
