CREATE DATABASE if not exists `esurvey`
    /*!40100 DEFAULT CHARACTER SET utf8mb4 */;


create table if not exists users
(
    id       int auto_increment
        primary key,
    username varchar(45) null,
    email    varchar(45) null
);

