// The highlighter lives inline in index.html: pull it out. Run: node tests/test_editor_highlight.js
const assert = require("assert"), fs = require("fs"), path = require("path");
const page = fs.readFileSync(path.join(__dirname, "..", "web", "index.html"), "utf8");
const code = page.slice(page.indexOf("const fxDQ ="), page.indexOf("function fxEdPaint"));
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const { fxHighlight, fxIndent } = new Function("esc", `${code}; return { fxHighlight, fxIndent };`)(esc);

const unescape = s => s.replace(/<[^>]*>/g, "").replace(/&(amp|lt|gt|quot|#39);/g, (_, e) => ({ amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'" })[e]);
const has = (html, cls, text) => assert(html.includes(`<span class="${cls}">${esc(text)}</span>`), `${cls} ${text} in ${html}`);

// the layer sits under the textarea, so its text must be the file's text, whatever the language
const samples = {
  "a.js": "const a = `x\n${1}`; // c <b>\nfoo(\"q\\\"\", 'it\\'s') /* m\nl */\n\tif (a) return 0x1f;\n/* unclosed\n'unterminated\n",
  "a.py": "def f(x):\n    '''doc\n    more'''\n    return None # it's\n",
  "a.sh": "#!/bin/sh\nFOO=1 # c\nls -l $FOO | grep \"a\" && echo ${FOO}\nif true; then sudo rm x; fi\n",
  "a.php": "<?php\n$a = new Foo(1); # c\n",
  "a.go": "func main() { s := `raw` }\n",
  "a.css": "/* c */\n.a:hover { --x: #fff; margin: 1px; }\n@media (x) {}\n",
  "a.html": "<!-- c -->\n<a href=\"x\" id='y'>don't & <b>it's</b></a>\n",
  "a.json": "{\"a\": 1, \"b\": [true, \"c\"]}\n",
  "a.yml": "key: 'v'\n- b: 1 # c\nurl: https://x.y\n",
  "a.md": "# T\n- **b** `c` [l](u)\n```\nfence\n```\n",
  "a.txt": "  plain \"text\" <here> & 1\n",
  "": "",
};
for (const [f, text] of Object.entries(samples)) assert.strictEqual(unescape(fxHighlight(text, f)), text, f);

let h = fxHighlight("const s = 'x'; // note\nfoo(1);\nnew Bar", "a.ts");
has(h, "k", "const"); has(h, "s", "'x'"); has(h, "c", "// note"); has(h, "f", "foo"); has(h, "n", "1"); has(h, "t", "Bar");
h = fxHighlight("#!/bin/bash\nX=1\nls -l | grep $X\n  git status\n", "script");
has(h, "c", "#!/bin/bash"); has(h, "f", "ls"); has(h, "f", "grep"); has(h, "f", "git"); has(h, "v", "$X");
assert(!h.includes('class="f">X'), "an assignment is no command");
h = fxHighlight("a#b\necho $#\n", "x.sh");
assert(!h.includes('class="c"'), "# inside a word is no comment");
has(fxHighlight("    x", "a.txt"), "ig", "    ");
assert(!fxHighlight('say "hi"', "a.txt").includes('"s"'), "unknown files stay uncoloured");

assert.strictEqual(fxIndent("a\n\tb"), "\t");
assert.strictEqual(fxIndent("a\n  b"), "  ");
assert.strictEqual(fxIndent("a\n    b"), "    ");
console.log("ok");
