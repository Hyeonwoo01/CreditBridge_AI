/** "샘플로 체험하기"에 쓰는 가상의 전적 대학 강의계획서 */
export interface SampleSyllabus {
  id: string;
  label: string;
  fileName: string;
  text: string;
}

export const SAMPLES: SampleSyllabus[] = [
  {
    id: 'calc',
    label: '해외 대학 · 미적분학',
    fileName: 'MATH101_Calculus_Syllabus.pdf',
    text: `Hanbit University
Department of Mathematics
MATH 101 Calculus I — Syllabus
Credits: 3
Instructor: Dr. J. Park

Course Description
This course introduces differential and integral calculus of functions of one variable. Topics include limits, continuity, derivatives, applications of the derivative, and the definite integral.

Learning Outcomes
- Evaluate limits algebraically and graphically, including one-sided limits and limits at infinity.
- Apply the product rule, quotient rule and chain rule to compute derivatives.
- Solve related rates and optimization problems.
- Use the Fundamental Theorem of Calculus to evaluate definite integrals.

Textbook
James Stewart, Calculus: Early Transcendentals, 9th edition

Prerequisites
Precalculus or placement exam

Weekly Schedule
Week 1: Functions and models, review of trigonometric functions
Week 2: The limit of a function, one-sided limits
Week 3: Continuity, intermediate value theorem, limits at infinity and asymptotes
Week 4: Derivatives and rates of change, the tangent line
Week 5: Differentiation rules: product rule and quotient rule
Week 6: The chain rule, implicit differentiation
Week 7: Midterm exam
Week 8: Related rates, linear approximation
Week 9: Maximum and minimum values, the mean value theorem
Week 10: Curve sketching and concavity, L'Hopital's rule
Week 11: Optimization problems, Newton's method
Week 12: Antiderivatives
Week 13: Riemann sums and the definite integral
Week 14: The fundamental theorem of calculus
Week 15: The substitution rule
Week 16: Final exam

Grading
Homework 20%
Quizzes 10%
Midterm 30%
Final exam 40%`,
  },
  {
    id: 'python',
    label: '커뮤니티 칼리지 · 파이썬',
    fileName: 'CS110_Intro_Programming.pdf',
    text: `Bayview Community College
CS 110 Introduction to Programming with Python
4 units

Course Overview
An introduction to computer programming using Python. Students learn to design, write and debug programs using variables, conditionals, loops, functions and basic data structures.

Student Learning Outcomes
1. Write Python programs that use variables, expressions and input/output.
2. Use conditional statements and loops to control program flow.
3. Decompose problems into functions with parameters and return values, including recursion.
4. Use lists, strings, dictionaries and files to store and process data.
5. Design simple classes using object-oriented programming.

Required Text
Think Python, 2nd edition, Allen Downey (free online)

Tentative Schedule
Week 1 - What is programming? Python setup, variables and data types
Week 2 - Expressions, operators, input and output
Week 3 - Boolean logic and if statements
Week 4 - While loops and for loops
Week 5 - Functions, parameters and return values
Week 6 - Scope and recursion
Week 7 - Strings and string methods
Week 8 - Lists and tuples
Week 9 - Dictionaries and sets
Week 10 - Reading and writing files, exceptions
Week 11 - Object-oriented programming: classes and objects
Week 12 - Higher-order functions and lambda
Week 13 - Final project

Grading
Labs 30%
Programming projects 30%
Midterm 15%
Final project 25%`,
  },
  {
    id: 'chem',
    label: '타주 칼리지 · 일반화학',
    fileName: 'CHEM101_General_Chemistry.txt',
    text: `Lakeshore College
CHEM 101 General Chemistry I
Credit Hours: 4 (3 lecture + 1 lab)

Course Description
Fundamental principles of chemistry including atomic structure, stoichiometry, chemical bonding, gases and thermochemistry, with an integrated laboratory.

Course Objectives
Students will be able to perform stoichiometric calculations using the mole concept, determine limiting reactants and percent yield.
Students will describe electron configuration and periodic trends.
Students will draw Lewis structures and predict molecular geometry using VSEPR theory.
Students will apply the ideal gas law and calculate enthalpy changes using Hess's law.

Textbook
Chemistry: The Central Science, Brown, LeMay, Bursten, 15th ed.

Course Outline
Week 1: Matter, measurement and significant figures
Week 2: Atoms, molecules and ions
Week 3: Chemical equations and stoichiometry, molar mass
Week 4: Limiting reactant and percent yield, empirical formula
Week 5: Reactions in aqueous solution
Week 6: Thermochemistry: enthalpy and calorimetry
Week 7: Exam 1
Week 8: Electronic structure of atoms, quantum numbers and orbitals
Week 9: Electron configuration and periodic trends
Week 10: Chemical bonding: ionic and covalent bonds, Lewis structures
Week 11: Molecular geometry, VSEPR and hybridization
Week 12: Gases: gas laws, ideal gas equation, kinetic molecular theory
Week 13: Intermolecular forces and liquids
Week 14: Review and final exam

Grading
Exams 45%
Laboratory 25%
Homework 15%
Final 15%`,
  },
  {
    id: 'econ',
    label: '해외 대학 · 경제원론',
    fileName: 'ECON100_Principles.pdf',
    text: `Hanbit University
ECON 100 Principles of Economics
3 credits

Course Description
An introduction to economic reasoning. The course covers how markets work through supply and demand, the behavior of consumers and firms, and an overview of national income and inflation.

Objectives
Explain how supply and demand determine market equilibrium and analyze elasticity.
Analyze consumer surplus, producer surplus and deadweight loss from a tax.
Compare perfect competition and monopoly.
Describe how GDP and inflation are measured.

Textbook
N. Gregory Mankiw, Principles of Economics, 9th ed.

Schedule
Week 1: Ten principles of economics, opportunity cost
Week 2: Supply and demand, market equilibrium
Week 3: Elasticity and its application
Week 4: Price ceiling and price floor
Week 5: Consumer surplus, producer surplus and market efficiency
Week 6: Application: the costs of taxation and deadweight loss
Week 7: Midterm
Week 8: Externalities and public goods
Week 9: Costs of production, marginal cost
Week 10: Firms in perfect competition
Week 11: Monopoly
Week 12: Measuring a nation's income: GDP
Week 13: Measuring the cost of living: consumer price index and inflation
Week 14: Final exam

Grading
Problem sets 25%
Midterm 35%
Final 40%`,
  },
];
