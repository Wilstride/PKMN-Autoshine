## Script for Raspberry Pi Model 3 B+

# Restart and clear bluetooth service
sudo systemctl restart bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up
# Run main script
sudo python3 scripts/web_control.py macros/plza_travel_cafe.txt --host 0.0.0.0 --port 8080
