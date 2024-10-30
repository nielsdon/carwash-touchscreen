#!/bin/bash
. update.sh

# ensure correct permissions are set
chmod a+x *.sh

# update and start influxDB reporting
sudo cp ./get_cpu_temp.sh /usr/local/bin/.
sudo chmod a+x /usr/local/bin/get_cpu_temp.sh
sudo chown telegraf:telegraf /usr/local/bin/get_cpu_temp.sh
sudo cp telegraf.conf /etc/telegraf/.
sudo systemctl restart telegraf

# install splash screen service
sudo cp ./asplashscreen.sh /etc/init.d/asplashscreen
sudo chmod a+x /etc/init.d/asplashscreen
sudo cp ./asplashscreen.service /etc/systemd/system/.
sudo systemctl daemon-reload
sudo systemctl enable asplashscreen.service