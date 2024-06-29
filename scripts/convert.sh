target="$1"
processing="$2"

if [[ "$processing" == "dithering+resize+cropping" ]]
then
    tmpdir=$(mktemp -d)
    tmpdir2=$(mktemp -d)
    mv "$target" $tmpdir/
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

    # From https://github.com/makew0rld/didder/releases
    $(dirname $0)/didder_1.3.0_linux_64-bit \
        --strength 70% \
        --contrast 0.1 \
        --palette "black white" \
        --width 991 \
        --input "$tmpdir/$(basename $target)" \
        --ouput "$tmpdir2/$target" \
        edm --serpentine FloydSteinberg

    convert "$tmpdir2/$(basename $target)" \
        -resize 991x \
        -gravity Center \
        -extent 991x306 \
        "$target"
fi
