-- Remove Tiếng Anh tăng cường 1 (7010610) from active curriculum pool.
-- Cannot DELETE from courses due to FK from user_grades — mark as non-counting instead.
-- course_elective_groups had no record for 7010610 (confirmed).

DELETE FROM course_elective_groups WHERE course_code = '7010610';

UPDATE courses SET count_toward_credits = FALSE WHERE course_code = '7010610';
