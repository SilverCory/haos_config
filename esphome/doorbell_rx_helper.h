#pragma once
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include "driver/rmt_tx.h"
#include "soc/gpio_sig_map.h"
#include "hal/gpio_hal.h"
#include "esp_rom_gpio.h"

// Subclass accessor to reach protected channel_ member of
// RemoteTransmitterComponent without modifying ESPHome source.
class DoorbellTxHelper
    : public esphome::remote_transmitter::RemoteTransmitterComponent {
 public:
  // After cc1101.begin_tx() calls pin_mode(FLAG_OUTPUT), the GPIO IO_MUX is
  // reset to plain software GPIO, breaking the RMT peripheral's GPIO matrix
  // route. This function re-routes the RMT TX channel output back to the pin
  // by calling esp_rom_gpio_connect_out_signal() with the channel's signal idx.
  static void reattach_rmt(
      esphome::remote_transmitter::RemoteTransmitterComponent *comp,
      uint8_t gpio_num) {
    auto *self = static_cast<DoorbellTxHelper *>(comp);
    // Get the RMT TX channel number from the handle.
    // On ESP32, rmt_channel_handle_t wraps a channel index 0-7.
    // rmt_tx_get_channel_id() retrieves it portably on IDF 5.x.
    int channel_id = 0;
    rmt_tx_get_channel_id(self->channel_, &channel_id);
    // RMT TX signal indices on ESP32: channel 0 = RMT_SIG_OUT0_IDX (87), etc.
    uint32_t signal_idx = RMT_SIG_OUT0_IDX + channel_id;
    esp_rom_gpio_connect_out_signal(gpio_num, signal_idx, false, false);
  }
};
