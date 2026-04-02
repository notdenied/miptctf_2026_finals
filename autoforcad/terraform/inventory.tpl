all:
  hosts:
    jury:
      ansible_host: ${jury_core_address}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu
    forcad:
      ansible_host: ${forcad_address}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu
    monitoring:
      ansible_host: ${monitoring_address}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu

%{ for id, addr in vulnbox_core_addrs ~}
    vulnbox_core_${id + 1}:
      ansible_host: ${addr}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu
%{ endfor ~}

%{ for id, addr in player_core_addrs ~}
    player_core_${id + 1}:
      ansible_host: ${addr}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu
%{ endfor ~}

%{ for id, addr in vulnbox_addrs ~}
    vlnbx_${id + 1}:
      ansible_host: ${addr}
      ansible_port: 22
      ansible_private_key_file: ${key}
      ansible_user: ubuntu
      vuln_pass: ${vulnbox_passwords[id]}
%{ endfor ~}