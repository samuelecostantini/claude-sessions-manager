# The script is a shell heredoc, not importable: pull session_file out of it. Run: python3 tests/test_session_file.py
import hashlib, os, re, shutil, stat, tempfile

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
exec(re.search(r"^def session_file\(.*?(?=^def )", src, re.S | re.M).group(0))

root = tempfile.mkdtemp()
out = tempfile.mkdtemp()
p = lambda n: os.path.join(root, n)
write = lambda n, b: open(p(n), "wb").write(b)
read = lambda n: open(p(n), "rb").read()

write("a.txt", b"one\n")
os.chmod(p("a.txt"), 0o755)
r = session_file(root, "a.txt")
assert r["text"] == "one\n"
s = session_file(root, "a.txt", "two\n", r["ver"])
assert read("a.txt") == b"two\n" and "ver" in s, s
assert stat.S_IMODE(os.stat(p("a.txt")).st_mode) == 0o755, "mode kept"

# changed on disk since it was read: no write unless forced
assert session_file(root, "a.txt", "three\n", r["ver"]) == {"conflict": True} and read("a.txt") == b"two\n"
assert "ver" in session_file(root, "a.txt", "three\n", r["ver"], True) and read("a.txt") == b"three\n"

# CRLF survives the textarea's LF
write("crlf.txt", b"a\r\nb\r\n")
r = session_file(root, "crlf.txt")
session_file(root, "crlf.txt", "a\nb\nc\n", r["ver"])
assert read("crlf.txt") == b"a\r\nb\r\nc\r\n"

# nothing outside the folder, by ../ or by symlink, read or written
open(os.path.join(out, "x"), "w").write("secret")
os.symlink(os.path.join(out, "x"), p("link"))
for rel in ("../" + os.path.basename(out) + "/x", os.path.join(out, "x"), "link", "", "."):
    assert "err" in session_file(root, rel), rel
    assert "err" in session_file(root, rel, "pwn", None, True), rel
assert open(os.path.join(out, "x")).read() == "secret"

# what can't be edited
write("bin", b"a\0b")
write("latin", b"\xff\xfe")
write("big", b"x" * ((1 << 20) + 1))
os.mkfifo(p("fifo"))
os.mkdir(p("dir"))
for rel in ("bin", "latin", "big", "fifo", "dir", "missing", "a\0b"):
    assert "err" in session_file(root, rel), rel
assert "err" in session_file(root, "fifo", "x", None, True) and "err" in session_file(root, "dir", "x", None, True)
assert not [f for f in os.listdir(root) if f.endswith(".tmp")]

shutil.rmtree(root); shutil.rmtree(out)
print("ok")
