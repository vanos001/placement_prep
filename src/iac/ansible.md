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

The agentless design is the headline architectural fact: no daemon, no port beyond SSH, no agent upgrades to schedule. The cost is that every task ships over the connection and every run re-inspects live state — which is why performance tuning (forks, fact caching, pipelining) matters more than in agent-based systems, and why the control node (Python, its dependencies, network reachability to everything) becomes critical infrastructure.

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

Static INI/YAML inventories are fine for a lab; production targets come from **dynamic inventory plugins** that query the actual source of truth — cloud APIs (`aws_ec2` plugin filtering by tag), CMDBs, Consul, Kubernetes. Host groups then map to reality instead of to a file someone forgot to update:

```yaml
# inventory/aws.yml — dynamic inventory plugin example
plugin: amazon.aws.aws_ec2
filters:
  tag:Env: prod
  instance-state-name: running
keyed_groups:
  - key: tags.Role
    prefix: role
```

Group variables layer (`group_vars/`, `host_vars/`) provide inheritance, and `ansible-inventory --graph` is the debugging command to see the composed view. Interview point: inventory *is* the answer to "how does one playbook target 800 servers and only the right 800."

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

The anatomy is worth naming precisely, because interviewers probe the pieces:

- **Play** — one `hosts:`-scoped unit mapping targets to tasks; a playbook is an ordered list of plays (often orchestrating across tiers: DBs first, then app servers).
- **Tasks** — modules called with arguments, executed in order per host; each returns `changed`/`ok`/`failed`, which drives handlers and the recap.
- **Handlers** — change-triggered side effects via `notify`; deduplicated and run once at end of play (or flushed with `meta: flush_handlers`). The idempotency payoff: restart nginx only if its config actually changed.
- **Tags** — `- name: Copy config` + `tags: [config]` lets `ansible-playbook --tags config` run a slice of the playbook; useful for long plays, dangerous as a substitute for splitting roles (untagged tasks get skipped silently — `--skip-tags never` style discipline needed).
- **Control flow** — `when` conditionals (facts-driven), `loop`/`with_items`, `block/rescue/always` for error handling, `register` to capture task output.

## Idempotency Model & Modules

Ansible modules are **idempotent** — running the same playbook multiple times produces the same result. `shell` and `command` are NOT idempotent by default.

Mechanically, a module receives its arguments, *checks current state on the target*, and acts only on the delta — `apt: name=nginx state=present` runs `dpkg -s nginx` first and no-ops if installed. This check-then-act model is what makes "rerun to converge" a valid drift-repair strategy. Two escape hatches break the model and are interview favorites:

- `shell`/`command` always report `changed`; wrap them with `changed_when:` (and guard with `creates:`) to restore idempotency.
- Failure handling: `failed_when`, `ignore_errors`, and `changed_when` let you encode what "success" means for non-ansible-aware systems.

Prefer dedicated modules (`ansible.builtin` first, cloud modules next) over raw commands; a `command` task is usually a missing module or a missing `changed_when`.

## Roles & Collections

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

Roles package a unit of configuration into a conventional directory layout: `tasks/`, `handlers/`, `templates/` (Jinja2), `files/`, `defaults/` (lowest-precedence, overridable vars), `vars/` (high-precedence), `meta/`. They are the reuse unit *inside* a repo — shareable via `requirements.yml` and Ansible Galaxy.

**Collections** are the modern distribution unit: a namespaced package of roles *plus* modules, plugins, and docs (`community.postgresql`, `amazon.aws`), versioned and installable via `ansible-galaxy collection install`. The interview distinction: a role organizes *your* playbooks; a collection distributes *reusable content* (yours or the community's) with its own changelog and dependencies.

### Variables & Precedence

Ansible resolves variables from a dozen-plus sources with a strict precedence ladder; interviews test the shape, not all 22 rungs:

| Source | Precedence | Typical use |
|---|---|---|
| Role `defaults/main.yml` | Lowest | Overridable API of the role |
| Inventory `group_vars/` | Low | Environment-level values |
| Inventory `host_vars/` | Medium | Per-host exceptions |
| Play `vars:` | High | Play-scoped intent |
| `extra_vars` (`-e`) | Highest | CI/CLI injection, wins over everything |

The design rule hiding in the ladder: **the lower the precedence, the more it belongs to the reusable component** — a role's defaults are its contract, and environment data flows in from inventory rather than being hard-coded over them. When debugging "why is this var wrong?", `ansible-inventory --host <name>` shows the composed value and the command `ansible localhost -m debug -a "var=myvar"` inside a play context settles which rung won.

### Check Mode, Linting & Debugging

Because Ansible mutates live hosts, it ships a dry-run contract: `ansible-playbook --check` predicts changes without applying them (modules that cannot predict report `check mode not supported`), and `--diff` shows what *would* change in files/templates — the closest analogue to `terraform plan` in the Ansible world, though it depends on module support rather than a state store. Static gates complement it: `ansible-lint` enforces style and best-practice rules, `--syntax-check` parses without executing, and `--start-at-task`/`--step` let you bisect a failing play interactively. A pipeline that runs `ansible-lint` + `--check --diff` against a staging inventory before touching production is the pull-model equivalent of a plan-on-PR review flow.

## Secrets: Ansible Vault

Vault encrypts individual files or inline strings with AES-256 using a shared password:

```bash
ansible-vault create group_vars/prod/vault.yml   # create encrypted vars
ansible-vault edit group_vars/prod/vault.yml     # decrypt-edit-reencrypt
ansible-playbook site.yml --ask-vault-pass       # or --vault-password-file
```

The standard pattern is a `vault.yml` per group holding secrets referenced by plain vars files, so the *shape* of config stays reviewable while values stay encrypted. Vault's honest limitations are an interview differentiator: the password is shared (no per-person revocation without re-encrypting everything), and Git diffs of encrypted files are opaque. For serious estates, delegate to a proper secrets manager (HashiCorp Vault, cloud KMS/SSM) via lookup plugins and keep Ansible Vault for bootstrap-level secrets.

## Execution Environments & AWX

Running Ansible well at team scale means controlling the *control node*:

- **Execution Environments (EEs)** — container images bundling a specific Ansible version with collections, Python deps, and plugins. They fix the classic "works on my control node" problem: CI, AWX, and laptops all run the same image. Build with `ansible-builder`, run with `ansible-navigator`.
- **AWX / Ansible Automation Platform** — the API+UI+RBAC layer over playbook execution: schedules, credentials vaulting, job templates ("run role X against inventory Y with these inputs"), audit logs, notifications. Red Hat sells it as AAP; the open-source upstream is AWX.
- **Surveys and job templates** — the AWX feature that turns a parameterized playbook into a self-service form for non-CLI users; the usual bridge between "only the automation person can run this" and platform-style self-service.
- The interview framing: EEs solve *dependency reproducibility*, AWX solves *operationalization* (who may run what, when, with which credentials).

## Ansible vs Terraform: The Boundary

The canonical pairing question — get it crisp:

| Dimension | Terraform | Ansible |
|---|---|---|
| Job | Provisioning (create/destroy the estate) | Configuration (manage what runs on it) |
| State | Persistent state file, diff against it | None — inspects live systems each run |
| Execution | Declarative graph, dependency-ordered | Procedural plays, in written order |
| Drift model | Detect via plan, converge via apply | Converge by re-running (modules are idempotent) |
| Target | Cloud APIs, provider plugins | SSH/WinRM to hosts, agentless |

Terraform deliberately stops at the guest OS boundary; Ansible deliberately avoids owning cloud resource graphs (its cloud modules exist but without state they handle drift poorly). The seam can blur — Ansible can provision VMs, Terraform can `remote-exec` — and the mature answer is that blurring it produces both tools doing what the other does better. Increasingly, the configuration half is itself displaced by baked images ([Packer](../cloud/packer.md)) and Kubernetes, leaving Ansible for hosts that will never be cattle: databases, edge boxes, legacy fleets.

## Performance

Ansible's default execution — one SSH connection and one Python interpreter spin-up per task per host — is the thing to optimize:

- **Forks** — parallel worker count (`-f 20` or `ansible.cfg`); the primary lever, default 5.
- **Pipelining** — ships module code over the SSH channel without staging temp files; big win, needs `sudo` without TTY on targets.
- **Fact caching** — gathered facts (default on every play, seconds per host) stored in Redis/memory/jsonfile and reused with `gathering = smart` + `fact_caching_timeout`; avoids re-paying discovery on every run.
- **Mitogen strategy** — the Mitogen library replaced SSH+Python round-trips with a persistent Python context over the connection, giving historically 2–7× speedups; it never shipped in core Ansible (maintenance and security-review concerns), but it is the vocabulary for "strategy plugins can change execution entirely" — free strategy, linear vs serial, `free` and `host_pinned` scheduling.
- **Structural wins** — shrink what runs: tags, `--limit`, role-level splitting, and not gathering facts where unneeded (`gather_facts: false`).
- **Rolling updates** — `serial: 5` (or a percentage) processes the fleet in batches, with `max_fail_percentage` aborting a bad rollout before it spreads; this is Ansible's built-in answer to "how do I config-manage 500 prod hosts without taking them all down at once".

Interview line: "agentless means every run pays connection and discovery costs, so Ansible performance work is about amortizing those — forks for parallelism, pipelining for transport, fact caching for discovery."

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
A: Tasks triggered by `notify` only when the notifying task makes a change. Example: restart nginx only when the config file changed. Handlers run at the end of the play, once each, regardless of how many times they were notified. When a later task depends on the restarted service mid-play, insert `meta: flush_handlers` to run notified handlers at that point instead of play-end.

**Q: How do dynamic inventories work and why do they matter at scale?**
A: A dynamic inventory plugin queries the real source of truth — cloud API filtered by tags, CMDB, Consul — and returns hosts and groups at run time, so the playbook targets reality instead of a hand-maintained file that rots. It matters because in autoscaling estates the set of targets changes hourly; a static inventory silently misses new instances and SSH's into dead ones. Debug with `ansible-inventory --graph` to see the composed view.

**Q: How do you keep secrets in Ansible, and what are Vault's limits?**
A: Ansible Vault encrypts files/strings with AES-256 under a password (`ansible-vault create/edit`, `--ask-vault-pass` at runtime); the common layout is encrypted `vault.yml` per group referenced from plain vars. Limits: passwords are shared rather than per-person, revoking someone means re-encrypting everything, and Git diffs become opaque. Mature estates push real secrets into HashiCorp Vault or cloud KMS/SSM via lookup plugins and reserve Ansible Vault for bootstrap credentials.

**Q: Playbook runs take 40 minutes for 300 hosts. What do you tune?**
A: Raise `forks` first (default 5 means serial batches of five hosts), enable SSH pipelining, and set up fact caching with `gathering = smart` so discovery isn't re-paid each run. Then shrink what runs: `--limit` and tags so only affected hosts execute, `gather_facts: false` where facts aren't used. If it's still slow, the conversation is architecture: replace per-host configuration with baked images, or note that strategy plugins (the Mitogen lineage) changed transport wholesale — evidence you know the execution model, not just flags.

**Q: What's the difference between a role and a collection?**
A: A role is an in-repo packaging convention — tasks, handlers, templates, defaults in a fixed directory tree — that organizes your own playbooks and is shareable via Galaxy/`requirements.yml`. A collection is the modern distribution unit: a namespaced, versioned package bundling roles *plus* modules, plugins, and docs (`community.postgresql`, `amazon.aws`), installed with `ansible-galaxy collection install`. Roles organize your code; collections distribute reusable content across teams and vendors.

**Q: Where does Ansible stop being the right tool, even though it *can* do the job?**
A: Cloud resource provisioning: Ansible's cloud modules have no persistent state, so it can create a VPC but can't reliably detect or reconcile drift against a resource graph the way Terraform's plan does. Long-lived orchestration and continuous convergence are also poor fits — a push tool that runs when invoked can't self-heal the way a GitOps controller or agent does. The pattern to cite: Terraform (or images + Kubernetes) for the estate, Ansible for the configuration-management slice that remains.

## References

- [Ansible Documentation](https://docs.ansible.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
