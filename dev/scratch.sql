# select json_object('a', '{"b": "abcd"}') as a;
# select CAST(JSON_UNQUOTE(JSON_EXTRACT(surveys, '$[0]')) as char) as test from crons
/*SELECT *
from crons c
JOIN surveys s ON JSON_CONTAINS(c.surveys, JSON_QUOTE(s.survey_uuid), '$')*/
# select JSON_CONTAINS(c.surveys, '43788fe207b143dc9eac4da38c036af6', '$') as matched
/*select c.*, s.*
FROM crons c
JOIN surveys s*/
# ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
/*SELECT c.*, surveys_table.surveys_json as surveys_j
FROM crons c,
     JSON_TABLE (c.surveys, '$' COLUMNS (
                 id FOR ORDINALITY,
                 surveys_json VARCHAR(32) PATH '$[0]')
     ) surveys_table;*/

/*SELECT
       *
   FROM crons c
   JOIN
       surveys s on IF((JSON_SEARCH(c.surveys, 'one', '$[*]') IS NOT null), JSON_EXTRACT(c.surveys, '$[1]'), FALSE) = s.survey_uuid;*/

# SELECT JSON_UNQUOTE(JSON_EXTRACT(surveys, '$')) FROM crons;

/*SELECT
       *
   FROM crons c
   JOIN surveys s on JSON_CONTAINS(CAST(c.surveys AS JSON), CAST(CONCAT('"', 'a0655674557e44148b8a2b57bd997183', '"') AS JSON))*/

/*SELECT JSON_CONTAINS(CAST(c.surveys AS JSON), CAST(CONCAT('"', s.survey_uuid, '"') AS JSON)) as res
FROM crons c
JOIN surveys s*/

SELECT *
FROM surveys s
         JOIN crons c
              ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
WHERE JSON_SEARCH(c.depts, 'all', 'sales') IS NOT NULL
  AND c.start_date < NOW()
  AND c.end_date > NOW()
ORDER BY s.id;

SELECT *
FROM surveys s
         JOIN crons c
              ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
WHERE JSON_SEARCH(c.depts, 'all', 'sales') IS NOT NULL
  AND c.start_date < NOW()
  AND c.end_date > NOW()
ORDER BY s.id


#####
SELECT c.id as cron_id, u.id as user_id, s.survey_uuid as suuid
                                FROM surveys s
                                         JOIN crons c
                                              ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
                                         JOIN users u
                                              ON (JSON_SEARCH(c.depts, 'all', u.dept) IS NOT NULL)
                                         LEFT JOIN answers a
                                                   ON s.survey_uuid = a.survey_uuid
                                         LEFT JOIN esurvey.survey_invites si
                                                   ON s.survey_uuid = si.survey_uuid
                                WHERE a.id IS NULL
                                  AND (si.user_id <> u.id OR si.id IS NULL)
                                  AND JSON_SEARCH(c.depts, 'all', 'sales') IS NOT NULL
                                  AND c.start_date < NOW()
                                  AND c.end_date > NOW()
                                GROUP BY s.id
                                ORDER BY s.id

###########


SELECT u.id as user_id, s.survey_uuid as s_sid, u.dept, a.id as ans_id, a.survey_uuid as ans_sid,
       a.id as a_id
FROM users u
         LEFT JOIN crons c
                   ON (JSON_SEARCH(c.depts, 'all', u.dept) IS NOT NULL)
         LEFT JOIN surveys s
                   ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
        LEFT JOIN answers a
                  ON (JSON_SEARCH(c.surveys, 'all', a.survey_uuid) IS NOT NULL)
#                     AND a.user_id = u.id
                    AND a.survey_uuid = s.survey_uuid
        LEFT JOIN survey_invites si ON (JSON_SEARCH(c.surveys, 'all', si.survey_uuid) IS NOT NULL)
                                            AND u.id = si.user_id
                                           and c.id = si.cron_id
WHERE c.start_date < NOW()
  AND c.end_date > NOW()
  AND a.id IS NULL
  AND si.id IS NULL
#     AND a.id
GROUP BY u.id, s.survey_uuid

##################################

create table survey_questions
(
	id int auto_increment,
	survey_id int not null,
	question json null,
	constraint survey_questions_pk
		primary key (id),
    CONSTRAINT `CONSTRAINT_3` CHECK (`question` is null or json_valid(`question`))
);
