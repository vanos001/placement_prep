# Ansible

## Architecture

```
Control Node → SSH → Managed Nodes
           ↓
       Inventory → Playbooks → Tasks → Modules
```

- **Control Node**: Where Ansible runs
- **Managed Nodes**: Target servers (agentless, SSH only)
- **Inventory**: List of hosts
- **Playbooks**: YAML orchestration files
- **Modules**: Reusable units (apt, copy, service, etc.)

## Inventory

```ini
# inventory/hosts
[webservers]
web1 ansible_host=10.0.0.1
web2 ansible_host=10.0.0.2

[dbservers]
db1 ansible_host=10.0.0.10

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/id_rsa
```

## Playbooks

```yaml
# playbook.yml
---
- name: Configure web servers
  hosts: webservers
  become: yes
  
  vars:
    http_port: 80
    app_version: "1.2.3"
  
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
        update_cache: yes
    
    - name: Copy config
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: Restart nginx
    
    - name: Ensure nginx is running
      service:
        name: nginx
        state: started
        enabled: yes
  
  handlers:
    - name: Restart nginx
      service:
        name: nginx
        state: restarted
```

## Roles

```
roles/
├── nginx/
│   ├── tasks/main.yml
│   ├── handlers/main.yml
│   ├── templates/nginx.conf.j2
│   ├── files/
│   ├── vars/main.yml
│   └── defaults/main.yml
└── database/
    ├── tasks/main.yml
    └── ...
```

```yaml
# site.yml
- hosts: webservers
  roles:
    - nginx
    - { role: app, tags: ["app"] }
```

## Key Modules

| Module | Purpose | Example |
|---|---|---|
| `apt` | Package management | `apt: name=nginx state=present` |
| `yum` | RPM packages | `yum: name=httpd state=latest` |
| `copy` | Copy files | `copy: src=a.txt dest=/tmp/` |
| `template` | Jinja2 templates | `template: src=t.j2 dest=/etc/` |
| `service` | Manage services | `service: name=nginx state=started` |
| `user` | User management | `user: name=deploy state=present` |
| `shell` | Run commands | `shell: echo hello` |
| `command` | Run commands (safer) | `command: ls -la` |
| `file` | File permissions | `file: path=/tmp state=directory mode=0755` |

## Idempotency

Ansible modules are **idempotent** — running the same playbook multiple times produces the same result. `shell` and `command` are NOT idempotent by default.

## Interview Questions

**Q: What is idempotency and why does it matter in IaC?**
A: Running the same operation multiple times produces the same result. Matters because: (1) safe to re-run playbooks, (2) no accidental side effects, (3) enables convergence (fix drift by re-applying).

**Q: Ansible vs Terraform — when to use which?**
A: Terraform for **provisioning** infrastructure (create VMs, networks, databases). Ansible for **configuring** servers (install packages, deploy apps, manage config). They complement each other: Terraform creates the infrastructure, Ansible configures it.

**Q: What are Ansible handlers?**
A: Tasks triggered by `notify` only when the notifying task makes a change. Example: restart nginx only when the config file changed. Handlers run at the end of the play, once each, regardless of how many times they were notified.

## References

- [Ansible Documentation](https://docs.ansible.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
