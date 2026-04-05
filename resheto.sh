#!/bin/bash

bash -c "cd miptctf_2026_finals && git pull"
ssh -i miptctf_finals_key ubuntu@forcad 'cp ~/ForcAD_v1.5.0-rc-1/checkers/resheto/checker.py ~/ForcAD_v1.5.0-rc-1/checkers/resheto/checker.py.bak'
scp -i miptctf_finals_key miptctf_2026_finals/checkers/resheto/checker.py ubuntu@forcad:~/ForcAD_v1.5.0-rc-1/checkers/resheto/checker.py
ssh -i miptctf_finals_key ubuntu@forcad 'md5sum ~/ForcAD_v1.5.0-rc-1/checkers/resheto/checker.py ~/ForcAD_v1.5.0-rc-1/checkers/resheto/checker.py.bak'
md5sum miptctf_2026_finals/checkers/resheto/checker.py
