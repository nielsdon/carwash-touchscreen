# Source the file containing the environment variables
source .env

# Check if GITHUB_ACCESS_TOKEN is set
if [ -z "${GITHUB_ACCESS_TOKEN}" ]; then
  echo "Error: GITHUB_ACCESS_TOKEN is not set."
  exit 1
fi

# Check if the branch name is provided as an argument
if [ -z "$1" ]; then
  echo "Error: No branch name provided."
  echo "Usage: $0 <branch-name>"
  exit 1
fi

# Set the project and branch variables
project='carwash-touchscreen'
branch=$1

# Validate the branch name
if [ "${branch}" != "develop" ] && [ "${branch}" != "main" ]; then
  echo "Error: Invalid branch name '${branch}'. Only 'develop' and 'main' branches are allowed."
  exit 1
fi

# clean up first
#rm *.py
#rm *.kv

# Print an update message
echo "Updating $project, branch: ${branch}"

# Download the zip archive from the GitHub repository, using the access token for authentication
curl -L -H "Authorization: token ${GITHUB_ACCESS_TOKEN}" -o archive.tar.gz https://github.com/nielsdon/${project}/archive/refs/heads/${branch}.tar.gz

# Extract the downloaded zip file, stripping the leading directory component
tar -xvf archive.tar.gz --strip-components=1

# Clean up
rm archive.tar.gz

# update the pip installer
pip install --upgrade pip

# run pip installer to make sure all node modules are installed as listed in requirements.txt
pip install -r requirements.txt