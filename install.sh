# Compile pbrt.
cd external/
mkdir -p pbrt_build
cd pbrt_build
cmake ../pbrt-v3
make -j4
cd ../../

# Log absolute path.
root_path=$(pwd)
printf "root_path = '%s'\n" "$root_path" > python/project_path.py