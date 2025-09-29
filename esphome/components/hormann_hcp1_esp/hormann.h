#pragma once
#include "esphome.h"

using namespace esphome;

typedef enum {
  hoermann_action_stop = 0,
  hoermann_action_open = 1,
  hoermann_action_close = 2,
  hoermann_action_venting = 3,
  hoermann_action_toggle_light = 4,
  hoermann_action_emergency_stop = 5,
  hoermann_action_impulse = 6
} hoermann_action_t;

typedef enum {
  cover_stopped = 0,
  cover_open,
  cover_closed,
  cover_opening,
  cover_closing
} cover_state_t;

struct hoermann_state_t {
  cover_state_t cover;
  bool venting;
  bool error;
  bool prewarn;
  bool light;
  bool option_relay;
  bool data_valid;
};

class HoermannComponent : public Component, public UARTDevice {
public:
  HoermannComponent(UARTComponent *parent) : UARTDevice(parent) {}

  void setup() override;
  void loop() override;

  // HA / user API
  void trigger_action(hoermann_action_t action);
  hoermann_state_t get_state();

protected:
  // Protocol constants (matching PIC)
  static const uint8_t BROADCAST_ADDR = 0x00;
  static const uint8_t MASTER_ADDR    = 0x80;
  static const uint8_t UAP1_ADDR      = 0x28;
  static const uint8_t UAP1_TYPE      = 0x14;

  static const uint8_t CMD_SLAVE_SCAN            = 0x01;
  static const uint8_t CMD_SLAVE_STATUS_REQUEST  = 0x20;
  static const uint8_t CMD_SLAVE_STATUS_RESPONSE = 0x29;

  static const uint16_t RESPONSE_DEFAULT        = 0x1000;
  static const uint16_t RESPONSE_EMERGENCY_STOP = 0x0000;
  static const uint16_t RESPONSE_OPEN           = 0x1001;
  static const uint16_t RESPONSE_CLOSE          = 0x1002;
  static const uint16_t RESPONSE_VENTING        = 0x1010;
  static const uint16_t RESPONSE_TOGGLE_LIGHT   = 0x1008;
  static const uint16_t RESPONSE_IMPULSE        = 0x1004;

  static const uint8_t CRC8_INITIAL_VALUE = 0xF3;

  // buffers (sizes as in PIC)
  uint8_t rx_buffer_[18];
  bool rx_message_ready_ = false;

  uint8_t tx_buffer_[18];
  bool tx_message_ready_ = false;
  uint8_t tx_length_ = 0;

  // state & timing
  uint16_t slave_response_data_ = RESPONSE_DEFAULT;
  uint16_t broadcast_status_ = 0;

  // RX parser state (ISR-like)
  int8_t rx_counter_ = -1;
  uint8_t rx_expected_length_ = 0;

  // For delayed reply (3 ms)
  uint32_t tx_send_at_ms_ = 0;

  // internal HA state representation
  hoermann_state_t ha_state_;

  // helpers
  uint8_t calc_crc8(const uint8_t *p_data, uint8_t length) const;
  void parse_message_from_buffer();
  void prepare_response_for_scan(uint8_t counter);
  void prepare_response_for_status_request(uint8_t counter);
  void send_tx_buffer_immediate();
  void update_ha_state_from_broadcast(uint16_t broadcast);

  // low-level serial handling
  void feed_rx_byte(uint8_t data);
};
