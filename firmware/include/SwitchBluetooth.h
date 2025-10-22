#ifndef SwitchBluetooth_h
#define SwitchBluetooth_h

#include "SwitchConsts.h"
#include "btstack.h"

class SwitchBluetooth {
 public:
  void init();
  void setHidCid(uint16_t hid_cid) { _hid_cid = hid_cid; };
  uint16_t getHidCid() { return _hid_cid; };
  uint8_t *generate_report();
  void setSwitchRequestReport(uint8_t *report, int report_size);
  void set_empty_switch_request_report();
  void set_controller_rumble(bool rumble);
  
  // Button control methods
  void press_button(const char* button);
  void release_button(const char* button);
  void release_all_buttons();
  void set_stick(const char* stick, float h, float v);
  void center_sticks();

 private:
  uint16_t _hid_cid = 0;
  SwitchReport _switchReport = {
      .batteryConnection = 0x91, .buttons = {0x0}, .l = {0x0}, .r = {0x0}};
  uint8_t _report[100] = {0x0};
  uint8_t _switchRequestReport[100] = {0x0};
  uint8_t _addr[6] = {0x0};
  bool _vibration_enabled = false;
  uint8_t _vibration_report = 0x00;
  uint8_t _vibration_idx = 0x00;
  bool _imu_enabled = false;
  uint8_t _player_number = 0x00;
  bool _device_info_queried = false;
  uint32_t _timer = 0;
  uint32_t _timestamp = 0;
  
  // Helper methods (from SwitchCommon)
  void set_empty_report();
  void set_subcommand_reply();
  void set_unknown_subcommand(uint8_t subcommand_id);
  void set_timer();
  void set_full_input_report();
  void set_standard_input_report();
  void set_bt();
  void set_device_info();
  void set_shipment();
  void toggle_imu();
  void imu_sensitivity();
  void set_imu_data();
  void spi_read();
  void set_mode();
  void set_trigger_buttons();
  void enable_vibration();
  void set_player_lights();
  void set_nfc_ir_state();
  void set_nfc_ir_config();
};

void packet_handler(SwitchBluetooth *inst, uint8_t packet_type, uint8_t *packet);
void hid_report_data_callback(SwitchBluetooth *inst, uint16_t report_id, uint8_t *report, int report_size);

#endif