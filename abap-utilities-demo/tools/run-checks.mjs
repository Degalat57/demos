// Runs installed tools only; never downloads or substitutes a JavaScript model for ABAP.
import {createRequire} from 'node:module';
import {readFileSync, existsSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
const require = createRequire(import.meta.url);
let failed = false;
let blocked = false;
function runPackage(name, command, args = []) {
  let file;
  try {
    const manifest = require.resolve(`${name}/package.json`);
    const pkg = JSON.parse(readFileSync(manifest, 'utf8'));
    file = resolve(dirname(manifest), typeof pkg.bin === 'string' ? pkg.bin : pkg.bin[command]);
    console.log(`${command}: installed version ${pkg.version}`);
  } catch {
    console.log(`BLOCKED ${command}: required package ${name} is not installed.`);
    blocked = true;
    return false;
  }
  const result = spawnSync(process.execPath, [file, ...args], {stdio: 'inherit', timeout: 120000});
  if (result.error || result.status !== 0) {
    console.log(`FAILED ${command}: exit ${result.status ?? 'unavailable'}`);
    failed = true;
    return false;
  }
  return true;
}
console.log(`Node ${process.version}; verification on open-source stack, no SAP kernel.`);
runPackage('@abaplint/cli', 'abaplint', ['abaplint.json']);
const transpiled = runPackage('@abaplint/transpiler-cli', 'abap_transpile');
if (transpiled) {
  if (!existsSync('output/index.mjs')) {
    console.log('FAILED unit: generated test runner missing.');
    failed = true;
  } else {
    const result = spawnSync(process.execPath, ['output/index.mjs'], {stdio: 'inherit', timeout: 120000});
    failed ||= result.status !== 0 || Boolean(result.error);
  }
} else {
  console.log('ABAP Unit: 0 executed; passed/failed counts unavailable (runner not generated).');
}
process.exitCode = failed ? 1 : blocked ? 2 : 0;
