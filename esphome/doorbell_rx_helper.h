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

  // Enter RX state WITHOUT calling pin_mode(FLAG_INPUT).
  // begin_rx() calls pin_mode(FLAG_INPUT) which disables the GPIO output
  // driver, preventing gpio_set_level() from working on subsequent TX cycles.
  // This version skips that call so the pin state is managed by the caller.
  static bool pub_enter_rx(esphome::cc1101::CC1101Component *comp) {
    auto *self = static_cast<DoorbellCC1101Helper *>(comp);
    self->enter_idle_();
    return self->enter_rx_();
  }
};

// Bit-bang the doorbell OOK signal on gpio_num.
// The CC1101 must already be in async-serial TX mode (PKTCTRL0=0x32, TX state).
// GPIO must already be configured as output before calling.
//
// Pulse timings are in microseconds. Positive = carrier ON, negative = carrier OFF.
//
// Each repeat is bit-banged inside a FreeRTOS critical section (spinlock) to
// prevent the scheduler from preempting mid-pulse. The critical section is
// released between repeats so the watchdog is fed and WiFi/BT tasks can run.
static portMUX_TYPE doorbell_mux = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR doorbell_bitbang_ook(uint8_t gpio_num,
                                           const int32_t *pulses, size_t len,
                                           uint32_t repeat_times,
                                           uint32_t inter_repeat_us) {
  for (uint32_t t = 0; t < repeat_times; t++) {
    taskENTER_CRITICAL(&doorbell_mux);
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
    gpio_set_level((gpio_num_t)gpio_num, 0);
    taskEXIT_CRITICAL(&doorbell_mux);
    // Inter-repeat gap outside the critical section — watchdog can run here.
    if (t + 1 < repeat_times && inter_repeat_us > 0)
      ets_delay_us(inter_repeat_us);
  }
  gpio_set_level((gpio_num_t)gpio_num, 0);
}
