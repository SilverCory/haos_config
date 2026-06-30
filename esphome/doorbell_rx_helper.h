#pragma once
#include "esphome/components/remote_receiver/remote_receiver.h"
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include "driver/rmt_rx.h"
#include "driver/rmt_tx.h"

// Subclass accessor to reach protected channel_ members without modifying
// ESPHome source. static_cast to derived type is used only for data member
// access (no virtual dispatch), so it works reliably with GCC/Clang.

class DoorbellTxHelper
    : public esphome::remote_transmitter::RemoteTransmitterComponent {
 public:
  static void reattach_rmt(
      esphome::remote_transmitter::RemoteTransmitterComponent *comp) {
    auto *self = static_cast<DoorbellTxHelper *>(comp);
    // begin_tx() calls pin_mode(FLAG_OUTPUT) which resets GPIO IO_MUX to
    // plain software GPIO, disconnecting the RMT TX peripheral from the pin.
    // Cycling rmt_disable/rmt_enable forces the RMT driver to re-assert its
    // GPIO matrix routing so subsequent rmt_transmit() calls reach the pin.
    rmt_disable(self->channel_);
    rmt_enable(self->channel_);
  }
};
