// Run: gjs -m tests/test_direct_unlock.js
// The controller runs unchanged; only Shell imports in the adapter are mocked.
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import {PromptController} from '../extensions/direct-unlock@testors.github.io/controller.js';

let passed = 0;
function assert(condition, description) {
    if (!condition)
        throw new Error(description);
}
function test(description, callback) {
    callback();
    passed++;
    print(`PASS ${description}`);
}
function fixture(overrides = {}) {
    const state = {locked: true, active: true, unlockSession: true, ready: true,
        sleeping: false, shaded: false, promptVisible: false, ...overrides};
    let pending = null;
    let calls = 0;
    const controller = new PromptController({
        readState: () => state,
        activate: () => calls++,
        schedule: callback => { pending = callback; return 42; },
        cancel: () => { pending = null; },
        reportError: error => { throw error; },
    });
    return {state, controller, calls: () => calls, flush: () => {
        const callback = pending;
        pending = null;
        callback?.();
    }};
}

test('coalesces signals and reads state after dialog construction', () => {
    const f = fixture({ready: false});
    f.controller.request();
    f.controller.request();
    f.state.ready = true;
    f.flush();
    assert(f.calls() === 1, 'must open the completed dialog exactly once');
});

test('never opens an unlocked, greeter, sleeping, shaded, or incomplete dialog', () => {
    for (const override of [{locked: false}, {active: false}, {unlockSession: false},
        {sleeping: true}, {shaded: true}, {ready: false}, {promptVisible: true}]) {
        const f = fixture(override);
        f.controller.request();
        f.flush();
        assert(f.calls() === 0, `must not activate ${JSON.stringify(override)}`);
    }
});

test('unlock and disable cancel a previously queued attempt', () => {
    const f = fixture();
    f.controller.request();
    f.state.locked = false;
    f.flush();
    f.state.locked = true;
    f.controller.request();
    f.controller.stop();
    f.flush();
    f.controller.request();
    f.flush();
    assert(f.calls() === 0, 'no activation after unlock or disable');
});

class Emitter {
    constructor() { this.handlers = new Map(); this.next = 1; }
    connect(signal, callback) { const id = this.next++; this.handlers.set(id, {signal, callback}); return id; }
    disconnect(id) { assert(this.handlers.delete(id), 'disconnect valid handler'); }
    emit(signal, ...args) {
        for (const entry of this.handlers.values())
            if (entry.signal === signal)
                entry.callback(this, ...args);
    }
}
class Dialog extends Emitter {
    constructor() {
        super();
        this.visible = true;
        this._promptBox = {visible: false};
        this._clock = {};
        this._activePage = this._clock;
        this.calls = 0;
    }
    activate() { this.calls++; this._activePage = this._promptBox; this._promptBox.visible = true; }
}
const shield = Object.assign(new Emitter(), {
    locked: true, active: true, _dialog: new Dialog(),
    _shortLightbox: Object.assign(new Emitter(), {visible: true}),
    _longLightbox: Object.assign(new Emitter(), {visible: false}),
    _loginManager: new Emitter(),
});
globalThis.directUnlockTest = {
    Main: {screenShield: shield, sessionMode: {isGreeter: false, currentMode: 'unlock-dialog'}},
    UnlockDialog: Dialog,
    Extension: class { constructor() { this.uuid = 'direct-unlock-test'; } },
};
const testDir = GLib.dir_make_tmp('direct-unlock-test-XXXXXX');
const sourceDir = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent()
    .get_child('extensions/direct-unlock@testors.github.io');
const decoder = new TextDecoder();
const read = name => decoder.decode(sourceDir.get_child(name).load_contents(null)[1]);
try {
    let source = read('extension.js');
    source = source.replace(/^import .* from 'resource:.*';$/gm, '');
    source = 'const {Main, UnlockDialog, Extension} = globalThis.directUnlockTest;\n' + source;
    GLib.file_set_contents(`${testDir}/extension.js`, source);
    GLib.file_set_contents(`${testDir}/controller.js`, read('controller.js'));
    const {default: DirectUnlock} = await import(Gio.File.new_for_path(`${testDir}/extension.js`).get_uri());
    const extension = new DirectUnlock();
    const context = GLib.MainContext.default();
    const flush = () => { while (context.pending()) context.iteration(false); };

    test('adapter opens on unblank without Enter; ignores duplicate wake events', () => {
        extension.enable();
        flush();
        assert(shield._dialog.calls === 0, 'blank screen must not start authentication');
        shield._shortLightbox.visible = false;
        shield._shortLightbox.emit('notify::visible');
        shield.emit('wake-up-screen');
        flush();
        assert(shield._dialog.calls === 1, 'wake should open the current user prompt');
        shield.emit('wake-up-screen');
        flush();
        assert(shield._dialog.calls === 1, 'preserve in-progress password/authentication');
    });

    test('adapter does not retry failures or cancellation', () => {
        shield._dialog._activePage = shield._dialog._clock;
        shield._dialog._promptBox.visible = false;
        shield._dialog.emit('failed');
        shield._dialog.emit('cancelled');
        flush();
        assert(shield._dialog.calls === 1, 'failure/cancellation must not trigger retry');
    });

    test('adapter blocks sleep, opens on resume, and completely disconnects', () => {
        shield._loginManager.emit('prepare-for-sleep', true);
        shield.emit('lock-screen-shown');
        flush();
        assert(shield._dialog.calls === 1, 'no authentication during sleep');
        shield._loginManager.emit('prepare-for-sleep', false);
        flush();
        assert(shield._dialog.calls === 2, 'resume opens prompt once');
        shield.emit('wake-up-screen');
        extension.disable();
        flush();
        for (const object of [shield, shield._shortLightbox, shield._longLightbox, shield._loginManager])
            assert(object.handlers.size === 0, 'disable must remove every signal handler');
        assert(shield._dialog.calls === 2, 'disable cancels scheduled activation');
    });
} finally {
    for (const name of ['extension.js', 'controller.js'])
        Gio.File.new_for_path(`${testDir}/${name}`).delete(null);
    Gio.File.new_for_path(testDir).delete(null);
    delete globalThis.directUnlockTest;
}
print(`${passed} test groups passed`);
