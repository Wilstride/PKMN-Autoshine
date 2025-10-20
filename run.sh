## Script for Raspberry Pi Model 3 B+

# Restart and clear bluetooth service
sudo systemctl restart bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up
# Run main script
sudo python3 main.py
