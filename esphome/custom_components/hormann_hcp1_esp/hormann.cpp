#include "hoermann.h"

static const uint8_t crctable[256] = {
  0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15, 0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
  0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
  0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
  0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
  0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
  0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
  0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
  0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
  0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
  0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
  0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
  0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
  0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
  0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
  0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
  0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3
};

void HoermannComponent::setup() {
  // init HA state
  ha_state_.cover = cover_stopped;
  ha_state_.venting = false;
  ha_state_.error = false;
  ha_state_.prewarn = false;
  ha_state_.light = false;
  ha_state_.option_relay = false;
  ha_state_.data_valid = false;

  // reset parser
  rx_counter_ = -1;
  rx_expected_length_ = 0;
  rx_message_ready_ = false;
  tx_message_ready_ = false;
  tx_length_ = 0;
  slave_response_data_ = RESPONSE_DEFAULT;
  broadcast_status_ = 0;
}

uint8_t HoermannComponent::calc_crc8(const uint8_t *p_data, uint8_t length) const {
  uint8_t crc = CRC8_INITIAL_VALUE;
  for (uint8_t i = 0; i < length; i++) {
    uint8_t data = (*p_data++) ^ crc;
    crc = crctable[data];
  }
  return crc;
}

void HoermannComponent::feed_rx_byte(uint8_t data) {
  // Modeled after hoermann_rx_isr() behavior on PIC
  if (rx_message_ready_) {
    // message not yet handled — drop incoming bytes (matching original)
    (void) data;
    return;
  }

  // framing: we set counter to 0 on first valid character (like PIC)
  if (rx_counter_ < 0) {
    // start new frame
    rx_counter_ = 0;
    rx_expected_length_ = 0;
  }

  // store byte
  rx_buffer_[rx_counter_] = data;
  rx_counter_++;

  if (rx_counter_ == 2) {
    // second byte contains length in low nibble
    rx_expected_length_ = (data & 0x0F) + 3; // ADR + LEN + CRC
    // safeguard
    if (rx_expected_length_ > (int)sizeof(rx_buffer_)) {
      rx_counter_ = -1;
      rx_expected_length_ = 0;
      return;
    }
  } else if (rx_expected_length_ != 0 && rx_counter_ == rx_expected_length_) {
    // full frame received
    if (calc_crc8(rx_buffer_, rx_expected_length_) == 0x00) {
      // copy into local buffer and mark ready
      rx_message_ready_ = true;
      // parse immediately instead of deferring to main loop
      parse_message_from_buffer();
    }
    rx_counter_ = -1;
    rx_expected_length_ = 0;
  }
}

void HoermannComponent::parse_message_from_buffer() {
  // Use rx_buffer_ contents (length already validated)
  uint8_t length_nibble = rx_buffer_[1] & 0x0F;
  uint8_t counter = (rx_buffer_[1] & 0xF0) + 0x10;

  // Broadcast message handling (address 0x00)
  if (rx_buffer_[0] == BROADCAST_ADDR && length_nibble == 0x02) {
    // payload bytes at rx_buffer_[2] (low) and rx_buffer_[3] (high)
    broadcast_status_ = rx_buffer_[2] | ((uint16_t)rx_buffer_[3] << 8);
    update_ha_state_from_broadcast(broadcast_status_);
  }

  // If targeted at our UAP1
  if (rx_buffer_[0] == UAP1_ADDR) {
    // Bus scan?
    if ((length_nibble == 0x02) && (rx_buffer_[2] == CMD_SLAVE_SCAN)) {
      prepare_response_for_scan(counter);
      // schedule transmit after 3 ms (matching PIC behaviour: wait 3ms before reply)
      tx_send_at_ms_ = millis() + 3;
      tx_message_ready_ = true;
    }
    // Slave status request?
    if ((length_nibble == 0x01) && (rx_buffer_[2] == CMD_SLAVE_STATUS_REQUEST)) {
      prepare_response_for_status_request(counter);
      tx_send_at_ms_ = millis() + 3;
      tx_message_ready_ = true;
    }
  }

  rx_message_ready_ = false; // handled
}

void HoermannComponent::prepare_response_for_scan(uint8_t counter) {
  // tx_buffer_ as in PIC: ADR | LEN|CNT | TYPE | ADDR | CRC
  tx_buffer_[0] = MASTER_ADDR;
  tx_buffer_[1] = 0x02 | counter;
  tx_buffer_[2] = UAP1_TYPE;
  tx_buffer_[3] = UAP1_ADDR;
  tx_buffer_[4] = calc_crc8(tx_buffer_, 4);
  tx_length_ = 5;
}

void HoermannComponent::prepare_response_for_status_request(uint8_t counter) {
  tx_buffer_[0] = MASTER_ADDR;
  tx_buffer_[1] = 0x03 | counter;
  tx_buffer_[2] = CMD_SLAVE_STATUS_RESPONSE;
  tx_buffer_[3] = (uint8_t)slave_response_data_;
  tx_buffer_[4] = (uint8_t)(slave_response_data_ >> 8);
  slave_response_data_ = RESPONSE_DEFAULT;
  tx_buffer_[5] = calc_crc8(tx_buffer_, 5);
  tx_length_ = 6;
}

void HoermannComponent::send_tx_buffer_immediate() {
  // write bytes via UARTDevice helper
  // write_array expects pointer/len - use write_array or write() in a loop
  for (uint8_t i = 0; i < tx_length_; i++) {
    write(tx_buffer_[i]);
  }
  // flush is not available; writing will use ESPHome UART which manages DE pin if RS485 configured
  tx_message_ready_ = false;
  tx_length_ = 0;
}

void HoermannComponent::update_ha_state_from_broadcast(uint16_t broadcast) {
  // Map bits exactly as your ESP8266 parsing did
  // byte low = bits in broadcast & 0xFF = rx_buffer[2]
  // byte high = (broadcast >> 8) & 0xFF = rx_buffer[3]
  uint8_t low = (uint8_t)(broadcast & 0xFF);
  uint8_t high = (uint8_t)((broadcast >> 8) & 0xFF);

  // cover
  if ((low & 0x01) == 0x01) {
    ha_state_.cover = cover_open;
  } else if ((low & 0x02) == 0x02) {
    ha_state_.cover = cover_closed;
  } else if ((low & 0x60) == 0x40) {
    ha_state_.cover = cover_opening;
  } else if ((low & 0x60) == 0x60) {
    ha_state_.cover = cover_closing;
  } else {
    ha_state_.cover = cover_stopped;
  }

  // option_relay
  ha_state_.option_relay = ((low & 0x04) == 0x04);

  // light
  ha_state_.light = ((low & 0x08) == 0x08);

  // error
  ha_state_.error = ((low & 0x10) == 0x10);

  // venting
  ha_state_.venting = ((low & 0x80) == 0x80);

  // prewarn from high byte bit0
  ha_state_.prewarn = ((high & 0x01) == 0x01);

  ha_state_.data_valid = true;

  // Publish states to Home Assistant via ESPHome entities:
  // For simplicity we use publish_state() on template sensors in YAML (they'll query get_state())
  // Also call logger
  ESP_LOGD("hoermann", "Broadcast: 0x%04X cover=%d vent=%d light=%d error=%d prewarn=%d option=%d",
           broadcast,
           ha_state_.cover,
           (int)ha_state_.venting,
           (int)ha_state_.light,
           (int)ha_state_.error,
           (int)ha_state_.prewarn,
           (int)ha_state_.option_relay);
}

void HoermannComponent::loop() {
  // Read any incoming bytes from UART
  while (available()) {
    uint8_t b = read();
    feed_rx_byte(b);
  }

  // If we have a scheduled TX and 3ms passed, send it
  if (tx_message_ready_ && ((int32_t)(millis() - tx_send_at_ms_) >= 0)) {
    // Ensure we stop reading while sending? write() handles DE toggling if uart.rs485 configured
    send_tx_buffer_immediate();
  }
}

void HoermannComponent::trigger_action(hoermann_action_t action) {
  // replicate hoermann_trigger_action() from PIC
  switch (action) {
    case hoermann_action_stop:
      // Motor needs only to be stopped if running (broadcast bits 0x60)
      if (((broadcast_status_ & 0x60) == 0x40) || ((broadcast_status_ & 0x60) == 0x60)) {
        slave_response_data_ = RESPONSE_IMPULSE;
      }
      break;
    case hoermann_action_open:
      slave_response_data_ = RESPONSE_OPEN;
      break;
    case hoermann_action_close:
      slave_response_data_ = RESPONSE_CLOSE;
      break;
    case hoermann_action_venting:
      slave_response_data_ = RESPONSE_VENTING;
      break;
    case hoermann_action_toggle_light:
      slave_response_data_ = RESPONSE_TOGGLE_LIGHT;
      break;
    case hoermann_action_emergency_stop:
      slave_response_data_ = RESPONSE_EMERGENCY_STOP;
      break;
    case hoermann_action_impulse:
      slave_response_data_ = RESPONSE_IMPULSE;
      break;
    default:
      break;
  }
}

hoermann_state_t HoermannComponent::get_state() {
  return ha_state_;
}
