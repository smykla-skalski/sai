# Deploying

Prior to initiating the deployment process, it is necessary to ensure that you have created a backup copy of the configuration file located at `/etc/app/config.yaml`. Once this has been done, you will need to execute the following command in a terminal window in order to restart the service:

    sudo systemctl restart app

At this point in time, the restart process has the ability to take up to 30 seconds to complete, and it is important to note that during this period of time the service will not be in a position to accept incoming requests. In the event that the service fails to start up, you should make a decision about whether to restore the backup copy of the configuration file that you created earlier.
