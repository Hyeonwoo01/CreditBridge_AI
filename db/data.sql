-- CreditBridge AI 초기 데이터 (데모용 대상 대학·과목·기준 강의계획서·계정, 비밀번호 demo1234).
-- 자동 생성: sh scripts/export_db_sql.sh (scripts/seed_demo.py 결과를 pg_dump) — 직접 고치지 말 것. 운영 DB에는 넣지 않는다
--
-- PostgreSQL database dump
--

\restrict creditbridge

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: institutions; Type: TABLE DATA; Schema: public; Owner: -
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.institutions DISABLE TRIGGER ALL;

INSERT INTO public.institutions (name, country, is_target, tuition_per_credit, degree_credits, sis_token_hash, id, created_at) VALUES ('Midwest State University', 'US', true, 1350, 120, NULL, 1, '2026-10-19 07:04:37.909387');
INSERT INTO public.institutions (name, country, is_target, tuition_per_credit, degree_credits, sis_token_hash, id, created_at) VALUES ('Hankuk University (한국대학교)', 'KR', false, NULL, NULL, NULL, 2, '2026-10-19 07:04:37.909399');


ALTER TABLE public.institutions ENABLE TRIGGER ALL;

--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.departments DISABLE TRIGGER ALL;

INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'Mathematics', 1, '2026-10-19 07:04:37.964974');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'Physics', 2, '2026-10-19 07:04:37.998448');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'Chemistry', 3, '2026-10-19 07:04:38.005427');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'Computer Science and Engineering', 4, '2026-10-19 07:04:38.011524');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'English', 5, '2026-10-19 07:04:38.026619');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'History', 6, '2026-10-19 07:04:38.032093');
INSERT INTO public.departments (institution_id, name, id, created_at) VALUES (1, 'Retired', 7, '2026-10-19 07:04:39.092048');


ALTER TABLE public.departments ENABLE TRIGGER ALL;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.users DISABLE TRIGGER ALL;

INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('jiwon@student.example', '$argon2id$v=19$m=65536,t=3,p=4$Ep7Le3f1gHp5VTQvVyAFKA$Mk+fEQzYJMrEZup8p+WxpX9FPATC08J1Q1VeLdNucOM', '이지원', 'student', 1, NULL, NULL, NULL, false, 0, NULL, true, NULL, NULL, 1, '2026-10-19 07:04:38.103175');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('rachel@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$TyZ0XEfWgYVmpyTK2pwrMg$ttbMFdMeXKb1gCZTmtET6jsZwGG4Wg6t6AYGoKLeO6w', 'Rachel Morgan', 'evaluator', 1, NULL, NULL, NULL, false, 0, NULL, true, NULL, NULL, 2, '2026-10-19 07:04:38.175063');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('admin@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$Zwms+r8+zEbsmR3XFGSG2g$7WzMgaxwa3bxvTdTPlqzwloa3f99w3GvXWkQw0nTz5A', 'MSU Admin', 'admin', 1, NULL, NULL, NULL, false, 0, NULL, true, NULL, NULL, 3, '2026-10-19 07:04:38.255172');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('dkim@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$f0cgjzXRu81lubJebEHgeg$NizSpZOA3k1o0HK92R6SnQ7UQ9P5IurFt482jU224EU', 'Daniel Kim', 'professor', 1, 1, NULL, NULL, false, 0, NULL, true, NULL, NULL, 4, '2026-10-19 07:04:38.337418');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('lchen@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$tzjpPNr0OAU7dXPfDyFhnA$9PLArKZ00LWb76vlVq9A12E9EovUwuH8SQT14I/xEas', 'Laura Chen', 'professor', 1, 1, NULL, NULL, false, 0, NULL, true, NULL, NULL, 5, '2026-10-19 07:04:38.408155');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('oali@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$Byq+qC0FU6gvf3XNLpe1Vg$/eMfxqLLkuTR549odaWi6voIyAI+2CCFc7JDrzDvjC0', 'Omar Ali', 'professor', 1, 4, NULL, NULL, false, 0, NULL, true, NULL, NULL, 6, '2026-10-19 07:04:38.478906');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('spark@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$hhqU1SUysJ0OxM6WPUePcw$xkMDd1sk2/pInV+iv+EEcjyY20/j0A6UmkDNNXnFBU8', 'Sarah Park', 'professor', 1, 4, NULL, NULL, false, 0, NULL, true, NULL, NULL, 7, '2026-10-19 07:04:38.548671');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('mbrown@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$xswYHlY+IZEH2tgpX6cQ9A$YAjWj0yqjTcRFeQbyjTOIjDovzS8fGP0NK5HCkARRiM', 'Mike Brown', 'professor', 1, 2, NULL, NULL, false, 0, NULL, true, NULL, NULL, 8, '2026-10-19 07:04:38.625425');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('ewong@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$uI5yjJQMJKG1s3hhmpwmKQ$7R6jqDvDik6N/xnSlFZvltieQxaYFjglCW2O+ngrqBs', 'Emily Wong', 'professor', 1, 2, NULL, NULL, false, 0, NULL, true, NULL, NULL, 9, '2026-10-19 07:04:38.704138');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('alopez@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$+RVDaovr3jMjmLY+nb4QhQ$qRae1k04fcRwLQIInY61g3EVSrgpi8SlT2Hvd3hTDXA', 'Ana Lopez', 'professor', 1, 3, NULL, NULL, false, 0, NULL, true, NULL, NULL, 10, '2026-10-19 07:04:38.78144');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('jreed@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$vdi3QlAiLBJKMwYju0ap/w$ntGb2N+t1VTGsX480io/p8MhXE8F0wQc07AoQyBZMOI', 'Jane Reed', 'professor', 1, 5, NULL, NULL, false, 0, NULL, true, NULL, NULL, 11, '2026-10-19 07:04:38.864626');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('twhite@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$9b10pML8YI1NxXhZq+4V0Q$V2SU94wBb8BvLicgkNvgBR2DejlMdwqgNQEQyER90aw', 'Tom White', 'professor', 1, 6, NULL, NULL, false, 0, NULL, true, NULL, NULL, 12, '2026-10-19 07:04:38.943784');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('senior@student.example', '$argon2id$v=19$m=65536,t=3,p=4$8DYSgztk/YFMj4GiIc4Vuw$iFQkhi2PLCrUllQQokkloXJyRldoH6tKiLIximda7Jk', '선배 학생', 'student', 1, NULL, NULL, NULL, false, 0, NULL, true, NULL, NULL, 13, '2026-10-19 07:04:39.012191');
INSERT INTO public.users (email, password_hash, name, role, institution_id, department_id, delegate_user_id, away_until, must_change_password, failed_logins, locked_until, is_active, deactivated_at, locale, id, created_at) VALUES ('retired@msu.example', '$argon2id$v=19$m=65536,t=3,p=4$J3IuQLAUvNp4Yp3dBuJVNw$YuejcVNvbH53dhGuf3P6MCiMfVrj6gM7ecuu9+PFUlM', 'Prof. Emeritus Hall', 'professor', 1, 7, NULL, NULL, false, 0, NULL, true, NULL, NULL, 14, '2026-10-19 07:04:39.093404');


ALTER TABLE public.users ENABLE TRIGGER ALL;

--
-- Data for Name: transfer_requests; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.transfer_requests DISABLE TRIGGER ALL;

INSERT INTO public.transfer_requests (student_id, source_institution_id, target_institution_id, major, status, submitted_at, transcript_file_key, transcript_masked_name, id, created_at) VALUES (13, 2, 1, 'Computer Science and Engineering', 'decided', '2025-10-19 07:04:39.094406', NULL, NULL, 1, '2026-10-19 07:04:39.095748');


ALTER TABLE public.transfer_requests ENABLE TRIGGER ALL;

--
-- Data for Name: syllabi; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.syllabi DISABLE TRIGGER ALL;

INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '7e09efae769294f6a3fc52fa2279354f7fa77bdb38a68356507999b712e8a1dd', 'MATH 1151.txt', 'en', 'Midwest State University
MATH 1151 Calculus I
Credits: 4

Course Description
Differential and integral calculus of one variable.

Weekly Schedule
Week 1: Limits, one-sided limits, limits at infinity and continuity; the Intermediate Value Theorem.
Week 2: The derivative as a limit and as a rate of change; the derivative as a function.
Week 3: Product rule, quotient rule, chain rule and derivatives of trigonometric, exponential and logarithmic functions.
Week 4: Implicit differentiation, related rates and linear approximation.
Week 5: Extreme values, the Mean Value Theorem, curve sketching and L''Hopital''s rule.
Week 6: Applied optimization problems.
Week 7: Antiderivatives, Riemann sums and the definite integral.
Week 8: The Fundamental Theorem of Calculus and integration by substitution.', NULL, 'MATH 1151', 'Calculus I', 4.0, NULL, NULL, NULL, NULL, 'ready', NULL, 1, '2026-10-19 07:04:37.912667');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '18841059c1ced70c079733ba222a370cf789594cc394cb48d88325ba3c47d0a4', 'MATH 1172.txt', 'en', 'Midwest State University
MATH 1172 Calculus II
Credits: 4

Course Description
Techniques and applications of integration, sequences and series.

Weekly Schedule
Week 1: Integration by parts, trigonometric substitution and partial fractions.
Week 2: Improper integrals and numerical integration.
Week 3: Volumes of revolution, arc length and work.
Week 4: Sequences, infinite series and convergence tests.
Week 5: Power series, Taylor and Maclaurin series.
Week 6: Parametric equations and polar coordinates.', NULL, 'MATH 1172', 'Calculus II', 4.0, NULL, NULL, NULL, NULL, 'ready', NULL, 2, '2026-10-19 07:04:37.970563');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '9fdc7427db8b44682c934f7cb13930d1ab357da24f06df6d7d4eeb4949d1aadd', 'MATH 2568.txt', 'en', 'Midwest State University
MATH 2568 Linear Algebra
Credits: 3

Course Description
Matrices, vector spaces, linear transformations and eigenvalues.

Weekly Schedule
Week 1: Systems of linear equations, Gaussian elimination, row reduction and echelon forms.
Week 2: Matrix operations, matrix inverses and elementary matrices.
Week 3: Determinants and their properties.
Week 4: Vector spaces, subspaces, null space and column space.
Week 5: Linear independence, basis, dimension and rank.
Week 6: Linear transformations and their matrices.
Week 7: Eigenvalues, eigenvectors and the characteristic equation.
Week 8: Diagonalization of matrices.
Week 9: Inner products, orthogonal projections, the Gram-Schmidt process and least squares.', NULL, 'MATH 2568', 'Linear Algebra', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 3, '2026-10-19 07:04:37.978624');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, 'dbacad3b13cf2c6c5dc0dd7f0c3a5aa927e0dccc2ce2eae5f9c895f829d9806f', 'MATH 1050.txt', 'en', 'Midwest State University
MATH 1050 College Algebra
Credits: 3

Course Description
Functions, polynomials, exponential and logarithmic functions.

Weekly Schedule
Week 1: Functions, domain and range, graphs and transformations.
Week 2: Polynomial and rational functions and their zeros.
Week 3: Exponential and logarithmic functions and equations.
Week 4: Systems of linear equations and inequalities.', NULL, 'MATH 1050', 'College Algebra', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 4, '2026-10-19 07:04:37.985387');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, 'a9b02b8ca02b267bdac04c9b11641ce2231f54cbcb910d1f2722d3fbb9c8074b', 'PHYSICS 1250.txt', 'en', 'Midwest State University
PHYSICS 1250 Mechanics, Work and Energy
Credits: 4

Course Description
Calculus-based introductory mechanics.

Weekly Schedule
Week 1: Kinematics in one and two dimensions, vectors and projectile motion.
Week 2: Newton''s laws of motion, free-body diagrams, friction and circular motion.
Week 3: Work, kinetic energy, potential energy and conservation of energy.
Week 4: Linear momentum, impulse and collisions.
Week 5: Rotation, torque, moment of inertia and angular momentum.
Week 6: Simple harmonic motion and universal gravitation.', NULL, 'PHYSICS 1250', 'Mechanics, Work and Energy', 4.0, NULL, NULL, NULL, NULL, 'ready', NULL, 5, '2026-10-19 07:04:37.993686');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, 'a02ef47e6ec3facfe569197edaf6bb3c8d9534f435827719c83189a3e9f8d8e7', 'CHEM 1210.txt', 'en', 'Midwest State University
CHEM 1210 General Chemistry I
Credits: 4

Course Description
Principles of chemistry with laboratory.

Weekly Schedule
Week 1: The mole, chemical equations and stoichiometry.
Week 2: Reactions in aqueous solution.
Week 3: Thermochemistry: enthalpy, calorimetry and Hess''s law.
Week 4: Electronic structure of atoms and periodic trends.
Week 5: Ionic and covalent bonding, Lewis structures, VSEPR and molecular geometry.
Week 6: Gas laws and the ideal gas equation.
Week 7: Weekly laboratory experiments in measurement, synthesis and titration.', NULL, 'CHEM 1210', 'General Chemistry I', 4.0, NULL, NULL, NULL, NULL, 'ready', NULL, 6, '2026-10-19 07:04:38.000103');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '3dd1a86aa215c4d4157f8bfb2cbbf809985ac7a52a2ca8ce080fda48618084f8', 'CSE 1222.txt', 'en', 'Midwest State University
CSE 1222 Introduction to Programming in C
Credits: 3

Course Description
Programming in C.

Weekly Schedule
Week 1: Variables, data types, operators and expressions in C.
Week 2: Conditional statements and loops.
Week 3: Functions, parameters and scope.
Week 4: Arrays and strings.
Week 5: Pointers, pointer arithmetic and dynamic memory allocation.
Week 6: Structures and file input and output.', NULL, 'CSE 1222', 'Introduction to Programming in C', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 7, '2026-10-19 07:04:38.00751');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '8d0e3a49d3221c8afeb28eca383c8dbd9a9254904191846591965387c2a444d8', 'CSE 2231.txt', 'en', 'Midwest State University
CSE 2231 Software II: Data Structures
Credits: 3

Course Description
Data structures and algorithm analysis.

Weekly Schedule
Week 1: Asymptotic analysis and Big-O notation.
Week 2: Linked lists, stacks and queues.
Week 3: Binary trees, binary search trees and balanced trees.
Week 4: Heaps and priority queues.
Week 5: Hash tables and hashing.
Week 6: Sorting algorithms including merge sort and quick sort.
Week 7: Graph representation and traversal.', NULL, 'CSE 2231', 'Software II: Data Structures', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 8, '2026-10-19 07:04:38.013087');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, 'b6833dafcec7e976e61878f6138879f3359ada386d02186cb0addce1ece79629', 'CSE 2321.txt', 'en', 'Midwest State University
CSE 2321 Foundations I: Discrete Structures
Credits: 3

Course Description
Discrete mathematics for computer science.

Weekly Schedule
Week 1: Propositional and predicate logic and proof techniques.
Week 2: Mathematical induction and recursion.
Week 3: Sets, functions and relations.
Week 4: Permutations, combinations and the pigeonhole principle.
Week 5: Graph theory and trees.', NULL, 'CSE 2321', 'Foundations I: Discrete Structures', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 9, '2026-10-19 07:04:38.018475');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '832ec74b0554aef6188f9e9e8ac0fac980a5f6350d21f330167860361e2b1b6f', 'ENGLISH 1110.txt', 'en', 'Midwest State University
ENGLISH 1110 First-Year English Composition
Credits: 3

Course Description
Academic writing and argument.

Weekly Schedule
Week 1: Rhetorical analysis of texts for audience and purpose.
Week 2: Composing thesis-driven arguments.
Week 3: Research writing with sources and citation.
Week 4: Drafting, peer review and revision.', NULL, 'ENGLISH 1110', 'First-Year English Composition', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 10, '2026-10-19 07:04:38.023228');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (1, NULL, NULL, NULL, '19c181410dd664bbfbdb498d96c1ab053c27f0f245b27941580e0dd9b3a9a3b9', 'HISTORY 1151.txt', 'en', 'Midwest State University
HISTORY 1151 American Civilization to 1877
Credits: 3

Course Description
Survey of American history to 1877.

Weekly Schedule
Week 1: Colonial societies in North America.
Week 2: The American Revolution and the Constitution.
Week 3: Expansion, slavery and the antebellum era.
Week 4: The Civil War and Reconstruction.', NULL, 'HISTORY 1151', 'American Civilization to 1877', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 11, '2026-10-19 07:04:38.028467');
INSERT INTO public.syllabi (institution_id, transfer_request_id, owner_id, source_file_key, content_hash, original_filename, language, raw_text, page_offsets, course_code, course_title, credits, extracted_json, extraction_model, quality_score, injection_flags, status, error_message, id, created_at) VALUES (2, 1, 13, NULL, '4b50b3c6aa26a1836afa35d3e40e456438d0b0e39c2e61fd606f95984b9a06f3', 'MATH201.pdf', 'en', 'Hankuk University
MATH 201 Linear Algebra
Credits: 3

Course Description
Systems of linear equations, matrices, determinants, vector spaces, linear transformations, eigenvalues and eigenvectors, and orthogonality.

Learning Outcomes
1. Solve systems of linear equations by Gaussian elimination and row reduction.
2. Compute matrix inverses and determinants.
3. Determine bases and dimension of vector spaces and subspaces.
4. Compute eigenvalues and eigenvectors and diagonalize matrices.
5. Apply the Gram-Schmidt process and least squares.

Textbook
David C. Lay, Linear Algebra and Its Applications, 6th edition

Weekly Schedule
Week 1: Systems of linear equations, row reduction and echelon forms
Week 2: Vector equations, the matrix equation Ax = b, solution sets
Week 3: Linear independence, introduction to linear transformations
Week 4: Matrix operations, the inverse of a matrix
Week 5: Determinants and their properties, Cramer''s rule
Week 6: Vector spaces and subspaces, null space and column space
Week 7: Bases, dimension and rank
Week 8: Midterm exam
Week 9: Eigenvalues and eigenvectors, the characteristic equation
Week 10: Diagonalization
Week 11: Inner product, orthogonal sets and orthogonal projections
Week 12: The Gram-Schmidt process, least squares problems
Week 13: Symmetric matrices
Week 14: Review
Week 15: Final exam

Assessment
Homework 25%, Midterm 35%, Final exam 40%
', NULL, 'MATH 201', 'Linear Algebra', 3.0, NULL, NULL, NULL, NULL, 'ready', NULL, 12, '2025-10-19 07:04:39.094406');


ALTER TABLE public.syllabi ENABLE TRIGGER ALL;

--
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.courses DISABLE TRIGGER ALL;

INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'MATH 1151', 'Calculus I', 4.0, 1, 'First-semester calculus for science and engineering majors (not business or applied calculus).', 1, NULL, 1, '2026-10-19 07:04:37.967124');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'MATH 1172', 'Calculus II', 4.0, 1, 'Second-semester calculus for science and engineering majors.', 2, NULL, 2, '2026-10-19 07:04:37.977607');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'MATH 2568', 'Linear Algebra', 3.0, 1, 'Sophomore-level linear algebra for majors.', 3, NULL, 3, '2026-10-19 07:04:37.984573');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'MATH 1050', 'College Algebra', 3.0, 1, 'Pre-calculus level course; not equivalent to calculus.', 4, NULL, 4, '2026-10-19 07:04:37.992589');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'PHYSICS 1250', 'Mechanics, Work and Energy', 4.0, 2, 'Calculus-based mechanics for science and engineering majors.', 5, NULL, 5, '2026-10-19 07:04:37.999384');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'CHEM 1210', 'General Chemistry I', 4.0, 3, 'First semester of general chemistry for science majors, with laboratory.', 6, NULL, 6, '2026-10-19 07:04:38.006576');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'CSE 1222', 'Introduction to Programming in C', 3.0, 4, 'First programming course for engineering majors.', 7, NULL, 7, '2026-10-19 07:04:38.012399');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'CSE 2231', 'Software II: Data Structures', 3.0, 4, 'Second programming course on data structures; requires CS1.', 8, NULL, 8, '2026-10-19 07:04:38.017631');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'CSE 2321', 'Foundations I: Discrete Structures', 3.0, 4, 'Discrete mathematics for CSE majors, proof-based.', 9, NULL, 9, '2026-10-19 07:04:38.022611');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'ENGLISH 1110', 'First-Year English Composition', 3.0, 5, 'First-year college writing.', 10, NULL, 10, '2026-10-19 07:04:38.027786');
INSERT INTO public.courses (institution_id, code, title, credits, department_id, level, reference_syllabus_id, concepts, id, created_at) VALUES (1, 'HISTORY 1151', 'American Civilization to 1877', 3.0, 6, 'Introductory survey of United States history.', 11, NULL, 11, '2026-10-19 07:04:38.033124');


ALTER TABLE public.courses ENABLE TRIGGER ALL;

--
-- Data for Name: course_evaluations; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.course_evaluations DISABLE TRIGGER ALL;

INSERT INTO public.course_evaluations (transfer_request_id, syllabus_id, candidate_course_id, status, recommendation, coverage, confidence, level_flag, coverage_json, summary, input_hash, prompt_version, model, error_message, is_latest, id, created_at) VALUES (1, 12, 3, 'done', 'direct', 0.900, 'high', NULL, NULL, '', NULL, NULL, NULL, NULL, true, 1, '2025-10-19 07:04:39.094406');


ALTER TABLE public.course_evaluations ENABLE TRIGGER ALL;

--
-- Data for Name: decisions; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.decisions DISABLE TRIGGER ALL;

INSERT INTO public.decisions (course_evaluation_id, decided_by, action, result, target_course_id, reason_codes, reason_memo, ai_recommendation_snapshot, conflict_acknowledged, appeal_id, decided_at, id) VALUES (1, 14, 'approve', 'direct', 3, '[]', '', '{"recommendation": "direct"}', false, NULL, '2025-10-19 07:04:39.094406', 1);


ALTER TABLE public.decisions ENABLE TRIGGER ALL;

--
-- Data for Name: appeals; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.appeals DISABLE TRIGGER ALL;



ALTER TABLE public.appeals ENABLE TRIGGER ALL;

--
-- Data for Name: appeal_files; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.appeal_files DISABLE TRIGGER ALL;



ALTER TABLE public.appeal_files ENABLE TRIGGER ALL;

--
-- Data for Name: assignments; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.assignments DISABLE TRIGGER ALL;



ALTER TABLE public.assignments ENABLE TRIGGER ALL;

--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs DISABLE TRIGGER ALL;



ALTER TABLE public.audit_logs ENABLE TRIGGER ALL;

--
-- Data for Name: equivalencies; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.equivalencies DISABLE TRIGGER ALL;



ALTER TABLE public.equivalencies ENABLE TRIGGER ALL;

--
-- Data for Name: evaluation_notes; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.evaluation_notes DISABLE TRIGGER ALL;



ALTER TABLE public.evaluation_notes ENABLE TRIGGER ALL;

--
-- Data for Name: evidence_spans; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.evidence_spans DISABLE TRIGGER ALL;



ALTER TABLE public.evidence_spans ENABLE TRIGGER ALL;

--
-- Data for Name: material_requests; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.material_requests DISABLE TRIGGER ALL;



ALTER TABLE public.material_requests ENABLE TRIGGER ALL;

--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.notifications DISABLE TRIGGER ALL;



ALTER TABLE public.notifications ENABLE TRIGGER ALL;

--
-- Data for Name: privacy_requests; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.privacy_requests DISABLE TRIGGER ALL;



ALTER TABLE public.privacy_requests ENABLE TRIGGER ALL;

--
-- Data for Name: push_subscriptions; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.push_subscriptions DISABLE TRIGGER ALL;



ALTER TABLE public.push_subscriptions ENABLE TRIGGER ALL;

--
-- Data for Name: supplement_files; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.supplement_files DISABLE TRIGGER ALL;



ALTER TABLE public.supplement_files ENABLE TRIGGER ALL;

--
-- Data for Name: syllabus_chunks; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.syllabus_chunks DISABLE TRIGGER ALL;

INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 1, 'Limits and continuity', 'Limits, one-sided limits, limits at infinity and continuity; the Intermediate Value Theorem.', 154, 245, 1);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 2, 'Definition of the derivative', 'The derivative as a limit and as a rate of change; the derivative as a function.', 255, 334, 2);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 3, 'Differentiation rules', 'Product rule, quotient rule, chain rule and derivatives of trigonometric, exponential and logarithmic functions.', 344, 455, 3);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 4, 'Implicit differentiation and related rates', 'Implicit differentiation, related rates and linear approximation.', 465, 529, 4);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 5, 'Applications of the derivative', 'Extreme values, the Mean Value Theorem, curve sketching and L''Hopital''s rule.', 539, 615, 5);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 6, 'Optimization', 'Applied optimization problems.', 625, 654, 6);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 7, 'Definite integral', 'Antiderivatives, Riemann sums and the definite integral.', 664, 719, 7);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (1, 8, 'Fundamental Theorem of Calculus', 'The Fundamental Theorem of Calculus and integration by substitution.', 729, 796, 8);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 1, 'Integration techniques', 'Integration by parts, trigonometric substitution and partial fractions.', 169, 239, 9);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 2, 'Improper integrals', 'Improper integrals and numerical integration.', 249, 293, 10);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 3, 'Applications of integration', 'Volumes of revolution, arc length and work.', 303, 345, 11);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 4, 'Sequences and series', 'Sequences, infinite series and convergence tests.', 355, 403, 12);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 5, 'Power and Taylor series', 'Power series, Taylor and Maclaurin series.', 413, 454, 13);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (2, 6, 'Parametric and polar curves', 'Parametric equations and polar coordinates.', 464, 506, 14);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 1, 'Linear systems and row reduction', 'Systems of linear equations, Gaussian elimination, row reduction and echelon forms.', 171, 253, 15);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 2, 'Matrix algebra and inverses', 'Matrix operations, matrix inverses and elementary matrices.', 263, 321, 16);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 3, 'Determinants', 'Determinants and their properties.', 331, 364, 17);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 4, 'Vector spaces and subspaces', 'Vector spaces, subspaces, null space and column space.', 374, 427, 18);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 5, 'Basis and dimension', 'Linear independence, basis, dimension and rank.', 437, 483, 19);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 6, 'Linear transformations', 'Linear transformations and their matrices.', 493, 534, 20);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 7, 'Eigenvalues and eigenvectors', 'Eigenvalues, eigenvectors and the characteristic equation.', 544, 601, 21);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 8, 'Diagonalization', 'Diagonalization of matrices.', 611, 638, 22);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (3, 9, 'Orthogonality and least squares', 'Inner products, orthogonal projections, the Gram-Schmidt process and least squares.', 648, 730, 23);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (4, 1, 'Functions and graphs', 'Functions, domain and range, graphs and transformations.', 170, 225, 24);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (4, 2, 'Polynomial and rational functions', 'Polynomial and rational functions and their zeros.', 235, 284, 25);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (4, 3, 'Exponential and logarithmic functions', 'Exponential and logarithmic functions and equations.', 294, 345, 26);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (4, 4, 'Systems of equations', 'Systems of linear equations and inequalities.', 355, 399, 27);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 1, 'Kinematics', 'Kinematics in one and two dimensions, vectors and projectile motion.', 160, 227, 28);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 2, 'Newton''s laws', 'Newton''s laws of motion, free-body diagrams, friction and circular motion.', 237, 310, 29);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 3, 'Work and energy', 'Work, kinetic energy, potential energy and conservation of energy.', 320, 385, 30);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 4, 'Momentum and collisions', 'Linear momentum, impulse and collisions.', 395, 434, 31);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 5, 'Rotational dynamics', 'Rotation, torque, moment of inertia and angular momentum.', 444, 500, 32);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (5, 6, 'Oscillations and gravitation', 'Simple harmonic motion and universal gravitation.', 510, 558, 33);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 1, 'Stoichiometry', 'The mole, chemical equations and stoichiometry.', 152, 198, 34);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 2, 'Aqueous reactions', 'Reactions in aqueous solution.', 208, 237, 35);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 3, 'Thermochemistry', 'Thermochemistry: enthalpy, calorimetry and Hess''s law.', 247, 300, 36);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 4, 'Atomic structure and periodicity', 'Electronic structure of atoms and periodic trends.', 310, 359, 37);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 5, 'Chemical bonding and molecular geometry', 'Ionic and covalent bonding, Lewis structures, VSEPR and molecular geometry.', 369, 443, 38);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 6, 'Gases', 'Gas laws and the ideal gas equation.', 453, 488, 39);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (6, 7, 'Laboratory techniques', 'Weekly laboratory experiments in measurement, synthesis and titration.', 498, 567, 40);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 1, 'C syntax, types and operators', 'Variables, data types, operators and expressions in C.', 141, 194, 41);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 2, 'Control flow', 'Conditional statements and loops.', 204, 236, 42);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 3, 'Functions', 'Functions, parameters and scope.', 246, 277, 43);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 4, 'Arrays and strings', 'Arrays and strings.', 287, 305, 44);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 5, 'Pointers and dynamic memory', 'Pointers, pointer arithmetic and dynamic memory allocation.', 315, 373, 45);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (7, 6, 'Structures and file I/O', 'Structures and file input and output.', 383, 419, 46);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 1, 'Algorithm analysis', 'Asymptotic analysis and Big-O notation.', 159, 197, 47);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 2, 'Linked lists, stacks and queues', 'Linked lists, stacks and queues.', 207, 238, 48);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 3, 'Trees and binary search trees', 'Binary trees, binary search trees and balanced trees.', 248, 300, 49);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 4, 'Heaps and priority queues', 'Heaps and priority queues.', 310, 335, 50);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 5, 'Hashing', 'Hash tables and hashing.', 345, 368, 51);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 6, 'Sorting algorithms', 'Sorting algorithms including merge sort and quick sort.', 378, 432, 52);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (8, 7, 'Graphs', 'Graph representation and traversal.', 442, 476, 53);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (9, 1, 'Logic and proofs', 'Propositional and predicate logic and proof techniques.', 168, 222, 54);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (9, 2, 'Induction', 'Mathematical induction and recursion.', 232, 268, 55);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (9, 3, 'Sets, functions and relations', 'Sets, functions and relations.', 278, 307, 56);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (9, 4, 'Counting', 'Permutations, combinations and the pigeonhole principle.', 317, 372, 57);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (9, 5, 'Graphs and trees', 'Graph theory and trees.', 382, 404, 58);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (10, 1, 'Rhetorical analysis', 'Rhetorical analysis of texts for audience and purpose.', 156, 209, 59);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (10, 2, 'Argument', 'Composing thesis-driven arguments.', 219, 252, 60);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (10, 3, 'Research and citation', 'Research writing with sources and citation.', 262, 304, 61);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (10, 4, 'Revision', 'Drafting, peer review and revision.', 314, 348, 62);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (11, 1, 'Colonial America', 'Colonial societies in North America.', 160, 195, 63);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (11, 2, 'Revolution and Constitution', 'The American Revolution and the Constitution.', 205, 249, 64);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (11, 3, 'Antebellum era', 'Expansion, slavery and the antebellum era.', 259, 300, 65);
INSERT INTO public.syllabus_chunks (syllabus_id, week_no, concept, text, char_start, char_end, id) VALUES (11, 4, 'Civil War and Reconstruction', 'The Civil War and Reconstruction.', 310, 342, 66);


ALTER TABLE public.syllabus_chunks ENABLE TRIGGER ALL;

--
-- Data for Name: transcript_entries; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.transcript_entries DISABLE TRIGGER ALL;



ALTER TABLE public.transcript_entries ENABLE TRIGGER ALL;

--
-- Name: appeal_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.appeal_files_id_seq', 1, false);


--
-- Name: appeals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.appeals_id_seq', 1, false);


--
-- Name: assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.assignments_id_seq', 1, false);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 1, false);


--
-- Name: course_evaluations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.course_evaluations_id_seq', 1, true);


--
-- Name: courses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.courses_id_seq', 11, true);


--
-- Name: decisions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.decisions_id_seq', 1, true);


--
-- Name: departments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.departments_id_seq', 7, true);


--
-- Name: equivalencies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.equivalencies_id_seq', 1, false);


--
-- Name: evaluation_notes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.evaluation_notes_id_seq', 1, false);


--
-- Name: evidence_spans_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.evidence_spans_id_seq', 1, false);


--
-- Name: institutions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.institutions_id_seq', 2, true);


--
-- Name: material_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.material_requests_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: privacy_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.privacy_requests_id_seq', 1, false);


--
-- Name: push_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.push_subscriptions_id_seq', 1, false);


--
-- Name: supplement_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.supplement_files_id_seq', 1, false);


--
-- Name: syllabi_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.syllabi_id_seq', 12, true);


--
-- Name: syllabus_chunks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.syllabus_chunks_id_seq', 66, true);


--
-- Name: transcript_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.transcript_entries_id_seq', 1, false);


--
-- Name: transfer_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.transfer_requests_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 14, true);


--
-- PostgreSQL database dump complete
--

\unrestrict creditbridge

