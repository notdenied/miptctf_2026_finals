Источник: https://github.com/cR4-sh/autoforcad

# How to
> [!INFO]
> Автоматизация адаптирована под yandex cloud

**[Tech info](tech.pdf)**

Внутри terraform надо сделать `tofu init` или иным тф клиентом

А также предварительно настроить `yc` -- утилиту для работы с Я.Облаком: `yc init`.

Надо сделать архив с сервисами `services.tar` и положить в ansible диру, важно наличие внутри `start_all.sh`, примеры внутри диры имеются.
(сейчас скрипт `deploy.sh` сам соберёт архив с сервисами из `../services`)

Затем конфигурим в `./ansible/group_vars/all`: `team_count` и `players_count` - количество команд и конфигов на команду. 
`teams.yaml` также нужно заполнить.

`./ansible/roles/forcad-setup/templates/config.yml.j2`  настраиваем конфиг форкада для сервисов.
`./ansible/roles/forcad-setup/files/checkers` закидываем чекеры (сейчас `deploy.sh` тоже это делает)


архивы для игроков положатся в `./ansible/release`
## Start 
`bash deploy.sh`

деплой занимает 30-60 минут на 10 команд. Как только задеплоилось нам остается зайти на тачку с форкадом и сделать 
```bash
cd ~/ForcAD_v1.5.0-rc-1
python3 control.py start
python3 control.py print_tokens
```

У этой версии форкада есть свои плюсы и минусы -- возможно, вам больше подойдёт версия из репозитория форкада, ~~где что-то поправлено, а что-то отломано~~.

для большей надежности в композе надо бы накинуть больше max_connections на постгрю.
если нужно изменить `config.yml` (осторожно, это сотрёт весь прогрес в форкаде -- делать до начала CTF)

```bash
python3 control.py reset
python3 control.py setup
python3 control.py start
```


открыть/закрыть сеть  (на момент деплоя открыта) 
```
cd ansible
ansible-playbook close.yml
ansible-playbook open.yml
```
