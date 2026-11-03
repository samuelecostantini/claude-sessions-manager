# Same trick as test_session_file.py: pull session_git out of the script. Run: python3 tests/test_session_git.py
import os, re, shutil, subprocess, tempfile  # shutil also used by claude_bin

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
exec(re.search(r"^def claude_bin\(.*?(?=^TR_HOME)", src, re.S | re.M).group(0))
exec(re.search(r"^def git_message\(.*?(?=^def session_file)", src, re.S | re.M).group(0))

tmp = tempfile.mkdtemp()
root, remote = os.path.join(tmp, "repo"), os.path.join(tmp, "remote.git")
sh = lambda *a, cwd=root: subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout
write = lambda n, t: open(os.path.join(root, n), "w").write(t)
subprocess.run(["git", "init", "-q", "--bare", remote], check=True)
subprocess.run(["git", "init", "-q", "-b", "main", root], check=True)
sh("config", "user.email", "t@t"); sh("config", "user.name", "t"); sh("config", "commit.gpgsign", "false")

# generate: a stand-in claude that records its prompt and flags
bin_dir = os.path.join(tmp, "bin")
os.mkdir(bin_dir)
open(os.path.join(bin_dir, "claude"), "w").write('#!/bin/sh\necho "$@" > "$CS_T/args"; cat > "$CS_T/prompt"; printf "$CS_OUT"; exit ${CS_RC:-0}\n')
os.chmod(os.path.join(bin_dir, "claude"), 0o755)
os.environ.update(PATH=bin_dir + os.pathsep + os.environ["PATH"], CS_T=tmp, CS_OUT="add a\\n")
INBOX_DIR, CHAT_MODEL = os.path.join(tmp, "inbox"), "haiku"
prompt = lambda: open(os.path.join(tmp, "prompt")).read()

assert session_git(root, "message") == dict(ok=False, out="nothing to commit")
assert not os.path.exists(os.path.join(tmp, "prompt")), "nothing to describe: claude not run"
write("new", "SECRET\n")
assert session_git(root, "message") == dict(ok=True, out="add a"), "unborn HEAD"
assert "new" in prompt() and "SECRET" not in prompt(), "untracked: name only"
args = open(os.path.join(tmp, "args")).read()
assert "--tools  --permission-mode dontAsk" in args and "--setting-sources" in args, args
os.environ["CS_OUT"] = "```\\nfenced\\n```\\n"
assert session_git(root, "message")["out"] == "fenced"
os.environ.update(CS_OUT="boom\\n", CS_RC="3")
assert session_git(root, "message") == dict(ok=False, out="boom")
os.environ.update(CS_OUT="", CS_RC="0")
assert not session_git(root, "message")["ok"], "empty reply"
os.environ["CS_OUT"] = "subject\\n"
assert sh("status", "--porcelain") == "?? new\n", "generate changes nothing"
os.remove(os.path.join(root, "new"))

# nothing runs without a message, or for an action we don't offer
write("a", "1\n")
assert not session_git(root, "commit", "  ")["ok"] and sh("status", "--porcelain") == "?? a\n"
assert not session_git(root, "reset --hard")["ok"]
assert not session_git(root, "commit", "a\0b")["ok"]

# nothing staged: commits everything, untracked included
assert session_git(root, "commit", "-first")["ok"], "message starting with a dash"
assert sh("log", "-1", "--format=%s").strip() == "-first" and sh("status", "--porcelain") == ""

# something staged: only that
write("a", "2\n"); write("b", "1\n"); sh("add", "b")
assert session_git(root, "commit", "only b")["ok"]
assert sh("show", "--name-only", "--format=").split() == ["b"] and sh("status", "--porcelain") == " M a\n"
sh("checkout", "a")

# generate describes what commit would take: staged only, if anything is staged
write("a", "tracked-unstaged\n"); write("b", "staged-line\n"); sh("add", "b")
assert session_git(root, "message")["ok"] and "staged-line" in prompt() and "tracked-unstaged" not in prompt()
sh("reset", "-q"); assert session_git(root, "message")["ok"] and "staged-line" in prompt() and "tracked-unstaged" in prompt()
sh("checkout", "a", "b")

# a clean tree reports why, nothing committed
r = session_git(root, "commit", "empty")
assert not r["ok"] and "nothing to commit" in r["out"], r

# conflicted files are not swept in with their markers
sh("switch", "-qc", "side"); write("a", "side\n"); sh("commit", "-qam", "side")
sh("switch", "-q", "main"); write("a", "main\n"); sh("commit", "-qam", "main")
assert subprocess.run(["git", "merge", "side"], cwd=root, capture_output=True).returncode
assert not session_git(root, "commit", "bad merge")["ok"] and sh("log", "-1", "--format=%s").strip() == "main"
assert "UU a" in sh("status", "--porcelain")
sh("merge", "--abort")

# push fails with git's reason without a remote, then sets the upstream on a new branch; fetch sees new work
assert not session_git(root, "push")["ok"]
sh("remote", "add", "origin", remote)
assert session_git(root, "push")["ok"]
assert sh("rev-parse", "--abbrev-ref", "@{u}").strip() == "origin/main"
other = os.path.join(tmp, "other")
subprocess.run(["git", "clone", "-q", remote, other], check=True)
sh("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "new", cwd=other)
sh("push", "-q", cwd=other)
assert session_git(root, "fetch")["ok"]
assert sh("rev-list", "--count", "HEAD..@{u}").strip() == "1"

# not a repo, or a missing folder: an error, not a crash
assert not session_git(tmp, "fetch")["ok"] and not session_git(tmp + "/nope", "commit", "x")["ok"]

shutil.rmtree(tmp)
print("ok")
