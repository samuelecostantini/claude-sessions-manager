# Same trick as test_session_file.py: pull the owned-session code out of the script. Run: python3 tests/test_own_clear.py
import json, os, re, threading, time

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
updates = []
class Conn:
    def execute(self, sql, args): updates.append(args)
def task_q(fn): return fn(Conn())
exec(re.search(r"^OWNED, OWN_LOCK = .*?(?=^def own_start)", src, re.S | re.M).group(0))

class Proc:
    returncode = 0
    def __init__(self, *events): self.stdout = [json.dumps(e) + "\n" for e in events]
    def poll(self): return None
    def wait(self): return 0

def run(sid, *events):
    o = OWNED[sid] = dict(p=Proc(*events), busy=True, pend=None, err=None, log="", closed=False, mode="default", want=None)
    own_read(sid, o)
    return o

init = lambda sid: dict(type="system", subtype="init", session_id=sid, permissionMode="plan")

o = run("a", init("a"), dict(type="result", session_id="a"))
assert owned("a") is o and not updates and not own_moves(), "the same id moves nothing"

o = run("old", init("old"), dict(type="conversation_reset", session_id="old"), dict(type="system", subtype="hook_started", session_id="new"), init("new"), dict(type="result", session_id="new"))
assert owned("new") is o and "old" not in OWNED, "the process follows the new id"
assert o["mode"] == "plan" and o["busy"] is False, "the init and the result are still handled"
assert updates == [("new", "old")], "the task follows too"
assert own_moves() == {"old": "new"}

def broken(fn): raise OSError("no database")
task_q = broken
o = run("old2", init("new2"))
assert owned("new2") is o, "a database error must not stop the reader"

OWN_MOVED["stale"] = ("gone", time.time() - 11)
assert "stale" not in own_moves(), "an old move stops steering the selection"
print("ok")
