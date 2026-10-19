#!/usr/bin/env bash
# Compile each figure in src/ to an SVG beside this script.
#
# src/<name>.tex is the body of one display (panels joined by \mapsto, + and so on);
# src/panels/ holds the TikZ panels it inputs, copied from the writeup.  Needs pdflatex
# (with tikz and contour) and pdftocairo (poppler-utils).
#
#     bash docs/figs/build.sh            # every figure
#     bash docs/figs/build.sh case_start # just these

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
build="$here/build"
mkdir -p "$build"

if [ "$#" -gt 0 ]; then
    names=("$@")
else
    names=()
    for f in "$here"/src/*.tex; do names+=("$(basename "$f" .tex)"); done
fi

for name in "${names[@]}"; do
    cat > "$build/wrap_$name.tex" <<EOF
\\documentclass[border=4pt]{standalone}
\\usepackage{amsmath,amssymb}
\\usepackage{tikz}
\\usepackage[outline]{contour}
\\contourlength{1.2pt}
\\newcommand{\\includetikz}[2][]{%
  \\begin{tikzpicture}[#1,every node/.append style={scale=1}, inner sep=0pt, outer sep=0pt]
    \\input{#2}
  \\end{tikzpicture}%
}
\\pagecolor{white}
\\begin{document}
\$\\displaystyle \\input{$name.tex}\$
\\end{document}
EOF
    (cd "$here/src" && pdflatex -interaction=nonstopmode -halt-on-error \
        -output-directory="$build" "$build/wrap_$name.tex" > /dev/null) \
        || { echo "pdflatex failed on $name; see $build/wrap_$name.log" >&2; exit 1; }
    pdftocairo -svg "$build/wrap_$name.pdf" "$here/$name.svg"
    echo "$name.svg"
done
