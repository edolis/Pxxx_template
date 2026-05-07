# Summary: PSRAM Trade-offs for ESP32-S3FH4R2 (Super Mini) with ED_S_JSON

Based on our analysis of your chip (`ESP32-S3FH4R2` – 2MB Quad PSRAM) and the board pinout, here are the key observations and conclusions regarding enabling PSRAM for your static JSON library.

## 🔬 Key Facts About Your Hardware

| Feature | Value |
|---------|-------|
| **Chip** | ESP32-S3FH4R2 |
| **Internal Flash** | 4MB |
| **PSRAM type** | **Quad** (2MB, inside the package) |
| **PSRAM bus width** | 4‑bit (Quad SPI) |
| **Exposed conflict pins when PSRAM is enabled** | **3 pins** – GPIO35, GPIO36, GPIO37 |
| **Permanently reserved pins (never exposed)** | GPIO26–32 |
| **Internal SRAM overhead when PSRAM enabled** | ~30–35 KB (for cache / memory mapping) |

## ⚖️ Trade-offs of Enabling PSRAM

### Pros
- **+2MB of extra memory** – useful for large JSON documents, multiple buffers, or other data‑heavy tasks.
- **Reduces heap fragmentation** – large allocations go to PSRAM, preserving internal SRAM for real‑time / ISR code.
- **Enables larger JSON messages** – beyond what internal SRAM (≈512KB total) could comfortably hold.

### Cons
- **Lose 3 exposed GPIOs** – GPIO35, GPIO36, GPIO37 become unavailable for your own sensors, LEDs, or peripherals.
- **Internal SRAM tax** – about 30 KB of internal SRAM is consumed by the PSRAM cache and mapping structures.
- **Slower access** – PSRAM is 5–10× slower than internal SRAM (80–200 ns vs. <20 ns). Not an issue for infrequent MQTT messages.
- **Potential boot / stability issues** if the hardware or configuration is mismatched.

## 📌 Recommendation for Your Use Case

You are building small, 1‑level JSON payloads (sensor readings) for MQTT.
**Internal SRAM (≈512KB total) is more than sufficient** – your typical JSON is probably under 1KB.

**Therefore, the optimal choice is to DISABLE PSRAM.**

### If you disable PSRAM:
- ✅ **All exposed GPIOs are usable** – including GPIO35,36,37.
- ✅ **No internal SRAM tax** – you keep the full ~512KB for critical tasks.
- ✅ **Simpler, more stable** – no PSRAM initialization or conflict risks.
- ❌ You lose the 2MB of external memory – but you don’t need it.

### If you must keep PSRAM (e.g., for future larger messages):
- ⚠️ **Avoid using GPIO35,36,37** in your circuit.
- ✅ Use all other exposed pins (GP1,2,3,4,5,6,7,8,9,10,11,12,13,14,16,17,18,21,33,34,38,39,41,42,45,46,47,48, etc.).
- ⚠️ Accept the ~30KB internal SRAM overhead.

## 🛠️ How to Implement Your Choice

### Disable PSRAM (Recommended)
Add these lines to your `sdkconfig.defaults`:

```cmake
# Disable PSRAM entirely
CONFIG_SPIRAM=n
CONFIG_ESP32S3_SPIRAM_SUPPORT=n
```

Then in `ED_S_JSON`, the buffers will automatically be allocated from internal SRAM (no code change needed, because without PSRAM, heap_caps_malloc with `MALLOC_CAP_SPIRAM` will fall back to internal).

### Keep PSRAM (If you really need it)
Add these lines to your `sdkconfig.defaults`:

```cmake
# Enable Quad PSRAM (correct for your chip)
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_QUAD=y
CONFIG_SPIRAM_TYPE_AUTO=y
CONFIG_ESP32S3_SPIRAM_SUPPORT=y

# Optional: your custom compile flag for ED_S_JSON
CONFIG_ED_S_JSON_USE_PSRAM=y
```

And modify `ED_S_JSON` to allocate from `MALLOC_CAP_SPIRAM` when that flag is set, with runtime fallback to internal SRAM if PSRAM not initialized.

## 📊 Final Memory Impact Comparison

| Scenario | Internal SRAM free (approx) | Usable GPIO loss | Max JSON size (safe) |
|----------|-----------------------------|------------------|----------------------|
| **PSRAM disabled** | ~480 KB (after system) | **None** | ~200 KB (theoretical, but limited by contiguous heap) |
| **PSRAM enabled** | ~450 KB (after tax) | GPIO35,36,37 | **2MB** (limited by PSRAM) |

For your current MQTT messages (few hundred bytes), disabling PSRAM is the clear winner – you keep all pins, avoid complexity, and have more than enough memory.

## ✅ Conclusion

- **Do not enable PSRAM** for your current use case.
- Use all 3 conflict pins for whatever you like.
- Revisit only if you later need to send multi‑kilobyte JSON documents.

The ED_S_JSON library will work perfectly with internal SRAM, and you will have no heap fragmentation issues for typical MQTT workloads.
```