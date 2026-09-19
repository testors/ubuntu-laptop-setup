// SPDX-License-Identifier: MIT
import GLib from 'gi://GLib';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {UnlockDialog} from 'resource:///org/gnome/shell/ui/unlockDialog.js';

import {PromptController} from './controller.js';

export default class DirectUnlock extends Extension {
    enable() {
        this._connections = [];
        this._sleeping = false;
        const shield = Main.screenShield;
        if (!shield || Main.sessionMode.isGreeter)
            return;

        const shades = [shield._shortLightbox, shield._longLightbox];
        this._controller = new PromptController({
            readState: () => {
                const dialog = shield._dialog;
                return {
                    locked: shield.locked,
                    active: shield.active,
                    unlockSession: !Main.sessionMode.isGreeter &&
                        Main.sessionMode.currentMode === 'unlock-dialog',
                    ready: dialog instanceof UnlockDialog &&
                        dialog.visible && !!dialog._promptBox && !!dialog._clock,
                    sleeping: this._sleeping,
                    shaded: shades.some(shade => shade.visible),
                    // Do not reset a password, a running verification, or a failure.
                    promptVisible: !!dialog &&
                        (dialog._activePage === dialog._promptBox ||
                         !!dialog._promptBox?.visible),
                };
            },
            activate: () => shield._dialog.activate(),
            schedule: callback => GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                callback();
                return GLib.SOURCE_REMOVE;
            }),
            cancel: id => GLib.Source.remove(id),
            reportError: error => console.error(`${this.uuid}:`, error),
        });

        const request = () => this._controller.request();
        for (const signal of ['locked-changed', 'lock-screen-shown', 'wake-up-screen'])
            this._connect(shield, signal, request);

        // User activity hides the lightboxes without always emitting wake-up-screen.
        // Waiting for hide also avoids authenticating while the display is blanked.
        for (const shade of shades)
            this._connect(shade, 'notify::visible', request);

        this._connect(shield._loginManager, 'prepare-for-sleep', (_manager, sleeping) => {
            this._sleeping = sleeping;
            if (!sleeping)
                request();
        });
        request();
    }

    _connect(object, signal, callback) {
        this._connections.push([object, object.connect(signal, callback)]);
    }

    disable() {
        this._controller?.stop();
        this._controller = null;
        for (const [object, id] of this._connections ?? [])
            object.disconnect(id);
        this._connections = [];
        this._sleeping = false;
    }
}
