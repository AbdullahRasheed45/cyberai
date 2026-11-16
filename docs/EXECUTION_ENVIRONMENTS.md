# Execution environments and current isolation limits

Current authority: `MASTER_BRIEF_v2.3.md` §§4,8,9. Three roles may use two or
three physical machines; the Spark and target lab must be physically separate.
No extra laptop or memory upgrade beyond the owner's 32 GB lab is assumed.

## Windows development host

Runs editing, lint, unit/CPU integration and scripted bounded reference checks.
Docker Desktop was demonstrated locally in the dated preparation evidence; that
is not proof of CUDA/ARM64 compatibility or today's daemon availability. No local
CPU result is GB10 hardware evidence. Do not run arbitrary untrusted binaries on
this host. If this host also serves as the lab laptop, targets run inside its
isolated disposable environment, not directly against Windows.

## Spark engine

Runs model serving, training, fresh reload, telemetry and evaluation preparation.
Weights/cache/adapters and engine credentials remain here. Use pinned containers
and the measured provider Docker flags. A compatible existing provider environment
is a separately labelled manual diagnostic path; it does not establish the Docker
lifecycle or future protected sealed installation.

Actual model/GPU compatibility remains unexecuted. One GPU serializes serving and
training. The cooperative rental lock prevents accidental overlap only among
participating commands; it is not an authorization boundary. The future protected
broker, sealed accounts/network namespace and registry remain SPEC.

## 32 GB Windows lab laptop

Use an isolated disposable Linux VM or equivalently reviewed sandbox with a clean
snapshot, explicit memory/disk limit and host reserve. Install only `lab/` and its
standard-library Python requirement inside it. No Windows drive sharing, clipboard
secrets, host credentials, engine keys, model weights or Docker socket mounts.
Do not wipe or reconfigure the Windows installation as part of this preparation.

The present worker starts a loopback-only HTTP target and uses a fixed action
allow-list. Controller and target still share a process/filesystem trust boundary;
this is deliberately not an admitted arbitrary-code/RCE/native target platform.
Full target/observer separation requires the later kit controls before such use.

Use a dedicated SSH key/account and a forced command from the current brief §9.
Pin the independently verified SSH host key and configure LAB_EXPECTED_HOSTNAME.
Deny shell, forwarding and non-lab egress for that account/environment. Record
actual deployed negative tests and firewall/VM restrictions before claiming
isolation. A hostname check and an SSH success are not those tests.

WireGuard/detonation XOR controls, third-party vulnerable targets and other-domain
VMs are future work. They are not installed or enforced merely because earlier
architecture documents list them. No detonation is authorized by this workflow.

## Evidence and export

Record physical host, OS/architecture, commit, configuration and actual command
for every result. Distinguish LOCAL/MOCKED from real hardware evidence. Keep
credentials out of logs and evidence archives. A copied bundle's matching hash
proves byte integrity, not that its destination survives provider deletion.
Verify durability by independent readback before the owner stops billing.
