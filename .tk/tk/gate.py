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
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

JOBS = {
    "lint": ["format", "lint", "types", "docs", "deadcode"],
    "test": ["tests"],
    "audit": ["security", "audit"],
    "e2e": ["e2e"],
}
ORDER = ["format", "lint", "types", "docs", "security", "tests", "deadcode", "audit", "e2e"]
TAIL = 40


def sh(argv, cwd, timeout=3600, env=None):
    try:
        p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout, env=dict(os.environ, **env) if env else None)
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
    def __init__(self, cat, lang, argv, tool, cwd="", shell_note="", skip="", cover="", requires=(), env=None):
        self.cat, self.lang, self.argv, self.tool, self.cwd = cat, lang, argv, tool, cwd
        self.note = shell_note
        self.skip = skip
        self.cover = cover          # report kind the gate parses itself to prove 100% (never the script's threshold)
        self.requires = tuple(requires)
        self.env = env or {}

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


def configured_types(top):
    """The type checker the project configures ('' when none): never silently replaced by another."""
    cfg = text(top, "pyproject.toml") + text(top, "setup.cfg")
    if "[tool.basedpyright" in cfg:
        return "basedpyright"
    if "[tool.pyright" in cfg or os.path.exists(os.path.join(top, "pyrightconfig.json")):
        return "pyright"
    return "mypy" if "[tool.mypy" in cfg or os.path.exists(os.path.join(top, "mypy.ini")) else ""


def python_stages(top, files, only_files):
    py = [f for f in (only_files if only_files is not None else files) if f.endswith(".py")]
    if only_files is not None and not py:
        return []
    tgt = py or ["."]
    cfg = text(top, "pyproject.toml") + text(top, "setup.cfg")
    s = []
    ruff = venv_bin(top, "ruff")
    if "[tool.yapf]" in cfg:  # the project's own formatter wins over ruff format (they disagree on layout)
        s.append(Stage("format", "python", [venv_bin(top, "yapf") or "yapf", "--diff", "--recursive", "--exclude", VENDOR_DIR + "/*"] + tgt, "yapf"))
    else:
        s.append(Stage("format", "python", [ruff or "ruff", "format", "--check"] + tgt, "ruff"))
    s.append(Stage("lint", "python", [ruff or "ruff", "check"] + tgt, "ruff"))
    if only_files is None:
        types = configured_types(top) or next((t for t in ("basedpyright", "pyright", "mypy") if venv_bin(top, t)), "mypy")
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
            "docs": ("docs:check",), "deadcode": ("deadcode", "knip"), "e2e": ("e2e", "test:e2e")}
    for cat, names in pick.items():
        if only_files is not None and cat not in ("format", "lint"):
            continue
        name = next((n for n in names if n in sc), "")
        if name:
            s.append(Stage(cat, "node", run + [name], tool, sub))
        elif cat in ("format", "lint"):
            s.append(Stage(cat, "node", run + [names[0]], tool, sub, "package.json has no '%s' script" % names[0]))
    if only_files is None:
        tname = next((n for n in ("test", "test:coverage", "coverage") if n in sc), "")
        if tname:
            s.append(Stage("tests", "node", run + [tname], tool, sub, cover="node"))
        else:
            s.append(Stage("tests", "node", run + ["test"], tool, sub,
                           "package.json has no test script", cover="node"))
        aud = {"bun": ["bun", "audit"], "pnpm": ["pnpm", "audit", "--audit-level", "high"],
               "yarn": ["yarn", "npm", "audit", "--severity", "high"]}.get(tool, ["npm", "audit", "--audit-level=high"])
        s.append(Stage("audit", "node", aud, aud[0], sub))
    return s


def rust_stages(top, files, only_files):
    s = [Stage("format", "rust", ["cargo", "fmt", "--check"], "cargo"),
         Stage("lint", "rust", ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"], "cargo")]
    if only_files is None:
        s += [Stage("tests", "rust", ["cargo", "llvm-cov", "--all", "--fail-under-lines", "100"], "cargo-llvm-cov"),
              Stage("audit", "rust", ["cargo", "audit"], "cargo-audit")]
    return s


GO_COVER = ('p=$(mktemp) || exit 1; go test -coverprofile="$p" ./... && t=$(go tool cover -func="$p" | '
            'awk \'/^total:/{print $NF}\') && echo "total coverage: $t (required 100.0%)" && [ "$t" = "100.0%" ]; '
            'r=$?; rm -f "$p"; exit $r')


def go_stages(top, files, only_files):
    s = [Stage("format", "go", ["sh", "-c", 'test -z "$(gofmt -l .)"'], "gofmt"),
         Stage("lint", "go", ["go", "vet", "./..."], "go")]
    if only_files is None:
        s += [Stage("tests", "go", ["sh", "-c", GO_COVER], "go"),
              Stage("audit", "go", ["govulncheck", "./..."], "govulncheck")]
    return s


def shell_stages(top, files, only_files):
    sh_files = [f for f in (only_files if only_files is not None else files) if f.endswith((".sh", ".bash"))]
    return [Stage("lint", "shell", ["shellcheck", "-x", "--source-path=SCRIPTDIR"] + sh_files, "shellcheck")] if sh_files else []


def java_stages(top, files, only_files):
    gradle = has(files, "build.gradle", "build.gradle.kts")
    tool = "gradle" if gradle else "mvn"
    s = [Stage("lint", "java", [tool, "-q", "check" if gradle else "verify"], tool)]
    if only_files is None:
        s.append(Stage("tests", "java", [tool, "-q", "test", "jacocoTestReport" if gradle else "jacoco:report"],
                       tool, cover="jacoco"))
    return s


def cmake_stages(top, files, only_files):
    if only_files is not None:
        return []
    fmt = [f for f in files if f.endswith((".c", ".h", ".cc", ".cpp", ".hpp"))]
    gcovr = shlex.quote(venv_bin(top, "gcovr") or "gcovr")
    return [Stage("format", "cmake", ["clang-format", "--dry-run", "--Werror"] + fmt, "clang-format"),
            Stage("tests", "cmake", ["sh", "-c", 'd=$(mktemp -d) && cmake -S . -B "$d" -DCMAKE_C_FLAGS=--coverage '
                   '-DCMAKE_CXX_FLAGS=--coverage -DCMAKE_EXE_LINKER_FLAGS=--coverage && cmake --build "$d" && '
                   'ctest --test-dir "$d" --output-on-failure && ' + gcovr + ' --root . --fail-under-line 100 '
                   '--fail-under-branch 100 "$d"; r=$?; rm -rf "$d"; exit $r'],
                   "gcovr", requires=("cmake", "ctest", "gcovr"))]


def php_stages(top, files, only_files):
    sc = json.loads(text(top, "composer.json") or "{}").get("scripts", {})
    s = [Stage("lint", "php", ["composer", "validate", "--strict"], "composer")]
    if only_files is None:
        s.append(Stage("tests", "php", ["composer", "run", "test"], "composer", "",
                       "" if "test" in sc else "composer.json has no 'test' script", cover="php"))
        s.append(Stage("audit", "php", ["composer", "audit"], "composer"))
    return s


def ruby_stages(top, files, only_files):
    s = [Stage("lint", "ruby", ["bundle", "exec", "rubocop"], "bundle")]
    if only_files is None:
        s += [Stage("tests", "ruby", ["bundle", "exec", "rake", "test"], "bundle", cover="simplecov"),
              Stage("audit", "ruby", ["bundle", "exec", "bundle-audit", "check", "--update"], "bundle")]
    return s


def dotnet_stages(top, files, only_files):
    s = [Stage("format", "dotnet", ["dotnet", "format", "--verify-no-changes"], "dotnet")]
    if only_files is None:
        s += [Stage("tests", "dotnet", ["dotnet", "test", "--collect:XPlat Code Coverage",
                                       "--results-directory", "{cov}"], "dotnet", cover="cobertura"),
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
    hidden = unjudged(files, langs) if sel is None else []
    for lang in hidden:
        for cat in ("lint", "tests"):
            stages.append(Stage(cat, lang, ["true"], "none", "", "no gate stage knows this %s code: define the Makefile target gate-%s-%s for it" % (lang, cat, lang)))
    cats = set()
    for o in (only or []):
        cats |= set(JOBS.get(o, [o]))
    out, seen = [], set()
    for cat in ORDER:
        if cats and cat not in cats:
            continue
        mine = [x for x in stages if x.cat == cat]
        own_langs = [l for l in langs + hidden if make_target(top, "gate-%s-%s" % (cat, l))]
        mine = [x for x in mine if x.lang not in own_langs]
        mine += [Stage(cat, l, ["make", "gate-%s-%s" % (cat, l)], "make") for l in own_langs]
        if make_target(top, "gate-" + cat):
            # the generic target replaces the built-in stages of the detected languages only: a
            # language nothing judges stays refused until its own gate-<category>-<language> exists
            out.append(Stage(cat, "make", ["make", "gate-" + cat], "make"))
            out += [x for x in mine if x.lang in own_langs or x.lang in hidden]
            continue
        out += mine
    return out, langs + unjudged(files, langs)


SKIP_DIRS = {".git", ".tk", "node_modules", "venv", ".venv", ".cache", "vendor"}
NODE_REPORTS = ("coverage-summary.json", "lcov.info", "clover.xml", "cobertura-coverage.xml", "coverage.cobertura.xml")
JAVA_REPORTS = ("jacoco.xml", "jacocoTestReport.xml")
PHP_REPORTS = ("clover.xml", "cobertura.xml", "coverage.cobertura.xml", "cobertura-coverage.xml", "coverage.xml")


def _walk(top):
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


def _fresh(path, started):
    try:
        return os.path.getmtime(path) >= started - 1
    except OSError:
        return False


def _reports(root, started, names):
    """Fresh report files under root, in preference order: a stale report from an
    earlier run can never prove this run's coverage."""
    hits = [p for p in _walk(root) if os.path.basename(p) in names and _fresh(p, started)]
    return sorted(hits, key=lambda p: (names.index(os.path.basename(p)), p))


def _judge(metrics):
    lines = metrics.get("lines")
    if not lines or not lines[1]:
        return False, "coverage below 100%: the report holds no executable lines"
    if lines[0] != lines[1]:
        return False, "coverage below 100%%: lines %d/%d (%.1f%%)" % (
            lines[0], lines[1], 100.0 * lines[0] / lines[1])
    branches = metrics.get("branches")
    if branches and branches[1] and branches[0] != branches[1]:
        return False, "coverage below 100%%: branches %d/%d (%.1f%%)" % (
            branches[0], branches[1], 100.0 * branches[0] / branches[1])
    return True, ""


def _lcov_metrics(path):
    lf = lh = brf = brh = da = dah = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("LF:"):
                lf += int(line[3:] or 0)
            elif line.startswith("LH:"):
                lh += int(line[3:] or 0)
            elif line.startswith("BRF:"):
                brf += int(line[4:] or 0)
            elif line.startswith("BRH:"):
                brh += int(line[4:] or 0)
            elif line.startswith("DA:"):
                parts = line[3:].split(",")
                da += 1
                if len(parts) > 1 and int(parts[1] or 0) > 0:
                    dah += 1
    if not lf and da:
        lf, lh = da, dah
    if not lf:
        raise ValueError("no line records")
    return {"lines": (lh, lf), "branches": (brh, brf) if brf else None}


def _istanbul_metrics(path):
    with open(path, encoding="utf-8") as fh:
        total = json.load(fh).get("total") or {}
    lines = total.get("lines") or {}
    branches = total.get("branches") or {}
    lt, lc = int(lines.get("total", 0)), int(lines.get("covered", 0))
    if not lt:
        raise ValueError("no line totals")
    bt, bc = int(branches.get("total", 0)), int(branches.get("covered", 0))
    return {"lines": (lc, lt), "branches": (bc, bt) if bt else None}


def _xml_metrics(path):
    """Cobertura (coverage/@line-rate, class/line/@hits) or Clover (project/metrics)."""
    root = ET.parse(path).getroot()
    if root.get("line-rate") is not None:
        elems = root.findall(".//line")
        if elems:
            lines = (sum(1 for e in elems if float(e.get("hits", "0")) > 0), len(elems))
            bc = bt = 0
            for e in elems:
                m = re.search(r"\((\d+)/(\d+)\)", e.get("condition-coverage", ""))
                if m:
                    bc, bt = bc + int(m.group(1)), bt + int(m.group(2))
            if bt:
                branches = (bc, bt)
            else:
                rate = root.get("branch-rate")
                branches = (0, 1) if rate is not None and float(rate) < 1.0 else None
        else:
            lines = (1 if float(root.get("line-rate")) >= 1.0 else 0, 1)
            rate = float(root.get("branch-rate", "1"))
            branches = (0, 1) if rate < 1.0 else None
        return {"lines": lines, "branches": branches}
    metrics = root.find("project/metrics")
    if metrics is None:
        raise ValueError("no Clover project/metrics element")
    st, sc = int(metrics.get("statements", 0)), int(metrics.get("coveredstatements", 0))
    if not st:
        raise ValueError("no statement totals")
    ct, cc = int(metrics.get("conditionals", 0)), int(metrics.get("coveredconditionals", 0))
    return {"lines": (sc, st), "branches": (cc, ct) if ct else None}


def _jacoco_metrics(path):
    root = ET.parse(path).getroot()
    counters = {c.get("type"): (int(c.get("covered", 0)), int(c.get("missed", 0)))
                for c in root.findall("counter")}
    if "LINE" not in counters:
        raise ValueError("no LINE counter")
    lc, lm = counters["LINE"]
    branches = None
    if "BRANCH" in counters:
        bc, bm = counters["BRANCH"]
        branches = (bc, bc + bm)
    return {"lines": (lc, lc + lm), "branches": branches}


def _simplecov_metrics(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    seen = {}
    for suite in data.values():
        for fname, value in ((suite or {}).get("coverage") or {}).items():
            lines = value.get("lines") if isinstance(value, dict) else value
            if not isinstance(lines, list):
                continue
            for index, hit in enumerate(lines):
                if hit is None:
                    continue
                if not isinstance(hit, (int, float)):
                    raise ValueError("non-numeric line hit count in %s" % fname)
                key = (fname, index)  # merge suites without counting a line twice
                seen[key] = seen.get(key, False) or bool(hit and hit > 0)
    if not seen:
        raise ValueError("no executable lines")
    return {"lines": (sum(1 for v in seen.values() if v), len(seen))}


def _judge_file(path, parser):
    try:
        return _judge(parser(path))
    except (OSError, ValueError, ET.ParseError) as e:
        return False, "unreadable coverage report %s: %s" % (os.path.relpath(path), e)


def _judge_all(pairs, root):
    """Judge every fresh report: one low or unreadable report fails the
    stage, so a multi-module run cannot hide behind the first report found."""
    for path, parser in pairs:
        ok, reason = _judge_file(path, parser)
        if not ok:
            try:
                rel = os.path.relpath(path, root)
            except ValueError:
                rel = path
            return False, reason + " [" + rel + "]"
    return True, ""


def verify_cover(top, st, started, tmp=""):
    """Prove 100% coverage from the raw report this run wrote. The project script
    and its configured threshold are never trusted: missing, stale or unreadable
    reports FAIL the stage (never a silent pass, never a skip)."""
    root = tmp or (os.path.join(top, st.cwd) if st.cwd else top)
    if st.cover == "simplecov":
        found = _reports(root, started, (".resultset.json",))
        if not found:
            return False, ("no SimpleCov resultset produced by this run: require 'simplecov' and start it "
                           "before the suite (expects coverage/.resultset.json)")
        return _judge_all([(p, _simplecov_metrics) for p in found], root)
    if st.cover == "jacoco":
        found = _reports(root, started, JAVA_REPORTS)
        if not found:
            return False, ("no JaCoCo XML report produced by this run: configure jacoco:report (Maven) or "
                           "jacocoTestReport with reports { xml.required = true } (Gradle)")
        return _judge_all([(p, _jacoco_metrics) for p in found], root)
    if st.cover == "node":
        found = _reports(root, started, NODE_REPORTS)
        if not found:
            return False, ("no coverage report produced by this run: expected coverage-summary.json, "
                           "lcov.info or a Cobertura XML (enable the runner's coverage reporter, e.g. c8 or nyc)")
        parsers = {"coverage-summary.json": _istanbul_metrics, "lcov.info": _lcov_metrics}
        return _judge_all([(p, parsers.get(os.path.basename(p), _xml_metrics)) for p in found], root)
    if st.cover == "php":
        found = _reports(root, started, PHP_REPORTS)
        if not found:
            return False, ("no PHP coverage report produced by this run: expected clover.xml or a Cobertura "
                           "XML (phpunit --coverage-clover/--coverage-cobertura; needs Xdebug or PCOV)")
        return _judge_all([(p, _xml_metrics) for p in found], root)
    found = _reports(root, started, ("coverage.cobertura.xml", "cobertura-coverage.xml"))
    if not found:
        return False, ("no coverage report produced by this run: expected coverage.cobertura.xml "
                       "(dotnet test --collect:\"XPlat Code Coverage\"; the test project needs coverlet.collector)")
    return _judge_all([(p, _xml_metrics) for p in found], root)


def execute(top, st):
    if st.note:
        return False, "missing: " + st.note
    for tool in st.requires:
        if not venv_bin(top, tool):
            return False, "missing tool: %s (required by the 100%% coverage stage of %s)" % (tool, st.lang)
    exe = st.argv[0]
    if not (os.path.isabs(exe) and os.access(exe, os.X_OK)) and not shutil.which(exe):
        if st.cover:
            return False, "missing tool: %s (required by the 100%% coverage stage of %s)" % (st.tool, st.lang)
        return False, "missing tool: %s (required by the detected %s language)" % (st.tool, st.lang)
    if st.tool == "pytest":
        py = os.path.join(os.path.dirname(exe), "python") if os.path.isabs(exe) else sys.executable
        if sh([py, "-c", "import pytest_cov"], top)[0] != 0:
            return False, "missing tool: pytest-cov (required by the 100% coverage stage)"
    tmp = ""
    argv = list(st.argv)
    if any("{cov}" in a for a in argv):
        tmp = tempfile.mkdtemp(prefix="tk-gate-cov-")  # keep test artifacts out of the repository
        argv = [a.replace("{cov}", tmp) for a in argv]
    try:
        started = time.time()
        code, out = sh(argv, os.path.join(top, st.cwd) if st.cwd else top, env=st.env)
        if st.cat == "tests" and st.lang == "python" and code == 5:
            return False, "no test collected: a project ships tests with its code"
        tail = "\n".join(out.splitlines()[-TAIL:])
        ok = code == 0
        if ok and st.cover:
            ok, why = verify_cover(top, st, started, tmp)
            if not ok:
                tail = (why + "\n" + tail).strip()
        return ok, tail
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


INSTALL = {
    "python": [["{py}", "-m", "pip", "install", "--quiet", "ruff", "mypy", "bandit", "pytest", "pytest-cov", "pip-audit"]],
    "cmake": [["{py}", "-m", "pip", "install", "--quiet", "gcovr"]],
    "rust": [["rustup", "component", "add", "rustfmt", "clippy", "llvm-tools-preview"], ["cargo", "install", "cargo-audit", "cargo-llvm-cov", "--locked"]],
    "go": [["go", "install", "golang.org/x/vuln/cmd/govulncheck@latest"]],
}


def install_commands(top, langs, files):
    """(language, argv) of every command provisioning the toolchain the gate stages will call."""
    cmds = [(l, c) for l in langs for c in INSTALL.get(l, [])]
    if "node" in langs:
        run_, tool = node_runner(files)
        frozen = {"bun": ["bun", "install", "--frozen-lockfile"], "pnpm": ["pnpm", "install", "--frozen-lockfile"],
                  "yarn": ["yarn", "install", "--frozen-lockfile"]}.get(tool, ["npm", "ci"])
        cmds.append(("node", frozen))
    if "python" in langs:
        cfg = text(top, "pyproject.toml") + text(top, "setup.cfg")
        extra = [tool for mark, tool in (("[tool.yapf", "yapf"), ("pydoclint", "pydoclint")) if mark in cfg]
        extra += [t for t in [configured_types(top)] if t and t != "mypy"]
        if extra:
            cmds.append(("python", ["{py}", "-m", "pip", "install", "--quiet"] + extra))
        for req in ("requirements.txt", "requirements-dev.txt"):
            if req in files:
                cmds.append(("python", ["{py}", "-m", "pip", "install", "--quiet", "-r", req]))
    return cmds


def install(top, langs, files):
    """Provision the toolchain of the detected languages (CI runners start empty)."""
    cmds = install_commands(top, langs, files)
    bad = 0
    venv = tool_venv(top)
    py = os.path.join(venv, "bin", "python")
    if any("{py}" in a for _, c in cmds for a in c) and not os.access(py, os.X_OK):
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
