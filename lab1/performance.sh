outputfile="medium_13069"
inputfile="new_medium.pdf"
direction="-p"
 
echo "./tftp.py $direction $inputfile rabbit.it.uu.se" > "output_"$outputfile".txt"
echo "./tftp.py $direction $inputfile rabbit.it.uu.se" > "extended_output_"$outputfile".txt"
for i in {1..11}
do
        t=$((time ./tftp.py "$direction" "$inputfile" rabbit.it.uu.se) 2>&1)
 
        echo $t >> "extended_output_"$outputfile".txt"
 
        echo "Iteration "$i >> "output_"$outputfile".txt"
        echo $t | cut -d "&" -f 2 | cut -d " " -f 2,3,4 >> "output_"$outputfile".txt"
        echo $t | cut -d "&" -f 2 | cut -d " " -f 6 >> "output_"$outputfile".txt"
done