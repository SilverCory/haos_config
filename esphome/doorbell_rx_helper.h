#pragma once
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include "driver/rmt_tx.h"
#include "soc/gpio_sig_map.h"
#include "esp_rom_gpio.h"

// Subclass accessor to reach protected channel_ member of
// RemoteTransmitterComponent without modifying ESPHome source.
class DoorbellTxHelper
    : public esphome::remote_transmitter::RemoteTransmitterComponent {
 public:
  // After cc1101.begin_tx() calls pin_mode(FLAG_OUTPUT), the GPIO IO_MUX is
  // reset to plain software GPIO, breaking the RMT TX peripheral's GPIO matrix
  // route. Re-connect the RMT TX channel signal to the pin directly.
  static void reattach_rmt(
      esphome::remote_transmitter::RemoteTransmitterComponent *comp,
      uint8_t gpio_num) {
    auto *self = static_cast<DoorbellTxHelper *>(comp);
    // On ESP32, RMT TX channel signal indices start at RMT_SIG_OUT0_IDX.
    // The transmitter is the first RMT channel allocated, so channel_id = 0.
    // esp_rom_gpio_connect_out_signal re-routes the peripheral signal through
    // the GPIO matrix to the physical pin, overriding the plain GPIO mode
    // that pin_mode(FLAG_OUTPUT) set.
    (void)self;  // channel_ unused since we hardcode channel 0
    esp_rom_gpio_connect_out_signal(gpio_num, RMT_SIG_OUT0_IDX, false, false);
  }
};
