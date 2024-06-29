target="$1"
processing="$2"

if [[ "$processing" == "dithering+resize+cropping" ]]
then
    tmpdir=$(mktemp -d)
    mv "$target" $tmpdir/
    convert "$tmpdir/$(basename $target)" \
        -background white \
        -alpha remove \
        -alpha off \
        -contrast-stretch 5%x5% \
        -colorspace gray \
        -ordered-dither o8x8 \
        -resize 991x \
        -gravity Center \
        -extent 991x306 \
        "$target"
fi
