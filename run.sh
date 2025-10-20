sudo systemctl restart bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up
sudo python3 shiny_hunt.py
