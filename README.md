<h1 align="center">Телеграм бот, с помощью которого можно получать заголовки актуальных новостей.</h1>
<h4>Для запуска программы нужно сделать следующие шаги:</h4>
<h5>1. В файле .env поменять переменную BOT_TOKEN на ваш токен<br>
2. Открыть консоль в папке приложения<br>
3. Ввести команду: docker build -t test_bot .<br>
4. Ввести команду: docker run -d test_bot<br>
6. Зайти в telegram и запустить бота командой /start</h5><br>

<h1 align="center">Реализация проекта:</h1>
<h5>1.В условии задачи стояло разработать простое web-приложение, было решено использовать Flask,
так как он быстрее всего справляется с подобными задачи без большого количества файлов<br>
2.Вторым шагом стала работа с API, была изученна документация и способы выполнения GET-запросов,
для получения информации с auud.io genious discogs<br>
3.Реализация, был написан отдельно код для каждой API, затем соединен в app.py 
Auud.io стал источником получения Исполнителя-Названия, так как способен обрабатывать 
mp3 файл, в genious discogs были загружены уже Исполнитель и Имя, затем мы получили
3 словаря с интересующими нас значениями, которые теперь используются в  html таблице, затем добавлен механизм загрузки файла в приложение.</h5>

<h3 align="center">Вы можете воспользоваться примерами музыки приложенными к приложению

 
