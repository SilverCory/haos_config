#pragma once
#include "esphome/components/cc1101/cc1101.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "rom/ets_sys.h"

// Subclass accessor to reach protected strobe_() / write_() on CC1101Component
// without modifying ESPHome source.
class DoorbellCC1101Helper : public esphome::cc1101::CC1101Component {
 public:
  // Strobe a CC1101 command register.
  static uint8_t pub_strobe(esphome::cc1101::CC1101Component *comp,
                            esphome::cc1101::Command cmd) {
    return static_cast<DoorbellCC1101Helper *>(comp)->strobe_(cmd);
  }

  // Write a byte value to a CC1101 configuration register.
  static void pub_write(esphome::cc1101::CC1101Component *comp,
                        esphome::cc1101::Register reg, uint8_t value) {
    static_cast<DoorbellCC1101Helper *>(comp)->write_(reg, value);
  }

  // Enter IDLE state via strobe (blocks until IDLE or timeout).
  static void pub_enter_idle(esphome::cc1101::CC1101Component *comp) {
    static_cast<DoorbellCC1101Helper *>(comp)->enter_idle_();
  }

  // Enter TX state via calibrated strobe sequence.
  // Returns true on success (PLL locked).
  static bool pub_enter_tx(esphome::cc1101::CC1101Component *comp) {
    return static_cast<DoorbellCC1101Helper *>(comp)->enter_tx_();
  }
};

// Bit-bang the doorbell OOK signal on gpio_num.
// The CC1101 must already be in async-serial TX mode (PKTCTRL0=0x32, TX state).
// GPIO must already be configured as output before calling.
//
// Pulse timings are in microseconds. Positive = carrier ON, negative = carrier OFF.
// Runs inside a FreeRTOS critical section to avoid scheduler jitter.
static void IRAM_ATTR doorbell_bitbang_ook(uint8_t gpio_num,
                                           const int32_t *pulses, size_t len,
                                           uint32_t repeat_times,
                                           uint32_t inter_repeat_us) {
  portDISABLE_INTERRUPTS();
  for (uint32_t t = 0; t < repeat_times; t++) {
    for (size_t i = 0; i < len; i++) {
      int32_t v = pulses[i];
      if (v > 0) {
        gpio_set_level((gpio_num_t)gpio_num, 1);
        ets_delay_us((uint32_t)v);
      } else {
        gpio_set_level((gpio_num_t)gpio_num, 0);
        ets_delay_us((uint32_t)(-v));
      }
    }
    // inter-repeat gap (pin low)
    gpio_set_level((gpio_num_t)gpio_num, 0);
    if (t + 1 < repeat_times && inter_repeat_us > 0)
      ets_delay_us(inter_repeat_us);
  }
  gpio_set_level((gpio_num_t)gpio_num, 0);
  portENABLE_INTERRUPTS();
}
