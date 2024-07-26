# Set the project and branch variables
project='carwash-touchscreen-dist'
branch=$1

# Validate the branch name
if [ "${branch}" != "develop" ] && [ "${branch}" != "main" ]; then
  CONFIG_FILE="config.ini"

  # Check if testMode is True
  TEST_MODE=$(grep -E '^testMode=True' "$CONFIG_FILE")

  if [ "$TEST_MODE" ]; then
    # Set the branch variable to 'develop'
    branch="develop"
  else
    # Set the branch variable to some default value or leave it empty
    branch="main"  # or set to "" if you prefer
  fi
fi

# clean up first
rm *.py
rm *.kv
rm *.txt
rm *.png

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
chmod +x ./get_hid_device.sh