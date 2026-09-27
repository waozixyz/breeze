import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { generateStorageLayout } from '../scripts/generate-storage-layout.mjs';

const root = path.resolve(import.meta.dirname, '..');

async function fixture(run) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'storage-layout-proof-'));
    try {
        const policy = path.join(directory, 'laws/storage_layout');
        fs.cpSync(path.join(root, 'laws/storage_layout'), policy, { recursive: true });
        const output = path.join(directory, 'storage_layout.h');
        await run({ policy, output });
    } finally {
        fs.rmSync(directory, { recursive: true, force: true });
    }
}

test('the checked policy generates the current layout deterministically', async () => {
    await fixture(async ({ policy, output }) => {
        const proof = await generateStorageLayout(policy, output);
        assert.equal(proof.laws.length, 6);
        const first = fs.readFileSync(output, 'utf8');
        const ziranOutput = output.replace(/\.h$/, '.zi');
        const ziran = fs.readFileSync(ziranOutput, 'utf8');
        assert.match(first, /#define STORAGE_DIR_NAME "inbe"/);
        assert.match(first, /#define STORAGE_DB_NAME "inbe\.db"/);
        assert.match(first, /#define STORAGE_DB_NAME_LEGACY "breathing\.db"/);
        assert.match(first, /#define STORAGE_DIR_LEGACY_WINDOWS "BreathSession"/);
        assert.match(first, /#define STORAGE_EXPORT_ENTRY_DB "inbe-data\/inbe\.db"/);
        assert.match(first, /#define STORAGE_IMPORT_ENTRY_COUNT 2/);
        assert.match(first, /"breathing-data\/breathing\.db"/);
        assert.match(first, /#define STORAGE_WEB_HOME "\/home\/inbe"/);
        assert.match(ziran, /CurrentDatabaseEntry :: "inbe-data\/inbe\.db"/);
        assert.match(ziran, /PreviousDirectoryWindows :: "BreathSession"/);
        assert.match(ziran, /ArchiveDirectorySuffix :: "\.before-breathing-migration-"/);
        assert.match(ziran, /PreviousDatabaseEntry :: "breathing-data\/breathing\.db"/);
        assert.match(ziran, /ExportDatabaseTemporaryName :: "export-inbe\.db"/);
        const mtime = fs.statSync(output).mtimeMs;
        const ziranMtime = fs.statSync(ziranOutput).mtimeMs;
        await generateStorageLayout(policy, output);
        assert.equal(fs.statSync(output).mtimeMs, mtime);
        assert.equal(fs.statSync(ziranOutput).mtimeMs, ziranMtime);
        fs.writeFileSync(output, 'stale or hand-edited output');
        fs.writeFileSync(ziranOutput, 'stale or hand-edited module');
        await generateStorageLayout(policy, output);
        assert.equal(fs.readFileSync(output, 'utf8'), first);
        assert.equal(fs.readFileSync(ziranOutput, 'utf8'), ziran);
    });
});

test('policies that change a proved layout guarantee fail', async () => {
    const mutations = [
        [text => text.replace('    case Windows{}:\n      Inbe{}',
                '    case Windows{}:\n      Breathing{}'),
        'every platform selects the current directory'],
        [text => text.replace('def current_db() -> DbName:\n  InbeDb{}',
                'def current_db() -> DbName:\n  BreathingDb{}'),
        'the database filename remains current'],
        [text => text.replace('    case Windows{}:\n      BreathSession{}',
            '    case Windows{}:\n      Inbe{}'),
        'the older directory remains distinct'],
        [text => text.replace('def legacy_db() -> DbName:\n  BreathingDb{}',
            'def legacy_db() -> DbName:\n  InbeDb{}'),
        'the older database name remains stable'],
        [text => text.replace('type Importable is Data:\n  Yes{}',
            'type Importable is Data:\n  Yes{}\n  No{}')
            .replace('    case InbeDataDb{}:\n      Yes{}',
                '    case InbeDataDb{}:\n      No{}'),
        'the export entry remains importable'],
        [text => text.replace('type Importable is Data:\n  Yes{}',
            'type Importable is Data:\n  Yes{}\n  No{}')
            .replace('    case BreathingDataDb{}:\n      Yes{}',
                '    case BreathingDataDb{}:\n      No{}'),
        'the historical archive entry remains importable'],
    ];
    for (const [mutate, reason] of mutations) {
        await fixture(async ({ policy, output }) => {
            await generateStorageLayout(policy, output);
            const old = fs.readFileSync(output, 'utf8');
            const ziranOutput = output.replace(/\.h$/, '.zi');
            const oldZiran = fs.readFileSync(ziranOutput, 'utf8');
            const source = path.join(policy, 'main.bend');
            const before = fs.readFileSync(source, 'utf8');
            const after = mutate(before);
            assert.notEqual(after, before, `mutation target missing: ${reason}`);
            fs.writeFileSync(source, after);
            await assert.rejects(generateStorageLayout(policy, output),
                /LAWS\.|storage\.layout/, reason);
            assert.equal(fs.readFileSync(output, 'utf8'), old);
            assert.equal(fs.readFileSync(ziranOutput, 'utf8'), oldZiran);
        });
    }
});
