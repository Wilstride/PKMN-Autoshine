## Script for Raspberry Pi Model 3 B+

# Restart and clear bluetooth service
sudo systemctl restart bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up
# Run main script
while true; do
	sudo python3 web.py
	echo "web controller exited with code $? -- restarting in 2s"
	sleep 2
done
