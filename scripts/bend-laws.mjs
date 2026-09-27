// Host-only proof checking and finite policy evaluation. No Bend runtime ships.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const toolDir = path.dirname(fileURLToPath(import.meta.url));
const bendDir = path.resolve(toolDir, '../build/packages/bend/bend2');
const pin = JSON.parse(fs.readFileSync(path.join(toolDir, 'bend-pin.json'), 'utf8'));

function requireLaw(condition, message) {
    if (!condition) {
        throw new Error(`proof.required: ${message}`);
    }
}

async function checker() {
    const [major, minor] = process.versions.node.split('.').map(Number);
    requireLaw(major > 22 || (major === 22 && minor >= 18), 'Node.js 22.18 or newer is required');
    for (const [name, expected] of Object.entries(pin.files)) {
        const file = path.join(bendDir, name);
        requireLaw(fs.existsSync(file), 'run sh scripts/packages.sh to fetch the pinned bend package');
        const actual = createHash('sha256').update(fs.readFileSync(file)).digest('hex');
        requireLaw(actual === expected, `${name} differs from pinned Bend ${pin.version} (${pin.commit})`);
    }
    return import(pathToFileURL(path.join(bendDir, 'bend.ts')).href);
}

// Restrict the proof package to Base and local .bend imports. Validate before
// loading: Bend's general-purpose package loader can otherwise access a hub.
function localFiles(entry) {
    const root = path.dirname(entry);
    const files = new Set();
    function visit(file) {
        const real = fs.realpathSync(file);
        const relative = path.relative(root, real);
        requireLaw(relative !== '..' && !relative.startsWith(`..${path.sep}`)
            && !path.isAbsolute(relative), `import leaves proof package: ${file}`);
        if (files.has(real)) {
            return;
        }
        files.add(real);
        for (const line of fs.readFileSync(real, 'utf8').split('\n')) {
            if (!/^\s*import(?:\s|$)/.test(line)) {
                continue;
            }
            if (/^\s*import\s+Base\s*(?:#.*)?$/.test(line)) {
                continue;
            }
            const match = line.match(/^\s*import\s+(\.\/\S+\.bend)\s+as\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:#.*)?$/);
            requireLaw(match, `only Base and ./local.bend imports are allowed: ${line.trim()}`);
            visit(path.resolve(path.dirname(real), match[1]));
        }
    }
    visit(entry);
    requireLaw(files.has(path.join(root, 'LAWS.bend')), 'PROOF.bend must import its sibling LAWS.bend');
    return [...files].sort();
}

export async function checkLaws(proofFile) {
    const entry = fs.realpathSync(proofFile);
    requireLaw(path.basename(entry) === 'PROOF.bend', 'entry point must be PROOF.bend');
    const files = localFiles(entry);
    const Bend = await checker();
    const book = Bend.book_nil();
    const seen = new Map();
    try {
        await Bend.book_load(book, entry, '', seen);
    } catch (error) {
        throw new Error(error?.$ === 'Err' ? Bend.err_show(error) : String(error));
    }
    const lawsFile = path.join(path.dirname(entry), 'LAWS.bend');
    requireLaw(seen.has(lawsFile), 'LAWS.bend was not loaded by the checker');
    for (const [name, declaration] of Object.entries(book.tlds)) {
        requireLaw(!declaration.u, `@unsafe is forbidden: ${name}`);
        requireLaw(!declaration.i || declaration.b === true, `foreign implementation is forbidden: ${name}`);
    }
    for (const [name, template] of Object.entries(book.tmps)) {
        requireLaw(!template.u, `@unsafe template is forbidden: ${name}`);
    }
    try {
        Bend.book_valid(book);
    } catch (error) {
        throw new Error(error?.$ === 'Err' ? Bend.err_show(error) : String(error));
    }
    requireLaw(book.hols === 0 && book.open === 0,
        `${book.hols} proof holes and ${book.open} unproved declarations`);
    const laws = [...fs.readFileSync(lawsFile, 'utf8').matchAll(/^law\s+([A-Za-z_][A-Za-z0-9_]*):/gm)]
        .map(match => match[1]);
    requireLaw(laws.length > 0, 'LAWS.bend must declare laws');

    function value(term) {
        const number = Bend.u32_from_term(term);
        if (number !== null) {
            return number;
        }
        requireLaw(term.$ === 'Ctr', 'finite policy must evaluate to a closed data value');
        return { constructor: term.k, fields: term.x.map(value) };
    }

    // Enumerate the *checked function's* finite domains, then normalize that
    // same implementation in the kernel. This avoids a second model and avoids
    // relying on Bend's optimizing C/JS emitters for this finite-policy path.
    function table(name) {
        const declaration = book.tlds[name];
        requireLaw(declaration?.$ === 'Def' && declaration.v !== null && !declaration.i,
            `unknown or foreign policy: ${name}`);
        const rows = [];
        const domains = [];
        function enumerate(type, term, args) {
            const head = Bend.term_wnf(book, type);
            if (head.$ !== 'All') {
                requireLaw(rows.length < 4096, 'finite table exceeds 4096 rows');
                rows.push({ arguments: args, value: value(Bend.term_snf(book, term)) });
                return;
            }
            requireLaw(head.q.$ !== 'None', 'erased policy parameters cannot index a table');
            const domain = Bend.term_wnf(book, head.A);
            const adt = domain.$ === 'ADT' ? book.tlds[domain.k] : null;
            requireLaw(adt?.$ === 'ADT' && adt.n === 0 && domain.r.length === 0
                && adt.c.length > 0 && adt.c.every(ctor => ctor.n === 0),
            'table parameters must be nonempty enumerations without fields');
            const constructors = adt.c.map(ctor => ctor.k);
            const depth = args.length;
            requireLaw(depth < 8, 'finite table exceeds 8 parameters');
            requireLaw(!domains[depth] || JSON.stringify(domains[depth]) === JSON.stringify(constructors),
                'dependent argument domains cannot form a rectangular table');
            domains[depth] = constructors;
            for (const constructor of constructors) {
                const argument = Bend.Ctr(constructor, []);
                enumerate(head.B(argument), Bend.App(term, argument), [...args, constructor]);
            }
        }
        enumerate(declaration.T, Bend.Ref(name), []);
        return { domains, rows };
    }
    return { laws, files, table, version: pin.version, commit: pin.commit };
}

// Bounded checker runner (law plan phase 2): proof checking happens in a
// separate process with a wall-clock timeout and a memory cap, so a stalled
// or runaway check fails with a diagnostic instead of hanging a gate.
import { spawnSync } from 'node:child_process';
export async function checkLawsProcess(proofFile, opts = {}) {
    const timeoutMs = opts.timeoutMs ?? 120000;
    const maxOldSpaceMb = opts.maxOldSpaceMb ?? 1024;
    const args = [`--max-old-space-size=${maxOldSpaceMb}`,
        new URL('bend-laws.mjs', import.meta.url).pathname, '--json', proofFile];
    const result = spawnSync(process.execPath, args, { encoding: 'utf8', timeout: timeoutMs });
    if (result.error) {
        const reason = result.error.code === 'ETIMEDOUT'
            ? `checker exceeded ${timeoutMs}ms wall-clock limit`
            : `checker could not run: ${result.error.message}`;
        throw new Error(`proof.bounded: ${reason}`);
    }
    if (result.status !== 0) {
        throw new Error(`proof.bounded: checker rejected the package:\n${result.stderr.trim()}`);
    }
    return JSON.parse(result.stdout);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
    try {
        requireLaw(process.argv.length === 3 || (process.argv.length === 4 && process.argv[2] === '--json'),
            'usage: node scripts/bend-laws.mjs [--json] path/to/PROOF.bend');
        const proof = await checkLaws(process.argv[process.argv.length - 1]);
        if (process.argv.includes('--json')) {
            console.log(JSON.stringify({ laws: proof.laws, files: proof.files, version: proof.version, commit: proof.commit }));
        } else {
            console.log(`Bend ${proof.version}: ${proof.laws.length} laws proved; no holes or open declarations`);
        }
    } catch (error) {
        console.error(error.message);
        process.exitCode = 1;
    }
}
