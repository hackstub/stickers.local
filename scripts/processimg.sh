set -eux

echo starting script
target="$1"
imagesdir="/home/pi/stickers.local/assets/uploads"

# on enregistre l'emplacement de destination en gardant le nom de la collection et le nom du fichier
target="$imagesdir/postprocessimg/$(echo $1 | rev | cut -d / -f 1-2 | rev )"
echo $target
#target="postprocessimg/$(basename "$target")"

# nom du fichier en ".png"
target_png="${target%.*}".png

# si le fichier original n'est pas déjà un png
if [[ $target_png != $target ]]
then
	# alors on le convertit
    convert "$1" "$target_png"
    # et on ne supprime pas le fichier original
    #rm $target
    	# puis on prend le png comme nom de fichier final
    target="$target_png"
else
	# sinon, on copie simplement le fichier dans le dossier final
    cp $1 $target"_processed.png"
fi


# [warning - merge] on désactive l'identification des dimensions de l'image pour pouvoir la tourner dans l'orientation qu'on veut et la rotation
#W="$(identify -format '%w' $target)"
#H="$(identify -format '%h' $target)"
DITHERING=true
##SIZE=small # aleks was here
#
#if ([[ "$SIZE" == "big" ]] && [[ "$H" -gt "$W" ]]) || ([[ "$SIZE" == "small" ]] && [[ "$W" -gt "$H" ]])
#then
#    target_before_rotation="${target%.*}".before_rotate.png
#    mv "$target" "$target_before_rotation"
#    convert "$target_before_rotation" -rotate 90 "$target"
#fi


target_before_process="${target%.*}".before_dither.png
mv "$target" "$target_before_process"
if [[ "$DITHERING" == "true" ]]
then
    # From https://github.com/makew0rld/didder/releases
        #--contrast 0.1 \
    /home/pi/stickers.local/scripts/didder_1.3.0_linux_arm64 \
        --height 696 \
        --brightness 0.1 \
        --palette "black white" \
        --in "$target_before_process" \
        --out "$target" \
        edm --serpentine Stucki
else
    #convert "$target_before_process" -resize 696x "$target"
		cp "$target_before_process" "$target"
		fi
		rm -f $target_before_process
