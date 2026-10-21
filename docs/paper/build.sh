#!/bin/sh
# Builds the paper's PDFs from docs/paper.md and its translations (docs/paper.<lang>.md) with pandoc and LaTeX (tectonic).
#   sh docs/paper/build.sh            # every language
# Needs pandoc 3, tectonic and pdftocairo (poppler). The figures (docs/figures/*.tex) are compiled first, to PDF for
# the paper and to SVG for the markdown; a figure is rebuilt when its source or any data file in docs/figures is newer.
# The figure data comes from the registry: python3 tools/paper-figures.py.
set -e
here=$(cd "$(dirname "$0")" && pwd)
docs=$(dirname "$here")
for f in "$docs"/figures/*.tex; do
  [ -e "$f" ] || continue
  b=${f%.tex}
  base=${b%-fr}
  stale=
  if [ ! -e "$b.pdf" ] || [ "$f" -nt "$b.pdf" ] || [ "$base.tex" -nt "$b.pdf" ]; then stale=1; fi
  for d in "$docs"/figures/*.dat; do [ -e "$d" ] && [ "$d" -nt "$b.pdf" ] && stale=1; done
  if [ -n "$stale" ]; then
    tectonic -X compile --outdir "$docs/figures" "$f" 2>&1 | grep -v "^note:" | grep -v "/dev/null" || true
    pdftocairo -svg "$b.pdf" "$b.svg"
  fi
done
build() { # $1 source, $2 output
  pandoc "$docs/$1" --from markdown+tex_math_dollars+raw_tex --template "$here/template.tex" \
    --lua-filter "$here/figures.lua" --citeproc --bibliography "$here/references.bib" --csl "$here/ieee.csl" --lua-filter "$here/colons.lua" \
    -H "$here/style.tex" -H "$here/colours.tex" --resource-path "$docs:$here" --number-sections --toc --pdf-engine=tectonic -o "$docs/$2"
}
base=n-ways-addressing-gabon
for src in "$docs"/paper.md "$docs"/paper.*.md; do
  [ -e "$src" ] || continue
  name=$(basename "$src")
  case $name in paper.md) lang=en ;; *) lang=${name#paper.}; lang=${lang%.md} ;; esac
  build "$name" "$base-$lang.pdf"
done
