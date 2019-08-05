# pwrstat-influxdb-scraper

CyberPower UPS offers the `pwrstat` command to query the current state of the UPS and gather some useful information such as Load (Watts).

By putting this data into a time series database (Influx) we can plot it (Grafana) and show off some cool charts.

Exciting...


## Requirements
- Python 3.X


## Setup
```text
git clone https://github.com/halsafar/pwrstat-influxdb-scraper.git
cd pwrstat-influxdb-scraper
python3 -m venv venv
source venv/bin/activate
```

## Config
Make a copy of `config.example.yaml`:
```text
cp config.example.yaml config.myserver.yaml
```

Modify the config to match your server settings.

If you have Influx setup to require authentication then this scraper will only try to make the pwrstat Database if you set `admin: True`.


## Usage
```text
source venv/bin/activate
./pwrstat-scraper.py --config-file config.myserver.yaml --series myserver -n 15 -v
```


## Install As A Systemd Service
Provided is an example systemd service file.  Start with copying it into the systemd service file location:
```text
sudo cp pwrstat-influxdb-scraper.service /etc/systemd/system/
```

Now you need to modify the service file to match your setup:
- Replace `{{ABSOLUTE_PATH_TO_VENV}}` with the absolute path to the VENV you made in the Setup step.
- Replace `{{ABSOLUTE_PATH_TO_REPO}}` with the absolute path to the repo location you checked out in the Setup step.
```text
sudo nano /etc/systemd/system/pwrstat-influxdb-scraper.service
```  

You must reload systemd before it will see your changes:
```text
sudo systemctl daemon-reload
```

Now you can try to start the service and check for errors:
```text
sudo systemctl start pwrstat-influxdb-scraper.service
sudo systemctl status pwrstat-influxdb-scraper.service
```

If you received no errors and the service started appropriately then set it to auto boot:
```text
sudo systemctl enable pwrstat-influxdb-scraper.service
```

## Summary of Setup

- Docker: https://docs.docker.com/install/
- InfluxDB : https://hub.docker.com/_/influxdb
- Grafana: https://grafana.com/docs/installation/docker/