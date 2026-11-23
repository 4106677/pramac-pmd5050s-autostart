# Pramac generator autostart — owner's guide

## How it works
- **The main control is the REMOTE input** (TAHO/REMOTE terminal). Close the contact (inverter, voltage relay,
  switch) and the generator starts, warms up and connects the load. Open it and the load is disconnected,
  the engine cools down without load and stops.
- Start sequence: ignition (ACC) → up to 3 starter attempts (the starter is released as soon as the engine runs) →
  warm-up → the load contactor closes.
- If the engine stalls while the start signal is still on, the unit starts it again.
- If it does not start in 3 attempts, the ignition is switched off and the page shows “Failed to start after 3 attempts”.

## Connecting to your home Wi-Fi (once)
1. Switch on the generator with the unit (it is powered from the generator battery).
2. On your phone, find the **Generator-Pramac** network; the password is on the unit's label.
3. The setup window opens (if not, open **http://192.168.4.1** in a browser). Language: UA / RU / EN at the top.
4. Tap your home network, enter its password, tap **Connect**.
5. The unit joins your home network and the Generator-Pramac network disappears.

If your home Wi-Fi is gone for more than a minute (new router or password), the Generator-Pramac network
comes back — repeat steps 2–4. The generator keeps running meanwhile.

## Generator page
On your home network, open **http://generator.local**. If the address does not open (common on Android),
find the **generator** device in your router's client list and open its IP address.

On the page:
- At the top — what the unit is doing (waiting, starter, warm-up, running, cool-down, error) and the RPM gauge.
- The big **Start / Stop** button works on the second tap, so it cannot be pressed by accident.
  While the REMOTE input is on, the generator cannot be stopped from the phone: the external signal wins.
- Tiles: external signal, engine running, load connected, engine hours.
- **Settings** — warm-up time before the load is connected and cool-down time before stopping (− / + buttons).
- **Network & board** — network, signal, IP address, firmware version and **Change Wi-Fi network**.
- At the bottom — page language: UA / RU / EN.

## Home Assistant (if you have it)
The device is discovered automatically (ESPHome integration) or can be added manually at generator.local,
port 6053, without an encryption key.

## Safety
- The page on your home network has no password: anyone on your Wi-Fi can control the generator.
- Disconnect the generator battery before working on the wiring.
