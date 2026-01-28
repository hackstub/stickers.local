set -eux

echo starting script
target="$1"

target="postprocessimg/$(basename "$target")"

target_png="${target%.*}".png
if [[ "$target_png" != "$target" ]]
then
    convert "$1" "$target_png"
    rm $target
    target="$target_png"
else
    cp $1 $target
fi


W="$(identify -format '%w' $target)"
H="$(identify -format '%h' $target)"
DITHERING=true
#SIZE=small # aleks was here
if ([[ "$SIZE" == "big" ]] && [[ "$H" -gt "$W" ]]) || ([[ "$SIZE" == "small" ]] && [[ "$W" -gt "$H" ]])
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
    ./didder_1.3.0_linux_arm64 \
        --height 696 \
        --brightness 0.1 \
        --palette "black white" \
        --in "$target_before_process" \
        --out "$target" \
        edm --serpentine FloydSteinberg
else
    #convert "$target_before_process" -resize 696x "$target"
		    cp "$target_before_process" "$target"
		fi
		rm -f $target_before_process
