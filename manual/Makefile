.PHONY: clean all

all: student_manual.pdf instructor_manual.pdf

student_manual.pdf: student_manual.tex pretor.sty
	latexmk -pdf student_manual.tex
	latexmk -c student_manual.tex

instructor_manual.pdf: instructor_manual.tex pretor.sty
	latexmk -pdf instructor_manual.tex
	latexmk -c instructor_manual.tex

clean:
	latexmk -C student_manual.tex
	latexmk -C instructor_manual.tex
