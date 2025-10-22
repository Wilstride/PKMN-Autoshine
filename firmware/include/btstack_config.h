#ifndef btstack_config_h
#define btstack_config_h

// Port related features
#define HAVE_EMBEDDED_TIME_MS
#define HAVE_MALLOC

// BTstack features that can be enabled
#define ENABLE_BLE
#define ENABLE_LE_PERIPHERAL
#define ENABLE_LE_CENTRAL
#define ENABLE_CLASSIC
#define ENABLE_HID_OVER_GATT
#define ENABLE_GATT_OVER_CLASSIC

// BTstack configuration. buffers, sizes, ...
#define HCI_ACL_PAYLOAD_SIZE (1691 + 4)
#define HCI_INCOMING_PRE_BUFFER_SIZE 14 // sizeof benign_dummy_hci_rx_packet_header
#define HCI_OUTGOING_PRE_BUFFER_SIZE 4
#define HCI_ACL_CHUNK_SIZE_ALIGNMENT 4
#define MAX_SPP_CONNECTIONS 1
#define MAX_NR_GATT_CLIENTS 1
#define MAX_NR_HCI_CONNECTIONS 2
#define MAX_NR_L2CAP_SERVICES  3
#define MAX_NR_L2CAP_CHANNELS  3
#define MAX_NR_RFCOMM_MULTIPLEXERS 1
#define MAX_NR_RFCOMM_SERVICES 1
#define MAX_NR_RFCOMM_CHANNELS 1
#define MAX_NR_BTSTACK_LINK_KEY_DB_MEMORY_ENTRIES  2
#define MAX_NR_BNEP_SERVICES 1
#define MAX_NR_BNEP_CHANNELS 1
#define MAX_NR_HID_HOST_CONNECTIONS 1
#define MAX_NR_WHITELIST_ENTRIES 1
#define MAX_NR_LE_DEVICE_DB_ENTRIES 1
#define NVM_NUM_DEVICE_DB_ENTRIES 1
#define NVM_NUM_LINK_KEYS 16

// Limit number of ACL buffers to use less memory
#define MAX_NR_CONTROLLER_ACL_BUFFERS 3

#define ENABLE_PRINTF_HEXDUMP

#endif