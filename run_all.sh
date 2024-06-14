gnome-terminal --working-directory=$(pwd)/Node1/ --wait -- python node.py 1 localhost 8501 &
gnome-terminal --working-directory=$(pwd)/Node2/ --wait -- python node.py 2 localhost 8502 &
gnome-terminal --working-directory=$(pwd)/Node3/ --wait -- python node.py 3 localhost 8503 &
gnome-terminal --working-directory=$(pwd)/Node4/ --wait -- python node.py 4 localhost 8504 &
gnome-terminal --working-directory=$(pwd)/Node5/ --wait -- python node.py 5 localhost 8505 &
gnome-terminal --working-directory=$(pwd)/client/ --wait -- python client.py localhost 8500 &

