CREATE DATABASE `crawl` CHARACTER SET utf8 COLLATE utf8_general_ci;
create user 'crawl'@'%' identified by 'crawl123';


create USER 'crawl'@'%' IDENTIFIED BY 'crawl123';

GRANT ALL ON `crawl`.* TO `crawl`@`%` IDENTIFIED BY 'crawl123';

grant all privileges on crawl.* to `crawl`@`%` identified by 'crawl123';



ALTER USER 'crawl'@'%' IDENTIFIED WITH mysql_native_password BY 'crawl123';

flush privileges;

参考文档:
https://www.jianshu.com/p/d7b9c468f20d