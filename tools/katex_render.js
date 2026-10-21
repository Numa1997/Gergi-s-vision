// Renders a batch of TeX formulas with KaTeX at build time.
// stdin: JSON [{ tex, display }]; stdout: JSON [{ html } | { error }]. Used by build_theory.py.
const katex = require('katex');
let input = '';
process.stdin.on('data', d => { input += d; });
process.stdin.on('end', () => {
  const out = JSON.parse(input).map(({ tex, display }) => {
    try {
      return { html: katex.renderToString(tex, { displayMode: display, output: 'html', throwOnError: true, strict: 'ignore' }) };
    } catch (e) {
      return { error: String(e.message || e) };
    }
  });
  process.stdout.write(JSON.stringify(out));
});
