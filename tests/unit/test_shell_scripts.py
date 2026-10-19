"""Unit tests for the ifupdown2 boot scripts, run against a sandboxed root.

The scripts hard-code ``/etc`` and ``/run``.  Each test copies the real script,
rewrites those two prefixes to a temporary directory and puts stub ``ip``,
``hostname``, ``dhclient`` and ``timeout`` binaries first on ``PATH``.  No
privilege or namespace is needed.
"""

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

SBIN = (
    Path(__file__).resolve().parents[2] / 'workflows' / 'bootc-debs-builder' /
    'ifupdown2postinstall' / 'usr' / 'sbin'
)

STUBS = {
    'ip':
    """#!/bin/bash
case "$*" in
  "-4 addr show scope global")
    [[ -n "${STUB_IP:-}" ]] && echo "    inet ${STUB_IP}/24 scope global eth0"
    exit 0 ;;
  "-o link show")
    echo "2: eth0: <BROADCAST> mtu 1500 link/ether 52:54:00:00:00:01"
    exit 0 ;;
esac
exit 0
""",
    'hostname':
    '#!/bin/bash\necho node1\n',
    'timeout':
    '#!/bin/bash\nshift\nexec "$@"\n',
    'dhclient':
    """#!/bin/bash
# -4 probe: write a lease when STUB_DHCP4=1; -6 probe: succeed on STUB_DHCP6=1.
v6=0; lf=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -6) v6=1 ;;
    -x) exit 0 ;;
    -lf) lf="$2"; shift ;;
  esac
  shift
done
if [[ $v6 == 1 ]]; then [[ "${STUB_DHCP6:-0}" == 1 ]]; exit; fi
[[ "${STUB_DHCP4:-0}" == 1 ]] || exit 1
echo '  option domain-name "lab.example";' >"$lf"
""",
}


@pytest.fixture(name='sandbox')
def fixture_sandbox(tmp_path: Path) -> Path:
    """Build a sandbox root with stub binaries and the etc/run skeleton.

    Args:
        tmp_path: Scratch directory that becomes the sandbox root.

    Returns:
        The sandbox root, holding ``bin/``, ``etc/network/`` and ``run/``.
    """
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    for name, body in STUBS.items():
        path = bindir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    (tmp_path / 'etc' / 'network').mkdir(parents=True)
    (tmp_path / 'run').mkdir()
    return tmp_path


def run_script(sandbox: Path, name: str,
               **env: str) -> subprocess.CompletedProcess[str]:
    """Run the real script *name* with ``/etc`` and ``/run`` redirected.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
        name: File name of the script under the ifupdown2 ``sbin`` directory.
        **env: Extra environment variables for the stub binaries.

    Returns:
        The completed process, with captured text output.
    """
    text = (SBIN / name).read_text()
    text = re.sub(r'(?<![\w.])/(etc|run)/', rf'{sandbox}/\1/', text)
    script = sandbox / name
    script.write_text(text)
    full_env = {
        'PATH': f'{sandbox / "bin"}:{os.environ["PATH"]}',
        **env,
    }
    return subprocess.run(['bash', str(script)],
                          env=full_env,
                          capture_output=True,
                          text=True,
                          check=False)


def test_domain_set_exits_quietly_without_ip(sandbox: Path) -> None:
    """No global IPv4 address: nothing is rendered and the exit code is 0.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    result = run_script(sandbox, 'domain-set')
    assert result.returncode == 0
    assert not (sandbox / 'etc' / 'hosts').exists()


def test_domain_set_renders_templates(sandbox: Path) -> None:
    """IP, short hostname and DHCP domain are substituted into hosts/issue.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    (sandbox / 'etc' /
     'hosts.tpl').write_text('{{ IP }} {{ HOST }}.{{ FQDN }}\n')
    (sandbox / 'etc' / 'issue.tpl').write_text('ip={{ IP }}\n')
    (sandbox / 'run' / 'ifupdown2-dhcp-domain').write_text('lab.example\n')
    result = run_script(sandbox, 'domain-set', STUB_IP='192.0.2.5')
    assert result.returncode == 0, result.stderr
    assert (sandbox / 'etc' /
            'hosts').read_text() == '192.0.2.5 node1.lab.example\n'
    assert (sandbox / 'etc' / 'issue').read_text() == 'ip=192.0.2.5\n'


@pytest.mark.parametrize('domain', ['', 'bad|dom&ain'])
def test_domain_set_falls_back_to_local(sandbox: Path, domain: str) -> None:
    """A missing or unsafe domain value is replaced by ``local``.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
        domain: Content of the DHCP domain file.
    """
    (sandbox / 'etc' / 'hosts.tpl').write_text('{{ HOST }}.{{ FQDN }}\n')
    (sandbox / 'etc' / 'issue.tpl').write_text('x\n')
    (sandbox / 'run' / 'ifupdown2-dhcp-domain').write_text(domain)
    result = run_script(sandbox, 'domain-set', STUB_IP='192.0.2.5')
    assert result.returncode == 0, result.stderr
    assert (sandbox / 'etc' / 'hosts').read_text() == 'node1.local\n'


def test_autoconf_skips_without_marker(sandbox: Path) -> None:
    """Without the marker line the interfaces file is left untouched.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
    """
    interfaces = sandbox / 'etc' / 'network' / 'interfaces'
    interfaces.write_text('custom\n')
    result = run_script(sandbox, 'ifupdown2-autoconf')
    assert result.returncode == 0
    assert interfaces.read_text() == 'custom\n'


@pytest.mark.parametrize(('dhcp4', 'dhcp6', 'expect_v4', 'expect_v6'), [
    ('1', '1', 'inet dhcp', 'inet6 auto'),
    ('1', '0', 'inet dhcp', None),
    ('0', '0', 'inet manual', None),
])
def test_autoconf_stanzas(
    sandbox: Path, dhcp4: str, dhcp6: str, expect_v4: str, expect_v6: str | None
) -> None:
    """Stanzas follow which DHCP probes answered; the domain is handed over.

    Args:
        sandbox: Sandbox root built by the ``sandbox`` fixture.
        dhcp4: ``1`` when the stub DHCPv4 probe answers.
        dhcp6: ``1`` when the stub DHCPv6 probe answers.
        expect_v4: Stanza expected for the IPv4 family.
        expect_v6: Stanza expected for IPv6, or ``None`` when absent.
    """
    interfaces = sandbox / 'etc' / 'network' / 'interfaces'
    interfaces.write_text('# ifupdown2-autoconf\n')
    result = run_script(
        sandbox, 'ifupdown2-autoconf', STUB_DHCP4=dhcp4, STUB_DHCP6=dhcp6
    )
    assert result.returncode == 0, result.stderr
    content = interfaces.read_text()
    assert f'iface eth0 {expect_v4}' in content
    assert ('iface eth0 inet6 auto' in content) == (expect_v6 is not None)
    assert content.startswith('# ifupdown2-autoconf')
    domain = (sandbox / 'run' / 'ifupdown2-dhcp-domain').read_text().strip()
    assert domain == ('lab.example' if dhcp4 == '1' else '')
