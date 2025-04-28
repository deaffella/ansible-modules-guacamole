#!/usr/bin/python

# Copyright: (c) 2020, Pablo Escobar <pablo.escobarlopez@unibas.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible_collections.scicore.guacamole.plugins.module_utils.guacamole import GuacamoleError, \
    guacamole_get_token, guacamole_get_connections, guacamole_get_connections_group_id, guacamole_get_connections_groups
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: guacamole_connections_group

short_description: Administer guacamole connections groups using the rest API

version_added: "2.9"

description:
    - "Add, remove or list guacamole connections groups."

options:
    base_url:
        description:
            - Url to access the guacamole API
        required: true
        aliases: ['url']
        type: str

    auth_username:
        description:
            - Guacamole admin user to login to the API
        required: true
        type: str

    auth_password:
        description:
            - Guacamole admin user password to login to the API
        required: true
        type: str

    validate_certs:
        description:
            - Validate ssl certs?
        default: true
        type: bool

    group_name:
        description:
            - Group name to create
        required: false
        type: str

    parent_group:
        description:
            - Parent group in case this is a sub-group
        default: 'ROOT'
        aliases: ['parentIdentifier']
        type: str

    group_type:
        description:
            - Choose the group type
        default: 'ORGANIZATIONAL'
        type: str
        choices:
            - "ORGANIZATIONAL"
            - "BALANCING"

    max_connections:
        description:
            - Max connections in this group
        type: int

    max_connections_per_user:
        description:
            - Max connections per user in this group
        type: int

    enable_session_affinity:
        description:
            - Enable session affinity for this group
        type: bool

    state:
        description:
            - Create, delete or list the connections group?
        default: 'present'
        type: str
        choices:
            - present
            - absent
            - list

    force_deletion:
        description:
            - Force deletion of the group even if it has child connections
        default: 'False'
        type: bool

author:
    - Pablo Escobar Lopez (@pescobar)
'''

EXAMPLES = '''

- name: List all connections groups
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    state: list

- name: Create a new connections group "group_3"
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    group_name: group_3

- name: Delete connections group "group_4"
  scicore.guacamole.guacamole_connections_group:
    base_url: http://localhost/guacamole
    auth_username: guacadmin
    auth_password: guacadmin
    group_name: group_4
    state: absent
'''

RETURN = '''
connections_group_info:
    description: Information about the created or updated connections group
    type: dict
    returned: when state is present or absent
connections_groups:
    description: Dictionary with all existing connections groups
    type: dict
    returned: when state is list
message:
    description: Some extra info about what the module did
    type: str
    returned: always
'''

URL_ADD_CONNECTIONS_GROUP = "{url}/api/session/data/{datasource}/connectionGroups/?token={token}"
URL_UPDATE_CONNECTIONS_GROUP = "{url}/api/session/data/{datasource}/connectionGroups/{group_numeric_id}?token={token}"
URL_DELETE_CONNECTIONS_GROUP = URL_UPDATE_CONNECTIONS_GROUP


def guacamole_populate_connections_group_payload(module_params):
    payload = {
        "parentIdentifier": module_params['parent_group'],
        "name": module_params['group_name'],
        "type": module_params['group_type'],
        "attributes": {
            "max-connections": module_params['max_connections'],
            "max-connections-per-user": module_params['max_connections_per_user'],
            "enable-session-affinity": module_params['enable_session_affinity'],
        }
    }
    return payload


def guacamole_add_connections_group(base_url, validate_certs, datasource, auth_token, payload):
    url_add_connections_group = URL_ADD_CONNECTIONS_GROUP.format(
        url=base_url, datasource=datasource, token=auth_token)
    headers = {'Content-Type': 'application/json'}
    open_url(url_add_connections_group, method='POST', validate_certs=validate_certs,
             headers=headers, data=json.dumps(payload))


def guacamole_update_connections_group(base_url, validate_certs, datasource, auth_token, group_numeric_id, payload):
    url_update_connections_group = URL_UPDATE_CONNECTIONS_GROUP.format(
        url=base_url, datasource=datasource, group_numeric_id=group_numeric_id, token=auth_token)
    headers = {'Content-Type': 'application/json'}
    open_url(url_update_connections_group, method='PUT', validate_certs=validate_certs,
             headers=headers, data=json.dumps(payload))


def guacamole_delete_connections_group(base_url, validate_certs, datasource, auth_token, group_numeric_id):
    url_delete_connections_group = URL_DELETE_CONNECTIONS_GROUP.format(
        url=base_url, datasource=datasource, group_numeric_id=group_numeric_id, token=auth_token)
    headers = {'Content-Type': 'application/json'}
    open_url(url_delete_connections_group, method='DELETE', validate_certs=validate_certs, headers=headers)


def main():
    module_args = dict(
        base_url=dict(type='str', aliases=['url'], required=True),
        auth_username=dict(type='str', required=True),
        auth_password=dict(type='str', required=True, no_log=True),
        validate_certs=dict(type='bool', default=True),
        group_name=dict(type='str'),
        parent_group=dict(type='str', default='ROOT'),
        group_type=dict(type='str', choices=['ORGANIZATIONAL', 'BALANCING'], default='ORGANIZATIONAL'),
        max_connections=dict(type='int'),
        max_connections_per_user=dict(type='int'),
        enable_session_affinity=dict(type='bool'),
        state=dict(type='str', choices=['absent', 'present', 'list'], default='present'),
        force_deletion=dict(type='bool', default=False)
    )

    result = dict(changed=False, msg='', connections_group_info={}, connections_groups={})

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        guacamole_token = guacamole_get_token(
            base_url=module.params.get('base_url'),
            auth_username=module.params.get('auth_username'),
            auth_password=module.params.get('auth_password'),
            validate_certs=module.params.get('validate_certs'),
        )
    except GuacamoleError as e:
        module.fail_json(msg=str(e))

    if module.params.get('state') == 'list':
        try:
            connections_groups = guacamole_get_connections_groups(
                base_url=module.params.get('base_url'),
                validate_certs=module.params.get('validate_certs'),
                datasource=guacamole_token['dataSource'],
                auth_token=guacamole_token['authToken'],
            )
        except GuacamoleError as e:
            module.fail_json(msg=str(e))
        result['connections_groups'] = connections_groups
        module.exit_json(**result)

    if module.params.get('parent_group') != "ROOT":
        try:
            module.params['parent_group'] = guacamole_get_connections_group_id(
                base_url=module.params.get('base_url'),
                validate_certs=module.params.get('validate_certs'),
                datasource=guacamole_token['dataSource'],
                group=module.params.get('parent_group'),
                auth_token=guacamole_token['authToken'],
            )
        except GuacamoleError as e:
            module.fail_json(msg=str(e))

    try:
        guacamole_connections_groups_before = guacamole_get_connections_groups(
            base_url=module.params.get('base_url'),
            validate_certs=module.params.get('validate_certs'),
            datasource=guacamole_token['dataSource'],
            auth_token=guacamole_token['authToken'],
        )
    except GuacamoleError as e:
        module.fail_json(msg=str(e))

    guacamole_connections_group_exists = False
    for group_id, group_info in guacamole_connections_groups_before.items():
        if group_info['name'] == module.params.get('group_name'):
            group_numeric_id = group_info['identifier']
            guacamole_connections_group_exists = True
            break

    if module.params.get('state') == 'present':
        payload = guacamole_populate_connections_group_payload(module.params)
        if guacamole_connections_group_exists:
            try:
                guacamole_update_connections_group(
                    base_url=module.params.get('base_url'),
                    validate_certs=module.params.get('validate_certs'),
                    datasource=guacamole_token['dataSource'],
                    auth_token=guacamole_token['authToken'],
                    group_numeric_id=group_numeric_id,
                    payload=payload
                )
            except GuacamoleError as e:
                module.fail_json(msg=str(e))
        else:
            try:
                guacamole_add_connections_group(
                    base_url=module.params.get('base_url'),
                    validate_certs=module.params.get('validate_certs'),
                    datasource=guacamole_token['dataSource'],
                    auth_token=guacamole_token['authToken'],
                    payload=payload
                )
            except GuacamoleError as e:
                module.fail_json(msg=str(e))
            result['msg'] = "Connections group '%s' added" % module.params.get('group_name')

    if module.params.get('state') == 'absent':
        if guacamole_connections_group_exists:
            if module.params.get('force_deletion'):
                try:
                    guacamole_delete_connections_group(
                        base_url=module.params.get('base_url'),
                        validate_certs=module.params.get('validate_certs'),
                        datasource=guacamole_token['dataSource'],
                        auth_token=guacamole_token['authToken'],
                        group_numeric_id=group_numeric_id
                    )
                except GuacamoleError as e:
                    module.fail_json(msg=str(e))
            else:
                try:
                    connections_in_group = guacamole_get_connections(
                        base_url=module.params.get('base_url'),
                        validate_certs=module.params.get('validate_certs'),
                        datasource=guacamole_token['dataSource'],
                        group=group_numeric_id,
                        auth_token=guacamole_token['authToken'],
                    )
                except GuacamoleError as e:
                    module.fail_json(msg=str(e))

                if not connections_in_group:
                    try:
                        guacamole_delete_connections_group(
                            base_url=module.params.get('base_url'),
                            validate_certs=module.params.get('validate_certs'),
                            datasource=guacamole_token['dataSource'],
                            auth_token=guacamole_token['authToken'],
                            group_numeric_id=group_numeric_id
                        )
                    except GuacamoleError as e:
                        module.fail_json(msg=str(e))
                else:
                    module.fail_json(
                        msg="Won't delete a group with child connections unless force_deletion=True"
                    )
        else:
            result['msg'] = "Connections group '%s' doesn't exists. Not doing anything" \
                            % (module.params.get('group_name'))

    try:
        guacamole_connections_groups_after = guacamole_get_connections_groups(
            base_url=module.params.get('base_url'),
            validate_certs=module.params.get('validate_certs'),
            datasource=guacamole_token['dataSource'],
            auth_token=guacamole_token['authToken'],
        )
    except GuacamoleError as e:
        module.fail_json(msg=str(e))

    if guacamole_connections_groups_before != guacamole_connections_groups_after:
        result['changed'] = True

    if module.params.get('state') == 'present':
        for group_id, group_info in guacamole_connections_groups_after.items():
            if group_info['name'] == module.params.get('group_name'):
                result['connections_group_info'] = group_info
                break
    else:
        for group_id, group_info in guacamole_connections_groups_before.items():
            if group_info['name'] == module.params.get('group_name'):
                result['connections_group_info'] = group_info
                break

    module.exit_json(**result)


if __name__ == '__main__':
    main()
