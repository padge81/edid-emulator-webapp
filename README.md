# edid-emulator-webapp
Web-based EDID emulator management for Raspberry Pi


# 🚀 Install

## 🔄 Update OS
```
sudo apt-get update
sudo apt-get upgrade
sudo reboot
```

## 📦 Install Dependencies:
```
sudo apt-get install git python3 python3-smbus edid-decode epiphany-browser
sudo reboot
```

## ⬇️ Download edid-emulator-webapp:
```
git clone https://github.com/padge81/edid-emulator-webapp.git
```

## ⚙️ Run Setup:
```
cd edid-emulator-webapp/backend
chmod +x setup.sh
./setup.sh
cd ..
chmod +x setup_kiosk.sh
./setup_kiosk.sh
sudo reboot
```
