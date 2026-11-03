# Same trick as test_session_file.py: pull plan_state out of the script. Run: python3 tests/test_task_plan.py
import json, os, re, tempfile

src = open(os.path.join(os.path.dirname(__file__), "..", "claude-sessions"), encoding="utf-8").read()
PLAN_READY = re.compile(re.search(r'^PLAN_READY = re\.compile\(r"(.*)"\)$', src, re.M).group(1))
exec(re.search(r"^PLAN_CACHE = .*?(?=^def task_sync)", src, re.S | re.M).group(0))

user = lambda text, **kw: dict(type="user", message=dict(content=text), **kw)
said = lambda text: dict(type="assistant", message=dict(content=[dict(type="text", text=text)]))

def state(*lines):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write("".join(json.dumps(l) + "\n" for l in lines))
    return plan_state(f.name)

PROMPT, PLAN = user("post it ending with [task #7 plan ready]"), said("Do X.\n\n[task #7 plan ready]\n")

assert state(PROMPT)["phase"] is None, "the prompt quoting the marker is not a plan"
assert state(PROMPT, said("about [task #7 plan ready] later"))["phase"] is None, "marker must end the message"
s = state(PROMPT, PLAN)
assert s["phase"] == "awaiting_approval" and s["plan"] == "Do X.", s
assert state(PROMPT, PLAN, user("ok, go"))["phase"] == "implementing"
assert state(PROMPT, PLAN, user([dict(type="text", text="ok, go")]))["phase"] == "implementing", "list content too"
assert state(PROMPT, PLAN, user("<command-name>/model</command-name>"))["phase"] == "awaiting_approval"
assert state(PROMPT, PLAN, user("note", isMeta=True))["phase"] == "awaiting_approval"
s = state(PROMPT, PLAN, user("change Y"), said("Do Y.\n[task #7 plan ready]"))
assert s["phase"] == "awaiting_approval" and s["plan"] == "Do Y.", s

epm = dict(type="assistant", message=dict(content=[dict(type="tool_use", id="a", name="ExitPlanMode", input=dict(plan="P"))]))
done = lambda err: dict(type="user", message=dict(content=[dict(type="tool_result", tool_use_id="a", is_error=err)]))
assert state(epm)["phase"] == "awaiting_approval"
assert state(epm, done(False))["phase"] == "implementing"
assert state(epm, done(True))["phase"] == "analyzing"
print("ok")
