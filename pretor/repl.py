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

        if target.is_file():
            logging.info("Loading PSF file '{}'".format(target))
            this.load_psf(target)
        else:
            this.fail("not yet implemented")

    def do_current(this, arg):
        """current

Display information about the PSF currently being manipulated, if any.
        """

        current = this.get_current()

        if current is None:
            this.fail("Not working on any PSF currently.")
            return

        s = str(current) + "\n"
        s += current.format_metadata()

        this.symtab["#result"] = s

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

        shell = os.getenv("SHELL")
        if shell is None or shell == "":
            shell = "sh"
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
        logging.debug("interact: workdir is '{}'".format(workdir))

        # Unpack the PSF into the workdir
        #
        # TODO: this needs to be *much* more robust, namely need to handle
        # inputs with revisions other than 'submission', and cases where there
        # is already a graded revision.
        if "graded" in current.revisions:
            logging.warning("revising grades is not properly supported yet, any changes you make will overwrite the previous grade information")
        else:
            current.create_revision("graded",
                    current.get_revision("submission"))
        grade_revision = current.get_revision("graded")
        grade_revision.write_files(workdir)

        env = dict(os.environ)
        env["PRETOR_WORKDIR"] = workdir
        env["PRETOR_VERSION"] = constants.version

        # https://stackoverflow.com/a/43012138

        # save original tty setting then set it to raw mode
        old_tty = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

        # open pseudo-terminal to interact with subprocess
        master_fd, slave_fd = pty.openpty()

        # use os.setsid() make it run in a new process group, or bash job
        # control will not be enabled
        p = subprocess.Popen(shell,
                  preexec_fn=os.setsid,
                  stdin=slave_fd,
                  stdout=slave_fd,
                  stderr=slave_fd,
                  universal_newlines=True,
                  env=env)

        # set prompt and CD to the workdir
        os.write(master_fd, b'export PS1="(pretor-repl) $PS1"\n')
        os.write(master_fd, b'cd "$PRETOR_WORKDIR"\n')

        while p.poll() is None:
            r, w, e = select.select([sys.stdin, master_fd], [], [])
            if sys.stdin in r:
                d = os.read(sys.stdin.fileno(), 10240)
                os.write(master_fd, d)
            elif master_fd in r:
                o = os.read(master_fd, 10240)
                if o:
                    os.write(sys.stdout.fileno(), o)

        status = p.wait()

        # restore tty settings back
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)


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

                s += str(p) + "\n"

            this.symtab["#result"] = s[:-1]  # chop off trailing \n

    def do_next(this, arg):
        """next

Begin grading the next PSF file in the queue.
        """

        # TODO: should check if the current PSF is finished being graded and
        # error out if not as a safety feature. This will require hooks into
        # psf.PSF to handle stored grades.

        # TODO: rather than linearly advancing, should search through all of
        # #psf for the next ungraded one, in case we skipped one for some
        # reason.

        if "#psf" not in this.symtab:
            this.fail("No PSFs loaded")
            return

        if "#current_psf" not in this.symtab:
            this.symtab["#current_psf"] = 0
        else:
            if this.symtab["#current_psf"] >= (len(this.symtab["#psf"]) - 1):
                this.fail("Reached end of queue, no further PSF files to process")
            else:
                this.symtab["#current_psf"] += 1

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

    parser.add_argument("--coursedir", "-c", default=None,
            help="Specify the directory where course files are stored. " +
            "If omitted, this can be set interactively via " +
            "'set coursedir /some/path'. Note that a single course file " +
            "may be specified instead of a directory if desired.")

    parser.add_argument("--ingest", "-i", default=None,
            help="Automatically ingest the PSF files from the specified " +
            "directory. This can be done interactively via the 'ingest' " +
            "command.")

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

    if args.rc.exists():
        logging.debug("loading RC file '{}'".format(args.rc))
        with open(args.rc, 'r') as f:
            for line in f:
                the_repl.exec(line)

    if args.coursedir is not None:
        the_repl.exec("set coursedir '{}'".format(args.coursedir))

    if args.ingest is not None:
        the_repl.exec("ingest '{}'".format(args.ingest))

    signal.signal(signal.SIGINT, signal_handler)

    the_repl.cmdloop()
