create database if not exists pylcx
  default character set = utf8
  default collate = utf8_unicode_ci;

use pylcx;

drop table if exists user;
create table user
(
  id       int unsigned not null auto_increment,
  username varchar(256) not null,
  salt     varchar(256) not null,
  secret   varchar(256) not null, -- secret = md5(password + salt)
  quota    float        not null, -- MB
  is_admin boolean default false,
  primary key (id)
);

drop table if exists detail;
create table detail
(
  id          int unsigned not null auto_increment,
  user_id     int unsigned not null,
  host        int unsigned not null,
  bind_port   int unsigned not null,
  login_time  datetime     not null,
  logout_time datetime     not null,
  upload      float        not null, -- MB
  download    float        not null, -- MB
  foreign key (user_id) references user (id) on DELETE cascade,
  primary key (id)
)