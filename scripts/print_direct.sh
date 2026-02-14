set -eux

echo starting script

export BROTHER_QL_PRINTER=file:///dev/usb/lp0
export BROTHER_QL_MODEL=QL-570
export BROTHER_QL_MODEL=QL-720NW
$(dirname $0)/../venv/bin/brother_ql print -l 62 "$1"
