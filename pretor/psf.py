# Copyright 2019 Charles A Daniels
# Distributed under the GNU AGPLv3 License (https://www.gnu.org/licenses/agpl.txt)

import argparse
import copy
import datetime
import getpass
import io
import logging
import pathlib
import re
import socket
import sys
import tabulate
import tempfile
import toml
import uuid
import zipfile
import zlib

from . import constants
from . import exceptions
from . import util
from . import course
from . import grade

def psf_cli(argv = None):
    parser = argparse.ArgumentParser(
            "Generate, inspect, and extract PSF (Pretor Submission File) archives")

    parser.add_argument("--version", action="version",
            version=constants.version)

    parser.add_argument("--debug", "-d", action="store_true", default=False,
            help="Log debugging output to the console.")

    parser.add_argument("--destination", "-D", default=None,
             help="Specify destination directory for" +
            " output file. Only used when combined with --create or" +
            " --extract. (default: ../ when used with --create, or" +
            "the name value when used with --extract)")

    parser.add_argument("--name", "-n", default=None,
            help="Override the name of the output file. Usually, you should "+
            "not need to specify this option, as Pretor will generate " +
            "a suitable name for your file automatically. Only used when " +
            "combined with --create.")

    parser.add_argument("--source", "-s", default="./", type=pathlib.Path,
            help="Source directory when using --create. " +
            "(default: ./)")

    parser.add_argument("--input", "-i", default=None,
            help="Input file when using --extract, --manifest, --metadata "+
            "or --summarize.")

    parser.add_argument("--revid", "-r", default="submission",
            help="Specify revision ID where applicable. (default: submission)")

    parser.add_argument("--course", "-C", default=None,
            help="Specify the course code (i.e. CSCE145). If not specified, " +
            "the course code will be read from pretor.toml in the source " +
            "directory. This option only has any effect when used with" +
            "--create.")

    parser.add_argument("--section", "-S", default=None,
            help="Specify the section number (i.e. 1). If not specified, " +
            "the section number will be read from pretor.toml in the source " +
            "directory. This option only has any effect when used with" +
            "--create.")

    parser.add_argument("--semester", "-e", default=None,
            help="Specify the semester (i.e. F2005). If not specified, " +
            "the semester will be read from pretor.toml in the source " +
            "directory. This option only has any effect when used with" +
            "--create.")

    parser.add_argument("--assignment", "-a", default=None,
            help="Specify the assignment. If not specified, the assignment" +
            "will be read from pretor.toml in the source directory." +
            "This option only has any effect when used with --create")

    parser.add_argument("--group", "-g", default=getpass.getuser(),
            help="Specify the group identifier. If you are working in a " +
            "group, this is usually your group number. If you are working " +
            "along, this is usually your student ID. If not specified " +
            "then the username of the logged in user will be used.")

    # Deliberately undocumented option - suppress all checks for the validity
    # of metadata (course, section, semester, groupid). Useful for testing, but
    # should not be used by students as the generated PSF files will be
    # impossible to grade.
    parser.add_argument("--no_meta_check", default=False, action="store_true",
            help=argparse.SUPPRESS)

    # Deliberately undocumented option - suppress check that pretor.toml exists
    # in the input directory and allow packing of any directory.  This should
    # not be used by students, as it would allow creating a submission that may
    # be invalid or improperly rooted. It would also permit bypassing any
    # plugin-supplied checks.
    parser.add_argument("--allow_no_toml", default=False, action="store_true",
            help=argparse.SUPPRESS)

    parser.add_argument("--force", "-F", default=False, action="store_true",
            help="Only used when combined with --create. Causes output " +
            "file to be overwritten even if it already exists.")

    action = parser.add_mutually_exclusive_group(required=True)

    action.add_argument("--create", "-c", default=False, action="store_true",
            help="Create a new PSF archive in the destination directory " +
            "(--destination) from the source (--source) directory. " +
            "--revid may be used change the ID of the created revision.")

    action.add_argument("--extract", "-x", default=False, action="store_true",
            help="Extract an existing PSF archive into the destination " +
            "directory (--destination). --revid may be used to specify " +
            "which revision should be extracted.")

    action.add_argument("--metadata", "-m", default=False, action="store_true",
            help="Dump metadata for the specified input PSF archive.")

    action.add_argument("--summarize", "-M", default=False, action="store_true",
            help="Summarize the specified PSF archive's structure")

    action.add_argument("--manifest", "-t", default=False, action="store_true",
            help="Display the manifest for the specified input archive and " +
            "revision ID.")

    action.add_argument("--forensic", "-f", default=False, action="store_true",
            help="Display forensic data encoded in the input archive.")

    action.add_argument("--scorecard", "-R", default=False, action="store_true",
            help="Generate a scorecard for the canonical grade" +
            "revision, or for the one specified as an argument to --revid.")

    args = None
    if argv is not None:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    if args.create:
        logging.info("creating PSF... ")

        # load data from pretor.toml
        pretor_path = pathlib.Path(args.source, "pretor.toml")
        if pretor_path.exists():
            pretor_path = pretor_path.resolve()
        pretor_data = {}
        excludelist = []
        logging.debug("looking for pretor.toml at {}".format(pretor_path))
        if pretor_path.exists():
            pretor_data = toml.load(pretor_path)
            logging.debug("loaded pretor.toml: {}".format(pretor_data))

        elif args.allow_no_toml:
            logging.warning("generating PSF without pretor.toml")

        elif not pretor_path.exists():
            logging.error("'{}' does not exist, refusing to generate PSF"
                    .format(pretor_path))
            sys.exit(1)
        else:
            logging.warning("packing PSF without pretor.toml")

        if "exclude" in pretor_data:
            excludelist = pretor_data["exclude"]

        if args.course is None:
            if "course" in pretor_data:
                args.course = pretor_data["course"]

        if args.section is None:
            if "section" in pretor_data:
                args.section = pretor_data["section"]

        if args.semester is None:
            if "semester" in pretor_data:
                args.semester = pretor_data["semester"]

        if args.assignment is None:
            if "assignment" in pretor_data:
                args.assignment = pretor_data["assignment"]

        if not args.no_meta_check:
            if args.semester is None:
                logging.error("Semester was not specified.")
                sys.exit(1)

            if args.assignment is None:
                logging.error("Assignment was not specified.")
                sys.exit(1)

            if args.course is None:
                logging.error("Course was not specified.")
                sys.exit(1)

            if args.section is None:
                logging.error("Section was not specified.")
                sys.exit(1)


        logging.info("reading data from {}".format(args.source))
        psf = PSF()
        psf.load_from_dir(args.source, args.revid, excludelist)

        # flag use of --no_meta_check
        if args.no_meta_check:
            psf.metadata["invalid_no_meta_check"] = True

        # flag use of --allow_no_toml
        if args.allow_no_toml:
            psf.metadata["allow_no_toml"] = True

        logging.info("generating metadata... ")
        psf.metadata["semester"] = args.semester
        psf.metadata["section"] = args.section
        psf.metadata["assignment"] = args.assignment
        psf.metadata["group"] = args.group
        psf.metadata["course"] = args.course
        psf.metadata["timestamp"] = datetime.datetime.now()
        psf.metadata["pretor_version"] = constants.version

        psf.forensic["hostname"] = socket.gethostname()
        psf.forensic["timestamp"] = datetime.datetime.now()
        psf.forensic["user"] = getpass.getuser()
        psf.forensic["source_dir"] = args.source
        psf.forensic["pretor_version"] = constants.version

        # write output file
        if args.name is None:
            args.name = "{}-{}-{}-{}-{}.psf".format(
                    args.semester,
                    args.course,
                    args.section,
                    args.group,
                    args.assignment)

        if args.destination is None:
            args.destination = "../"

        output_path = pathlib.Path(args.destination) / args.name
        if output_path.exists():
            output_path = output_path.resolve()

        logging.info("writing output... ")
        if not output_path.exists() or args.force:
            psf.save_to_archive(output_path)
        else:
            logging.error("output file '{}' exists, refusing to overwrite"
                .format(output_path))
            sys.exit(1)
        logging.info("PSF written to '{}'".format(output_path))

        sys.exit(0)


    if args.input is None:
        logging.error("No input file specified.")
        sys.exit(1)

    psf = PSF()
    try:
        psf.load_from_archive(args.input)
    except Exception as e:
        util.log_exception(e)
        logging.error("failed to load PSF")
        sys.exit(1)

    if args.summarize:
        sys.stdout.write(psf.generate_tree())

    elif args.metadata:
        print(psf.format_metadata())

    elif args.manifest:
        for path in psf.get_revision(args.revid).contents:
            print(path)

    elif args.extract:
        if args.destination is None:
            args.destination = pathlib.Path(args.input).name.replace(".psf", "")

        psf.get_revision(args.revid).write_files(args.destination)

    elif args.forensic:
        print(psf.format_forensic())

    elif args.scorecard is not None:
        if args.revid == "submission":
            if psf.is_graded():
                sys.stdout.write(psf.get_grade_rev().grade.generate_scorecard())
            else:
                logging.error("PSF has not been graded")
                sys.exit(1)
        else:
            if args.revid in psf.revisions:
                if psf.get_revision(args.revid).grade is not None:
                    sys.stdout.write(
                            psf.get_revision(args.revid).grade.generate_scorecard())
                else:
                    logging.error("revision {} has no grade".format(args.revid))
                    sys.exit(1)

            else:
                logging.error("no such revision {}".format(args.revid))
                sys.exit(1)




class PSF:
    """PSF

    This is the top-level abstraction to interact with PSF files.

    A PSF object acts as a container for submitted code, and supports
    maintaining multiple revisions of the same file structure. This is to allow
    a grader to make modifications to the code (i.e. to get it to compile) in
    a way that records their changes separately from the student's.

    PSF files consist of a zip file. Revisions are stored in
    "revisions/<revID>". Each revision contains a
    "revisions/<revID>/rev_data.toml" file which stores metadata about the
    specific revision. The revision's contents are stored in
    "revisions/<revID>/contents/".

    Additionally, a "pretor_data.toml" is present in the top level of the PSF
    file, which contains metadata about the overall archive.
    """

    def __init__(this):
        this.revisions = {}
        this.ID        = None
        this.metadata  = {}
        this.forensic  = {}

    def __str__(this):
        if this.ID is None:
            return "<PSF UNINITIALIZED>"
        else:
            return "<PSF ID={}>".format(this.ID)

    def format_metadata(this):
        """format_metadata

        Return a string containing a pretty-formatted table of metadata in this
        PSF.

        :param this:
        """

        return tabulate.tabulate(
                [(k, this.metadata[k]) for k in this.metadata],
                tablefmt = "plain")

    def format_forensic(this):
        """format_forensic

        Return a string containing a pretty-formatted table of forensic
        data in this PSF.

        :param this:
        """

        return tabulate.tabulate(
                [(k, this.forensic[k]) for k in this.forensic],
                tablefmt = "plain")

    def generate_tree(this):
        """generate_tree

        Return a string containing a tree representation of this PSF file

        :param this:
        """

        s = str(this) + "\n"
        for revID in this.revisions:
            rev = this.revisions[revID]
            s += "\t{}\n".format(rev)
            for path in rev.contents:
                s += "\t\t{}\n".format(rev.contents[path])

        return s

    def load_from_dir(this, path: pathlib.Path, revID, excludelist=[]):
        """load_from_dir

        Populate this PSF object from a directory.

        :param this:
        :param path:
        :type path: pathlib.Path
        :param revID: revision ID to use for the created revision"
        :param excludelist: List of glob patterns to exclude
        """

        logging.debug("populating revID {} with dir {}".format(revID, path))

        this.ID = uuid.uuid4()
        logging.debug("ID={}".format(this.ID))

        rev = Revision(this, revID)
        this.revisions[revID] = rev
        for child in path.glob("**/*"):

            exclude = False
            for pattern in excludelist:
                if child.match(pattern):
                    logging.debug("ignoring file '{}' per excludelist"
                            .format(child))
                    exclude = True
                    break

            if exclude or child.is_dir():
                continue

            with open(str(child), 'rb') as f:
                rev.put_file(
                        child.relative_to(path),
                        f.read())

    def load_from_archive(this, archive_path: pathlib.Path):
        logging.debug("loading PSF archive {}".format(archive_path))

        archive_path = pathlib.Path(archive_path)

        with zipfile.ZipFile(str(archive_path), 'r') as f:

            # load forensic data from PSF
            try:
                this.forensic = toml.loads(
                        zlib.decompress(f.comment).decode("utf-8"))
            except Exception as e:
                util.log_exception(e)
                logging.warning("archive {} has missing or invalid forensic data"
                        .format(archive_path))

            # load the pretor data file for the PSF
            try:
                f.getinfo("pretor_data.toml")
            except KeyError:
                raise PSFInvalid("Invalid archive {}, no pretor_data.toml"
                        .format(archive_path))

            pretor_data = None
            try:
                pretor_data = toml.loads(
                        f.read("pretor_data.toml").decode("utf-8"))
            except Exception as e:
                util.log_exception(e)
                raise PSFInvalid("Invalid archive {}, could not load pretor_data.toml"
                        .format(archive_path))

            # ensure pretor_data contains all required keys
            for key in ["pretor_version", "ID", "revisions"]:
                if key not in pretor_data:
                    raise PSFInvalid("Invalid archive {}, pretor_data.toml missing key {}"
                        .format(archive_path, key))

            logging.debug("pretor_data.toml is valid")

            this.ID = pretor_data["ID"]

            if "metadata" in pretor_data:
                this.metadata = pretor_data["metadata"]

            # XXX: maybe this loop body should be it's own function?
            for revID in pretor_data["revisions"]:
                logging.debug("processing revision {}".format(revID))

                if '..' in revID or '~' in revID:
                    raise PSFInvalid(
                        "Archive {} contains maliciously constructed revID {}"
                        .format(archive_path, revID))

                rev_data = None

                # load the revision data from the archive
                try:
                    rev_data = f.getinfo("revisions/{}/rev_data.toml".format(revID))
                    rev_data = f.read(rev_data)
                    rev_data = toml.loads(rev_data.decode("utf-8"))
                    logging.debug("loaded revision data successfully")
                except KeyError:
                    raise PSFInvalid(
                        "Invalid archive {}, pretor_data.toml specifies nonexistant revID {}"
                        .format(archive_path, revID))
                except Exception as e:
                    util.log_exception(e)
                    raise PSFInvalid(
                        "Invalid archive {}, could not load rev_data.toml for revID {}"
                        .format(archive_path, revID))

                # load grade data from archive
                grade_data = None
                course_data = None
                try:
                    grade_data = f.getinfo("revisions/{}/grade.toml".format(revID))
                    grade_data = f.read(grade_data)
                    grade_data = toml.loads(grade_data.decode("utf-8"))
                    logging.debug("loaded grade data successfully")
                except KeyError as e:
                    # no grade specified
                    logging.debug("no grade.toml: {}".format(e))
                    pass
                except Exception as e:
                    util.log_exception(e)
                    raise PSFInvalid(
                        "Invalid archive {}, invalid grade.toml for revID {}"
                        .format(archive_path, revID))

                try:
                    course_data = f.getinfo("revisions/{}/course.toml".format(revID))
                    course_data = f.read(course_data)
                    course_data = toml.loads(course_data.decode("utf-8"))
                    logging.debug("loaded course data successfully")
                except KeyError:
                    # no grade specified
                    logging.debug("no course data specified")
                    if grade_data is not None:
                        raise PSFInvalid(
                            "Invalid archive {}, grade specified without course for revID {}"
                            .format(archive_path, revID))
                except Exception as e:
                    util.log_exception(e)
                    raise PSFInvalid(
                        "Invalid archive {}, invalid course.toml for revID {}"
                        .format(archive_path, revID))

                course_obj = None
                if course_data is not None:
                    course_obj = course.load_course_definition(course_data)

                # validate that we will be able to correctly de-serialize the
                # course and grade data
                try:
                    if grade_data is not None:
                        assert course_data is not None
                        assert "assignment_name" in grade_data
                        assert grade_data["assignment_name"] in course_data
                except Exception as e:
                    raise PSFInvalid(
                        "Invalid archive {}, mangled course/grade data for revID {}"
                        .format(archive_path, revID))

                grade_obj = None
                if grade_data is not None:
                    grade_obj = grade.Grade(
                        course_obj.assignments[grade_data["assignment_name"]])
                    grade_obj.load_data(grade_data)
                    logging.debug("generated grade object: {}"
                            .format(grade_obj))

                # validate the revision data
                for key in ["ID", "contents"]:
                    if key not in rev_data:
                        raise PSFInvalid(
                            "Invalid archive {}, rev_data.toml for revID {} missing key {}"
                            .format(archive_path, revID, key))

                # initialize revision object and install into revisions
                rev = Revision(this, revID)
                if "parentID" in rev_data:
                    rev.parentID = rev_data["parentID"]
                this.revisions[revID] = rev

                logging.debug("generated revision object: {}".format(rev))

                rev.grade = grade_obj


                # load revision files from archive
                for path in rev_data["contents"]:
                    if '..' in path or '~' in path:
                        raise PSFInvalid(
                            "Archive {} contains maliciously constructed path {}"
                            .format(archive_path, path))

                    logging.debug("loading file {}".format(path))

                    full_path = "revisions/{}/contents/{}".format(revID, path)

                    try:
                        rev.put_file(path, f.read(full_path))
                    except Exception as e:
                        util.log_exception(e)
                        raise PSFInvalid(
                                "Invalid archive {}, could not load {} from revision {}"
                                .format(archive_path, path, revID))

        this.metadata["archive_name"] = archive_path

    def save_to_archive(this, path: pathlib.Path):
        """save_to_archive

        Generate a PSF formatted archive file from this PSF object.

        :param this:
        :param path: destination path to write archive to
        :type path: pathlib.Path
        """

        logging.debug("saving PSF {} to {}".format(this, path))

        path = str(pathlib.Path(path))
        with zipfile.ZipFile(str(path), "w") as f:

            # write pretor_data.toml
            pretor_data = {}
            pretor_data["ID"] = this.ID
            pretor_data["pretor_version"] = constants.version
            pretor_data["revisions"] = list(this.revisions.keys())
            pretor_data["metadata"] = this.metadata
            f.writestr("pretor_data.toml",
                    toml.dumps(pretor_data), compress_type=zipfile.ZIP_LZMA)

            # write forensic data
            f.comment = \
                zlib.compress(toml.dumps(this.forensic).encode("utf-8"))

            # write each revision file
            for revID in this.revisions:
                this.save_revision_to_archive(f, revID)

    def save_revision_to_archive(this, f, revID):
        """save_revision_to_archive

        Save a revision to the already open ZipFile

        :param this:
        :param f: the ZipFile object
        :param revID:
        """

        rev = this.revisions[revID]

        logging.debug("saving revision {}".format(rev))

        # write rev_data.toml
        rev_data = {}
        rev_data["ID"] = revID
        rev_data["parentID"] = rev.parentID
        rev_data["contents"] = list(rev.contents.keys())
        f.writestr("revisions/{}/rev_data.toml".format(revID),
                toml.dumps(rev_data), compress_type=zipfile.ZIP_LZMA)

        if rev.grade is not None:
            f.writestr("revisions/{}/grade.toml".format(revID),
                    rev.grade.dump_string(), compress_type=zipfile.ZIP_LZMA)

            f.writestr("revisions/{}/course.toml".format(revID),
                    rev.grade.assignment.course.dump_string(),
                    compress_type=zipfile.ZIP_LZMA)

        # add each file to the archive
        for path in rev.contents:
            logging.debug("saving {}".format(rev.contents[path]))

            data = rev.contents[path].get_data()
            f.writestr("revisions/{}/contents/{}".format(revID, path),
                    data, compress_type=zipfile.ZIP_LZMA)

    def create_revision(this, revID, baseRevID=None):
        """create_revision

        Create a new revision. Note that grade data is not preserved in the
        child, if you want that, check out create_grade_revision().

        :param this:
        :param revID:
        :param baseRev: the revision to base this one on.  Use None if this
        revision has no base.
        """

        if revID in this.revisions:
            raise PSFRevisionError(
                "Cannot create revID {}, already exists in PSF {}"
                .format(revID, this))

        baseRev = this.get_revision(baseRevID)

        this.revisions[revID] = Revision(
                this,
                revID,
                baseRev)

        return this.revisions[revID]

    def get_revision(this, revID):
        """get_revision

        :param this:
        :param revID:
        """

        if revID not in this.revisions:
            raise PSFRevisionError("No such revID {}".format(revID))

        else:
            return this.revisions[revID]

    def get_grade_rev(this):
        """get_grade_rev

        Get the most recent revision which has a grade on it. This makes the
        assumption that the list of graded revisions is linear in nature.
        Essentially, this function searches through all revisions until it
        finds one that has a grade attached, then follows it's child revisions
        until it finds the "tail" of the grade revisions.

        WARNING: this function makes the assumption that the grade revisions
        are linear in nature; if this is not the case, then the behavior of
        this function is undefined. This assumption is not validated.

        WARNING: this function has an unhandled edge case -- a graded revision
        with a child revision that is ungraded will not count as being the
        tail of the list. If this circumstance is brought about artificially,
        this function will return None.

        :param this:
        """

        for revID in this.revisions:
            rev = this.revisions[revID]
            if (rev.grade is not None) and (len(this.get_children(rev)) == 0):
                # if a revision has no children, but is graded, it *must*
                # be the tail of the revision list.

                return rev

        return None

    def create_grade_revision(this, baseRevID = None):
        """create_grade_revision

        Create a new revision with a dynamically selected revID for grading
        purposes. If baseRevID is specified, then it is used as the parent
        revision, otherwise the result of get_grade_rev() is used as the
        parent. Any grade information already stored in the parent is copied to
        the child.

        :param this:
        :param baseRevID:
        """

        if baseRevID == None:
            if this.get_grade_rev() is None:
                logging.error("failed to create grade revision without " +
                        "explicit baseRevID: no graded revisions in {}"
                        .format(this))
                raise exceptions.StateError(
                        "no graded revisions in {}".format(this))

            baseRevID = this.get_grade_rev().ID

        baseRev = this.get_revision(baseRevID)

        newRevID = baseRevID
        revNo = 0
        while newRevID in this.revisions:
            if re.match(r".*_[0-9]+", newRevID):
                revNo = int(str(
                    re.findall(r"_[0-9]+", newRevID)[-1]).replace("_", "")) + 1
                newRevID = re.sub(r"_[0-9]+", "", newRevID)
                newRevID = "{}_{}".format(newRevID, revNo)
            else:
                newRevID = "{}_{}".format(newRevID, revNo)

        newRev = this.create_revision(newRevID, baseRevID)

        # XXX: this is a deep copy, which means that newRev.grade.assignment is
        # a duplicate of baseRev.grade.assignment. At time of writing, this is
        # fine since the Assignment object is only ever read, never written. If
        # this assumption changes in the future, this will break.
        newRev.grade = copy.deepcopy(baseRev.grade)

        return newRev


    def get_children(this, rev):
        """get_children

        Given a revision, find all revisions which have this revision as an
        *immediate* parent.

        :param this:
        :param rev:
        :type rev: Revision
        """

        revs = []
        for revID in this.revisions:
            rev = this.revisions[revID]
            if rev.parentID == rev.ID:
                revs.append(rev)

        return revs

    def is_graded(this):
        """is_graded

        Check if any revision has a non-null grade field.

        :param this:
        """

        return this.get_grade_rev() is not None


class Revision:
    """Revision

    This object abstracts a single PSF revision"
    """

    def __init__(this, psf, revID, parentRev = None):
        """__init__

        :param this:
        :param psf: the PSF object this revision is stored in.
        :param revID:
        :param parentRev: the parent revision (not the ID, the Revision
        object), only specify this if you are creating a new revision and you
        want all the files copied from the old to the new, otherwise just set
        parentID after instantiating the Revision object.
        """

        this.psf = psf
        this.ID = revID
        this.contents = {}
        this.parentID = None
        this.grade = None

        if parentRev is None:
            return

        this.parentID = parentRev.ID
        # copy all files from the base revision to this one
        for path in parentRev.contents:
            parent = './'
            name = path
            if '/' in path:
                parent = '/'.join(path.split('/')[:-1])
                name = path.split('/')[-1]

            this.contents[path] = FileData(
                    this,
                    parent,
                    name,
                    parentRev.contents[path].get_data())

    def __str__(this):
        if this.parentID is None:
            return "<Revision ID={}>".format(this.ID)
        else:
            return "<Revision ID={} parent={}>".format(this.ID, this.parentID)

    def get_listing(this, path):
        """get_listing

        :param this:
        :param path: the directory to list
        """

        return (this.contents[p] for p in this.contents
                if str(this.contents[p].parent) == str(path))

    def get_file(this, path):
        if path in this.contents:
            return this.contents[path]
        else:
            raise PSFRevisionNoSuchFile(this, path)

    def put_file(this, path, data):
        logging.debug("adding file {} to {}".format(path, this))

        path = str(path)

        if not isinstance(data, FileData):
            data = FileData(
                    this,
                    '/'.join(path.split('/')[:-1]),
                    path.split('/')[-1],
                    data)

        data.parent =  '/'.join(path.split('/')[:-1])
        data.name = path.split('/')[-1]

        this.contents[path] = data

    def delete_file(this, path):
        if path in this.contents:
            this.contents.pop(path)
        else:
            raise PSFRevisionNoSuchFile(this, path)

    def write_files(this, path: pathlib.Path):
        """write_files

        Write all files in this revision to the output directory path.

        :param this:
        :param path:
        :type path: pathlib.Path
        """

        path = pathlib.Path(path)

        logging.debug("write contents of {} to {}".format(this, path))

        if not path.exists():
            path.mkdir()

        for fpath in this.contents:
            fdata = this.contents[fpath]
            target_path = path / fpath

            logging.debug("writing file {} to {}".format(fpath, target_path))

            if not target_path.parent.exists():
                target_path.parent.mkdir()

            with open(target_path, 'wb') as f:
                # write to destination file
                f.write(fdata.get_data())


class FileData:
    """
    This object abstracts a single file in a single revision. Note that the
    contents are always stored as a file-like. If contents are not file-like
    when passed to the constructor, they are stored in a SpooledTemporaryFile.
    """

    def __init__(this,
            revision: Revision,
            parent: pathlib.PurePath,
            name: str,
            data
            ):
        """__init__

        :param this:
        :param revision: parent revision
        :param parent: parent folder
        :param name: file name
        :param data: bytes or file-like
        """

        this.revision = revision
        this.parent   = pathlib.PurePath(parent)
        this.name     = str(name)

        if isinstance(data, io.IOBase):
            this.data = data
        else:
            if isinstance(data, str):
                data = data.encode("utf-8")
            elif not isinstance(data, bytes):
                data = bytes(data)

            this.data = tempfile.SpooledTemporaryFile()
            this.data.write(data)

    def __str__(this):
        return "<FileData '{}' in {}>" \
                .format(this.get_path(), str(this.revision))

    def get_data(this):
        this.data.seek(0, 0)
        return this.data.read()

    def get_path(this):
        return pathlib.Path(this.parent) / this.name


class PSFInvalid(Exception):
    """PSFInvalid

    The PSF file is invalid:
    """

    def __init__(this, msg="unspecified"):
        msg = "PSF Invalid: {}".format(str(msg))

        super().__init__(msg)

class PSFRevisionError(Exception):
    """PSFRevisionError

    Indicates that a problem has occurred relating to a PSF revision.
    """

    def __init__(this, msg="unspecified"):
        msg = "PSF Revision Error: {}".format(str(msg))

        super().__init__(msg)

class PSFRevisionNoSuchFile(Exception):
    """PSFRevisionNoSuchFile

    An attempt has been made to access a file which does not exist within a
    given revision.
    """

    def __init__(this, rev, path):
        msg = "No file '{}' in revision {}".format(path, rev)

        super().__init__(msg)
