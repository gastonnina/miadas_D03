TEXFILE = main
DOCS_DIR = docs
PDF_NAME = monografia_gaston_nina_sossa.pdf
LATEXINDENT = latexindent
PDFLATEX = pdflatex
LATEXMK = latexmk

.PHONY: all bib quick clean format logs copy-pdf copy help

help:
	@echo "Targets disponibles:"
	@echo "  make quick     -> compilacion rapida con pdflatex"
	@echo "  make bib       -> compilacion completa de la monografia"
	@echo "  make all       -> alias de bib"
	@echo "  make clean     -> limpia archivos auxiliares de LaTeX"
	@echo "  make format    -> formatea archivos .tex con latexindent"
	@echo "  make logs      -> muestra las ultimas lineas del log"
	@echo "  make copy      -> alias de copy-pdf"
	@echo "  make copy-pdf  -> copia el PDF compilado a la raiz"
	@echo ""
	@echo "Requisitos del sistema:"
	@echo "  pdflatex   -> para quick / bib / all"
	@echo "  latexmk    -> opcional para clean"
	@echo "  latexindent -> opcional para format"

all: bib

quick:
	@command -v $(PDFLATEX) >/dev/null 2>&1 || { \
		echo "Error: '$(PDFLATEX)' no esta instalado."; \
		echo "Instala una distribucion LaTeX que incluya pdflatex."; \
		exit 127; \
	}
	@echo "Compilando LaTeX sin bibliografia..."
	@cd $(DOCS_DIR) && $(PDFLATEX) $(TEXFILE).tex

bib:
	@command -v $(PDFLATEX) >/dev/null 2>&1 || { \
		echo "Error: '$(PDFLATEX)' no esta instalado."; \
		echo "Instala una distribucion LaTeX que incluya pdflatex."; \
		exit 127; \
	}
	@echo "Compilando LaTeX completo..."
	@cd $(DOCS_DIR) && $(PDFLATEX) $(TEXFILE).tex
	@cd $(DOCS_DIR) && $(PDFLATEX) $(TEXFILE).tex
	@cd $(DOCS_DIR) && $(PDFLATEX) $(TEXFILE).tex

clean:
	@echo "Limpiando auxiliares..."
	@if command -v $(LATEXMK) >/dev/null 2>&1; then \
		cd $(DOCS_DIR) && $(LATEXMK) -C $(TEXFILE).tex || true; \
	else \
		echo "Aviso: '$(LATEXMK)' no esta instalado; se omitira esa parte del clean."; \
	fi
	@rm -f $(DOCS_DIR)/*.aux \
		$(DOCS_DIR)/*.bbl \
		$(DOCS_DIR)/*.bcf \
		$(DOCS_DIR)/*.blg \
		$(DOCS_DIR)/*.fdb_latexmk \
		$(DOCS_DIR)/*.fls \
		$(DOCS_DIR)/*.lof \
		$(DOCS_DIR)/*.log \
		$(DOCS_DIR)/*.lol \
		$(DOCS_DIR)/*.lot \
		$(DOCS_DIR)/*.out \
		$(DOCS_DIR)/*.run.xml \
		$(DOCS_DIR)/*.synctex.gz \
		$(DOCS_DIR)/*.toc \
		$(DOCS_DIR)/sections/*.aux

format:
	@command -v $(LATEXINDENT) >/dev/null 2>&1 || { \
		echo "Error: '$(LATEXINDENT)' no esta instalado."; \
		echo "Instalalo si quieres autoformato de archivos .tex."; \
		exit 127; \
	}
	@echo "Formateando archivos .tex..."
	@for file in $(DOCS_DIR)/main.tex $(DOCS_DIR)/sections/*.tex; do \
		echo "Formateando $$file"; \
		$(LATEXINDENT) -w $$file; \
	done

logs:
	@echo "Ultimas lineas de $(DOCS_DIR)/main.log"
	@tail -n 80 $(DOCS_DIR)/main.log || true

copy-pdf:
	@test -f $(DOCS_DIR)/$(TEXFILE).pdf || { \
		echo "Error: no existe $(DOCS_DIR)/$(TEXFILE).pdf."; \
		echo "Ejecuta 'make quick' o 'make all' antes de copiar el PDF."; \
		exit 1; \
	}
	@echo "Copiando PDF compilado a la raiz..."
	@cp $(DOCS_DIR)/$(TEXFILE).pdf ./$(PDF_NAME)

copy: copy-pdf
