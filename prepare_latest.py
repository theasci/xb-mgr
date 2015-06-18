#!/usr/bin/python

# This script prepares the latest incremental backup in the backup rootdir
# (/mnt/linode_backups/mysql.the-jci.org/) and places it at /home/backup_dir/prepare/.
#
# This is meant to be used when you need to grab data from an incremental backup

from lib.config_helper import Config_helper
from lib.log_helper import Log_helper
from lib.preparer import Preparer
from lib.backup import Backup
import sys

host = "localhost"

config_helper = Config_helper(host=host)
logger = Log_helper(host, log_name="%s_logger" % host)
logger.setup()

logger.info_message("######### STARTING PREPARE PROCESS #########")

host_backup = Backup(host, logger=logger)
backup_dir = host_backup.get_latest_backup_dir_name()
logger.info_message("Preparing backup dir %s" % backup_dir)

prepare_obj = Preparer(host=host,
        backup_type=Backup.BACKUP_TYPE_INC,
        backup_dir=backup_dir,
        prepare_dir=config_helper.get_prepare_dir(),
        logger=logger)
prepare_obj.setup()
prepare_dir = prepare_obj.prepare()
logger.info_message("Prepare dir %s" % prepare_dir)
