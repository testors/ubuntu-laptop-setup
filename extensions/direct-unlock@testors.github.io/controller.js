// SPDX-License-Identifier: MIT

// Keep event coalescing and eligibility independent of Shell for lifecycle tests.
export class PromptController {
    constructor({readState, activate, schedule, cancel, reportError}) {
        this._readState = readState;
        this._activate = activate;
        this._schedule = schedule;
        this._cancel = cancel;
        this._reportError = reportError;
        this._pending = null;
        this._enabled = true;
    }

    request() {
        if (!this._enabled || this._pending !== null)
            return;

        // Read the state after Shell has finished creating/showing its dialog.
        this._pending = this._schedule(() => {
            this._pending = null;
            if (!this._enabled)
                return;
            try {
                const state = this._readState();
                if (state.locked && state.active && state.unlockSession &&
                    state.ready && !state.sleeping && !state.shaded &&
                    !state.promptVisible)
                    this._activate();
            } catch (error) {
                // Leave Shell's ordinary Enter/click authentication path intact.
                this._reportError(error);
            }
        });
    }

    stop() {
        this._enabled = false;
        if (this._pending !== null)
            this._cancel(this._pending);
        this._pending = null;
    }
}
