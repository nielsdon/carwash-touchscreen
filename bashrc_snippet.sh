ping -c 5 api.washterminalpro.nl > carwash.log 2>&1
source ./env/bin/activate
source ./update.sh
python main.py >> carwash.log 2>&1
