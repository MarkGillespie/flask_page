drop table if exists sites;
create table sites (
	id integer primary key autoincrement,
	'title' text not null,
	'link' text not null,
	'text' text not null
);

drop table if exists notes;
create table notes (
	id integer primary key autoincrement,
	'title' text not null,
	'text' text not null	
);
