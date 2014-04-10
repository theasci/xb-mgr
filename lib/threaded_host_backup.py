# (c) 2012, Ovais Tariq <ovaistariq@gmail.com>
#
# This file is part of Xtrabackup Backup Manager
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from backup import Backup
from preparer import Preparer
from verifier import Verifier
from config_helper import Config_helper
from log_helper import Log_helper
from recycler import Recycler
import threading
import os
import shutil
import subprocess
from datetime import datetime

backup_lock = threading.Lock()

class Threaded_host_backup(threading.Thread):
    QPRESS_CMD = "/usr/bin/qpress"

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        host = self.queue.get()
        config_helper = Config_helper(host=host)
        backup_root = config_helper.get_backup_dir()
        prepare_dir = config_helper.get_prepare_dir()
	archive_dir = config_helper.get_archive_dir()

	prepare_error_dir = os.path.join(backup_root, "prepare_error")
	if os.path.isdir(prepare_error_dir):
	    shutil.rmtree(prepare_error_dir)
	verify_error_dir = os.path.join(backup_root, "verify_error")
	if os.path.isdir(verify_error_dir):
            shutil.rmtree(verify_error_dir)

	logger = self.setup_logger(host=host)

	start_time = datetime.now()
	logger.info_message("######### STARTING BACKUP PROCESS #########")

        return_val = self.do_backup(host=host, logger=logger)
        if return_val:
            prepare_status = self.prepare_backup(host=host,
                                    backup_type=return_val['backup_type'],
                                    backup_dir=return_val['backup_dir'],
                                    prepare_dir=prepare_dir,
				    logger=logger)

            if prepare_status:
                verify_status = self.verify_backup(host=host, 
                                        dir_to_verify=prepare_dir,
					logger=logger)
		    
		if verify_status:
		    self.archive_backup(archive_dir=archive_dir,
				    backup_dir=return_val['backup_dir'],
				    dir_to_archive=prepare_dir,
				    logger=logger)

		    self.recycle_backups(host=host, logger=logger)
		else:
		    shutil.move(prepare_dir, verify_error_dir)
	    else:
		shutil.move(prepare_dir, prepare_error_dir)

	end_time = datetime.now()
	timedelta = end_time - start_time
	logger.info_message("######### BACKUP PROCESS COMPLETED "
				"[TOTAL DURATION: %s] #########" % 
				str(timedelta))

        self.queue.task_done()

    def setup_logger(self, host):
	log_helper = Log_helper(host, log_name="%s_logger" % host)

	backup_lock.acquire()
	try:
	    log_helper.setup()
	finally:
            backup_lock.release()

	return log_helper

    def do_backup(self, host, logger):
        host_backup = Backup(host, logger=logger)

        backup_lock.acquire()
        try:
            host_backup.setup()
        finally:
            backup_lock.release()

        return host_backup.do_backup()

    def prepare_backup(self, host, backup_type, backup_dir, prepare_dir, logger):
        prepare_obj = Preparer(host=host, 
                                backup_type=backup_type,
                                backup_dir=backup_dir,
                                prepare_dir=prepare_dir,
				logger=logger)

        backup_lock.acquire()
        try:
            prepare_obj.setup()
        finally:
            backup_lock.release()

        return prepare_obj.prepare()

    def verify_backup(self, host, dir_to_verify, logger):
        verifier_obj = Verifier(host=host, dir_to_verify=dir_to_verify,
				logger=logger)

        backup_lock.acquire()
        try:
            verifier_obj.setup()
        finally:
            backup_lock.release()

        return verifier_obj.verify()

    def archive_backup(self, archive_dir, backup_dir, dir_to_archive, logger):
	backup_dir_name = os.path.basename(backup_dir)
	try:
	    datetime.strptime(backup_dir_name, "%Y_%m_%d_%H_%M_%S")
	except Excetion as e:
	    return False

	start_time = datetime.now()

	logger.info_message("Initializing archive directory...")
	backup_lock.acquire()
	try:
	    if not os.path.isdir(archive_dir):
		os.makedirs(archive_dir)
	finally:
            backup_lock.release()

	archive_name = "%s/%s.qp" % (archive_dir, backup_dir_name)

	logger.info_message("Archiving backup %s to %s" % 
					(backup_dir, archive_name))

	os.chdir(dir_to_archive)
	cmd = "%s -rfT4 * %s" % (Threaded_host_backup.QPRESS_CMD, archive_name)

        logger.info_message("Executing command %s" % cmd)

        cmd_return_code = subprocess.call(cmd, shell=True)
        if cmd_return_code > 0:
	    logger.error_message("Failed to complete archiving")
            return False

	logger.info_message("Archiving finished")
	logger.info_message("Removing directory %s" % dir_to_archive)
	
	shutil.rmtree(dir_to_archive)

	end_time = datetime.now()
        timedelta = end_time - start_time

        logger.info_message("Archiving completed successfully "
			    "[Duration: %s]" % str(timedelta))

	return True

    def recycle_backups(self, host, logger):
	recycler_obj = Recycler(host=host, logger=logger)
	return recycler_obj.recycle()

