# Pretor

**Pretor** - *an ancient Roman magistrate ranking below a consul and having
chiefly judicial functions*
([Merriam-Webster](https://www.merriam-webster.com/dictionary/pretor))

Pretor is a *grading assistant* designed to make programming assignments easier
for both students and instructors. It features an easy to use tool for students
to pack up their assignments, and a powerful REPL for graders to interact with
student submission. Pretor is written entirely in Python 3, and is distributed
under the GPLv3 license.

<!-- vim-markdown-toc GFM -->

* [Overview](#overview)
* [Documentation](#documentation)

<!-- vim-markdown-toc -->

## Overview

Pretor offers the following key features:

* Student assignments are always packed in a consistent fashion (no more
  inconsistent file formats or rooting).

* Grades, student submissions, and any changes made by the grader (i.e. fixing
  a compile errors) are stored in a single archive file.

* Archive files are readable using standard zip file viewers.

* Support for any level of automation, from fully manual to fully automatic,
  or anything in between.

* Track multiple revisions to a student's submission grade over time.

* Plugin system to allow pre-packing validation, and extensions to the grading
  REPL. ([WiP](https://github.com/HeRCLab/pretor/issues?q=is%3Aissue+is%3Aopen+label%3A%22plugin+system%22))

## Documentation

* [Student's Manual](manual/student_manual.pdf)
* [Instructor's Manual](manual/instructor_manual.pdf)


----

Copyright (c) 2019 Charles A Daniels, made available under the GNU GPLv3
license. See [LICENSE](./LICENSE) and [COPYING](./COPYING).
