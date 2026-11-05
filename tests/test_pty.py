# The script is a shell heredoc, not importable: pull the pty code out of it. Run: python3 tests/test_pty.py
import os, re, subprocess, sys, tempfile, threading, time

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
exec(re.search(r"^import fcntl, select.*?(?=^def server\()", src, re.S | re.M).group(0))
os.environ["SHELL"] = "/bin/sh"
os.environ["ENV"] = ""
os.environ["TERM_SESSION_ID"] = "the-parent-tab"

def until(p, text, secs=10):
    end = time.time() + secs
    while time.time() < end:
        with p["cond"]:
            if text in p["buf"]: return True
            p["cond"].wait(0.2)
    raise AssertionError(f"no {text!r} in {p['buf']!r}")

root = os.path.realpath(tempfile.mkdtemp())
p = pty_open(root, 100, 30)
assert pty_open(root, 100, 30) is p, "one shell per folder"

# runs in the folder, sized, on a tty; printf splits the marker so the echoed command can't match
pty_write(root, 'printf "%s%s %s\\n" MA RK "$(pwd) $(stty size) $TERM"\n')
until(p, f"MARK {root} 30 100 xterm-256color".encode())

pty_write(root, 'printf "%s%s %s\\n" SE SS "${TERM_SESSION_ID-unset}"\n')
until(p, b"SESS unset")

# bash can put the old size back if a resize lands just as a command finishes, zsh does not; wait for its prompt
time.sleep(0.5)
pty_size(p, 120, 40)
pty_write(root, 'printf "%s%s %s\\n" SI ZE "$(stty size)"\n')
until(p, b"SIZE 40 120")

# ctrl-c only reaches the foreground job with a controlling tty: the 60s sleep must end at once
pty_write(root, "sleep 60; printf '%s%s\\n' CU T\n")
time.sleep(0.5)
pty_write(root, "\x03")
until(p, b"CUT\r")

# python's ignored SIGPIPE must not leak: yes dies quietly instead of printing EPIPE errors
pty_write(root, 'yes | head -1 >/dev/null; printf "%s%s\\n" PI PE\n')
until(p, b"PIPE\r")
assert b"roken pipe" not in p["buf"], p["buf"]

# a reader catches up from any offset, and one too far behind skips to what is kept
d, at = pty_chunk(p, 0)
assert at == p["end"] and d == p["buf"]
p["buf"], keep = p["buf"][-5:], p["buf"]
assert pty_chunk(p, 0)[0] == p["buf"]
p["buf"] = keep
assert pty_chunk(p, at, lambda: False) is None, "a gone client stops waiting"

# after exit: gone from the table, readers released, writes refused, next open is a new shell
pty_write(root, "exit\n")
end = time.time() + 10
while not p["done"] and time.time() < end: time.sleep(0.05)
assert p["done"] and root not in PTYS
assert pty_chunk(p, p["end"]) is None
assert pty_write(root, "x") is False
q = pty_open(root, 80, 24)
assert q is not p
pty_write(root, "exit\n")

# no folder, no shell, nothing left behind
try: pty_open(root + "/nope", 80, 24); raise AssertionError("opened")
except OSError: pass
assert root + "/nope" not in PTYS

# zsh: the prompt is only the folder, even over the user's own, and their startup files still load
home = os.path.realpath(tempfile.mkdtemp())
os.makedirs(home + "/proj")
open(home + "/.zshenv", "w").write("export FROM_ENV=1\n")
open(home + "/.zshrc", "w").write("export FROM_RC=1\nPROMPT='someone@host %1~ %# '\n")
os.environ.update(SHELL="/bin/zsh", HOME=home)
z = pty_open(home + "/proj", 100, 30)
until(z, b"proj % ")
assert b"someone@host" not in z["buf"]
pty_write(home + "/proj", 'printf "%s%s %s\\n" ZD OT "${ZDOTDIR-unset} ${CS_ZDOTDIR-unset} $FROM_ENV $FROM_RC"\n')
until(z, b"ZDOT unset unset 1 1")
pty_write(home + "/proj", "exit\n")
print("ok")
