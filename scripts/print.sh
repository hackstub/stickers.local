set -eux

target="$1"

tmpdir=$(mktemp -d)
cp "$target" "$tmpdir"
target="$tmpdir/$(basename $target)"

target_png="${target%.*}".png
if [[ "$target_png" != "$target" ]]
then
    convert "$target" "$target_png"
    rm "$target"
    target="$target_png"
fi


W="$(identify -format '%w' $target)"
H="$(identify -format '%h' $target)"
if ([[ "$SIZE" == "big" ]] && [[ "$H" -gt "$W" ]]) || ([[ "$SIZE" == "small" ]] && [[ "$W" -gt "$H" ]])
then
    target_before_rotation="${target%.*}".before_rotate.png
    mv "$target" "$target_before_rotation"
    convert "$target_before_rotation" -rotate 90 "$target"
fi


if [[ "$DITHERING" == "true" ]]
then
    # From https://github.com/makew0rld/didder/releases
        #--contrast 0.1 \
    target_before_dither="${target%.*}".before_dither.png
    mv "$target" "$target_before_dither"
    ./scripts/didder_1.3.0_linux_64-bit \
        --height 696 \
        --brightness 0.1 \
        --palette "black white" \
        --in "$target_before_dither" \
        --out "$target" \
        edm --serpentine FloydSteinberg
else
    target_before_resize="${target%.*}".before_resize.png
    convert "$target_before_resize" \
        -resize 696x \
        "$target"
fi

export BROTHER_QL_PRINTER=file:///dev/usb/lp0
export BROTHER_QL_MODEL=QL-570
#brother_ql print -r90 -l 29x90 "$1"
brother_ql print -r90 -l 62 "$target"

rm -rf "$tmpdir"
