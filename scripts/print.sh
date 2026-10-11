set -eux

# Options from the env file
[[ ! -e ../.env ]] || source ../.env
PRINTER=${PRINTER:-/dev/usb/lp0}
PRINTER_MODEL=${PRINTER_MODEL:-QL-570}
DEFAULT_PRINT_SIZE=${DEFAULT_PRINT_SIZE:-large}
PAPER_WIDTH=${PAPER_WIDTH:-62}
IMAGE_PREPROCESSING_WIDTH=${IMAGE_PREPROCESSING_WIDTH:-696}

# Options from the python call
DITHERING=${DITHERING:-true}
QUANTITY=${QUANTITY:-1}
SIZE=${SIZE:-default}
if [[ "$SIZE" == "default" ]]
then
    SIZE="${DEFAULT_PRINT_SIZE:-large}"
fi

target="$1"

tmpdir=$(mktemp -d)
cp "$target" "$tmpdir"
target="$tmpdir/$(basename "$target")"

target_png="${target%.*}".png
if [[ "$target_png" != "$target" ]]
then
    convert "$target" "$target_png"
    rm "$target"
    target="$target_png"
fi

W="$(identify -format '%w' $target)"
H="$(identify -format '%h' $target)"

#SIZE=small # aleks was here
if ([[ "$SIZE" == "large" ]] && [[ "$H" -gt "$W" ]]) || ([[ "$SIZE" == "small" ]] && [[ "$W" -gt "$H" ]])
then
    target_before_rotation="${target%.*}".before_rotate.png
    mv "$target" "$target_before_rotation"
    convert "$target_before_rotation" -rotate 90 "$target"
fi

target_before_process="${target%.*}".before_dither.png
mv "$target" "$target_before_process"
if [[ "$DITHERING" == "true" ]]
then
    # From https://github.com/makew0rld/didder/releases
        #--contrast 0.1 \
    if [[ $(uname -m) == "x86_64" ]]
    then
        didder_suffix="64-bit"
    elif [[ $(uname -m) == "aarch64" ]]
    then
        didder_suffix="arm64"
    else
       echo "Uhoh, c'est quoi $(uname -m) comme archi?!"
       exit 1
    fi
    ./scripts/didder_1.3.0_linux_${didder_suffix} \
        --height $IMAGE_PREPROCESSING_WIDTH \
        --brightness 0.1 \
        --palette "black white" \
        --in "$target_before_process" \
        --out "$target" \
        edm --serpentine FloydSteinberg
else
    #convert "$target_before_process" -resize 696x "$target"
    cp "$target_before_process" "$target"
fi

export BROTHER_QL_PRINTER=file://$PRINTER
export BROTHER_QL_MODEL=$PRINTER_MODEL
for I in $(seq 1 $QUANTITY)
do
    $(dirname $0)/../venv/bin/brother_ql print -r90 -l ${PAPER_WIDTH:-64} "$target"
    sleep 0.1
done

rm -rf "$tmpdir"
