# Copyright 2019 Charles A Daniels
# Distributed under the GNU GPLv3 License (https://www.gnu.org/licenses/gpl.txt)

import argparse
import cmd
import logging
import os
import pathlib
import pdb
import select
import shlex
import signal
import subprocess
import sys
import tabulate
import tempfile
import pty
import termios
import tty

from . import constants
from . import course
from . import grade
from . import util
from . import psf

class REPL(cmd.Cmd):
    """REPL

    Pretor grading repl, usually used as a singleton by repl().

    A key feature of the REPL which is important to understand when developing
    new commands is the symbol table, stored in the symtab field as a
    hashtable.

    Any symbols which begin with a '#' character are internal, and can be ready
    by the user via 'get', but not modified via 'set'. These commands are
    usually used for book-keeping purposes. Not all internal symbols are
    guaranteed to exist at any given time, depending on the REPL state, except
    for #result, #lastresult, #status, #laststatus, and #error. The internal
    symbols that may exist are enumerated below:

    #result - The result of the command which just executed, if non-"", this
    will be displayed to the console.

    #lastresult - The result of the previous command

    #status - True if the command completed successfully, or False
    otherwise

    #laststatus - The status of the last command.

    #error - If non-"", a string or other object describing the nature of any
    error which occurred while executing a command.

    #argv - Shorthand for shlex.split(arg).

    #psf - list containing all loaded PSF objects

    #current_psf - index into #psf of the PSF object which is currently being
    worked on

    Additionally, plugins may define their own internal symbols, or override
    the ones noted here. Refer to the documentation of any plugins you are
    using for more information.
    """

    intro = "PRETOR version {} interactive grading shell.".format(constants.version)
    prompt = "grader> "
    file = None

    def __init__(this):
        super().__init__()
        this.history = []
        this.symtab = {}
        this.symtab["#result"] = ""
        this.symtab["#lastresult"] = ""
        this.symtab["#status"] = True
        this.symtab["#laststaus"] = True
        this.symtab["#error"] = ""
        this.symtab["#finalized"] = []

        # configurable
        this.symtab["coursepath"] = "./"
        this.symtab["outputdir"] = "./"
        this.symtab["revision"] = ""
        this.symtab["base_revision"] = "submission"

    def do_exit(this, arg):
        """exit

        Exit pretor.

        """

        sys.exit(0)

    def do_history(this):
        """history

Return a list of previously entered commands
        """

        this.symtab["#result"] = '\n'.join(this.history)

    def do_EOF(this, arg):
        "Exit when EOF is read"

        print("caught EOF")
        sys.exit(0)

    def do_set(this, arg):
        """set SYMBOL VALUE

Set a symbol in the REPL to the specified value. Result is set to to as one.
        """

        if not this.check_arg(2): return

        symbolname = this.symtab["#argv"][1]
        value = this.symtab["#argv"][2]

        if symbolname.startswith('#'):
            this.fail("may not override internal symbols")
            return
        else:
            if symbolname in this.symtab:
                this.symtab["#result"] = this.symtab[symbolname]
            this.symtab[symbolname] = value

    def do_get(this, arg):
        """get SYMBOL

Get the value of a symbol if it exists.
        """

        if not this.check_arg(1): return

        symbolname = this.symtab["#argv"][1]

        if symbolname in this.symtab:
            this.symtab["#result"] = this.symtab[symbolname]
        else:
            this.symtab["#status"] = False
            this.symtab["#error"] = "no such symbol '{}'".format(symbolname)

    def do_ingest(this, arg):
        """ingest TARGET

Ingest a directory by loading all PSF files it contains.

TARGET may be either a directory, which will be searched recursively for PSF
files, or it may be a single PSF file.
        """

        if not this.check_arg(1): return

        target = pathlib.Path(this.symtab["#argv"][1])

        if not target.exists():
            this.fail("No such file or directory '{}'".format(target))
            return

        if target.is_file():
            logging.info("Loading PSF file '{}'".format(target))
            this.load_psf(target)
        else:
            for p in target.glob("**/*.psf"):
                if p.is_file():
                    logging.info("Loading PSF file '{}'".format(p))
                    this.load_psf(p)

    def do_current(this, arg):
        """current

Display information about the PSF currently being manipulated, if any.
        """

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        s = str(current) + "\n"
        s += current.format_metadata() + "\n"
        if current.is_graded():
            s += "PSF has been graded"
        else:
            s += "PSF has NOT been graded"

        this.symtab["#result"] = s

    def do_showgrade(this, arg):
        """showgrade

Display the assigned grade for the PSF, if any
        """

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        if not current.is_graded():
            this.fail("PSF has not been graded")
            return

        if this.symtab["revision"] != "":
                rev = current.get_revision(this.symtab["revision"])
                if rev.grade is None:
                    this.symtab["#status"] = False
                    this.symtab["#error"] = \
                            "Revision '{}' not graded".format(rev)

                else:
                    this.symtab["#result"] = rev.grade.generate_scorecard()
        else:
            this.symtab["#result"] = \
                    current.get_grade_rev().grade.generate_scorecard()


    def do_forensic(this, arg):
        """forensic

Display forensic information stored in the PSF currently being manipulated, if
any.
        """

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        s = str(current) + "\n"
        s += current.format_forensic()

        this.symtab["#result"] = s

    def do_interact(this, arg):
        """interact

Begin an interactive shell session in the current PSF so that it may be graded.
        """

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        # TODO: make this configurable, maybe, but how to set --norc
        # portably?
        shell = ["bash", "--norc"]
        logging.debug("interact: shell set to '{}'".format(shell))

        # We annotate each PSF object with the workdir we're using, that way if
        # the user wants to interact with the same PSF more than once before
        # finalizing, they can.
        workdir = None
        if hasattr(current, "repl_workdir"):
            logging.debug("{} already annotated with workdir".format(current))
            workdir = current.repl_workdir
        else:
            workdir = tempfile.mkdtemp()
            current.repl_workdir = workdir
        workdir = pathlib.Path(workdir)
        logging.debug("interact: workdir is '{}'".format(workdir))

        # handle various case of revision symbol and graded status
        grade_revision = None
        if this.symtab["revision"] != "":
            if this.symtab["revision"] in current.revisions:
                # case where we have a known revision and it already exists
                grade_revision = current.get_revision(this.symtab["revision"])

            else:
                # case where we have a known revision, but it dosen't
                # exist yet
                logging.info("creating revision '{}'"
                        .format(this.symtab["revision"]))
                grade_revision = current.create_revision(
                        this.symtab["revision"], this.symtab["base_revision"])

        elif current.is_graded():
            logging.info("{} has already been graded. ".format(current) +
                    "If this is surprising, you may want to check for " +
                    "tampering.")
            grade_revision = current.create_grade_revision()
            this.symtab["revision"] = grade_revision.ID

        else:
            grade_revision = current.create_revision("graded_0",
                    this.symtab["base_revision"])
            this.symtab["revision"] = grade_revision.ID

        # Unpack the PSF into the workdir
        grade_revision.write_files(workdir / "submission")

        # make sure the metadata we'll need is present
        metadata = current.metadata
        metadata_ok = ("assignment" in metadata) and \
            ("group" in metadata) and \
            ("course" in metadata)

        if not metadata_ok:
            logging.warning("'{}' missing metadata".format(current))

        # we only need to create a new grade revision if there isn't one
        if grade_revision.grade is None:

            # load all courses in the coursepath
            courses = {}
            for p in this.symtab["coursepath"].split(":"):
                p = pathlib.Path(p)
                if p.is_file():
                    try:
                        c = course.load_course_definition(p)
                        courses[c.name] = c
                    except Exception as e:
                        util.log_exception(e)
                        logging.warning("failed to load course from '{}'"
                                .format(p))
                else:
                    for fp in p.glob("**/*.toml"):
                        try:
                            c = course.load_course_definition(fp)
                            courses[c.name] = c
                        except Exception as e:
                            util.log_exception(e)
                            logging.warning("failed to load course from '{}'"
                                    .format(fp))


            # Create a Grade object and associate it with this revision
            grade_obj = None
            if metadata_ok:
                if metadata["course"] not in courses:
                    logging.error("no course found in '{}': '{}'"
                            .format(this.symtab["coursepath"], metadata["course"]))

                elif metadata["assignment"] not in courses[metadata["course"]].assignments:
                    logging.error("no assignment '{}' in course '{}'"
                            .format(metadata["assignment"], metadata["course"]))

                elif grade_revision.grade is not None:
                    # this case should never occur
                    grade_obj = grade_revision.grade

                else:
                    grade_obj = grade.Grade(
                            courses[metadata["course"]].assignments[metadata["assignment"]])
                    grade_revision.grade = grade_obj

        grade_obj = grade_revision.grade

        if grade_obj is None:
            logging.warning("unable to instantiate new grade, PSF may have missing or invalid metadata")

        else:
            # write out grade file
            with open(workdir / "grade.toml", "w") as f:
                f.write(grade_obj.dump_string())

        env = dict(os.environ)
        env["PRETOR_WORKDIR"] = workdir
        env["PRETOR_VERSION"] = constants.version

        if metadata_ok:
            env["PS1"] = "grading {} by {} $ ".format(
                    current.metadata["assignment"],
                    current.metadata["group"])
        else:
            env["PS1"] = "grading [MISSING METADATA] $ "

        logging.info("dropping you to a shell: {}".format(' '.join(shell)))
        try:
            p = subprocess.Popen(shell, env = env, cwd = workdir)
            status = p.wait()
        except Exception as e:
            util.log_exception(e)

        logging.info("shell session terminated")

        # load up any changes made by the grader
        if grade_obj is not None:
            grade_obj.load_file(workdir / "grade.toml")

    def do_lsrev(this, arg):
        """lsrev

List all revisions that exist in the current file.

HINT: you can change your working revision via 'set revision REVID'.
"""

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        s = ""
        for revID in current.revisions:
            if revID == this.symtab["revision"]:
                s += "--> {}\n".format(revID)

            else:
                s += "    {}\n".format(revID)

        this.symtab["#result"] = s


    def do_shell(this, arg):
        """shell COMMAND

Execute a shell command via 'sh -c'. This can also be done by prefixing your
command with '!'. Users are encouraged not to try to be clever.

Note that commands like 'cd' will not affect the REPL.
        """

        this.symtab["#result"] = \
                subprocess.check_output(["sh", "-c", arg]).decode("utf-8")

    def do_loaded(this, arg):
        """loaded

        Display a list of all currently loaded PSF files.
        """

        if '#psf' not in this.symtab:
            this.fail("No PSF files loaded.")
            return

        else:
            s = ""
            for i in range(len(this.symtab["#psf"])):
                p = this.symtab["#psf"][i]
                if "#current_psf" in this.symtab:
                    if this.symtab["#current_psf"] == i:
                        s += "--> "
                    else:
                        s += "    "
                else:
                    s += "    "

                s += "{:4d}: ".format(i)

                if "archive_name" in p.metadata:
                    s += str(p.metadata["archive_name"]).split("/")[-1]
                else:
                    s += str(p)

                s += "\n"

            this.symtab["#result"] = s[:-1]  # chop off trailing \n

    def do_select(this, arg):
        """select PSFNO [force]

Change the active PSF to PSFNO, which is an index as shown by the loaded
command.

If "force" is specified, then the active PSF can be switched even if the
current one has not been finalized yet.
"""

        this.check_arg(1)

        if "#psf" not in this.symtab:
            this.fail("No PSFs loaded")
            return

        psfno = int(this.symtab["#argv"][1])
        force = "force" in this.symtab["#argv"]

        this.switch_to(psfno, force)

    def do_next(this, arg):
        """next [force]

Begin grading the next un-finalized PSF file in the queue.

If "force" is specified, then the active PSF can be switched even if the
current one has not been finalized yet.
        """

        if "#psf" not in this.symtab:
            this.fail("No PSFs loaded")
            return

        force = "force" in this.symtab["#argv"]

        for psfno in range(len(this.symtab["#psf"])):
            if psfno in this.symtab["#finalized"]:
                continue

            else:
                this.switch_to(psfno, force)
                break


    def do_finalize(this, arg):
        """finalize [next]

Finalizes the active PSF, causing it to be written out to disk in the specified
output directory. The output directory can be changed with 'set outputdir
/some/path'.
"""
        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        metadata_ok = True
        for key in ["semester", "course", "section", "group", "assignment"]:
            if key not in current.metadata:
                logging.warning("{} missing metadata: '{}', using UUID"
                        .format(this, key))
                metadata_ok = False


        if metadata_ok:
            name = "{}-{}-{}-{}-{}".format(
                        current.metadata["semester"],
                        current.metadata["course"],
                        current.metadata["section"],
                        current.metadata["group"],
                        current.metadata["assignment"])

        else:
            name = str(current.ID)

        name += ".psf"

        dest = pathlib.Path(this.symtab["outputdir"]) / name
        logging.info("writing to '{}'".format(dest))
        current.save_to_archive(dest)

        this.symtab["#finalized"].append(this.symtab["#current_psf"])
        this.symtab.pop("#current_psf")


    def switch_to(this, psfno, force):
        psfnow = int(psfno)

        if this.symtab["#psf"] not in this.symtab["#finalized"]:
            if "#current_psf" not in this.symtab:
                pass

            elif not force:
                this.fail("Your current PSF is not finalized, refusing to select")
                return

            else:
                logging.warning("force was specified, switching away from non-finalized PSF")

        if psfno in this.symtab["#finalized"]:
            logging.warning("PSF {} has been marked as finalized".format(psfno))

        print(psfno)
        print(this.symtab["#psf"])
        print(len(this.symtab["#psf"]))
        if (psfno > (len(this.symtab["#psf"]) - 1)) or (psfno < 0):
            this.fail("PSF {} does not identify a loaded PSF".format(psfno))
            return
        else:
            if "#current_psf" not in this.symtab:
                this.symtab["#current_psf"] = 0
            this.symtab["#current_psf"] = psfno

        this.do_current([])

    def do_symtab(this, arg):
        """symtab

Display the interpreter's current symbol table state.
        """
        this.symtab["#result"] = tabulate.tabulate(
                [(k, this.symtab[k]) for k in this.symtab], tablefmt="plain")

    def get_current(this):
        """get_current

Get the current PSF file, if any, return it or None if there is none.

        :param this:
        """

        if "#psf" in this.symtab and "#current_psf" in this.symtab:
            return this.symtab["#psf"][this.symtab["#current_psf"]]
        else:
            return None

    def load_psf(this, target: pathlib.Path):
        """load_psf

        Load a single PSF.

        :param this:
        """

        target = pathlib.Path(target)

        if "#psf" not in this.symtab:
            this.symtab["#psf"] = []

        the_psf = psf.PSF()
        the_psf.load_from_archive(target)
        this.symtab["#psf"].append(the_psf)

    def debug(this):
        # Drop to a PDB debugging shell. This command is only useful for
        # debugging Pretor, and should generally not be used during grading.
        #
        # This is deliberately undocumented to reduce the chance that an
        # unwitting use will activate it by mistake

        logging.warning("Dropping to interactive PDB shell. If this was " +
                "a mistake, enter 'continue' to resume the Pretor REPL.")

        pdb.set_trace()

    def fail(this, msg):
        """fail

        Set #status to False and provide a message for #error.

        :param this:
        :param msg:
        """

        this.symtab["#status"] = False
        this.symtab["#error"] = msg

    def check_arg(this, n):
        """check_arg

        Throw an error if length of #argv is not at least n+1.

        :param this:
        :param n:
        """

        if len(this.symtab["#argv"]) < (n + 1):
            this.fail("Too few arguments, required at least {}".format(n))
            return False

        return True

    def default(this, line):
        if line.startswith('#'):
            # comment, do nothing
            pass
        elif line == "debug":
            # don't connect the debug command to the normal command processing
            # infrastructure, that way it won't appear in the help output.
            this.debug()
        else:
            super().default(line)

    def emptyline(this):
        # do nothing on empty lines
        pass

    def exec(this, s):
        # execute a command, including precmd and postcmd

        this.precmd(s)
        this.onecmd(s)
        this.postcmd(False, s)

    def onecmd(this, s):
        try:
            super().onecmd(s)
        except Exception as e:
            util.log_exception(e)
            this.symtab["#error"] = \
                    "exception while processing command '{}'".format(s)
            this.symtab["#status"] = False

    def precmd(this, line):
        # shlex will preserve quoted groups
        this.symtab["#argv"] = shlex.split(line)
        this.history.append(line.strip())

        # reset symbol table constant
        this.symtab["#laststatus"] = this.symtab["#status"]
        this.symtab["#lastresult"] = this.symtab["#result"]
        this.symtab["#error"] = ""
        this.symtab["#status"] = True
        this.symtab["#result"] = None

        return line

    def postcmd(this, stop, line):
        if this.symtab["#result"] is not None:
            sys.stdout.write("{}\n".format(str(this.symtab["#result"])))

        if not this.symtab["#status"]:
            sys.stdout.write("ERROR: {}\n".format(str(this.symtab["#error"])))

        return False

    def preloop(this):
        cmd.Cmd.preloop(this)

def signal_handler(sig, frame):
    sys.stdout.flush()
    sys.stdout.write("Caught ^C. Use ^D or 'exit' to exit\n")
    sys.stdout.write("> ")
    sys.stdout.flush()

def launch_repl():
    """repl

    Launch the Pretor grader interactive REPL.
    """

    parser = argparse.ArgumentParser("""Interactive REPL used to grade
PSF formatted submissions.""")

    parser.add_argument("--version", action="version",
            version=constants.version)

    parser.add_argument("--debug", "-d", action="store_true", default=False,
            help="Log debugging output to the console.")

    parser.add_argument("--coursepath", "-c", default=None,
            help="Specify the directory where course files are stored. " +
            "If omitted, this can be set interactively via " +
            "'set coursedir /some/path'. Note that a single course file " +
            "may be specified instead of a directory if desired. " +
            "Multiple files or directories may be specified, delimited with " +
            "the ':' character")

    parser.add_argument("--ingest", "-i", default=None,
            help="Automatically ingest the PSF files from the specified " +
            "directory. This can be done interactively via the 'ingest' " +
            "command.")

    parser.add_argument("--outputdir", "-o", default=None,
            help="Specify the directory where finalized PSF files should " +
            "be saved. This may be specified interactively via " +
            "'set outputdir /some/path'. (default: ./)")

    parser.add_argument("--rc", "-r", type=pathlib.Path,
            default=pathlib.Path("~/.config/pretor/rc").expanduser(),
            help="Specify RC file to use. Each line in this file is " +
            "executed before beginning the interactive REPL. " +
            "(default: ~/.config/pretor/rc")

    parser.add_argument("--plugin_dir", "-p", type=pathlib.Path, default=None,
            help="Load plugins from the specified directory before launching" +
            " the REPL. This is in addition to any plugins specified by " +
            "the course definition file.")

    parser.add_argument("--no_course_plugins", "-N", default=False,
            action="store_true", help="Don't load plugins specified by " +
            "course definition files.")

    args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    the_repl = REPL()

    if args.coursepath is not None:
        the_repl.exec("set coursepath '{}'".format(args.coursepath))

    if args.ingest is not None:
        the_repl.exec("ingest '{}'".format(args.ingest))

    if args.outputdir is not None:
        this.repl.exec("set outputdir '{}'".format(args.outputdir))

    if args.rc.exists():
        logging.debug("loading RC file '{}'".format(args.rc))
        with open(args.rc, 'r') as f:
            for line in f:
                the_repl.exec(line)

    signal.signal(signal.SIGINT, signal_handler)

    the_repl.cmdloop()
