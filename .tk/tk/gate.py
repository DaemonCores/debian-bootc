#!/usr/bin/env python3
"""tk gate: the code-quality gate of the reference repo, for ANY project.

Languages are detected from the tracked files, never listed per repo. Each
detected language gets the same stage families as the reference gate:
format, lint, types, docs, security, tests (100% coverage), deadcode, audit,
e2e. A tool that is required by a detected language but missing FAILS its
stage (never a silent skip). A repo may replace any stage with its own
Makefile target gate-<category> (probed with make -n).

Jobs map to CI jobs: lint=format,lint,types,docs,deadcode; test=tests;
audit=security,audit; e2e=e2e.

Usage: tk gate [--only <job|category>[,..]] [--staged] [--list]
Exit: 0 all stages green (or nothing to judge), 1 a stage failed or a tool is missing.
"""
import json
import os
import shutil
import subprocess
import sys

JOBS = {
    "lint": ["format", "lint", "types", "docs", "deadcode"],
    "test": ["tests"],
    "audit": ["security", "audit"],
    "e2e": ["e2e"],
}
ORDER = ["format", "lint", "types", "docs", "security", "tests", "deadcode", "audit", "e2e"]
TAIL = 40


def sh(argv, cwd, timeout=3600):
    try:
        p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "timeout after %ss" % timeout
    except OSError as e:
        return 127, str(e)
    return p.returncode, p.stdout


VENDOR_DIR = ".tk"  # the vendored tk CLI (tk align --fix tk): tool-owned, never judged as project code


def own(files):
    return [f for f in files if f != VENDOR_DIR and not f.startswith(VENDOR_DIR + "/")]


def tracked(top):
    code, out = sh(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], top)
    return own([f for f in out.split("\0") if f]) if code == 0 else []


def staged(top):
    code, out = sh(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], top)
    return own([f for f in out.split("\0") if f]) if code == 0 else []


def has(files, *names):
    s = set(files)
    return any(n in s or any(f.endswith("/" + n) for f in files) for n in names)


def has_ext(files, *exts):
    return any(f.endswith(exts) for f in files)


def text(top, rel):
    try:
        with open(os.path.join(top, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def languages(files):
    langs = []
    if has(files, "pyproject.toml", "setup.cfg", "setup.py", "requirements.txt") or has_ext(files, ".py"):
        langs.append("python")
    if has(files, "package.json"):
        langs.append("node")
    if has(files, "Cargo.toml"):
        langs.append("rust")
    if has(files, "go.mod"):
        langs.append("go")
    if has_ext(files, ".sh", ".bash"):
        langs.append("shell")
    if has(files, "pom.xml", "build.gradle", "build.gradle.kts"):
        langs.append("java")
    if has(files, "CMakeLists.txt"):
        langs.append("cmake")
    if has(files, "composer.json"):
        langs.append("php")
    if has(files, "Gemfile"):
        langs.append("ruby")
    if has_ext(files, ".csproj", ".sln"):
        langs.append("dotnet")
    return langs


# code extension -> language name: a tracked file of such a language that no
# stage judges makes the gate FAIL (never a green over unjudged code).
CODE_EXT = {".py": "python", ".js": "node", ".jsx": "node", ".ts": "node", ".tsx": "node", ".mjs": "node",
            ".cjs": "node", ".rs": "rust", ".go": "go", ".sh": "shell", ".bash": "shell", ".java": "java",
            ".kt": "kotlin", ".scala": "scala", ".c": "c", ".h": "c", ".cc": "c++", ".cpp": "c++", ".hpp": "c++",
            ".php": "php", ".rb": "ruby", ".cs": "dotnet", ".swift": "swift", ".lua": "lua", ".pl": "perl",
            ".dart": "dart", ".ex": "elixir", ".exs": "elixir", ".hs": "haskell", ".zig": "zig", ".r": "r",
            ".clj": "clojure", ".ml": "ocaml", ".vue": "node", ".svelte": "node", ".astro": "node"}
COVERS = {"cmake": ("c", "c++"), "java": ("java", "kotlin", "scala"), "dotnet": ("dotnet",), "php": ("php",),
          "ruby": ("ruby",)}


def unjudged(files, langs):
    """Code languages present in the tracked files that no detected stage family covers."""
    have = set(langs)
    for l in langs:
        have |= set(COVERS.get(l, ()))
    seen = {CODE_EXT[os.path.splitext(f)[1].lower()] for f in files if os.path.splitext(f)[1].lower() in CODE_EXT}
    return sorted(seen - have)


def tool_venv(top):
    """The environment holding the python gate tools: the project's own venv when it has one, else a
    per-user cache venv outside every git tree (PEP 668 forbids installing into the system python)."""
    for d in ("venv", ".venv"):
        if os.access(os.path.join(top, d, "bin", "python"), os.X_OK):
            return os.path.join(top, d)
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(cache, "tk", "gate-venv")


def venv_bin(top, tool):
    p = os.path.join(tool_venv(top), "bin", tool)
    if os.access(p, os.X_OK):
        return p
    return shutil.which(tool) or ""


def node_runner(files):
    if has(files, "bun.lock", "bun.lockb"):
        return ["bun", "run"], "bun"
    if has(files, "pnpm-lock.yaml"):
        return ["pnpm", "run"], "pnpm"
    if has(files, "yarn.lock"):
        return ["yarn", "run"], "yarn"
    return ["npm", "run"], "npm"


def scripts_of(top, files):
    rel = "package.json" if "package.json" in files else next((f for f in files if f.endswith("/package.json")), "")
    try:
        return json.loads(text(top, rel) or "{}").get("scripts", {}), os.path.dirname(rel)
    except ValueError:
        return {}, os.path.dirname(rel)


class Stage:
    def __init__(self, cat, lang, argv, tool, cwd="", shell_note="", skip=""):
        self.cat, self.lang, self.argv, self.tool, self.cwd = cat, lang, argv, tool, cwd
        self.note = shell_note
        self.skip = skip

    def label(self):
        return "%s/%s" % (self.cat, self.lang)


def pyproject_has_project(top):
    """True when pyproject.toml declares a [project] table. An unreadable or
    malformed file is treated as declaring one: pip-audit then judges it and
    fails loudly instead of the gate skipping it on a guess."""
    try:
        import tomllib
    except ImportError:
        return True
    try:
        with open(os.path.join(top, "pyproject.toml"), "rb") as fh:
            return isinstance(tomllib.load(fh).get("project"), dict)
    except (OSError, ValueError):
        return True


def python_stages(top, files, only_files):
    py = [f for f in (only_files if only_files is not None else files) if f.endswith(".py")]
    if only_files is not None and not py:
        return []
    tgt = py or ["."]
    cfg = text(top, "pyproject.toml") + text(top, "setup.cfg")
    s = []
    ruff = venv_bin(top, "ruff")
    if "[tool.yapf]" in cfg:  # the project's own formatter wins over ruff format (they disagree on layout)
        s.append(Stage("format", "python", [venv_bin(top, "yapf") or "yapf", "--diff", "--recursive"] + tgt, "yapf"))
    else:
        s.append(Stage("format", "python", [ruff or "ruff", "format", "--check"] + tgt, "ruff"))
    s.append(Stage("lint", "python", [ruff or "ruff", "check"] + tgt, "ruff"))
    if only_files is None:
        types = next((t for t in ("basedpyright", "pyright", "mypy") if venv_bin(top, t)), "mypy")
        s.append(Stage("types", "python", [venv_bin(top, types) or types, "--exclude", "(^|/)" + VENDOR_DIR.replace(".", "[.]") + "/", "."] if types == "mypy"
                       else [venv_bin(top, types) or types], types))
        if "pydoclint" in cfg:
            s.append(Stage("docs", "python", [venv_bin(top, "pydoclint") or "pydoclint", "."], "pydoclint"))
        s.append(Stage("security", "python", [venv_bin(top, "bandit") or "bandit", "-q", "-r", ".",
                                              "--severity-level", "medium", "-x", "./venv,./.venv,./tests,./node_modules,./" + VENDOR_DIR], "bandit"))
        pt = venv_bin(top, "pytest") or "pytest"
        s.append(Stage("tests", "python", [pt, "-q", "--cov", "--cov-branch", "--cov-fail-under=100"], "pytest"))
        # audit the project's declared dependencies, never the tool environment the gate runs in
        pip_audit = venv_bin(top, "pip-audit") or "pip-audit"
        if has(files, "requirements.txt"):
            s.append(Stage("audit", "python", [pip_audit, "-r", "requirements.txt"], "pip-audit"))
        elif has(files, "pyproject.toml"):
            if pyproject_has_project(top):
                s.append(Stage("audit", "python", [pip_audit, "."], "pip-audit"))
            else:
                s.append(Stage("audit", "python", [pip_audit, "."], "pip-audit",
                               skip="no [project] table, nothing to audit"))
    return s


def node_stages(top, files, only_files):
    sc, sub = scripts_of(top, files)
    run, tool = node_runner(files)
    s = []
    if only_files is not None and not has_ext(only_files, ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".astro", ".vue", ".svelte"):
        return s
    pick = {"format": ("format:check", "fmt:check", "format-check"), "lint": ("lint",), "types": ("typecheck", "types", "check:types"),
            "docs": ("docs:check",), "deadcode": ("deadcode", "knip"), "tests": ("test:coverage", "coverage", "test"),
            "e2e": ("e2e", "test:e2e")}
    for cat, names in pick.items():
        if only_files is not None and cat not in ("format", "lint"):
            continue
        name = next((n for n in names if n in sc), "")
        if name:
            s.append(Stage(cat, "node", run + [name], tool, sub))
        elif cat in ("format", "lint", "tests"):
            s.append(Stage(cat, "node", run + [names[0]], tool, sub, "package.json has no '%s' script" % names[0]))
    if only_files is None:
        aud = {"bun": ["bun", "audit"], "pnpm": ["pnpm", "audit", "--audit-level", "high"],
               "yarn": ["yarn", "npm", "audit", "--severity", "high"]}.get(tool, ["npm", "audit", "--audit-level=high"])
        s.append(Stage("audit", "node", aud, aud[0], sub))
    return s


def rust_stages(top, files, only_files):
    s = [Stage("format", "rust", ["cargo", "fmt", "--check"], "cargo"),
         Stage("lint", "rust", ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"], "cargo")]
    if only_files is None:
        s += [Stage("tests", "rust", ["cargo", "test", "--all"], "cargo"),
              Stage("audit", "rust", ["cargo", "audit"], "cargo-audit")]
    return s


def go_stages(top, files, only_files):
    s = [Stage("format", "go", ["sh", "-c", 'test -z "$(gofmt -l .)"'], "gofmt"),
         Stage("lint", "go", ["go", "vet", "./..."], "go")]
    if only_files is None:
        s += [Stage("tests", "go", ["go", "test", "-cover", "./..."], "go"),
              Stage("audit", "go", ["govulncheck", "./..."], "govulncheck")]
    return s


def shell_stages(top, files, only_files):
    sh_files = [f for f in (only_files if only_files is not None else files) if f.endswith((".sh", ".bash"))]
    return [Stage("lint", "shell", ["shellcheck"] + sh_files, "shellcheck")] if sh_files else []


def java_stages(top, files, only_files):
    gradle = has(files, "build.gradle", "build.gradle.kts")
    tool = "gradle" if gradle else "mvn"
    s = [Stage("lint", "java", [tool, "-q", "check" if gradle else "verify"], tool)]
    if only_files is None:
        s.append(Stage("tests", "java", [tool, "-q", "test"], tool))
    return s


def cmake_stages(top, files, only_files):
    if only_files is not None:
        return []
    fmt = [f for f in files if f.endswith((".c", ".h", ".cc", ".cpp", ".hpp"))]
    return [Stage("format", "cmake", ["clang-format", "--dry-run", "--Werror"] + fmt, "clang-format"),
            Stage("tests", "cmake", ["sh", "-c", 'd=$(mktemp -d) && cmake -S . -B "$d" && cmake --build "$d" && ctest --test-dir "$d" --output-on-failure; r=$?; rm -rf "$d"; exit $r'], "cmake")]


def php_stages(top, files, only_files):
    sc = json.loads(text(top, "composer.json") or "{}").get("scripts", {})
    s = [Stage("lint", "php", ["composer", "validate", "--strict"], "composer")]
    if only_files is None:
        s.append(Stage("tests", "php", ["composer", "run", "test"], "composer", "", "" if "test" in sc else "composer.json has no 'test' script"))
        s.append(Stage("audit", "php", ["composer", "audit"], "composer"))
    return s


def ruby_stages(top, files, only_files):
    s = [Stage("lint", "ruby", ["bundle", "exec", "rubocop"], "bundle")]
    if only_files is None:
        s += [Stage("tests", "ruby", ["bundle", "exec", "rake", "test"], "bundle"),
              Stage("audit", "ruby", ["bundle", "exec", "bundle-audit", "check", "--update"], "bundle")]
    return s


def dotnet_stages(top, files, only_files):
    s = [Stage("format", "dotnet", ["dotnet", "format", "--verify-no-changes"], "dotnet")]
    if only_files is None:
        s += [Stage("tests", "dotnet", ["dotnet", "test"], "dotnet"),
              Stage("audit", "dotnet", ["dotnet", "list", "package", "--vulnerable", "--include-transitive"], "dotnet")]
    return s


BUILDERS = {"java": java_stages, "cmake": cmake_stages, "php": php_stages, "ruby": ruby_stages, "dotnet": dotnet_stages,"python": python_stages, "node": node_stages, "rust": rust_stages, "go": go_stages, "shell": shell_stages}


def make_target(top, target):
    if not os.path.exists(os.path.join(top, "Makefile")) and not os.path.exists(os.path.join(top, "makefile")):
        return False
    return sh(["make", "-n", target], top)[0] == 0


def plan(top, only=None, only_staged=False):
    files = tracked(top)
    sel = staged(top) if only_staged else None
    stages = []
    langs = languages(files)
    for lang in langs:
        stages += BUILDERS[lang](top, files, sel)
    if sel is None:
        for lang in unjudged(files, langs):
            stages.append(Stage("tests", lang, ["true"], "none", "", "no gate stage knows %s code: define a Makefile target gate-tests (and gate-lint) for it" % lang))
    cats = set()
    for o in (only or []):
        cats |= set(JOBS.get(o, [o]))
    out, seen = [], set()
    for cat in ORDER:
        if cats and cat not in cats:
            continue
        if make_target(top, "gate-" + cat):
            out.append(Stage(cat, "make", ["make", "gate-" + cat], "make"))
            seen.add(cat)
            continue
        out += [x for x in stages if x.cat == cat]
    return out, langs + unjudged(files, langs)


def execute(top, st):
    if st.note:
        return False, "missing: " + st.note
    exe = st.argv[0]
    if not (os.path.isabs(exe) and os.access(exe, os.X_OK)) and not shutil.which(exe):
        return False, "missing tool: %s (required by the detected %s language)" % (st.tool, st.lang)
    if st.tool == "pytest":
        py = os.path.join(os.path.dirname(exe), "python") if os.path.isabs(exe) else sys.executable
        if sh([py, "-c", "import pytest_cov"], top)[0] != 0:
            return False, "missing tool: pytest-cov (required by the 100% coverage stage)"
    code, out = sh(st.argv, os.path.join(top, st.cwd) if st.cwd else top)
    if st.cat == "tests" and st.lang == "python" and code == 5:
        return False, "no test collected: a project ships tests with its code"
    return code == 0, "\n".join(out.splitlines()[-TAIL:])


INSTALL = {
    "python": [["{py}", "-m", "pip", "install", "--quiet", "ruff", "mypy", "bandit", "pytest", "pytest-cov", "pip-audit"]],
    "rust": [["rustup", "component", "add", "rustfmt", "clippy"], ["cargo", "install", "cargo-audit", "--locked"]],
    "go": [["go", "install", "golang.org/x/vuln/cmd/govulncheck@latest"]],
}


def install(top, langs, files):
    """Provision the toolchain of the detected languages (CI runners start empty)."""
    cmds = [(l, c) for l in langs for c in INSTALL.get(l, [])]
    if "node" in langs:
        run_, tool = node_runner(files)
        frozen = {"bun": ["bun", "install", "--frozen-lockfile"], "pnpm": ["pnpm", "install", "--frozen-lockfile"],
                  "yarn": ["yarn", "install", "--frozen-lockfile"]}.get(tool, ["npm", "ci"])
        cmds.append(("node", frozen))
    if "python" in langs and has(files, "requirements.txt"):
        cmds.append(("python", ["{py}", "-m", "pip", "install", "--quiet", "-r", "requirements.txt"]))
    bad = 0
    venv = tool_venv(top)
    py = os.path.join(venv, "bin", "python")
    if "python" in langs and not os.access(py, os.X_OK):
        code, out = sh([sys.executable, "-m", "venv", venv], top)
        print("gate: install/venv    %s %s" % ("ok" if code == 0 else "FAIL", venv))
        if code != 0:
            print("\n".join(out.splitlines()[-TAIL:]))
            return 1
    for lang, c in cmds:
        c = [py if a == "{py}" else a for a in c]
        code, out = sh(c, top)
        print("gate: install/%-7s %s" % (lang, "ok" if code == 0 else "FAIL"))
        if code != 0:
            bad += 1
            print("\n".join(out.splitlines()[-TAIL:]))
    return 1 if bad else 0


def main(top, args):
    if args[:1] == ["--install"]:
        files = tracked(top)
        return install(top, languages(files), files)
    only, st_only, lst, i = [], False, False, 0
    while i < len(args):
        if args[i] == "--only" and i + 1 < len(args):
            only = [x for x in args[i + 1].split(",") if x]
            i += 2
        elif args[i] == "--staged":
            st_only, i = True, i + 1
        elif args[i] == "--list":
            lst, i = True, i + 1
        else:
            sys.stderr.write("usage: tk gate [--install] [--only job|category[,..]] [--staged] [--list]\n")
            return 1
    stages, langs = plan(top, only, st_only)
    if lst:
        print(json.dumps({"languages": langs, "stages": [x.label() for x in stages if not x.skip]}))
        return 0
    if not langs:
        print("gate: no language detected in the tracked files: nothing to judge")
        return 0
    if not stages:
        print("gate: no stage selected for %s (languages: %s)" % (",".join(only) or "all", ",".join(langs)))
        return 0
    bad = 0
    for st in stages:
        if st.skip:
            print("gate: %-18s skipped: %s" % (st.label(), st.skip))
            sys.stdout.flush()
            continue
        ok, tail = execute(top, st)
        print("gate: %-18s %s" % (st.label(), "ok" if ok else "FAIL"))
        sys.stdout.flush()
        if not ok:
            bad += 1
            print(tail)
    return 1 if bad else 0
