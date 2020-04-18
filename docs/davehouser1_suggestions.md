davehouser1 Zpark Suggestions
==============================

# The following are recommendtions for code
- Updated the requirements.txt for "MarkupSafe==1.1.1". Version 1.0 caused errors when trying to install.

# The following are recommendations for the install guide found here:
# https://knightjoel.github.io/zpark/install.html 

## Adjustments to the install process:
The following section details minor changes I would recommend for the documentation. These recommendations are based of pain points / trouble I ran into. Believe the problems I ran into can be avoided by future Zpark installs based off these recommendations. 

1. Would recommend including the "Z bot" icon image you show in your examples! Its cool, and would be neat to have available in your master branch.

2. Would recommend clearly stating that Zpark's supported services can all be installed on the same server. Inserting this dialog, right after the diagram would be great.

3. I personally did not know how to change a user's $HOME directory name. All the examples (and the code base) have a user named `_zpark` however their home directory was `zpark`. The following steps are what I following to make the appropriate changes to `_zpark`'s home directory: (There maybe an easier way to do this)

`
sudo adduser _zpark --force-badname
sudo usermod -aG sudo _zpark
sudo mkdir /home/zpark
sudo chown -R _zpark:_zpark /home/zpark
sudo chmod -R 700 /home/zpark
cp * -r /home/_zpark /home/zpark
su - zpark
HOME=/home/zpark
exit
su - zpark
sudo rm -rf /home/_zpark
`

4. System requirements should include the following should be installed:
    - pip3 
    - virtualenv (Install with pip3)
    - virtualenvwrapper (Install with pip3)

5. The VIRTUALEVNWRAPPER_PYTHON and VIRTUALENVWRAPPER_VIRTUALENV variables can be looked up with "which python3" and "which virtualenv", this helped me find where they were located. Would recommend including these commands to help people find where they should be pointing for the variables. Would also recommend stating these values still need to be added to the ~/.bashrc or ~/.profile for settings to be perminant.

6. For the CELERY_BROKER_URL example. provide an example if RabbitMQ is run on the same server as Zpark (i.e. CELERY_BROKER_URL = 'amqp://user:pass@localhost/zpark')

7. Major recommendation: Would really recommend adding a section under configuring the zpark supervisor service for the zpark_celery service. This was a must for getting zpark operational. It was not clear to me that celery required its own service to run in the documetnation. The good news is you had examples already in extra/, would recommend letting users know this directory exists with those examples. 
    - Also recommend letting users know they can use "supervisorctl status" to show all supervisor services running (zpark and zpark_celery should be listed as "Running" for zpark to work at all)

8. Would recommend providing simple nginx config examples. It was not clear in the documentation that the "upstream" was supposed to go into nginx.conf, and "location" was supposed to go in the site-avaialble config. 
    - I have included the following in this branch as examples to configure such services.
	- extra/nginx/nginx.conf: Working config
        - extra/nginx/zpark: zpark reverse proxy config 

9. The nginx reverse proxy config shows the user can use "/zpark" as the location. Using "/zpark" as my location seemed to break the api ping web interface [/zpark/api/v1/ping] (404 not found errors from Nginx). I needed to make the location "/" only. Not sure if I was doing something wrong, but using "/" as the reverse proxy location was the only way I could access the /api/vi/ping web interface with a 401 response. Would recommend removing "/zpark/api/v1/ping" as an example.

10. The screen shots for zabbix are a little dated, I was able to figure out how to perform the instructed configurations based off what was depicted, but the interface has changed a little for Zabbix v4.2.1. Up to you if you want to update these screen shots. I am guessing they will continue to change as Zabbix creates more updates. 

## Commands user
This section details all the commands I used to get the requirements installed:

`
# Update Ubuntu packages
sudo apt update

# Install python3
sudo apt install python3
python3 --version

# Check your python3 path
python -c "import sys; print(sys.path)"
# should show "/usr/lib/python3.6"


# Install pip3
sudo apt install python3-pip3
pip3 --version

# Install virtualenv with pip3
pip3 install virtualenv
virtualenv --version

# Install virtualenvwrapper with pip3 and set up
pip3 install --user virtualenvwrapper
cd ~
mkdir ~/venvs
which python3 (make note of path)
which virtualenv (make note of path)

#NOTE! You should mention these need to be added to .bashrc or .profile, log out and log back in.

export VIRTUALENVWRAPPER_PYTHON="<Path from which python3>"
export VIRTUALENVWRAPPER_VIRTUALENV="<Path from which virtualenv>"
export WORKON_HOME="$HOME/venvs"
source ~/.local/bin/virtualenvwrapper.sh


# Install nginx
sudo apt install nginx
sudo service nginx status (Check that service is running)
sudo systemctl list-unit-files --type=service | grep nginx (Make sure its "enabled" which means if the system reboots this service will start automatically)

# Install supervisor
sudo apt install supervisor
service supervisor restart
service supervisor status (Check that service is running)
sudo systemctl list-unit-files --type=service | grep supervisor (Check start service on startup)

# Install RabbitMQ
sudo apt-get install curl gnupg -y
curl -fsSL https://github.com/rabbitmq/signing-keys/releases/download/2.0/rabbitmq-release-signing-key.asc | sudo apt-key add -
sudo apt-get install apt-transport-https
## Add Bintray repositories that provision latest RabbitMQ and Erlang 21.x releases
sudo tee /etc/apt/sources.list.d/bintray.rabbitmq.list <<EOF
## Installs the latest Erlang 22.x release.
## Change component to "erlang-21.x" to install the latest 21.x version.
## "bionic" as distribution name should work for any later Ubuntu or Debian release.
## See the release to distribution mapping table in RabbitMQ doc guides to learn more.
deb https://dl.bintray.com/rabbitmq-erlang/debian bionic erlang
deb https://dl.bintray.com/rabbitmq/debian bionic main
EOF
sudo apt-get update -y
sudo apt-get install rabbitmq-server -y --fix-missing
sudo service rabbitmq-server status (Check that service is running)
sudo systemctl list-unit-files --type=service | grep rabbitmq-server (Check start service on startup)

# Create a rabbitmq admin user for zpark
sudo rabbitmqctl add_user zpark <password>
sudo rabbitmqctl set_permissions -p / zpark ".*" ".*" ".*"
sudo rabbitmqctl authenticate_user zpark <password> (Check user is created)

# Install curl
sudo apt install curl
curl --version (Check version to show its installed)

# Install Jo
sudo apt install jo
jo -v (Check version to show its installed)
`

