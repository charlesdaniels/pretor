import cmd
import os
import sys

import pretor

class PretorShell(cmd.Cmd):

    intro = "PRETOR version {} interactive grading shell.".format(pretor.__version__)
    prompt = "grader> "
    file = None


    def do_exit(this, arg):
        """
        exit

        Exit pretor.

        """

        sys.exit(0)

    def do_history(this, arg):
        """
        history

        Return a list of previously entered commands
        """

        this.symtab["#result"] = '\n'.join(this.history)

    def do_EOF(this, arg):
        "Exit when EOF is read"

        print("caught EOF")
        sys.exit(0)

    def do_pwd(this, arg):
        """
        pwd

        Return current working directory.
        """

        this.symtab["#result"] = os.getcwd()

    def do_s(this, arg):
        """
        s [command]

        Alias for shell.
        """

        return this.do_shell(arg)

    def do_shell(this, arg):
        """
        shell [command]

        Execute a command in the system shell.
        """

        os.system(arg)

    def do_ls(this, arg):
        """
        ls

        Display a directory listing.
        """

        s = "directory listing for '{}'\n".format(os.getcwd())

        count = 0
        for item in os.listdir(os.getcwd()):
            s += "\t{}\n".format(item)
            count += 1
        s += "{} items".format(count)

        this.symtab["#result"] = s

    def do_ingest(this, arg):
        """
        ingest [path]

        Mark a directory of student submission PSF files for grading in this
        session. The specified path is traversed recursively to identify files
        to load. All files with the .psf extension are marked for grading.  If
        [path] is a file, that file will be unconditionally marked for grading
        regardless of extension. The files to be ingested will not be modified
        on disk.
        """

    def do_execbg(this, arg):
        """
        execbg

        All submission files marked for grading which have not yet been
        executed are executed in the background. Note that any files marked
        with interactive=true in their relevant assignment file will not be
        executed via this command. This command will also not execute any
        assignments which have not been marked with parallel_safe=true.
        """

    def do_next(this, arg):
        """
        next

        Begin grading the next ungraded submission file which has been marked
        for grading. This will move the interpreter session into the
        submissions execution environment, and will begin executing the
        assignment if it has not already been executed using execbg.
        """

    def do_exec(this, arg):
        """
        exec

        Available only while grading an assignment. Re-executes the assignments
        grading script on the assignment as it exists in the execution
        environment (i.e. including any grader-made modifications).
        """

    def do_edit(this, arg):
        """
        edit [path]

        Available only while grading an assignment. Edits the specified file
        in the execution environment.
        """

    def do_score(this, arg):
        """
        score [item] [score] [remark]

        Available only while grading an assignment. Assign a score to an item
        on the rubric, replacing any existing value.  [score] must be specified
        as an integer percentage in 0..100 (point value will be calculated from
        the rubric). The remark field is optional, and is a string of text that
        will be visible on the
        student-facing report.

        If this command is called without any arguments, then the current
        score and remark on each item on the rubric for this assignment
        is displayed instead.
        """

    def do_rubric(this, arg):
        """
        rubric

        Available only while grading an assignment. Display the rubric for this
        assignment.
        """

    def do_override(this, arg):
        """
        override [point value] [remark]

        Available only while grading an assignment. Add an additional [point
        value] points to the overall score beyond any rubric category. This
        is useful for adding bonus points or similar.
        """

    def do_finalize(this, arg):
        """
        finalize

        Available only while grading an assignment. Finish grading the
        assignment and record the score and remarks to the gradebook.
        """

    def do_autofinalize(this, arg):
        """
        autofinalize [threshold]

        Automatically finalize all assignments which currently have a score
        greater equal to [threshold]. [threshold] must be specified as an
        integer percentage in 0..100.
        """

    def precmd(this, line):
        this.symtab["#argv"] = line.split()
        this.history.append(line.strip())

        # reset symbol table constant
        this.symtab["#laststatus"] = this.symtab["#status"]
        this.symtab["#lastresult"] = this.symtab["#result"]
        this.symtab["#error"] = ""
        this.symtab["#status"] = True
        this.symtab["#result"] = ""

        return line

    def postcmd(this, stop, line):
        if str(this.symtab["#result"] != ""):
            sys.stdout.write("{}\n".format(str(this.symtab["#result"]).strip()))

        if not this.symtab["#status"]:
            sys.stdout.write("ERROR: {}\n".format(str(this.symtab["#error"]).strip()))

        return False

    def preloop(this):
        cmd.Cmd.preloop(this)
        this.history = []
        this.symtab = {}
        this.symtab["#result"] = ""
        this.symtab["#lastresult"] = ""
        this.symtab["#status"] = True
        this.symtab["#laststaus"] = True
        this.symtab["#error"] = ""

def repl():
    """repl

    Launch the Pretor grader interactive REPL.
    """

    PretorShell().cmdloop()

if __name__ == "__main__":
    repl()
