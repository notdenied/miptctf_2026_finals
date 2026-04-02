terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
    local = {
      source = "hashicorp/local"
      version = "2.2.0"
    }
  }
  required_version = ">= 0.13"
}

locals {
  config = yamldecode(file("${path.module}/../ansible/group_vars/all"))
  ssh_key_path = "/home/andrey/.ssh/miptctf_finals_key"
}

resource "random_password" "vulnbox" {
  count   = local.config.team_count
  length  = 14
  special = false
}

provider "yandex" {
  zone = "ru-central1-b"
}


resource "yandex_compute_instance" "jury" {
  name = "core"
  allow_stopping_for_update = true

  resources {
    cores  = 8
    memory = 8
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }
#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_compute_instance" "vboxcore" {
  name = "vulnbox-core-${count.index}"
  count = local.config.team_count
  allow_stopping_for_update = true

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 10
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }

#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_compute_instance" "player" {
  name = "player-core-${count.index}"
  count = local.config.team_count
  allow_stopping_for_update = true

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 10
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }
#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_compute_instance" "vulnbox" {
  name = "vulnbox-${count.index + 1}"
  count = local.config.team_count
  allow_stopping_for_update = true

  resources {
    cores  = 4
    memory = 8
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 65
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    user-data = <<-CLOUDCFG
      #cloud-config
      ssh_pwauth: true
      users:
        - name: ubuntu
          sudo: ALL=(ALL) NOPASSWD:ALL
          shell: /bin/bash
          lock_passwd: false
          ssh_authorized_keys:
          - ${file("~/.ssh/miptctf_finals_key.pub")}
      chpasswd:
        expire: false
        list: |
          ubuntu:${random_password.vulnbox[count.index].result}
    CLOUDCFG
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }

#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_compute_instance" "forcad" {
  name = "forcad"
  #platform_id = "standard-v2"
  allow_stopping_for_update = true

  resources {
    cores  = 32
    memory = 32
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 100
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }
  
#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_compute_instance" "monitoring" {
  name = "monitoring"
  allow_stopping_for_update = true

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = "fd80bm0rh4rkepi5ksdi"
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/miptctf_finals_key.pub")}"
  }
  
#  scheduling_policy {
#    preemptible = true
#  }
}

resource "yandex_vpc_network" "network-1" {
  name = "network1"
}

resource "yandex_vpc_subnet" "subnet-1" {
  name           = "subnet1"
  zone           = "ru-central1-b"
  network_id     = yandex_vpc_network.network-1.id
  v4_cidr_blocks = ["192.168.10.0/24"]
}

resource "null_resource" "delay" {
  provisioner "local-exec" {
    command = "sleep 180"
  }
}


resource "local_file" "inventory" {
  depends_on = [null_resource.delay]
  filename = "${path.module}/../ansible/hosts"
  file_permission  = "0644"

  content = templatefile("${path.module}/inventory.tpl", {
    vulnbox_core_addrs = yandex_compute_instance.vboxcore[*].network_interface[0].nat_ip_address
    jury_core_address = yandex_compute_instance.jury.network_interface[0].nat_ip_address
    player_core_addrs = yandex_compute_instance.player[*].network_interface[0].nat_ip_address
    forcad_address = yandex_compute_instance.forcad.network_interface[0].nat_ip_address
    monitoring_address = yandex_compute_instance.monitoring.network_interface[0].nat_ip_address
    vulnbox_addrs = yandex_compute_instance.vulnbox[*].network_interface[0].nat_ip_address
    vulnbox_passwords = random_password.vulnbox[*].result
    key = local.ssh_key_path
  })

  # provisioner "local-exec" {
  #   command = "ANSIBLE_CONFIG=${path.module}/../ansible/ansible.cfg ansible-playbook ${path.module}/../ansible/playbook.yml"
  # }
}

output "external_ip_address_jury" {
  value = yandex_compute_instance.jury.network_interface.0.nat_ip_address
}

output "external_ip_addresses_vulnbox" {
  value = yandex_compute_instance.vulnbox[*].network_interface.0.nat_ip_address
}

output "external_ip_address_player" {
  value = yandex_compute_instance.player[*].network_interface.0.nat_ip_address
}

output "external_ip_address_monitoring" {
  value = yandex_compute_instance.monitoring.network_interface.0.nat_ip_address
}