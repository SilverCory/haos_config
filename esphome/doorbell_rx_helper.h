#pragma once
#include "esphome/components/remote_receiver/remote_receiver.h"
#include "driver/rmt_rx.h"

// Subclass accessor to reach protected channel_ and store_ members of
// RemoteReceiverComponent without modifying ESPHome source.
// static_cast to derived type is used only for data member access (no virtual
// dispatch), so it works reliably with GCC/Clang on this platform.
class DoorbellRxHelper
    : public esphome::remote_receiver::RemoteReceiverComponent {
 public:
  static void pause_rx(
      esphome::remote_receiver::RemoteReceiverComponent *comp) {
    auto *self = static_cast<DoorbellRxHelper *>(comp);
    rmt_disable(self->channel_);
  }

  static void resume_rx(
      esphome::remote_receiver::RemoteReceiverComponent *comp) {
    auto *self = static_cast<DoorbellRxHelper *>(comp);
    rmt_enable(self->channel_);
    rmt_receive(self->channel_,
                const_cast<uint8_t *>(self->store_.buffer),
                self->store_.receive_size, &self->store_.config);
  }
};
