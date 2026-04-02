#!/bin/bash

source terraform/creds.sh
tofu -chdir="./terraform" apply -auto-approve
ANSIBLE_CONFIG=./ansible/ansible.cfg ansible-playbook ./ansible/playbook.yml
