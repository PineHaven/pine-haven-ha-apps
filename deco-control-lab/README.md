# FREE THE DECO LAB

Package 2.0's fail-closed Home Assistant App for one physically isolated TP-Link
Deco M9 Plus. It installs alongside the read-only production monitor and never
publishes MQTT entities.

The App starts with writes locked. Its baseline run performs only two reads:

- `admin/device`, form `device_list`;
- `admin/wireless`, form `wlan`.

It refuses control unless the reply contains exactly one online controller and
that controller matches the expected spare-unit MAC supplied through protected
Home Assistant App options. The configured lab target must also differ from the
configured production controller target.

The exact firmware version is part of the baseline. A separate firmware-write
compatibility acknowledgement is required after that version has been reviewed;
older firmware is never assumed equivalent to the dissected production version.

When separately armed, the only admitted experiment is:

1. re-read identity and radio state;
2. capture a recognized rollback pair;
3. write channel 11 with `HT20`;
4. verify the readback;
5. hold for the configured 15–300 seconds;
6. restore and verify the captured channel and `HT20`/`HT40` width.

Only one experiment is accepted per App start. A failed candidate call still
enters rollback. There is no generic endpoint, arbitrary payload runner, scan,
optimizer, reboot, client inventory, production-device selector, or Home
Assistant service for radio control.

Do not point this App at the production mesh. Do not enable writes until the
read-only baseline shows `VERIFIED` and the experiment has its own approval.
