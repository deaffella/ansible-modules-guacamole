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
    guacamole_get_connections,
    guacamole_get_connections_group_id,
    guacamole_get_connections_groups,
    guacamole_get_token,
)

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: guacamole_connections_group

short_description: Manage Apache Guacamole connection-groups through the REST API

version_added: "2.9"

description:
  - Create, update, delete or list connection-groups in an Apache Guacamole server.

options:
  base_url:
    description: URL to access the Guacamole API
    required: true
    aliases: [url]
    type: str
  auth_username:
    description: Guacamole admin user to login to the API
    required: true
    type: str
  auth_password:
    description: Guacamole admin user password to login to the API
    required: true
    type: str
  validate_certs:
    description: Validate TLS certificates?
    type: bool
    default: true
  group_name:
    description: Name of the connection-group to create / update / delete
    type: str
  parent_group:
    description: Parent group (identifier) if this shall be a subgroup
    type: str
    aliases: [parentIdentifier]
    default: ROOT
  group_type:
    description: Group type
    type: str
    choices: [ORGANIZATIONAL, BALANCING]
    default: ORGANIZATIONAL
  max_connections:
    description: Maximum simultaneous connections allowed in this group
    type: int
  max_connections_per_user:
    description: Maximum simultaneous connections per user in this group
    type: int
  enable_session_affinity:
    description: Enable session affinity for this group
    type: bool
  state:
    description: Desired state
    type: str
    choices: [present, absent, list]
    default: present
  force_deletion:
    description: Force deletion even if the group contains child connections
    type: bool
    default: false

author:
  - Pablo Escobar Lopez (@pescobar)
"""

EXAMPLES = """
- name: List every connection-group
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    state: list

- name: Create connections group 'group_3'
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    group_name: group_3

- name: Delete connections group 'group_4'
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    group_name: group_4
    state: absent
"""

RETURN = """
connections_group_info:
  description: Details of the group that was created, updated or removed
  returned: when state is C(present) or C(absent)
  type: dict
connections_groups:
  description: Dictionary of every existing connection-group
  returned: when state is C(list)
  type: dict
message:
  description: Informational message
  returned: always
  type: str
"""

URL_ADD_CONNECTIONS_GROUP = (
    "{url}/api/session/data/{datasource}/connectionGroups/?token={token}"
)
URL_UPDATE_CONNECTIONS_GROUP = (
    "{url}/api/session/data/{datasource}/connectionGroups/{group_id}?token={token}"
)
URL_DELETE_CONNECTIONS_GROUP = URL_UPDATE_CONNECTIONS_GROUP


def _build_payload(params):
    return {
        "parentIdentifier": params["parent_group"],
        "name": params["group_name"],
        "type": params["group_type"],
        "attributes": {
            "max-connections": params["max_connections"],
            "max-connections-per-user": params["max_connections_per_user"],
            "enable-session-affinity": params["enable_session_affinity"],
        },
    }


def _api_call(url, method, validate_certs, data=None):
    headers = {"Content-Type": "application/json"}
    open_url(url, method=method, validate_certs=validate_certs, headers=headers, data=data)


def main():
    module_args = dict(
        base_url=dict(type="str", aliases=["url"], required=True),
        auth_username=dict(type="str", required=True),
        auth_password=dict(type="str", required=True, no_log=True),
        validate_certs=dict(type="bool", default=True),
        group_name=dict(type="str"),
        parent_group=dict(type="str", default="ROOT"),
        group_type=dict(type="str", choices=["ORGANIZATIONAL", "BALANCING"], default="ORGANIZATIONAL"),
        max_connections=dict(type="int"),
        max_connections_per_user=dict(type="int"),
        enable_session_affinity=dict(type="bool"),
        state=dict(type="str", choices=["present", "absent", "list"], default="present"),
        force_deletion=dict(type="bool", default=False),
    )

    result = dict(
        changed=False,
        msg="",
        connections_group_info={},
        connections_groups={},
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

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

    # LIST ------------------------------------------------------------------ #
    if module.params["state"] == "list":
        try:
            result["connections_groups"] = guacamole_get_connections_groups(
                base_url=module.params["base_url"],
                validate_certs=module.params["validate_certs"],
                datasource=datasource,
                auth_token=auth_token,
            )
        except GuacamoleError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(**result)

    # From here on, present/absent require a group_name
    if not module.params["group_name"]:
        module.fail_json(msg="parameter 'group_name' is required when state is 'present' or 'absent'")

    # Resolve parent group identifier when not ROOT
    if module.params["parent_group"] != "ROOT":
        try:
            module.params["parent_group"] = guacamole_get_connections_group_id(
                base_url=module.params["base_url"],
                validate_certs=module.params["validate_certs"],
                datasource=datasource,
                group=module.params["parent_group"],
                auth_token=auth_token,
            )
        except GuacamoleError as exc:
            module.fail_json(msg=str(exc))

    # Current groups before modifications
    try:
        groups_before = guacamole_get_connections_groups(
            base_url=module.params["base_url"],
            validate_certs=module.params["validate_certs"],
            datasource=datasource,
            auth_token=auth_token,
        )
    except GuacamoleError as exc:
        module.fail_json(msg=str(exc))

    group_exists = False
    group_id = None
    for gid, ginfo in groups_before.items():
        if ginfo["name"] == module.params["group_name"]:
            group_exists = True
            group_id = ginfo["identifier"]
            break

    # PRESENT --------------------------------------------------------------- #
    if module.params["state"] == "present":
        payload = json.dumps(_build_payload(module.params))
        if group_exists:
            try:
                _api_call(
                    URL_UPDATE_CONNECTIONS_GROUP.format(
                        url=module.params["base_url"], datasource=datasource, group_id=group_id, token=auth_token
                    ),
                    "PUT",
                    module.params["validate_certs"],
                    payload,
                )
            except Exception as exc:
                module.fail_json(msg=str(exc))
        else:
            try:
                _api_call(
                    URL_ADD_CONNECTIONS_GROUP.format(
                        url=module.params["base_url"], datasource=datasource, token=auth_token
                    ),
                    "POST",
                    module.params["validate_certs"],
                    payload,
                )
                result["msg"] = "Connections group '{}' created".format(module.params["group_name"])
            except Exception as exc:
                module.fail_json(msg=str(exc))

    # ABSENT ---------------------------------------------------------------- #
    if module.params["state"] == "absent":
        if not group_exists:
            result["msg"] = "Connections group '{}' does not exist".format(module.params["group_name"])
        else:
            # Check for child connections if not forcing deletion
            if not module.params["force_deletion"]:
                try:
                    childs = guacamole_get_connections(
                        base_url=module.params["base_url"],
                        validate_certs=module.params["validate_certs"],
                        datasource=datasource,
                        group=group_id,
                        auth_token=auth_token,
                    )
                except GuacamoleError as exc:
                    module.fail_json(msg=str(exc))
                if childs:
                    module.fail_json(msg="Group has child connections – set force_deletion=true to override")
            try:
                _api_call(
                    URL_DELETE_CONNECTIONS_GROUP.format(
                        url=module.params["base_url"], datasource=datasource, group_id=group_id, token=auth_token
                    ),
                    "DELETE",
                    module.params["validate_certs"],
                )
            except Exception as exc:
                module.fail_json(msg=str(exc))

    # Groups AFTER ---------------------------------------------------------- #
    try:
        groups_after = guacamole_get_connections_groups(
            base_url=module.params["base_url"],
            validate_certs=module.params["validate_certs"],
            datasource=datasource,
            auth_token=auth_token,
        )
    except GuacamoleError as exc:
        module.fail_json(msg=str(exc))

    if groups_before != groups_after:
        result["changed"] = True

    # Populate connections_group_info
    if module.params["state"] == "present":
        for gid, ginfo in groups_after.items():
            if ginfo["name"] == module.params["group_name"]:
                result["connections_group_info"] = ginfo
                break
    elif module.params["state"] == "absent":
        for gid, ginfo in groups_before.items():
            if ginfo["name"] == module.params["group_name"]:
                result["connections_group_info"] = ginfo
                break

    module.exit_json(**result)


if __name__ == "__main__":
    main()
