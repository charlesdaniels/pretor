import zipfile
import sys
import os
import traceback
import logging
import pretor.exceptions
import pprint

def zip_folder(folder_path, output_path, comment=""):
    """Zip the contents of an entire folder (with that folder included
    in the archive). Empty subfolders will be included in the archive
    as well.

    Retrieved from
    https://www.calazan.com/how-to-zip-an-entire-directory-with-python/
    2018-08-08.

    """

    folder_path = str(os.path.abspath(str(folder_path)))
    output_path = str(os.path.abspath(str(output_path)))
    starting_dir = os.getcwd()

    if type(comment) is not bytes:
        comment = str(comment)
        comment = comment.encode("utf-8")

    parent_folder = os.path.dirname(folder_path)
    # Retrieve the paths of the folder contents.
    os.chdir(folder_path)
    contents = os.walk("./")

    try:
        zip_file = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_LZMA)
        for root, folders, files in contents:
            # Include all subfolders, including empty ones.
            for folder_name in folders:
                absolute_path = os.path.join(root, folder_name)
                relative_path = absolute_path.replace(parent_folder + '\\',
                        '')
                logging.info("Adding '%s' to archive." % absolute_path)
                zip_file.write(absolute_path, relative_path)
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                relative_path = absolute_path.replace(parent_folder + '\\',
                        '')
                logging.info("Adding '%s' to archive." % absolute_path)
                zip_file.write(absolute_path, relative_path)
        logging.info("burning metadata... ")
        zip_file.comment = comment
        logging.info("'%s' created successfully." % output_path)
    except IOError as e:
        logging.error(e)
        raise IOError
    except OSError as e:
        logging.error(e)
        raise OSError
    except zipfile.BadZipfile as e:
        logging.error(e)
        raise Exception
    finally:
        zip_file.close()

    os.chdir(starting_dir)

def zip_read_comment(file_path):
    """zip_read_comment

    Read the contents of a zipfile's comment field.

    :param file_path:
    """

    logging.debug("retrieving comment from {}".format(file_path))
    comment = None
    with zipfile.ZipFile(file_path, 'r') as f:
        comment = f.comment
    logging.debug("loaded raw comments '{}'".format(comment))
    return comment


def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level,
            format='%(levelname)s: %(message)s',
            datefmt='%H:%M:%S')


def log_exception(e):
    logging.error("Exception: {}".format(e))
    logging.debug("".join(traceback.format_tb(e.__traceback__)))

def log_pretty(logfunc, obj):
    logfunc(pprint.pformat(obj))
