# Drives the real `claude-sessions --mcp` over stdio, then reads its call back from a transcript. Run: python3 tests/test_mcp.py
import json, os, re, subprocess, tempfile

script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "claude-sessions")
root = tempfile.mkdtemp()
open(os.path.join(root, "a.txt"), "w").write("a\n")
open(os.path.join(root, "bin"), "wb").write(b"a\0b")

p = subprocess.Popen([script, "--mcp"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def rpc(method, **params):
    p.stdin.write(json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
def show(*paths): return rpc("tools/call", name="show_files", arguments=dict(paths=list(paths)))["result"]

assert rpc("initialize", protocolVersion="2099-01-01")["result"]["protocolVersion"] == "2099-01-01"
# a notification gets no reply: the next line read must answer the ping
p.stdin.write(json.dumps(dict(jsonrpc="2.0", method="notifications/initialized")) + "\n")
assert rpc("ping")["result"] == {}
assert [t["name"] for t in rpc("tools/list")["result"]["tools"]] == ["show_files"]
assert "error" in rpc("nope")

assert not show("a.txt")["isError"]
assert not show(os.path.join(os.path.realpath(root), "a.txt"))["isError"]
for bad in (["a.txt", "missing"], ["../x"], ["bin"], ["/etc/hosts"]):
    r = show(*bad)
    assert r["isError"] and bad[-1] in r["content"][0]["text"], bad
for args in (dict(), dict(paths=[]), dict(paths="a.txt"), dict(paths=[1])):
    assert rpc("tools/call", name="show_files", arguments=args)["result"]["isError"], args

p.stdin.write("not json\n"); p.stdin.flush()
assert json.loads(p.stdout.readline())["error"]["code"] == -32700
p.stdin.close()
assert p.wait(5) == 0

# chatlog: the last call whose result succeeded, resolved against that turn's folder
src = open(script, encoding="utf-8").read()
TX_CACHE, SHOW_TOOL = {}, "mcp__cs__show_files"
tool_line = lambda x: x["name"]
tag = lambda *a: None
exec(re.search(r"^SHOWN = .*?(?=^OWNED, )", src, re.S | re.M).group(0))
def call(i, paths): return dict(type="assistant", cwd="/w", message=dict(content=[dict(type="tool_use", id=i, name=SHOW_TOOL, input=dict(paths=paths))]))
def done(i, err=False): return dict(type="user", message=dict(content=[dict(type="tool_result", tool_use_id=i, is_error=err)]))
tx = os.path.join(root, "t.jsonl")
def write(*lines):
    open(tx, "w").write("".join(json.dumps(l) + "\n" for l in lines) + "broken\n")
    TX_CACHE.clear(); SHOWN.clear(); chatlog(tx)
write(call("1", ["a"]))
assert tx not in SHOWN, "no result yet"
write(call("1", ["a"]), done("1", True))
assert tx not in SHOWN, "failed call"
write(call("1", ["a"]), done("1"), call("2", ["b", "/abs/c"]), done("2"), call("3", ["d"]), done("3", True))
assert SHOWN[tx] == dict(id="2", files=["/w/b", "/abs/c"]), SHOWN
print("ok")
