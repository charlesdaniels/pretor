.PHONY: clean

student_manual.pdf: student_manual.tex pretor.sty
	latexmk -pdf student_manual.tex
	latexmk -c student_manual.tex

clean:
	latexmk -C student_manual.tex
