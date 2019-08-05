# pwrstat-influxdb-scraper

CyberPower UPS offers the `pwrstat` command to query the current state of the UPS and gather some useful information such as Load (Watts).

By putting this data into a time series database (Influx) we can plot it (Grafana) and show off some cool charts.

Exciting...


## Requirements
- Python 3.X


## Setup
```sh
git clone https://github.com/halsafar/pwrstat-influxdb-scraper.git
cd pwrstat-influxdb-scraper
python -m venv venv
source venv/bin/activate
```

## Config
Make a copy of `config.example.yaml`:
```bash
cp config.example.yaml config.myserver.yaml
```

Modify the config to match your server settings.

If you have Influx setup to require authentication then this scraper will only try to make the pwrstat Database if you set `admin: True`.


## Usage
```sh
source venv/bin/activate
./pwrstat-scraper.py --config-file config.myserver.yaml --series myserver -n 15 -v
```


## Summary of Setup

- Docker: https://docs.docker.com/install/
- InfluxDB : https://hub.docker.com/_/influxdb
- Grafana: https://grafana.com/docs/installation/docker/