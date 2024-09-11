# Set the project and branch variables
project='carwash-touchscreen'
branch=$1

# Validate the branch name
if [ "${branch}" != "develop" ] && [ "${branch}" != "main" ]; then
  CONFIG_FILE="config.ini"

  # Check if testMode is True
  TEST_MODE=$(grep -E '^testMode=True' "$CONFIG_FILE")

  if [ "$TEST_MODE" ]; then
    # Set the branch variable to 'develop'
    branch="develop"
    export KIVY_NO_FILELOG=1  # Disable file logging
    export KIVY_NO_CONSOLELOG=0  # Enable console logging
    export KIVY_LOG_LEVEL=debug  # Set log level to debug (all messages will be shown)
  else
    # Set the branch variable to some default value or leave it empty
    branch="main"  # or set to "" if you prefer
    export KIVY_NO_FILELOG=1  # Disable file logging
    export KIVY_NO_CONSOLELOG=1  # Disable console logging
    export KIVY_LOG_LEVEL=error  # Set log level to error (only error messages will be shown)
  fi
fi

# Print an update message
#echo "Updating $project, branch: ${branch}"

# Download the zip archive from the GitHub repository, using the access token for authentication
curl -sS -L -o archive.tar.gz https://github.com/nielsdon/${project}/archive/refs/heads/${branch}.tar.gz

# Extract the downloaded zip file, stripping the leading directory component
tar -xvf archive.tar.gz --strip-components=1 > /dev/null 2>&1

# Clean up
rm archive.tar.gz

# update the pip installer
pip install --upgrade pip > /dev/null 2>&1

# run pip installer to make sure all node modules are installed as listed in requirements.txt
pip install -r requirements.txt > /dev/null 2>&1

# ensure correct permissions are set
chmod a+x *.sh

# update and start influxDB reporting
sudo cp ./get_cpu_temp.sh /usr/local/bin/.
sudo chmod a+x /usr/local/bin/get_cpu_temp.sh
sudo chown telegraf:telegraf /usr/local/bin/get_cpu_temp.sh
sudo cp telegraf.conf /etc/telegraf/.
sudo systemctl restart telegraf