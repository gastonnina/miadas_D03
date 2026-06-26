TEXFILE = main
DOCS_DIR = docs
PDF_NAME = monografia_gaston_nina_sossa.pdf
LATEXINDENT = latexindent

.PHONY: all bib quick clean format logs copy-pdf help

help:
	@echo "Targets disponibles:"
	@echo "  make quick     -> compilacion rapida con pdflatex"
	@echo "  make bib       -> compilacion completa de la monografia"
	@echo "  make all       -> alias de bib"
	@echo "  make clean     -> limpia archivos auxiliares de LaTeX"
	@echo "  make format    -> formatea archivos .tex con latexindent"
	@echo "  make logs      -> muestra las ultimas lineas del log"
	@echo "  make copy-pdf  -> copia el PDF compilado a la raiz"

all: bib

quick:
	@echo "Compilando LaTeX sin bibliografia..."
	@cd $(DOCS_DIR) && pdflatex $(TEXFILE).tex

bib:
	@echo "Compilando LaTeX completo..."
	@cd $(DOCS_DIR) && pdflatex $(TEXFILE).tex
	@cd $(DOCS_DIR) && pdflatex $(TEXFILE).tex
	@cd $(DOCS_DIR) && pdflatex $(TEXFILE).tex

clean:
	@echo "Limpiando auxiliares..."
	@cd $(DOCS_DIR) && latexmk -C $(TEXFILE).tex || true
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
		$(DOCS_DIR)/*.toc

format:
	@echo "Formateando archivos .tex..."
	@for file in $(DOCS_DIR)/main.tex $(DOCS_DIR)/sections/*.tex; do \
		echo "Formateando $$file"; \
		$(LATEXINDENT) -w $$file; \
	done

logs:
	@echo "Ultimas lineas de $(DOCS_DIR)/main.log"
	@tail -n 80 $(DOCS_DIR)/main.log || true

copy-pdf:
	@echo "Copiando PDF compilado a la raiz..."
	@cp $(DOCS_DIR)/$(TEXFILE).pdf ./$(PDF_NAME)
