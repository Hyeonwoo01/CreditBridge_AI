"""Midwest State University(가칭) 모의 카탈로그. 각 과목의 기준 강의계획서는 개념 목록으로 만든다.

개념 이름은 대상 과목의 '필수 개념'이고, 주차 문장은 기준 강의계획서 원문이 된다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCourse:
    code: str
    title: str
    credits: float
    department: str
    level: str
    description: str
    concepts: list[tuple[str, str]]  # (개념 이름, 기준 강의계획서 주차 문장)


MSU_COURSES = [
    CatalogCourse(
        "MATH 1151",
        "Calculus I",
        4,
        "Mathematics",
        "First-semester calculus for science and engineering majors (not business or applied calculus).",
        "Differential and integral calculus of one variable.",
        [
            (
                "Limits and continuity",
                "Limits, one-sided limits, limits at infinity and continuity; the Intermediate Value Theorem.",
            ),
            (
                "Definition of the derivative",
                "The derivative as a limit and as a rate of change; the derivative as a function.",
            ),
            (
                "Differentiation rules",
                "Product rule, quotient rule, chain rule and derivatives of trigonometric, exponential and "
                "logarithmic functions.",
            ),
            (
                "Implicit differentiation and related rates",
                "Implicit differentiation, related rates and linear approximation.",
            ),
            (
                "Applications of the derivative",
                "Extreme values, the Mean Value Theorem, curve sketching and L'Hopital's rule.",
            ),
            ("Optimization", "Applied optimization problems."),
            ("Definite integral", "Antiderivatives, Riemann sums and the definite integral."),
            ("Fundamental Theorem of Calculus", "The Fundamental Theorem of Calculus and integration by substitution."),
        ],
    ),
    CatalogCourse(
        "MATH 1172",
        "Calculus II",
        4,
        "Mathematics",
        "Second-semester calculus for science and engineering majors.",
        "Techniques and applications of integration, sequences and series.",
        [
            ("Integration techniques", "Integration by parts, trigonometric substitution and partial fractions."),
            ("Improper integrals", "Improper integrals and numerical integration."),
            ("Applications of integration", "Volumes of revolution, arc length and work."),
            ("Sequences and series", "Sequences, infinite series and convergence tests."),
            ("Power and Taylor series", "Power series, Taylor and Maclaurin series."),
            ("Parametric and polar curves", "Parametric equations and polar coordinates."),
        ],
    ),
    CatalogCourse(
        "MATH 2568",
        "Linear Algebra",
        3,
        "Mathematics",
        "Sophomore-level linear algebra for majors.",
        "Matrices, vector spaces, linear transformations and eigenvalues.",
        [
            (
                "Linear systems and row reduction",
                "Systems of linear equations, Gaussian elimination, row reduction and echelon forms.",
            ),
            ("Matrix algebra and inverses", "Matrix operations, matrix inverses and elementary matrices."),
            ("Determinants", "Determinants and their properties."),
            ("Vector spaces and subspaces", "Vector spaces, subspaces, null space and column space."),
            ("Basis and dimension", "Linear independence, basis, dimension and rank."),
            ("Linear transformations", "Linear transformations and their matrices."),
            ("Eigenvalues and eigenvectors", "Eigenvalues, eigenvectors and the characteristic equation."),
            ("Diagonalization", "Diagonalization of matrices."),
            (
                "Orthogonality and least squares",
                "Inner products, orthogonal projections, the Gram-Schmidt process and least squares.",
            ),
        ],
    ),
    CatalogCourse(
        "MATH 1050",
        "College Algebra",
        3,
        "Mathematics",
        "Pre-calculus level course; not equivalent to calculus.",
        "Functions, polynomials, exponential and logarithmic functions.",
        [
            ("Functions and graphs", "Functions, domain and range, graphs and transformations."),
            ("Polynomial and rational functions", "Polynomial and rational functions and their zeros."),
            ("Exponential and logarithmic functions", "Exponential and logarithmic functions and equations."),
            ("Systems of equations", "Systems of linear equations and inequalities."),
        ],
    ),
    CatalogCourse(
        "PHYSICS 1250",
        "Mechanics, Work and Energy",
        4,
        "Physics",
        "Calculus-based mechanics for science and engineering majors.",
        "Calculus-based introductory mechanics.",
        [
            ("Kinematics", "Kinematics in one and two dimensions, vectors and projectile motion."),
            ("Newton's laws", "Newton's laws of motion, free-body diagrams, friction and circular motion."),
            ("Work and energy", "Work, kinetic energy, potential energy and conservation of energy."),
            ("Momentum and collisions", "Linear momentum, impulse and collisions."),
            ("Rotational dynamics", "Rotation, torque, moment of inertia and angular momentum."),
            ("Oscillations and gravitation", "Simple harmonic motion and universal gravitation."),
        ],
    ),
    CatalogCourse(
        "CHEM 1210",
        "General Chemistry I",
        4,
        "Chemistry",
        "First semester of general chemistry for science majors, with laboratory.",
        "Principles of chemistry with laboratory.",
        [
            ("Stoichiometry", "The mole, chemical equations and stoichiometry."),
            ("Aqueous reactions", "Reactions in aqueous solution."),
            ("Thermochemistry", "Thermochemistry: enthalpy, calorimetry and Hess's law."),
            ("Atomic structure and periodicity", "Electronic structure of atoms and periodic trends."),
            (
                "Chemical bonding and molecular geometry",
                "Ionic and covalent bonding, Lewis structures, VSEPR and molecular geometry.",
            ),
            ("Gases", "Gas laws and the ideal gas equation."),
            ("Laboratory techniques", "Weekly laboratory experiments in measurement, synthesis and titration."),
        ],
    ),
    CatalogCourse(
        "CSE 1222",
        "Introduction to Programming in C",
        3,
        "Computer Science and Engineering",
        "First programming course for engineering majors.",
        "Programming in C.",
        [
            ("C syntax, types and operators", "Variables, data types, operators and expressions in C."),
            ("Control flow", "Conditional statements and loops."),
            ("Functions", "Functions, parameters and scope."),
            ("Arrays and strings", "Arrays and strings."),
            ("Pointers and dynamic memory", "Pointers, pointer arithmetic and dynamic memory allocation."),
            ("Structures and file I/O", "Structures and file input and output."),
        ],
    ),
    CatalogCourse(
        "CSE 2231",
        "Software II: Data Structures",
        3,
        "Computer Science and Engineering",
        "Second programming course on data structures; requires CS1.",
        "Data structures and algorithm analysis.",
        [
            ("Algorithm analysis", "Asymptotic analysis and Big-O notation."),
            ("Linked lists, stacks and queues", "Linked lists, stacks and queues."),
            ("Trees and binary search trees", "Binary trees, binary search trees and balanced trees."),
            ("Heaps and priority queues", "Heaps and priority queues."),
            ("Hashing", "Hash tables and hashing."),
            ("Sorting algorithms", "Sorting algorithms including merge sort and quick sort."),
            ("Graphs", "Graph representation and traversal."),
        ],
    ),
    CatalogCourse(
        "CSE 2321",
        "Foundations I: Discrete Structures",
        3,
        "Computer Science and Engineering",
        "Discrete mathematics for CSE majors, proof-based.",
        "Discrete mathematics for computer science.",
        [
            ("Logic and proofs", "Propositional and predicate logic and proof techniques."),
            ("Induction", "Mathematical induction and recursion."),
            ("Sets, functions and relations", "Sets, functions and relations."),
            ("Counting", "Permutations, combinations and the pigeonhole principle."),
            ("Graphs and trees", "Graph theory and trees."),
        ],
    ),
    CatalogCourse(
        "ENGLISH 1110",
        "First-Year English Composition",
        3,
        "English",
        "First-year college writing.",
        "Academic writing and argument.",
        [
            ("Rhetorical analysis", "Rhetorical analysis of texts for audience and purpose."),
            ("Argument", "Composing thesis-driven arguments."),
            ("Research and citation", "Research writing with sources and citation."),
            ("Revision", "Drafting, peer review and revision."),
        ],
    ),
    CatalogCourse(
        "HISTORY 1151",
        "American Civilization to 1877",
        3,
        "History",
        "Introductory survey of United States history.",
        "Survey of American history to 1877.",
        [
            ("Colonial America", "Colonial societies in North America."),
            ("Revolution and Constitution", "The American Revolution and the Constitution."),
            ("Antebellum era", "Expansion, slavery and the antebellum era."),
            ("Civil War and Reconstruction", "The Civil War and Reconstruction."),
        ],
    ),
]


def reference_syllabus_text(course: CatalogCourse) -> str:
    lines = [
        "Midwest State University",
        f"{course.code} {course.title}",
        f"Credits: {course.credits:g}",
        "",
        "Course Description",
        course.description,
        "",
        "Weekly Schedule",
    ]
    lines += [f"Week {i}: {sentence}" for i, (_, sentence) in enumerate(course.concepts, start=1)]
    return "\n".join(lines)
