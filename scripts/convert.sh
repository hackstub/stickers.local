target="$1"
processing="$2"

set -x

if [[ "$processing" == "dithering+resize" ]]
then
    tmpdir=$(mktemp -d)
    #convert "$tmpdir/$(basename $target)" \
    #    -background white \
    #    -alpha remove \
    #    -alpha off \
    #    -contrast-stretch 5%x5% \
    #    -colorspace gray \
    #    -ordered-dither o8x8 \
    #    -resize 991x \
    #    -gravity Center \
    #    -extent 991x306 \
    #    "$target"

    target_png="${target%.*}".png
    if [[ "$target_png" != "$target" ]]
    then
        convert "$target" "$target_png"
        rm "$target"
        target="$target_png"
    fi

    # From https://github.com/makew0rld/didder/releases
    mv "$target" $tmpdir/
        #--contrast 0.1 \
    ./scripts/didder_1.3.0_linux_64-bit \
        --height 696 \
        --brightness 0.5 \
        --palette "black white" \
        --in "$tmpdir/$(basename $target)" \
        --out "$target" \
        edm --serpentine FloydSteinberg

    #convert "$tmpdir2/$(basename $target)" \
    #    -resize 991x \
    #    -gravity Center \
    #    -extent 991x306 \
    #    "$target"
   
    rm -rf "$tmpdir"
fi
