import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { generateSyncRetry } from '../scripts/generate-sync-retry.mjs';

const root = path.resolve(import.meta.dirname, '..');
const resultModule = path.join(root, 'src/storage/sync_result.zi');

async function fixture(run) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'sync-retry-proof-'));
    try {
        fs.cpSync(path.join(root, 'laws/sync_retry'), path.join(directory, 'laws/sync_retry'), { recursive: true });
        const policy = path.join(directory, 'laws/sync_retry');
        const output = path.join(directory, 'src/app/sync_retry.zi');
        await run({ directory, policy, output });
    } finally {
        fs.rmSync(directory, { recursive: true, force: true });
    }
}

test('proved table generation is deterministic and repairs stale generated content', async () => {
    await fixture(async ({ policy, output }) => {
        const proof = await generateSyncRetry(policy, output, resultModule);
        assert.equal(proof.laws.length, 11);
        const first = fs.readFileSync(output, 'utf8');
        const mtime = fs.statSync(output).mtimeMs;
        await generateSyncRetry(policy, output, resultModule);
        assert.equal(fs.statSync(output).mtimeMs, mtime);
        fs.writeFileSync(output, 'stale or hand-edited output');
        await generateSyncRetry(policy, output, resultModule);
        assert.equal(fs.readFileSync(output, 'utf8'), first);
    });
});

test('policy changes that break each class of behavior fail their proofs', async () => {
    const mutations = [
        ['      60', '      61'],
        ['      Decision{0, 0, 0}', '      Decision{1, 0, 0}'],
        ['    case AuthFailed{}:\n      stop(attempt)', '    case AuthFailed{}:\n      retry(attempt)'],
        ['    case Capped{}:\n      Capped{}', '    case Capped{}:\n      Initial{}'],
    ];
    for (const [before, after] of mutations) {
        await fixture(async ({ policy, output }) => {
            await generateSyncRetry(policy, output, resultModule);
            const old = fs.readFileSync(output, 'utf8');
            const source = path.join(policy, 'main.bend');
            const text = fs.readFileSync(source, 'utf8');
            assert.ok(text.includes(before));
            fs.writeFileSync(source, text.replace(before, after));
            await assert.rejects(generateSyncRetry(policy, output, resultModule), /LAWS\./);
            assert.equal(fs.readFileSync(output, 'utf8'), old);
        });
    }
});

test('changed runtime enum cannot silently acquire an unproved mapping', async () => {
    await fixture(async ({ directory, policy, output }) => {
        const changedModule = path.join(directory, 'sync_result.zi');
        fs.writeFileSync(changedModule, fs.readFileSync(resultModule, 'utf8').replace('SYNC_AUTH_FAILED', 'SYNC_NEW_RESULT'));
        await assert.rejects(generateSyncRetry(policy, output, changedModule), /result_enum_changed/);
    });
});

test('generation rejects renumbered result codes', async () => {
    await fixture(async ({ directory, policy, output }) => {
        const changedModule = path.join(directory, 'sync_result.zi');
        fs.writeFileSync(changedModule, fs.readFileSync(resultModule, 'utf8').replace('SYNC_OK :: 0', 'SYNC_OK :: 1'));
        await assert.rejects(generateSyncRetry(policy, output, changedModule),
            /result_enum_changed/);
        assert.equal(fs.existsSync(output), false);
    });
});

test('actual Make proof prerequisite rejects broken policy despite existing Ziran source', async () => {
    await fixture(async ({ directory, policy, output }) => {
        fs.mkdirSync(path.join(directory, 'scripts'));
        fs.mkdirSync(path.join(directory, 'vendor'));
        fs.mkdirSync(path.join(directory, 'src/core'), { recursive: true });
        fs.mkdirSync(path.join(directory, 'src/storage'), { recursive: true });
        for (const file of ['scripts/bend-laws.mjs', 'scripts/bend-pin.json',
            'scripts/generate-sync-retry.mjs', 'scripts/generate-storage-layout.mjs',
            'src/storage/sync_result.zi', 'src/core/version.h', 'Makefile']) {
            fs.copyFileSync(path.join(root, file), path.join(directory, file));
        }
        fs.cpSync(path.join(root, 'laws/storage_layout'), path.join(directory, 'laws/storage_layout'),
            { recursive: true });
        fs.mkdirSync(path.join(directory, 'build/packages'), { recursive: true });
        // The package links below are already in place; the manifest and a
        // newer packages.mk keep Make from fetching them again.
        for (const file of ['ziran.toml', 'ziran.lock', 'scripts/packages.sh', 'mk/sync.mk']) {
            fs.mkdirSync(path.dirname(path.join(directory, file)), { recursive: true });
            fs.copyFileSync(path.join(root, file), path.join(directory, file));
        }
        fs.writeFileSync(path.join(directory, 'build/packages.mk'), 'PACKAGES_READY := 1\n');
        fs.symlinkSync(path.join(root, 'build/packages/kryon'), path.join(directory, 'build/packages/kryon'), 'dir');
        fs.symlinkSync(path.join(root, 'build/packages/bend'), path.join(directory, 'build/packages/bend'), 'dir');
        const make = () => spawnSync('make', ['src/app/sync_retry.zi'], {
            cwd: directory, encoding: 'utf8', timeout: 30000,
        });
        const good = make();
        assert.ifError(good.error);
        assert.equal(good.status, 0, good.stdout + good.stderr);
        const old = fs.readFileSync(output, 'utf8');
        const source = path.join(policy, 'main.bend');
        fs.writeFileSync(source, fs.readFileSync(source, 'utf8').replace('      60', '      61'));
        const bad = make();
        assert.ifError(bad.error);
        assert.notEqual(bad.status, 0);
        assert.match(bad.stdout + bad.stderr, /LAWS\./);
        assert.equal(fs.readFileSync(output, 'utf8'), old);
    });
});
