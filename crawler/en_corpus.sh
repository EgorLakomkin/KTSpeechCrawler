#!/bin/bash
trap "exit" INT

target_dir=$1
filter_dir=$2

declare -a arr=("and" "the" "on"  "in" "is" "to" "of" "a" "have" "it" "for" "not" "with" "as" "you" "do" "this" "but" "his" "by" "from" "they" "we" "say" "her" "she" "or" "an" "will"  "my"  "one"  "all" "would"  "there"  "their"  "what"  "up"  "if" "about"  "who"  "which"  "go"  "when" "make" "can" "like" "time"  "just" "him"  "take"  "people" "into" "good"  "some"  "could"  "them" "see" "other" "only"  "then" "come"  "its" "also" "over" "think" "also" "back" "after" "use" "two" "how" "our" "work" "first" "well" "way" "even" "new" "want" "because" "any" "these" "give" "day" "most" "us" "time" "person" "year" "get" "know" )
for i in `seq 1 30`;
do
    echo "PAGE="$i
    for kw in "${arr[@]}"
    do
        youtube-dl --download-archive ./en-downloaded.txt --no-overwrites -f 'bestaudio[ext=m4a]' --restrict-filenames --youtube-skip-dash-manifest --prefer-ffmpeg --socket-timeout 20  -iwc --write-info-json -k --write-srt --sub-format ttml --sub-lang en --convert-subs vtt  "https://www.youtube.com/results?sp=EgQIBCgB&q="$kw"&p="$i -o "$target_dir%(id)s%(title)s.%(ext)s" --exec "python ./crawler/process.py {} '$filter_dir'"
    done
done
