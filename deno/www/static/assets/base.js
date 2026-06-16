// deno-lint-ignore no-unused-vars
function copyCodeBlock(codeBlockCount) {
  const codeBlock = document.getElementById(`code-block-${codeBlockCount}`);
  if (!codeBlock) return;

  const code = codeBlock.querySelector("pre");
  if (!code) return;

  navigator.clipboard.writeText(code.textContent)
}
