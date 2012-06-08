DROP TABLE IF EXISTS rh_user CASCADE;
DROP TABLE IF EXISTS rh_review CASCADE;
DROP TABLE IF EXISTS cot_session CASCADE;

CREATE TABLE rh_user (
	name TEXT UNIQUE NOT NULL PRIMARY KEY,
	password CHAR(40) NOT NULL,
	email TEXT UNIQUE NOT NULL
);
CREATE TABLE rh_review (
	id SERIAL NOT NULL PRIMARY KEY,
	writer TEXT NOT NULL REFERENCES rh_user(name) ON UPDATE CASCADE,
	writer_ip INET NOT NULL DEFAULT '0.0.0.0',
	happy BOOLEAN NOT NULL,
	lon FLOAT NOT NULL,
	lat FLOAT NOT NULL,
	date_posted TIMESTAMP NOT NULL DEFAULT now(),
	content TEXT NOT NULL
);
CREATE TABLE cot_session (
	session_id CHAR(128) UNIQUE NOT NULL,
	atime TIMESTAMP NOT NULL DEFAULT current_timestamp,
	data TEXT
);

CREATE UNIQUE INDEX rh_user__name__lower ON rh_user(lower(name));
CREATE UNIQUE INDEX rh_user__email__lower ON rh_user(lower(email));

INSERT INTO rh_user(name, password, email) VALUES('Anonymous', '', '');
INSERT INTO rh_user(name, password, email) VALUES('Shish', '6f90969f138be3c75101028711871a27972d1fe8', 'webmaster@shishnet.org');
