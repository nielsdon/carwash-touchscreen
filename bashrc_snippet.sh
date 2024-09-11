export LC_CTYPE=nl_NL.UTF-8
export LC_ALL=nl_NL.UTF-8

#show splash screen
. ~/show_splash.sh
#start carwash
. ~/env/bin/activate
. update.sh
python main.py > /dev/null 2>&1
