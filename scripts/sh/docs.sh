#!/usr/bin/env bash
# Sincroniza os blocos ```mermaid dos .md com os arquivos docs/md/diagramas/*.mmd (fonte única).
#   docs.sh          reescreve os blocos
#   docs.sh --check  falha se algum bloco estiver desatualizado (uso em CI)
#   docs.sh --render renderiza os .mmd em SVG (requer mmdc) em build/docs/ para validar a sintaxe
source "$(dirname "$0")/lib.sh"

mode="${1:-}"

if [[ "$mode" == "--render" ]]; then
    command -v mmdc >/dev/null || { echo "mmdc não encontrado (npm i -g @mermaid-js/mermaid-cli)" >&2; exit 2; }
    mkdir -p build/docs
    for f in docs/md/diagramas/*.mmd; do
        echo ">> mmdc $f"
        mmdc -i "$f" -o "build/docs/$(basename "$f" .mmd).svg" -q
    done
    exit 0
fi

python3 - "$mode" <<'PY'
import pathlib
import re
import sys

check = sys.argv[1] == "--check"
root = pathlib.Path("docs/md")
pattern = re.compile(r"(<!-- mmd:(?P<name>[\w-]+) -->\n)(.*?)(<!-- /mmd -->)", re.S)
stale: list[str] = []

for md in sorted([*root.glob("*.md"), pathlib.Path("README.md")]):
    text = md.read_text(encoding="utf-8")

    def render(match: re.Match[str]) -> str:
        source = (root / "diagramas" / f"{match['name']}.mmd").read_text(encoding="utf-8").rstrip()
        return f"{match[1]}```mermaid\n{source}\n```\n{match[4]}"

    updated = pattern.sub(render, text)
    if updated != text:
        stale.append(str(md))
        if not check:
            md.write_text(updated, encoding="utf-8")

if check and stale:
    print("Diagramas desatualizados (rode `make docs`): " + ", ".join(stale), file=sys.stderr)
    sys.exit(1)
print("Diagramas sincronizados." if not stale or check else f"Atualizados: {', '.join(stale)}")
PY
