#!/usr/bin/env bash

printf "build.sh reporting for duty!\n"
#pip install --upgrade pip
#pip install poetry
#poetry install
#pip install dephell
#poetry build
#tar -xvf $1 --wildcards --no-anchored '*/setup.py' --strip=1
#poetry build
#tar -xvf $1 --wildcards --no-anchored '*/setup.py' --strip=1
#dephell deps convert

# if [[ "$(which direnv)" && (-f '.envrc' || -f '.env') ]]; then
#   printf "Detected direnv. Allowing...\n"
#   direnv allow
# fi

if [ "$IN_PRODUCTION" == "0" ]; then
  printf "Detected dev environment; running live build...\n"
  poetry update
  dephell deps convert --from=pyproject.toml --to-path requirements.txt --to-format pip
  dephell deps convert --from=pyproject.toml --to-path setup.py
  sass --style compressed --update static/urora/scss
  cd static/js || exit
  npm i --update
else
  printf "Detected production environment; running dev build...\n"
  #cd ~ || exit;
  #mkdir api;
  #cd api || exit;
  #git clone https://github.com/TensorTom/collections-json.git;
  #cd static/js
  #npm i
fi

#if [ "$THIS_IS_MODULE" == "0" ]; then
#  tar -xvf $1 --wildcards --no-anchored '*/setup.py' --strip=1
#  poetry build
#  tar -xvf $1 --wildcards --no-anchored '*/setup.py' --strip=1
#fi
